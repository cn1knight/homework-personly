package com.movie.controller;

import com.movie.entity.Movie;
import com.movie.service.MovieService;
import com.movie.service.RatingService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/movie")
public class MovieController {

    @Autowired
    private MovieService movieService;
    
    @Autowired
    private RatingService ratingService;
    
    /**
     * 根据ID获取电影详情
     */
    @GetMapping("/{movieId}")
    public Map<String, Object> getMovieDetail(@PathVariable String movieId) {
        Map<String, Object> result = new HashMap<>();
        
        Movie movie = movieService.getMovieById(movieId);
        if (movie != null) {
            result.put("success", true);
            result.put("data", movie);
            result.put("averageRating", ratingService.getMovieAverageRating(movieId));
        } else {
            result.put("success", false);
            result.put("message", "电影不存在");
        }
        
        return result;
    }
    
    /**
     * 按标题关键词搜索电影
     */
    @GetMapping("/search/title")
    public Map<String, Object> searchByTitle(@RequestParam String keyword) {
        Map<String, Object> result = new HashMap<>();
        
        List<Movie> movies = movieService.searchMoviesByTitle(keyword);
        result.put("success", true);
        result.put("data", movies);
        result.put("total", movies.size());
        
        return result;
    }
    
    /**
     * 按类型搜索电影
     */
    @GetMapping("/search/genre")
    public Map<String, Object> searchByGenre(@RequestParam String genre) {
        Map<String, Object> result = new HashMap<>();
        
        List<Movie> movies = movieService.searchMoviesByGenre(genre);
        result.put("success", true);
        result.put("data", movies);
        result.put("total", movies.size());
        
        return result;
    }
    
    /**
     * 获取评分最高的电影
     */
    @GetMapping("/top-rated")
    public Map<String, Object> getTopRatedMovies(@RequestParam(defaultValue = "10") int count) {
        Map<String, Object> result = new HashMap<>();
        
        Map<String, Double> topRatedMovies = ratingService.getTopRatedMovies(count);
        Map<String, Object> moviesWithDetails = new HashMap<>();
        
        for (Map.Entry<String, Double> entry : topRatedMovies.entrySet()) {
            String movieId = entry.getKey();
            Double rating = entry.getValue();
            
            Movie movie = movieService.getMovieById(movieId);
            if (movie != null) {
                Map<String, Object> movieDetail = new HashMap<>();
                movieDetail.put("movie", movie);
                movieDetail.put("rating", rating);
                
                moviesWithDetails.put(movieId, movieDetail);
            }
        }
        
        result.put("success", true);
        result.put("data", moviesWithDetails);
        
        return result;
    }
} 