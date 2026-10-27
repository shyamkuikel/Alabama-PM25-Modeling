"""LSTM-only: recurrent encoding of the full historical window."""
from torch import nn
from .common import ResidualHead,neural_candidates
KIND='neural'
def candidates():return neural_candidates()


class Model(ResidualHead):
    def __init__(self,n_counties,lookback=14,width=16,dropout=.1):
        super().__init__(width,n_counties,dropout)
        self.lookback=lookback;self.lstm=nn.LSTM(14,width,batch_first=True)

    def forward(self,x,calendar,county):
        if x.shape[1]!=self.lookback:raise ValueError('Wrong history length')
        z,_=self.lstm(x)
        return x[:,-1,0]+self.correction(z[:,-1],calendar,county)


if __name__=='__main__':
    from run_study import main
    main(['lstm'])
