"""How many months climate leads dengue cases.

The same-month correlations  were weak; climate is expected to *lead*
cases by one to two months (mosquito breeding, then transmission, then reported
illness). This module quantifies that by correlating cases with each climate
variable shifted back 0–4 months, pooled and split by elevation band.

Lags are taken **within each district's own monthly series** so a December value
never leaks into the next January of a different district. The panel is complete
(77 districts × 36 consecutive months), so a grouped ``shift`` is exact.

Artifacts: ``outputs/figures/lag_correlation.png`` and the printed/​saved
best-lag table ``outputs/tables/lag_best.csv``. The lagged predictor columns are
produced by :func:`add_lagged_features` for the negative-binomial model.
"""

import pandas as pd

from dengue_climate.config import PROJECT_ROOT, get_path
from dengue_climate.viz.plots import BAND_ORDER, plot_lag_correlation

CLIMATE_VARS = ["precip", "temp_mean", "temp_max", "temp_min", "humidity"]
LAGS = [0, 1, 2, 3, 4]


def load_panel() -> pd.DataFrame:
    """Read the analysis panel, sorted so per-district shifts are chronological."""
    panel = pd.read_csv(get_path("analysis_panel"))
    panel["elevation_band"] = pd.Categorical(
        panel["elevation_band"], categories=BAND_ORDER, ordered=True
    )
    return panel.sort_values(["district", "year", "month"]).reset_index(drop=True)


def add_lagged_features(
    panel: pd.DataFrame, variables=CLIMATE_VARS, lags=(1, 2)
) -> pd.DataFrame:
    """Return a copy with ``<var>_lag<k>`` columns, shifted within each district.

    Row *t* receives the climate value from *t − k* of the **same** district, so
    the new column expresses "climate k months ago". Early months of each
    district are NaN (no prior reading) and are left for the caller to drop.
    """
    panel = panel.sort_values(["district", "year", "month"]).reset_index(drop=True)
    grouped = panel.groupby("district", observed=True)
    for var in variables:
        for k in lags:
            panel[f"{var}_lag{k}"] = grouped[var].shift(k)
    return panel


def lag_correlations(
    panel: pd.DataFrame, variables=CLIMATE_VARS, lags=LAGS
) -> pd.DataFrame:
    """Pearson r of cases vs each variable lagged 0–4 months, overall and per band.

    Returns a long table with columns ``variable, band, lag, r`` where ``band`` is
    ``"All"`` for the pooled correlation plus one row per elevation band.
    """
    lagged = add_lagged_features(panel, variables, lags)

    def corr_for(df: pd.DataFrame, band: str) -> list[dict]:
        rows = []
        for var in variables:
            for k in lags:
                r = df["cases"].corr(df[f"{var}_lag{k}"])
                rows.append({"variable": var, "band": band, "lag": k, "r": r})
        return rows

    rows = corr_for(lagged, "All")
    for band in BAND_ORDER:
        sub = lagged[lagged["elevation_band"] == band]
        if len(sub):
            rows += corr_for(sub, band)
    return pd.DataFrame(rows).round(3)


def best_lags(corr_table: pd.DataFrame) -> pd.DataFrame:
    """Dominant lag per variable per band: the one with the largest |r|.

    Sign is kept in ``r`` so a negative association is still visible.
    """
    idx = corr_table.groupby(["variable", "band"], observed=True)["r"].apply(
        lambda s: s.abs().idxmax()
    )
    best = corr_table.loc[idx, ["variable", "band", "lag", "r"]]
    return best.sort_values(["variable", "band"]).reset_index(drop=True)


def best_lag_matrix(best: pd.DataFrame) -> pd.DataFrame:
    """Best lag as a variable × band grid (the printable headline table)."""
    bands = ["All", *[b for b in BAND_ORDER if b in best["band"].unique()]]
    return (
        best.pivot(index="variable", columns="band", values="lag")
        .reindex(index=CLIMATE_VARS, columns=bands)
    )


def main() -> None:
    panel = load_panel()
    corr_table = lag_correlations(panel)
    best = best_lags(corr_table)

    fig_path = plot_lag_correlation(
        corr_table, best, get_path("figures") / "lag_correlation.png"
    )
    print(f"saved {fig_path.relative_to(PROJECT_ROOT)}")

    tbl_path = get_path("tables") / "lag_best.csv"
    tbl_path.parent.mkdir(parents=True, exist_ok=True)
    best.to_csv(tbl_path, index=False)
    print(f"saved {tbl_path.relative_to(PROJECT_ROOT)}")

    print("\n=== Best lag (months) per variable per band ===")
    print(best_lag_matrix(best).to_string())
    print("\n=== Pooled correlation by lag ===")
    pooled = corr_table[corr_table["band"] == "All"].pivot(
        index="variable", columns="lag", values="r"
    )
    print(pooled.to_string())


if __name__ == "__main__":
    main()
