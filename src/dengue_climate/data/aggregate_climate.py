"""Aggregate daily NASA POWER climate to monthly per district.

Reads the precip-fixed daily CSV, collapses it to one row per
(district, year, month) — summing rainfall, averaging temperature/humidity —
and writes ``data/processed/climate_monthly.csv``.

It also prints a monsoon-vs-winter rainfall sanity check (monsoon must be
clearly higher).

"""

import calendar

import pandas as pd

from dengue_climate.config import PROJECT_ROOT, get_path, load_config
from dengue_climate.viz.plots import plot_rainfall_seasonality


def load_daily(path) -> pd.DataFrame:
    """Read the daily climate CSV, merging in the re-fetched supplement if present.

    The raw export is missing 2022-2024 for some districts; if
    ``fetch_missing_climate`` has produced a supplement in ``data/interim``, its
    rows are unioned in (raw wins on any overlap).
    """
    cfg = load_config()["climate"]
    usecols = ["Date", "District", *cfg["sum_vars"], *cfg["mean_vars"]]
    df = pd.read_csv(path, usecols=usecols, parse_dates=["Date"])

    supplement = get_path("climate_refetch")
    if supplement.exists():
        extra = pd.read_csv(supplement, usecols=usecols, parse_dates=["Date"])
        before = len(df)
        df = pd.concat([df, extra], ignore_index=True)
        df = df.drop_duplicates(["District", "Date"], keep="first")
        print(
            f"  merged {len(df) - before} re-fetched daily rows from {supplement.name}"
        )

    df["year"] = df["Date"].dt.year
    df["month"] = df["Date"].dt.month
    return df


def aggregate_monthly(daily: pd.DataFrame) -> pd.DataFrame:
    """Collapse daily rows to one row per (district, year, month).

    Rainfall is summed; temperature/humidity are averaged. ``n_days`` records how
    many daily observations fed each month; months thinner than
    ``climate.min_days_fraction`` of their calendar length are dropped as
    unreliable.
    """
    cfg = load_config()["climate"]
    agg = {v: "sum" for v in cfg["sum_vars"]}
    agg.update({v: "mean" for v in cfg["mean_vars"]})

    monthly = daily.groupby(["District", "year", "month"], as_index=False).agg(
        **{c: (c, how) for c, how in agg.items()}, n_days=("Date", "size")
    )

    days_in_month = monthly.apply(
        lambda r: calendar.monthrange(int(r["year"]), int(r["month"]))[1], axis=1
    )
    keep = monthly["n_days"] >= cfg["min_days_fraction"] * days_in_month
    dropped = int((~keep).sum())
    if dropped:
        print(
            f"  dropped {dropped} partial month(s) below "
            f"{cfg['min_days_fraction']:.0%} day coverage"
        )
    monthly = monthly[keep].reset_index(drop=True)

    # Round to the raw input's 2-decimal precision.
    value_cols = cfg["sum_vars"] + cfg["mean_vars"]
    monthly[value_cols] = monthly[value_cols].round(2)

    return monthly.rename(columns={"District": "district"}).sort_values(
        ["district", "year", "month"], ignore_index=True
    )


def validate_seasonality(monthly: pd.DataFrame) -> None:
    """Monsoon rainfall must clearly exceed winter rainfall, or fail loudly."""
    seasons = load_config()["seasons"]
    precip = monthly.dropna(subset=["Precip"])
    monsoon = precip.loc[precip["month"].isin(seasons["monsoon"]), "Precip"].mean()
    winter = precip.loc[precip["month"].isin(seasons["winter"]), "Precip"].mean()

    print("\n=== Seasonality sanity check ===")
    print(f"mean monthly rainfall — monsoon (Jun-Sep): {monsoon:7.1f} mm")
    print(f"mean monthly rainfall — winter (Dec-Feb): {winter:7.1f} mm")
    ratio = monsoon / winter if winter else float("inf")
    print(f"monsoon / winter ratio: {ratio:.1f}*")
    if monsoon <= winter:
        raise AssertionError(
            "Monsoon rainfall is not higher than winter — aggregation is wrong."
        )
    print("✓ monsoon clearly wetter than winter")


def main() -> None:
    raw_path = get_path("climate_raw")
    out_path = get_path("climate_monthly")
    print(f"reading daily climate from {raw_path.name} …")
    daily = load_daily(raw_path)
    print(f"  {len(daily):,} daily rows, {daily['District'].nunique()} districts")

    monthly = aggregate_monthly(daily)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(out_path, index=False)
    print(f"wrote {out_path.relative_to(PROJECT_ROOT)} ({len(monthly)} rows)")

    validate_seasonality(monthly)

    fig_path = get_path("figures") / "rainfall_seasonality.png"
    plot_rainfall_seasonality(monthly, fig_path)
    print(f"\nsaved figure {fig_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
