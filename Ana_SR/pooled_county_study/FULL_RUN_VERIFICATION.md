# Evidence of the complete dataset run

The committed results are from the full run, not the smoke test. Rechecked during GitHub preparation on 11 October 2026.

| Item | Verified value |
| --- | --- |
| Source worksheets | All 10 counties |
| Period | 1 January through 31 December 2025 |
| Raw and cleaned panel rows | 3,650 each |
| Observed cleaned PM2.5 | 3,580; 70 missing including 11 negative readings |
| Model families | Persistence, ridge, random forest, CNN, LSTM, CNN-LSTM |
| Outer validation folds | 3 expanding chronological folds |
| Validation cases | 1,783 per family, across folds |
| Shared test cases | 887 per family, October-December |
| Candidate settings | 4 each for all 5 learned families; persistence has none |
| Stochastic seeds | 11, 22, 33 |
| Maximum inner epochs / patience | 60 / 8 |
| Random forest trees | 150 |
| Paired bootstrap replicates | 1,000 |
| Full-run device | CPU, native ARM64 |
| Smoke flag | false |

These values are recorded in `results/run_metadata.json`, `experiment_design.json`, candidate/fold metrics and predictions. The full experiment took approximately 354 seconds on the execution environment; runtime elsewhere will vary. Missing targets and missing previous-day concentrations are excluded consistently, so 887 test cases do not mean a subset of counties was used.

The seven pipeline tests pass. `python verify_results.py` independently passes 11 checks: complete three-fold coverage, CV-based selection, training-only preprocessing recomputation, prescribed epoch selection, identical test cases, recalculated metrics, seed averages, temporal windows, paired differences, input hash and checkpoint round trips. Saved checkpoint inference is also exercised by `predict_saved.py`.

Reproduce from the study directory:

```sh
python -m unittest -v test_pipeline.py
python verify_results.py
python run_study.py --data data/merged_counties.xlsx --device auto --output results_new
python verify_results.py --data data/merged_counties.xlsx --results results_new
```

The code is complete for this workbook structure and 2025 study design. It is deliberately not an arbitrary-year validation framework: new years require updating the prespecified split dates and audit rules before fitting. For future one-day inference, supply updated historical inputs to `predict_saved.py`; this does not retrain the models.

## GitHub preparation checks

- Copied only Git-eligible repository files into a separate folder, with no Git metadata, local environments or caches.
- The copied full results passed all 11 independent audits using the included merged Excel workbook.
- All six families completed a fresh short end-to-end run from that separate folder using all 3,650 panel rows. Its reduced training is a portability check only; it does not replace the saved full results.
- Rebuilt all CSV data from the source workbook into a separate directory and compared the clean panel exactly with the saved data: identical.
- All 42 Python source files parse successfully.
- Current pooled pipeline: 7 unit tests pass. Python PCA: 5 tests pass. Earlier six-model comparison: 4 tests pass. Earlier initial study: 99 audit checks and 14 figures pass in the copied folder.
- Intended publication files are below GitHub's 100 MB individual-file limit. Ignore rules retain required Excel data and historical/current result directories while excluding caches and environments.

These checks use the existing native ARM64 scientific environment. They establish portability of repository paths, not a fresh dependency installation on another machine. `requirements.txt` gives compatible ranges; `requirements-tested.txt` records exact versions used for the full pooled run.
