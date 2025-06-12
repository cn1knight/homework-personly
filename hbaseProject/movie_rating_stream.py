# movie_rating_stream.py
from pyspark.sql import SparkSession
from pyspark.sql.functions import window, count, col, desc, from_json, to_timestamp
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, LongType
import happybase
import time
import json
import random
from datetime import datetime
from threading import Thread

# HBase配置
HBASE_HOST = '127.0.0.1'
HBASE_PORT = 19090
HOT_MOVIES_TABLE = 'hot_movies'
COLUMN_FAMILY = 'info'


def create_hbase_table_if_not_exists(connection, table_name):
    """创建HBase表如果不存在"""
    try:
        tables = connection.tables()
        if table_name.encode() not in tables:
            connection.create_table(
                table_name,
                {COLUMN_FAMILY: dict()}
            )
            print(f"表 {table_name} 创建成功")
            return True
        print(f"表 {table_name} 已存在")
        return False
    except Exception as e:
        print(f"创建表 {table_name} 时出错: {str(e)}")
        if "already exists" in str(e):
            return False
        raise


def save_hot_movies_to_hbase(timestamp, hot_movies_json):
    """保存热门电影到HBase"""
    try:
        connection = happybase.Connection(host=HBASE_HOST, port=HBASE_PORT)
        connection.open()
        create_hbase_table_if_not_exists(connection, HOT_MOVIES_TABLE)

        table = connection.table(HOT_MOVIES_TABLE)
        row_key = f"hot_{timestamp}".encode()

        table.put(row_key, {
            f'{COLUMN_FAMILY}:timestamp'.encode(): str(timestamp).encode(),
            f'{COLUMN_FAMILY}:hot_movies'.encode(): hot_movies_json.encode()
        })

        print(f"热门电影数据已保存到HBase, 时间戳: {timestamp}")
    except Exception as e:
        print(f"保存热门电影到HBase时出错: {str(e)}")
    finally:
        if connection:
            connection.close()


def generate_ratings(movies, spark_context):
    """模拟生成实时电影评分数据"""
    movie_ids = [movie[0] for movie in movies]
    user_ids = list(range(1, 1001))  # 假设有1000个用户

    while True:
        # 随机选择用户和电影
        user_id = random.choice(user_ids)
        movie_id = random.choice(movie_ids)
        rating = round(random.uniform(1, 5), 1)  # 1.0-5.0的随机评分
        timestamp = int(time.time())

        # 创建评分数据
        rating_data = {
            "userId": user_id,
            "movieId": movie_id,
            "rating": rating,
            "timestamp": timestamp
        }

        # 将数据发送到Spark Streaming
        yield json.dumps(rating_data)

        # 每0.1-0.5秒生成一条评分
        time.sleep(random.uniform(0.1, 0.5))


def process_streaming_ratings(movies_path):
    """处理实时电影评分流"""
    # 创建SparkSession
    spark = SparkSession.builder \
        .appName("MovieRatingStream") \
        .getOrCreate()

    # 读取电影数据
    movies_df = spark.read.csv(movies_path, header=True, inferSchema=True)
    # 重命名列以避免歧义
    movies_df = movies_df.withColumnRenamed("movieId", "movie_id")
    movies = [(row.movie_id, row.title) for row in movies_df.collect()]

    # 定义评分数据的模式
    rating_schema = StructType([
        StructField("userId", StringType(), True),
        StructField("movieId", StringType(), True),
        StructField("rating", DoubleType(), True),
        StructField("timestamp", LongType(), True)
    ])

    # 启动模拟数据生成器
    def start_generator():
        from pyspark.sql.streaming import DataStreamWriter
        from socketserver import TCPServer, StreamRequestHandler

        class RatingHandler(StreamRequestHandler):
            def handle(self):
                for rating in generate_ratings(movies, spark.sparkContext):
                    self.wfile.write(f"{rating}\n".encode())

        # 启动套接字服务器
        server = TCPServer(("localhost", 9999), RatingHandler)
        server.serve_forever()

    # 在后台线程中启动生成器
    Thread(target=start_generator, daemon=True).start()

    # 从套接字流读取数据
    streaming_df = spark \
        .readStream \
        .format("socket") \
        .option("host", "localhost") \
        .option("port", 9999) \
        .load()

    # 解析JSON数据
    parsed_df = streaming_df \
        .select(from_json(col("value"), rating_schema).alias("data")) \
        .select("data.*")

    # 添加时间戳列
    df_with_time = parsed_df \
        .withColumn("event_time", to_timestamp(col("timestamp")))

    # 使用10分钟滑动窗口计算热门电影
    hot_movies = df_with_time \
        .withWatermark("event_time", "10 minutes") \
        .groupBy(
        window(col("event_time"), "10 minutes", "1 minute"),
        col("movieId")
    ) \
        .agg(count("*").alias("rating_count"))

    # 与电影数据关联 - 修复：明确指定join条件并转换类型匹配
    hot_movies_with_titles = hot_movies.join(
        movies_df,
        hot_movies.movieId.cast("int") == movies_df.movie_id
    )

    # 输出结果到控制台和HBase
    query = hot_movies_with_titles \
        .writeStream \
        .outputMode("complete") \
        .foreachBatch(lambda batch_df, batch_id:
                      save_hot_movies_batch(batch_df, batch_id)
                      ) \
        .start()

    query.awaitTermination()


def save_hot_movies_batch(batch_df, batch_id):
    """保存批次的热门电影数据到HBase"""
    if batch_df.count() > 0:
        # 提取窗口信息
        window_info = batch_df.select("window").first()
        timestamp = int(window_info.window.end.timestamp())

        # 获取热门电影 - 修复：明确指定列并去除歧义
        hot_movies = batch_df.select(
            col("movieId").alias("movie_id"),
            col("title"),
            col("rating_count")
        ).orderBy(col("rating_count").desc()).limit(10).collect()

        # 转换为JSON
        hot_movies_list = []
        for row in hot_movies:
            hot_movies_list.append({
                "movie_id": row.movie_id,
                "title": row.title,
                "rating_count": row.rating_count
            })

        hot_movies_json = json.dumps(hot_movies_list)

        # 保存到HBase
        save_hot_movies_to_hbase(timestamp, hot_movies_json)

        # 打印到控制台
        print(f"Batch {batch_id} - 热门电影 (窗口结束: {window_info.window.end}):")
        for i, movie in enumerate(hot_movies_list, 1):
            print(f"{i}. {movie['title']} - {movie['rating_count']} 条评分")


if __name__ == "__main__":
    # 指定电影数据文件路径
    movies_path = "movies.csv"

    # 处理实时电影评分
    process_streaming_ratings(movies_path)
