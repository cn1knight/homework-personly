package com.movie.service;

import com.movie.entity.Movie;

import java.util.List;

public interface MovieService {
    /**
     * 初始化表结构
     */
    void initTables();
    
    /**
     * 从CSV文件导入电影数据
     * @return 导入的电影数量
     */
    int importMoviesFromCsv();
    
    /**
     * 根据ID获取电影
     * @param movieId 电影ID
     * @return 电影对象
     */
    Movie getMovieById(String movieId);
    
    /**
     * 根据标题关键词搜索电影
     * @param keyword 关键词
     * @return 电影列表
     */
    List<Movie> searchMoviesByTitle(String keyword);
    
    /**
     * 根据类型搜索电影
     * @param genre 电影类型
     * @return 电影列表
     */
    List<Movie> searchMoviesByGenre(String genre);
} 