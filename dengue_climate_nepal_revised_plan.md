# Dengue × Climate in Nepal — Revised Phase-by-Phase Plan

**Project type:** Spatial climate–dengue analysis across Nepal's elevation gradient, with a validated predictive model. Sole evaluation for the subject.

**Research questions:**
1. How does monthly dengue incidence relate to rainfall, temperature, and humidity across Nepal's 77 districts?
2. Does that relationship change with **elevation** (Terai → hill → mountain) — i.e. are higher-altitude districts becoming newly dengue-suitable?
3. Can a model trained on 2022–2023 predict the 2024 monsoon season?

**Data reality (locked):**
- Dengue: **monthly**, per district, for **2022, 2023, 2024** (three outbreak seasons). 2020–21 excluded (COVID-disrupted), 2025 excluded (partial year, no monsoon).
- Climate: **daily**, all 77 districts, NASA POWER (`Precip` rebuilt; temp/humidity already present).
- Unit of analysis: **district-month** (~77 × 36 = 2,772 rows). Statistical power comes from **districts**, not years.

**Core method:** Pooled **negative binomial** regression on the district-month panel, with a **climate × elevation** interaction. Per-district time-series models are deliberately avoided (only 36 months each — too few). No deep learning (would overfit). Interpretability is a feature.

---

## Guiding principles (apply in every phase)

- **Raw is immutable.** Downloads live in `data/raw/` and are never edited by hand. All transformation happens in code.
- **One canonical source per value.** Dengue counts come from **EDCD**; OpenDengue is the **validator**, not an input. (Because 2025 is dropped, you *may* instead use OpenDengue for 2022–24 with EDCD as validator — pick one, document it, never mix per-cell.)
- **Validate before trust.** Every extraction is checked against a printed control total before use.
- **Each phase ends with a visible artifact** — a file, a figure, or a printed report you can open and inspect.

---

## PHASE 0 — Scaffolding
**Goal:** Turn the bare `uv` init into a working project skeleton.

**Steps:**
1. Add dependencies via uv:
   ```bash
   uv add pandas numpy requests pdfplumber openpyxl epiweeks  statsmodels scipy matplotlib seaborn pyyaml jupyter
   uv add --dev pytest ruff
   ```
2. Create the folder structure (see final section) and `config.yaml`.
3. Replace `main.py` with a tiny CLI dispatcher that will call each pipeline step.
4. Write `README.md` describing the project and how to run each phase.

**✅ Visible at end of phase:**
Running `uv run python main.py --help` prints the list of pipeline commands (even if each is just a stub that prints "not yet implemented"). The folder tree exists. `uv.lock` is updated.

---

## PHASE 1 — Climate data ready
**Goal:** A clean, monthly, per-district climate table you can plot.

**Steps:**
1. Place the raw weather CSV in `data/raw/climate/`.
2. Run the precip rebuild (`fix_precip_from_nasapower.py`) → fills the broken `Precip` column from NASA POWER. Output to `data/interim/`.
3. Aggregate daily → monthly per district: **sum** `Precip`; **average** `Temp_2m`, `MaxTemp_2m`, `MinTemp_2m`, `RH_2m`, `Humidity_2m`. Output `data/processed/climate_monthly.parquet`.
4. Validate: print monsoon (Jun–Sep) vs winter (Dec–Feb) mean rainfall — monsoon must be clearly higher.

**✅ Visible at end of phase:**
- `data/processed/climate_monthly.parquet` exists (77 districts × ~66 months).
- A saved figure `outputs/figures/rainfall_seasonality.png` showing the monsoon hump for a few districts.
- Console prints the monsoon-vs-winter sanity check.

---

## PHASE 2 — Dengue data extracted & validated
**Goal:** A clean monthly district-level dengue panel for 2022–2024 that provably matches the official totals.

**Steps:**
1. Put each EDCD year-end PDF/Excel in `data/raw/dengue/`. Prefer **embedded Excel** where it exists; fall back to `pdfplumber` extraction otherwise.
2. Write **one small reader per year** (layouts differ). Each outputs the identical schema: `year, month, province, district, cases`.
3. Fix extraction artifacts (e.g. digits split across lines like `9⏎6 → 96`; the mangled multi-stream table layout in some SITREPs).
4. **Validate each year**: extracted district numbers must sum to the printed `TOTAL (PROVINCE)` and national total. Fail loudly if not.
5. Normalize district names to one canonical spelling (`CHITAWAN→Chitwan`, `SUDUR PASHCHIM→Sudurpaschim`, `NAWALPARASI EAST`, `RUKUM EAST/WEST`, etc.).
6. Concatenate into `data/processed/dengue_monthly.parquet` with a `source` column.
7. **Cross-check** against OpenDengue 2022–2024 (month × district) — report agreement.

**✅ Visible at end of phase:**
- `data/processed/dengue_monthly.parquet` (district × month × 3 years).
- A printed validation report: per-year "sum equals official total ✓", and the OpenDengue agreement summary.
- A saved figure `outputs/figures/dengue_national_trend.png` reproducing the Jul–Oct outbreak curve.

---

## PHASE 3 — The unified analysis table
**Goal:** One tidy table joining dengue + climate + elevation — the single input to all analysis.

**Steps:**
1. Assign each district an **elevation value** (district HQ altitude) and an **elevation band**: Terai (low), Hill (mid), Mountain (high). Store as `data/raw/reference/district_elevation.csv`.
2. Join dengue ⨝ climate on `(district, year, month)`; attach elevation band.
3. Resolve any name mismatches surfaced by the join (no silent drops).
4. Output `data/processed/analysis_panel.parquet` with columns:
   `district, province, elevation_m, elevation_band, year, month, cases, precip, temp_mean, temp_max, temp_min, humidity`.
5. Assert: no duplicate `(district, year, month)`; expected row count; no unexpected nulls.

**✅ Visible at end of phase:**
- `data/processed/analysis_panel.parquet` (~2,772 rows).
- A printed data-quality report (row counts, null counts, districts per band).
- `outputs/tables/panel_summary.csv` — counts and means per elevation band.

---

## PHASE 4 — Exploratory data analysis
**Goal:** See the structure before modeling; surface issues that feed back into cleaning.

**Steps (notebook `01_eda.ipynb`):**
1. National & per-band monthly time series of cases (overlay rainfall/temperature).
2. Seasonality: cases by month-of-year, by elevation band.
3. Correlation heatmap: cases vs each climate variable.
4. Map-style or band-grouped view of where cases concentrate.
5. Distribution checks (overdispersion → justifies negative binomial).
6. **Loop back:** any anomaly found here becomes a documented rule in the cleaning code, not a manual edit.

**✅ Visible at end of phase:**
- A set of figures in `outputs/figures/` (seasonality, overlays, heatmap).
- Notebook renders top-to-bottom without manual fixes.
- A short written "EDA findings" note (markdown cell or `reports/eda_findings.md`).

---

## PHASE 5 — Lag analysis (supporting result)
**Goal:** Quantify how many **months** climate leads cases.

**Steps (notebook `02_lag.ipynb`, logic in `src/analysis/crosscorr.py`):**
1. For each climate variable, compute correlation with cases at lags **0–4 months**.
2. Identify the dominant lag (expected: rainfall/temperature leading by ~1–2 months).
3. Compare lag structure **across elevation bands** (does the hill lag differ from the Terai lag?).
4. Create the lagged predictor columns (e.g. `precip_lag1`, `temp_lag1`) for modeling.

**✅ Visible at end of phase:**
- `outputs/figures/lag_correlation.png` — lag-vs-correlation curve per variable, the headline lag marked.
- Printed table of best lag per variable per band.

---

## PHASE 6 — Modeling (core result)
**Goal:** A defensible, interpretable model with the climate × elevation interaction, plus honest validation.

**Steps (notebook `03_model.ipynb`, logic in `src/analysis/models.py`):**
1. **Pooled negative binomial GLM** on the panel: `cases ~ lagged climate + elevation_band + climate:elevation_band + season terms`. Handle overdispersion (that's why NB, not Poisson). Add `log(population)` offset if available.
2. Report coefficients as **incidence rate ratios**, with the interaction interpreted ("a 100 mm rainfall rise raises expected cases by X% in Terai vs Y% in hills").
3. **Predictive validation:** train on **2022–2023**, test on **2024**. Report out-of-sample MAE/RMSE and whether the model captures the 2024 peak timing and magnitude.
4. **Avoid leakage:** any quantity learned for cleaning/scaling is fit on the training years only.
5. Compare against a simple seasonal baseline (does climate add predictive value over "just the calendar"?).

**✅ Visible at end of phase:**
- `outputs/tables/model_coefficients.csv` (IRRs + CIs).
- `outputs/figures/predicted_vs_actual_2024.png`.
- Printed metrics: test MAE/RMSE, baseline comparison.

---

## PHASE 7 — Interpretation & write-up
**Goal:** Turn results into the elevation-gradient narrative and a finished report.

**Steps:**
1. Synthesize: how the climate–dengue link shifts with altitude; evidence (or not) of upward spread.
2. Write `reports/final_report.md` — question, data, methods, results, limitations.
3. **Limitations (state plainly):** 3-year panel (power from districts, not years); monthly resolution (lag detectable only to ~1 month); single NASA POWER grid-point per district (~50 km); surveillance under-reporting; correlation ≠ causation (urbanization, mobility also drive spread).
4. Reproducibility pass: delete `data/processed/` and `outputs/`, re-run the full pipeline from raw, confirm identical results.

**✅ Visible at end of phase:**
- `reports/final_report.md` complete with embedded figures.
- A clean `uv run python main.py all` regenerates every output from raw.

---

## PHASE 8 (optional polish) — Dashboard & scenario
**Goal:** Headroom for a top grade.

**Steps:**
- Streamlit app: pick a district/band → see cases-vs-climate overlay and the model's fit.
- Short scenario discussion: under projected warming, which currently-marginal hill districts may become dengue-suitable.

**✅ Visible at end of phase:**
- `uv run streamlit run app/dashboard.py` launches an interactive view.

---

## Phase → visible-artifact summary

| Phase | You can see... |
|---|---|
| 0 | `main.py --help` lists commands; tree + lockfile exist |
| 1 | `climate_monthly.parquet` + rainfall seasonality figure |
| 2 | `dengue_monthly.parquet` + validation report + outbreak-curve figure |
| 3 | `analysis_panel.parquet` + data-quality report |
| 4 | EDA figures + findings note |
| 5 | Lag-correlation figure + best-lag table |
| 6 | Coefficient table + predicted-vs-actual-2024 figure + metrics |
| 7 | Final report; full pipeline re-runs from raw |
| 8 | Interactive Streamlit dashboard |

---

## Project structure (extends your current `uv` init)

Your existing files are marked **(exists)**. Everything else is what you add. This keeps the `uv` conventions (`pyproject.toml`, `uv.lock`, `.venv`, package under `src/`).

```
dengue-climate-nepal/
├── .venv/                      (exists)
├── .python-version             (exists)
├── .gitignore                  (exists) — add data/raw/, data/processed/, outputs/, .venv/
├── pyproject.toml              (exists) — deps added via `uv add`
├── uv.lock                     (exists)
├── README.md                   (exists) — fill in run instructions
├── main.py                     (exists) — becomes the CLI dispatcher (calls phases)
├── config.yaml                 # study years, elevation bands, lags, paths
│
├── data/                       (exists)
│   ├── raw/                    # IMMUTABLE — never hand-edit
│   │   ├── climate/            # NASA POWER weather csv
│   │   ├── dengue/             # EDCD year-end PDFs / embedded Excel (2022–2024)
│   │   │   └── opendengue/     # OpenDengue extract (validator)
│   │   └── reference/
│   │       └── district_elevation.csv
│   ├── interim/                # precip-fixed weather, partially cleaned
│   └── processed/              # analysis-ready (gitignored)
│       ├── climate_monthly.parquet
│       ├── dengue_monthly.parquet
│       └── analysis_panel.parquet
│
├── src/
│   └── dengue_climate/         # importable package
│       ├── __init__.py
│       ├── config.py           # loads config.yaml
│       ├── data/
│       │   ├── fix_precip.py        # NASA POWER precip rebuild (Phase 1)
│       │   ├── aggregate_climate.py # daily → monthly (Phase 1)
│       │   ├── read_edcd_2022.py    # per-year readers (Phase 2)
│       │   ├── read_edcd_2023.py
│       │   ├── read_edcd_2024.py
│       │   ├── normalize_names.py   # canonical district names
│       │   └── validate_dengue.py   # sum-equals-total + OpenDengue cross-check
│       ├── build_panel.py      # join dengue+climate+elevation (Phase 3)
│       ├── analysis/
│       │   ├── eda.py
│       │   ├── crosscorr.py    # monthly lag analysis (Phase 5)
│       │   └── models.py       # negative binomial + validation (Phase 6)
│       └── viz/
│           └── plots.py
│
├── notebooks/
│   ├── 01_eda.ipynb
│   ├── 02_lag.ipynb
│   └── 03_model.ipynb
│
├── outputs/                    # gitignored
│   ├── figures/
│   └── tables/
│
├── reports/
│   ├── eda_findings.md
│   └── final_report.md
│
├── app/                        # optional Phase 8
│   └── dashboard.py
│
└── tests/
    ├── test_normalize_names.py
    ├── test_aggregate_climate.py
    └── test_build_panel.py
```

**How `main.py` ties it together** — a thin dispatcher so each phase is one command:
```bash
uv run python main.py fix-precip       # Phase 1
uv run python main.py climate-monthly  # Phase 1
uv run python main.py dengue            # Phase 2
uv run python main.py panel             # Phase 3
uv run python main.py all               # run the whole pipeline from raw
```

**`.gitignore` additions:** `data/raw/`, `data/interim/`, `data/processed/`, `outputs/`, `.venv/`, `nasa_power_cache/`. Keep `reports/` and `src/` tracked. (Keep raw out of git if files are large; otherwise track raw and gitignore only `processed/` + `outputs/`.)
```

