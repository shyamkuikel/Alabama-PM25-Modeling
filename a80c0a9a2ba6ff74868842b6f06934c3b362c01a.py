import torch
from torch import nn


class ResidualHead(nn.Module):
    def __init__(self,width,n_counties,dropout):
        super().__init__();self.county=nn.Embedding(n_counties,4)
        self.head=nn.Sequential(nn.Linear(width+9,16),nn.ReLU(),nn.Dropout(dropout),nn.Linear(16,1))
        nn.init.zeros_(self.head[-1].weight);nn.init.zeros_(self.head[-1].bias)

    def correction(self,representation,calendar,county):
        return self.head(torch.cat([representation,calendar,self.county(county)],dim=1)).squeeze(-1)


def neural_candidates():
    return [dict(width=w,learning_rate=lr,dropout=.1) for w in [8,16] for lr in [.001,.0003]]
