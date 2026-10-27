# CNN-LSTM for PM2.5 on Apple Silicon

This small PyTorch model runs on an Apple M1 Mac using Metal Performance Shaders
(MPS) when available, with a CPU fallback. It does not require CUDA. Use a native
arm64 Python 3.12 virtual environment, not Python running under Rosetta.
The installed PyTorch wheel must support your macOS version; the tested PyTorch
2.14.1 wheel requires macOS 14 or newer. CPU mode still requires a compatible
PyTorch installation. On an older macOS, upgrade macOS or use a compatible older
PyTorch release from the official installation page.

## Install and run

In Terminal:

```sh
cd /Users/sijanregmi/Documents/Codex/2026-10-11/can/PM2.5_Study/Ana_SR/initial_study/07_prediction/cnn_lstm
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "import platform, torch; print(platform.machine()); print(torch.__version__); print('MPS available:', torch.backends.mps.is_available())"
python train_cnn_lstm.py --device auto
```

If `python3` is not native arm64 or is not a supported version, use the explicit
path/name of your native Python 3.12 installation in the venv command. Choose
`--device cpu` to run on the M1 CPU, or `--device mps` to require GPU execution.
Auto mode probes forward/backward Conv1D-LSTM operations before choosing MPS.
The runtime prints the actual selected device. CPU can be faster for this tiny
network; MPS availability is not a promise of acceleration.

The default workbook is the existing copied Excel file in Ana_SR. The input
workbook and previous study results are preserved. Outputs go into `results/`.
Reruns overwrite matching results; choose a new folder when comparing settings:

```sh
python train_cnn_lstm.py --lookback 7 --output results_7days
python train_cnn_lstm.py --lookback 14 --seeds 11 22 33 --output results_14days
```

Choose lookback based on validation, never by choosing the most favorable test
score. `--epochs`, `--patience`, `--batch-size` and `--learning-rate` are available.
For a quick execution check rather than an accuracy experiment:

```sh
python train_cnn_lstm.py --device cpu --epochs 2 --seeds 11 --output smoke_results
python -m unittest test_cnn_lstm.py -v
```

## What the model does

Each sample contains 14 historical days (7 is also supported). The seven numeric
features are PM2.5, temperature, dew point, relative humidity, wind speed,
pressure and precipitation. Seven additional channels indicate missing inputs.
Every sequence is within one county and ends on the day before the target.

```text
Historical sequence: [batch, days, 14 channels]
    -> left-padded causal Conv1D: 16 filters, kernel size 3
    -> ReLU and dropout 0.1
    -> LSTM: 16 hidden units
    -> concatenate final hidden state, county embedding and target-date calendar
    -> small dense head predicts a correction
    -> add yesterday's standardized PM2.5
    -> convert back to original concentration units
```

The final output layer starts at zero, so the untrained model equals persistence.
The CNN-LSTM learns a correction to that baseline. One network is shared across
all ten counties; a four-dimensional county embedding distinguishes locations.
The forecast calendar inputs are two annual sine/cosine harmonics and a weekend
indicator. The actual parameter count is recorded in run metadata.

## Chronology and missing observations

- Initial training targets: before July 1, 2025. Validation targets: July through
  September. No random split across dates or counties is used. Training batches
  may shuffle samples AFTER the chronological partitions are fixed.
- Imputation and per-county scaling fit January-June only for epoch selection.
  Median-imputed training observations contribute to predictor scaling. The
  same PM2.5 mean/SD scales both historical PM2.5 and the target.
- Early stopping selects an epoch count separately for each seed, minimizing
  pooled validation MAE in original workbook units. Training loss is standardized
  MAE, which changes the relative weight of counties compared with pooled MAE.
- For final models, preprocessing refits on January-September. Each seed starts
  a new model and trains on January-September for its selected number of epochs.
  Test targets are October-December. Models do not update during testing, but
  lagged observed inputs update each day for one-day-ahead forecasts.
- Missing targets and missing previous-day PM2.5 are excluded; older missing
  inputs use training medians plus missing indicators. No future interpolation,
  full-year scaling or target imputation is performed. All-missing county training
  columns use pooled training medians; constant scales are set to one.
- Negative PM2.5 readings remain intact. Suspect joint-zero weather placeholders
  and physically impossible weather values follow the initial-study flag rules.
  The source workbook is read-only. Measurement units are unverified.

## Outputs

`RESULTS.md`, training/validation curves, test forecast plots, pooled and county
metrics, per-seed scores and predictions, the mean-of-seeds ensemble, quality
flags, sample date audits, preprocessing JSON, run metadata and verification.
One `.pt` checkpoint per seed contains weights, architecture and fitted
preprocessing. The ensemble includes all specified seeds; it never chooses a
seed based on test performance. Seed prediction SD is not a prediction interval.

Persistence is scored on exactly the same test dates. If the prior study's daily
prediction table is present, its ridge/Ana_SK/forest and preselected-model predictions
are compared on those same county-days, with an observation-consistency check.
The previous models trained separately per county, while this network is pooled;
performance differences cannot be attributed to architecture alone.

## Load a trained model for a forecast

```sh
python predict_next_day.py --checkpoint results/model_seed_11.pt --date 2026-01-01 --output results/next_day_predictions.csv
```

The forecast script ignores target-day and later measurements, requires sufficient
history and an observed previous-day PM2.5 value, and reports skipped counties.
This example uses the final 2025 observations to produce one prediction per
eligible county for January 1, 2026. That date has no outcome in the supplied file,
so prediction accuracy cannot be evaluated. It uses a single seed checkpoint,
not the three-seed ensemble. Later forecasts require new historical observations.

## Interpretation and reproducibility

October-December results were already inspected during the earlier study. This is
an exploratory comparison, not an untouched confirmatory test. One year, overlapping
windows and shared county/weather patterns limit the effective amount of information.
There is no guarantee that deep learning beats persistence or random forest. A new
year is needed for stronger evaluation. Forecasts assume previous-day inputs are
available in time; source reporting delays have not been verified.

Seeds control random initialization, dropout and batch order, but exact
cross-device/version reproducibility is not guaranteed. Checkpoint predictions are
verified after reloading on CPU with a tolerance for MPS/CPU arithmetic differences.
No full-model pickle is used; checkpoints load with `weights_only=True`.

Official references:
- https://docs.pytorch.org/docs/stable/notes/mps.html
- https://pytorch.org/get-started/locally/
- https://developer.apple.com/metal/pytorch/

## Completed verification run

Native arm64 Python 3.12.14, PyTorch 2.14.1; CPU execution verified. MPS was
not available in this session, so GPU execution has not been verified here.
Six unit tests passed; three saved checkpoints reproduced predictions after reload.
A next-day inference smoke test also passed. The 14-day, three-seed ensemble
scored MAE 2.1111 on 897 Oct-Dec county-days, versus 2.4764 for persistence
and 2.2699 for the previous random forest. This is exploratory evidence, not
a claim of statistically significant improvement. See results/RESULTS.md.
