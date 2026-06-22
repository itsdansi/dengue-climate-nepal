"""Canonical district-name normalization.

The dengue (OpenDengue) and climate (NASA POWER) sources spell some districts
differently. We treat the climate spellings as canonical and map the dengue
variants onto them, so the two tables join cleanly on ``district``.
"""

import pandas as pd

# {variant spelling : canonical spelling}. Canonical = the climate file's names.
DISTRICT_CANONICAL: dict[str, str] = {
    "Chitawan": "Chitwan",
    "Dhanusa": "Dhanusha",
    "Kapilbastu": "Kapilvastu",
    "Tanahu": "Tanahun",
    "Rukum East": "East Rukum",
    "Rukum West": "West Rukum",
    "Nawalparasi East": "Nawalpur",
    "Nawalparasi West": "Parasi",
}


def normalize_district(names: pd.Series) -> pd.Series:
    """Map district-name variants to their canonical spelling."""
    return names.replace(DISTRICT_CANONICAL)
