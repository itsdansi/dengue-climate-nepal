"""Dengue × Climate in Nepal — a minimalist findings + exploration dashboard.

Reads the already-built analysis artifacts (the joined panel, summary tables,
and pre-rendered figures) through the project's config path helpers, so it works
regardless of the directory Streamlit is launched from. It computes nothing new:
the narrative tabs reuse the report's figures, and the Explore tab slices the
panel live.

Run (project venv console scripts are stale, so go through the module):

    uv run python -m streamlit run dashboard/app.py
"""

import altair as alt
import pandas as pd
import streamlit as st

from dengue_climate.config import get_path

ACCENT = "#0E7C7B"
MUTED = "#9AA0A6"
MONTHS = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}
CLIMATE_VARS = {
    "precip": "Rainfall (mm)",
    "temp_mean": "Mean temp (°C)",
    "temp_max": "Max temp (°C)",
    "temp_min": "Min temp (°C)",
    "humidity": "Humidity (%)",
}


# --------------------------------------------------------------------------- #
# data access
# --------------------------------------------------------------------------- #
@st.cache_data
def load_panel() -> pd.DataFrame:
    """The district × month analysis panel, with a parsed date column."""
    df = pd.read_csv(get_path("analysis_panel"))
    df["date"] = pd.to_datetime(dict(year=df["year"], month=df["month"], day=1))
    return df


@st.cache_data
def load_table(name: str) -> pd.DataFrame:
    """Read one CSV from outputs/tables/ by stem (e.g. 'panel_summary')."""
    return pd.read_csv(get_path("tables") / f"{name}.csv")


def figure(name: str) -> str:
    """Absolute path to a pre-rendered figure in outputs/figures/."""
    return str(get_path("figures") / f"{name}.png")


def show_figure(name: str) -> None:
    """Render a full-width figure inside a centered column so it stays
    on-screen on wide layouts instead of stretching edge to edge."""
    _, mid, _ = st.columns([1, 2, 1])
    mid.image(figure(name), use_container_width=True)


# --------------------------------------------------------------------------- #
# tabs
# --------------------------------------------------------------------------- #
def overview_tab(panel: pd.DataFrame) -> None:
    total = int(panel["cases"].sum())
    by_month = panel.groupby("month")["cases"].sum()
    peak_month = MONTHS[int(by_month.idxmax())]
    by_district = panel.groupby("district")["cases"].sum().sort_values(ascending=False)
    top5_share = by_district.head(5).sum() / total if total else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total cases", f"{total:,}")
    c2.metric("Peak month", peak_month)
    c3.metric("Districts", f"{panel['district'].nunique()}")
    c4.metric("Top-5 district share", f"{top5_share:.0%}")

    st.caption(
        f"{panel['province'].nunique()} provinces · "
        f"{panel['year'].min()}-{panel['year'].max()} · monthly resolution"
    )

    show_figure("dengue_national_trend")

    st.subheader("By elevation band")
    summary = load_table("panel_summary")
    st.dataframe(summary, hide_index=True, use_container_width=True)


def climate_lag_tab() -> None:
    st.markdown(
        "Dengue tracks the monsoon, and the climate signal **leads** cases by a "
        "month or two — strongest in the higher elevation bands."
    )
    show_figure("cases_climate_overlay")

    left, right = st.columns(2)
    left.image(figure("seasonality_by_band"), use_container_width=True)
    right.image(figure("correlation_heatmap"), use_container_width=True)

    st.subheader("Climate leads cases")
    show_figure("lag_correlation")
    st.caption("Best-lag (months) per climate variable and elevation band:")
    st.dataframe(load_table("lag_best"), hide_index=True, use_container_width=True)

    st.subheader("Model: what drives the case count")
    show_figure("predicted_vs_actual_2024")
    st.markdown(
        "A negative-binomial model with lagged climate × elevation interactions. "
        "Each row is an **incidence rate ratio** — values above 1 raise expected "
        "cases. Lagged minimum temperature and humidity, and rainfall in the "
        "Hill/Mountain bands, are the headline drivers."
    )
    coef = load_table("model_coefficients").rename(
        columns={
            "term": "Term",
            "irr": "IRR",
            "ci_low": "95% CI low",
            "ci_high": "95% CI high",
            "p_value": "p",
        }
    )
    st.dataframe(coef, hide_index=True, use_container_width=True)


def explore_tab(panel: pd.DataFrame) -> None:
    bands = ["All"] + sorted(panel["elevation_band"].unique())
    band = st.radio("Elevation band", bands, horizontal=True)
    scope = panel if band == "All" else panel[panel["elevation_band"] == band]

    ranked = scope.groupby("district")["cases"].sum().sort_values(ascending=False)
    districts = st.multiselect(
        "Districts",
        options=list(ranked.index),
        default=list(ranked.head(5).index),
        help="Defaults to the five highest-burden districts in the selected band.",
    )
    years = st.multiselect(
        "Years",
        options=sorted(panel["year"].unique()),
        default=sorted(panel["year"].unique()),
    )
    var = st.selectbox(
        "Climate variable",
        options=list(CLIMATE_VARS),
        format_func=lambda v: CLIMATE_VARS[v],
    )

    sel = scope[scope["district"].isin(districts) & scope["year"].isin(years)]
    if sel.empty:
        st.info("Select at least one district and year to see charts.")
        return

    # Monthly aggregate: cases sum across the selection, climate averaged.
    agg = (
        sel.groupby("date")
        .agg(cases=("cases", "sum"), climate=(var, "mean"))
        .reset_index()
    )

    st.subheader("Monthly cases")
    cases_chart = (
        alt.Chart(agg)
        .mark_area(line={"color": ACCENT}, color=ACCENT, opacity=0.15)
        .encode(
            x=alt.X("date:T", title=None),
            y=alt.Y("cases:Q", title="Cases"),
            tooltip=["date:T", "cases:Q"],
        )
        .properties(height=260)
    )
    st.altair_chart(cases_chart, use_container_width=True)

    st.subheader(f"Cases vs {CLIMATE_VARS[var]}")
    base = alt.Chart(agg).encode(x=alt.X("date:T", title=None))
    cases_line = base.mark_line(color=ACCENT).encode(
        y=alt.Y("cases:Q", title="Cases", axis=alt.Axis(titleColor=ACCENT)),
        tooltip=["date:T", "cases:Q"],
    )
    clim_line = base.mark_line(color=MUTED, strokeDash=[4, 3]).encode(
        y=alt.Y("climate:Q", title=CLIMATE_VARS[var], axis=alt.Axis(titleColor=MUTED)),
        tooltip=["date:T", alt.Tooltip("climate:Q", title=CLIMATE_VARS[var])],
    )
    dual = alt.layer(cases_line, clim_line).resolve_scale(y="independent").properties(
        height=260
    )
    st.altair_chart(dual, use_container_width=True)

    st.subheader("Filtered data")
    table = sel[
        ["district", "elevation_band", "year", "month", "cases", *CLIMATE_VARS]
    ].sort_values(["district", "year", "month"])
    st.dataframe(table, hide_index=True, use_container_width=True)
    st.download_button(
        "Download CSV",
        table.to_csv(index=False).encode("utf-8"),
        file_name="dengue_climate_selection.csv",
        mime="text/csv",
    )


# --------------------------------------------------------------------------- #
# pagepage
# --------------------------------------------------------------------------- #
def main() -> None:
    st.set_page_config(
        page_title="Dengue × Climate in Nepal",
        page_icon="🦟",
        layout="wide",
    )
    st.title("Dengue × Climate in Nepal")
    st.caption("How rainfall, temperature, and humidity track dengue across elevation, 2022–2024.")

    panel = load_panel()
    overview, climate, explore = st.tabs(["Overview", "Climate & Lag", "Explore"])
    with overview:
        overview_tab(panel)
    with climate:
        climate_lag_tab()
    with explore:
        explore_tab(panel)


if __name__ == "__main__":
    main()
