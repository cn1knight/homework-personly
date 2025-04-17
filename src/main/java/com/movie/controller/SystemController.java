package com.movie.controller;

import com.movie.HBaseUtils;
import com.movie.constant.HBaseConstants;
import com.movie.service.MovieService;
import com.movie.service.RatingService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/system")
public class SystemController {

    @Autowired
    private HBaseUtils hbaseUtils;
    
    @Autowired
    private MovieService movieService;
    
    @Autowired
    private RatingService ratingService;
    
    /**
     * 获取系统信息
     */
    @GetMapping("/info")
    public Map<String, Object> getSystemInfo() {
        Map<String, Object> result = new HashMap<>();
        
        // 表是否存在
        boolean movieTableExists = hbaseUtils.isExists(HBaseConstants.MOVIE_TABLE);
        boolean ratingTableExists = hbaseUtils.isExists(HBaseConstants.RATING_TABLE);
        boolean userRatingTableExists = hbaseUtils.isExists(HBaseConstants.USER_RATING_TABLE);
        boolean movieRatingTableExists = hbaseUtils.isExists(HBaseConstants.MOVIE_RATING_TABLE);
        
        // 表数据量统计
        int movieCount = 0;
        int ratingCount = 0;
        
        if (movieTableExists) {
            movieCount = hbaseUtils.getData(HBaseConstants.MOVIE_TABLE).size();
        }
        
        if (ratingTableExists) {
            // 评分数据量可能很大，这里只是返回部分数据的数量
            ratingCount = hbaseUtils.getData(HBaseConstants.RATING_TABLE).size();
        }
        
        // 构建结果
        Map<String, Object> tables = new HashMap<>();
        int finalMovieCount = movieCount;
        tables.put("movie", new HashMap<String, Object>() {{
            put("exists", movieTableExists);
            put("count", finalMovieCount);
        }});
        int finalRatingCount = ratingCount;
        tables.put("rating", new HashMap<String, Object>() {{
            put("exists", ratingTableExists);
            put("count", finalRatingCount);
        }});
        tables.put("user_rating", new HashMap<String, Object>() {{
            put("exists", userRatingTableExists);
        }});
        tables.put("movie_rating", new HashMap<String, Object>() {{
            put("exists", movieRatingTableExists);
        }});
        
        result.put("success", true);
        result.put("tables", tables);
        result.put("hbase_connected", true);
        
        return result;
    }
} 