"""Pipeline dispatcher: run any stage, or the whole thing from raw.

Each subcommand calls one module's ``main()``. ``all`` runs the deterministic
analysis chain in order — from the saved raw/interim inputs straight through to
the model — so deleting ``data/processed/`` and ``outputs/`` and re-running
``all`` reproduces every table and figure with no network access.

The two network-dependent prep steps (``fetch-climate``, ``fetch-elevation``)
are one-off and excluded from ``all``: their outputs are already saved under
``data/interim/`` and ``data/raw/reference/`` and treated as inputs.

    uv run python main.py all              # regenerate everything from raw
    uv run python main.py panel            # just rebuild the analysis panel
    uv run python main.py --list           # show all stages
"""

import argparse

from dengue_climate.analysis import crosscorr, eda, models
from dengue_climate.data import (
    aggregate_climate,
    fetch_elevation,
    fetch_missing_climate,
    read_opendengue,
)
from dengue_climate import build_panel

# name -> (callable, one-line help). Order is the reproducible run order.
STAGES = {
    "climate-monthly": (aggregate_climate.main, "daily NASA POWER -> monthly climate"),
    "dengue": (read_opendengue.main, "OpenDengue extract -> monthly dengue panel"),
    "panel": (build_panel.main, "join dengue + climate + elevation -> analysis panel"),
    "eda": (eda.main, "exploratory figures + findings note"),
    "lag": (crosscorr.main, "climate-leads-cases lag analysis"),
    "model": (models.main, "negative-binomial model + 2024 validation"),
}

# Network prep, run once to populate inputs; not part of `all`.
PREP_STAGES = {
    "fetch-climate": (fetch_missing_climate.main, "re-fetch missing district-years (NASA POWER API)"),
    "fetch-elevation": (fetch_elevation.main, "fetch district HQ elevations + bands"),
}

ALL_STAGES = {**STAGES, **PREP_STAGES}


def run_all() -> None:
    """Run the deterministic analysis chain end to end."""
    for name, (fn, _) in STAGES.items():
        print(f"\n{'=' * 70}\n# {name}\n{'=' * 70}")
        fn()


def main() -> None:
    choices = [*ALL_STAGES, "all"]
    parser = argparse.ArgumentParser(description="Dengue x climate pipeline dispatcher.")
    parser.add_argument("stage", nargs="?", choices=choices, help="stage to run")
    parser.add_argument("--list", action="store_true", help="list stages and exit")
    args = parser.parse_args()

    if args.list or not args.stage:
        width = max(len(n) for n in choices)
        print("Stages (in reproducible order):")
        for name, (_, desc) in STAGES.items():
            print(f"  {name:<{width}}  {desc}")
        print("\nNetwork prep (run once, excluded from `all`):")
        for name, (_, desc) in PREP_STAGES.items():
            print(f"  {name:<{width}}  {desc}")
        print(f"\n  {'all':<{width}}  run the deterministic chain from raw")
        return

    if args.stage == "all":
        run_all()
    else:
        ALL_STAGES[args.stage][0]()


if __name__ == "__main__":
    main()
