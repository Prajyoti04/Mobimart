"""Phase 5B markdown policy."""
def markdown_rate(status, successor_active):
    if status == "EOL_RECOMMEND":
        return 0.25 if successor_active else 0.20
    if status == "WATCH":
        return 0.10
    return 0.0
