# Step 6: the PySpark text job over the YouTube trailer comments and the IMDb 50K reviews.
# clean -> measure length -> find the script (Latin, Devanagari, Tamil ...) -> count terms
# -> count aspect words (music, story ...) -> aggregate by film. Row counts after each step.

import os
import sys
from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F
from pyspark.ml.feature import RegexTokenizer, StopWordsRemover

# PySpark needs Java 17; use Homebrew's copy if JAVA_HOME is not set
if "JAVA_HOME" not in os.environ and os.path.exists("/opt/homebrew/opt/openjdk@17"):
    os.environ["JAVA_HOME"] = "/opt/homebrew/opt/openjdk@17"
os.environ["PYSPARK_PYTHON"] = sys.executable      # Spark workers use the same Python as this script

spark = (SparkSession.builder.appName("release-day-radar")
         .config("spark.sql.session.timeZone", "Asia/Kolkata")    # show all times in IST
         .config("spark.driver.memory", "4g")
         .config("spark.ui.showConsoleProgress", "false")
         .getOrCreate())
spark.sparkContext.setLogLevel("ERROR")

counts = []


def log(step, df):
    n = df.count()
    counts.append((step, n))
    print(f"{step:50s} {n:>8,}", flush=True)


def read(path):
    # the text has commas, quotes and line breaks inside it; pandas wrote "" for a quote
    return spark.read.csv(path, header=True, multiLine=True, escape='"')


# 1. load both text sources as plain text and put them in the same shape
yt = read("data/raw/youtube_comments.csv").select(
    F.lit("youtube").alias("source"), F.col("comment_id").alias("doc_id"), "film_id",
    F.col("published_utc").alias("time_text"), "text", F.col("likes").alias("likes_text"))
im = read("data/raw/imdb_reviews.csv").select(
    F.lit("imdb").alias("source"), F.col("review_id").alias("doc_id"), F.lit(None).cast("string").alias("film_id"),
    F.lit(None).cast("string").alias("time_text"), "text", F.lit(None).cast("string").alias("likes_text"))
docs = yt.unionByName(im)
log("1. raw rows (YouTube comments + IMDb reviews)", docs)
log("   1a. of which YouTube comments", yt)
log("   1b. of which IMDb reviews", im)

# 2. empty text
docs = docs.filter(F.col("text").isNotNull() & (F.trim("text") != ""))
log("2. empty text dropped", docs)

# 3. the same id twice
docs = docs.dropDuplicates(["source", "doc_id"])
log("3. duplicate ids dropped", docs)

# 4. type casting: time is ISO text in UTC, likes are numbers stored as text
docs = (docs.withColumn("published", F.to_timestamp("time_text"))
            .withColumn("likes", F.col("likes_text").cast("int"))
            .drop("time_text", "likes_text"))
log("   4a. YouTube rows whose time did not parse",
    docs.filter((F.col("source") == "youtube") & F.col("published").isNull()))

# 5. clean the text: lower case, drop links, html leftovers and extra spaces
clean = F.lower("text")
clean = F.regexp_replace(clean, r"https?://\S+|www\.\S+", " ")
clean = F.regexp_replace(clean, r"<br\s*/?>|&#39;|&quot;|&amp;", " ")
clean = F.trim(F.regexp_replace(clean, r"\s+", " "))
docs = docs.withColumn("text_clean", clean)

# 6. length in characters and words
docs = (docs.withColumn("n_chars", F.length("text_clean"))
            .withColumn("n_words", F.size(F.split("text_clean", " "))))

# 7. which script is it written in? the Unicode block with the most letters wins
scripts = {"latin": "a-z", "devanagari": "ऀ-ॿ", "tamil": "஀-௿",
           "telugu": "ఀ-౿", "kannada": "ಀ-೿", "malayalam": "ഀ-ൿ"}
for name, rng in scripts.items():
    docs = docs.withColumn("n_" + name, F.length(F.regexp_replace("text_clean", f"[^{rng}]", "")))
most = F.greatest(*[F.col("n_" + s) for s in scripts])
docs = docs.withColumn("script", F.lit("no letters"))
for s in scripts:
    docs = docs.withColumn("script", F.when((most > 0) & (F.col("n_" + s) == most), s).otherwise(F.col("script")))
docs = docs.drop(*["n_" + s for s in scripts]).cache()
log("7. clean rows", docs)

# 8. term counts per film (Latin-script words; English and common Hinglish stop words removed)
hinglish = ["hai", "hain", "bhai", "kya", "nahi", "nhi", "bhi", "aur", "toh", "tha", "thi", "ho", "hi", "ka",
            "ki", "ke", "ko", "se", "me", "mein", "ye", "yeh", "wo", "woh", "ek", "koi", "kuch", "sab", "jo",
            "par", "pe", "hum", "aap", "kar", "raha", "rahe", "rahi", "hoga", "gaya",
            "movie", "film", "trailer", "sir", "anna", "garu", "bro"]
tok = RegexTokenizer(inputCol="text_clean", outputCol="tokens", pattern="[^a-z]+", minTokenLength=3)
stop = StopWordsRemover(inputCol="tokens", outputCol="terms",
                        stopWords=StopWordsRemover.loadDefaultStopWords("english") + hinglish)
terms = stop.transform(tok.transform(docs.filter(F.col("source") == "youtube")))
term_counts = terms.select("film_id", F.explode("terms").alias("term")).groupBy("film_id", "term").count()
rank = Window.partitionBy("film_id").orderBy(F.desc("count"))
top_terms = term_counts.withColumn("rank", F.row_number().over(rank)).filter("rank <= 15")
log("8. distinct film x term pairs", term_counts)

# 9. aspect words: which part of the film is the comment about?
aspects = {"music": r"\b(music|songs?|bgm|album|background score)\b",
           "story": r"\b(story|script|plot|screenplay|writing)\b",
           "acting": r"\b(acting|performances?|actor|acted|expressions?)\b",
           "vfx": r"\b(vfx|cgi|graphics|visuals|effects)\b",
           "action": r"\b(action|fights?|stunts?)\b",
           "length": r"\b(length|lengthy|runtime|slow|drag|dragged|boring)\b"}
for a, rx in aspects.items():
    docs = docs.withColumn("about_" + a, F.col("text_clean").rlike(rx))

# 10. aggregate by film
by_film = (docs.filter(F.col("source") == "youtube").groupBy("film_id")
               .agg(F.count("*").alias("comments"),
                    F.round(F.avg("n_words"), 1).alias("avg_words"),
                    F.round(100 * F.avg((F.col("script") == "latin").cast("int")), 1).alias("pct_latin_script"),
                    *[F.sum(F.col("about_" + a).cast("int")).alias("n_" + a) for a in aspects])
               .orderBy("film_id"))
log("10. film summary rows", by_film)

docs.write.mode("overwrite").parquet("data/clean/text_clean.parquet")    # keeps original text for VADER
by_film.toPandas().to_csv("data/clean/film_text_summary.csv", index=False)
top_terms.orderBy("film_id", "rank").toPandas().to_csv("data/clean/top_terms.csv", index=False)
(docs.groupBy("source", "script").count().orderBy("source", F.desc("count"))
     .toPandas().to_csv("data/clean/script_counts.csv", index=False))
spark.createDataFrame(counts, ["step", "rows"]).toPandas().to_csv("data/clean/spark_row_counts.csv", index=False)
spark.stop()
