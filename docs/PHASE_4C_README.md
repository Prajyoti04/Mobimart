# Phase 4C — Naive Baseline vs MobiMart Optimizer

Both strategies use the same Phase 3 forecast, the same 70% product-level supply pool, and the same ₹4 crore budget.

Naive = proportional product supply allocation by store forecast, with demand ceilings.
Optimizer = Phase 4B priority-per-rupee allocation with demand and supply constraints.

## Results
          strategy  allocated_units  allocated_value  budget_utilization_pct  forecast_fill_rate_pct  unmet_forecast_units  store_coverage  model_coverage  units_per_₹_lakh
Naive proportional              606       14343000.0                 35.8575               61.931528                 372.5              25              27          4.225058
MobiMart optimizer              610       14522600.0                 36.3065               62.340317                 368.5              25              27          4.200350

Optimizer minus naive forecast fill-rate: 0.41 percentage points.
Optimizer minus naive units per ₹ lakh: -0.02.

## Validation
                       check  passed
    naive budget <= ₹4 crore    True
optimizer budget <= ₹4 crore    True
          naive non-negative    True
      optimizer non-negative    True
             naive <= supply    True
         optimizer <= supply    True
           naive <= forecast    True
       optimizer <= forecast    True

The supply pool is explicitly a prototype assumption because the supplied dataset does not contain future inventory or purchase-order quantities. No claim is made that the optimizer wins every metric; this comparison reports the measured trade-off honestly.
