# Pooled county PM2.5 study with three-fold time-series validation

## Data and cleaning

Ten county sheets were merged into 3,650 county-day rows, with 3,580 observed cleaned PM2.5 values. County identity and original sheet/row provenance remain available. Raw observations are preserved separately. Impossible weather placeholders are missing in the analysis copy. By default, negative PM2.5 measurements are missing for both predictors and targets, not clipped to zero. Training-period imputation is performed separately inside each fold; the merged cleaned dataset itself is not globally imputed.

## Validation and tuning

Fold 1: train Jan–Mar, validate Apr–May. Fold 2: train Jan–May, validate Jun–Jul. Fold 3: train Jan–Jul, validate Aug–Sep. All counties share date boundaries. Each 14-day sequence stays within a county and ends the day before its target. Outer validation measures daily one-step forecasts using previously observed days; it is not a recursive forecast made two months in advance.

Neural early stopping uses only the final 21 days inside each outer training period, with independently fitted inner preprocessing. The model is then refitted on the full outer training period for that duration before scoring outer validation. Candidate settings minimize the unweighted mean of three outer-fold ensemble MAEs. Final neural epochs are each seed’s median stopping duration for the selected candidate across folds. All settings are frozen before Jan–Sep final fitting and Oct–Dec scoring. This is temporal cross-validation with inner stopping, not a fully nested outer performance-estimation study; reported selected CV scores also participated in selection.

Persistence has no trainable parameters or hyperparameters. Ridge tunes alpha; forest tunes depth and leaf size; CNN, LSTM and CNN-LSTM each tune width and learning rate. Neural loss is standardized L1, classical fits use squared error, and parameter counts/tuning budgets differ. Lookback, convolution kernel, dropout and other fixed settings are documented rather than exhaustively searched. All learned models predict a correction to persistence from the same histories, missingness, calendar and county information.

## Selected cross-validation results

| model | mean_fold_mae | fold_mae_sd | mean_fold_rmse | validation_cases |
| --- | --- | --- | --- | --- |
| lstm | 1.8757 | 0.1627 | 2.4609 | 1783 |
| random_forest | 1.9017 | 0.1832 | 2.4563 | 1783 |
| cnn_lstm | 1.9146 | 0.1888 | 2.5202 | 1783 |
| ridge | 1.9343 | 0.0751 | 2.7628 | 1783 |
| persistence | 1.9904 | 0.2108 | 2.6571 | 1783 |
| cnn | 2.0754 | 0.0833 | 3.0507 | 1783 |

Fold SD describes variation across three time periods, not a standard error.

## Exploratory test results

| model | n | mae | rmse | bias | r_squared | high_days_n | high_days_mae |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cnn_lstm | 887 | 2.1131 | 2.7337 | 0.2745 | 0.3549 | 27 | 4.4352 |
| lstm | 887 | 2.1332 | 2.7504 | 0.2388 | 0.3470 | 27 | 4.4483 |
| ridge | 887 | 2.1855 | 2.8232 | 0.4913 | 0.3120 | 27 | 4.3115 |
| cnn | 887 | 2.1862 | 2.8701 | 0.4695 | 0.2889 | 27 | 3.8719 |
| random_forest | 887 | 2.1907 | 2.8083 | 0.5549 | 0.3192 | 27 | 4.3704 |
| persistence | 887 | 2.4780 | 3.2994 | 0.0167 | 0.0603 | 27 | 3.6741 |

Stochastic-family primary predictions average all declared seeds, including the forest. Individual-run metrics are saved separately. High days use each county’s Jan–Sep 95th percentile; their small count limits conclusions about extreme pollution.

CNN-LSTM minus LSTM test MAE difference: -0.0201 µg/m³, paired 95% block-bootstrap interval [-0.0558, 0.0088]. The interval crosses zero, so this experiment does not clearly distinguish their average error.

## Conclusions and limits

The lowest observed test MAE was 2.1131 for cnn_lstm. This ranking is descriptive and does not establish performance in a new year or county. Compare CV consistency, uncertainty, county results and high-day errors before choosing a model.

The test months were previously inspected in earlier studies, so this remains exploratory. Pooling increases training rows but not years or independent seasonal cycles. Adjacent counties and duplicated weather inputs create dependence. A seven-day paired calendar-block bootstrap keeps counties together; its intervals are pointwise, not adjusted for multiple comparisons, and condition on the fitted ensembles. Monthly and annual distribution changes remain a concern. Source matching supports PM2.5 units, but weather provenance, pressure/precipitation definitions and real-time availability remain partly unresolved. These measurements represent monitoring sites within counties, not county-wide averages. Negative-value removal changes eligibility compared with the earlier study; this is a new experiment, not a direct replication. Additional untouched years and an explicitly defined peak-prediction objective are needed for stronger conclusions.

## Practical interpretation

LSTM had the lowest selected mean validation MAE (1.8757), whereas CNN-LSTM had the lowest observed test MAE (2.1131). The hybrid reduced test MAE by approximately 14.7% against persistence, but only 0.0201 µg/m³ against LSTM, with an interval that crosses zero. These results support LSTM as a simpler competitive starting point and do not demonstrate a reliable benefit from adding convolution. A final model choice should follow a prespecified validation rule rather than choosing whichever architecture won the previously inspected test.

All learned families reduced overall test MAE relative to persistence. However, persistence had the lowest MAE on the 27 test high days (3.6741); CNN-LSTM high-day MAE was 4.4352. Lower overall error therefore does not establish better prediction of pollution peaks. County rankings also differ: no architecture wins everywhere.

## Selected settings

```json
{
  "persistence": {
    "candidate_id": 0,
    "parameters": {},
    "mean_fold_mae": 1.990406088851343
  },
  "ridge": {
    "candidate_id": 3,
    "parameters": {
      "alpha": 1000.0
    },
    "mean_fold_mae": 1.934306787114398
  },
  "random_forest": {
    "candidate_id": 1,
    "parameters": {
      "max_depth": 6,
      "min_samples_leaf": 15
    },
    "mean_fold_mae": 1.901735518151626
  },
  "cnn": {
    "candidate_id": 1,
    "parameters": {
      "width": 8,
      "learning_rate": 0.0003,
      "dropout": 0.1
    },
    "mean_fold_mae": 2.0754366513417093,
    "epochs_by_seed": {
      "11": 51,
      "22": 35,
      "33": 49
    }
  },
  "lstm": {
    "candidate_id": 1,
    "parameters": {
      "width": 8,
      "learning_rate": 0.0003,
      "dropout": 0.1
    },
    "mean_fold_mae": 1.8757399335954839,
    "epochs_by_seed": {
      "11": 43,
      "22": 30,
      "33": 56
    }
  },
  "cnn_lstm": {
    "candidate_id": 1,
    "parameters": {
      "width": 8,
      "learning_rate": 0.0003,
      "dropout": 0.1
    },
    "mean_fold_mae": 1.914555958044896,
    "epochs_by_seed": {
      "11": 49,
      "22": 40,
      "33": 46
    }
  }
}
```
