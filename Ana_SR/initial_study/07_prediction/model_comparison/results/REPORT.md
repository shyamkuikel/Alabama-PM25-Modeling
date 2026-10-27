# CNN / LSTM / CNN-LSTM and baseline comparison

Actual device: cpu. Lookback: 14 days. Seeds: [11, 22, 33]. All learned models were newly trained pooled across counties with the same histories, missingness channels, calendar features, county identity and test county-days.

## Pooled test performance

| model | n | mae | rmse | bias | r_squared | high_days_n | high_days_mae |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cnn_lstm | 897 | 2.1111 | 2.7174 | 0.2615 | 0.3813 | 27 | 4.6099 |
| lstm | 897 | 2.1265 | 2.7369 | 0.2516 | 0.3724 | 27 | 4.4291 |
| ridge | 897 | 2.2000 | 2.8365 | 0.5209 | 0.3259 | 27 | 4.3014 |
| random_forest | 897 | 2.2028 | 2.8163 | 0.5682 | 0.3354 | 27 | 4.3521 |
| cnn | 897 | 2.4693 | 3.2932 | 0.2149 | 0.0913 | 27 | 3.5424 |
| persistence | 897 | 2.4764 | 3.2987 | 0.0146 | 0.0883 | 27 | 3.6741 |

The lowest observed test MAE is 2.1111 (cnn_lstm). CNN-LSTM MAE is 2.1111. This ranking is descriptive; it was not used to select or refit models.

## Does the hybrid add value?

| comparison | mae_difference | ci_low | ci_high | mae_improvement_percent |
| --- | --- | --- | --- | --- |
| CNN-LSTM minus cnn | -0.3582 | -0.5116 | -0.1983 | 14.5064 |
| CNN-LSTM minus lstm | -0.0154 | -0.0698 | 0.0366 | 0.7253 |
| CNN-LSTM minus ridge | -0.0889 | -0.1579 | -0.0222 | 4.0410 |
| CNN-LSTM minus random_forest | -0.0918 | -0.1787 | -0.0073 | 4.1657 |
| CNN-LSTM minus persistence | -0.3653 | -0.5237 | -0.2050 | 14.7509 |

Negative MAE differences favor CNN-LSTM. Intervals use paired seven-day calendar-block resampling with all counties resampled together. They are exploratory pointwise intervals, not simultaneous multiple-comparison intervals, and condition on the fitted ensembles. An interval crossing zero does not clearly distinguish the models. It does not establish equality.

## Single-run variability

| model | seed | n | mae | rmse | bias | r_squared |
| --- | --- | --- | --- | --- | --- | --- |
| cnn | 11 | 897 | 2.4760 | 3.2985 | 0.1166 | 0.0884 |
| cnn | 22 | 897 | 2.4645 | 3.2874 | 0.3772 | 0.0945 |
| cnn | 33 | 897 | 2.4755 | 3.3014 | 0.1510 | 0.0868 |
| lstm | 11 | 897 | 2.1672 | 2.7733 | 0.4074 | 0.3556 |
| lstm | 22 | 897 | 2.1224 | 2.7501 | 0.1335 | 0.3663 |
| lstm | 33 | 897 | 2.1266 | 2.7304 | 0.2139 | 0.3754 |
| cnn_lstm | 11 | 897 | 2.1918 | 2.8150 | 0.5595 | 0.3361 |
| cnn_lstm | 22 | 897 | 2.1208 | 2.7364 | 0.2845 | 0.3726 |
| cnn_lstm | 33 | 897 | 2.0887 | 2.6995 | -0.0593 | 0.3894 |
| random_forest | 11 | 897 | 2.2058 | 2.8204 | 0.5675 | 0.3335 |
| random_forest | 22 | 897 | 2.2063 | 2.8250 | 0.5960 | 0.3313 |
| random_forest | 33 | 897 | 2.2020 | 2.8128 | 0.5412 | 0.3371 |

Primary CNN, LSTM, CNN-LSTM and random-forest predictions average ALL declared seeds; ridge and persistence are deterministic. Per-seed metrics also allow single-model comparisons without crediting only neural networks for ensembling. Across-seed SD is not a prediction interval.

## Design

Selection training: Jan-Jun (1620 windows); validation: Jul-Sep (902); refit training: Jan-Sep (2522); test: Oct-Dec (897). Each sequence stays within one county and ends the day before its target. Preprocessing fits Jan-Jun for selection and Jan-Sep for refitting. Missing targets and missing yesterday PM2.5 are excluded; older missing inputs are training-median imputed with masks. No future interpolation or test fitting is used.

All five learned families predict a correction to persistence in county-standardized units. CNN-only reads all encoded days through a flattened projection; LSTM-only reads the same full sequence; CNN-LSTM convolves then recurs. Neural heads share county embedding, calendar, dropout, optimizer, loss and persistence skip. Ridge and forest flatten the same history and receive one-hot county identity. Parameter counts differ and are reported.

Neural width is selected by mean individual-seed validation MAE; each seed gets a validation-selected epoch count. Ridge alpha and forest depth/leaf size are selected with the same validation dates and original-unit MAE criterion. Candidate budgets differ and are explicit in validation_scores.csv. Neural training uses standardized L1 loss; ridge and forest use squared-error fitting, so comparisons do not isolate architecture alone. All families refit with chosen settings before test scoring.

## Limits

Oct-Dec has already been inspected in earlier analyses, so this is not a fresh confirmatory test. One year, overlapping windows, shared weather inputs and correlated counties limit generalization. More years are needed. Units and reporting delays are unverified. Training-period county 95th percentiles define high days; some test subsets can be small. Negative readings remain in the primary analysis and forecasts are not clipped. The nonnegative-target metric is an evaluation sensitivity, not a retraining. MPS acceleration is used only when available; see metadata for the actual device.

## Selected settings

```json
{
  "cnn": {
    "width": 8,
    "mean_validation_mae": 1.8253764537064596,
    "epochs_by_seed": {
      "11": 1,
      "22": 3,
      "33": 1
    }
  },
  "lstm": {
    "width": 8,
    "mean_validation_mae": 1.6934440443587029,
    "epochs_by_seed": {
      "11": 9,
      "22": 11,
      "33": 12
    }
  },
  "cnn_lstm": {
    "width": 16,
    "mean_validation_mae": 1.6910370853375312,
    "epochs_by_seed": {
      "11": 7,
      "22": 9,
      "33": 14
    }
  },
  "ridge": {
    "alpha": 1000.0,
    "validation_mae": 1.9010007278547267
  },
  "random_forest": {
    "config": {
      "n_estimators": 150,
      "max_depth": 6,
      "min_samples_leaf": 15,
      "max_features": 0.7,
      "criterion": "squared_error",
      "n_jobs": 2
    },
    "mean_validation_mae": 1.716161088640006
  }
}
```
