# Step 15: turns report/report.md into report/report.docx (python-docx) and report.pdf (Apple Pages).
# The markdown uses only a few things, so we read it line by line:
# headings (#, ##, ###), paragraphs with **bold** and `code`, bullet and numbered lists,
# tables (| a | b |) and pictures (![](../charts/x.png)).

import os
import re
import subprocess
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

FONT = "Times New Roman"
BLUE = RGBColor(0x1F, 0x3A, 0x5F)

doc = Document()
for sec in doc.sections:
    sec.left_margin = sec.right_margin = Cm(2)
    sec.top_margin = sec.bottom_margin = Cm(1.8)
for name, size in [("Normal", 11), ("Title", 22), ("Heading 1", 15), ("Heading 2", 12.5), ("Heading 3", 11.5),
                   ("List Bullet", 11), ("List Number", 11)]:
    st = doc.styles[name]
    st.font.name, st.font.size = FONT, Pt(size)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    if name != "Normal" and not name.startswith("List"):
        st.font.color.rgb, st.font.bold = BLUE, True
doc.styles["Normal"].paragraph_format.space_after = Pt(5)


def add_text(p, text, size=None):
    """Write text into paragraph p, turning **bold** and `code` into formatted runs."""
    for part in re.split(r"(\*\*.+?\*\*|`.+?`)", text):
        if not part:
            continue
        if part.startswith("**"):
            run = p.add_run(part[2:-2]); run.bold = True
        elif part.startswith("`"):
            run = p.add_run(part[1:-1]); run.font.name = "Courier New"
        else:
            run = p.add_run(part)
        if size:
            run.font.size = Pt(size)


def borders(table):
    b = OxmlElement("w:tblBorders")
    for side in ["top", "left", "bottom", "right", "insideH", "insideV"]:
        e = OxmlElement(f"w:{side}")
        e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "4"); e.set(qn("w:color"), "8C8C8C")
        b.append(e)
    table._tbl.tblPr.append(b)


def add_table(rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    cells = [r for r in cells if not all(re.fullmatch(r":?-+:?", c) for c in r)]      # drop the |---| line
    t = doc.add_table(rows=len(cells), cols=len(cells[0]))
    borders(t)
    # column widths: a narrow "#" column if there is one, the rest shared equally (17 cm in all)
    n = len(cells[0])
    widths = [0.8] + [16.2 / (n - 1)] * (n - 1) if cells[0][0] == "#" else [17 / n] * n
    t.autofit = False
    for j, w in enumerate(widths):
        t.columns[j].width = Cm(w)
    for i, row in enumerate(cells):
        for j, value in enumerate(row):
            cell = t.cell(i, j)
            cell.width = Cm(widths[j])
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(1)
            add_text(p, value, size=9)
            if i == 0:
                for run in p.runs:
                    run.bold = True
                shd = OxmlElement("w:shd")
                shd.set(qn("w:val"), "clear"); shd.set(qn("w:fill"), "DCE6F1")
                cell._tc.get_or_add_tcPr().append(shd)
    doc.add_paragraph()


lines = open("report/report.md").read().splitlines()
i = 0
while i < len(lines):
    line = lines[i]
    if line.startswith("|"):                       # a table runs until the first non-table line
        rows = []
        while i < len(lines) and lines[i].startswith("|"):
            rows.append(lines[i]); i += 1
        add_table(rows)
        continue
    if line.startswith("# "):
        doc.add_paragraph(line[2:], style="Title").alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif line.startswith("## "):
        doc.add_heading(line[3:], level=1)
    elif line.startswith("### "):
        doc.add_heading(line[4:], level=2)
    elif line.strip() == "<!-- pagebreak -->":
        doc.add_page_break()
    elif line.startswith("!["):
        path = os.path.normpath(os.path.join("report", re.search(r"\((.+?)\)", line).group(1)))
        doc.add_picture(path, width=Cm(14))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif line.startswith("* "):
        add_text(doc.add_paragraph(style="List Bullet"), line[2:])
    elif re.match(r"\d+\. ", line):                # keep the number as written, so each list starts at 1
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.7)
        p.paragraph_format.first_line_indent = Cm(-0.5)
        add_text(p, line)
    elif line.strip():
        p = doc.add_paragraph()
        add_text(p, line)
        if i < 8:                                  # the title block lines are centred
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    i += 1
doc.save("report/report.docx")

# docx -> pdf with Apple Pages (comes with macOS; through AppleScript)
docx, pdf = os.path.abspath("report/report.docx"), os.path.abspath("report/report.pdf")
subprocess.run(["osascript", "-e", f'''
tell application "Pages"
    set d to open (POSIX file "{docx}")
    export d to (POSIX file "{pdf}") as PDF
    close d saving no
end tell'''], check=True)
print("built report/report.docx and report/report.pdf")
