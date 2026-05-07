-- ============================================================
-- schema.sql - News Fetcher + Bookmark System
-- MySQL Database Schema
--
-- Run from MySQL client:
--   mysql -u root -p < schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS news_fetcher
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE news_fetcher;

DROP TABLE IF EXISTS bookmarks;

CREATE TABLE bookmarks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    url VARCHAR(768) NOT NULL UNIQUE,
    category VARCHAR(100) DEFAULT 'General',
    sentiment VARCHAR(20) DEFAULT 'Neutral',
    tag VARCHAR(50) DEFAULT 'None',
    saved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_bookmarks_category (category),
    INDEX idx_bookmarks_title (title(191))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO bookmarks (title, description, url, category, sentiment, tag)
VALUES
    (
        'Python 3.13 Released with Major Performance Gains',
        'The Python Software Foundation announces version 3.13 with a new JIT compiler.',
        'https://python.org/news/3.13',
        'Technology',
        'Positive',
        'Important'
    ),
    (
        'Global Markets Rise on Positive Economic Data',
        'Stock markets surged worldwide after encouraging inflation figures were released.',
        'https://example.com/markets-rise',
        'Business',
        'Positive',
        'Read Later'
    ),
    (
        'Scientists Discover New Species in Amazon Rainforest',
        'Researchers have catalogued over 200 previously unknown species in the Amazon.',
        'https://example.com/amazon-discovery',
        'Science',
        'Positive',
        'None'
    );

SELECT * FROM bookmarks;
