"""Phase 5A: transparent product lifecycle / EOL candidate scoring."""
def lifecycle_label(score):
    if score >= 0.70:
        return "EOL_RECOMMEND"
    if score >= 0.45:
        return "WATCH"
    return "ACTIVE"
