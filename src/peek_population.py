"""Step 10b: find the pages that hold the state population table and show their headings."""
import re
from pathlib import Path

import pdfplumber

pdf_path = Path("data/raw/population_projections_2011_2036.pdf")
pattern = re.compile(r"09\s+Uttar\s+Pradesh\s+199,812")

with pdfplumber.open(pdf_path) as pdf:
    print("Total pages:", len(pdf.pages))
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        if pattern.search(text):
            lines = [ln for ln in text.splitlines() if ln.strip()]
            print("\n=== PDF page", i + 1, "===")
            print("\n".join(lines[:6]))
            print("   ...")
            print("\n".join(lines[-4:]))
            up = [ln for ln in lines if "Uttar Pradesh" in ln]
            print("UP line:", up[:1])