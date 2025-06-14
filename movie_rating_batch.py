from pyspark.sql import SparkSession
from pyspark.sql.functions import avg, count, col, round
import happybase
import os
import time

# HBase配置
HBASE_HOST = '127.0.0.1'
HBASE_PORT = 19090
MOVIE_RATINGS_TABLE = 'movie_avg_ratings'
COLUMN_FAMILY = 'info'
BATCH_SIZE = 1000  # 批量处理大小
THREAD_POOL_SIZE = 10  # 线程池大小

# 使用count 去hbase中去查数量  count  'movie_avg_ratings'


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


def save_batch_to_hbase(batch_data):
    """批量保存电影评分到HBase"""
    try:
        connection = happybase.Connection(host=HBASE_HOST, port=HBASE_PORT)
        connection.open()

        table = connection.table(MOVIE_RATINGS_TABLE)
        batch = table.batch(batch_size=BATCH_SIZE)

        current_time = str(int(time.time()))

        for row in batch_data:
            row_key = f"movie_{row.movieId}".encode()

            batch.put(row_key, {
                f'{COLUMN_FAMILY}:movie_id'.encode(): str(row.movieId).encode(),
                f'{COLUMN_FAMILY}:title'.encode(): str(row.title).encode(),
                f'{COLUMN_FAMILY}:avg_rating'.encode(): str(row.avg_rating).encode(),
                f'{COLUMN_FAMILY}:rating_count'.encode(): str(row.rating_count).encode(),
                f'{COLUMN_FAMILY}:last_updated'.encode(): current_time.encode()
            })

        batch.send()
        print(f"成功批量保存 {len(batch_data)} 条记录到HBase")
    except Exception as e:
        print(f"批量保存到HBase时出错: {str(e)}")
        raise
    finally:
        if connection:
            connection.close()


def process_movie_ratings(ratings_path, movies_path):
    """处理电影评分数据"""
    # 创建SparkSession
    spark = SparkSession.builder \
        .appName("MovieRatingBatch") \
        .config("spark.sql.shuffle.partitions", "200") \
        .config("spark.executor.memory", "4g") \
        .getOrCreate()

    try:
        # 读取评分数据
        ratings_df = spark.read.csv(ratings_path, header=True, inferSchema=True)

        # 读取电影数据
        movies_df = spark.read.csv(movies_path, header=True, inferSchema=True)

        # 缓存电影数据，因为它会被多次使用
        movies_df.cache()

        # 计算每部电影的平均评分和评分次数
        avg_ratings = ratings_df.groupBy("movieId") \
            .agg(
            round(avg("rating"), 2).alias("avg_rating"),
            count("rating").alias("rating_count")
        )

        # 与电影数据关联
        movie_ratings = avg_ratings.join(movies_df, "movieId")

        # 简化处理逻辑，避免复杂的分区操作
        movie_ratings_list = movie_ratings.collect()
        
        # 分批处理数据
        batch_data = []
        for row in movie_ratings_list:
            batch_data.append(row)
            if len(batch_data) >= BATCH_SIZE:
                save_batch_to_hbase(batch_data)
                batch_data = []
        
        # 处理剩余数据
        if batch_data:
            save_batch_to_hbase(batch_data)

        print(f"批处理完成: 处理了 {len(movie_ratings_list)} 部电影的评分数据")

    finally:
        spark.stop()


if __name__ == "__main__":
    # 指定数据文件路径
    # 优先使用ratings2.csv，如果不存在则使用ratings.csv
    ratings_path = "ratings2.csv" if os.path.exists("ratings2.csv") else "ratings.csv"
    movies_path = "movies.csv"
    
    print(f"使用评分数据文件: {ratings_path}")
    
    start_time = time.time()
    # 处理电影评分
    process_movie_ratings(ratings_path, movies_path)
    end_time = time.time()

    print(f"总执行时间: {end_time - start_time:.2f}秒")
