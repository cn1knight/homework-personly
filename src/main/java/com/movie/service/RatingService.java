package com.movie.service;

import com.movie.entity.Rating;

import java.util.List;
import java.util.Map;

public interface RatingService {
    /**
     * 从CSV文件导入评分数据
     * @return 导入的评分数量
     */
    int importRatingsFromCsv();
    
    /**
     * 获取用户的所有评分
     * @param userId 用户ID
     * @return 评分列表
     */
    List<Rating> getUserRatings(String userId);
    
    /**
     * 获取电影的所有评分
     * @param movieId 电影ID
     * @return 评分列表
     */
    List<Rating> getMovieRatings(String movieId);
    
    /**
     * 获取电影的平均评分
     * @param movieId 电影ID
     * @return 平均评分
     */
    double getMovieAverageRating(String movieId);
    
    /**
     * 获取评分最高的N部电影
     * @param n 数量
     * @return 电影评分映射，key为movieId，value为平均评分
     */
    Map<String, Double> getTopRatedMovies(int n);
} 