# PM2.5: six-model comparison on Apple Silicon

Compare persistence, ridge regression, random forest, CNN-only, LSTM-only and CNN-LSTM. The experiment forecasts the next daily PM2.5 value for each county using the preceding 14 days. It pools training across counties.

## Setup and run

Use a native ARM64 Python 3.12 environment on an M1 Mac. From this folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m unittest -v test_comparison.py
python compare_models.py --device auto
```

Auto mode tries PyTorch's Apple Metal (MPS) backend and falls back to CPU. `--device cpu` forces CPU. This package was executed on ARM64 CPU; MPS execution was unavailable in the testing session. No tensorflow-macos or tensorflow-metal packages are needed.

The default workbook is `../../../Meterological_data_ALAbama_copy.xlsx`, resolved relative to the source file. Override it with `--workbook /absolute/path/to/file.xlsx`. Keep the adjacent `../cnn_lstm/train_cnn_lstm.py`: `data.py` imports its shared workbook reading, quality checks, preprocessing and window functions. It does not import fitted models or old predictions.

For a short pipeline check, use a separate output directory:

```sh
python compare_models.py --epochs 2 --widths 8 --seeds 11 --rf-trees 20 --bootstrap 50 --output smoke_results
```

## Experimental design

- Train January–June 2025; select settings and stopping epochs on July–September.
- Refit using January–September with frozen selected settings; evaluate October–December.
- Fit imputation and scaling only within the appropriate training period. Windows stop the day before the target. No future weather is supplied.
- All learned models receive the same seven historical variables, missingness indicators, target-date calendar information and county identity. Neural networks use a county embedding; classical models use one-hot county identity.
- All learned models predict a correction to yesterday's PM2.5. Persistence itself simply predicts yesterday's observed value. This makes the comparison about improving that strong baseline.
- CNN-only uses all encoded historical days. LSTM-only reads raw histories. CNN-LSTM passes convolution features into an LSTM. Their heads and dropout are shared in design, but parameter counts differ and are reported.
- Neural models use absolute-error loss, early stopping, width candidates 8/16 and seeds 11/22/33. Ridge selects alpha from 1/10/100/1000. Random forest selects depth 6/unlimited and minimum leaf size 5/15 with 150 trees and the same three seeds. Classical models fit squared error. Tuning budgets and capacities are not identical.
- Primary stochastic-model predictions average all three prescribed seeds. Individual-seed results are also reported; no seed is selected using test performance.
- Evaluate only dates with an observed target and observed previous-day PM2.5, identically across all models. Earlier missing inputs use training medians with missingness indicators.

## Outputs

`results/REPORT.md` explains results and limitations. CSV files contain pooled/county MAE, RMSE, bias, R-squared, seed results, predictions, validation scores, training history, sample audits and quality flags. PNG figures show pooled errors, county errors, validation curves and forecasts. `models/` stores every final fitted model. JSON files record preprocessing, selected settings, versions, source hashes, model manifests and verification checks.

Load the fitted models for a specified forecast date using only earlier workbook rows:

```sh
python predict_models.py --date 2026-01-01 --device auto
```

Add new observations to a separate workbook and pass `--workbook` when forecasting later dates. Counties with insufficient history or missing previous-day PM2.5 are omitted. Only load trusted local model files: joblib files can execute Python code.

`paired_model_mae_intervals.csv` gives paired MAE differences with a circular seven-day block bootstrap that keeps counties together. Negative differences favor model A. These are exploratory pointwise intervals, not multiple-comparison-adjusted significance tests. Seed variability and temporal sampling uncertainty are different and are reported separately.

The October–December outcomes have already been inspected in earlier studies: this is an exploratory benchmark, not a fresh confirmatory test. One year of data cannot establish generalization to later years. Workbook units, measurement quality and real-time reporting delays need confirmation. Negative PM2.5 readings remain in the primary analysis, with a separate nonnegative-target sensitivity metric. A CNN-LSTM advantage should be judged against both simpler neural networks and classical baselines, including its uncertainty and county-level consistency.

For a new lookback experiment, use a separate output directory and predeclare it; do not choose lookback based on October–December performance. Future work should validate the chosen approach on additional untouched years.
