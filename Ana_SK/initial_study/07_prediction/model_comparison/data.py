"""Reuse the tested workbook preparation from the adjacent CNN-LSTM experiment.

This imports functions only: the original training script is NOT executed and
none of its fitted models or results are used by the comparison.
"""
from pathlib import Path
import sys

SHARED=Path(__file__).resolve().parent.parent/'cnn_lstm'
if not (SHARED/'train_cnn_lstm.py').exists():
    raise ImportError('Keep the adjacent cnn_lstm/train_cnn_lstm.py file with this comparison package.')
sys.path.insert(0,str(SHARED))
from train_cnn_lstm import (FEATURES, DEFAULT_WORKBOOK, read_workbook,
    fit_preprocessing, make_samples, metrics, loader, seed_everything, select_device)

__all__=['FEATURES','DEFAULT_WORKBOOK','read_workbook','fit_preprocessing',
         'make_samples','metrics','loader','seed_everything','select_device']
