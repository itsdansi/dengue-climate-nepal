"""Plotting helpers for the dengue × climate pipeline."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: save figures without a display
import matplotlib.pyplot as plt

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
