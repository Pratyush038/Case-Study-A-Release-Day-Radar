# Step 3: trailer statistics and trailer comments from the YouTube Data API v3 (JSON).
#  - videos.list: views, likes, comment count, upload time and length (1 quota unit)
#  - commentThreads.list: the top 2,000 comments per trailer, YouTube's "relevance"
#    order (the comments people liked and replied to most), 100 per page, 1 unit a page.
# 28 trailers x 20 pages = 560 units, well inside the free 10,000 a day.
# Privacy: the "fields" filter asks only for comment text, time and like count,
# so usernames and channel links are never downloaded.

import os
import json
import time
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv(".env")
KEY = os.environ["YOUTUBE_API_KEY"]
URL = "https://www.googleapis.com/youtube/v3/"
OUT = "data/raw/youtube"
PAGES = 20                                   # 20 pages x 100 = 2,000 comments per trailer
os.makedirs(f"{OUT}/comments", exist_ok=True)

trailers = pd.read_csv("data/trailers.csv")

# ---------- 1. trailer statistics (raw JSON kept, then flattened) ----------
if not os.path.exists(f"{OUT}/videos_raw.json"):        # one snapshot, kept for reruns
    raw = requests.get(URL + "videos", params={"part": "snippet,statistics,contentDetails",
                                               "id": ",".join(trailers.video_id), "key": KEY}, timeout=60).json()
    raw["accessed_utc"] = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M")
    json.dump(raw, open(f"{OUT}/videos_raw.json", "w"), ensure_ascii=False)
raw = json.load(open(f"{OUT}/videos_raw.json"))

# json_normalize turns the nested dicts into columns like statistics.viewCount
videos = pd.json_normalize(raw["items"])[["id", "snippet.channelTitle", "snippet.title", "snippet.publishedAt",
                                          "contentDetails.duration", "statistics.viewCount",
                                          "statistics.likeCount", "statistics.commentCount"]]
videos.columns = ["video_id", "channel", "video_title", "published_utc", "duration_iso",
                  "views_text", "likes_text", "comments_text"]
videos = trailers.merge(videos, on="video_id", how="left")
videos["accessed_utc"] = raw["accessed_utc"]
videos.to_csv("data/raw/trailer_stats.csv", index=False)
print(videos[["film_id", "channel", "views_text", "comments_text"]].to_string())

# ---------- 2. top comments ----------
for v in videos.itertuples():
    path = f"{OUT}/comments/{v.film_id}.json"
    if os.path.exists(path):                 # skip trailers we already have
        continue
    params = {"part": "snippet", "videoId": v.video_id, "maxResults": 100, "order": "relevance",
              "textFormat": "plainText", "key": KEY,
              "fields": "nextPageToken,items(id,snippet(totalReplyCount,topLevelComment/snippet"
                        "(textOriginal,publishedAt,likeCount)))"}
    pages = []
    for _ in range(PAGES):
        d = requests.get(URL + "commentThreads", params=params, timeout=60).json()
        if "error" in d:
            raise SystemExit(d["error"]["message"])
        pages.append(d)
        if "nextPageToken" not in d:
            break
        params["pageToken"] = d["nextPageToken"]
        time.sleep(0.2)
    json.dump(pages, open(path, "w"), ensure_ascii=False)
    print(f"{v.film_id:14s} {sum(len(p['items']) for p in pages):>6,} comments", flush=True)

# ---------- 3. flatten into one table ----------
rows = []
for v in videos.itertuples():
    for page in json.load(open(f"{OUT}/comments/{v.film_id}.json")):
        items = pd.json_normalize(page["items"])
        if len(items):
            items.insert(0, "film_id", v.film_id)
            rows.append(items)
comments = pd.concat(rows, ignore_index=True)
comments.columns = [c.split(".")[-1] for c in comments.columns]    # ...snippet.textOriginal -> textOriginal
comments = comments.rename(columns={"id": "comment_id", "textOriginal": "text", "publishedAt": "published_utc",
                                    "likeCount": "likes", "totalReplyCount": "replies"})
comments.to_csv("data/raw/youtube_comments.csv", index=False)
print("comments:", len(comments))
