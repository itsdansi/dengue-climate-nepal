"""Phase 2 — build the monthly district dengue panel from OpenDengue.

OpenDengue is used as the single source (EDCD PDF extraction is skipped — a
sanctioned simplification since 2025 is out of scope). The raw Nepal export
mixes spatial/temporal resolutions; we keep only the Admin2 + monthly rows for
the study years, tidy the columns, and write
``data/processed/dengue_monthly.csv``.

Because we trust this one source, we keep a few cheap sanity asserts — not heavy
verification, just insurance that the file loaded as expected.

Run:
    uv run python -m dengue_climate.data.read_opendengue
"""

from __future__ import annotations

import pandas as pd

from dengue_climate.config import PROJECT_ROOT, get_path, load_config
from dengue_climate.data.normalize_names import DISTRICT_CANONICAL, normalize_district
from dengue_climate.viz.plots import plot_dengue_national_trend

# Output schema, in order.
COLUMNS = ["Province", "District", "Year", "Month", "cases"]


def load_panel(path) -> pd.DataFrame:
    """Read OpenDengue and reduce it to the tidy district-month panel.

    Keeps only Admin2 (district) rows at monthly resolution for the study years,
    derives ``Month`` from the calendar start date, Title-cases the place names,
    and drops every column we don't analyse.
    """
    years = load_config()["study"]["years"]
    raw = pd.read_csv(path)

    panel = raw[(raw["S_res"] == "Admin2") & (raw["T_res"] == "Month")].copy()
    panel = panel[panel["Year"].isin(years)]

    panel["Month"] = pd.to_datetime(panel["calendar_start_date"]).dt.month
    panel = panel.rename(
        columns={
            "adm_1_name": "Province",
            "adm_2_name": "District",
            "dengue_total": "cases",
        }
    )
    panel["Province"] = panel["Province"].str.title()
    panel["District"] = normalize_district(panel["District"].str.title())

    return panel[COLUMNS].sort_values(["District", "Year", "Month"], ignore_index=True)


def sanity_check(panel: pd.DataFrame) -> None:
    """Cheap asserts that the trusted source loaded correctly."""
    years = load_config()["study"]["years"]
    n_districts = panel["District"].nunique()
    expected_rows = n_districts * len(years) * 12

    print("\n=== Sanity checks ===")
    print(f"rows               : {len(panel)}")
    print(f"districts          : {n_districts}")
    print(f"years              : {sorted(panel['Year'].unique().tolist())}")

    assert not panel.empty, "panel is empty — filter matched no rows"
    assert set(panel["Year"]) == set(years), f"unexpected years: {set(panel['Year'])}"
    assert set(panel["Month"]) == set(range(1, 13)), "expected all 12 months present"
    assert panel[COLUMNS].notna().all().all(), "unexpected nulls in panel"
    assert (panel["cases"] >= 0).all(), "negative case counts found"
    assert not panel.duplicated(["District", "Year", "Month"]).any(), (
        "duplicate (District, Year, Month) rows"
    )
    leftover = set(panel["District"]) & set(DISTRICT_CANONICAL)
    assert not leftover, f"un-normalized district name(s) remain: {leftover}"
    assert len(panel) == expected_rows, (
        f"expected {expected_rows} rows ({n_districts}×{len(years)}×12), got {len(panel)}"
    )
    print(f"✓ all checks passed ({n_districts}×{len(years)}×12 = {expected_rows} rows)")


def main() -> None:
    raw_path = get_path("dengue_raw")
    out_path = get_path("dengue_monthly")
    print(f"reading dengue from {raw_path.name} …")
    panel = load_panel(raw_path)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(out_path, index=False)
    print(f"wrote {out_path.relative_to(PROJECT_ROOT)} ({len(panel)} rows)")

    sanity_check(panel)

    fig_path = get_path("figures") / "dengue_national_trend.png"
    plot_dengue_national_trend(panel, fig_path)
    print(f"\nsaved figure {fig_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
