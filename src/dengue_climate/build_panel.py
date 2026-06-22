"""Build the unified analysis panel.

Joins the dengue panel, the monthly climate table, and the district elevation
reference into one tidy district-month table — the single input to all later
analysis. Writes ``data/processed/analysis_panel.csv`` plus a per-band summary,
and prints a data-quality report.

"""

import pandas as pd

from dengue_climate.config import PROJECT_ROOT, get_path, load_config

# Final column order (the schema every later phase reads).
PANEL_COLUMNS = [
    "district",
    "province",
    "elevation_m",
    "elevation_band",
    "year",
    "month",
    "cases",
    "precip",
    "temp_mean",
    "temp_max",
    "temp_min",
    "humidity",
]

# climate_monthly column -> panel column. RH_2m (relative humidity %) is the
# analysis "humidity"; the specific-humidity column is not carried.
CLIMATE_RENAME = {
    "Precip": "precip",
    "Temp_2m": "temp_mean",
    "MaxTemp_2m": "temp_max",
    "MinTemp_2m": "temp_min",
    "RH_2m": "humidity",
}


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load and tidy the three inputs to the panel schema's names/years."""
    years = load_config()["study"]["years"]

    dengue = pd.read_csv(get_path("dengue_monthly")).rename(
        columns={
            "Province": "province",
            "District": "district",
            "Year": "year",
            "Month": "month",
        }
    )

    climate = pd.read_csv(get_path("climate_monthly"))
    climate = climate[climate["year"].isin(years)].rename(columns=CLIMATE_RENAME)
    climate = climate[["district", "year", "month", *CLIMATE_RENAME.values()]]

    elevation = pd.read_csv(get_path("district_elevation"))[
        ["district", "elevation_m", "elevation_band"]
    ]
    return dengue, climate, elevation


def build_panel(dengue, climate, elevation) -> pd.DataFrame:
    """Join dengue ⨝ climate on (district, year, month), then attach elevation."""
    panel = dengue.merge(climate, on=["district", "year", "month"], how="inner")
    panel = panel.merge(elevation, on="district", how="left")
    return panel[PANEL_COLUMNS].sort_values(
        ["district", "year", "month"], ignore_index=True
    )


def quality_report(panel: pd.DataFrame, dengue, climate) -> None:
    """Print row/null/band checks and hard-assert the panel's integrity."""
    n_districts = panel["district"].nunique()
    expected = n_districts * len(load_config()["study"]["years"]) * 12

    print("\n=== Data-quality report ===")
    print(
        f"panel rows        : {len(panel)}  (expected {expected} = {n_districts}×3×12)"
    )
    print(f"districts         : {n_districts}")
    print(
        f"dengue rows in     : {len(dengue)} | climate (study) rows in: {len(climate)}"
    )

    nulls = panel.isna().sum()
    print("\nnull counts per column:")
    print(nulls.to_string())

    print("\ndistricts per elevation band:")
    print(
        panel.groupby("elevation_band", observed=True)["district"].nunique().to_string()
    )

    assert not panel.duplicated(["district", "year", "month"]).any(), (
        "duplicate (district, year, month) rows"
    )
    assert len(panel) == expected, f"row count {len(panel)} != expected {expected}"
    assert panel.notna().all().all(), f"unexpected nulls:\n{nulls[nulls > 0]}"
    print("\n✓ no duplicates, no nulls, expected row count")


def write_band_summary(panel: pd.DataFrame) -> None:
    """Write counts and means per elevation band to outputs/tables."""
    summary = (
        panel.groupby("elevation_band", observed=True)
        .agg(
            districts=("district", "nunique"),
            rows=("district", "size"),
            mean_cases=("cases", "mean"),
            mean_precip=("precip", "mean"),
            mean_temp=("temp_mean", "mean"),
            mean_humidity=("humidity", "mean"),
        )
        .round(1)
        .reset_index()
    )
    out_path = get_path("tables") / "panel_summary.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out_path, index=False)
    print(f"\nwrote {out_path.relative_to(PROJECT_ROOT)}")
    print(summary.to_string(index=False))


def main() -> None:
    dengue, climate, elevation = load_inputs()
    panel = build_panel(dengue, climate, elevation)

    out_path = get_path("analysis_panel")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(out_path, index=False)
    print(f"wrote {out_path.relative_to(PROJECT_ROOT)} ({len(panel)} rows)")

    quality_report(panel, dengue, climate)
    write_band_summary(panel)


if __name__ == "__main__":
    main()
