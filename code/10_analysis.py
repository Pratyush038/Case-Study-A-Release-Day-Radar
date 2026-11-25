# Step 10: findings and charts.
# Films differ hugely in scale (trailer views ~30x apart, gross ~50x), so we use logs,
# z-scores and rank correlation (Spearman: "does a bigger signal go with a bigger gross?").
#
# Buzz index = average z-score of three trailer-stage signals: log trailer views,
# log trailer likes and log trailer-week Wikipedia views. The z-scores and the line from
# index to gross are fitted on the 21 films of 2025 only, then used to predict the
# 7 films of 2026 that the fit never saw.

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid")
rng = np.random.default_rng(0)
notes = []


def say(text):
    print(text)
    notes.append(text)


def spearman(x, y, n_perm=10000):
    """Rank correlation, and a permutation p-value: how often shuffled data does as well."""
    ok = x.notna() & y.notna()
    rx, ry = x[ok].rank().to_numpy(), y[ok].rank().to_numpy()
    r = np.corrcoef(rx, ry)[0, 1]
    perm = np.array([np.corrcoef(rx, rng.permutation(ry))[0, 1] for _ in range(n_perm)])
    return r, (np.abs(perm) >= abs(r)).mean(), int(ok.sum())


def miss(actual, predicted):
    """How many times off a prediction was, either way (1.0 = spot on)."""
    return np.maximum(actual / predicted, predicted / actual)


m = pd.read_csv("data/clean/film_metrics.csv", parse_dates=["release_date"])
pv = pd.read_csv("data/clean/pageviews_clean.csv", parse_dates=["date"])
c = pd.read_parquet("data/clean/comments_scored.parquet")
train = m[m.holdout == 0]

# ---------- 1. which signal goes with the gross? (21 films of 2025) ----------
signals = {"trailer_views": "Trailer views (YouTube)",
           "trailer_likes": "Trailer likes (YouTube)",
           "like_rate_pct": "Likes per 100 views (YouTube)",
           "pv_trailer_week": "Trailer week, Wikipedia views",
           "pv_pre_release_week": "Week before release, Wikipedia views",
           "pv_opening_3d": "Opening 3 days, Wikipedia views",
           "sentiment_before": "Comment sentiment before release",
           "sentiment_after": "Comment sentiment after release"}
corr = []
for col, label in signals.items():
    r, p, n = spearman(train[col], train.gross_cr)
    corr.append({"signal": label, "spearman_r": round(r, 2), "p_value": round(p, 3), "films": n})
corr = pd.DataFrame(corr)
corr.to_csv("data/clean/signal_correlations.csv", index=False)
say("Rank correlation with worldwide gross, 21 films of 2025:\n" + corr.to_string(index=False))

# ---------- 2. buzz index, fitted on 2025, tested on 2026 ----------
parts = ["trailer_views", "trailer_likes", "pv_trailer_week"]
for p in parts:
    mu, sd = np.log10(train[p]).mean(), np.log10(train[p]).std()
    m["z_" + p] = (np.log10(m[p]) - mu) / sd
m["buzz_index"] = m[["z_" + p for p in parts]].mean(axis=1)
train = m[m.holdout == 0]
b, a = np.polyfit(train.buzz_index, np.log10(train.gross_cr), 1)
m["pred_from_buzz_cr"] = 10 ** (a + b * m.buzz_index)
r_fit = np.corrcoef(train.buzz_index, np.log10(train.gross_cr))[0, 1]
say(f"Buzz index vs log gross on 2025 films: r = {r_fit:.2f} (explains {100 * r_fit ** 2:.0f}% of the spread)")

# the Monday signal: opening 3 days of Wikipedia views, fitted the same way
b2, a2 = np.polyfit(np.log10(train.pv_opening_3d), np.log10(train.gross_cr), 1)
m["pred_from_opening_cr"] = 10 ** (a2 + b2 * np.log10(m.pv_opening_3d))
r_open = np.corrcoef(np.log10(train.pv_opening_3d), np.log10(train.gross_cr))[0, 1]
say(f"Opening-3-day Wikipedia views vs log gross on 2025 films: r = {r_open:.2f} "
    f"(explains {100 * r_open ** 2:.0f}%)")

test = m[m.holdout == 1].copy()
test["miss_buzz"] = miss(test.gross_cr, test.pred_from_buzz_cr)
test["miss_opening"] = miss(test.gross_cr, test.pred_from_opening_cr)
say("2026 films, never used in fitting:\n" + test[["wiki_title", "gross_cr", "pred_from_buzz_cr", "miss_buzz",
                                                     "pred_from_opening_cr", "miss_opening"]].round(1).to_string(index=False))
say(f"Median miss on 2026 films: buzz index {test.miss_buzz.median():.2f}x, "
    f"opening 3 days {test.miss_opening.median():.2f}x")
med = train.gross_cr.median()
for col, name in [("pred_from_buzz_cr", "buzz index"), ("pred_from_opening_cr", "opening 3 days")]:
    right = ((test[col] >= med) == (test.gross_cr >= med)).sum()
    say(f"Above or below the 2025 median gross (₹{med:.0f} cr): {name} called {right} of {len(test)} right")
m["actual_vs_buzz"] = (m.gross_cr / m.pred_from_buzz_cr).round(2)
m.to_csv("data/clean/film_metrics_scored.csv", index=False)

# ---------- 3. word of mouth: does sentiment explain films that beat their buzz? ----------
for col in ["sentiment_after", "pv_week2_vs_week1_pct"]:
    r, p, n = spearman(m[col], m.actual_vs_buzz)
    say(f"{col} vs (actual gross / buzz-index prediction), all films: rank r = {r:.2f}, p = {p:.3f}, n = {n}")

# ---------- 4. velocity: how fast interest rises and fades ----------
peak = pv.loc[pv.groupby("film_id").views.idxmax(), ["film_id", "day_from_release", "views"]]
say(f"Day of peak Wikipedia interest relative to release: {peak.day_from_release.value_counts().sort_index().to_dict()}")
say(f"Week 2 after release as % of week 1: median {m.pv_week2_vs_week1_pct.median():.0f}%, "
    f"range {m.pv_week2_vs_week1_pct.min():.0f}% to {m.pv_week2_vs_week1_pct.max():.0f}%")
say(f"Busiest single day: {peak.views.max():,} views ({peak.loc[peak.views.idxmax(), 'film_id']}), "
    f"about {peak.views.max() / 24:,.0f} an hour")

# ---------- 5. which part of the film do comments praise or criticise? ----------
yt = c[(c.source == "youtube") & c.scored]
aspects = ["music", "story", "acting", "vfx", "action", "length"]
asp = pd.DataFrame([{"aspect": a, "comments": int(yt["about_" + a].sum()),
                     "mean_sentiment": yt.loc[yt["about_" + a], "compound"].mean(),
                     "pct_negative": 100 * (yt.loc[yt["about_" + a], "compound"] <= -0.05).mean()}
                    for a in aspects]).round(3)
asp.to_csv("data/clean/aspect_sentiment.csv", index=False)
say("Aspects in Latin-script comments (all films):\n" + asp.to_string(index=False))

# ---------- 6. Hindi vs South Indian ----------
for g, d in m.groupby("language_group"):
    r, p, n = spearman(d.trailer_views, d.gross_cr, 2000)
    say(f"{g}: {n} films, trailer views vs gross rank r = {r:.2f}; median "
        f"₹{(d.gross_cr * 1e7 / d.trailer_views).median():.0f} gross per trailer view")

open("data/clean/findings.txt", "w").write("\n\n".join(notes))


# =============================== charts ===============================
COL = {"Hindi": "#d95f02", "South Indian": "#386cb0"}
short = m.set_index("film_id").wiki_title.str.replace(r"\s*\(.*\)", "", regex=True)

# chart 1: trailer views vs gross (YouTube + Wikipedia, two sources joined on film_id)
fig, ax = plt.subplots(figsize=(9, 5.5))
for g, d in m.groupby("language_group"):
    r, _, n = spearman(d.trailer_views, d.gross_cr, 2000)
    ax.scatter(d.trailer_views / 1e6, d.gross_cr, s=60, color=COL[g], label=f"{g} ({n} films, rank r = {r:.2f})")
for row in m.itertuples():
    ax.annotate(short[row.film_id], (row.trailer_views / 1e6, row.gross_cr), fontsize=7,
                xytext=(4, 3), textcoords="offset points")
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("Trailer views on YouTube, millions (log scale)")
ax.set_ylabel("Worldwide gross, Rs crore (log scale)")
ax.set_title("Trailer views track the gross of Hindi films,\nbut say almost nothing about South Indian films")
ax.legend(loc="upper left")
plt.tight_layout(); plt.savefig("charts/01_views_vs_gross.png", dpi=150); plt.close()

# chart 2: which signal tracks gross best (2025 films)
cc = corr.sort_values("spearman_r")
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.barh(cc.signal, cc.spearman_r, color=["#386cb0" if p < 0.05 else "#b3c6e0" for p in cc.p_value])
for y, (r, p) in enumerate(zip(cc.spearman_r, cc.p_value)):
    ax.text(r + 0.01, y, f"{r:.2f}" + (" *" if p < 0.05 else ""), va="center", fontsize=9)
ax.set_xlim(0, 0.75)
ax.set_xlabel("Rank correlation with worldwide gross, 21 films of 2025 (* = p below 0.05)")
ax.set_title("Trailer likes and opening-weekend Wikipedia views track the gross best;\nraw trailer views barely do")
plt.tight_layout(); plt.savefig("charts/02_signal_strength.png", dpi=150); plt.close()

# chart 3: normalised daily interest around release (min-max per film, so big and small films share one scale)
d = pv[pv.day_from_release.between(-7, 21)].copy()
d["scaled"] = d.groupby("film_id").views.transform(lambda s: (s - s.min()) / (s.max() - s.min()))
fig, ax = plt.subplots(figsize=(10, 4.8))
for fid, g in d.groupby("film_id"):
    ax.plot(g.day_from_release, g.scaled, color="grey", alpha=0.25, lw=1)
typical = d.groupby("day_from_release").scaled.median()
ax.plot(typical.index, typical.values, color="black", lw=2.5, label="median of 28 films")
for fid, c_ in [("saiyaara", "#e7298a"), ("lokah", "#1b9e77"), ("dhurandhar", "#d95f02")]:
    g = d[d.film_id == fid]
    ax.plot(g.day_from_release, g.scaled, color=c_, lw=2,
            label=f"{short[fid]} (week 2 = {m.set_index('film_id').pv_week2_vs_week1_pct[fid]:.0f}% of week 1)")
ax.axvline(0, color="black", lw=0.6, ls="--")
ax.set_xlabel("Days from release"); ax.set_ylabel("Daily Wikipedia views, scaled 0 to 1 per film")
ax.set_title("Interest peaks the day after release and halves within a week, word-of-mouth hits keep climbing")
ax.legend(fontsize=8)
plt.tight_layout(); plt.savefig("charts/03_buzz_decay.png", dpi=150); plt.close()

# chart 4: the 2026 test
t = m[m.holdout == 1].sort_values("gross_cr")
fig, ax = plt.subplots(figsize=(9, 4.5))
y = np.arange(len(t))
ax.scatter(t.gross_cr, y, color="black", s=60, label="actual gross", zorder=3)
ax.scatter(t.pred_from_buzz_cr, y, color="#386cb0", marker="D", s=45, label="buzz index (before release)")
ax.scatter(t.pred_from_opening_cr, y, color="#d95f02", marker="s", s=45, label="opening 3 days (Monday)")
ax.axvline(med, color="grey", ls="--", lw=1); ax.text(med, -0.75, " 2025 median", fontsize=8, color="grey")
ax.set_yticks(y); ax.set_yticklabels(t.wiki_title.str.replace(r"\s*\(.*\)", "", regex=True))
ax.set_xscale("log"); ax.set_xlabel("Worldwide gross, Rs crore (log scale)")
ax.set_title("2026 test: the buzz index put 6 of 7 films on the right side of the median,\nbut no signal saw how big Dhurandhar: The Revenge would be")
ax.legend(fontsize=8, loc="lower right")
plt.tight_layout(); plt.savefig("charts/04_test_2026.png", dpi=150); plt.close()

# chart 5: what comments praise or criticise
a = asp.sort_values("pct_negative")
fig, ax = plt.subplots(figsize=(8, 4))
ax.barh(a.aspect + "  (" + a.comments.astype(str) + " comments)", a.pct_negative,
        color=["#d95f02" if x > 50 else "#386cb0" for x in a.pct_negative])
ax.set_xlabel("% of comments on this aspect that are negative (VADER)")
ax.set_title("Comments praise acting and music;\nlength is the one thing most people complain about")
plt.tight_layout(); plt.savefig("charts/05_aspects.png", dpi=150); plt.close()
print("charts saved")
