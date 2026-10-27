# PM2.5 prediction: model comparisons and study conclusions

## Main finding

CNN-LSTM had the lowest overall error in this experiment, but its improvement over LSTM-only was small and uncertain. Both recurrent models outperformed persistence and CNN-only. LSTM-only is therefore a reasonable simpler candidate for further validation; the results do not establish that adding CNN to LSTM provides a reliable benefit.

## What was compared

The task was one-day-ahead daily PM2.5 prediction across ten Alabama counties, using the preceding 14 days of PM2.5 and six weather variables. All learned models received the same historical measurements, missingness information, calendar features and county identity. Each learned model predicted a correction to yesterday's PM2.5; persistence simply predicted yesterday's observed value.

Models were trained on January–June 2025 and settings selected using July–September. They were then refitted on January–September and evaluated on October–December. Preprocessing was fitted only on the corresponding training period. All six models were scored on the same 897 county-day observations with observed targets and observed previous-day PM2.5. There were 1,620 initial training windows, 902 validation windows and 2,522 refitting windows.

CNN-only, LSTM-only, CNN-LSTM and random forest each used seeds 11, 22 and 33. Their primary predictions average all three runs; ridge and persistence are deterministic. Individual-run results are saved separately. Settings were selected using validation performance, not test performance.

## Overall results

Lower MAE and RMSE indicate better predictions. Bias is mean prediction minus observation; positive bias means average overprediction. R-squared compares squared error with predicting the pooled test mean. Concentration units remain unverified workbook units.

| Model | MAE | RMSE | Bias | R-squared |
|---|---:|---:|---:|---:|
| CNN-LSTM | 2.1111 | 2.7174 | 0.2615 | 0.3813 |
| LSTM-only | 2.1265 | 2.7369 | 0.2516 | 0.3724 |
| Ridge regression | 2.2000 | 2.8365 | 0.5209 | 0.3259 |
| Random forest | 2.2028 | 2.8163 | 0.5682 | 0.3354 |
| CNN-only | 2.4693 | 3.2932 | 0.2149 | 0.0913 |
| Persistence | 2.4764 | 3.2987 | 0.0146 | 0.0883 |

CNN-LSTM reduced MAE by 14.75% relative to persistence, 14.51% relative to CNN-only, 4.04% relative to ridge, 4.17% relative to random forest and 0.73% relative to LSTM-only. Ridge and random forest were practically close in overall MAE; random forest had slightly lower RMSE. Small average bias for persistence does not mean low prediction error: positive and negative errors can cancel.

## How certain are the comparisons?

The following differences are CNN-LSTM MAE minus comparator MAE. Negative values favor CNN-LSTM. Approximate 95% intervals use 1,000 paired circular seven-day calendar-block bootstrap samples, resampling counties together to preserve same-day dependence.

| Comparator | MAE difference | Interval |
|---|---:|---:|
| LSTM-only | -0.0154 | [-0.0698, 0.0366] |
| CNN-only | -0.3582 | [-0.5116, -0.1983] |
| Ridge regression | -0.0889 | [-0.1579, -0.0222] |
| Random forest | -0.0918 | [-0.1787, -0.0073] |
| Persistence | -0.3653 | [-0.5237, -0.2050] |

The CNN-LSTM versus LSTM-only interval includes zero. There is no clear evidence of a reliable hybrid advantage in this experiment; this does not prove equivalence. Other displayed intervals favor CNN-LSTM, but they are exploratory, pointwise intervals without adjustment for multiple comparisons and condition on the fitted ensembles. They do not include every source of uncertainty, such as model selection or new-year distribution changes.

Single-run CNN-LSTM MAE ranged from 2.0887 to 2.1918; LSTM-only ranged from 2.1224 to 2.1672. The hybrid did not outperform LSTM for every matched seed. Three runs provide only a limited view of training variability. Ridge versus random forest also had an interval crossing zero, as did CNN-only versus persistence; their small differences should not be overinterpreted.

## County differences and high-concentration days

Performance varies by county, so the pooled ranking is not universal. For example, LSTM-only had lower MAE than CNN-LSTM in Etowah and Sumter, while random forest performed best among these models in Etowah. Jefferson had larger errors than the other counties for every model. These patterns motivate further investigation; they do not by themselves identify the causes of county differences. See `results/county_test_metrics.csv` and `results/county_mae_heatmap.png` for the full comparison.

The best overall model was not the best on high-concentration days. Using each county's January–September 95th percentile as a fixed threshold, only 27 eligible test observations were high days. Their MAEs were:

| Model | High-day MAE |
|---|---:|
| CNN-only | 3.5424 |
| Persistence | 3.6741 |
| Ridge regression | 4.3014 |
| Random forest | 4.3521 |
| LSTM-only | 4.4291 |
| CNN-LSTM | 4.6099 |

This small-subset descriptive result shows that lower overall error does not guarantee better peak prediction. It is insufficient to establish a dependable high-day ranking. If detecting pollution episodes is the main objective, that objective needs its own prespecified metrics, larger event sample and validation design.

## Why might CNN add little to LSTM?

These are plausible explanations, not mechanisms demonstrated by this comparison:

- LSTM already reads the full 14-day history and may learn much of the same information that the convolution extracts.
- Daily aggregation may smooth short local patterns that would be more informative in hourly data.
- One year of overlapping windows across related counties supplies limited independent information for estimating additional parameters.
- The shared persistence correction already uses yesterday's concentration directly, leaving less predictable variation for extra layers to explain.
- Unmeasured emissions, smoke transport or other influences can cause errors that an extra layer cannot resolve from the same inputs.

The study cannot conclude that CNN is generally ineffective, that LSTM captures all relevant dynamics, or that CNN-LSTM would behave similarly on other datasets. Architectures differ in parameter count; training losses and tuning budgets also differ between neural and classical models. The experiment compares complete configured approaches, not architecture in isolation.

## Conclusions and practical recommendation

1. Temporal recurrent models were useful for average next-day prediction in this dataset: LSTM-only and CNN-LSTM improved on persistence, CNN-only and the classical baselines under the tested settings.
2. CNN-LSTM ranked first overall, but its advantage over LSTM-only was too small and uncertain to justify a claim that combining CNN and LSTM reliably adds value.
3. LSTM-only is a reasonable simpler model to carry forward, with CNN-LSTM retained as a competing candidate. Model choice should also consider peak prediction, training cost and future validation.
4. Ridge and random forest remain useful benchmarks. Their results demonstrate that a deep model should be evaluated against strong, inexpensive alternatives.
5. High-concentration prediction remains unresolved. The recurrent models' overall advantage did not extend to the small high-day subset.
6. Validate the chosen approach on additional untouched years before making deployment or broad scientific claims. If exploring hourly data, alternative lookbacks or matched model capacities, select those choices within training/validation periods rather than choosing them from these test results.

Suggested study wording:

> CNN-LSTM achieved the lowest overall prediction error, with a 14.75% reduction in MAE relative to persistence. However, its improvement over LSTM-only was only 0.73%, and the paired uncertainty interval included zero. Thus, the present exploratory experiment provides no clear evidence that adding a convolutional layer to LSTM improves predictive performance. Performance varied by county and concentration level, and further validation on independent years is required.

## Limits and reproducibility

October–December outcomes were examined in earlier analyses, so this is an exploratory benchmark rather than a fresh confirmatory test. The data cover one year; overlapping sequences, correlated counties and some shared weather records limit independence and generalization. Workbook units and real-time reporting delays are unverified. Negative PM2.5 readings remain in the primary analysis; excluding negative targets from scoring did not change the overall model ranking, but this sensitivity does not resolve measurement validity. Missing inputs use training medians with missingness indicators; missing targets and missing yesterday PM2.5 are excluded from evaluation.

Execution was verified on native ARM64 CPU. MPS support is implemented but GPU execution was unavailable in the testing session. Ten unit tests passed; saved-table audits verified aligned evaluation cases, recomputed metrics, seed averaging, validation selection and chronological windows. Loaded models reproduced eligible October 1 evaluation predictions.

Source evidence: `results/pooled_test_metrics.csv`, `results/county_test_metrics.csv`, `results/seed_test_metrics.csv`, `results/paired_model_mae_intervals.csv`, `results/selected_settings.json`, `results/run_metadata.json` and `results/verification.json`. Code and run instructions are in this folder. This summary interprets the existing run; no models were retrained for this document.
