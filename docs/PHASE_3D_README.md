# Phase 3D — Broader Validation

Selected method: **4-week rolling average**.

Backtest uses all 25 stores × 60 models at forecast cutoffs [36, 40, 44, 48], with no random split and no future leakage.

## Overall
      4_week_baseline
MAE          0.419250
RMSE         0.926755
WAPE         0.752243
Bias        -0.015667

## By week
 forecast_week      MAE     RMSE     WAPE      Bias
            37 0.381167 0.805993 0.772635  0.061500
            41 0.429667 0.912277 0.826282 -0.025333
            45 0.432000 0.938794 0.767773 -0.043333
            49 0.434167 1.035515 0.664541 -0.055500

## By store segment
store_segment   tier  observations      MAE     RMSE     WAPE      Bias
     Balanced Tier 2           240 0.388542 0.851316 0.832589  0.023958
      Premium Tier 1          1920 0.482682 0.987371 0.758388  0.002734
        Value Tier 2          1440 0.402083 0.889610 0.754889 -0.007639
        Value Tier 3          2400 0.381875 0.905510 0.737329 -0.039167

## By category
 category  observations      MAE     RMSE     WAPE      Bias
    Entry           900 0.578056 1.358487 0.594571 -0.158056
   Budget          1200 0.671458 1.205996 0.691631 -0.031458
   Keypad           400 0.398750 0.752496 0.817949  0.072500
Mid-range          1300 0.429038 0.852964 0.862056  0.036731
  Premium           700 0.201071 0.512609 0.874224 -0.024643
Upper-mid          1000 0.302000 0.609918 1.055944  0.017500
 Flagship           500 0.059000 0.193649 1.966667  0.018000

## Final forecast
Generated 1500 store-model forecasts for week 53. Products not yet launched by week 53 receive zero sellable demand.

## Validation
          check  passed
      25 stores    True
      60 models    True
 1500 forecasts    True
  no duplicates    True
   no negatives    True
      valid IDs    True
pre-launch zero    True
      4 cutoffs    True

The final forecast uses only the four most recent observed weeks. The target week is used only for historical evaluation.
