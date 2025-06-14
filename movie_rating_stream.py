# movie_rating_stream.py
import os

# -*- coding: utf-8 -*-
import os

# 创建必要的目录
os.makedirs('C:\\tmp\\spark-warehouse', exist_ok=True)
os.makedirs('C:\\tmp\\spark-checkpoint', exist_ok=True)

print("正在启动流处理脚本...")

from pyspark.sql import SparkSession
from pyspark.sql.functions import window, count, col, desc, from_json, to_timestamp, avg
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


def create_spark_session():
    """创建Spark会话"""
    try:
        print("正在创建Spark会话...")
        spark = SparkSession.builder \
            .appName("MovieRatingStream") \
            .config("spark.sql.warehouse.dir", "file:///C:/tmp/spark-warehouse") \
            .config("spark.hadoop.io.native.lib.available", "false") \
            .config("spark.sql.execution.arrow.pyspark.enabled", "false") \
            .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
            .getOrCreate()
        
        print(f"Spark会话创建成功，版本: {spark.version}")
        return spark
    except Exception as e:
        print(f"创建Spark会话时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


def process_streaming_ratings(movies_path):
    """处理实时电影评分流 - 简化版本"""
    print("开始处理电影评分数据...")
    
    # 创建SparkSession
    spark = create_spark_session()

    try:
        # 读取电影数据
        print("读取电影数据...")
        movies_df = spark.read.csv(movies_path, header=True, inferSchema=True)
        print(f"电影数据加载完成，共 {movies_df.count()} 部电影")
        
        # 读取评分数据
        print("读取评分数据...")
        ratings_df = spark.read.csv("ratings.csv", header=True, inferSchema=True)
        print(f"评分数据加载完成，共 {ratings_df.count()} 条评分")
        
        # 计算热门电影（按评分数量排序）
        print("计算热门电影...")
        hot_movies = ratings_df \
            .groupBy("movieId") \
            .agg(
                count("*").alias("rating_count"),
                avg("rating").alias("avg_rating")
            ) \
            .orderBy(col("rating_count").desc()) \
            .limit(10)
        
        # 与电影数据关联获取标题
        hot_movies_with_titles = hot_movies.join(
            movies_df,
            hot_movies.movieId == movies_df.movieId
        ).select(
            col("movieId").alias("movie_id"),
            col("title"),
            col("genres"),
            col("rating_count"),
            col("avg_rating")
        )
        
        print("热门电影计算完成:")
        hot_movies_with_titles.show(truncate=False)
        
        # 转换为JSON格式并保存到HBase
        hot_movies_list = []
        for row in hot_movies_with_titles.collect():
            hot_movies_list.append({
                "movie_id": int(row.movie_id),
                "title": row.title,
                "rating_count": int(row.rating_count),
                "genres": row.genres if row.genres else '',
                "avg_rating": round(float(row.avg_rating), 2)
            })
        
        hot_movies_json = json.dumps(hot_movies_list)
        timestamp = int(time.time())
        
        # 保存到HBase
        print("保存热门电影数据到HBase...")
        save_hot_movies_to_hbase(timestamp, hot_movies_json)
        
        print(f"流处理完成！生成了 {len(hot_movies_list)} 部热门电影数据")
        for i, movie in enumerate(hot_movies_list, 1):
            print(f"{i}. {movie['title']} - {movie['rating_count']} 条评分 (平均: {movie['avg_rating']})")
            
    except Exception as e:
        print(f"流处理过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        spark.stop()
        print("Spark会话已关闭")


# 删除了save_hot_movies_batch函数，因为已简化为直接处理


if __name__ == "__main__":
    # 指定电影数据文件路径
    movies_path = "movies.csv"

    # 处理实时电影评分
    process_streaming_ratings(movies_path)
