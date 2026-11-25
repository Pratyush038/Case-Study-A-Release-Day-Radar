# Step 4: daily Wikipedia pageviews for each film (Wikimedia JSON API).
# Window: 14 days before the trailer to 28 days after release.
#
# The API counts views per page TITLE, and film pages get renamed (Saiyaara was
# "Saiyaara" on release day and is "Saiyaara (film)" now). So we read each page's
# old titles from its "moved page [[A]] to [[B]]" edit comments and add up the
# views of every title the page has had.

import os
import re
import json
import time
import urllib.parse
import requests
import pandas as pd

UA = {"User-Agent": "ReleaseDayRadar/1.0 (student data project)"}
WIKI = "https://en.wikipedia.org/w/api.php"
PV = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/"
OUT = "data/raw/pageviews"
os.makedirs(OUT, exist_ok=True)

info = pd.read_csv("data/raw/wiki_infobox.csv")
trailers = pd.read_csv("data/raw/trailer_stats.csv")
films = info.merge(trailers[["film_id", "published_utc"]], on="film_id")
films["release"] = pd.to_datetime(films.release_text.str.extract(r"\((\d{4}-\d{2}-\d{2})\)")[0])
films["trailer_day"] = (pd.to_datetime(films.published_utc).dt.tz_convert("Asia/Kolkata")
                        .dt.tz_localize(None).dt.normalize())


def get_json(url, params=None):
    """GET with retries; Wikipedia answers 429 (slow down) when busy."""
    for attempt in range(6):
        r = requests.get(url, params=params, headers=UA, timeout=120)
        if r.status_code == 404:
            return {}
        if r.status_code == 200 and r.text.startswith("{"):
            return r.json()
        time.sleep(5 * (attempt + 1))
    raise RuntimeError("failed: " + url)


def old_titles(title):
    """Every title this page has had, from 'moved page' comments in its edit history."""
    titles, params = {title}, {"action": "query", "prop": "revisions", "titles": title,
                               "rvprop": "comment", "rvlimit": "max", "format": "json"}
    while True:
        j = get_json(WIKI, params)
        for rev in next(iter(j["query"]["pages"].values())).get("revisions", []):
            m = re.search(r"moved page \[\[(.+?)\]\] to \[\[(.+?)\]\]", rev.get("comment", ""))
            if m:
                titles |= {m.group(1), m.group(2)}
        if "continue" not in j:
            return titles
        params.update(j["continue"])


for f in films.itertuples():
    path = f"{OUT}/{f.film_id}.json"
    if os.path.exists(path):                  # skip films we already have
        continue
    start = f.trailer_day - pd.Timedelta(days=14)
    end = f.release + pd.Timedelta(days=28)
    views = {}
    for t in old_titles(f.wiki_title):
        url = PV + urllib.parse.quote(t.replace(" ", "_"), safe="") + f"/daily/{start:%Y%m%d}/{end:%Y%m%d}"
        views[t] = get_json(url).get("items", [])
        time.sleep(0.5)
    json.dump({"views": views}, open(path, "w"))
    print(f"{f.film_id:14s} titles: {sorted(views)}", flush=True)

# flatten: one row per film, title and day, then add up the titles
rows = [{"film_id": f.film_id, "title": t, "date": pd.Timestamp(i["timestamp"][:8]), "views": i["views"]}
        for f in films.itertuples()
        for t, items in json.load(open(f"{OUT}/{f.film_id}.json"))["views"].items() for i in items]
by_title = pd.DataFrame(rows)
by_title.to_csv("data/raw/pageviews_by_title.csv", index=False)
days = pd.concat([pd.DataFrame({"film_id": f.film_id,
                                "date": pd.date_range(f.trailer_day - pd.Timedelta(days=14),
                                                      f.release + pd.Timedelta(days=28))})
                  for f in films.itertuples()])
pv = days.merge(by_title.groupby(["film_id", "date"]).views.sum().reset_index(), how="left")
pv.to_csv("data/raw/pageviews_daily.csv", index=False)     # empty views = no record that day
print("film-days:", len(pv), " with no record:", pv.views.isna().sum())
