# Release Day Radar

Our Case Study A project. We asked whether online buzz around a film's trailer and release predicts how much it grosses, for 28 Hindi and South Indian films of 2025 and 2026.

In short, trailer views barely track the gross, but trailer likes and Wikipedia views in the opening three days do, and every film whose interest fell to 37% or less in week two was a flop. The full story is in `report/report.pdf`.

## What's in here

```
code/      scripts, numbered in the order you run them
data/      film list, hand-checked trailer list, raw downloads, cleaned files
sql/       MySQL schema, queries and their output
charts/    every chart in the report
report/    report (Markdown, Word and PDF)
slides/    10 slide deck (PowerPoint and PDF)
team_contribution.md
```

## Setup

You need Python 3.10 to 3.13, Java 17 (for PySpark) and MySQL 8. Steps 11 and 15 use Microsoft Excel and Apple Pages on macOS.

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On a Mac, Java and MySQL come from Homebrew:

```
brew install openjdk@17 mysql
brew services start mysql
```

Steps 2 and 3 need a free YouTube Data API v3 key (Google Cloud Console, APIs and Services, enable "YouTube Data API v3", create an API key). Put it in a file called `.env` in this folder:

```
YOUTUBE_API_KEY=your_key_here
```

`.env` is in `.gitignore`, so the key never goes to GitHub.

## Run it

Run everything from this folder, one step at a time.

```
python code/01_get_wikipedia.py      # film pages and box-office tables, about 3 min
python code/02_find_trailers.py      # trailer search, uses 2,800 of the 10,000 daily YouTube units
python code/03_get_youtube.py        # trailer stats and top comments, about 1 min
python code/04_get_pageviews.py      # daily Wikipedia views, about 20 min (Wikipedia asks us to go slowly)
python code/05_get_imdb.py           # IMDb 50K reviews, 84 MB download
python code/06_spark_text.py         # PySpark text job
python code/07_clean.py              # type casting, name matching, gaps
python code/08_sentiment.py          # VADER, tested on IMDb first
python code/09_metrics.py            # one row per film
python code/10_analysis.py           # findings and charts
python code/11_pivot_check.py        # same cleaning step in Excel and pandas
python code/12_load_mysql.py         # load MySQL and run the queries
python code/13_diagrams.py           # ER diagram and pipeline picture
python code/14_make_slides.py        # slide deck
python code/15_build_report.py       # report to Word and PDF
```

Steps 1 to 5 download the raw data. If you already have `data/raw/`, you can skip them. Every download script skips files it already has, so it is safe to rerun one that stopped halfway.

`data/trailers.csv` is the trailer list we checked by hand. Step 2 shows what the search rule picks; we replaced 7 of its picks (dubbed versions, a Netflix trailer and a fan video), and the reason for each is in that file.

## MySQL

The loader logs in as user `student` with password `student` on localhost. Make that user once with this command.

```
mysql -u root -e "CREATE USER 'student'@'localhost' IDENTIFIED BY 'student'; GRANT ALL ON release_radar.* TO 'student'@'localhost';"
```

Or use your own login like this.

```
MYSQL_USER=me MYSQL_PASSWORD=secret python code/12_load_mysql.py
```

## Data

* Film pages and box-office tables from Wikipedia, https://en.wikipedia.org/w/api.php
* Trailer statistics and comments from the YouTube Data API v3 (no usernames are downloaded)
* Daily page views from the Wikimedia Pageviews API, https://wikimedia.org/api/rest_v1/metrics/pageviews/
* IMDb Large Movie Review Dataset (Maas et al., 2011), https://ai.stanford.edu/~amaas/data/sentiment/

Three files are over 50 MB and are not in the repo: the IMDb archive and its table (`data/raw/imdb/`, `data/raw/imdb_reviews.csv`, rebuilt by step 5) and the clean text table (`data/clean/text_clean.parquet/`, rebuilt by step 6). Everything else, raw and clean, is in `data/`.

GitHub repo : https://github.com/Pratyush038/Case-Study-A-Release-Day-Radar
