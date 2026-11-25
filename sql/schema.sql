-- MySQL schema for Release Day Radar
-- 4 tables linked by keys. See charts/er_diagram.png

DROP DATABASE IF EXISTS release_radar;
CREATE DATABASE release_radar CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE release_radar;

-- one row per film (Wikipedia infobox, cleaned)
CREATE TABLE films (
    film_id           VARCHAR(20) PRIMARY KEY,
    wiki_title        VARCHAR(80) NOT NULL,
    language          VARCHAR(20),
    language_group    VARCHAR(20),
    release_date      DATE NOT NULL,
    runtime_min       INT,
    budget_cr         DOUBLE,
    gross_cr          DOUBLE,
    gross_low_cr      DOUBLE,
    gross_high_cr     DOUBLE,
    gross_is_estimate BOOLEAN,
    holdout           BOOLEAN
);

-- one row per trailer (YouTube Data API, JSON flattened)
CREATE TABLE trailers (
    video_id                VARCHAR(11) PRIMARY KEY,
    film_id                 VARCHAR(20) NOT NULL UNIQUE,
    channel                 VARCHAR(60),
    published_ist           DATETIME,
    duration_s              INT,
    views                   BIGINT,
    likes                   BIGINT,
    comment_count           INT,
    days_trailer_to_release INT,
    FOREIGN KEY (film_id) REFERENCES films(film_id)
);

-- one row per film per day (Wikimedia pageviews API, JSON)
CREATE TABLE pageviews_daily (
    film_id          VARCHAR(20),
    date             DATE,
    views            INT,
    day_from_trailer INT,
    day_from_release INT,
    PRIMARY KEY (film_id, date),
    FOREIGN KEY (film_id) REFERENCES films(film_id)
);

-- one row per YouTube trailer comment (free text, no usernames), times in IST
CREATE TABLE youtube_comments (
    comment_id     VARCHAR(30) PRIMARY KEY,
    video_id       VARCHAR(11) NOT NULL,
    published_ist  DATETIME,
    text_clean     TEXT,
    n_words        INT,
    script         VARCHAR(30),
    compound       DOUBLE,
    about_music    BOOLEAN,
    about_story    BOOLEAN,
    about_acting   BOOLEAN,
    about_vfx      BOOLEAN,
    about_action   BOOLEAN,
    about_length   BOOLEAN,
    FOREIGN KEY (video_id) REFERENCES trailers(video_id)
);
