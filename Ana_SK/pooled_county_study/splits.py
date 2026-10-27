"""Shared expanding-window folds; test dates are never part of model selection."""
import pandas as pd
FOLDS=[('fold_1','2025-04-01','2025-06-01'),
       ('fold_2','2025-06-01','2025-08-01'),
       ('fold_3','2025-08-01','2025-10-01')]
TEST_START='2025-10-01'


def masks(meta,train_end,validation_end=None):
    train=meta.date.lt(train_end).to_numpy()
    valid=None if validation_end is None else (meta.date.ge(train_end)&meta.date.lt(validation_end)).to_numpy()
    return train,valid


def stopping_start(train_end):
    """Use final 21 training days for inner stopping, never the outer validation."""
    return str((pd.Timestamp(train_end)-pd.Timedelta(days=21)).date())
