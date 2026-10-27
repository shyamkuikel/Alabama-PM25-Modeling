# Merged dataset

`merged_counties.xlsx` has four sheets: Clean panel, Raw panel, Quality summary and Dictionary. The raw and cleaned panels each contain all 3,650 county-days. CSV versions retain machine-readable values and provenance. `cleaning_log.csv` records changes; `data_metadata.json` records the source hash. `workbook_verification.json` records the Excel/CSV consistency check.

The raw source is `../../Meterological_data_ALAbama_copy.xlsx` relative to this data directory. No full-year target or predictor imputation is applied to the clean file. Fold-specific imputation/scaling happens during model fitting.

From the study directory, rebuild the complete CSV panels into a new location:

```sh
python prepare_data.py --workbook ../Meterological_data_ALAbama_copy.xlsx --output data_rebuilt
python run_study.py --data data_rebuilt/merged_clean.csv --device auto --output results_rebuilt
python verify_results.py --data data_rebuilt/merged_clean.csv --results results_rebuilt
```

CSV and Excel inputs are both supported. The provided formatted Excel export is preserved; CSV regeneration does not refresh it automatically. Modeling needs no external spreadsheet export tool. Do not replace the input of saved results without rerunning their hash audit.
