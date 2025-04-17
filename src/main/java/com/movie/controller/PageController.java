package com.movie.controller;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

/**
 * 页面控制器
 */
@Controller
public class PageController {
    
    /**
     * 首页
     */
    @GetMapping("/")
    public String index() {
        return "index";
    }
    
    /**
     * 电影详情页
     */
    @GetMapping("/movie")
    public String movieDetail() {
        return "movie";
    }
    
    /**
     * 用户评分页
     */
    @GetMapping("/user-ratings")
    public String userRatings() {
        return "user-ratings";
    }
} 