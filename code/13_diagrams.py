# Step 13: draws the ER diagram (charts/er_diagram.png) and the pipeline (charts/pipeline.png).

import matplotlib.pyplot as plt

tables = {
    "films":            (0.03, 0.50, ["PK film_id", "wiki_title", "language, language_group", "release_date",
                                      "runtime_min", "budget_cr, gross_cr", "gross_low_cr, gross_high_cr",
                                      "gross_is_estimate, holdout"]),
    "trailers":         (0.38, 0.58, ["PK video_id", "FK film_id (unique)", "channel, published_ist",
                                      "duration_s", "views, likes, comment_count", "days_trailer_to_release"]),
    "youtube_comments": (0.73, 0.50, ["PK comment_id", "FK video_id", "published_ist", "text_clean, n_words",
                                      "script, compound", "about_music ... about_length"]),
    "pageviews_daily":  (0.03, 0.06, ["PK,FK film_id", "PK date", "views", "day_from_trailer",
                                      "day_from_release"]),
}
W, LINE = 0.25, 0.042

fig, ax = plt.subplots(figsize=(12, 6.5))
for name, (x, y, cols) in tables.items():
    h = LINE * (len(cols) + 1)
    ax.add_patch(plt.Rectangle((x, y), W, h, fill=False, lw=1.5))
    ax.add_patch(plt.Rectangle((x, y + h - LINE), W, LINE, color="#386cb0"))
    ax.text(x + 0.01, y + h - LINE / 2, name, color="white", va="center", weight="bold")
    for i, c in enumerate(cols):
        ax.text(x + 0.01, y + h - LINE * (i + 1.5), c, va="center", fontsize=9)

arrows = [((0.28, 0.80), (0.38, 0.80), "1 : 1"),          # films -> trailers
          ((0.63, 0.75), (0.73, 0.75), "1 : many"),       # trailers -> youtube_comments
          ((0.15, 0.50), (0.15, 0.31), "1 : many")]       # films -> pageviews_daily
for (x1, y1), (x2, y2), label in arrows:
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", lw=1.3))
    ax.text((x1 + x2) / 2 + 0.01, (y1 + y2) / 2 + 0.015, label, fontsize=8, ha="center")

ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.set_title("ER diagram: release_radar database (MySQL)")
plt.tight_layout()
plt.savefig("charts/er_diagram.png", dpi=150)
plt.close()

# ---------- pipeline diagram ----------
steps = [
    ("Sources", ["Wikipedia pages\n(HTML tables)", "YouTube Data API\n(JSON + comment text)",
                 "Wikimedia pageviews\n(JSON, daily)", "IMDb 50K\n(text files)"]),
    ("Download\n01 to 05", ["data/raw/", "trailer picked by rule,\nchecked by hand"]),
    ("PySpark\n06_spark_text", ["drop empty, duplicates", "cast times", "clean text, length", "find script",
                                "terms, aspects by film"]),
    ("pandas\n07 to 09", ["parse ₹ crore, dates", "match film names", "fill pageview gaps", "VADER sentiment",
                          "one row per film"]),
    ("Outputs\n10 to 15", ["charts/", "spreadsheet check", "MySQL (4 tables)", "report, slides"]),
]
fig, ax = plt.subplots(figsize=(12, 4.6))
for i, (title, items) in enumerate(steps):
    x = 0.02 + i * 0.2
    ax.text(x + 0.08, 0.95, title, ha="center", va="top", weight="bold", fontsize=10)
    for j, item in enumerate(items):
        y = 0.74 - j * 0.15
        ax.add_patch(plt.Rectangle((x, y - 0.06), 0.16, 0.12, color="#dbe5f1"))
        ax.text(x + 0.08, y, item, ha="center", va="center", fontsize=8)
    if i < len(steps) - 1:
        ax.annotate("", xy=(x + 0.195, 0.45), xytext=(x + 0.165, 0.45),
                    arrowprops=dict(arrowstyle="->", lw=1.5))
ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
plt.tight_layout()
plt.savefig("charts/pipeline.png", dpi=150)
plt.close()
print("saved charts/er_diagram.png and charts/pipeline.png")
