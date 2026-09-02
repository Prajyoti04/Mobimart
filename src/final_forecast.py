import numpy as np

def forecast_units(history_units):
    """Selected MobiMart Phase 3 method: four-week rolling average."""
    x=np.asarray(history_units,dtype=float)
    if len(x)<4: raise ValueError("Need at least 4 historical weeks")
    return max(0.0,float(np.mean(x[-4:])))
