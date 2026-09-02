"""Phase 4A: transparent greedy allocation under a capital budget."""
BUDGET = 40_000_000

def allocate_candidates(candidates):
    """Allocate integer units in priority-per-rupee order.

    candidates must contain: price, max_units, priority_score.
    """
    remaining = BUDGET
    allocations = []
    for row in sorted(
        candidates,
        key=lambda r: (r["priority_score"] / r["price"], r["priority_score"]),
        reverse=True
    ):
        price = float(row["price"])
        max_units = int(row["max_units"])
        if price <= 0 or max_units <= 0:
            units = 0
        else:
            units = min(max_units, int(remaining // price))
        allocations.append(units)
        remaining -= units * price
        if remaining <= 0:
            break
    return allocations, remaining
