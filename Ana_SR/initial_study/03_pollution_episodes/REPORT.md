# High-pollution days and episodes

## Summary

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

## Highest observed days

| county | date | pm25 | threshold |
| --- | --- | --- | --- |
| Clay | 2025-01-26 00:00:00 | 48.500 | 13.360 |
| Jefferson | 2025-03-28 00:00:00 | 39.900 | 20.800 |
| Clay | 2025-03-23 00:00:00 | 30.500 | 13.360 |
| Montgomery | 2025-02-23 00:00:00 | 30.200 | 13.720 |
| Jefferson | 2025-03-10 00:00:00 | 29.100 | 20.800 |
| Jefferson | 2025-03-27 00:00:00 | 28.800 | 20.800 |
| Jefferson | 2025-02-26 00:00:00 | 27.600 | 20.800 |
| Jefferson | 2025-01-26 00:00:00 | 27.100 | 20.800 |
| Etowah | 2025-03-12 00:00:00 | 25.800 | 14.525 |
| Tuscaloosa | 2025-02-26 00:00:00 | 25.200 | 13.100 |

## Methods and interpretation

A high day is at or above the county's empirical 95th percentile of available 2025 PM2.5 readings. Ties can produce more than 5% high days. This is a relative research threshold, not an air-quality standard. Episodes require consecutive calendar days; a missing PM2.5 day breaks an episode. A 90th/95th/97.5th percentile sensitivity table shows dependence on the cutoff. Thresholds use the full year for retrospective description and must not be reused as training-derived prediction labels.

Weather contrasts are unadjusted descriptive comparisons and can reflect season or missing weather. Peak dates are candidates for source-data review and later linkage with smoke, fire, emissions, or event records. This workbook alone cannot attribute them to a particular source.

## Files

County summaries, episode dates and lengths, high-day weather, ten highest days per county, threshold sensitivity, weather contrasts and timelines.

## Scope and provenance

Source: `../Meterological_data_ALAbama_copy.xlsx` relative to initial_study. All concentrations and weather values use workbook units, which are unverified. County names are sheet labels, not proof of county-wide representativeness. The Jefferson worksheet is named Jefferson_NB in the source. These are exploratory results for 2025, not causal estimates, regulatory determinations, or evidence of long-term trends. See `../METHODS.md` and the root quality tables.
