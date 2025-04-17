package com.movie.service.impl;

import com.movie.dao.MovieDao;
import com.movie.entity.Movie;
import com.movie.service.MovieService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Service;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.List;

@Service
public class MovieServiceImpl implements MovieService {

    @Autowired
    private MovieDao movieDao;

    @Override
    public void initTables() {
        movieDao.createMovieTable();
    }

    @Override
    public int importMoviesFromCsv() {
        List<Movie> movies = new ArrayList<>();
        
        try {
            // 读取CSV文件
            ClassPathResource resource = new ClassPathResource("movies.csv");
            BufferedReader reader = new BufferedReader(new InputStreamReader(resource.getInputStream()));
            
            // 跳过标题行
            String line = reader.readLine();
            
            // 读取数据行
            while ((line = reader.readLine()) != null) {
                String[] parts = line.split(",(?=([^\"]*\"[^\"]*\")*[^\"]*$)");
                if (parts.length >= 3) {
                    String movieId = parts[0];
                    String title = parts[1];
                    String genres = parts[2];
                    
                    Movie movie = new Movie(movieId, title, genres);
                    movies.add(movie);
                }
            }
            
            reader.close();
            
            // 批量导入到HBase
            movieDao.batchImportMovies(movies);
            
            return movies.size();
        } catch (IOException e) {
            e.printStackTrace();
            return 0;
        }
    }

    @Override
    public Movie getMovieById(String movieId) {
        return movieDao.getMovieById(movieId);
    }

    @Override
    public List<Movie> searchMoviesByTitle(String keyword) {
        return movieDao.searchMoviesByTitle(keyword);
    }

    @Override
    public List<Movie> searchMoviesByGenre(String genre) {
        return movieDao.searchMoviesByGenre(genre);
    }
} 