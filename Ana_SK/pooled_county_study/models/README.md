# Separate model implementations

Run these commands from the parent `pooled_county_study` folder, after installing its requirements:

```sh
python -m models.persistence --data data/merged_counties.xlsx --output persistence_run
python -m models.ridge --data data/merged_counties.xlsx --output ridge_run
python -m models.random_forest --data data/merged_counties.xlsx --output forest_run
python -m models.cnn --data data/merged_counties.xlsx --output cnn_run
python -m models.lstm --data data/merged_counties.xlsx --output lstm_run
python -m models.cnn_lstm --data data/merged_counties.xlsx --output hybrid_run
```

Each entry point uses the shared cleaning, chronology, tuning and evaluation pipeline. Its model definition and candidate grid are in its own Python module. `common.py` provides the shared neural prediction head; shared fitting is in `../training.py`. Persistence has no trainable parameters to tune.

For a fair combined comparison run `python run_study.py --data data/merged_counties.xlsx --output results_new`; this freezes all family selections before test scoring. Use a new output directory for each experiment.
