"""Build the district elevation reference table.

Two pieces of information per district:

* ``elevation_m`` — district-HQ altitude (m), a continuous secondary variable,
  looked up for each district's NASA POWER grid point via the Open-Meteo API.
* ``elevation_band`` — the categorical ecological belt (Mountain / Hill / Terai).
  NOT derived from ``elevation_m``: a single HQ altitude can't capture a
  district's dominant physiography, so each district takes its official
  whole-district belt (see ``BAND_SOURCE``).

Written once to ``data/raw/reference/district_elevation.csv`` as immutable raw
reference data.
"""

import pandas as pd
import requests

from dengue_climate.config import PROJECT_ROOT, get_path

API_URL = "https://api.open-meteo.com/v1/elevation"

# Nepal's official three-fold ecological belt classification assigns every
# district as a whole to one belt by its dominant physiography.
BAND_SOURCE = "GoN National Statistics Office (CBS) — ecological belt, Census 2021"

# 16 Mountain + 40 Hill + 21 Terai = 77 districts.
OFFICIAL_BANDS: dict[str, str] = {
    # --- Mountain (16) ---
    "Achham": "Mountain",
    "Darchula": "Mountain",
    "Dolakha": "Mountain",
    "Dolpa": "Mountain",
    "Gorkha": "Mountain",
    "Humla": "Mountain",
    "Jumla": "Mountain",
    "Manang": "Mountain",
    "Mugu": "Mountain",
    "Mustang": "Mountain",
    "Myagdi": "Mountain",
    "Rasuwa": "Mountain",
    "Sankhuwasabha": "Mountain",
    "Sindhupalchok": "Mountain",
    "Solukhumbu": "Mountain",
    "Taplejung": "Mountain",
    # --- Hill (40) ---
    "Arghakhanchi": "Hill",
    "Baglung": "Hill",
    "Baitadi": "Hill",
    "Bajhang": "Hill",
    "Bajura": "Hill",
    "Bhaktapur": "Hill",
    "Bhojpur": "Hill",
    "Dadeldhura": "Hill",
    "Dailekh": "Hill",
    "Dhading": "Hill",
    "Dhankuta": "Hill",
    "Doti": "Hill",
    "East Rukum": "Hill",
    "Gulmi": "Hill",
    "Ilam": "Hill",
    "Jajarkot": "Hill",
    "Kalikot": "Hill",
    "Kaski": "Hill",
    "Kathmandu": "Hill",
    "Kavrepalanchok": "Hill",
    "Khotang": "Hill",
    "Lalitpur": "Hill",
    "Lamjung": "Hill",
    "Makwanpur": "Hill",
    "Nuwakot": "Hill",
    "Okhaldhunga": "Hill",
    "Palpa": "Hill",
    "Panchthar": "Hill",
    "Parbat": "Hill",
    "Pyuthan": "Hill",
    "Ramechhap": "Hill",
    "Rolpa": "Hill",
    "Salyan": "Hill",
    "Sindhuli": "Hill",
    "Surkhet": "Hill",
    "Syangja": "Hill",
    "Tanahun": "Hill",
    "Terhathum": "Hill",
    "Udayapur": "Hill",
    "West Rukum": "Hill",
    # --- Terai (21) ---
    "Banke": "Terai",
    "Bara": "Terai",
    "Bardiya": "Terai",
    "Chitwan": "Terai",
    "Dang": "Terai",
    "Dhanusha": "Terai",
    "Jhapa": "Terai",
    "Kailali": "Terai",
    "Kanchanpur": "Terai",
    "Kapilvastu": "Terai",
    "Mahottari": "Terai",
    "Morang": "Terai",
    "Nawalpur": "Terai",
    "Parasi": "Terai",
    "Parsa": "Terai",
    "Rautahat": "Terai",
    "Rupandehi": "Terai",
    "Saptari": "Terai",
    "Sarlahi": "Terai",
    "Siraha": "Terai",
    "Sunsari": "Terai",
}

# Districts whose HQ-town altitude alone would suggest a different band than the
# official whole-district belt. Kept explicit so the override is reproducible.
BORDERLINE_NOTES: dict[str, str] = {
    # Mountain districts whose HQ town sits low in a valley / mid-hills:
    "Achham": "HQ altitude is mid-hill; district is officially Mountain belt",
    "Dolakha": "HQ altitude is mid-hill; district is officially Mountain belt",
    "Gorkha": "HQ altitude is mid-hill; district is officially Mountain belt",
    "Jumla": "HQ altitude is mid-hill; district is officially Mountain belt",
    "Myagdi": "HQ altitude is mid-hill; district is officially Mountain belt",
    "Rasuwa": "HQ altitude is mid-hill; district is officially Mountain belt",
    "Sankhuwasabha": "HQ altitude is mid-hill; district is officially Mountain belt",
    "Sindhupalchok": "HQ altitude is mid-hill; district is officially Mountain belt",
    "Taplejung": "HQ altitude is mid-hill; district is officially Mountain belt",
    # Hill district whose HQ town sits high:
    "Bajhang": "HQ altitude is high; district is officially Hill belt",
    # Hill districts whose HQ town sits low (inner-Terai / valley floor):
    "Doti": "HQ altitude is low; district is officially Hill belt",
    "Makwanpur": "HQ altitude is low (inner-Terai); district is officially Hill belt",
    "Nuwakot": "HQ altitude is low; district is officially Hill belt",
    "Ramechhap": "HQ altitude is low; district is officially Hill belt",
    "Tanahun": "HQ altitude is low; district is officially Hill belt",
    "Terhathum": "HQ altitude is low; district is officially Hill belt",
    "Udayapur": "HQ altitude is low (inner-Terai); district is officially Hill belt",
    # Terai district with an inner-Terai (dun) HQ above the plains:
    "Dang": "HQ altitude is elevated (inner-Terai dun); district is officially Terai belt",
}


def assign_official_bands(districts: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Map each district to its official belt and borderline note (no altitude)."""
    band = districts.map(OFFICIAL_BANDS)
    note = districts.map(BORDERLINE_NOTES).fillna("")
    missing = districts[band.isna()].tolist()
    assert not missing, f"districts with no official belt mapping: {missing}"
    return band, note


def fetch_elevations(coords: pd.DataFrame) -> list[float]:
    """Look up elevation (m) for each (Latitude, Longitude) row in one request."""
    resp = requests.get(
        API_URL,
        params={
            "latitude": ",".join(coords["Latitude"].astype(str)),
            "longitude": ",".join(coords["Longitude"].astype(str)),
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["elevation"]


def main() -> None:
    raw = pd.read_csv(
        get_path("climate_raw"), usecols=["District", "Latitude", "Longitude"]
    )
    coords = (
        raw.groupby("District")[["Latitude", "Longitude"]]
        .first()
        .reset_index()
        .rename(columns={"District": "district"})
        .sort_values("district", ignore_index=True)
    )
    print(f"looking up elevation for {len(coords)} districts …")

    coords["elevation_m"] = fetch_elevations(coords)
    coords["elevation_band"], coords["band_note"] = assign_official_bands(
        coords["district"]
    )
    coords["band_source"] = BAND_SOURCE

    assert coords["elevation_m"].notna().all(), "missing elevation for some districts"
    assert coords["elevation_band"].notna().all(), (
        "missing official belt for some districts"
    )

    out_path = get_path("district_elevation")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    coords.to_csv(out_path, index=False)
    print(f"wrote {out_path.relative_to(PROJECT_ROOT)} ({len(coords)} districts)")
    print("\ndistricts per band:")
    print(coords["elevation_band"].value_counts().to_string())


if __name__ == "__main__":
    main()
