# Associations with weather

## Largest month-adjusted descriptive correlations

| county | variable | paired_n | pearson_r | month_demeaned_r |
| --- | --- | --- | --- | --- |
| DeKalb | temperature | 359 | 0.320 | 0.448 |
| Morgan | temperature | 348 | 0.300 | 0.401 |
| Tuscaloosa | temperature | 360 | 0.405 | 0.395 |
| Etowah | temperature | 346 | 0.278 | 0.360 |
| Etowah | wind | 346 | -0.363 | -0.345 |
| DeKalb | dew_point | 359 | 0.270 | 0.341 |
| Montgomery | wind | 349 | -0.333 | -0.336 |
| Jefferson | wind | 358 | -0.232 | -0.334 |
| Jefferson | humidity | 358 | -0.359 | -0.290 |
| Morgan | dew_point | 348 | 0.239 | 0.286 |

The joint weather regression has 15 weather coefficients with BY-adjusted q < 0.05 across 59 tested coefficients. This is exploratory inference, not variable selection.

Wind has a negative conditional coefficient with q < 0.05 in 9/10 counties. Maximum weather VIF ranges from 28.0 to 636.3, showing substantial redundancy. In particular, large temperature/dew-point effects should not be interpreted in isolation.

| county | term | coefficient | ci_low | ci_high | q_by |
| --- | --- | --- | --- | --- | --- |
| Baldwin | dew_point | 7.510 | 2.647 | 12.374 | 0.045 |
| Baldwin | humidity | -3.270 | -5.349 | -1.191 | 0.043 |
| Baldwin | wind | -0.641 | -1.049 | -0.232 | 0.043 |
| DeKalb | wind | -0.742 | -1.109 | -0.374 | 0.003 |
| DeKalb | rain | -0.586 | -0.788 | -0.383 | 0.000 |
| Etowah | wind | -1.388 | -1.808 | -0.967 | 0.000 |
| Jefferson | wind | -1.412 | -2.052 | -0.771 | 0.001 |
| Mobile | dew_point | 8.745 | 3.144 | 14.347 | 0.043 |
| Mobile | humidity | -3.520 | -5.715 | -1.324 | 0.042 |
| Mobile | wind | -0.954 | -1.312 | -0.596 | 0.000 |
| Montgomery | wind | -1.466 | -2.022 | -0.910 | 0.000 |
| Morgan | humidity | -1.316 | -2.063 | -0.569 | 0.015 |
| Morgan | wind | -0.655 | -0.993 | -0.317 | 0.005 |
| Sumter | wind | -0.642 | -0.953 | -0.330 | 0.002 |
| Tuscaloosa | wind | -0.855 | -1.217 | -0.492 | 0.000 |

## Methods

Pearson and Spearman correlations use available pairs. Month-demeaned correlations remove each variable's county-specific monthly mean; this coarse adjustment does not remove all time confounding. County-specific OLS uses all varying weather variables together plus month indicators. Weather coefficients express the PM2.5 difference per one sample SD, conditional on other variables. Constant rainfall in Sumter is excluded.

Confidence intervals use calendar-aware Newey–West covariance with seven daily lags and a small-sample factor. P-values use an asymptotic normal approximation; Benjamini–Yekutieli adjustment addresses multiple weather tests under dependence. These measures remain approximate with one year. Models are descriptive and use the full 2025 sample, not forecast evaluation.

## Diagnostics and sensitivity

`model_diagnostics.csv` includes VIF, condition number, adjusted R² and residual lag-one correlation. Temperature, dew point and humidity can be strongly redundant: joint coefficients can be unstable or reverse sign. Sensitivities exclude negative readings, omit dew point, and omit the highest 5% PM2.5 days. Wet/dry contrasts adjust for month only and are in original concentration units per wet versus dry day. They do not adjust for all other weather. No rain contrast is estimable for Sumter.

## Files

Correlation table, joint coefficients and q-values, sensitivity models, diagnostics, fitted values/residuals, correlation heatmap and weather scatterplots.

## Scope and provenance

Source: `../Meterological_data_ALAbama_copy.xlsx` relative to initial_study. All concentrations and weather values use workbook units, which are unverified. County names are sheet labels, not proof of county-wide representativeness. The Jefferson worksheet is named Jefferson_NB in the source. These are exploratory results for 2025, not causal estimates, regulatory determinations, or evidence of long-term trends. See `../METHODS.md` and the root quality tables.
