# Step 11: the same cleaning step in a spreadsheet and in pandas, then compare.
# Step: turn Wikipedia's gross text ("₹797.34–809 crore", "est. ₹242.8 crore",
# "₹1,350.83–₹1,428 crore") into one number in crore, the midpoint of a range.
#   a) spreadsheet: SUBSTITUTE / FIND / MID / VALUE formulas (calculated by Microsoft Excel)
#   b) pandas: parse_money() in 07_clean.py, already in films_clean.csv
# openpyxl only writes formulas, it cannot calculate them, so Microsoft Excel opens the
# file, calculates it and hands the results back (macOS, through AppleScript).

import os
import subprocess
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font

films = pd.read_csv("data/clean/films_clean.csv")

wb = Workbook()
ws = wb.active
ws.title = "gross"
ws.append(["film_id", "gross_text (from Wikipedia)", "cleaned text", "low", "high", "gross_cr (midpoint)"])
for c in ws[1]:
    c.font = Font(bold=True)
for i, r in enumerate(films.itertuples(), start=2):
    ws.cell(i, 1, r.film_id)
    ws.cell(i, 2, r.gross_text)
    # C: drop ₹, commas, "est." and " crore", make every dash the same en dash, trim
    ws.cell(i, 3, f'=TRIM(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE('
                  f'B{i},"₹",""),",",""),"est.","")," crore",""),"−","–"))')
    # D: the number before the dash (or the only number)
    ws.cell(i, 4, f'=VALUE(TRIM(LEFT(C{i},FIND("–",C{i}&"–")-1)))')
    # E: the number after the dash, or the same number when there is no range
    ws.cell(i, 5, f'=IF(ISNUMBER(FIND("–",C{i})),VALUE(TRIM(MID(C{i},FIND("–",C{i})+1,99))),D{i})')
    ws.cell(i, 6, f"=(D{i}+E{i})/2")
for col, width in zip("ABCDEF", [14, 28, 20, 10, 10, 18]):
    ws.column_dimensions[col].width = width
wb.save("data/clean/gross_cleaning_spreadsheet.xlsx")

# let Excel open the file, calculate it and hand back column A and F as text
path = os.path.abspath("data/clean/gross_cleaning_spreadsheet.xlsx")
out = subprocess.run(["osascript", "-e", f'''
tell application "Microsoft Excel"
    open (POSIX file "{path}")
    set wb to active workbook
    calculate full
    set ws to worksheet "gross" of wb
    set txt to ""
    repeat with i from 2 to {len(films) + 1}
        set txt to txt & (value of range ("A" & i) of ws) & "|" & (value of range ("F" & i) of ws) & linefeed
    end repeat
    close wb saving no
    return txt
end tell'''], check=True, capture_output=True, text=True).stdout
excel = pd.DataFrame([line.split("|") for line in out.strip().splitlines()], columns=["film_id", "excel_gross_cr"])
excel["excel_gross_cr"] = pd.to_numeric(excel.excel_gross_cr, errors="coerce")
excel = excel.merge(films[["film_id", "gross_text"]])

both = excel[["film_id", "gross_text", "excel_gross_cr"]].merge(films[["film_id", "gross_cr"]])
both["difference"] = (both.excel_gross_cr - both.gross_cr).abs()
both.to_csv("data/clean/spreadsheet_vs_pandas.csv", index=False)
print(both.to_string())
print("films:", len(both), " largest difference (crore):", round(both.difference.max(), 6),
      " spreadsheet errors:", both.excel_gross_cr.isna().sum())
