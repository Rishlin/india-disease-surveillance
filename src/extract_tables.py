"""Step 9: pull the state-wise tables out of the NCVBDC PDFs into tidy CSV files."""
import re
from pathlib import Path

import pandas as pd
import pdfplumber

RAW = Path("data/raw")
OUT = Path("data/processed")
OUT.mkdir(parents=True, exist_ok=True)


def pdf_text(path):
    with pdfplumber.open(path) as pdf:
        return "\n".join((page.extract_text() or "") for page in pdf.pages)


# This state's name wraps over several lines in the PDF, so we find its row by serial number
FALLBACK_NAMES = {32: "The Dadra And Nagar Haveli And Daman And Diu"}


def extract_malaria(path, years):
    """Each state row has 4 numbers per year: tested, positive, Pf, deaths."""
    text = pdf_text(path).replace("\n", " ")
    n = 4 * len(years)
    num_block = r"((?:\d+\s+){%d}\d+)" % (n - 1)
    row = re.compile(r"\b(\d{1,2})\s+([A-Za-z][A-Za-z&\s]*?)\s+" + num_block)
    rows = {int(s): (" ".join(name.split()), nums) for s, name, nums in row.findall(text)}

    for serial in range(1, 37):
        if serial not in rows:
            m = re.search(r"\b%d\s+" % serial + num_block, text)
            if m and serial in FALLBACK_NAMES:
                rows[serial] = (FALLBACK_NAMES[serial], m.group(1))
            else:
                print("WARNING: could not read row", serial)
                i = text.find("Haveli")
                print(text[max(0, i - 200): i + 400])

    records = []
    for serial in sorted(rows):
        name, nums = rows[serial]
        nums = [int(x) for x in nums.split()]
        for i, year in enumerate(years):
            tested, positive, pf, deaths = nums[4 * i: 4 * i + 4]
            records.append({
                "state": name, "year": year, "disease": "Malaria",
                "cases": positive, "tested": tested, "pf_cases": pf, "deaths": deaths,
            })
    india = re.search(r"India\s+((?:\d+\s+){%d}\d+)" % (n - 1), text)
    india = [int(x) for x in india.group(1).split()]
    totals = {y: india[4 * i + 1] for i, y in enumerate(years)}
    return pd.DataFrame(records), totals


def extract_dengue(path):
    """Each state row has cases and deaths for 2021-2026. Some cells are special."""
    years = [2021, 2022, 2023, 2024, 2025, 2026]
    records, totals = [], {}
    for line in pdf_text(path).splitlines():
        tok = line.split()
        if not tok:
            continue
        if "Non endemic" in line:  # Ladakh has no numbers
            name = " ".join(t for t in tok if not t.isdigit()).replace("Non endemic", "").strip()
            for y in years:
                records.append({"state": name, "year": y, "disease": "Dengue",
                                "cases": None, "deaths": None, "status": "non_endemic"})
            continue
        if tok[0].isdigit() and len(tok) > 1 and not tok[1][0].isdigit():
            tok = tok[1:]  # drop the serial number
        i = 0
        while i < len(tok) and not re.match(r"\d|NR$", tok[i]):
            i += 1
        name, vals = " ".join(tok[:i]), tok[i:]
        if not name or len(vals) != 12:
            continue
        cases, deaths = vals[0::2], vals[1::2]
        if name == "TOTAL":
            totals = {y: int(c) for y, c in zip(years, cases)}
            continue
        for y, c, d in zip(years, cases, deaths):
            m = re.fullmatch(r"(\d+)(\*+)?", c)
            if m:
                n_cases = int(m.group(1))
                status = "partial_year" if m.group(2) else "ok"
            else:  # "NR" means not reported
                n_cases, status = None, "not_reported"
            n_deaths = int(re.sub(r"\D", "", d)) if re.search(r"\d", d) else None
            records.append({"state": name, "year": y, "disease": "Dengue",
                            "cases": n_cases, "deaths": n_deaths, "status": status})
    return pd.DataFrame(records), totals


if __name__ == "__main__":
    dengue, d_tot = extract_dengue(RAW / "dengue_2021_2026_ncvbdc.pdf")
    malaria, m_tot = extract_malaria(RAW / "malaria_from2022_ncvbdc.pdf", [2022, 2023, 2024, 2025, 2026])
    dengue.to_csv(OUT / "dengue_extracted.csv", index=False)
    malaria.to_csv(OUT / "malaria_extracted.csv", index=False)

    print("Dengue rows (expect 222):", len(dengue))
    print("Malaria rows (expect 180):", len(malaria))
    for name, df, tot in [("Dengue", dengue, d_tot), ("Malaria", malaria, m_tot)]:
        print(f"\n{name}: sum of states vs official India total")
        for y, t in tot.items():
            s = int(df.loc[df.year == y, "cases"].sum())
            print(y, "| sum:", s, "| official:", t, "| difference:", t - s)