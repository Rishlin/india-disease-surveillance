"""Step 12: can a simple model beat 'same as last year'? Rolling-origin backtest."""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

PROCESSED = Path("data/processed")
TEST_YEARS = {"Dengue": [2023, 2024, 2025], "Malaria": [2024, 2025]}


def make_pairs(df):
    """One row per state-year, with last year's cases next to this year's cases."""
    df = df[df["usable"]].sort_values(["disease", "state", "year"]).copy()
    grp = df.groupby(["disease", "state"])
    df["lag_cases"] = grp["cases"].shift(1)
    prev_year = grp["year"].shift(1)
    df = df[(prev_year == df["year"] - 1) & df["lag_cases"].notna()].copy()  # consecutive years only
    df["x"] = np.log1p(df["lag_cases"])
    df["y"] = np.log1p(df["cases"])
    return df


def scores(actual, predicted):
    err = np.abs(actual - predicted)
    return err.mean(), err.sum() / actual.sum() * 100  # MAE, WAPE (%)


def backtest(pairs):
    """For each test year, train only on earlier years, then compare with the baseline."""
    rows = []
    for disease, years in TEST_YEARS.items():
        d = pairs[pairs["disease"] == disease]
        for t in years:
            train, test = d[d["year"] < t], d[d["year"] == t]
            if len(train) < 20 or test.empty:
                continue
            model = LinearRegression().fit(train[["x"]], train["y"])
            actual = test["cases"].to_numpy()
            pred_model = np.expm1(model.predict(test[["x"]]))
            pred_base = test["lag_cases"].to_numpy()  # baseline: same as last year
            mae_b, wape_b = scores(actual, pred_base)
            mae_m, wape_m = scores(actual, pred_model)
            rows.append({
                "disease": disease, "test_year": t, "n_states": len(test),
                "MAE_baseline": round(mae_b), "MAE_model": round(mae_m),
                "WAPE_baseline_%": round(wape_b, 1), "WAPE_model_%": round(wape_m, 1),
                "model_wins": wape_m < wape_b,
            })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = pd.read_csv(PROCESSED / "cases_per100k.csv")
    pairs = make_pairs(df)
    print("Usable (state, year) pairs per disease:")
    print(pairs.groupby("disease").size())

    results = backtest(pairs)
    print("\nBacktest: model vs 'same as last year' baseline")
    print(results.to_string(index=False))
    results.to_csv(PROCESSED / "backtest_results.csv", index=False)

    print("\nWhat the model learned (all data): log(cases) = intercept + slope * log(last year's cases)")
    for disease, d in pairs.groupby("disease"):
        m = LinearRegression().fit(d[["x"]], d["y"])
        print(f"{disease}: intercept = {m.intercept_:.2f}, slope = {m.coef_[0]:.2f}")