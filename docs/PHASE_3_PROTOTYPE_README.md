# Phase 3 Prototype — Demand Forecasting

## Scope

This is a lightweight prototype only. It uses the existing Phase 1 and Phase 2 data and does not modify them.

Prototype:
- 5 stores: ST001, ST002, ST003, ST004, ST005
- 10 models: MD002, MD003, MD001, MD004, MD005, MD006, MD007, MD008, MD009, MD010
- Historical weeks: 41–52
- Forecast target: week 53 (2025-09-01)
- 50 store-model forecasts

## Methods

### Baseline
The baseline is the mean unit demand over the most recent 4 historical weeks.

### Enhanced prototype
The enhanced forecast uses:
1. A 4-week weighted moving average, with higher weight on recent weeks.
2. A gentle trend ratio comparing the latest 4-week mean with the preceding 4-week mean.
3. The trend ratio is capped between 0.75 and 1.25 to avoid runaway extrapolation.
4. Products not yet launched by the forecast week receive no sellable-demand forecast.

No future actual sales are used.

## Important limitation

The prototype target is week 53, immediately after the available 52-week history. It is therefore a **non-festive** forecast week. Festive adjustment and successor-specific adjustments will be added and backtested in the full Phase 3 implementation only after this prototype is validated.

## Validation

                       check  passed
                    5 stores    True
                   10 models    True
one forecast per store-model    True
        no negative baseline    True
        no negative enhanced    True
             valid store IDs    True
             valid model IDs    True
        no pre-launch demand    True

## Next step

If this prototype passes review, scale the same lightweight approach to time-based backtesting and the full store-model universe. Do not add heavy ML models or hyperparameter searches unless there is a demonstrated business need.
