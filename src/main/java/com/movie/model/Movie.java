package com.movie.model;

public class Movie {
    private String title;
    private Integer year;
    private String genres;
    private Double rating;
    private String coverUrl;
    private String description;

    // 省略getter/setter方法
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public Integer getYear() { return year; }
    public void setYear(Integer year) { this.year = year; }
    public String getGenres() { return genres; }
    public void setGenres(String genres) { this.genres = genres; }
    public Double getRating() { return rating; }
    public void setRating(Double rating) { this.rating = rating; }
    public String getCoverUrl() { return coverUrl; }
    public void setCoverUrl(String coverUrl) { this.coverUrl = coverUrl; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
}