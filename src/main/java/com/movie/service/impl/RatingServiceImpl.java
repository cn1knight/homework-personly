package com.movie.service.impl;

import com.movie.dao.RatingDao;
import com.movie.entity.Movie;
import com.movie.entity.Rating;
import com.movie.service.MovieService;
import com.movie.service.RatingService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Service;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class RatingServiceImpl implements RatingService {

    @Autowired
    private RatingDao ratingDao;
    
    @Autowired
    private MovieService movieService;

    @Override
    public int importRatingsFromCsv() {
        List<Rating> ratings = new ArrayList<>();
        
        try {
            // 读取CSV文件
            ClassPathResource resource = new ClassPathResource("ratings.csv");
            BufferedReader reader = new BufferedReader(new InputStreamReader(resource.getInputStream()));
            
            // 跳过标题行
            String line = reader.readLine();
            
            // 读取数据行
            int count = 0;
            while ((line = reader.readLine()) != null && count < 100000) { // 限制导入数量，避免内存溢出
                String[] parts = line.split(",");
                if (parts.length >= 4) {
                    String userId = parts[0];
                    String movieId = parts[1];
                    String rating = parts[2];
                    String timestamp = parts[3];
                    
                    Rating ratingObj = new Rating(userId, movieId, rating, timestamp);
                    ratings.add(ratingObj);
                    
                    // 每1000条批量提交一次
                    if (ratings.size() >= 1000) {
                        ratingDao.batchImportRatings(ratings);
                        count += ratings.size();
                        ratings.clear();
                    }
                }
            }
            
            // 提交剩余的数据
            if (!ratings.isEmpty()) {
                ratingDao.batchImportRatings(ratings);
                count += ratings.size();
            }
            
            reader.close();
            return count;
        } catch (IOException e) {
            e.printStackTrace();
            return 0;
        }
    }

    @Override
    public List<Rating> getUserRatings(String userId) {
        return ratingDao.getUserRatings(userId);
    }

    @Override
    public List<Rating> getMovieRatings(String movieId) {
        return ratingDao.getMovieRatings(movieId);
    }

    @Override
    public double getMovieAverageRating(String movieId) {
        return ratingDao.getMovieAverageRating(movieId);
    }

    @Override
    public Map<String, Double> getTopRatedMovies(int n) {
        // 获取所有电影评分
        Map<String, Double> movieRatings = new HashMap<>();
        
        // 通过遍历前N部电影ID来获取评分（实际项目中可能需要更复杂的实现）
        for (int i = 1; i <= 200; i++) {
            String movieId = String.valueOf(i);
            Movie movie = movieService.getMovieById(movieId);
            if (movie != null) {
                double avgRating = getMovieAverageRating(movieId);
                if (avgRating > 0) {
                    movieRatings.put(movieId, avgRating);
                }
            }
        }
        
        // 对评分进行排序并返回前N部电影
        return movieRatings.entrySet().stream()
                .sorted(Map.Entry.<String, Double>comparingByValue().reversed())
                .limit(n)
                .collect(Collectors.toMap(
                        Map.Entry::getKey,
                        Map.Entry::getValue,
                        (e1, e2) -> e1,
                        LinkedHashMap::new
                ));
    }
} 