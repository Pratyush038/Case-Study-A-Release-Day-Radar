# Step 2a: find each film's official theatrical trailer on YouTube (JSON API).
# A search costs 100 of our 10,000 daily quota units, so we search once and save
# the candidates. Then a rule picks one trailer per film:
#   - uploaded in the year before the release date and before the release itself
#     (search returned Netflix trailers uploaded after the film reached OTT)
#   - title says "trailer", and not teaser, glimpse, promo, reaction, review or song
#   - not an OTT or cinema-chain channel (Netflix, Prime Video, PVR ...)
#   - among what is left, the one with the most views
# The picked ids are written to data/trailers.csv, which we then checked by hand.

import os
import json
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv(".env")
KEY = os.environ["YOUTUBE_API_KEY"]
URL = "https://www.googleapis.com/youtube/v3/"
OUT = "data/raw/youtube/search"
os.makedirs(OUT, exist_ok=True)

info = pd.read_csv("data/raw/wiki_infobox.csv")
info["release"] = pd.to_datetime(info.release_text.str.extract(r"\((\d{4}-\d{2}-\d{2})\)")[0])
info["title"] = info.wiki_title.str.replace(r"\s*\(.*?film\)", "", regex=True)

rows = []
for f in info.itertuples():
    path = f"{OUT}/{f.film_id}.json"
    if not os.path.exists(path):
        params = {"part": "snippet", "q": f"{f.title} official trailer", "type": "video",
                  "maxResults": 25, "key": KEY,
                  "publishedAfter": (f.release - pd.Timedelta(days=365)).strftime("%Y-%m-%dT00:00:00Z"),
                  "publishedBefore": (f.release + pd.Timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")}
        data = requests.get(URL + "search", params=params, timeout=60).json()
        if "error" in data:
            raise RuntimeError(data["error"]["message"])
        json.dump(data, open(path, "w"))
    for it in json.load(open(path))["items"]:
        rows.append({"film_id": f.film_id, "title": f.title, "release": f.release,
                     "video_id": it["id"]["videoId"], "channel": it["snippet"]["channelTitle"],
                     "video_title": it["snippet"]["title"], "published": it["snippet"]["publishedAt"]})
cand = pd.DataFrame(rows)

# views for every candidate (videos.list takes 50 ids per call, 1 unit each)
stats = []
ids = cand.video_id.unique().tolist()
for i in range(0, len(ids), 50):
    data = requests.get(URL + "videos", params={"part": "statistics", "id": ",".join(ids[i:i + 50]),
                                                "key": KEY}, timeout=60).json()
    stats += [{"video_id": v["id"], "views": int(v["statistics"].get("viewCount", 0))} for v in data["items"]]
cand = cand.merge(pd.DataFrame(stats), on="video_id", how="left")
cand.to_csv("data/raw/trailer_candidates.csv", index=False)

# the rule
t = cand.video_title.str.lower()
ok = (t.str.contains("trailer")
      & ~t.str.contains(r"teaser|glimpse|promo|reaction|review|song|lyric|making|bts|breakdown|explained|spoof|fan made|fanmade")
      & ~cand.channel.str.contains(r"netflix|prime video|jiohotstar|hotstar|zee5|sony liv|pvr|inox|cinepolis|bookmyshow|filmibeat|pinkvilla|bollywood hungama",
                                   case=False)
      & (pd.to_datetime(cand.published).dt.tz_localize(None) < cand.release))
best = cand[ok].sort_values("views", ascending=False).drop_duplicates("film_id")
best = info[["film_id"]].merge(best, how="left")
print(best[["film_id", "video_id", "channel", "views", "published", "video_title"]].to_string())
print("films without a trailer:", best.video_id.isna().sum())
best[["film_id", "video_id", "channel", "video_title", "published", "views"]].to_csv(
    "data/raw/trailers_picked_by_rule.csv", index=False)
