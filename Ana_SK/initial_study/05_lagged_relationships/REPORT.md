# Persistence and delayed weather relationships

## One-day PM2.5 persistence

| county | paired_n | raw_pairwise_autocorrelation | month_demeaned_autocorrelation |
| --- | --- | --- | --- |
| Baldwin | 355 | 0.511 | 0.401 |
| Clay | 354 | 0.372 | 0.327 |
| DeKalb | 356 | 0.555 | 0.480 |
| Etowah | 350 | 0.562 | 0.497 |
| Jefferson | 353 | 0.474 | 0.382 |
| Mobile | 361 | 0.492 | 0.385 |
| Montgomery | 351 | 0.553 | 0.470 |
| Morgan | 351 | 0.546 | 0.485 |
| Sumter | 362 | 0.625 | 0.531 |
| Tuscaloosa | 356 | 0.556 | 0.449 |

Across 236 lagged-weather tests, 74 have BY-adjusted q < 0.05. Consult the full table rather than selecting the most favorable lag.

| variable | lag_days | tested_counties | q_below_05 | median_standardized_effect |
| --- | --- | --- | --- | --- |
| dew_point | 0 | 10 | 1 | 0.316 |
| dew_point | 1 | 10 | 10 | -1.125 |
| dew_point | 2 | 10 | 6 | -1.015 |
| dew_point | 3 | 10 | 0 | -0.432 |
| humidity | 0 | 10 | 1 | -0.265 |
| humidity | 1 | 10 | 8 | -0.654 |
| humidity | 2 | 10 | 0 | -0.315 |
| humidity | 3 | 10 | 0 | 0.043 |
| pressure | 0 | 10 | 0 | 0.189 |
| pressure | 1 | 10 | 8 | 0.651 |
| pressure | 2 | 10 | 0 | 0.273 |
| pressure | 3 | 10 | 0 | -0.048 |
| rain | 0 | 9 | 4 | -0.496 |
| rain | 1 | 9 | 4 | -0.546 |
| rain | 2 | 9 | 0 | -0.190 |
| rain | 3 | 9 | 0 | 0.023 |
| temperature | 0 | 10 | 4 | 1.172 |
| temperature | 1 | 10 | 4 | -0.925 |
| temperature | 2 | 10 | 6 | -0.979 |
| temperature | 3 | 10 | 0 | -0.526 |
| wind | 0 | 10 | 9 | -0.700 |
| wind | 1 | 10 | 9 | -1.024 |
| wind | 2 | 10 | 0 | 0.040 |
| wind | 3 | 10 | 0 | 0.175 |

## Methods and interpretation

Lags use a complete daily calendar and never shift across counties. Raw and monthly-demeaned PM2.5 correlations are shown at 1–30 days. These are pairwise lag correlations, not a conventional complete-series ACF estimator; paired counts are included. No missing PM2.5 is interpolated. Lag zero is same-day association. Weather lags 1–3 use earlier dates.

Each weather/lag model includes one weather predictor, yesterday's PM2.5 and month indicators. It asks whether that weather lag is associated with today's PM2.5 after a simple persistence and monthly adjustment. It is not a distributed-lag model and does not separate correlated weather variables or neighboring lags. Standardized weather effects use calendar-aware HAC(7) uncertainty and BY adjustment over the entire primary lagged-weather family. Negative-exclusion sensitivity is provided for lag one. Residual confounding remains; lag correlation does not prove delayed causation.

## Files

Raw and adjusted PM2.5 lag correlations, weather-lag correlations, adjusted weather effects, negative sensitivity, persistence heatmap and lag-response plots.

## Scope and provenance

Source: `../Meterological_data_ALAbama_copy.xlsx` relative to initial_study. All concentrations and weather values use workbook units, which are unverified. County names are sheet labels, not proof of county-wide representativeness. The Jefferson worksheet is named Jefferson_NB in the source. These are exploratory results for 2025, not causal estimates, regulatory determinations, or evidence of long-term trends. See `../METHODS.md` and the root quality tables.
