# Simultaneous county peaks

## Strongest county pairs after monthly adjustment

| county_a | county_b | paired_days | raw_r | month_demeaned_r | joint_high_days |
| --- | --- | --- | --- | --- | --- |
| DeKalb | Etowah | 350 | 0.888 | 0.882 | 10 |
| DeKalb | Morgan | 350 | 0.868 | 0.851 | 9 |
| Etowah | Morgan | 347 | 0.838 | 0.820 | 11 |
| Baldwin | Mobile | 357 | 0.770 | 0.751 | 10 |
| Montgomery | Tuscaloosa | 352 | 0.766 | 0.744 | 9 |
| Jefferson | Morgan | 349 | 0.678 | 0.717 | 6 |
| Etowah | Jefferson | 349 | 0.681 | 0.714 | 7 |
| Morgan | Tuscaloosa | 351 | 0.701 | 0.713 | 9 |

## Dates with the most simultaneous high readings

| date | observed_counties | high_counties | high_county_names |
| --- | --- | --- | --- |
| 2025-03-28 00:00:00 | 10 | 8 | Clay, DeKalb, Etowah, Jefferson, Montgomery, Morgan, Sumter, Tuscaloosa |
| 2025-04-18 00:00:00 | 10 | 7 | Baldwin, Clay, DeKalb, Etowah, Montgomery, Morgan, Tuscaloosa |
| 2025-06-03 00:00:00 | 10 | 7 | Clay, DeKalb, Etowah, Jefferson, Montgomery, Morgan, Tuscaloosa |
| 2025-06-25 00:00:00 | 10 | 7 | Clay, DeKalb, Etowah, Jefferson, Montgomery, Morgan, Tuscaloosa |
| 2025-02-23 00:00:00 | 10 | 6 | Baldwin, DeKalb, Mobile, Montgomery, Sumter, Tuscaloosa |
| 2025-09-19 00:00:00 | 10 | 6 | Clay, Etowah, Jefferson, Montgomery, Sumter, Tuscaloosa |
| 2025-07-05 00:00:00 | 10 | 5 | Baldwin, Etowah, Jefferson, Mobile, Morgan |
| 2025-09-20 00:00:00 | 8 | 5 | Clay, Etowah, Mobile, Montgomery, Sumter |
| 2025-09-21 00:00:00 | 8 | 5 | Clay, Mobile, Montgomery, Sumter, Tuscaloosa |
| 2025-02-22 00:00:00 | 10 | 4 | Baldwin, Clay, Mobile, Montgomery |

There are 26 dates with at least three high counties and at least eight observed counties. The within-month shift null averages 9.8 such days; the exploratory Monte Carlo p-value is 0.0010.

## Methods and interpretation

High-day thresholds are county-specific full-year 95th percentiles, as in Study 3. Missing readings are not treated as low pollution. Raw and monthly-demeaned correlations use paired dates. Pairwise adjusted-correlation intervals use 500 joint 7-day moving-block resamples and are pointwise, not simultaneous. Jaccard is joint high days divided by days high in either county on jointly observed dates.

The 999-replicate null independently rotates each county's observed high/missing series within each calendar month, preserving monthly event counts and approximate short-range clustering while breaking exact same-date alignment. The statistic counts eligible days with at least three high counties. Rotation wraps at month boundaries and assumes within-month exchangeability; the p-value is model-dependent, not proof of a regional transport mechanism. Shared meteorology, shared monitoring inputs or common emissions can all produce synchrony. See the root shared-weather audit before treating counties as independent.

## Files

Two correlation matrices, paired comparisons and intervals, daily peak counts and names, month anomalies, randomization draws, null summary, correlation heatmap and peak-count timeline.

## Scope and provenance

Source: `../Meterological_data_ALAbama_copy.xlsx` relative to initial_study. All concentrations and weather values use workbook units, which are unverified. County names are sheet labels, not proof of county-wide representativeness. The Jefferson worksheet is named Jefferson_NB in the source. These are exploratory results for 2025, not causal estimates, regulatory determinations, or evidence of long-term trends. See `../METHODS.md` and the root quality tables.
