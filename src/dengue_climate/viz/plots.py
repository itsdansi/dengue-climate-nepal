"""Plotting helpers for the dengue × climate pipeline."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: save figures without a display
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

MONTHS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]

# Low → high elevation, so every figure reads Terai → Hill → Mountain.
BAND_ORDER = ["Terai", "Hill", "Mountain"]
BAND_COLORS = {"Terai": "tab:red", "Hill": "tab:green", "Mountain": "tab:blue"}


def plot_rainfall_seasonality(monthly, out_path: Path, districts=None) -> Path:
    """Plot mean monthly rainfall (the monsoon hump) for a few districts.

    For each district, rainfall is averaged across years by calendar month, so
    the curve shows the typical seasonal cycle rather than any single year.
    """
    if districts is None:
        # a spread across the elevation gradient (Terai → hill → mountain)
        preferred = ["Jhapa", "Chitwan", "Kathmandu", "Kaski", "Mustang"]
        available = set(monthly["district"].unique())
        districts = [d for d in preferred if d in available]
        if not districts:
            districts = sorted(available)[:5]

    cycle = (
        monthly[monthly["district"].isin(districts)]
        .groupby(["district", "month"])["Precip"]
        .mean()
        .reset_index()
    )

    fig, ax = plt.subplots(figsize=(9, 5.5))
    for district in districts:
        d = cycle[cycle["district"] == district].sort_values("month")
        ax.plot(d["month"], d["Precip"], marker="o", label=district)

    ax.axvspan(6, 9, color="tab:blue", alpha=0.08, label="monsoon (Jun-Sep)")
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(MONTHS)
    ax.set_xlabel("month")
    ax.set_ylabel("mean monthly rainfall (mm)")
    ax.set_title("Rainfall seasonality across Nepal's elevation gradient")
    ax.legend(title="district", fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_dengue_national_trend(panel, out_path: Path) -> Path:
    """Plot the national monthly dengue curve, one line per study year.

    Cases are summed across all districts per month, so the seasonal outbreak
    shape (the Jul-Oct surge) is visible and comparable across years.
    """
    national = panel.groupby(["Year", "Month"])["cases"].sum().reset_index()

    fig, ax = plt.subplots(figsize=(9, 5.5))
    for year in sorted(national["Year"].unique()):
        d = national[national["Year"] == year].sort_values("Month")
        ax.plot(d["Month"], d["cases"], marker="o", label=str(year))

    ax.axvspan(7, 10, color="tab:red", alpha=0.07, label="outbreak (Jul-Oct)")
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(MONTHS)
    ax.set_xlabel("month")
    ax.set_ylabel("national dengue cases")
    ax.set_title("Nepal national dengue trend by month")
    ax.legend(title="year", fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def _bands_present(panel) -> list[str]:
    """Bands actually in the panel, kept in low→high elevation order."""
    present = set(panel["elevation_band"].unique())
    return [b for b in BAND_ORDER if b in present]


def plot_cases_climate_overlay(panel, out_path: Path) -> Path:
    """Monthly cases per elevation band over the study period, with rainfall.

    Cases are summed within each band per calendar month; national mean rainfall
    is drawn behind them on a second axis, so the visual question — do case
    surges trail the monsoon? — is read straight off the figure.
    """
    panel = panel.copy()
    panel["date"] = pd.to_datetime(
        dict(year=panel["year"], month=panel["month"], day=1)
    )
    by_band = (
        panel.groupby(["elevation_band", "date"])["cases"].sum().reset_index()
    )
    rain = panel.groupby("date")["precip"].mean().reset_index()

    fig, ax = plt.subplots(figsize=(11, 5.5))
    rain_ax = ax.twinx()
    rain_ax.bar(
        rain["date"], rain["precip"], width=20, color="tab:blue",
        alpha=0.12, label="national mean rainfall",
    )
    rain_ax.set_ylabel("mean monthly rainfall (mm)", color="tab:blue")
    rain_ax.tick_params(axis="y", labelcolor="tab:blue")

    for band in _bands_present(panel):
        d = by_band[by_band["elevation_band"] == band].sort_values("date")
        ax.plot(d["date"], d["cases"], marker="o", ms=3,
                color=BAND_COLORS[band], label=band)

    ax.set_zorder(rain_ax.get_zorder() + 1)
    ax.patch.set_visible(False)
    ax.set_xlabel("month")
    ax.set_ylabel("monthly dengue cases")
    ax.set_title("Dengue cases by elevation band vs rainfall, 2022-2024")
    ax.legend(title="elevation band", loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_seasonality_by_band(panel, out_path: Path) -> Path:
    """Mean monthly cases by calendar month, one line per elevation band.

    Averaging across years collapses the three seasons into the typical annual
    cycle, exposing whether the outbreak peaks later (or not at all) at altitude.
    """
    cycle = (
        panel.groupby(["elevation_band", "month"])["cases"].mean().reset_index()
    )

    fig, ax = plt.subplots(figsize=(9, 5.5))
    for band in _bands_present(panel):
        d = cycle[cycle["elevation_band"] == band].sort_values("month")
        ax.plot(d["month"], d["cases"], marker="o",
                color=BAND_COLORS[band], label=band)

    ax.axvspan(7, 10, color="tab:red", alpha=0.07, label="outbreak (Jul-Oct)")
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(MONTHS)
    ax.set_xlabel("month of year")
    ax.set_ylabel("mean cases per district-month")
    ax.set_title("Dengue seasonality by elevation band")
    ax.legend(title="elevation band", fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_correlation_heatmap(panel, out_path: Path, columns=None) -> Path:
    """Pearson correlation heatmap of cases against each climate variable."""
    if columns is None:
        columns = ["cases", "precip", "temp_mean", "temp_max", "temp_min", "humidity"]
    corr = panel[columns].corr()

    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(columns)), columns, rotation=45, ha="right")
    ax.set_yticks(range(len(columns)), columns)
    for i in range(len(columns)):
        for j in range(len(columns)):
            ax.text(j, i, f"{corr.iat[i, j]:.2f}", ha="center", va="center",
                    color="white" if abs(corr.iat[i, j]) > 0.5 else "black",
                    fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Pearson r")
    ax.set_title("Cases vs climate — correlation")
    fig.tight_layout()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_cases_concentration(panel, out_path: Path) -> Path:
    """Where cases concentrate: total cases per band and the top districts."""
    by_band = (
        panel.groupby("elevation_band")["cases"].sum()
        .reindex(_bands_present(panel))
    )
    share = 100 * by_band / by_band.sum()
    top = panel.groupby("district")["cases"].sum().nlargest(10).iloc[::-1]

    fig, (ax_band, ax_top) = plt.subplots(1, 2, figsize=(12, 5.5))

    bars = ax_band.bar(by_band.index, by_band.values,
                       color=[BAND_COLORS[b] for b in by_band.index])
    for bar, pct in zip(bars, share.values):
        ax_band.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                     f"{pct:.0f}%", ha="center", va="bottom", fontsize=9)
    ax_band.set_ylabel("total cases, 2022-2024")
    ax_band.set_title("Total dengue cases by elevation band")
    ax_band.grid(True, axis="y", alpha=0.3)

    ax_top.barh(top.index, top.values, color="tab:purple", alpha=0.8)
    ax_top.set_xlabel("total cases, 2022-2024")
    ax_top.set_title("Top 10 districts by case load")
    ax_top.grid(True, axis="x", alpha=0.3)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_cases_distribution(panel, out_path: Path) -> Path:
    """Distribution of monthly district cases — the overdispersion evidence.

    A raw histogram (dominated by zeros) beside a log1p histogram makes the
    long right tail visible; the mean/variance gap is annotated to motivate the
    negative-binomial choice over Poisson.
    """
    cases = panel["cases"]
    mean, var = cases.mean(), cases.var()
    zero_frac = 100 * (cases == 0).mean()

    fig, (ax_raw, ax_log) = plt.subplots(1, 2, figsize=(12, 5))

    ax_raw.hist(cases, bins=50, color="tab:gray")
    ax_raw.set_yscale("log")
    ax_raw.set_xlabel("monthly cases per district")
    ax_raw.set_ylabel("district-months (log scale)")
    ax_raw.set_title("Raw case counts")
    ax_raw.text(0.97, 0.95,
                f"mean={mean:.1f}\nvar={var:.0f}\nvar/mean={var / mean:.0f}\n"
                f"zeros={zero_frac:.0f}%",
                transform=ax_raw.transAxes, ha="right", va="top", fontsize=9,
                bbox=dict(boxstyle="round", fc="white", alpha=0.8))

    ax_log.hist(np.log1p(cases), bins=40, color="tab:orange")
    ax_log.set_xlabel("log(1 + monthly cases)")
    ax_log.set_ylabel("district-months")
    ax_log.set_title("Log-transformed counts")

    fig.suptitle("Monthly dengue counts are overdispersed and zero-heavy")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_lag_correlation(corr_table, best, out_path: Path) -> Path:
    """Pooled correlation of cases vs each climate variable at lags 0-4 months.

    One line per variable; the dominant lag (largest |r|) is marked so the
    headline "climate leads cases by ~k months" reads straight off the figure.
    Per-band detail lives in the printed/saved best-lag table, not here.
    """
    pooled = corr_table[corr_table["band"] == "All"]
    best_all = best[best["band"] == "All"].set_index("variable")

    fig, ax = plt.subplots(figsize=(8, 5.5))
    for var, grp in pooled.groupby("variable"):
        grp = grp.sort_values("lag")
        line, = ax.plot(grp["lag"], grp["r"], marker="o", label=var)
        if var in best_all.index:
            lag, r = best_all.loc[var, "lag"], best_all.loc[var, "r"]
            ax.scatter([lag], [r], s=140, facecolors="none",
                       edgecolors=line.get_color(), linewidths=2, zorder=5)

    ax.axhline(0, color="gray", lw=0.8)
    ax.set_xticks(sorted(pooled["lag"].unique()))
    ax.set_xlabel("lag (months climate leads cases)")
    ax.set_ylabel("Pearson r with monthly cases")
    ax.set_title("How far climate leads dengue cases (pooled, 77 districts)")
    ax.grid(True, alpha=0.3)
    ax.legend(title="climate variable", fontsize=9)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_predicted_vs_actual(monthly, out_path: Path) -> Path:
    """National 2024 monthly cases: actual vs the model and calendar baseline.

    The test year was never seen in training, so this shows whether the climate
    model captures the real Jul-Oct peak's timing and height better than a model
    that knows only the calendar.
    """
    m = monthly.sort_values("month")
    x = m["month"]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(x, m["cases"], color="black", marker="o", lw=2, label="actual 2024")
    ax.plot(x, m["pred_full"], color="tab:red", marker="s", lw=1.8,
            label="climate + elevation")
    ax.plot(x, m["pred_base"], color="tab:gray", ls="--", marker="^", lw=1.5,
            label="calendar baseline")

    ax.set_xticks(range(1, 13), MONTHS)
    ax.set_xlabel("month of 2024")
    ax.set_ylabel("national cases (sum over 77 districts)")
    ax.set_title("Out-of-sample 2024 forecast vs actual")
    ax.grid(True, alpha=0.3)
    ax.legend()

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path
