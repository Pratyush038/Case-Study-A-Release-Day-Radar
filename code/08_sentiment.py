# Step 8: sentiment with VADER, tested first on the labelled IMDb 50K corpus.
# VADER gives each text a "compound" score from -1 (negative) to +1 (positive).
# 1. test plain VADER on IMDb: how often does compound >= 0.05 agree with the label?
# 2. VADER reads Indian film slang wrongly (🔥 = "fire" = negative), so we add a small
#    domain lexicon and test again on IMDb to make sure it did not get worse.
# 3. score the YouTube text. Only Latin-script text is scored: VADER only
#    knows English, and comments in Devanagari, Tamil or Telugu script would all score 0.

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

notes = []


def say(text):
    print(text)
    notes.append(text)


docs = pd.read_parquet("data/clean/text_clean.parquet")

plain = SentimentIntensityAnalyzer()
tuned = SentimentIntensityAnalyzer()
# domain lexicon (VADER scale is -4 to +4). Why each one:
#   fire / 🔥   : "trailer is fire 🔥" is praise here, VADER scores "fire" -1.4
#   goosebumps : praise, missing from VADER
#   cringe     : criticism, missing from VADER
#   💥         : VADER reads it as "collision" (negative); in hype comments it is not
tuned.lexicon.update({"fire": 2.0, "goosebumps": 2.0, "cringe": -2.0})
tuned.emojis["💥"] = ""

# ---------- 1 and 2: test on IMDb ----------
imdb = docs[docs.source == "imdb"].copy()
imdb = imdb.merge(pd.read_csv("data/raw/imdb_reviews.csv", usecols=["review_id", "label"]),
                  left_on="doc_id", right_on="review_id")
results = []
for name, sia in [("plain VADER", plain), ("VADER + domain words", tuned)]:
    score = imdb.text.map(lambda s: sia.polarity_scores(s)["compound"])
    pred = (score >= 0.05).map({True: "pos", False: "neg"})
    acc = (pred == imdb.label).mean()
    results.append({"method": name, "accuracy_pct": round(100 * acc, 1),
                    "pos_reviews_called_pos_pct": round(100 * (pred[imdb.label == "pos"] == "pos").mean(), 1),
                    "neg_reviews_called_neg_pct": round(100 * (pred[imdb.label == "neg"] == "neg").mean(), 1)})
    if name == "VADER + domain words":
        imdb["compound"] = score
val = pd.DataFrame(results)
val.to_csv("data/clean/sentiment_validation.csv", index=False)
say("IMDb 50K check (compound >= 0.05 = positive):\n" + val.to_string(index=False))
say(f"VADER is better at spotting praise than criticism; negative reviews with mean compound "
    f"{imdb[imdb.label == 'neg'].compound.mean():.2f}, positive {imdb[imdb.label == 'pos'].compound.mean():.2f}")

# what the domain words change on our own comments
yt = docs[docs.source == "youtube"]
fire = yt[yt.text.str.contains("🔥")]
sample = fire.sample(min(5000, len(fire)), random_state=1)
before = sample.text.map(lambda s: plain.polarity_scores(s)["compound"]).mean()
after = sample.text.map(lambda s: tuned.polarity_scores(s)["compound"]).mean()
say(f"{len(fire):,} YouTube comments contain 🔥 ({100 * len(fire) / len(yt):.1f}%). Their mean score moves "
    f"from {before:+.2f} (plain VADER) to {after:+.2f} with the domain words")

# ---------- 3: score our comments and posts ----------
ours = docs[docs.source != "imdb"].copy()
ours["scored"] = ours.script == "latin"
ours["compound"] = None
ours.loc[ours.scored, "compound"] = ours.loc[ours.scored, "text"].map(lambda s: tuned.polarity_scores(s)["compound"])
ours["compound"] = ours.compound.astype(float)
ours["published_ist"] = pd.to_datetime(ours.published)       # parquet keeps the IST session time
by_script = ours.groupby("source").scored.mean().mul(100).round(1)
say(f"Share of text in Latin script (scored): {by_script.to_dict()}")
ours.drop(columns=["text", "published"]).to_parquet("data/clean/comments_scored.parquet", index=False)
open("data/clean/sentiment_notes.txt", "w").write("\n".join(notes))
