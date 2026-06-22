# Dengue × Climate in Nepal

How rainfall, temperature, and humidity relate to dengue across Nepal's
elevation bands, 2022–2024. A reproducible pipeline joins OpenDengue case counts
with NASA POWER climate data and district elevations into a district × month
panel, then runs exploratory analysis, a climate-leads-cases lag analysis, and a
negative-binomial model. The unit of analysis is the district-month
(77 districts × 36 months = 2,772 rows).

## Data sources

| Source | What | Resolution |
|---|---|---|
| [OpenDengue](https://opendengue.org/) | Reported dengue cases, all 77 districts | Monthly, 2022–2024 |
| [NASA POWER](https://power.larc.nasa.gov/) | Rainfall, temperature (mean/max/min), humidity | Daily → monthly |
| GoN National Statistics Office (CBS), Census 2021 | District HQ elevation (m) + ecological belt (Terai / Hill / Mountain) | Per district |

Please cite these sources if you reuse the data.

## Setup

Requires Python ≥ 3.13 and [uv](https://docs.astral.sh/uv/).

```
uv sync
```

## Pipeline

```
uv run python main.py --list      # list stages
uv run python main.py all         # regenerate every table and figure from raw
uv run python main.py panel       # run a single stage
```

Outputs land in `data/processed/` (tables) and `outputs/` (figures + summary
tables).

## Dashboard

An interactive dashboard presents the findings (overview, climate & lag, model
results) and lets you slice the panel by district, elevation band, year, and
climate variable. It reads the artifacts produced by the pipeline above, so run
`main.py all` first if `outputs/` is empty.

```
uv run python -m streamlit run dashboard/app.py
```

## Findings

The written analysis lives in [reports/final_report.md](reports/final_report.md)
(questions, results, and limitations) and
[reports/eda_findings.md](reports/eda_findings.md) (exploratory detail). The
notebooks under `notebooks/` walk through the EDA, lag, and modelling steps
interactively.

## Project layout

```
src/dengue_climate/   pipeline + analysis package
  data/               ingest, normalize, aggregate sources
  analysis/           EDA, lag analysis, model
  viz/                figure functions
notebooks/            EDA, lag, and model notebooks
dashboard/            Streamlit dashboard (app.py)
data/                 raw inputs, interim, processed panel
outputs/              generated figures + summary tables
reports/              written findings
config.yaml           study years, seasons, aggregation rules, paths
main.py               pipeline dispatcher
```
