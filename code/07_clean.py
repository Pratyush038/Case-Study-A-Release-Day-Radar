# Step 7: clean the structured and semi-structured tables with pandas.
#  a) type casting: "₹797.34–809 crore" -> numbers in crore, "14 February 2025 (2025-02-14)"
#     -> datetime, counts stored as text -> integers, "PT2M41S" -> seconds
#  b) film-name matching: the same film is written differently in every source
#  c) cross-check the gross from two Wikipedia tables
#  d) gaps in the daily pageviews
# Every number quoted in the cleaning log is printed here and saved to data/clean/cleaning_notes.txt.

import re
import difflib
import pandas as pd

notes = []


def say(text):
    print(text)
    notes.append(text)


# ---------------- a) casting money text ----------------
def parse_money(text):
    """'₹1,350.83–₹1,428 crore' -> (1350.83, 1428.0) in crore. Ranges keep both ends.
    Handles crore, lakh, billion and plain rupees like '1,25,00,000'."""
    if pd.isna(text):
        return None, None
    t = str(text).lower()
    t = re.sub(r"\(.*?\)|\[.*?\]", " ", t)                 # "(combined with part 2)", footnotes
    t = t.replace("est.", " ").replace(",", "")
    t = re.sub(r"[–−—]", "-", t)                            # three different dash characters
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", t)]
    if not nums:
        return None, None
    if "crore" in t:
        scale = 1
    elif "lakh" in t:
        scale = 0.01                                        # 100 lakh = 1 crore
    elif "billion" in t:
        scale = 100                                         # ₹1 billion = 100 crore
    else:
        scale = 1e-7                                        # plain rupees
    lo, hi = nums[0] * scale, nums[min(1, len(nums) - 1)] * scale
    return lo, hi


info = pd.read_csv("data/raw/wiki_infobox.csv")
films = pd.read_csv("data/films.csv")
f = films.merge(info, on="film_id", suffixes=("_list", ""))

for col in ["budget", "gross"]:
    lo_hi = f[col + "_text"].map(parse_money)
    f[col + "_low_cr"] = lo_hi.str[0]
    f[col + "_high_cr"] = lo_hi.str[1]
    f[col + "_cr"] = (f[col + "_low_cr"] + f[col + "_high_cr"]) / 2        # a range becomes its midpoint
    f[col + "_is_range"] = f[col + "_low_cr"] != f[col + "_high_cr"]
    f[col + "_is_estimate"] = f[col + "_text"].str.contains("est", na=False)
say(f"Gross given as a range for {f.gross_is_range.sum()} of {len(f)} films, budget for {f.budget_is_range.sum()}; "
    f"we use the midpoint. 'est.' on {f.gross_is_estimate.sum()} grosses and {f.budget_is_estimate.sum()} budgets.")
say("Widest gross range: " + ", ".join(
    f"{r.film_id} {r.gross_low_cr:.0f}-{r.gross_high_cr:.0f}" for r in
    f.assign(w=f.gross_high_cr - f.gross_low_cr).nlargest(3, "w").itertuples()))

# shared budgets: the two Dhurandhar parts list one combined budget, so we cannot split it fairly
shared = f.budget_text.str.contains("combined", na=False)
f.loc[shared, ["budget_low_cr", "budget_high_cr", "budget_cr"]] = None
say(f"Budget set to missing: {', '.join(f.film_id[shared])} (one budget shared by two films); "
    f"budget missing on Wikipedia: {', '.join(f.film_id[f.budget_text.isna()])}.")
f["gross_to_budget"] = (f.gross_cr / f.budget_cr).round(2)

# release date: the ISO date Wikipedia puts in brackets; runtime: minutes
f["release_date"] = pd.to_datetime(f.release_text.str.extract(r"\((\d{4}-\d{2}-\d{2})\)")[0])
f["release_weekday"] = f.release_date.dt.day_name()
f["runtime_min"] = f.runtime_text.str.extract(r"(\d+)\s*min")[0].astype("Int64")
f["language"] = f.language_text.str.split("|").str[0].str.strip()
f["language_group"] = f.language.where(f.language == "Hindi", "South Indian")
say(f"Release weekdays: {f.release_weekday.value_counts().to_dict()}")
say(f"Runtime missing for {f.runtime_min.isna().sum()} films: {', '.join(f.film_id[f.runtime_min.isna()])}")

# ---------------- trailers: counts stored as text, ISO times and durations ----------------
t = pd.read_csv("data/raw/trailer_stats.csv", dtype=str)
for c in ["views", "likes", "comments"]:
    t[c] = pd.to_numeric(t[c + "_text"]).astype("Int64")
t["published_ist"] = pd.to_datetime(t.published_utc).dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
dur = t.duration_iso.str.extract(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?").astype(float).fillna(0).astype(int)
t["duration_s"] = dur[0] * 3600 + dur[1] * 60 + dur[2]
t = t.merge(f[["film_id", "release_date"]])
t["trailer_day"] = t.published_ist.dt.normalize()
t["days_trailer_to_release"] = (t.release_date - t.trailer_day).dt.days
t["like_rate_pct"] = (100 * t.likes / t.views).round(2)
say(f"Trailer lead time: {t.days_trailer_to_release.min()} to {t.days_trailer_to_release.max()} days, "
    f"median {t.days_trailer_to_release.median():.0f}")
say(f"Trailer views {t.views.min():,} to {t.views.max():,} ({t.views.max() / t.views.min():.0f}x apart)")

# ---------------- b) film-name matching ----------------
LANGS = r"official|trailer|teaser|hindi|telugu|tamil|kannada|malayalam|2\.0"


def key(name, youtube=False):
    """Matching key: lower case, footnotes and '(2025 film)' dropped, letters and digits only."""
    s = re.sub(r"\[.*?\]|\((?:\d{4} )?film\)", "", str(name).lower())
    if youtube:                                  # keep the part before | or - or (, drop trailer words
        s = re.split(r"\||\s-|\(", s)[0]
        s = re.sub(LANGS, " ", s)
    return re.sub(r"[^a-z0-9]", "", s)


lists = pd.read_csv("data/raw/wiki_gross_lists.csv")
lists["key"] = lists.title.map(key)
f["key"] = f.wiki_title.map(key)
t["key"] = t.video_title.map(lambda s: key(s, youtube=True))
match = f[["film_id", "wiki_title", "key"]].merge(t[["film_id", "video_title", "key"]], on="film_id",
                                                  suffixes=("_wiki", "_youtube"))
match["exact"] = match.key_wiki == match.key_youtube
match["similarity"] = [round(difflib.SequenceMatcher(None, a, b).ratio(), 2)
                       for a, b in zip(match.key_wiki, match.key_youtube)]
say(f"Name matching Wikipedia vs YouTube: {match.exact.sum()} of {len(match)} exact after normalising; "
    f"the rest: " + ", ".join(f"{r.video_title.split('|')[0].strip()} -> {r.wiki_title} ({r.similarity})"
                              for r in match[~match.exact].itertuples()))
lists_in = lists[lists.key.isin(f.key)].drop_duplicates(["key", "list_page"])
say(f"Films found in the Wikipedia gross ranking tables: {lists_in.key.nunique()} of {len(f)}")
match.to_csv("data/clean/name_matching.csv", index=False)

# ---------------- c) cross-check the gross: infobox vs ranking table ----------------
cross = lists_in.drop_duplicates("key").merge(f[["key", "film_id", "gross_text", "gross_low_cr", "gross_high_cr"]])
lo_hi = cross.worldwide_gross.map(parse_money)
cross["list_low_cr"], cross["list_high_cr"] = lo_hi.str[0], lo_hi.str[1]
cross["agree"] = (cross.list_low_cr <= cross.gross_high_cr + 0.5) & (cross.list_high_cr >= cross.gross_low_cr - 0.5)
say(f"Gross cross-check: infobox and ranking table overlap for {cross.agree.sum()} of {len(cross)} films; "
    "differ: " + (", ".join(f"{r.film_id} ({r.gross_text} vs {r.worldwide_gross})"
                            for r in cross[~cross.agree].itertuples()) or "none"))
cross[["film_id", "gross_text", "worldwide_gross", "list_page", "agree"]].to_csv("data/clean/gross_crosscheck.csv", index=False)

# ---------------- d) pageviews: gaps ----------------
pv = pd.read_csv("data/raw/pageviews_daily.csv", parse_dates=["date"])
pv = pv.merge(t[["film_id", "trailer_day"]]).merge(f[["film_id", "release_date"]])
pv["day_from_release"] = (pv.date - pv.release_date).dt.days
pv["day_from_trailer"] = (pv.date - pv.trailer_day).dt.days
pv["missing"] = pv.views.isna()
first = pv[~pv.missing].groupby("film_id").date.min().rename("first_record")
pv = pv.merge(first, on="film_id", how="left")
before = pv.missing & (pv.date < pv.first_record)
inside = pv.missing & ~before
say(f"Pageview days with no record: {pv.missing.sum()} of {len(pv)}. {before.sum()} fall before the page "
    f"existed (filled with 0: nobody can read a page that does not exist), {inside.sum()} inside the series "
    f"(filled with 0: the API leaves out days with no views).")
say("Films whose page did not exist on trailer day: " +
    (", ".join(pv[before & (pv.day_from_trailer == 0)].film_id.unique()) or "none"))
pv["views"] = pv.views.fillna(0).astype(int)
titles = pd.read_csv("data/raw/pageviews_by_title.csv").groupby("film_id").title.nunique()
say(f"Films whose Wikipedia page had more than one title (views summed over all of them): "
    f"{(titles > 1).sum()} of {len(titles)}, up to {titles.max()} titles ({titles.idxmax()})")
own = pd.read_csv("data/raw/pageviews_by_title.csv")
own = own.merge(f[["film_id", "wiki_title"]])
share = 1 - own[own.title == own.wiki_title].views.sum() / own.views.sum()
say(f"Views that would be lost by reading only today's title: {100 * share:.1f}% of all views in the windows")
pv = pv.drop(columns=["first_record", "missing", "trailer_day", "release_date"])

f.drop(columns=["key", "wiki_title_list"]).to_csv("data/clean/films_clean.csv", index=False)
t.drop(columns=["key"]).to_csv("data/clean/trailers_clean.csv", index=False)
pv.to_csv("data/clean/pageviews_clean.csv", index=False)
open("data/clean/cleaning_notes.txt", "w").write("\n".join(notes))
