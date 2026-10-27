# Methods, assumptions and reproducibility

This is a completed exploratory analysis of the supplied workbook, not a finalized
publication or a regulatory assessment. Each numbered folder contains a runnable
`analysis.py`, CSV results, PNG figures and a `REPORT.md`. Shared calculations live
in `study.py` so data handling stays consistent across all seven studies.

## Input and data quality

- Input defaults to `Ana_SR/Meterological_data_ALAbama_copy.xlsx`. Both workbook
  copies are preserved. No Excel cells are changed.
- Ten county-labeled sheets, daily calendar January 1–December 31, 2025. Sheet
  labels Dekalb/Etohaw/Jefferson_NB map to DeKalb/Etowah/Jefferson. This does not
  establish monitor identities, spatial representativeness or monitor aggregation.
- Required columns must exist; nonnumeric/infinite observations and duplicate or
  missing dates cause an explicit failure. Dates are normalized to days. Missing
  calendar dates are inserted as missing observations. Only 2025 is supported.
- Source units, collection methods, instrument-quality flags, and weather
  aggregation definitions have not been verified. In particular, precipitation
  may not be a daily accumulated total. No unit conversions are guessed.
- Negative PM2.5 observations are flagged and retained in the primary analysis.
  Small negative instrumental readings can require source-specific treatment;
  the workbook does not establish that they are errors. `pm25_nonnegative` is an
  explicit sensitivity series that excludes, rather than zero-clips, negatives.
- Weather rows with simultaneous zero temperature, dew point and humidity are
  treated as likely placeholders: all six weather variables on that date are set
  missing in the analysis copy. Nonpositive pressure, humidity outside 0–100,
  negative wind or negative precipitation are also set missing. This is a
  conservative analysis assumption, recorded value-by-value in `quality_flags.csv`.
- Other unusual values are retained and can require source review. Sumter's
  constant precipitation is excluded from descriptive scaled regression. Shared
  weather series are audited in `shared_weather_check.csv`; common inputs limit
  independence of county meteorological evidence.
- Missing PM2.5 is never filled. Descriptive tables use available observations and
  report denominators. Correlations use available pairs. Regression uses complete
  cases within its stated predictor set, with sample size reported. Prediction
  imputes predictors using training medians only.

## Study designs

1. **County comparison:** available-day mean/median/SD/quantiles; paired-date mean
   differences; joint calendar-date moving-block bootstrap intervals; 3/7/14-day
   block sensitivity and negative-reading sensitivity.
2. **Monthly patterns:** daily-weighted monthly and seasonal summaries; monthly
   coverage; trailing 7-day means requiring five readings. Monthly coverage below
   75% is flagged, not automatically excluded. Winter combines Jan–Feb and Dec
   within this one calendar year.
3. **Episodes:** full-year county-specific empirical 95th percentile, inclusive of
   ties; missing dates break runs. Threshold sensitivity at 90/95/97.5%. High-day
   weather comparisons are descriptive, not season-adjusted causal contrasts.
4. **Weather:** raw Pearson/Spearman and monthly-demeaned correlations; joint
   county-specific OLS with standardized varying weather predictors and month
   indicators; calendar-aware HAC(7) covariance; VIF and residual diagnostics.
   Sensitivities exclude negative targets, omit dew point, or exclude the top 5%
   PM2.5 days. Wet/dry regression adjusts only for month.
5. **Lags:** pairwise calendar-lag PM2.5 correlations at 1–30 days, raw and monthly
   demeaned; weather lag 0–3 correlations; separate month/yesterday-PM2.5-adjusted
   weather-lag regressions. These do not jointly identify distributed lag effects.
6. **Synchrony:** paired raw and monthly-demeaned county correlations; paired high
   day overlap; eligible dates require at least eight reporting counties for the
   regional statistic. Independent circular shifts within each county/month form
   an exploratory reference distribution for days with at least three high counties.
7. **Prediction:** daily one-step-ahead forecasts using prior-day weather and PM2.5
   lags, plus known calendar features. July–September expanding monthly validation;
   fixed Jan–Sep refits tested on Oct–Dec. No test data fit preprocessing or model
   selection. Persistence and training-mean baselines accompany lag-only ridge,
   weather ridge, weather-PCA ridge and random forest. Shared evaluation dates
   require observed target and lag-one PM2.5. Weather-PCA retains 80% training
   weather variance. Models are saved for reproduction; predictions are not clipped.

## Statistical uncertainty

The circular moving-block bootstrap resamples consecutive **calendar dates**,
retaining missing observations and joint county alignment. Most intervals use
1,000 resamples and a seven-day block; Study 6 correlation intervals use 500.
These are pointwise percentile intervals, not simultaneous county/contrast bands.
They describe temporal resampling uncertainty under a local-dependence assumption;
nonstationarity, one annual cycle and unverified measurement error limit them.

The HAC calculation forms OLS score vectors on the full daily calendar, inserting
zero score vectors for incomplete model rows. Bartlett-weighted lag products use
seven actual calendar lags, rather than compressing gaps after deleting rows.
The covariance includes the factor n/(n−p). Confidence intervals and p-values use
asymptotic normal approximations. This does not eliminate model misspecification,
seasonal confounding or small-sample limitations.

Benjamini–Yekutieli adjusted q-values address dependent multiple comparisons over
all primary weather coefficients in Study 4, and separately all primary lagged
weather coefficients in Study 5. Each sensitivity scenario is a separate family.
Correlation tables deliberately omit independent-observation p-values. The
synchrony randomization reports one prespecified count statistic with 999 draws
and the correction `(1 + extreme_draws)/(1 + draws)`. It assumes approximate
within-month rotation exchangeability and is not a source-attribution test.

Prediction comparisons use paired daily absolute-error differences versus
persistence and seven-day date-block intervals. Pooled metrics weight observed
county-days equally; they are not independence-based statistical tests. Held-out
permutation sensitivity disrupts chronology and correlated features, is explicitly
descriptive, and never changes the selected model.

## Reproduce

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python study.py --study all
```

Run `python 04_weather_associations/analysis.py` for one topic, or
`python study.py --study 4 --workbook /absolute/path/to/workbook.xlsx`.
Outputs with matching names are overwritten on a rerun. Partial reruns do not
refresh other topics; rerun all studies whenever the input or shared methods change.
The input SHA-256, package versions and random seed are saved in run metadata.
`environment_versions.txt` records the exact installed package versions from the
completed execution environment. `verification.json` records numerical and
structural verification of the completed outputs.

## Method references

- [scikit-learn: preventing preprocessing leakage](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage)
- [scikit-learn: time-series validation](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)
- [SciPy: dependent-test false discovery control](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.false_discovery_control.html)
- [statsmodels: Newey–West covariance](https://www.statsmodels.org/stable/generated/statsmodels.stats.sandwich_covariance.cov_hac.html)

## Scientific limits

The observational data support descriptive differences, associations and a limited
within-year forecast assessment. They cannot establish causal effects, identify
wildfire/traffic/industrial contributions, establish population exposure, evaluate
health outcomes, confirm regulatory attainment or detect long-term trends. Those
questions require verified units/provenance and additional years or external data.
