"""Phase 4B supply-constrained greedy allocation prototype."""
BUDGET = 40_000_000

def product_supply(chain_forecast, supply_fraction=0.70):
    """Finite product pool used when no explicit inventory table is supplied."""
    return max(int(np.ceil(chain_forecast * supply_fraction)), 1)
