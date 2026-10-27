# Monthly and seasonal patterns

## Highest-mean month in each county

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

## Methods and interpretation

Monthly and seasonal means weight each observed day equally, not each month equally. Coverage is valid PM2.5 days divided by calendar days; monthly rows below 75% coverage are flagged, not hidden. The rolling mean is trailing, not centered, and requires 5 readings within 7 calendar days. Winter here combines January–February and December 2025; it is not one continuous winter season.

A single annual cycle describes patterns within 2025 but cannot establish repeatable seasonality or long-term trends. No independent-days ANOVA is used because nearby daily observations can be correlated. The negative-exclusion monthly means are a sensitivity check.

## Files

Monthly and seasonal tables, highest-month table, daily rolling values, monthly heatmap, monthly lines, and ten daily time-series panels.

## Scope and provenance

Source: `../Meterological_data_ALAbama_copy.xlsx` relative to initial_study. All concentrations and weather values use workbook units, which are unverified. County names are sheet labels, not proof of county-wide representativeness. The Jefferson worksheet is named Jefferson_NB in the source. These are exploratory results for 2025, not causal estimates, regulatory determinations, or evidence of long-term trends. See `../METHODS.md` and the root quality tables.
