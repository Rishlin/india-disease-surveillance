"""Step 10b: read state populations from Table 21 and compute cases per 100,000."""
import re
from pathlib import Path

import pandas as pd
import pdfplumber

RAW = Path("data/raw")
PROCESSED = Path("data/processed")
DNHDD = "Dadra and Nagar Haveli and Daman and Diu"

# Table 21 spells some names differently. Keys are lower case, with '&' written as 'and'.
NAME_FIXES = {
    "jammu and kashmir (ut)": "Jammu and Kashmir",
    "jammu and kashmir": "Jammu and Kashmir",
    "uttaranchal": "Uttarakhand",
    "nct of delhi": "Delhi",
    "orissa": "Odisha",
    "chattisgarh": "Chhattisgarh",
    "pondicherry": "Puducherry",
    "dadra and nagar haveli": DNHDD,
    "daman and diu": DNHDD,
    "d and n haveli": DNHDD,
    "daman diu": DNHDD,
    "dadra nagar haveli": DNHDD,
}
ROW = re.compile(r"^(\d{1,2})\s+(.+?)\s+((?:[\d,]+\s+){8}[\d,]+)$")


def canonical(raw):
    raw = re.sub(r"^\d+\s+", "", raw.strip())  # drop a stray serial number
    key = re.sub(r"\s+", " ", raw.replace("&", "and").replace("*", "")).strip().lower()
    if key in NAME_FIXES:
        return NAME_FIXES[key]
    return key.title().replace(" And ", " and ").replace(" Of ", " of ")


def read_table(pdf, page_numbers):
    """Return {(state, year): persons in thousands} using the 'Persons' column of each year."""
    out = {}
    for pn in page_numbers:
        lines = [ln.strip() for ln in (pdf.pages[pn - 1].extract_text() or "").splitlines()]
        years = None
        for ln in lines:
            m = re.fullmatch(r"(20\d\d)\s+(20\d\d)\s+(20\d\d)", ln)
            if m:
                years = [int(y) for y in m.groups()]
        print(f"PDF page {pn}: years found = {years}")
        if not years:
            continue
        for ln in lines:
            m = ROW.match(ln)
            if m and re.search(r"[A-Za-z]", m.group(2)):
                nums = [int(x.replace(",", "")) for x in m.group(3).split()]
                name = canonical(m.group(2))
                for i, y in enumerate(years):
                    out[(name, y)] = out.get((name, y), 0) + nums[3 * i]  # Persons column
    return out


def load_population():
    with pdfplumber.open(RAW / "population_projections_2011_2036.pdf") as pdf:
        table = read_table(pdf, [263, 264])
    pop = pd.DataFrame([{"state": s, "year": y, "thousands": v} for (s, y), v in table.items()])
    wide = pop.pivot(index="state", columns="year", values="thousands")
    if 2021 not in wide.columns or 2026 not in wide.columns:
        raise SystemExit("Could not find both 2021 and 2026. Paste me what was printed above.")
    rows = []
    for state, r in wide.iterrows():
        for y in range(2021, 2026):
            est = r[2021] * (r[2026] / r[2021]) ** ((y - 2021) / 5) * 1000
            rows.append({"state": state, "year": y, "population": round(est)})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    pop = load_population()
    cases = pd.read_csv(PROCESSED / "cases_clean.csv")
    merged = cases.merge(pop, on=["state", "year"], how="left")

    missing = sorted(merged.loc[merged["population"].isna(), "state"].unique())
    print("\nStates with no population match:", missing or "none")
    print("Population-table names not in case data:", sorted(set(pop.state) - set(cases.state)) or "none")
    print("\nUttar Pradesh population estimates:")
    print(pop[pop.state == "Uttar Pradesh"].to_string(index=False))
    print("\nDadra/Daman combined estimates:")
    print(pop[pop.state == DNHDD].to_string(index=False))
    

    merged["cases_per_100k"] = merged["cases"] / merged["population"] * 100_000
    merged.to_csv(PROCESSED / "cases_per100k.csv", index=False)
    for disease in ["Dengue", "Malaria"]:
        top = (merged[(merged.disease == disease) & (merged.year == 2025) & merged.usable]
               .nlargest(5, "cases_per_100k")[["state", "cases", "population", "cases_per_100k"]])
        print(f"\nTop 5 {disease} states in 2025, per 100,000 people:")
        print(top.round(1).to_string(index=False))