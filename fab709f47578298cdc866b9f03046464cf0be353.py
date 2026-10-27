"""Untuned baseline: tomorrow's concentration equals today's observed concentration."""
KIND='baseline'
def candidates():return [{}]
def predict(meta):return meta.persistence.to_numpy()
if __name__=='__main__':
    from run_study import main
    main(['persistence'])
