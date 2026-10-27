# County-wise PCA variable screening (Python)

## Results summary at a glance

This is the completed **weather PCA screening** summarized in [the unchanged PDF](output/pdf/county_pca_variable_rankings.pdf). All ten counties and six candidate weather variables were considered; components were retained to explain at least 80% of standardized weather variance.

| County | Complete weather rows | Retained PCs | Variance explained | Top-ranked variable | Contribution |
| --- | ---: | ---: | ---: | --- | ---: |
| Baldwin | 363 | 3 | 84.3% | Dew Point | 18.9% |
| Clay | 365 | 3 | 83.4% | Dew Point | 19.1% |
| DeKalb | 365 | 3 | 82.7% | Dew Point | 19.4% |
| Etowah | 357 | 4 | 91.4% | Dew Point | 18.2% |
| Jefferson | 365 | 4 | 91.0% | Precipitation | 18.1% |
| Mobile | 359 | 3 | 85.0% | Dew Point | 18.7% |
| Montgomery | 357 | 4 | 91.9% | Dew Point | 18.1% |
| Morgan | 362 | 3 | 80.5% | Dew Point | 20.1% |
| Sumter | 351 | 3 | 91.1% | Wind Speed | 21.3% |
| Tuscaloosa | 365 | 3 | 82.9% | Dew Point | 19.1% |

**Interpretation:** contribution is a variable's share of variance represented by the retained components. It is not PM2.5 predictive importance, a causal effect or statistical significance. Temperature and dew point are highly redundant in several counties; Sumter's constant precipitation cannot enter scaled PCA. This Python screening starts with all variables and differs from the R workflow's predetermined removals.

![Example county PCA ranking](published_results/Baldwin/variable_ranking.png)

The table comes from [saved run metadata](published_results/run_summary.json) and [all county rankings](published_results/all_county_rankings.csv). For concentration forecasting rather than weather variance, use [the pooled study](pooled_county_study/README.md#results-summary-at-a-glance).

For the current six-model forecasting experiment, use [pooled_county_study/README.md](pooled_county_study/README.md). For seven descriptive and historical prediction analyses, see [initial_study/README.md](initial_study/README.md). The instructions below describe only weather PCA screening.

This independent workflow adapts the workbook sheet names, six weather variables,
and standardized county-wise PCA approach from `../Ana_SK/code/pca_analysis.R`.
It starts with **all six variables**, without copying the R script's predetermined
variable removals. PM2.5 is not used to construct or rank the components.

## Run

From the repository root, with Python 3.10 or newer:

```sh
python3 -m venv Ana_SR/.venv
source Ana_SR/.venv/bin/activate
python -m pip install -r Ana_SR/requirements.txt
python Ana_SR/pca_variable_ranking.py '/path/to/workbook.xlsx'
# Optional subset (use original workbook sheet names):
python Ana_SR/pca_variable_ranking.py '/path/to/workbook.xlsx' --counties Baldwin Morgan
```

The source workbook is included at `Ana_SK/Meterological_data_ALAbama.xlsx` and copied to `Ana_SR/Meterological_data_ALAbama_copy.xlsx`. Its sheets and column names must match the
original R workflow. Sheets: Baldwin, Clay, Dekalb, Etohaw, Jefferson_NB, Mobile,
Montgomery, Morgan, Sumter, Tuscaloosa. Columns: Temperature, Dew Point,
Relative Humidity, Wind Speed, Pressure, Precipitation. PM2.5 is optional and ignored.
This PCA script does not export raw observations.

## What the ranking means

Each county is fitted independently. Variables are centered and scaled using
sample standard deviations, matching R's `prcomp(center=TRUE, scale.=TRUE)`.
SVD gives eigenvectors v and eigenvalues lambda. Keep the smallest number of PCs
explaining at least 80% of variance (change with `--variance-target 0.90`).

For variable j, retained communality is:

`h_j² = sum over retained PCs k of lambda_k * v_jk²`

The reported importance is `100 * h_j² / sum_j(h_j²)`, descending. It is the
variable's share of variance represented by the retained components. Correlation
loadings are `sqrt(lambda_k) * v_jk`, not just the eigenvectors reported as
loadings in the R script. Signs do not affect rankings.

**This is PCA contribution, not statistical significance, causal importance, or
predictive importance for PM2.5.** PCA alone cannot establish that a variable is
irrelevant to pollution. A low-ranked variable can still predict PM2.5 well.
A separate supervised analysis with time-aware validation would answer that question.
PCA maximizes variance; see the [PCA documentation](https://scikit-learn.org/1.7/modules/generated/sklearn.decomposition.PCA.html).

## Screening flags and limitations

- `low_representation`: retained communality < 0.50 (adjust `--low-threshold`).
  This means the retained PCs represent less than half of that variable's variance.
- `high_redundancy`: absolute correlation with another variable >= 0.90
  (adjust `--redundancy-threshold`). Both members are flagged; neither is deleted.
  Correlated duplicate variables can both rank highly.
- `constant`, `all_missing`, or `constant_on_complete_rows`: cannot enter scaled
  PCA; listed after ranked variables with no numerical rank or importance.

Thresholds are exploratory choices, not hypothesis tests. No variable is removed
based on rank. Compare rankings under multiple variance targets before making a
selection. When all PCs are retained, all standardized variables have communality
1 and equal importance; the script reports this limitation. Near ties (10 decimal
places in importance) share a rank. Rankings have no confidence intervals and may
be unstable when eigenvalues are close or sample sizes are small.

All-missing and constant columns are excluded first. Remaining missing weather
observations are handled by complete-case deletion, with counts in the output.
Constants arising on that complete-case subset are then excluded without recovering
previously dropped rows. Non-numeric and infinite values fail explicitly. At least
two varying variables and more complete observations than variables are required.
No imputation, KMO/Bartlett tests, or PM2.5 regression is performed here.

## Outputs

Default output: `Ana_SR/results/` (override with `--output PATH`).

Each county receives `variable_ranking.csv` (most to least contribution),
`variable_ranking.png`, `explained_variance.csv`, `correlation_loadings.csv`, and
`weather_correlations.csv`. The combined `all_county_rankings.csv` keeps each
county's ranking separate. `run_summary.json` records thresholds, row counts,
excluded variables, retained variance, and software versions.

Local PCA results are ignored by Git; explicit exceptions include the source copy, merged workbook and published pooled results. Running again overwrites
matching outputs; use a distinct output folder when comparing settings. Existing
outputs from counties not selected in a later run are left in place.

## Tests

```sh
python -m unittest discover -s Ana_SR -p 'test_*.py' -v
```

Tests use synthetic data; actual study rankings require the original workbook.

## Completed local workbook run

The county rankings from `Ana_SK/Meterological_data_ALAbama.xlsx` are available in
[published_results](published_results/). The [PDF report](output/pdf/county_pca_variable_rankings.pdf)
contains a summary, each county's ordered results and chart, and methods.
The published run uses the default 80% variance target and records the input
workbook SHA-256 in its metadata. The renamed workbook is included in this update.

To reproduce the analysis and report from the repository root:

```sh
python Ana_SR/pca_variable_ranking.py 'Ana_SK/Meterological_data_ALAbama.xlsx' --output Ana_SR/published_results
python -m pip install reportlab
python Ana_SR/build_report.py
```
