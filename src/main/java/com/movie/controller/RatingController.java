package com.movie.controller;

import com.movie.entity.Movie;
import com.movie.entity.Rating;
import com.movie.service.MovieService;
import com.movie.service.RatingService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/rating")
public class RatingController {

    @Autowired
    private RatingService ratingService;
    
    @Autowired
    private MovieService movieService;
    
    /**
     * 获取用户的评分记录
     */
    @GetMapping("/user/{userId}")
    public Map<String, Object> getUserRatings(@PathVariable String userId) {
        Map<String, Object> result = new HashMap<>();
        
        List<Rating> ratings = ratingService.getUserRatings(userId);
        List<Map<String, Object>> ratingsWithMovieInfo = new ArrayList<>();
        
        for (Rating rating : ratings) {
            Map<String, Object> ratingInfo = new HashMap<>();
            ratingInfo.put("rating", rating);
            
            // 获取电影信息
            Movie movie = movieService.getMovieById(rating.getMovieId());
            if (movie != null) {
                ratingInfo.put("movie", movie);
            }
            
            ratingsWithMovieInfo.add(ratingInfo);
        }
        
        result.put("success", true);
        result.put("data", ratingsWithMovieInfo);
        result.put("total", ratings.size());
        
        return result;
    }
    
    /**
     * 获取电影的评分记录
     */
    @GetMapping("/movie/{movieId}")
    public Map<String, Object> getMovieRatings(@PathVariable String movieId) {
        Map<String, Object> result = new HashMap<>();
        
        List<Rating> ratings = ratingService.getMovieRatings(movieId);
        result.put("success", true);
        result.put("data", ratings);
        result.put("total", ratings.size());
        result.put("averageRating", ratingService.getMovieAverageRating(movieId));
        
        return result;
    }
}