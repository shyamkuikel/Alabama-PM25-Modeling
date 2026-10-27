"""Comparable sequence encoders with shared county/calendar head and residual skip."""
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

NEURAL_MODELS=('cnn','lstm','cnn_lstm')
ALL_MODELS=('persistence','ridge','random_forest',*NEURAL_MODELS)


class ForecastNetwork(nn.Module):
    """Predict a standardized correction to yesterday's PM2.5.

    Inputs: historical values + missingness [batch, days, 14], target-calendar
    features [batch, 5], and integer county IDs [batch]. All encoders receive the
    same lookback. CNN-only flattens ALL encoded days, so its head can use the
    full historical window rather than only the last kernel's receptive field.
    """
    def __init__(self,architecture,n_counties,lookback=14,width=16,channels=14,dropout=.1):
        super().__init__()
        if architecture not in NEURAL_MODELS:raise ValueError(architecture)
        self.architecture=architecture
        self.lookback=lookback
        self.dropout=nn.Dropout(dropout)
        if architecture in ['cnn','cnn_lstm']:
            self.conv=nn.Conv1d(channels,width,kernel_size=3)
        if architecture=='cnn':
            self.temporal_projection=nn.Linear(lookback*width,width)
        if architecture in ['lstm','cnn_lstm']:
            self.lstm=nn.LSTM(channels if architecture=='lstm' else width,width,batch_first=True)
        self.county=nn.Embedding(n_counties,4)
        self.head=nn.Sequential(nn.Linear(width+4+5,16),nn.ReLU(),nn.Dropout(dropout),nn.Linear(16,1))
        nn.init.zeros_(self.head[-1].weight)
        nn.init.zeros_(self.head[-1].bias)

    def forward(self,x,calendar,county):
        if x.shape[1]!=self.lookback:raise ValueError('Input lookback differs from model configuration')
        if self.architecture in ['cnn','cnn_lstm']:
            z=self.dropout(F.relu(self.conv(F.pad(x.transpose(1,2),(2,0)))))
            z=z.transpose(1,2)
        else:z=x
        if self.architecture=='cnn':
            representation=F.relu(self.temporal_projection(z.reshape(z.shape[0],-1)))
        else:
            z,_=self.lstm(z)
            representation=z[:,-1]
        correction=self.head(torch.cat([representation,self.county(county),calendar],dim=1)).squeeze(-1)
        return x[:,-1,0]+correction


def classical_inputs(arrays,n_counties):
    """Same full histories/missingness/calendar; county identity is one-hot encoded."""
    x,calendar,ids,_=arrays
    onehot=np.eye(n_counties,dtype=np.float32)[ids]
    return np.concatenate([x.reshape(len(x),-1),calendar,onehot],axis=1)


def residual_target(arrays):
    """Target correction to persistence, in the same units used by the neural head."""
    return arrays[-1]-arrays[0][:,-1,0]


def classical_predict(model,arrays,n_counties,mask):
    return arrays[0][mask,-1,0]+model.predict(classical_inputs(arrays,n_counties)[mask])
