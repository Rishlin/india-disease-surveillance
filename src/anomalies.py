"""Step 13: flag unusual state-years and forecast next year with an uncertainty band."""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from models import make_pairs

PROCESSED = Path("data/processed")

# Chosen from the Step 12 backtest: for dengue the model won 2 of 3 tests (one by a hair),
# while for malaria the baseline 'same as last year' won both tests.
METHOD = {"Dengue": "model", "Malaria": "baseline"}
MIN_CASES = 50   # ignore tiny counts, where big swings are just noise
Z_CUTOFF = 2.0   # how many 'typical errors' away counts as unusual


def fit_predictor(d, method):
    """Return a function that turns last year's log-cases into this year's expected log-cases."""
    if method == "model":
        lr = LinearRegression().fit(d[["x"]], d["y"])
        return lambda x: lr.predict(pd.DataFrame({"x": np.asarray(x, dtype=float)}))
    return lambda x: np.asarray(x, dtype=float)  # baseline: same as last year


if __name__ == "__main__":
    df = pd.read_csv(PROCESSED / "cases_per100k.csv")
    pairs = make_pairs(df)
    scored, forecasts = [], []

    for disease, d in pairs.groupby("disease"):
        predict = fit_predictor(d, METHOD[disease])
        expected = predict(d["x"].to_numpy())
        resid = d["y"].to_numpy() - expected
        sigma = resid.std(ddof=1)
        print(f"{disease}: method = {METHOD[disease]}, typical error = {sigma:.2f} (log units)")

        out = d[["state", "disease", "year", "cases", "lag_cases"]].copy()
        out["expected"] = np.expm1(expected).round()
        out["z_score"] = resid / sigma
        scored.append(out)

        # Forecast 2026 from each state's usable 2025 value
        last = df[(df.disease == disease) & (df.year == 2025) & df.usable].copy()
        mid = predict(np.log1p(last["cases"].to_numpy()))
        last["forecast_2026"] = np.expm1(mid).round()
        last["low_80"] = np.expm1(mid - 1.28 * sigma).round()
        last["high_80"] = np.expm1(mid + 1.28 * sigma).round()
        forecasts.append(last[["state", "disease", "cases", "forecast_2026", "low_80", "high_80"]]
                         .rename(columns={"cases": "cases_2025"}))

    res = pd.concat(scored, ignore_index=True)
    big_enough = res[["cases", "lag_cases"]].max(axis=1) >= MIN_CASES
    res["unusual"] = (res["z_score"].abs() >= Z_CUTOFF) & big_enough
    res["direction"] = np.where(res["z_score"] > 0, "higher than expected", "lower than expected")
    res.to_csv(PROCESSED / "anomalies.csv", index=False)
    fc = pd.concat(forecasts, ignore_index=True)
    fc.to_csv(PROCESSED / "forecast_2026.csv", index=False)

    print(f"\nUnusual state-years (|z| >= {Z_CUTOFF}, at least {MIN_CASES} cases): "
          f"{int(res.unusual.sum())} of {len(res)}")
    cols = ["disease", "state", "year", "cases", "expected", "z_score", "direction"]
    flagged = res[res.unusual].sort_values("z_score", key=lambda s: s.abs(), ascending=False)
    print(flagged[cols].round(1).to_string(index=False))

    print("\nForecast for 2026 (with an 80% range), five largest per disease:")
    for disease, g in fc.groupby("disease"):
        print(g.nlargest(5, "forecast_2026").to_string(index=False))