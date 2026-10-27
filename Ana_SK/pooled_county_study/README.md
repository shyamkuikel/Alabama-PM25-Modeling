# Pooled Alabama county PM2.5 prediction study

## Results summary at a glance

This summarizes the [unchanged four-page PDF](PM25_Pooled_County_Study_Summary.pdf). All ten counties were merged into **3,650 county-days**, with **3,580 observed cleaned concentrations**. Three expanding chronological folds supplied 1,783 validation cases; final October-December evaluation used **887 shared county-days**. Five learned families were tuned; persistence has no trainable settings. Stochastic predictions average three seeds.

| Model | Mean validation MAE | Test MAE | Test RMSE | High-day test MAE |
| --- | ---: | ---: | ---: | ---: |
| CNN-LSTM | 1.915 | 2.113 | 2.734 | 4.435 |
| LSTM | 1.876 | 2.133 | 2.750 | 4.448 |
| Ridge | 1.934 | 2.186 | 2.823 | 4.312 |
| CNN-only | 2.075 | 2.186 | 2.870 | 3.872 |
| Random forest | 1.902 | 2.191 | 2.808 | 4.370 |
| Persistence | 1.990 | 2.478 | 3.299 | 3.674 |

MAE and RMSE use micrograms per cubic meter; lower is better. Validation MAE is an unweighted average of three folds and participated in tuning. High-day error uses only **27** cases above county-specific January-September 95th percentiles.

![Validation and test model comparison](results/model_comparison.png)

### What the results support

- **LSTM led validation (1.876); CNN-LSTM narrowly led the test (2.113).** CNN-LSTM reduced test MAE by about 14.7% versus persistence.
- The hybrid-minus-LSTM MAE difference was **-0.0201**, with a paired 95% seven-day block-bootstrap interval **[-0.0558, 0.0088]**. It crosses zero: a reliable benefit from adding CNN is not demonstrated. LSTM remains a simpler competitive starting point.
- All learned families improved overall test MAE, but **persistence performed best on high days** (3.674 versus hybrid 4.435). Average accuracy does not establish better pollution-peak prediction.
- County winners differed: CNN-LSTM led five counties, LSTM three, random forest Etowah and ridge Mobile. Jefferson had the largest errors and Sumter the smallest. Hybrid MAE was 1.833 in coastal Baldwin and 1.837 in Mobile; this does not identify geography as the cause.

![County test MAE](results/county_mae.png)

**Limits:** only one year is available, test months had already been inspected, nearby counties/shared weather create dependence, and weather provenance remains partly unresolved. These are site observations, not county-wide averages. Bootstrap intervals are pointwise and conditional on fitted models. Stronger conclusions require untouched years and a separate peak-prediction objective.

See [full findings](STUDY_RESULTS_AND_CONCLUSIONS.md), [verification evidence](FULL_RUN_VERIFICATION.md) and [saved numerical results](results/README.md). Setup and full-run commands follow below.

This separate study merges all ten county worksheets into one panel and compares persistence, ridge regression, random forest, CNN-only, LSTM-only and CNN-LSTM using three expanding-window validation folds. Every model implementation and candidate grid has its own file in `models/`. Shared code handles preparation, temporal windows, fitting, evaluation and forecasting.

## Files and data

- `data/merged_counties.xlsx`: one combined Excel workbook with Clean panel, Raw panel, Quality summary and Dictionary. Each panel has 3,650 county-day rows. Raw measurements remain intact; the cleaned panel has 3,580 observed PM2.5 values.
- `data/merged_raw.csv` and `data/merged_clean.csv`: matching flat tables for analysis. The merged panel is sorted by date and county. Keep county identity; never concatenate counties into one temporal sequence or average them into a single target.
- `data/cleaning_log.csv`: cell-level changes and reasons. `data/quality_summary.csv` reports county missingness. Source sheet and Excel row preserve record provenance.
- `prepare_data.py`: merges the original sheets and regenerates CSV data, quality summaries and workbook payload. The provided Excel file is verified against both CSV panels. Spreadsheet export in this Codex session uses Artifact Tool; ordinary Python modeling does not require it.
- `preprocessing.py`, `splits.py`, `training.py`: shared leakage-safe data preparation and fitting.
- `models/persistence.py`, `ridge.py`, `random_forest.py`, `cnn.py`, `lstm.py`, `cnn_lstm.py`: independent model definitions and tuning grids.
- `run_study.py`: full comparison. `predict_saved.py`: inference. `verify_results.py` and `test_pipeline.py`: validation.
- `results/`: fitted models, test and validation predictions, metrics, selected settings, training histories, fold audits, preprocessing, figures, environment metadata and findings.

## Setup on an M1 Mac

Use native ARM64 Python 3.12. From this folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m unittest -v test_pipeline.py
```

Run the complete experiment from the merged Excel file:

```sh
python run_study.py --data data/merged_counties.xlsx --device auto --output results_new
python verify_results.py --data data/merged_counties.xlsx --results results_new
```

Alternatively use `--data data/merged_clean.csv`. Select an unused output directory: the script refuses to overwrite a completed selection record. A full run was executed and saved in `results/`; CPU execution was verified on ARM64. Auto mode attempts Apple's MPS backend with a forward/backward probe, otherwise CPU; MPS was unavailable in this session. No TensorFlow-specific packages are needed.

Short end-to-end check (not meaningful model-performance results):

```sh
python run_study.py --smoke --device cpu --output smoke_results
```

Run an individual model while keeping the same fold and tuning logic:

```sh
python -m models.ridge --data data/merged_counties.xlsx --output ridge_run
python -m models.random_forest --data data/merged_counties.xlsx --output forest_run
python -m models.cnn --data data/merged_counties.xlsx --output cnn_run
python -m models.lstm --data data/merged_counties.xlsx --output lstm_run
python -m models.cnn_lstm --data data/merged_counties.xlsx --output hybrid_run
python -m models.persistence --data data/merged_counties.xlsx --output persistence_run
```

Regenerate CSV panels from the original workbook:

```sh
python prepare_data.py --workbook ../Meterological_data_ALAbama_copy.xlsx
```

Use a separate `--output` data directory and `--negative-policy retain` for a prespecified negative-value sensitivity run. Do not overwrite the primary dataset while preserving results that refer to its hash. Rebuilding CSVs does not automatically update the provided Excel workbook; use the CSV input for refreshed Python runs or regenerate the workbook through the spreadsheet builder in Codex.

## Cleaning decisions

Normalize county names and dates; require unique county/date keys; reject nonnumeric/infinite measurements; insert missing daily rows if needed. Replace joint-zero temperature/dew point/humidity weather placeholders, nonpositive pressure, humidity outside 0–100 and negative wind/precipitation with missing values. Default negative PM2.5 readings become missing rather than zero; raw values and flags remain available. Positive extremes are retained, not removed based on full-year distributions. This policy is stricter than the earlier initial study and changes forecast eligibility.

No target imputation or future interpolation is used. Each training period fits county-specific feature medians, means and standard deviations. All-missing features fall back to pooled training medians, then zero if the entire training feature is missing. Constant features get standard deviation 1. Missingness indicators accompany all seven variables. Missing targets or missing previous-day PM2.5 make a prediction ineligible, equally for every model; earlier missing predictors are training-median imputed.

## Temporal k-fold design

| Fold | Outer training | Outer validation | Inner stopping period |
|---|---|---|---|
| 1 | January–March | April–May | Final 21 days of outer training |
| 2 | January–May | June–July | Final 21 days of outer training |
| 3 | January–July | August–September | Final 21 days of outer training |

This is three-fold time-series cross-validation, not shuffled k-fold. Counties always share calendar boundaries. Model histories end the day before the target; the same county's earlier validation observations may enter later validation histories because the task is daily one-step forecasting. This is not a recursive multi-month forecast. No same-day or future weather enters a prediction.

Neural early stopping is performed inside each outer training period. Its imputation/scaling uses only the earlier inner-training segment. The model is then initialized again and fitted on the full outer training period using the selected epoch count, with outer-training preprocessing. Only then is the outer validation fold scored. Thus outer validation does not simultaneously serve as early-stopping data.

Select each family's settings by the lowest unweighted mean of its three outer-fold ensemble MAEs; ties follow candidate-list order. Stochastic model families use all seeds 11, 22 and 33, including random forest. Ridge and persistence are deterministic. Single-run metrics are saved separately. Selected CV performance participated in tuning; it is not an unbiased nested-CV performance estimate. Final neural epochs are the per-seed median of the selected candidate's inner stopping epochs across the three folds.

After all settings are frozen, fit every learned family on January–September and evaluate October–December on identical county-days. October–December outcomes were inspected in prior studies, so this is an exploratory evaluation, not a fresh confirmatory test. The pipeline supports forecasting future dates, but new years of untouched observations are needed for stronger validation.

## Prespecified hyperparameter search

| Model | Tuned settings | Fixed settings |
|---|---|---|
| Persistence | None: no trainable parameters | Previous-day concentration |
| Ridge | Alpha 1, 10, 100, 1000 | Full flattened histories and one-hot county identity |
| Random forest | Depth 6/unlimited; minimum leaf 5/15 | 150 trees, feature fraction 0.7, three seeds |
| CNN-only | Width 8/16; learning rate 0.001/0.0003 | Causal kernel 3, full-window projection, dropout 0.1 |
| LSTM-only | Width 8/16; learning rate 0.001/0.0003 | One LSTM layer, dropout 0.1 in prediction head |
| CNN-LSTM | Width 8/16; learning rate 0.001/0.0003 | Causal kernel 3, one LSTM layer, dropout 0.1 |

All neural models share a county embedding, target-calendar features, residual persistence skip, AdamW weight decay 0.001, batch size 64, gradient clipping 1.0, maximum 60 inner epochs and patience 8. CNN-only sees every encoded day, not just the final convolution kernel. All five learned families predict a standardized correction to persistence. Neural fitting minimizes standardized L1 error; ridge and forest fit squared error. Capacities and candidate budgets differ, so the comparison does not isolate architecture alone. A modest search is appropriate to one year of data; exhaustive tuning is neither necessary nor supported by the data volume.

Lookback remains 14 days, fixed before this experiment. Changing it requires a separate prespecified experiment and output folder; do not select it by October–December errors. Pooling increases rows, not years or independent seasonal cycles. Monitor observations represent sites within counties, not spatial county means. Weather provenance, pressure/precipitation definitions and reporting delays remain partly unresolved.

## Results and forecasting

Read `results/REPORT.md` for actual CV and test rankings, uncertainty and conclusions. MAE, RMSE, bias and R-squared are reported overall and by county. High-day MAE uses training-period county 95th percentiles. Paired 95% MAE-difference intervals use 1,000 joint-county circular seven-day block-bootstrap samples. These pointwise intervals condition on fitted models and are not multiple-comparison adjusted. Fold SD describes three periods, not a standard error. Seed SD is not a forecast uncertainty interval.

Forecast from saved models using only observations preceding the requested date:

```sh
python predict_saved.py --results results --data data/merged_counties.xlsx --date 2026-01-01 --device auto --output forecasts.csv
```

For later dates, supply an updated cleaned panel containing the historical inputs. Counties with insufficient history or missing previous-day PM2.5 are omitted. Only load trusted local checkpoints; joblib files can execute Python code. This is a research pipeline, not a verified real-time monitoring system.
