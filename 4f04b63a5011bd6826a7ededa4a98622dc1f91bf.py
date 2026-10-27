"""Shared fitting mechanics; model architectures and candidate grids are separate."""
import numpy as np
import torch
from torch import nn
from preprocessing import seed_everything,loader,predict,metrics


def units(scaled,meta):return scaled*meta.target_std.to_numpy()+meta.target_mean.to_numpy()


def design(arrays,n_counties):
    x,calendar,ids,_=arrays
    return np.concatenate([x.reshape(len(x),-1),calendar,np.eye(n_counties,dtype=np.float32)[ids]],axis=1)


def residual(arrays):return arrays[-1]-arrays[0][:,-1,0]


def classical_predict(model,arrays,meta,mask,n_counties):
    scaled=arrays[0][mask,-1,0]+model.predict(design(arrays,n_counties)[mask])
    return units(scaled,meta.loc[mask])


def fit_neural(module,config,arrays,meta,train_mask,valid_mask,seed,device,
               epochs,patience,batch_size,n_counties,stage):
    seed_everything(seed)
    model_config={k:v for k,v in config.items() if k!='learning_rate'}
    model=module.Model(n_counties=n_counties,lookback=arrays[0].shape[1],**model_config).to(device)
    optimizer=torch.optim.AdamW(model.parameters(),lr=config['learning_rate'],weight_decay=.001)
    loss_function=nn.L1Loss();batches=loader(arrays,train_mask,batch_size,True,seed)
    best=float('inf');best_epoch=0;state=None;stale=0;history=[]
    for epoch in range(1,epochs+1):
        model.train();total=0;count=0
        for x,calendar,county,y in batches:
            x,calendar,county,y=(v.to(device) for v in (x,calendar,county,y))
            optimizer.zero_grad(set_to_none=True)
            loss=loss_function(model(x,calendar,county),y)
            if not torch.isfinite(loss):raise RuntimeError('Nonfinite loss')
            loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1.);optimizer.step()
            total+=float(loss.detach().cpu())*len(y);count+=len(y)
        row={'stage':stage,'epoch':epoch,'training_standardized_mae':total/count}
        if valid_mask is not None:
            forecast=units(predict(model,arrays,valid_mask,device),meta.loc[valid_mask])
            score=metrics(meta.loc[valid_mask,'observed'],forecast)['mae'];row['inner_stopping_mae']=score
            if score<best-1e-5:
                best=score;best_epoch=epoch;stale=0
                state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
            else:stale+=1
        history.append(row)
        if valid_mask is not None and stale>=patience:break
    if valid_mask is not None:model.load_state_dict(state)
    else:best_epoch=epochs
    return model,best_epoch,history


def select_device(requested):
    if requested=='mps' and not torch.backends.mps.is_available():raise RuntimeError('MPS unavailable; use CPU.')
    device=torch.device('mps' if requested!='cpu' and torch.backends.mps.is_available() else 'cpu')
    if device.type=='mps':
        try:
            from models.cnn_lstm import Model
            probe=Model(2).to(device)
            probe(torch.zeros(2,14,14,device=device),torch.zeros(2,5,device=device),torch.zeros(2,dtype=torch.long,device=device)).sum().backward()
            torch.mps.synchronize()
        except RuntimeError:
            if requested=='mps':raise
            device=torch.device('cpu')
    return device
