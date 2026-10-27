# Adjacent counties and daily PM2.5

There are three adjacent pairs among the ten study counties. All three show positive daily association that persists after removing monthly averages.

| Adjacent pair | Paired days | Daily r | Monthly-adjusted r | Daily r interval |
|---|---:|---:|---:|---|
| DeKalb–Etowah | 350 | 0.888 | 0.882 | [0.855, 0.919] |
| Baldwin–Mobile | 357 | 0.770 | 0.751 | [0.668, 0.849] |
| Jefferson–Tuscaloosa | 353 | 0.604 | 0.707 | [0.458, 0.725] |

Mean pairwise correlation is 0.754 for the three adjacent pairs versus 0.562 for the 42 nonadjacent pairs. After monthly demeaning, the corresponding means are 0.780 and 0.550. These are unweighted descriptive means, not an independent-samples significance test.

DeKalb–Etowah has the highest raw correlation of all 45 study pairs. But nonadjacent DeKalb–Morgan and Etowah–Morgan are also strongly correlated. Shared borders are therefore not necessary for synchronized pollution variation. Correlation describes movement together, not equal concentrations or evidence that one county causes pollution in another.

Methods: official 2025 Census adjacency list, including water boundaries and point contacts; all three observed study pairs have positive shared-boundary length. Daily Pearson/Spearman correlations use pairwise observed PM2.5 without imputation. Monthly demeaning subtracts each county’s own monthly average; it removes broad monthly seasonality, not all weather effects or trends. Negative measurements remain, consistent with the earlier study. Intervals for adjacent pairs use 1,000 circular seven-day calendar-block bootstrap samples, retaining missingness and resampling both counties together. Monthly-adjusted intervals condition on the fitted monthly means. Intervals are exploratory, pointwise, not adjusted for multiple comparisons; block length is fixed.

Limits: only three adjacent pairs, selected monitors from ten of Alabama’s 67 counties, one year of measurements and dependent pairwise observations. This cannot establish a general adjacency effect, pollution transport or causality. Baldwin and Mobile share weather inputs in the workbook; weather-independent synchrony has not been established. County adjacency is also an imperfect measure of distance between the actual monitors. Future work could examine monitor distance, wind direction, regional weather and additional years. When building forecasts, test other-county lagged observations using chronological validation and realistic reporting availability; do not use unavailable same-day measurements.

Source: [US Census Bureau 2025 County Adjacency File](https://www.census.gov/geographies/reference-files/time-series/geo/county-adjacency.2025.html). All 45 raw correlations were verified against the earlier simultaneous-peaks analysis. No models were retrained.
