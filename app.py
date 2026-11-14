"""India Disease Surveillance Dashboard: dengue and malaria by state (NCVBDC data)."""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATA = Path("data/processed")

st.set_page_config(page_title="India Disease Surveillance Dashboard", layout="wide")


@st.cache_data
def load():
    cases = pd.read_csv(DATA / "cases_per100k.csv")
    anomalies = pd.read_csv(DATA / "anomalies.csv")
    forecast = pd.read_csv(DATA / "forecast_2026.csv")
    backtest = pd.read_csv(DATA / "backtest_results.csv")
    return cases, anomalies, forecast, backtest


cases, anomalies, forecast, backtest = load()

# ---------- Sidebar ----------
st.sidebar.header("Filters")
disease = st.sidebar.selectbox("Disease", sorted(cases["disease"].unique()))
d = cases[(cases["disease"] == disease) & cases["usable"]]
years = sorted(d["year"].unique())
year = st.sidebar.selectbox("Year", years, index=len(years) - 1)
metric_label = st.sidebar.radio("Measure", ["Cases per 100,000", "Reported cases"])
metric = "cases_per_100k" if metric_label == "Cases per 100,000" else "cases"

# ---------- Header and key numbers ----------
st.title("India Disease Surveillance Dashboard")
st.caption("Reported dengue and malaria cases by state (NCVBDC, Ministry of Health and Family Welfare), "
           "with population-adjusted rates, unusual-year detection and a 2026 outlook.")

this_year = d[d["year"] == year]
flags = anomalies[(anomalies["disease"] == disease) & (anomalies["year"] == year) & anomalies["unusual"]]
top = this_year.loc[this_year[metric].idxmax()]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Reported cases (usable states)", f"{int(this_year['cases'].sum()):,}")
c2.metric(f"Highest: {metric_label.lower()}", top["state"])
c3.metric("States with usable data", this_year["state"].nunique())
c4.metric("Unusual state-years flagged", len(flags))
st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Overview", "Trends", "Unusual years", "2026 outlook", "Data and method"])

# ---------- Overview ----------
with tab1:
    n = st.slider("Number of states to show", 5, 20, 12)
    show = this_year.nlargest(n, metric).sort_values(metric)
    fig = px.bar(show, x=metric, y="state", orientation="h",
                 hover_data={"cases": ":,", "population": ":,", "cases_per_100k": ":.1f"},
                 labels={metric: metric_label, "state": ""},
                 title=f"{disease}, {year}: top {n} states by {metric_label.lower()}")
    st.plotly_chart(fig, width="stretch")
    st.caption("Small populations make rates jump with only a few cases, so check the case count in the hover text.")

# ---------- Trends ----------
with tab2:
    default = list(this_year.nlargest(5, metric)["state"])
    chosen = st.multiselect("States", sorted(d["state"].unique()), default=default)
    if chosen:
        fig = px.line(d[d["state"].isin(chosen)], x="year", y=metric, color="state", markers=True,
                      labels={metric: metric_label, "year": "Year"})
        fig.update_xaxes(dtick=1)
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("Pick at least one state.")
    st.caption("Partial or unreported years are left out of the charts, so a line may skip a year.")

# ---------- Unusual years ----------
with tab3:
    st.write("A state-year is flagged when its cases are far from what the model expected "
             "(at least 2 typical errors away, and at least 50 cases). A flag shows where to look. "
             "It does not prove an outbreak: it can also come from changes in testing or reporting.")
    a = anomalies[anomalies["disease"] == disease]
    if st.checkbox("Only the selected year", value=False):
        a = a[a["year"] == year]
    table = a[a["unusual"]].sort_values("z_score", key=lambda s: s.abs(), ascending=False)
    if table.empty:
        st.info("No unusual state-years for this selection.")
    else:
        st.dataframe(table[["state", "year", "cases", "expected", "z_score", "direction"]].round(1),
                     hide_index=True, width="stretch")
    fig = px.scatter(a, x="expected", y="cases", color="unusual", log_x=True, log_y=True,
                     hover_data=["state", "year"],
                     labels={"expected": "Expected cases", "cases": "Actual cases"},
                     title="Actual vs expected cases (log scale)")
    st.plotly_chart(fig, width="stretch")

# ---------- 2026 outlook ----------
with tab4:
    f = forecast[forecast["disease"] == disease].copy()
    st.warning("These ranges are wide on purpose. With only a few years of data, next year cannot be "
               "predicted precisely, so read them as a plausible range and not a promise.")
    method = ("a regression model that pulls extreme years back toward typical levels"
              if disease == "Dengue" else "'same as last year'")
    st.write(f"Method for {disease}: **{method}**, chosen from the backtest on the 'Data and method' tab.")
    n2 = st.slider("States to show", 5, 20, 10, key="n2")
    show = f.nlargest(n2, "forecast_2026").sort_values("forecast_2026")
    show["above"] = show["high_80"] - show["forecast_2026"]
    show["below"] = show["forecast_2026"] - show["low_80"]
    fig = px.scatter(show, x="forecast_2026", y="state", error_x="above", error_x_minus="below",
                     labels={"forecast_2026": "Estimated cases in 2026", "state": ""})
    fig.data[0].name = "2026 estimate (80% range)"
    fig.data[0].showlegend = True
    fig.add_scatter(x=show["cases_2025"], y=show["state"], mode="markers", name="2025 reported",
                    marker_symbol="diamond")
    st.plotly_chart(fig, width="stretch")
    st.dataframe(f.sort_values("forecast_2026", ascending=False), hide_index=True, width="stretch")

# ---------- Data and method ----------
with tab5:
    st.subheader("Does the model beat 'same as last year'?")
    st.write("Each row trains only on earlier years, then predicts the test year. "
             "WAPE is the total error as a percentage of total actual cases (lower is better).")
    st.dataframe(backtest, hide_index=True, width="stretch")
    st.subheader("Data")
    st.markdown(
        "- **Cases:** NCVBDC state-wise dengue (2021-2025) and malaria (2022-2025) tables.\n"
        "- **Population:** Census 2011 based projections (National Commission on Population, 2020); "
        "values for 2022-2025 are estimated between the 2021 and 2026 projections.\n"
        "- **Not used:** West Bengal dengue 2023-2025 (partial or not reported) and Ladakh dengue (non-endemic).")
    st.subheader("Limitations")
    st.markdown(
        "- Reported cases under-count the true burden, and testing and reporting change over time.\n"
        "- Only 4-5 yearly values per state, so the models are deliberately simple.\n"
        "- Rates for small populations are unstable.\n"
        "- Flags and forecasts are decision aids, not diagnoses.")

st.divider()
st.caption("Data: NCVBDC, Ministry of Health and Family Welfare. A student project, not an official surveillance tool.")