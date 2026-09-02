# Phase 5A — End-of-Life Candidate Detection

## Objective
Identify products that should be considered for EOL / replenishment stop decisions using the observed 52-week sales history and Phase 1 successor relationships.

## Signals
The score combines:
- recent 6-week demand decline versus prior 6 weeks,
- low recent demand,
- recent inactivity,
- whether a known successor has already launched.

## Thresholds
- `0.70+` → EOL_RECOMMEND
- `0.45–0.69` → WATCH
- `<0.45` → ACTIVE

These are transparent prototype thresholds, not claims of a real Mobimart policy.

## Results
- Products analyzed: 60
- EOL_RECOMMEND: 9
- WATCH: 14
- ACTIVE: 37
- Products with successor relationships: 25
- Successors already launched: 18

## Top candidates

model_id   model_name successor_model_id  recent_6w_avg_units  recent_vs_prior_pct  eol_score lifecycle_status                                       recommended_action
   MD011    Halex Max              MD012             2.666667           -68.000000   0.783333    EOL_RECOMMEND              Stop replenishment; transition to successor
   MD049  Zentro Nova              MD050             3.166667           -74.324324   0.770833    EOL_RECOMMEND              Stop replenishment; transition to successor
   MD051  Kryon Orbit              MD052             1.666667           -44.444444   0.769444    EOL_RECOMMEND              Stop replenishment; transition to successor
   MD018  Corvo Pixel              MD019             3.333333           -55.555556   0.766667    EOL_RECOMMEND              Stop replenishment; transition to successor
   MD026    Halex Ace              MD027             1.166667           -41.666667   0.762500    EOL_RECOMMEND              Stop replenishment; transition to successor
   MD040   Orbil Vibe                                0.000000          -100.000000   0.750000    EOL_RECOMMEND                Stop replenishment; review residual stock
   MD059   Vantix Arc                                0.000000          -100.000000   0.750000    EOL_RECOMMEND                Stop replenishment; review residual stock
   MD025    Orbil Neo                                0.166667           -50.000000   0.745833    EOL_RECOMMEND                Stop replenishment; review residual stock
   MD009  Orbil Ember              MD010             4.666667           -66.265060   0.733333    EOL_RECOMMEND              Stop replenishment; transition to successor
   MD057 Nubira Pulse              MD058             2.666667           -33.333333   0.666667            WATCH Monitor demand; reduce replenishment if decline persists

## Validation

                       check  passed
    all products represented    True
       no duplicate products    True
      valid lifecycle labels    True
               scores in 0-1    True
          no negative demand    True
successor IDs valid or blank    True

## Important limitation
The supplied dataset does not include actual inventory-on-hand, supplier lead times, purchase orders, or contractual EOL dates. Therefore this phase identifies **EOL candidates**, not legally binding or operational EOL events.
