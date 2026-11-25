# Step 14: builds slides/release_day_radar_slides.pptx (10 slides, one idea each) and a PDF copy (Keynote, through AppleScript).

import os
import subprocess
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.33), Inches(7.5)
BLANK = prs.slide_layouts[6]
DARK = RGBColor(0x22, 0x22, 0x22)
BLUE = RGBColor(0x38, 0x6C, 0xB0)


def text_box(slide, text, left, top, width, height, size=20, bold=False, color=DARK):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    box.text_frame.word_wrap = True
    for i, line in enumerate(text.split("\n")):
        p = box.text_frame.paragraphs[0] if i == 0 else box.text_frame.add_paragraph()
        p.text = line
        p.font.size, p.font.bold, p.font.color.rgb = Pt(size), bold, color
        p.space_after = Pt(8)


def slide(title, bullets="", image=None, note=""):
    s = prs.slides.add_slide(BLANK)
    text_box(s, title, 0.5, 0.3, 12.3, 1.0, size=30, bold=True, color=BLUE)
    if image:
        pic = s.shapes.add_picture(image, Inches(0.5), Inches(1.4), width=Inches(8.3))
        if pic.height > Inches(5.6):          # tall charts: shrink to fit the slide
            pic.width = int(pic.width * Inches(5.6) / pic.height)
            pic.height = Inches(5.6)
        text_box(s, bullets, 9.1, 1.6, 3.9, 5.5, size=17)
    else:
        text_box(s, bullets, 0.8, 1.6, 11.8, 5.5, size=22)
    if note:
        text_box(s, note, 0.5, 6.8, 12.3, 0.5, size=12, color=RGBColor(0x77, 0x77, 0x77))


slide("Trailer views don't predict box office. Likes and opening-weekend interest do.",
      "1. Trailer views barely track worldwide gross (rank r = 0.15, 21 films of 2025).\n"
      "2. Trailer likes (0.58) and Wikipedia views in the opening 3 days (0.59) track it best.\n"
      "3. Every film whose week-2 interest fell to 37% of week 1 or less was a flop.\n\n"
      "We ask: plan screens on likes, check opening-weekend views on Monday, "
      "and cut screens when week-2 interest collapses.",
      note="Rahul Patnaik, Vishal P Joy, Ansh Ravi Kashyap, Pratyush RB. 28 Hindi and South Indian films, 2025 to 2026")

slide("The question",
      "Did online buzz around a film's trailer and release predict how much it grossed?\n\n"
      "Every Monday the Head of Distribution decides: add screens, cut screens, or spend more on promotion.\n\n"
      "Buzz arrives days before box-office numbers. If it lines up with the gross, the desk can act within 72 hours.\n\n"
      "28 films: 21 from 2025 to find patterns, 7 from 2026 kept aside to test them.")

slide("Four sources, three shapes of data",
      "Wikipedia film pages: release date, budget, worldwide gross (HTML tables)\n"
      "YouTube Data API: trailer views and likes, 32,522 top comments (JSON + text)\n"
      "Wikipedia pageviews API: daily interest in each film, 1,924 film-days (JSON)\n"
      "IMDb 50K reviews: to test our sentiment method (text)\n\n"
      "Variety dominated: HTML, nested JSON, and comments in six scripts.\n"
      "PySpark cleaned and counted 82,520 text rows.")

slide("The hard part was making the sources line up",
      "Same film, many names: \"L2: Empuraan\" vs \"L2E Empuraan Trailer\"\n\n"
      "Money as text: \"₹1,350.83–₹1,428 crore\"\n\n"
      "Search found Netflix and dubbed trailers: 7 of 28 fixed by hand\n\n"
      "Renamed Wikipedia pages: 21 of 28; Saiyaara's whole release week sat under an old title\n\n"
      "VADER read 🔥 as negative: fixed, 🔥 comments moved from -0.28 to +0.72")

slide("Likes and opening-weekend interest track gross, raw views barely do",
      "Trailer views: 0.15, no better than chance\n\n"
      "Trailer likes: 0.58\n\n"
      "Opening 3 days on Wikipedia: 0.59\n\n"
      "A view can be bought; a like or a Wikipedia visit takes a decision.",
      image="charts/02_signal_strength.png")

slide("South Indian films don't follow their trailer views",
      "Hindi: views and gross line up (r = 0.71)\n\n"
      "South Indian: no link (r = 0.07)\n\n"
      "₹151 gross per view for South Indian films, ₹53 for Hindi\n\n"
      "Likely cause: audiences watch dubbed and fan uploads too",
      image="charts/01_views_vs_gross.png")

slide("Interest halves within a week, unless word of mouth is strong",
      "Typical film peaks the day after release\n\n"
      "Saiyaara, Lokah, Dhurandhar kept climbing into week 2\n\n"
      "All 6 films that fell to 37% or less in week 2 were flops",
      image="charts/03_buzz_decay.png",
      note="Each film scaled 0 to 1 so big and small films share one picture.")

slide("Tested on 2026: a fair guide, not a crystal ball",
      "Buzz index called 6 of 7 films on the right side of the median\n\n"
      "Typically 1.4x off\n\n"
      "Nothing saw how big Dhurandhar: The Revenge would be",
      image="charts/04_test_2026.png",
      note="Fitted on the 21 films of 2025 only. 7 films is a small test.")

slide("What the desk can do next Friday",
      "1. Before release: judge trailers by likes, not views. Never compare South Indian and Hindi trailers on views.\n\n"
      "2. Monday morning: check opening-weekend Wikipedia views against the film's forecast. "
      "Well above it means add screens.\n\n"
      "3. Second Friday: if week-2 interest has fallen to 37% of week 1 or less, cut screens and hold promotion money. "
      "Above 60% with a real opening, back the word of mouth.\n\n"
      "The 37% line is a rule of thumb found on these 28 films: War 2 held 39% and also flopped.")

slide("How far you can trust this",
      "28 films, 7 in the test. One giant sequel can move the numbers.\n\n"
      "Correlation, not cause. No screen counts, no star or date effects measured.\n\n"
      "English Wikipedia and YouTube commenters are young and urban.\n\n"
      "VADER is 70% right on IMDb and weak on criticism and Hinglish.\n\n"
      "Thank you. Questions?")

os.makedirs("slides", exist_ok=True)
prs.save("slides/release_day_radar_slides.pptx")
print("saved", len(prs.slides), "slides")

# pptx -> pdf with Keynote (comes with macOS)
pptx, pdf = os.path.abspath("slides/release_day_radar_slides.pptx"), os.path.abspath("slides/release_day_radar_slides.pdf")
subprocess.run(["osascript", "-e", f'''
tell application "Keynote"
    set d to open (POSIX file "{pptx}")
    export d to (POSIX file "{pdf}") as PDF
    close d saving no
end tell'''], check=True)
print("built slides/release_day_radar_slides.pdf")
