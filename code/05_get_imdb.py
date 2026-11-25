# Step 5: the IMDb 50K movie-review corpus (Maas et al., Stanford), the brief's practice corpus.
# 50,000 English reviews labelled positive or negative. We use it to test our sentiment
# method before trusting it on our own, unlabelled comments, and it goes into the
# PySpark text job as a second text source.
# Each review is one small text file named <id>_<star rating>.txt in a pos or neg folder.

import os
import tarfile
import requests
import pandas as pd

URL = "https://ai.stanford.edu/~amaas/data/sentiment/aclImdb_v1.tar.gz"
OUT = "data/raw/imdb"
TAR = f"{OUT}/aclImdb_v1.tar.gz"
os.makedirs(OUT, exist_ok=True)

if not os.path.exists(TAR):
    with requests.get(URL, stream=True, timeout=600) as r:
        with open(TAR, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)

rows = []
with tarfile.open(TAR) as tar:                 # read straight from the archive, no unpacking
    for m in tar:
        parts = m.name.split("/")              # aclImdb/train/pos/123_9.txt
        if m.isfile() and len(parts) == 4 and parts[2] in ("pos", "neg") and m.name.endswith(".txt"):
            num, stars = parts[3][:-4].split("_")
            rows.append({"review_id": f"{parts[1]}_{parts[2]}_{num}", "split": parts[1],
                         "label": parts[2], "stars": int(stars),
                         "text": tar.extractfile(m).read().decode("utf-8")})
imdb = pd.DataFrame(rows)
imdb.to_csv("data/raw/imdb_reviews.csv", index=False)
print(imdb.groupby(["split", "label"]).size())
print("reviews:", len(imdb))
