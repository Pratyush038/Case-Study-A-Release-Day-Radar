USE release_radar;

-- Q1. How big is each table?
SELECT 'films' AS tbl, COUNT(*) AS n FROM films
UNION ALL SELECT 'trailers', COUNT(*) FROM trailers
UNION ALL SELECT 'pageviews_daily', COUNT(*) FROM pageviews_daily
UNION ALL SELECT 'youtube_comments', COUNT(*) FROM youtube_comments;

-- Q2. (JOIN) Trailer views and likes next to the box office, biggest gross first
SELECT f.wiki_title, f.language, ROUND(t.views / 1e6, 1) AS trailer_views_m,
       ROUND(t.likes / 1e3, 0) AS trailer_likes_k, ROUND(f.gross_cr, 0) AS gross_cr
FROM films f
JOIN trailers t ON t.film_id = f.film_id
ORDER BY f.gross_cr DESC;

-- Q3. (JOIN + GROUP BY) Hindi vs South Indian films: rupees of gross per trailer view
SELECT f.language_group, COUNT(*) AS films,
       ROUND(AVG(f.gross_cr), 0) AS avg_gross_cr,
       ROUND(AVG(t.views) / 1e6, 1) AS avg_trailer_views_m,
       ROUND(SUM(f.gross_cr) * 1e7 / SUM(t.views), 1) AS rupees_gross_per_trailer_view
FROM films f JOIN trailers t ON t.film_id = f.film_id
GROUP BY f.language_group;

-- Q4. (3-table JOIN + GROUP BY) Opening 3 days on Wikipedia vs trailer views vs gross
SELECT f.wiki_title, SUM(p.views) AS opening_3day_pageviews,
       ROUND(t.views / 1e6, 1) AS trailer_views_m, ROUND(f.gross_cr, 0) AS gross_cr
FROM films f
JOIN pageviews_daily p ON p.film_id = f.film_id AND p.day_from_release BETWEEN 0 AND 2
JOIN trailers t ON t.film_id = f.film_id
GROUP BY f.film_id, f.wiki_title, t.views, f.gross_cr
ORDER BY opening_3day_pageviews DESC;

-- Q5. (3-table JOIN + GROUP BY) Mean comment sentiment per film, before and after release
SELECT f.wiki_title,
       ROUND(AVG(CASE WHEN c.published_ist <  f.release_date THEN c.compound END), 3) AS before_release,
       ROUND(AVG(CASE WHEN c.published_ist >= f.release_date THEN c.compound END), 3) AS after_release,
       COUNT(c.compound) AS scored_comments
FROM youtube_comments c
JOIN trailers t ON t.video_id = c.video_id
JOIN films f ON f.film_id = t.film_id
GROUP BY f.film_id, f.wiki_title
ORDER BY after_release DESC;

-- Q6. (GROUP BY) Which part of a film do comments talk about, and how warmly?
SELECT 'music' AS aspect, COUNT(*) AS comments, ROUND(AVG(compound), 3) AS mean_sentiment FROM youtube_comments WHERE about_music AND compound IS NOT NULL
UNION ALL SELECT 'story', COUNT(*), ROUND(AVG(compound), 3) FROM youtube_comments WHERE about_story AND compound IS NOT NULL
UNION ALL SELECT 'acting', COUNT(*), ROUND(AVG(compound), 3) FROM youtube_comments WHERE about_acting AND compound IS NOT NULL
UNION ALL SELECT 'vfx', COUNT(*), ROUND(AVG(compound), 3) FROM youtube_comments WHERE about_vfx AND compound IS NOT NULL
UNION ALL SELECT 'action', COUNT(*), ROUND(AVG(compound), 3) FROM youtube_comments WHERE about_action AND compound IS NOT NULL
UNION ALL SELECT 'length', COUNT(*), ROUND(AVG(compound), 3) FROM youtube_comments WHERE about_length AND compound IS NOT NULL;

-- Q7. (GROUP BY with CASE) Hits and flops by gross-to-budget ratio
SELECT CASE WHEN budget_cr IS NULL THEN 'budget unknown'
            WHEN gross_cr / budget_cr >= 2 THEN 'hit (2x budget or more)'
            WHEN gross_cr / budget_cr >= 1 THEN 'average (1x to 2x)'
            ELSE 'flop (below budget)' END AS verdict,
       COUNT(*) AS films, GROUP_CONCAT(wiki_title ORDER BY gross_cr DESC SEPARATOR ', ') AS which_films
FROM films
GROUP BY verdict;
