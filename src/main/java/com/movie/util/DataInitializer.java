package com.movie.util;

import com.movie.dao.MovieDao;
import com.movie.dao.RatingDao;
import com.movie.service.MovieService;
import com.movie.service.RatingService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

@Component
public class DataInitializer implements CommandLineRunner {
    
    @Autowired
    private MovieDao movieDao;
    
    @Autowired
    private RatingDao ratingDao;
    
    @Autowired
    private MovieService movieService;
    
    @Autowired
    private RatingService ratingService;
    
    @Override
    public void run(String... args) {
        System.out.println("------------ 开始初始化HBase表 -------------");
        
        // 初始化表结构
        movieDao.createMovieTable();
        ratingDao.createRatingTables();
        
        // 检查是否需要导入数据
        if (isTableEmpty()) {
            System.out.println("表为空，开始导入电影数据...");
            long startTime = System.currentTimeMillis();
            
            // 导入电影数据
            int movieCount = movieService.importMoviesFromCsv();
            System.out.println("成功导入" + movieCount + "部电影数据");
            
            // 导入评分数据
            int ratingCount = ratingService.importRatingsFromCsv();
            System.out.println("成功导入" + ratingCount + "条评分数据");
            
            long endTime = System.currentTimeMillis();
            System.out.println("数据导入完成，耗时：" + (endTime - startTime) / 1000 + "秒");
        } else {
            System.out.println("表中已存在数据，跳过数据导入");
        }
        
        System.out.println("------------ HBase表初始化完成 -------------");
    }
    
    /**
     * 判断表是否为空
     */
    private boolean isTableEmpty() {
        // 检查电影表是否为空
        return movieDao.getMovieById("1") == null;
    }
} 