package com.movie.constant;

/**
 * HBase表常量
 */
public class HBaseConstants {
    // 电影表
    public static final String MOVIE_TABLE = "movie";
    public static final String MOVIE_FAMILY = "info";
    
    // 评分表
    public static final String RATING_TABLE = "rating";
    public static final String RATING_FAMILY = "info";
    
    // 用户评分表（按用户ID组织）
    public static final String USER_RATING_TABLE = "user_rating";
    public static final String USER_RATING_FAMILY = "movies";
    
    // 电影评分表（按电影ID组织）
    public static final String MOVIE_RATING_TABLE = "movie_rating";
    public static final String MOVIE_RATING_FAMILY = "users";
} 