package com.movie.controller;

import com.movie.model.Movie;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;

@Controller
public class MovieViewController {

    @GetMapping("/movie/detail/{id}")
    public String showMovieDetail(@PathVariable String id, Model model) {
        Movie movie = new Movie();
        movie.setTitle("肖申克的救赎");
        movie.setYear(1994);
        movie.setGenres("剧情/犯罪");
        movie.setRating(9.7);
        movie.setCoverUrl("/images/shawshank.jpg");
        movie.setDescription("希望让人自由...");

        model.addAttribute("movie", movie);
        return "detail";
    }
}