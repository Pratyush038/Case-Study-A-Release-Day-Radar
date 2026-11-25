# Step 1: download each film's Wikipedia page (structured source, HTML tables).
# We keep the raw page exactly as received, then read the infobox, which is an
# HTML table, into one row per film. Values stay as text here ("₹797.34–809 crore",
# "14 February 2025 (2025-02-14)"). Type casting happens later in 05_clean.py.

import os
import re
import json
import time
import requests
import pandas as pd
from lxml import html

API = "https://en.wikipedia.org/w/api.php"
UA = {"User-Agent": "ReleaseDayRadar/1.0 (student data project)"}   # Wikipedia asks for a named client
OUT = "data/raw/wikipedia"
FIELDS = ["Directed by", "Starring", "Production companies", "Production company", "Distributed by",
          "Release dates", "Release date", "Running time", "Country", "Language", "Budget", "Box office"]
os.makedirs(OUT, exist_ok=True)

films = pd.read_csv("data/films.csv")


def get_page(title):
    """Call the parse API, wait and retry if Wikipedia says slow down (HTTP 429)."""
    for attempt in range(6):
        r = requests.get(API, params={"action": "parse", "page": title, "prop": "text",
                                      "format": "json", "redirects": 1}, headers=UA, timeout=60)
        if r.status_code == 200 and r.text.startswith("{"):
            return r.json()
        time.sleep(15 * (attempt + 1))
    raise RuntimeError("could not download " + title)


rows = []
for f in films.itertuples():
    path = f"{OUT}/{f.film_id}.json"
    if not os.path.exists(path):              # skip pages we already have
        with open(path, "w") as fh:
            json.dump(get_page(f.wiki_title), fh)
        time.sleep(3)
    page = json.load(open(path))["parse"]
    doc = html.fromstring(page["text"]["*"])

    # the infobox is a two-column HTML table: label in <th>, value in <td>
    row = {"film_id": f.film_id, "wiki_title": page["title"], "wiki_pageid": page["pageid"]}
    for tr in doc.xpath('//table[contains(@class,"infobox")]//tr'):
        th, td = tr.xpath("./th"), tr.xpath("./td")
        if th and td:
            label = th[0].text_content().strip()
            if label in FIELDS:
                for junk in td[0].xpath(".//style|.//sup"):     # css and footnote marks
                    junk.drop_tree()
                # keep list items apart with " | " so "Telugu" and "Hindi" don't run together
                for li in td[0].xpath(".//li"):
                    li.tail = " | " + (li.tail or "")
                for br in td[0].xpath(".//br"):
                    br.tail = " | " + (br.tail or "")
                row[label] = re.sub(r"\s+", " ", td[0].text_content()).strip(" |")
    rows.append(row)

info = pd.DataFrame(rows).reindex(columns=["film_id", "wiki_title", "wiki_pageid"] + FIELDS)
# Wikipedia uses both spellings of two labels, merge them
info["release_text"] = info.pop("Release dates").combine_first(info.pop("Release date"))
info["production_text"] = info.pop("Production companies").combine_first(info.pop("Production company"))
info = info.rename(columns={"Directed by": "director_text", "Starring": "cast_text",
                            "Distributed by": "distributor_text", "Running time": "runtime_text",
                            "Country": "country_text", "Language": "language_text",
                            "Budget": "budget_text", "Box office": "gross_text"})
info.to_csv("data/raw/wiki_infobox.csv", index=False)
print(info[["film_id", "release_text", "language_text", "budget_text", "gross_text"]].to_string())

# second structured source: the "highest-grossing" HTML tables on Wikipedia's list pages.
# Titles there are written differently ("Mahavatar Narsimha[α]"), which is the
# film-name matching problem, and the gross lets us cross-check the infobox.
import io
LISTS = {"hindi_2025": "List of Hindi films of 2025", "hindi_2026": "List of Hindi films of 2026",
         "indian_all_time": "List of highest-grossing Indian films"}
tables = []
for key, title in LISTS.items():
    path = f"{OUT}/list_{key}.json"
    if not os.path.exists(path):
        with open(path, "w") as fh:
            json.dump(get_page(title), fh)
        time.sleep(3)
    for t in pd.read_html(io.StringIO(json.load(open(path))["parse"]["text"]["*"])):
        cols = [str(c) for c in t.columns]
        if "Title" in cols and "Worldwide gross" in cols:      # the box-office ranking tables
            t = t.astype(str)
            t["list_page"] = title
            tables.append(t[[c for c in ["Title", "Worldwide gross", "Language", "Year", "list_page"] if c in t]])
            if key != "indian_all_time":                        # list pages: first ranking table only
                break
lists = pd.concat(tables, ignore_index=True)
lists.columns = [c.lower().replace(" ", "_") for c in lists.columns]
lists.to_csv("data/raw/wiki_gross_lists.csv", index=False)
print("rows in gross ranking tables:", len(lists))
