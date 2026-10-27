# Initial PM2.5 study: seven analyses

## Results summary at a glance

This summarizes the [unchanged initial findings PDF](PM25_findings_summary.pdf). It describes the original experiment: **3,591 observed concentrations**, with 11 negative values retained and sensitivity checks. The later pooled study uses a stricter cleaning policy and is a separate experiment.

### County and weather findings

- **Jefferson had the highest annual mean (10.12)**, versus DeKalb's 6.30, approximately 61% higher. Middle-ranked counties often had overlapping uncertainty intervals.
- **Clay had the highest single-day reading (48.50)** despite a mean of 6.71. Typical concentration and extreme events tell different stories.
- Wind had the most consistent negative adjusted relationship: coefficients were negative with adjusted q < 0.05 in **9 of 10 counties**. These observational associations do not establish causation.
- Temperature, dew point and humidity were strongly redundant. Rainfall evidence was inconsistent, and Sumter's constant rainfall could not support a coefficient. Baldwin and Mobile shared the same weather values on jointly observed days.

![Annual county concentration distributions](01_county_comparison/county_boxplots.png)

### Initial next-day prediction comparison

July-September chronological validation selected settings; fixed models fitted on January-September were evaluated on **897 shared October-December county-days**, using daily updated lagged observations. Lower MAE/RMSE is better; concentrations use micrograms per cubic meter as supported by later source matching.

| Approach | Test MAE | Test RMSE |
| --- | ---: | ---: |
| Training-period mean | 2.878 | 3.498 |
| Persistence | 2.476 | 3.299 |
| Ridge: lags and calendar | 2.507 | 3.104 |
| Ridge: adding lagged weather | 2.281 | 2.868 |
| Ridge: weather PCA components | 2.298 | 2.867 |
| Random forest | 2.270 | 2.876 |
| Validation-selected model per county | 2.276 | 2.876 |

The validation-selected approach reduced pooled MAE by approximately **8%** versus persistence, improving in 7/10 counties but doing worse in Baldwin, Mobile and Sumter. Weather improved the ridge comparison; weather PCA did not improve pooled error over original weather variables. The selected forecasts still overpredicted, with pooled bias **+0.87**. County improvements were uncertain in most locations.

One year does not establish repeated seasonality, long-term trends or causal effects. The later use of these test months makes subsequent comparisons exploratory. [Detailed methods](METHODS.md), [prediction results](07_prediction/REPORT.md) and the seven sections below retain uncertainty and sensitivity analyses. For the newer tuned neural/classical experiment, see [pooled results](../pooled_county_study/README.md#results-summary-at-a-glance).

## Current experiment and provenance update

This folder preserves the earlier exploratory study and its original methods. For three-fold tuning and the current six-model comparison, use [../pooled_county_study/README.md](../pooled_county_study/README.md). Later [source matching](07_prediction/model_comparison/source_verification/SOURCE_FINDINGS.md) supports PM2.5 units of micrograms per cubic meter; weather provenance remains partly unresolved. Statements below describing units as unverified reflect the initial analysis date.

From this folder, create a separate Python 3.12 environment, install `requirements.txt`, then run `python study.py --study all` and `python verify.py`. Each numbered folder has an `analysis.py` entry point; maps, adjacency and neural comparisons have separate scripts. Running the original studies overwrites their matching outputs. Both source workbooks are included in this update.

Source: `Ana_SR/Meterological_data_ALAbama_copy.xlsx`. Period: January 1–December 31, 2025. Ten county-labeled daily series. Source workbook preserved. Concentration and weather units are unverified, so no regulatory exceedance or health-risk classification is made.

## Data quality

| county | observed_pm25 | missing_pm25 | negative_pm25 | constant_weather |
| --- | --- | --- | --- | --- |
| Baldwin | 359 | 6 | 0 | — |
| Clay | 359 | 6 | 2 | — |
| DeKalb | 359 | 6 | 2 | — |
| Etowah | 356 | 9 | 0 | — |
| Jefferson | 358 | 7 | 0 | — |
| Mobile | 363 | 2 | 3 | — |
| Montgomery | 357 | 8 | 1 | — |
| Morgan | 356 | 9 | 0 | — |
| Sumter | 364 | 1 | 0 | rain |
| Tuscaloosa | 360 | 5 | 3 | — |

Negative readings remain in the primary analysis with explicit sensitivity checks. Implausible weather placeholders are flagged and treated as missing in analysis copies. `quality_flags.csv` records every affected value. `shared_weather_check.csv` audits weather reuse.

## 1. County comparison

| county | n | mean | median | p95 | max |
| --- | --- | --- | --- | --- | --- |
| Jefferson | 358 | 10.122 | 8.800 | 20.800 | 39.900 |
| Etowah | 356 | 8.191 | 7.600 | 14.525 | 25.800 |
| Montgomery | 357 | 8.069 | 7.600 | 13.720 | 30.200 |
| Mobile | 363 | 7.345 | 7.200 | 11.890 | 21.600 |
| Tuscaloosa | 360 | 7.032 | 6.600 | 13.100 | 25.200 |
| Sumter | 364 | 7.031 | 6.800 | 12.185 | 16.400 |
| Morgan | 356 | 6.875 | 6.350 | 12.525 | 18.500 |
| Clay | 359 | 6.715 | 5.900 | 13.360 | 48.500 |
| Baldwin | 359 | 6.616 | 6.700 | 11.430 | 24.500 |
| DeKalb | 359 | 6.303 | 5.800 | 12.100 | 20.200 |

## 2. Highest-mean months

| county | month | mean | coverage |
| --- | --- | --- | --- |
| Baldwin | 7 | 8.543 | 0.968 |
| Clay | 9 | 9.193 | 0.933 |
| DeKalb | 6 | 8.300 | 1.000 |
| Etowah | 9 | 10.687 | 1.000 |
| Jefferson | 3 | 13.850 | 1.000 |
| Mobile | 2 | 9.062 | 0.929 |
| Montgomery | 9 | 10.358 | 1.000 |
| Morgan | 6 | 8.643 | 1.000 |
| Sumter | 9 | 9.803 | 1.000 |
| Tuscaloosa | 9 | 10.467 | 1.000 |

## 3. Pollution episodes

| county | n | p95_threshold | high_days | episodes | longest_episode |
| --- | --- | --- | --- | --- | --- |
| Baldwin | 359 | 11.430 | 18 | 14 | 3 |
| Clay | 359 | 13.360 | 18 | 14 | 3 |
| DeKalb | 359 | 12.100 | 19 | 12 | 3 |
| Etowah | 356 | 14.525 | 18 | 13 | 2 |
| Jefferson | 358 | 20.800 | 19 | 16 | 2 |
| Mobile | 363 | 11.890 | 19 | 13 | 2 |
| Montgomery | 357 | 13.720 | 18 | 12 | 4 |
| Morgan | 356 | 12.525 | 18 | 14 | 2 |
| Sumter | 364 | 12.185 | 19 | 9 | 7 |
| Tuscaloosa | 360 | 13.100 | 19 | 12 | 3 |

## 4. Weather associations

15 of 59 joint weather coefficients have BY-adjusted q < 0.05 after month adjustment and HAC uncertainty. Maximum weather VIF ranges from 28.0 to 636.3; interpret conditional coefficients cautiously where predictors are redundant.

## 5. Persistence

| county | raw_pairwise_autocorrelation | month_demeaned_autocorrelation |
| --- | --- | --- |
| Baldwin | 0.511 | 0.401 |
| Clay | 0.372 | 0.327 |
| DeKalb | 0.555 | 0.480 |
| Etowah | 0.562 | 0.497 |
| Jefferson | 0.474 | 0.382 |
| Mobile | 0.492 | 0.385 |
| Montgomery | 0.553 | 0.470 |
| Morgan | 0.546 | 0.485 |
| Sumter | 0.625 | 0.531 |
| Tuscaloosa | 0.556 | 0.449 |

## 6. Simultaneous peaks

| statistic | observed | null_mean | null_p95 | monte_carlo_p | replicates |
| --- | --- | --- | --- | --- | --- |
| eligible_days_at_least3_high | 26 | 9.850 | 14 | 0.001 | 999 |

The within-month circular-shift comparison is exploratory and assumption-dependent; synchrony alone does not establish regional transport or common emissions.

## 7. Forecast performance

| model | n | mae | rmse | r_squared | bias_pred_minus_observed |
| --- | --- | --- | --- | --- | --- |
| random_forest | 897 | 2.270 | 2.876 | 0.307 | 0.875 |
| validation_selected_per_county | 897 | 2.276 | 2.876 | 0.307 | 0.867 |
| ridge_weather | 897 | 2.281 | 2.868 | 0.311 | 0.467 |
| ridge_pca_weather | 897 | 2.298 | 2.867 | 0.312 | 0.560 |
| persistence | 897 | 2.476 | 3.299 | 0.088 | 0.015 |
| ridge_lag_calendar | 897 | 2.507 | 3.104 | 0.193 | 0.742 |
| training_mean | 897 | 2.878 | 3.498 | -0.025 | 1.020 |

Models selected using July–September only; fixed fitted models evaluated October–December using daily updated lagged observations. Compare MAE with persistence before concluding that weather or PCA improves prediction.

## Navigation

1. [01_county_comparison](./01_county_comparison/REPORT.md) — code, tables, figures and interpretation.
2. [02_monthly_patterns](./02_monthly_patterns/REPORT.md) — code, tables, figures and interpretation.
3. [03_pollution_episodes](./03_pollution_episodes/REPORT.md) — code, tables, figures and interpretation.
4. [04_weather_associations](./04_weather_associations/REPORT.md) — code, tables, figures and interpretation.
5. [05_lagged_relationships](./05_lagged_relationships/REPORT.md) — code, tables, figures and interpretation.
6. [06_simultaneous_peaks](./06_simultaneous_peaks/REPORT.md) — code, tables, figures and interpretation.
7. [07_prediction](./07_prediction/REPORT.md) — code, tables, figures and interpretation.

## Shared weather inputs

| county_a | county_b | variable | paired_days | fraction_identical |
| --- | --- | --- | --- | --- |
| Baldwin | Mobile | temperature | 357 | 1.000 |
| Baldwin | Mobile | dew_point | 357 | 1.000 |
| Baldwin | Mobile | humidity | 357 | 1.000 |
| Baldwin | Mobile | wind | 357 | 1.000 |
| Baldwin | Mobile | pressure | 357 | 1.000 |

Baldwin and Mobile have identical values for all six weather variables on jointly observed dates. This can reflect a shared station or duplicated source inputs; verify provenance before treating their weather evidence as independent.


## Reproduce

Python 3.12 was used. Install `requirements.txt` in a virtual environment, then run `python study.py --study all`. Run a single study with `python study.py --study 1`, or run its folder's `analysis.py`. Use `--workbook PATH` for a different input with the same structure. Runs overwrite matching generated outputs. See METHODS.md for assumptions, and run_metadata.json for input hash, versions and random seed.

## Limits

One year cannot establish a long-term trend or repeatable seasonal cycle. The workbook lacks verified units, monitor IDs, source-quality flags, reporting delays, emissions, wind direction and external event records. It supports associations and within-year prediction, not source attribution or county-population exposure estimates.
