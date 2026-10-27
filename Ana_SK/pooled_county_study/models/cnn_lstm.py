"""CNN-LSTM: causal convolution followed by recurrent encoding."""
from torch import nn
from torch.nn import functional as F
from .common import ResidualHead,neural_candidates
KIND='neural'
def candidates():return neural_candidates()


class Model(ResidualHead):
    def __init__(self,n_counties,lookback=14,width=16,dropout=.1):
        super().__init__(width,n_counties,dropout)
        self.lookback=lookback;self.conv=nn.Conv1d(14,width,3)
        self.dropout=nn.Dropout(dropout);self.lstm=nn.LSTM(width,width,batch_first=True)

    def forward(self,x,calendar,county):
        if x.shape[1]!=self.lookback:raise ValueError('Wrong history length')
        z=self.dropout(F.relu(self.conv(F.pad(x.transpose(1,2),(2,0)))))
        z,_=self.lstm(z.transpose(1,2))
        return x[:,-1,0]+self.correction(z[:,-1],calendar,county)


if __name__=='__main__':
    from run_study import main
    main(['cnn_lstm'])
