# Step 12: load the clean tables into MySQL and run the queries in sql/queries.sql.
# Set your login first if it is not student/student, for example:
#   MYSQL_USER=me MYSQL_PASSWORD=secret python code/12_load_mysql.py

import os
import pandas as pd
from sqlalchemy import create_engine, text

user = os.getenv("MYSQL_USER", "student")
pwd = os.getenv("MYSQL_PASSWORD", "student")
host = os.getenv("MYSQL_HOST", "localhost") + ":" + os.getenv("MYSQL_PORT", "3306")
server = create_engine(f"mysql+pymysql://{user}:{pwd}@{host}?charset=utf8mb4")

# 1. create the database and tables
with server.begin() as con:
    for stmt in open("sql/schema.sql").read().split(";"):
        if stmt.strip():
            con.execute(text(stmt))
db = create_engine(f"mysql+pymysql://{user}:{pwd}@{host}/release_radar?charset=utf8mb4")

films = pd.read_csv("data/clean/films_clean.csv", parse_dates=["release_date"])
films = films[["film_id", "wiki_title", "language", "language_group", "release_date", "runtime_min",
               "budget_cr", "gross_cr", "gross_low_cr", "gross_high_cr", "gross_is_estimate", "holdout"]]

trailers = pd.read_csv("data/clean/trailers_clean.csv", parse_dates=["published_ist"])
trailers = trailers.rename(columns={"comments": "comment_count"})[
    ["video_id", "film_id", "channel", "published_ist", "duration_s", "views", "likes", "comment_count",
     "days_trailer_to_release"]]

pv = pd.read_csv("data/clean/pageviews_clean.csv", parse_dates=["date"])
pv = pv[["film_id", "date", "views", "day_from_trailer", "day_from_release"]]

c = pd.read_parquet("data/clean/comments_scored.parquet")
yt = c[c.source == "youtube"].merge(trailers[["film_id", "video_id"]], on="film_id")
yt = yt.rename(columns={"doc_id": "comment_id"})[
    ["comment_id", "video_id", "published_ist", "text_clean", "n_words", "script", "compound",
     "about_music", "about_story", "about_acting", "about_vfx", "about_action", "about_length"]]

tables = [("films", films), ("trailers", trailers), ("pageviews_daily", pv), ("youtube_comments", yt)]
for name, df in tables:
    df.to_sql(name, db, if_exists="append", index=False, chunksize=5000)
    print(f"loaded {name}: {len(df):,} rows", flush=True)

# 2. run every query and save the output
out = []
with db.connect() as con:
    for q in open("sql/queries.sql").read().split(";"):
        q = q.strip()
        if q and not q.startswith("USE"):
            res = pd.read_sql(text(q), con)
            out.append(q + "\n\n" + res.to_string(index=False) + "\n")
open("sql/query_results.txt", "w").write("\n" + ("\n" + "-" * 60 + "\n").join(out))
print("query results saved to sql/query_results.txt")
