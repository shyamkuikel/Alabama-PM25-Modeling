"""Ridge regression of standardized change from persistence."""
from sklearn.linear_model import Ridge
KIND='classical'
def candidates():return [{'alpha':a} for a in [1.,10.,100.,1000.]]
def build(config,seed,trees,threads):return Ridge(**config)
if __name__=='__main__':
    from run_study import main
    main(['ridge'])
