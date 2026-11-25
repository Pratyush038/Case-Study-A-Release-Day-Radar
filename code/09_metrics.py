# Step 9: one row per film with every buzz signal next to the box office.
# Wikipedia pageviews are counted in fixed windows so films of different dates compare fairly:
#   trailer week   = the 7 days from the trailer upload (day 0 to 6)
#   pre-release    = the 7 days before release
#   opening 3 days = release day and the 2 days after (what is known by Monday morning)
# Comment sentiment is split into comments written before and after release.

import pandas as pd

films = pd.read_csv("data/clean/films_clean.csv", parse_dates=["release_date"])
trailers = pd.read_csv("data/clean/trailers_clean.csv")
pv = pd.read_csv("data/clean/pageviews_clean.csv", parse_dates=["date"])
c = pd.read_parquet("data/clean/comments_scored.parquet").merge(films[["film_id", "release_date"]])

m = films[["film_id", "wiki_title", "language", "language_group", "holdout", "release_date",
           "gross_cr", "budget_cr", "gross_to_budget"]].merge(
    trailers[["film_id", "views", "likes", "like_rate_pct", "days_trailer_to_release"]]
    .rename(columns={"views": "trailer_views", "likes": "trailer_likes"}))


def window(name, col, lo, hi):
    return pv[pv[col].between(lo, hi)].groupby("film_id").views.sum().rename(name)


m = (m.merge(window("pv_trailer_week", "day_from_trailer", 0, 6), on="film_id")
      .merge(window("pv_pre_release_week", "day_from_release", -7, -1), on="film_id")
      .merge(window("pv_opening_3d", "day_from_release", 0, 2), on="film_id"))
# how fast interest fades: views in week 2 after release as a % of week 1
w1 = window("w1", "day_from_release", 0, 6)
w2 = window("w2", "day_from_release", 7, 13)
m = m.merge((100 * w2 / w1).round(1).rename("pv_week2_vs_week1_pct"), on="film_id")

# sentiment of the top comments, before and after release (Latin script only)
c["period"] = (c.published_ist >= c.release_date).map({False: "before", True: "after"})
s = c[c.scored].groupby(["film_id", "period"]).compound.mean().unstack().round(3)
m = m.merge(s.add_prefix("sentiment_").reset_index(), on="film_id", how="left")
m = m.merge(c[c.period == "after"].groupby("film_id").size().rename("comments_after_release"),
            on="film_id", how="left")
m["comments_after_release"] = m.comments_after_release.fillna(0).astype(int)

m.to_csv("data/clean/film_metrics.csv", index=False)
print(m.drop(columns=["wiki_title"]).to_string())
