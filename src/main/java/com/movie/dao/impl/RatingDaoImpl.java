package com.movie.dao.impl;

import com.movie.HBaseUtils;
import com.movie.constant.HBaseConstants;
import com.movie.dao.RatingDao;
import com.movie.entity.Rating;
import org.apache.hadoop.hbase.filter.CompareFilter;
import org.apache.hadoop.hbase.filter.Filter;
import org.apache.hadoop.hbase.filter.PrefixFilter;
import org.apache.hadoop.hbase.filter.SingleColumnValueFilter;
import org.apache.hadoop.hbase.util.Bytes;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

@Repository
public class RatingDaoImpl implements RatingDao {

    @Autowired
    private HBaseUtils hbaseUtils;

    @Override
    public void createRatingTables() {
        // 创建评分表
        if (!hbaseUtils.isExists(HBaseConstants.RATING_TABLE)) {
            hbaseUtils.createTable(HBaseConstants.RATING_TABLE, Arrays.asList(HBaseConstants.RATING_FAMILY));
        }
        
        // 创建用户评分表
        if (!hbaseUtils.isExists(HBaseConstants.USER_RATING_TABLE)) {
            hbaseUtils.createTable(HBaseConstants.USER_RATING_TABLE, Arrays.asList(HBaseConstants.USER_RATING_FAMILY));
        }
        
        // 创建电影评分表
        if (!hbaseUtils.isExists(HBaseConstants.MOVIE_RATING_TABLE)) {
            hbaseUtils.createTable(HBaseConstants.MOVIE_RATING_TABLE, Arrays.asList(HBaseConstants.MOVIE_RATING_FAMILY));
        }
    }

    @Override
    public void batchImportRatings(List<Rating> ratings) {
        for (Rating rating : ratings) {
            // 向评分表插入数据，rowkey为userId_movieId
            hbaseUtils.putData(
                    HBaseConstants.RATING_TABLE,
                    rating.getUserId() + "_" + rating.getMovieId(),
                    HBaseConstants.RATING_FAMILY,
                    Arrays.asList("userId", "movieId", "rating", "timestamp"),
                    Arrays.asList(rating.getUserId(), rating.getMovieId(), rating.getRating(), rating.getTimestamp())
            );
            
            // 向用户评分表插入数据，按用户组织
            hbaseUtils.putData(
                    HBaseConstants.USER_RATING_TABLE,
                    rating.getUserId(),
                    HBaseConstants.USER_RATING_FAMILY,
                    rating.getMovieId(),
                    rating.getRating()
            );
            
            // 向电影评分表插入数据，按电影组织
            hbaseUtils.putData(
                    HBaseConstants.MOVIE_RATING_TABLE,
                    rating.getMovieId(),
                    HBaseConstants.MOVIE_RATING_FAMILY,
                    rating.getUserId(),
                    rating.getRating()
            );
        }
    }

    @Override
    public List<Rating> getMovieRatings(String movieId) {
        List<Rating> ratings = new ArrayList<>();
        
        // 创建过滤器
        Filter filter = new SingleColumnValueFilter(
                Bytes.toBytes(HBaseConstants.RATING_FAMILY),
                Bytes.toBytes("movieId"),
                CompareFilter.CompareOp.EQUAL,
                Bytes.toBytes(movieId)
        );
        
        List<Map<String, String>> results = hbaseUtils.getData(HBaseConstants.RATING_TABLE, filter);
        for (Map<String, String> data : results) {
            Rating rating = new Rating();
            rating.setUserId(data.get(HBaseConstants.RATING_FAMILY + ":userId"));
            rating.setMovieId(data.get(HBaseConstants.RATING_FAMILY + ":movieId"));
            rating.setRating(data.get(HBaseConstants.RATING_FAMILY + ":rating"));
            rating.setTimestamp(data.get(HBaseConstants.RATING_FAMILY + ":timestamp"));
            ratings.add(rating);
        }
        
        return ratings;
    }

    @Override
    public List<Rating> getUserRatings(String userId) {
        List<Rating> ratings = new ArrayList<>();
        
        // 从用户评分表获取数据
        Map<String, String> userData = hbaseUtils.getData(HBaseConstants.USER_RATING_TABLE, userId);
        if (userData != null && !userData.isEmpty()) {
            for (Map.Entry<String, String> entry : userData.entrySet()) {
                String key = entry.getKey();
                if (key.startsWith(HBaseConstants.USER_RATING_FAMILY + ":")) {
                    String movieId = key.substring((HBaseConstants.USER_RATING_FAMILY + ":").length());
                    String ratingValue = entry.getValue();
                    
                    Rating rating = new Rating();
                    rating.setUserId(userId);
                    rating.setMovieId(movieId);
                    rating.setRating(ratingValue);
                    // 时间戳为空，因为在用户评分表中没有存储
                    rating.setTimestamp("");
                    
                    ratings.add(rating);
                }
            }
        }
        
        return ratings;
    }

    @Override
    public double getMovieAverageRating(String movieId) {
        List<Rating> ratings = getMovieRatings(movieId);
        if (ratings.isEmpty()) {
            return 0.0;
        }
        
        double sum = 0.0;
        for (Rating rating : ratings) {
            sum += Double.parseDouble(rating.getRating());
        }
        
        return sum / ratings.size();
    }
} 