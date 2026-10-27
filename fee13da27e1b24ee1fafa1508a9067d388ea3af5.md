# Next-day PM2.5 prediction

## Held-out performance

| model | n | mae | rmse | r_squared | bias_pred_minus_observed |
| --- | --- | --- | --- | --- | --- |
| random_forest | 897 | 2.270 | 2.876 | 0.307 | 0.875 |
| validation_selected_per_county | 897 | 2.276 | 2.876 | 0.307 | 0.867 |
| ridge_weather | 897 | 2.281 | 2.868 | 0.311 | 0.467 |
| ridge_pca_weather | 897 | 2.298 | 2.867 | 0.312 | 0.560 |
| persistence | 897 | 2.476 | 3.299 | 0.088 | 0.015 |
| ridge_lag_calendar | 897 | 2.507 | 3.104 | 0.193 | 0.742 |
| training_mean | 897 | 2.878 | 3.498 | -0.025 | 1.020 |

The validation-selected model improves MAE over persistence in 7/10 counties; 3/10 paired 7-day bootstrap intervals are entirely below zero. These intervals are exploratory and pointwise.

## County-specific comparisons

| county | selected_model | mae_difference_vs_persistence | ci_low_block7 | ci_high_block7 |
| --- | --- | --- | --- | --- |
| Baldwin | random_forest | 0.162 | -0.247 | 0.609 |
| Clay | random_forest | -0.263 | -0.657 | 0.138 |
| DeKalb | random_forest | -0.384 | -0.744 | 0.003 |
| Etowah | random_forest | -0.436 | -0.971 | -0.000 |
| Jefferson | random_forest | -0.203 | -1.131 | 0.588 |
| Mobile | random_forest | 0.049 | -0.335 | 0.504 |
| Montgomery | random_forest | -0.518 | -0.823 | -0.239 |
| Morgan | random_forest | -0.494 | -0.801 | -0.167 |
| Sumter | ridge_weather | 0.043 | -0.161 | 0.234 |
| Tuscaloosa | random_forest | -0.015 | -0.339 | 0.356 |

## Forecast question and information availability

At the end of day t−1, predict day t PM2.5 using PM2.5 at t−1, t−2 and t−7, weather at t−1, and known calendar features (two annual sine/cosine harmonics and weekend). This assumes those previous-day values are actually available by the forecast time; the workbook has no reporting-delay metadata. Same-day weather is excluded.

## Validation design

Expanding-window validation predicts July, August and September separately using only earlier dates. Hyperparameters minimize pooled validation MAE within each county. The best model family is also selected using these validation months only. Models then refit on January–September and remain fixed for October–December. This is a rolling one-day-ahead evaluation using newly observed lagged inputs each day, not a 92-day forecast made on October 1. October–December data never fit model parameters, imputers, scaling or PCA.

All models and baselines share test dates with observed target and yesterday's PM2.5. Missing targets are never imputed. Missing other predictors are training-median imputed; missing indicators are included except in the weather-PCA branch. Missing targets or lag-one readings limit test coverage, reported in the parameter table.

## Models

Training-mean and persistence baselines; ridge with PM2.5 lags/calendar; ridge adding lagged weather; ridge using training-fitted weather PCs retaining at least 80% of weather variance; random forest with lagged weather and PM2.5/calendar. Ridge alpha grid is 1/10/100. Forest has 150 trees, maximum depth 6 and leaf-size grid 5/15. All configurations and fold scores are saved. PCA signs are arbitrary; compare forecasts, not signs. PCA explains weather variance, not PM2.5 predictive importance.

## Limitations and diagnostics

MAE/RMSE/bias are in workbook units; R² can be negative. Pooling weights available county-days equally and does not make them independent. Negative-target-exclusion MAE evaluates the same fitted models on a restricted target set, not a retrained sensitivity. Predictions are not clipped. The selected-model permutation table describes held-out error sensitivity to individual feature shuffling, which disrupts time structure and correlated predictors; it is neither causal importance nor an inference test and is not used for model changes. A future year is needed for stronger external validation.

## Files

Fold scores, selected parameters, county and pooled test metrics, daily predictions, paired error intervals, PCA variance, permutation sensitivity, MAE heatmap, forecast panels and fitted joblib models. Load joblib files only from this trusted local run.

## Scope and provenance

Source: `../Meterological_data_ALAbama_copy.xlsx` relative to initial_study. All concentrations and weather values use workbook units, which are unverified. County names are sheet labels, not proof of county-wide representativeness. The Jefferson worksheet is named Jefferson_NB in the source. These are exploratory results for 2025, not causal estimates, regulatory determinations, or evidence of long-term trends. See `../METHODS.md` and the root quality tables.
