# Adjacent-county associations

Read `REPORT.md` for findings and limitations. This is a separate descriptive analysis, not a neighboring-input forecasting model.

First reproduce the seven initial studies to obtain `../analysis_ready_data.csv`. Install the initial-study requirements, then run from this folder:

```sh
python analyze_adjacency.py
```

The included Census adjacency table and study county mapping define adjacency. Saved outputs include all county-pair correlations, adjacent-pair summaries, a chart and metadata. Review the script's documented source URLs when refreshing boundary data. This does not modify the pooled forecasting study.
