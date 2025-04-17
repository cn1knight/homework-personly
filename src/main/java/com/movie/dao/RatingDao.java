package com.movie.dao;

import com.movie.entity.Rating;

import java.util.List;
import java.util.Map;

public interface RatingDao {
    /**
     * 创建评分相关表
     */
    void createRatingTables();
    
    /**
     * 批量导入评分数据
     * @param ratings 评分列表
     */
    void batchImportRatings(List<Rating> ratings);
    
    /**
     * 获取某部电影的所有评分
     * @param movieId 电影ID
     * @return 评分列表
     */
    List<Rating> getMovieRatings(String movieId);
    
    /**
     * 获取某用户的所有评分
     * @param userId 用户ID
     * @return 评分列表
     */
    List<Rating> getUserRatings(String userId);
    
    /**
     * 获取电影的平均评分
     * @param movieId 电影ID
     * @return 平均评分
     */
    double getMovieAverageRating(String movieId);
} 