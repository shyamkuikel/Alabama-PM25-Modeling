"""Random forest of standardized change from persistence."""
from sklearn.ensemble import RandomForestRegressor
KIND='classical'
def candidates():return [dict(max_depth=d,min_samples_leaf=l) for d in [6,None] for l in [5,15]]
def build(config,seed,trees,threads):
    return RandomForestRegressor(**config,n_estimators=trees,max_features=.7,random_state=seed,n_jobs=threads)
if __name__=='__main__':
    from run_study import main
    main(['random_forest'])
