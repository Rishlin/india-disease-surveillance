"""Step 10a: clean state names, drop the partial year, and combine dengue + malaria."""
from pathlib import Path

import pandas as pd

PROCESSED = Path("data/processed")
DNHDD = "Dadra and Nagar Haveli and Daman and Diu"

NAME_FIXES = {
    "A&N Islands": "Andaman and Nicobar Islands",
    "Andaman And Nicobar Islands": "Andaman and Nicobar Islands",
    "J&K": "Jammu and Kashmir",
    "Jammu And Kashmir": "Jammu and Kashmir",
    "D&N Haveli": DNHDD,
    "Daman & Diu": DNHDD,
    "The Dadra And Nagar Haveli And Daman And Diu": DNHDD,
}
YEARS = [2021, 2022, 2023, 2024, 2025]  # 2026 is a partial year, so it is excluded


def first_issue(statuses):
    """If any merged row has a problem, keep that problem; otherwise 'ok'."""
    bad = [s for s in statuses if s != "ok"]
    return bad[0] if bad else "ok"


def load_clean():
    dengue = pd.read_csv(PROCESSED / "dengue_extracted.csv")
    malaria = pd.read_csv(PROCESSED / "malaria_extracted.csv")
    malaria["status"] = "ok"

    df = pd.concat([dengue, malaria], ignore_index=True)
    df["state"] = df["state"].str.strip().replace(NAME_FIXES)
    df = df[df["year"].isin(YEARS)]

    # Daman & Diu and D&N Haveli now share one name, so add them together
    df = df.groupby(["state", "disease", "year"], as_index=False).agg(
        cases=("cases", lambda s: s.sum(min_count=1)),
        deaths=("deaths", lambda s: s.sum(min_count=1)),
        tested=("tested", "first"),
        pf_cases=("pf_cases", "first"),
        status=("status", first_issue),
    )
    df["usable"] = df["status"].eq("ok")
    return df


if __name__ == "__main__":
    df = load_clean()
    df.to_csv(PROCESSED / "cases_clean.csv", index=False)
    print("States per disease:")
    print(df.groupby("disease")["state"].nunique())
    print("\nRows per disease:")
    print(df.groupby("disease").size())
    print("\nRows we should NOT trust (partial, missing, non-endemic):")
    print(df.loc[~df["usable"], ["state", "disease", "year", "cases", "status"]].to_string(index=False))