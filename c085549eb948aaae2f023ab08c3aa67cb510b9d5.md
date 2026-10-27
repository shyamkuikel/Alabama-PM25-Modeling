# County differences

## Findings

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

Jefferson has the highest observed mean (10.12); DeKalb has the lowest (6.30). Means use available readings and retain negative values. Missing readings are not filled. The negative-exclusion column checks sensitivity without assuming negatives are invalid.

## Methods and interpretation

County summaries describe these monitoring series. Paired differences compare the same dates, which reduces confounding by unequal observation dates. Intervals use 1,000 circular moving-block resamples of 7 consecutive calendar days, resampling dates jointly across counties. Three- and 14-day block sensitivity is also supplied. The intervals quantify temporal variability under a resampling assumption, not instrument or spatial uncertainty. Pairwise intervals are not simultaneous multiple-comparison intervals. Nonstationarity and a single year limit confidence-interval interpretation.

## Files

`county_summary.csv`, `paired_county_differences.csv`, `block_length_sensitivity.csv`; distribution and interval plots. Descriptive differences do not identify emissions sources.

## Scope and provenance

Source: `../Meterological_data_ALAbama_copy.xlsx` relative to initial_study. All concentrations and weather values use workbook units, which are unverified. County names are sheet labels, not proof of county-wide representativeness. The Jefferson worksheet is named Jefferson_NB in the source. These are exploratory results for 2025, not causal estimates, regulatory determinations, or evidence of long-term trends. See `../METHODS.md` and the root quality tables.
