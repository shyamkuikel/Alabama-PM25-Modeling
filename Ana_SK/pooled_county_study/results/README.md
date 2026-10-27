# Saved full experiment

These files are the completed full-data run, preserved for inspection and reproducibility. Do not overwrite this directory when exploring new settings.

- `run_metadata.json`: full-run flags, environment, seeds, input/code hashes and checkpoint verification.
- `experiment_design.json`, `selected_settings.json`: frozen search design and chosen configurations.
- `cv_candidate_fold_metrics.csv`, `cv_seed_metrics.csv`, `cv_selected_summary.csv`: all candidate, seed and selected cross-validation scores.
- `fold_sample_audit.csv`, `preprocessing_*.json`: chronological eligibility and training-only preprocessing.
- `test_predictions.csv`, `test_predictions_by_seed.csv`: ensemble and individual test predictions.
- `pooled_test_metrics.csv`, `county_test_metrics.csv`, `seed_test_metrics.csv`: performance summaries.
- `paired_mae_intervals.csv`, `high_day_thresholds.csv`: uncertainty and peak definitions.
- `models/`, `model_manifest.json`: trusted local checkpoints and their loader metadata.
- `training_history.csv`, `parameter_counts.csv`: fitting histories and model size.
- `REPORT.md`, PNG figures: findings and visual comparisons.
- `verification.json`, `independent_verification.json`: completed result checks.
- `example_next_day_forecasts.csv`: example saved-model inference, not validated future observations.

From the parent study folder run `python verify_results.py` to audit this experiment. Use `python run_study.py --output results_new` for another full run. The source/merged files are included so the verifier requires no downloads. Only load checkpoints from trusted sources; joblib can execute code.
