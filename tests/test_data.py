"""Basic checks that the data pipeline output is sane."""
import pandas as pd
import pytest

from src.models import make_pairs

KNOWN_PROBLEM_STATES = {"West Bengal", "Ladakh"}


@pytest.fixture(scope="module")
def df():
    return pd.read_csv("data/processed/cases_per100k.csv")


def test_no_negative_cases(df):
    assert (df["cases"].dropna() >= 0).all()


def test_every_disease_has_36_states(df):
    assert df.groupby("disease")["state"].nunique().eq(36).all()


def test_years_covered(df):
    years = {k: sorted(g["year"].unique()) for k, g in df.groupby("disease")}
    assert years["Dengue"] == [2021, 2022, 2023, 2024, 2025]
    assert years["Malaria"] == [2022, 2023, 2024, 2025]


def test_rate_matches_formula(df):
    ok = df.dropna(subset=["cases", "population"])
    expected = ok["cases"] / ok["population"] * 100_000
    assert (ok["cases_per_100k"] - expected).abs().max() < 1e-6


def test_untrusted_rows_are_only_the_known_problems(df):
    bad = df[~df["usable"]]
    assert set(bad["state"]) <= KNOWN_PROBLEM_STATES
    assert (bad["disease"] == "Dengue").all()


def test_pairs_use_consecutive_years(df):
    pairs = make_pairs(df)
    keys = set(zip(df["disease"], df["state"], df["year"]))
    assert all((r.disease, r.state, r.year - 1) in keys for r in pairs.itertuples())