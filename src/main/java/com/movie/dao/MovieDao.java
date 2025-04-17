package com.movie.dao;

import com.movie.entity.Movie;

import java.util.List;
import java.util.Map;

public interface MovieDao {
    /**
     * 创建电影表
     */
    void createMovieTable();
    
    /**
     * 批量导入电影数据
     * @param movies 电影列表
     */
    void batchImportMovies(List<Movie> movies);
    
    /**
     * 根据电影ID查询电影信息
     * @param movieId 电影ID
     * @return 电影信息
     */
    Movie getMovieById(String movieId);
    
    /**
     * 根据电影标题关键词查询电影
     * @param keyword 关键词
     * @return 电影列表
     */
    List<Movie> searchMoviesByTitle(String keyword);
    
    /**
     * 根据电影类型查询电影
     * @param genre 电影类型
     * @return 电影列表
     */
    List<Movie> searchMoviesByGenre(String genre);
} 