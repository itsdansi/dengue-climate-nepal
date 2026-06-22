"""Re-fetch the climate study years missing for some districts.

The raw NASA POWER export is missing 2022-2024 for ~15 districts (only a
download artifact — the data exists at source). This pulls those district-years
back from the NASA POWER daily-point API, using each district's own grid
coordinates already present in the raw file, and writes the supplement to
``data/interim/climate_missing_refetch.csv``. Raw stays immutable; the
daily-to-monthly aggregation merges this supplement in.

"""

import pandas as pd
import requests

from dengue_climate.config import PROJECT_ROOT, get_path, load_config

API_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

# NASA POWER parameter -> our column name. (Same mapping the raw file uses.)
PARAM_TO_COLUMN = {
    "PRECTOTCORR": "Precip",
    "T2M": "Temp_2m",
    "T2M_MAX": "MaxTemp_2m",
    "T2M_MIN": "MinTemp_2m",
    "RH2M": "RH_2m",
    "QV2M": "Humidity_2m",
}
FILL_VALUE = -999.0  # NASA POWER's missing-data sentinel


def find_missing_districts(raw: pd.DataFrame, years: list[int]) -> pd.DataFrame:
    """Return districts with no study-year data, with their grid coordinates."""
    in_study = raw[raw["Date"].dt.year.isin(years)]
    present = set(in_study["District"].unique())
    missing = sorted(set(raw["District"].unique()) - present)
    coords = (
        raw[raw["District"].isin(missing)]
        .groupby("District")[["Latitude", "Longitude"]]
        .first()
    )
    return coords


def fetch_district(
    district: str, lat: float, lon: float, start: str, end: str
) -> pd.DataFrame:
    """Fetch one district's daily climate for the given date range."""
    resp = requests.get(
        API_URL,
        params={
            "parameters": ",".join(PARAM_TO_COLUMN),
            "community": "AG",
            "longitude": lon,
            "latitude": lat,
            "start": start,
            "end": end,
            "format": "JSON",
        },
        timeout=60,
    )
    resp.raise_for_status()
    params = resp.json()["properties"]["parameter"]

    df = pd.DataFrame(params).rename(columns=PARAM_TO_COLUMN)
    df = df.reset_index(names="Date")
    df["Date"] = pd.to_datetime(df["Date"], format="%Y%m%d")
    df.insert(1, "District", district)
    df.insert(2, "Latitude", lat)
    df.insert(3, "Longitude", lon)
    return df


def main() -> None:
    years = load_config()["study"]["years"]
    start, end = f"{min(years)}0101", f"{max(years)}1231"

    raw = pd.read_csv(
        get_path("climate_raw"),
        usecols=["Date", "District", "Latitude", "Longitude"],
        parse_dates=["Date"],
    )
    coords = find_missing_districts(raw, years)
    print(f"districts missing {min(years)}-{max(years)}: {len(coords)}")

    frames = []
    for district, row in coords.iterrows():
        df = fetch_district(district, row["Latitude"], row["Longitude"], start, end)
        frames.append(df)
        print(f"  fetched {district:14s} {len(df)} days")

    out = pd.concat(frames, ignore_index=True)

    # Replace NASA POWER's -999 fill with NaN and report any.
    value_cols = list(PARAM_TO_COLUMN.values())
    n_fill = (out[value_cols] == FILL_VALUE).sum().sum()
    if n_fill:
        print(f"⚠️  {n_fill} fill (-999) value(s) replaced with NaN")
        out[value_cols] = out[value_cols].replace(FILL_VALUE, pd.NA)

    out_path = get_path("climate_refetch")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    print(
        f"\nwrote {out_path.relative_to(PROJECT_ROOT)} "
        f"({len(out)} rows, {out['District'].nunique()} districts)"
    )


if __name__ == "__main__":
    main()
