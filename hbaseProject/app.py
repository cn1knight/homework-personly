import tempfile

from flask import Flask, render_template, request, jsonify, redirect, url_for
import happybase
import csv
import os
import json
import time
import subprocess
from io import StringIO
from threading import Thread
import datetime

app = Flask(__name__)

# HBase连接配置
HBASE_HOST = '127.0.0.1'
HBASE_PORT = 19090

# 表名和列族配置
MOVIES_TABLE = 'movies'
RATINGS_TABLE = 'ratings'
MOVIE_RATINGS_TABLE = 'movie_avg_ratings'
HOT_MOVIES_TABLE = 'hot_movies'
COLUMN_FAMILY = 'info'  # 统一使用'info'列族


def get_connection():
    """获取HBase连接"""
    return happybase.Connection(
        host=HBASE_HOST,
        port=HBASE_PORT,
        timeout=30000,  # 增加超时时间
        autoconnect=False
    )


@app.route('/')
def index():
    """首页"""
    hot_movies_data = []
    connection = None
    try:
        connection = get_connection()
        connection.open()
        table = connection.table(HOT_MOVIES_TABLE)

        latest_timestamp = None
        latest_hot_movies_json = None

        # 获取最新的热门电影数据，假设行键是时间戳或者可以排序的标识
        # 实际应用中，HOT_MOVIES_TABLE的行键设计很重要
        # 这里简化为扫描并找到最新的记录
        # 假设行键是时间戳倒序排列，或者有一个特定的行键存储最新的热门电影列表
        # 如果行键不是时间戳，可能需要扫描表并根据'info:timestamp'列排序
        # 为简化，我们假设表里只有一条或几条记录，取最新的那条
        # 或者，如果表结构是固定的，比如总有一行叫 'latest_hot_movies'
        # row = table.row(b'latest_hot_movies') 
        # if row: 
        #    latest_hot_movies_json = row.get(f'{COLUMN_FAMILY}:hot_movies'.encode(), b'[]').decode('utf-8')
        # else: # Fallback to scan if specific row key not found
        
        # 扫描表，找到时间戳最大的那条记录
        for key, data in table.scan(limit=100): # Limit scan for performance
            timestamp = data.get(f'{COLUMN_FAMILY}:timestamp'.encode(), b'0').decode('utf-8')
            if timestamp.isdigit():
                if latest_timestamp is None or int(timestamp) > int(latest_timestamp):
                    latest_timestamp = timestamp
                    latest_hot_movies_json = data.get(f'{COLUMN_FAMILY}:hot_movies'.encode(), b'[]').decode('utf-8')

        if latest_hot_movies_json:
            hot_movies_data = json.loads(latest_hot_movies_json)
            # 为每个电影添加海报URL
            for movie in hot_movies_data:
                movie['poster_url'] = url_for('static', filename=f'images/posters/{movie.get("movie_id")}.jpg')
        
    except Exception as e:
        print(f"Error fetching hot movies for index: {e}")
        hot_movies_data = [] # 出错时返回空列表
    finally:
        if connection:
            connection.close()

    return render_template('index.html', hot_movies=hot_movies_data)


def create_table_if_not_exists(connection, table_name):
    """更健壮的表创建方法"""
    try:
        # 先检查表是否存在
        tables = connection.tables()
        if table_name.encode() not in tables:
            # 创建表（统一使用info列族）
            connection.create_table(
                table_name,
                {COLUMN_FAMILY: dict()}  # 使用统一的列族名
            )
            print(f"表 {table_name} 创建成功")
            return True
        print(f"表 {table_name} 已存在")
        return False
    except Exception as e:
        print(f"创建表 {table_name} 时出错: {str(e)}")
        # 尝试处理表可能已存在的情况
        if "already exists" in str(e):
            return False
        raise


from flask import jsonify, render_template, request
import csv
from threading import Thread, Lock
from collections import defaultdict

# 全局变量用于存储导入进度（生产环境中建议使用Redis等持久化存储）
import_progress = defaultdict(dict)
progress_lock = Lock()


def update_progress(import_type, current, total=None):
    """更新导入进度"""
    with progress_lock:
        if current < 0:
            # 标记为出错状态
            import_progress[import_type] = {
                'current': 0,
                'total': 0,
                'percentage': 0,
                'error': True
            }
            return

        if total:
            import_progress[import_type]['total'] = total
        import_progress[import_type]['current'] = current
        import_progress[import_type]['percentage'] = int(
            (current / (total or current)) * 100) if total and total > 0 else 0
        import_progress[import_type]['error'] = False

def get_progress(import_type):
    """获取当前导入进度"""
    with progress_lock:
        return import_progress.get(import_type, {'current': 0, 'total': 0, 'percentage': 0})


def batch_insert_movies(connection, batch):
    """批量插入电影数据到HBase"""
    if not batch:
        return

    table = connection.table(MOVIES_TABLE)
    try:
        with table.batch() as b:
            for movie in batch:
                row_key = movie['movieId']
                data = {
                    'info:title': movie['title'],
                    'info:genres': movie['genres']
                }
                b.put(row_key, data)
    except Exception as e:
        raise Exception(f"批量插入电影数据失败: {str(e)}")


def batch_insert_ratings(connection, batch):
    """批量插入评分数据到HBase"""
    if not batch:
        return

    table = connection.table(RATINGS_TABLE)
    try:
        with table.batch() as b:
            for rating in batch:
                row_key = f"{rating['userId']}_{rating['movieId']}_{rating['timestamp']}"
                data = {
                    'info:userId': str(rating['userId']),
                    'info:movieId': str(rating['movieId']),
                    'info:rating': str(rating['rating']),
                    'info:timestamp': str(rating['timestamp'])
                }
                b.put(row_key, data)
    except Exception as e:
        raise Exception(f"批量插入评分数据失败: {str(e)}")


def import_movies(connection, file_stream):
    batch_size = 2000  # 增加批次大小
    batch = []

    # 使用流式处理读取文件，不再计算总行数（这会导致文件被完整读取一遍）
    reader = csv.reader(file_stream)
    next(reader, None)  # 跳过标题行（如果有）

    current_line = 0
    processed = 0
    estimated_total = 100000  # 初始估计值

    for row in reader:
        current_line += 1
        if len(row) < 3:
            continue

        movie_data = {
            'movieId': row[0],
            'title': row[1],
            'genres': row[2]
        }
        batch.append(movie_data)

        # 每100行更新一次进度，减少进度更新频率
        if current_line % 100 == 0:
            update_progress('movies', current_line, estimated_total)

        if len(batch) >= batch_size:
            batch_insert_movies(connection, batch)
            processed += len(batch)
            batch = []

            # 每处理10个批次，重新估计总数
            if processed % (batch_size * 10) == 0:
                # 根据已处理的数据量调整估计总数
                if current_line > estimated_total / 2:
                    estimated_total = int(current_line * 1.5)
                update_progress('movies', current_line, estimated_total)

    if batch:
        batch_insert_movies(connection, batch)

    # 最终更新为100%完成
    update_progress('movies', current_line, current_line)

def import_ratings(connection, file_stream):
    batch_size = 100000  # 评分数据更大，使用更大的批次
    batch = []

    reader = csv.reader(file_stream)
    next(reader, None)  # 跳过标题行

    current_line = 0
    processed = 0
    estimated_total = 30000000  # 初始估计值

    for row in reader:
        current_line += 1
        if len(row) < 4:
            continue

        rating_data = {
            'userId': row[0],
            'movieId': row[1],
            'rating': row[2],
            'timestamp': row[3]
        }
        batch.append(rating_data)

        # 每10000行更新一次进度，减少更新频率
        if current_line % 10000 == 0:
            update_progress('ratings', current_line, estimated_total)

        if len(batch) >= batch_size:
            batch_insert_ratings(connection, batch)
            processed += len(batch)
            batch = []

            # 每处理10个批次，重新估计总数
            if processed % (batch_size * 10) == 0:
                if current_line > estimated_total / 5:
                    estimated_total = int(current_line * 1.2)
                update_progress('ratings', current_line, estimated_total)

    if batch:
        batch_insert_ratings(connection, batch)

    # 最终更新为100%完成
    update_progress('ratings', current_line, current_line)

@app.route('/import/progress')
def get_import_progress():
    """获取导入进度API"""
    return jsonify({
        'movies': get_progress('movies'),
        'ratings': get_progress('ratings')
    })


@app.route('/import', methods=['GET', 'POST'])
def import_data():
    """导入数据页面"""
    if request.method == 'POST':
        if 'movies_file' not in request.files or 'ratings_file' not in request.files:
            return jsonify({'status': 'error', 'message': '请上传电影和评分CSV文件'})

        movies_file = request.files['movies_file']
        ratings_file = request.files['ratings_file']

        if movies_file.filename == '' or ratings_file.filename == '':
            return jsonify({'status': 'error', 'message': '请选择文件'})

        try:
            # 重置进度
            update_progress('movies', 0, 100000)  # 设置初始估计值
            update_progress('ratings', 0, 30000000)  # 设置初始估计值

            connection = get_connection()
            connection.open()

            # 创建表
            create_table_if_not_exists(connection, MOVIES_TABLE)
            create_table_if_not_exists(connection, RATINGS_TABLE)
            create_table_if_not_exists(connection, MOVIE_RATINGS_TABLE)
            create_table_if_not_exists(connection, HOT_MOVIES_TABLE)

            # 保存文件到临时目录，避免内存溢出
            import tempfile
            import os

            temp_dir = tempfile.mkdtemp()
            movies_path = os.path.join(temp_dir, 'movies.csv')
            ratings_path = os.path.join(temp_dir, 'ratings.csv')

            movies_file.save(movies_path)
            ratings_file.save(ratings_path)

            # 使用线程处理导入
            def import_task():
                try:
                    # 先导入电影数据（较小）
                    with open(movies_path, 'r', encoding='utf-8') as f:
                        import_movies(connection, f)

                    # 再导入评分数据（较大）
                    with open(ratings_path, 'r', encoding='utf-8') as f:
                        import_ratings(connection, f)

                    # 导入完成后，删除临时文件
                    os.remove(movies_path)
                    os.remove(ratings_path)
                    os.rmdir(temp_dir)

                    # 启动批处理计算
                    Thread(target=run_batch_processing).start()
                except Exception as e:
                    update_progress('movies', -1)  # 标记出错
                    update_progress('ratings', -1)  # 标记出错
                    print(f"导入出错: {str(e)}")
                finally:
                    connection.close()

            Thread(target=import_task).start()

            return jsonify({'status': 'success', 'message': '数据导入已开始，请查看进度'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': f'导入失败: {str(e)}'})

    return render_template('import.html')

def run_batch_processing():
    """运行批处理脚本"""
    try:
        # 假设批处理脚本在同一目录
        script_path = os.path.join(app.root_path, 'movie_rating_batch.py')
        subprocess.run(['python', script_path], check=True)
    except Exception as e:
        print(f"运行批处理脚本时出错: {str(e)}")


def run_stream_processing():
    """运行流处理脚本"""
    try:
        # 假设流处理脚本在同一目录
        script_path = os.path.join(app.root_path, 'movie_rating_stream.py')
        subprocess.run(['python', script_path], check=True)
    except Exception as e:
        print(f"运行流处理脚本时出错: {str(e)}")


@app.route('/database_status')
def database_status():
    # TODO: 实现数据库状态检查逻辑
    # 比如检查HBase连接，表是否存在，数据量等
    hbase_connected = False
    tables_status = {}
    try:
        connection = get_connection()
        connection.open()
        hbase_connected = True
        tables = connection.tables()
        table_names = [MOVIES_TABLE, RATINGS_TABLE, MOVIE_RATINGS_TABLE, HOT_MOVIES_TABLE]
        for t_name in table_names:
            tables_status[t_name] = {'exists': t_name.encode() in tables, 'count': 'N/A'}
            # 获取表行数在HBase中通常需要扫描，可能较慢，此处暂不实现详细计数
        connection.close()
    except Exception as e:
        print(f"Error checking HBase status: {e}")
        hbase_connected = False
    return render_template('database_status.html', hbase_connected=hbase_connected, tables_status=tables_status)


@app.route('/search_user_ratings', methods=['GET'])
def search_user_ratings():
    user_id = request.args.get('user_id', '').strip()
    ratings = []
    message = ""
    if not user_id:
        message = "请输入用户ID进行搜索。"
        return render_template('user_ratings.html', ratings=ratings, message=message, user_id=user_id)

    connection = None
    try:
        connection = get_connection()
        connection.open()
        ratings_table = connection.table(RATINGS_TABLE)
        movies_table = connection.table(MOVIES_TABLE)

        user_ratings_data = []
        # 假设 ratings 表的行键是 userId_movieId_timestamp
        for key, data in ratings_table.scan(row_prefix=f"{user_id}_".encode()):
            movie_id = data.get(f'{COLUMN_FAMILY}:movieId'.encode(), b'').decode('utf-8')
            rating_value = data.get(f'{COLUMN_FAMILY}:rating'.encode(), b'').decode('utf-8')
            timestamp_val = data.get(f'{COLUMN_FAMILY}:timestamp'.encode(), b'').decode('utf-8')
            
            movie_title = '未知电影'
            # 根据movieId获取电影标题, movieId 在 movies 表中是行键
            movie_row = movies_table.row(movie_id.encode()) 
            if movie_row:
                movie_title = movie_row.get(f'{COLUMN_FAMILY}:title'.encode(), 'Unknown Movie'.encode('utf-8')).decode('utf-8')

            user_ratings_data.append({
                'movie_id': movie_id,
                'movie_title': movie_title,
                'rating': rating_value,
                'timestamp': datetime.datetime.fromtimestamp(int(timestamp_val)).strftime('%Y-%m-%d %H:%M:%S') if timestamp_val.isdigit() else timestamp_val
            })
        
        if user_ratings_data:
            ratings = sorted(user_ratings_data, key=lambda x: x['timestamp'], reverse=True)
        else:
            message = f"未找到用户ID '{user_id}' 的评分记录。"

    except Exception as e:
        message = f"查询用户评分失败: {str(e)}"
        print(f"Error querying user ratings for {user_id}: {e}")
    finally:
        if connection:
            connection.close()
    
    return render_template('user_ratings.html', ratings=ratings, message=message, user_id=user_id)


@app.route('/search', methods=['GET'])
def search_page():
    title_query = request.args.get('title_query', '').strip().lower()
    genre_query = request.args.get('genre_query', '').strip().lower()
    page = request.args.get('page', 1, type=int)
    per_page = 30 # 3卡片/行 * 10行 = 30个卡片每页

    results = []
    message = ""
    total_movies = 0
    total_pages = 0
    connection = None

    if not title_query and not genre_query:
        message = "请输入电影标题或类型进行搜索，或浏览热门推荐。"
        return render_template('search_page.html', movies=[], message=message, page=page, 
                               total_pages=total_pages, title_query=title_query, genre_query=genre_query,
                               current_page=page, has_prev=False, has_next=False, prev_num=None, next_num=None)

    try:
        connection = get_connection()
        connection.open()
        movies_table = connection.table(MOVIES_TABLE)
        movie_ratings_table = connection.table(MOVIE_RATINGS_TABLE) # 获取电影评分表
        
        all_matching_movies = []
        
        # 构建 HBase 过滤器
        filter_list = []
        if title_query:
            # 使用 SubstringComparator 进行模糊匹配标题
            # 注意：HBase 的 SubstringComparator 对大小写敏感，如果需要不敏感，数据层面或应用层面需要额外处理
            filter_list.append(f"SingleColumnValueFilter('{COLUMN_FAMILY}', 'title', =, 'substring:{title_query}')")
        
        if genre_query:
            query_genres_list = [g.strip() for g in genre_query.split(',') if g.strip()]
            # 对于多类型查询，需要确保每个类型都存在。这可以通过多个 SingleColumnValueFilter 实现
            # HBase 的 FilterList(MUST_PASS_ALL) 可以组合它们
            # 更复杂的类型查询（如部分匹配、OR逻辑）可能需要更复杂的过滤器或应用层逻辑
            for g_query in query_genres_list:
                filter_list.append(f"SingleColumnValueFilter('{COLUMN_FAMILY}', 'genres', =, 'substring:{g_query}')")
        
        hbase_filter_str = None
        if len(filter_list) > 1:
            hbase_filter_str = f"FilterList(MUST_PASS_ALL, [{', '.join(filter_list)}])"
        elif len(filter_list) == 1:
            hbase_filter_str = filter_list[0]

        # scan_limit 仍然可以用于防止返回过多数据，但过滤应该在服务器端进行
        # 注意：HBase scan 的 limit 是限制返回的行数，不是处理的行数。分页最好在应用层做，或者使用 PageFilter
        # 这里我们先获取所有匹配项，再在应用层分页
        
        # 优化：如果查询条件为空，并且希望展示所有电影，则不使用过滤器
        scan_kwargs = {}
        if hbase_filter_str:
            scan_kwargs['filter'] = hbase_filter_str
        # scan_kwargs['limit'] = 50000 # 暂时移除 scan limit，依赖 filter

        for key, data in movies_table.scan(**scan_kwargs):
            movie_id = key.decode('utf-8')
            title = data.get(f'{COLUMN_FAMILY}:title'.encode(), b'').decode('utf-8')
            genres = data.get(f'{COLUMN_FAMILY}:genres'.encode(), b'').decode('utf-8')

            # 应用层再次确认，因为 HBase substring 可能是部分匹配，而需求可能是更精确的
            # 对于标题，如果 HBase filter 已经是 substring，这里可以简化或移除
            # 对于类型，如果 HBase filter 已经是 substring 并且是 AND 逻辑，这里也可能可以简化
            # 但为了确保逻辑正确性，保留应用层校验，特别是对于 genre_query 的 all 匹配逻辑
            title_match_app_layer = True
            if title_query and not (title_query in title.lower()): # 确保应用层也是小写比较
                title_match_app_layer = False

            genre_match_app_layer = True
            if genre_query:
                current_movie_genres_set = set(g.lower() for g in genres.split('|'))
                # query_genres_list 已经在上面定义并处理为小写
                if not all(q_g.lower() in current_movie_genres_set for q_g in query_genres_list):
                    genre_match_app_layer = False
            
            if not (title_match_app_layer and genre_match_app_layer):
                continue # 如果应用层校验不通过，则跳过这条记录

            avg_rating = 'N/A'
            rating_row = movie_ratings_table.row(movie_id.encode())
            # 使用 COLUMN_FAMILY 而不是未定义的 STATS_COLUMN_FAMILY
            if rating_row and f'{COLUMN_FAMILY}:avg_rating'.encode() in rating_row:
                avg_rating_bytes = rating_row[f'{COLUMN_FAMILY}:avg_rating'.encode()]
                try:
                    avg_rating_val = float(avg_rating_bytes.decode('utf-8'))
                    avg_rating = f"{avg_rating_val:.1f}"
                except ValueError:
                    avg_rating = 'N/A'

            all_matching_movies.append({
                'movie_id': movie_id,
                'title': title,
                'genres': genres,
                'avg_rating': avg_rating,
                'poster_url': url_for('static', filename=f'images/posters/{movie_id}.jpg')
            })
        
        total_movies = len(all_matching_movies)
        if total_movies == 0 and (title_query or genre_query):
            message = "未找到符合条件的电影。"
        elif total_movies == 0:
            message = "电影库为空或未能加载电影数据。"
        
        # 分页
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        paginated_movies = all_matching_movies[start_index:end_index]
        total_pages = (total_movies + per_page - 1) // per_page

        results = paginated_movies

    except Exception as e:
        message = f"电影搜索失败: {str(e)}"
        print(f"Error in search_page: {e}")
    finally:
        if connection:
            connection.close()

    return render_template('search_page.html', movies=results, message=message, 
                           page=page, total_pages=total_pages, 
                           title_query=request.args.get('title_query', ''), 
                           genre_query=request.args.get('genre_query', ''))


@app.route('/movie/<movie_id>')
def movie_detail_page(movie_id):
    movie_data = None
    ratings_data = []
    message = ""
    connection = None

    try:
        connection = get_connection()
        connection.open()
        movies_table = connection.table(MOVIES_TABLE)
        ratings_table = connection.table(RATINGS_TABLE)
        movie_avg_ratings_table = connection.table(MOVIE_RATINGS_TABLE)

        # 获取电影基本信息, movies表行键是movieId
        movie_row = movies_table.row(movie_id.encode())
        if not movie_row:
            message = "未找到该电影。"
            return render_template('movie_detail.html', movie=None, ratings=[], message=message)

        movie_data = {
            'movie_id': movie_id,
            'title': movie_row.get(f'{COLUMN_FAMILY}:title'.encode(), b'').decode('utf-8'),
            'genres': movie_row.get(f'{COLUMN_FAMILY}:genres'.encode(), b'').decode('utf-8'),
            'poster_url': url_for('static', filename=f'images/posters/{movie_id}.jpg'),
            'overview': '暂无详细剧情简介。', # 假设HBase中没有存储剧情简介
            'release_date': '未知' # 假设HBase中没有存储上映日期
        }

        # 获取电影平均评分和评分次数 (从 movie_avg_ratings 表, 行键是 movie_movieId)
        avg_rating_row = movie_avg_ratings_table.row(f"movie_{movie_id}".encode())
        if avg_rating_row:
            movie_data['avg_rating'] = avg_rating_row.get(f'{COLUMN_FAMILY}:avg_rating'.encode(), b'N/A').decode('utf-8')
            movie_data['rating_count'] = avg_rating_row.get(f'{COLUMN_FAMILY}:rating_count'.encode(), b'0').decode('utf-8')
        else:
            movie_data['avg_rating'] = 'N/A'
            movie_data['rating_count'] = '0'

        # 获取该电影的评分列表 (从 ratings 表, 行键格式: userId_movieId_timestamp)
        # 需要扫描所有包含 _movieId_ 的行，然后过滤
        # 效率较低，理想情况是有按movieId索引的二级表或使用更高级的HBase查询
        count = 0
        # 示例：扫描 ratings 表并过滤 movieId
        # 注意：对于非常大的表，这可能非常慢。应该使用更具针对性的查询，例如使用HBase过滤器或二级索引。
        # 此处为简化演示，直接扫描并过滤。
        for key, data in ratings_table.scan(): # 扫描整个表，非常低效！
            key_str = key.decode('utf-8')
            parts = key_str.split('_') # 行键格式 userId_movieId_timestamp
            if len(parts) == 3 and parts[1] == movie_id:
                ratings_data.append({
                    'user_id': data.get(f'{COLUMN_FAMILY}:userId'.encode(), b'').decode('utf-8'),
                    'rating': data.get(f'{COLUMN_FAMILY}:rating'.encode(), b'').decode('utf-8'),
                    'timestamp': datetime.datetime.fromtimestamp(int(data.get(f'{COLUMN_FAMILY}:timestamp'.encode(), b'0').decode('utf-8'))).strftime('%Y-%m-%d %H:%M:%S')
                })
                count += 1
                if count >= 50: # 最多显示50条评分
                    break
        
        ratings_data.sort(key=lambda x: x['timestamp'], reverse=True)

    except Exception as e:
        message = f"获取电影详情失败: {str(e)}"
        print(f"Error in movie_detail_page for {movie_id}: {e}")
        movie_data = None 
    finally:
        if connection:
            connection.close()

    return render_template('movie_detail.html', movie=movie_data, ratings=ratings_data, message=message)


@app.route('/query/movies', methods=['GET', 'POST'])
def query_movies():
    """查询电影数据"""
    results = []
    message = ""
    connection = None

    if request.method == 'POST':
        try:
            movie_id = request.form.get('movie_id', '')
            movie_title = request.form.get('movie_title', '').strip().lower()
            connection = get_connection()
            connection.open()
            table = connection.table(MOVIES_TABLE)

            if movie_id:
                # 查询特定电影
                row_key = f"movie_{movie_id}".encode()
                row = table.row(row_key)
                if row:
                    results.append({
                        'movie_id': movie_id,
                        'title': row.get(f'{COLUMN_FAMILY}:title'.encode(), b'').decode('utf-8'),
                        'genres': row.get(f'{COLUMN_FAMILY}:genres'.encode(), b'').decode('utf-8')
                    })
                else:
                    message = f"未找到ID为{movie_id}的电影"
            elif movie_title:
                # 通过电影名称查询 - 需要全表扫描
                for key, data in table.scan(limit=10000):  # 增加限制避免性能问题
                    title = data.get(f'{COLUMN_FAMILY}:title'.encode(), b'').decode('utf-8').lower()
                    if movie_title in title:
                        movie_id = key.decode('utf-8').split('_')[1] if '_' in key.decode('utf-8') else key.decode(
                            'utf-8')
                        results.append({
                            'movie_id': movie_id,
                            'title': data.get(f'{COLUMN_FAMILY}:title'.encode(), b'').decode('utf-8'),
                            'genres': data.get(f'{COLUMN_FAMILY}:genres'.encode(), b'').decode('utf-8')
                        })
                if not results:
                    message = f"未找到包含'{movie_title}'的电影"
            else:
                # 查询所有电影（限制50条）
                for key, data in table.scan(limit=50):
                    movie_id = key.decode('utf-8').split('_')[1] if '_' in key.decode('utf-8') else key.decode('utf-8')
                    results.append({
                        'movie_id': movie_id,
                        'title': data.get(f'{COLUMN_FAMILY}:title'.encode(), b'').decode('utf-8'),
                        'genres': data.get(f'{COLUMN_FAMILY}:genres'.encode(), b'').decode('utf-8')
                    })

                if not results:
                    message = "未找到电影数据"

        except Exception as e:
            message = f"查询失败: {str(e)}"
        finally:
            if connection:
                connection.close()

    return render_template('query_movies.html', results=results, message=message)



@app.route('/query/ratings', methods=['GET', 'POST'])
def query_ratings():
    """查询评分数据"""
    results = []
    message = ""
    rating_stats = {}  # 用于存储电影评分统计信息
    connection = None

    if request.method == 'POST':
        try:
            movie_title = request.form.get('movie_title', '').strip().lower()
            connection = get_connection()
            connection.open()

            # 获取评分表和电影表
            ratings_table = connection.table(RATINGS_TABLE)
            movies_table = connection.table(MOVIES_TABLE)

            # 获取匹配的电影ID
            movie_ids = []
            if movie_title:
                for key, data in movies_table.scan(limit=10000):
                    title = data.get(f'{COLUMN_FAMILY}:title'.encode(), b'').decode('utf-8').lower()
                    if movie_title in title:
                        movie_id = key.decode('utf-8').split('_')[1] if '_' in key.decode('utf-8') else key.decode(
                            'utf-8')
                        movie_ids.append(movie_id)
                if not movie_ids:
                    message = f"未找到包含'{movie_title}'的电影"

            # 查询特定电影的所有评分
            if movie_ids:
                for movie_id in movie_ids:
                    # 获取电影信息
                    movie_row = movies_table.row(f"movie_{movie_id}".encode())
                    full_movie_title = movie_row.get(f'{COLUMN_FAMILY}:title'.encode(), b'').decode('utf-8')
                    genres = movie_row.get(f'{COLUMN_FAMILY}:genres'.encode(), b'').decode('utf-8')

                    # 使用行键前缀扫描提高效率
                    # 注意：这里假设行键格式是 userId_movieId_timestamp
                    # 所以我们需要扫描所有包含 _movieId_ 的行
                    prefix_filter = f"_{movie_id}_"
                    ratings = []
                    rating_details = []
                    rating_distribution = {'1': 0, '2': 0, '3': 0, '4': 0, '5': 0}

                    # 修改列名匹配HBase实际存储
                    for key, data in ratings_table.scan(row_prefix=None, limit=10000):
                        key_str = key.decode('utf-8')
                        if f"_{movie_id}_" in key_str:
                            rating = float(data.get(f'{COLUMN_FAMILY}:rating'.encode(), b'0').decode('utf-8'))
                            ratings.append(rating)

                            # 更新评分分布
                            rating_key = str(int(round(rating)))
                            rating_distribution[rating_key] = rating_distribution.get(rating_key, 0) + 1

                            # 存储评分详情
                            rating_details.append({
                                'user_id': data.get(f'{COLUMN_FAMILY}:userId'.encode(), b'').decode('utf-8'),
                                # 改为userId
                                'movie_id': movie_id,
                                'movie_title': full_movie_title,
                                'rating': rating,
                                'timestamp': data.get(f'{COLUMN_FAMILY}:timestamp'.encode(), b'').decode('utf-8')
                            })

                    # 计算评分统计信息
                    if ratings:
                        rating_stats[full_movie_title] = {
                            'avg_rating': round(sum(ratings) / len(ratings), 2),
                            'max_rating': max(ratings),
                            'min_rating': min(ratings),
                            'rating_count': len(ratings),
                            'genres': genres,
                            'rating_distribution': rating_distribution,
                            'rating_details': rating_details
                        }

                if not rating_stats:
                    message = f"未找到电影{movie_title}的评分数据"
            else:
                message = "请输入电影名称进行查询"

        except Exception as e:
            message = f"查询失败: {str(e)}"
        finally:
            if connection:
                connection.close()

    return render_template('query_ratings.html', results=results, message=message, rating_stats=rating_stats)


@app.route('/batch/ratings')
def batch_ratings():
    results = []
    message = None
    connection = None

    # 获取分页参数，默认为第1页，每页10条
    page = request.args.get('page', 1, type=int)
    per_page = 10
    sort_by = request.args.get('sort_by', 'avg_rating')

    try:
        connection = get_connection()
        connection.open()
        table = connection.table(MOVIE_RATINGS_TABLE)

        # 查询所有批处理计算的电影评分
        for key, data in table.scan(limit=1000000):  # 增加limit以获取更多数据
            movie_id = data.get(f'{COLUMN_FAMILY}:movie_id'.encode(), b'').decode('utf-8')
            title = data.get(f'{COLUMN_FAMILY}:title'.encode(), b'').decode('utf-8')
            avg_rating = float(data.get(f'{COLUMN_FAMILY}:avg_rating'.encode(), b'0').decode('utf-8'))
            rating_count = int(data.get(f'{COLUMN_FAMILY}:rating_count'.encode(), b'0').decode('utf-8'))
            last_updated = data.get(f'{COLUMN_FAMILY}:last_updated'.encode(), b'0').decode('utf-8')

            if last_updated.isdigit():
                last_updated_dt = datetime.datetime.fromtimestamp(int(last_updated))
                last_updated = last_updated_dt.strftime('%Y-%m-%d %H:%M:%S')

            results.append({
                'movie_id': movie_id,
                'title': title,
                'avg_rating': avg_rating,
                'rating_count': rating_count,
                'last_updated': last_updated
            })

        # 根据排序参数排序
        if sort_by == 'avg_rating':
            results.sort(key=lambda x: x['avg_rating'], reverse=True)
        elif sort_by == 'rating_count':
            results.sort(key=lambda x: x['rating_count'], reverse=True)

        # 计算分页
        total_items = len(results)
        total_pages = (total_items + per_page - 1) // per_page
        start = (page - 1) * per_page
        end = start + per_page
        paginated_results = results[start:end]

        if not results:
            message = "未找到批处理计算的评分数据"

    except Exception as e:
        message = f"查询失败: {str(e)}"
    finally:
        if connection:
            connection.close()

    return render_template('batch_ratings.html',
                           results=paginated_results,
                           message=message,
                           page=page,
                           total_pages=total_pages,
                           sort_by=sort_by)


@app.route('/hot/movies', methods=['GET'])
def hot_movies():
    """查询热门电影"""
    results = []
    message = ""
    connection = None

    try:
        connection = get_connection()
        connection.open()
        table = connection.table(HOT_MOVIES_TABLE)

        # 获取最新的热门电影数据
        latest_timestamp = None
        latest_hot_movies = None

        for key, data in table.scan(limit=100):
            timestamp = data.get(f'{COLUMN_FAMILY}:timestamp'.encode(), b'0').decode('utf-8')

            if timestamp.isdigit():
                if latest_timestamp is None or int(timestamp) > int(latest_timestamp):
                    latest_timestamp = timestamp
                    latest_hot_movies = data.get(f'{COLUMN_FAMILY}:hot_movies'.encode(), b'[]').decode('utf-8')

        if latest_hot_movies:
            # 解析JSON数据
            hot_movies_data = json.loads(latest_hot_movies)

            # 格式化时间戳
            timestamp_dt = datetime.datetime.fromtimestamp(int(latest_timestamp))
            formatted_time = timestamp_dt.strftime('%Y-%m-%d %H:%M:%S')

            results = hot_movies_data
            window_end_time = formatted_time
        else:
            message = "未找到热门电影数据"
            window_end_time = None

    except Exception as e:
        message = f"查询失败: {str(e)}"
        window_end_time = None
    finally:
        if connection:
            connection.close()

    return render_template('hot_movies.html', results=results, message=message, window_end_time=window_end_time)


@app.route('/start/stream', methods=['GET'])
def start_stream():
    """启动流处理"""
    try:
        # 在后台线程启动流处理
        Thread(target=run_stream_processing, daemon=True).start()
        return redirect(url_for('hot_movies'))
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'启动流处理失败: {str(e)}'})


if __name__ == '__main__':
    # 确保模板目录存在
    os.makedirs('templates', exist_ok=True)

    app.run(debug=True, host='0.0.0.0', port=5000)
