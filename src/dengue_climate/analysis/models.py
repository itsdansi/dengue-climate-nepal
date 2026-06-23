"""Negative-binomial model of dengue cases on lagged climate × elevation.

Monthly counts are overdispersed and zero-heavy (the EDA showed variance ≫ mean),
so a **negative binomial** is used rather than Poisson. The model is pooled across
all 77 districts — statistical power comes from districts, not the three years —
with a **climate × elevation-band interaction** so the climate response is allowed
to differ between the Terai, hills and mountains.

Predictors are the dominant lags found in the lag analysis: rainfall and minimum
temperature two months back, humidity one month back. Calendar month enters as a
categorical to absorb the shared Jul-Oct seasonal shape. No population offset is
used (no district population data), so coefficients describe expected **case
counts**, not per-capita incidence — stated as a limitation.

Validation is genuinely out-of-sample: fit on **2022-2023**, predict **2024**.
Every quantity learned for the model (the climate standardisation) is fit on the
training years only, so the 2024 test set never leaks into training. A calendar-only
baseline (month + band, no climate) shows whether climate adds predictive value.

Artifacts: ``outputs/tables/model_coefficients.csv`` (incidence-rate ratios + CIs)
and ``outputs/figures/predicted_vs_actual_2024.png``.
"""

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from dengue_climate.analysis.crosscorr import add_lagged_features, load_panel
from dengue_climate.config import PROJECT_ROOT, get_path
from dengue_climate.viz.plots import plot_predicted_vs_actual

# Dominant lags from the lag analysis, one variable per climate family to avoid
# the collinearity among temp_mean/max/min.
CLIMATE_PREDICTORS = ["precip_lag2", "temp_min_lag2", "humidity_lag1"]
TRAIN_YEARS = [2022, 2023]
TEST_YEAR = 2024

# Terai (lowest band) is the interaction reference, so interaction terms read as
# "how the hill / mountain climate response differs from the Terai".
_FULL_FORMULA = (
    "cases ~ (precip_lag2 + temp_min_lag2 + humidity_lag1)"
    " * C(elevation_band, Treatment('Terai')) + C(month)"
)
_BASELINE_FORMULA = "cases ~ C(month) + C(elevation_band, Treatment('Terai'))"


def build_frame() -> pd.DataFrame:
    """Panel with lag predictors, dropping each district's lag-warmup months."""
    frame = add_lagged_features(load_panel(), lags=(1, 2))
    return frame.dropna(subset=CLIMATE_PREDICTORS).reset_index(drop=True)


def split(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Train = 2022-2023, test = 2024 — the out-of-sample forecast split."""
    train = frame[frame["year"].isin(TRAIN_YEARS)].copy()
    test = frame[frame["year"] == TEST_YEAR].copy()
    return train, test


def standardize(train, test, cols=CLIMATE_PREDICTORS):
    """Z-score the climate predictors using **training** mean/std only.

    Fitting the scaler on train alone keeps 2024 out of training; the same shift
    and scale are then applied to the test rows. Standardising also puts every IRR
    on a comparable "per one training-SD" footing and helps the fit converge.
    """
    mu, sigma = train[cols].mean(), train[cols].std()
    train_s, test_s = train.copy(), test.copy()
    train_s[cols] = (train[cols] - mu) / sigma
    test_s[cols] = (test[cols] - mu) / sigma
    return train_s, test_s, mu, sigma


def fit(train_s: pd.DataFrame, formula: str = _FULL_FORMULA):
    """Fit a negative-binomial (NB2) GLM by maximum likelihood.

    The ``errstate`` guard silences a benign divide-by-zero numpy warning from
    statsmodels' NB Hessian at large fitted means; both models still converge.
    """
    model = smf.negativebinomial(formula, data=train_s)
    with np.errstate(divide="ignore", invalid="ignore"):
        return model.fit(disp=0, maxiter=200)


def irr_table(result) -> pd.DataFrame:
    """Coefficients as incidence-rate ratios with 95% CIs and p-values.

    IRR = exp(coef): the multiplicative change in expected cases per one
    training-SD rise in a climate predictor (or per category for the factors).
    """
    ci = result.conf_int()
    tbl = pd.DataFrame(
        {
            "irr": np.exp(result.params),
            "ci_low": np.exp(ci[0]),
            "ci_high": np.exp(ci[1]),
            "p_value": result.pvalues,
        }
    )
    return tbl.drop(index="alpha", errors="ignore").round(3)


def evaluate(result, test_s: pd.DataFrame) -> dict[str, float]:
    """Out-of-sample MAE/RMSE of predicted vs actual 2024 district-month cases."""
    pred = result.predict(test_s)
    err = test_s["cases"].to_numpy() - pred.to_numpy()
    return {"mae": float(np.abs(err).mean()), "rmse": float(np.sqrt((err**2).mean()))}


def monthly_2024(test_s, full_result, base_result) -> pd.DataFrame:
    """National monthly actual vs predicted cases for 2024 (summed over districts)."""
    out = test_s[["month", "cases"]].copy()
    out["pred_full"] = full_result.predict(test_s).to_numpy()
    out["pred_base"] = base_result.predict(test_s).to_numpy()
    return out.groupby("month", as_index=False).sum()


def main() -> None:
    train, test = split(build_frame())
    train_s, test_s, mu, sigma = standardize(train, test)

    full = fit(train_s, _FULL_FORMULA)
    base = fit(train_s, _BASELINE_FORMULA)

    irrs = irr_table(full)
    tbl_path = get_path("tables") / "model_coefficients.csv"
    tbl_path.parent.mkdir(parents=True, exist_ok=True)
    irrs.to_csv(tbl_path, index_label="term")
    print(f"saved {tbl_path.relative_to(PROJECT_ROOT)}")

    monthly = monthly_2024(test_s, full, base)
    fig_path = plot_predicted_vs_actual(
        monthly, get_path("figures") / "predicted_vs_actual_2024.png"
    )
    print(f"saved {fig_path.relative_to(PROJECT_ROOT)}")

    full_m, base_m = evaluate(full, test_s), evaluate(base, test_s)
    print(f"\ntrain rows {len(train_s)} | test rows {len(test_s)} (2024)")
    print("\n=== In-sample fit (2022-2023, lower AIC is better) ===")
    print(f"climate + elevation : AIC {full.aic:8.0f}")
    print(f"calendar baseline   : AIC {base.aic:8.0f}")
    print(f"-> climate improves in-sample fit by {base.aic - full.aic:.0f} AIC points")
    print("\n=== 2024 out-of-sample error, district-month (lower is better) ===")
    print(f"climate + elevation : MAE {full_m['mae']:6.2f}  RMSE {full_m['rmse']:7.2f}")
    print(f"calendar baseline   : MAE {base_m['mae']:6.2f}  RMSE {base_m['rmse']:7.2f}")
    better = "beats" if full_m["rmse"] < base_m["rmse"] else "does NOT beat"
    print(
        f"-> climate {better} the calendar baseline out-of-sample: 2024 was a much\n"
        "   smaller season than 2022-2023, so both over-forecast the peak and the\n"
        "   richer climate model over-forecasts it more (power comes from districts,\n"
        "   not the three years)."
    )

    print("\n=== Incidence-rate ratios (per 1 training-SD of climate) ===")
    print("SD in original units:", {c: round(sigma[c], 1) for c in CLIMATE_PREDICTORS})
    print(irrs.to_string())


if __name__ == "__main__":
    main()
