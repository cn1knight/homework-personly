package com.movie.dao.impl;

import com.movie.HBaseUtils;
import com.movie.constant.HBaseConstants;
import com.movie.dao.MovieDao;
import com.movie.entity.Movie;
import org.apache.hadoop.hbase.client.Scan;
import org.apache.hadoop.hbase.filter.*;
import org.apache.hadoop.hbase.util.Bytes;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

@Repository
public class MovieDaoImpl implements MovieDao {

    @Autowired
    private HBaseUtils hbaseUtils;

    @Override
    public void createMovieTable() {
        if (!hbaseUtils.isExists(HBaseConstants.MOVIE_TABLE)) {
            hbaseUtils.createTable(HBaseConstants.MOVIE_TABLE, Arrays.asList(HBaseConstants.MOVIE_FAMILY));
        }
    }

    @Override
    public void batchImportMovies(List<Movie> movies) {
        for (Movie movie : movies) {
            hbaseUtils.putData(
                    HBaseConstants.MOVIE_TABLE,
                    movie.getMovieId(),
                    HBaseConstants.MOVIE_FAMILY,
                    Arrays.asList("title", "genres"),
                    Arrays.asList(movie.getTitle(), movie.getGenres())
            );
        }
    }

    @Override
    public Movie getMovieById(String movieId) {
        Map<String, String> data = hbaseUtils.getData(HBaseConstants.MOVIE_TABLE, movieId);
        if (data != null && !data.isEmpty()) {
            Movie movie = new Movie();
            movie.setMovieId(movieId);
            movie.setTitle(data.get(HBaseConstants.MOVIE_FAMILY + ":title"));
            movie.setGenres(data.get(HBaseConstants.MOVIE_FAMILY + ":genres"));
            return movie;
        }
        return null;
    }

    @Override
    public List<Movie> searchMoviesByTitle(String keyword) {
        List<Movie> movies = new ArrayList<>();
        
        // 创建过滤器
        Filter filter = new SingleColumnValueFilter(
                Bytes.toBytes(HBaseConstants.MOVIE_FAMILY),
                Bytes.toBytes("title"),
                CompareFilter.CompareOp.EQUAL,
                new SubstringComparator(keyword)
        );

        List<Map<String, String>> results = hbaseUtils.getData(HBaseConstants.MOVIE_TABLE, filter);
        for (Map<String, String> data : results) {
            Movie movie = new Movie();
            movie.setMovieId(data.get("row"));
            movie.setTitle(data.get(HBaseConstants.MOVIE_FAMILY + ":title"));
            movie.setGenres(data.get(HBaseConstants.MOVIE_FAMILY + ":genres"));
            movies.add(movie);
        }
        
        return movies;
    }

    @Override
    public List<Movie> searchMoviesByGenre(String genre) {
        List<Movie> movies = new ArrayList<>();
        
        // 创建过滤器
        Filter filter = new SingleColumnValueFilter(
                Bytes.toBytes(HBaseConstants.MOVIE_FAMILY),
                Bytes.toBytes("genres"),
                CompareFilter.CompareOp.EQUAL,
                new SubstringComparator(genre)
        );

        List<Map<String, String>> results = hbaseUtils.getData(HBaseConstants.MOVIE_TABLE, filter);
        for (Map<String, String> data : results) {
            Movie movie = new Movie();
            movie.setMovieId(data.get("row"));
            movie.setTitle(data.get(HBaseConstants.MOVIE_FAMILY + ":title"));
            movie.setGenres(data.get(HBaseConstants.MOVIE_FAMILY + ":genres"));
            movies.add(movie);
        }
        
        return movies;
    }
} 