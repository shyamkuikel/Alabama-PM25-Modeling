# CNN-LSTM exploratory results

Device: cpu; parameters: 3337; lookback: 14 days; seeds: [11, 22, 33].

Ensemble test MAE: 2.1111; persistence MAE: 2.4764. MAE improvement versus persistence: 14.75%. A negative improvement means worse forecasts.

                       model   n      mae     rmse     bias  r_squared
           cnn_lstm_ensemble 897 2.111081 2.717373 0.261550   0.381302
                 persistence 897 2.476366 3.298672 0.014604   0.088287
      previous_random_forest 897 2.269937 2.876371 0.875156   0.306782
 previous_ridge_lag_calendar 897 2.507192 3.103734 0.742363   0.192860
  previous_ridge_pca_weather 897 2.298211 2.866535 0.559671   0.311515
      previous_ridge_weather 897 2.281074 2.867637 0.467256   0.310985
      previous_training_mean 897 2.877714 3.497535 1.020340  -0.024954
previous_validation_selected 897 2.276149 2.876205 0.866872   0.306862

Training uses per-county standardized absolute-error loss; validation selects epochs using original-unit pooled MAE. Each seed refits independently on Jan-Sep for its selected duration. The ensemble averages every specified seed; no seed is selected using test performance. Seed SD is model variability, not a calibrated prediction interval.

October-December was already inspected in earlier studies. This is an exploratory comparison, not a fresh confirmatory test. One year and shared county/weather patterns limit generalization. Units and reporting delays remain unverified. Forecasts assume yesterday's data are available. Negative readings are retained and predictions are not clipped.

Prior study predictions compared on exactly the CNN-LSTM test dates.
