package com.movie;

import org.apache.hadoop.hbase.HBaseConfiguration;
import org.apache.hadoop.hbase.client.Admin;
import org.apache.hadoop.hbase.client.Connection;
import org.apache.hadoop.hbase.client.ConnectionFactory;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

@Configuration
@ConfigurationProperties(prefix = "hbase")
public class HBaseConfig {
 
    private Map<String, String> config = new HashMap<>();
 
    public Map<String, String> getConfig() {
        return config;
    }
 
    public void setConfig(Map<String, String> config) {
        this.config = config;
    }
 
    public org.apache.hadoop.conf.Configuration configuration() {
        org.apache.hadoop.conf.Configuration configuration = HBaseConfiguration.create();
        for(Map.Entry<String, String> map : config.entrySet()){
            configuration.set(map.getKey(), map.getValue());
        }
        return configuration;
    }
 
    @Bean
    public Admin admin() {
        Admin admin = null;
        try {
            Connection connection = ConnectionFactory.createConnection(configuration());
            admin = connection.getAdmin();
        } catch (IOException e) {
            e.printStackTrace();
        }
        return admin;
    }
}