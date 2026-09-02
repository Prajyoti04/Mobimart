# Phase 4A — ₹4 Crore Allocation Engine

## Goal
Convert the Phase 3 demand forecast into a weekly store-model allocation while respecting the assignment's ₹4 crore capital budget.

## Allocation rules
1. Forecast demand is the maximum sellable quantity for a store-model.
2. Allocation is integer units.
3. A unit cannot be allocated if its price is unavailable/non-positive.
4. Candidate rows are ranked by **priority per rupee**.
5. The greedy allocator spends the budget from highest priority-per-rupee to lowest.
6. Total allocated value cannot exceed ₹4 crore.
7. Every allocation receives an auditable reason.

## Current prototype
- Stores: 25
- Models: 60
- Candidate store-model rows: 1500
- Budget: ₹40,000,000
- Total spend: ₹16,723,100.00
- Budget utilization: 41.81%
- Allocated units: 745

## Top allocations by value

store_id model_id  category   price  forecast_units  allocated_units  allocated_value                                     recommendation_reason
   ST008    MD050   Premium 97100.0            6.00                6         582600.0 Allocated based on forecast demand and priority per rupee
   ST001    MD052   Premium 96000.0            5.25                5         480000.0 Allocated based on forecast demand and priority per rupee
   ST006    MD050   Premium 97100.0            3.25                3         291300.0 Allocated based on forecast demand and priority per rupee
   ST008    MD052   Premium 96000.0            3.50                3         288000.0 Allocated based on forecast demand and priority per rupee
   ST023    MD012     Entry  9100.0           27.00               27         245700.0 Allocated based on forecast demand and priority per rupee
   ST006    MD016    Budget 23300.0           10.75               10         233000.0 Allocated based on forecast demand and priority per rupee
   ST006    MD021    Budget 25200.0            8.25                8         201600.0 Allocated based on forecast demand and priority per rupee
   ST018    MD021    Budget 25200.0            8.50                8         201600.0 Allocated based on forecast demand and priority per rupee
   ST001    MD038 Mid-range 39900.0            5.00                5         199500.0 Allocated based on forecast demand and priority per rupee
   ST003    MD038 Mid-range 39900.0            5.00                5         199500.0 Allocated based on forecast demand and priority per rupee
   ST003    MD050   Premium 97100.0            2.75                2         194200.0 Allocated based on forecast demand and priority per rupee
   ST007    MD050   Premium 97100.0            2.00                2         194200.0 Allocated based on forecast demand and priority per rupee
   ST003    MD052   Premium 96000.0            2.50                2         192000.0 Allocated based on forecast demand and priority per rupee
   ST010    MD016    Budget 23300.0            8.50                8         186400.0 Allocated based on forecast demand and priority per rupee
   ST024    MD016    Budget 23300.0            8.00                8         186400.0 Allocated based on forecast demand and priority per rupee

## Validation

                   check  passed
      budget <= ₹4 crore    True
 non-negative allocation    True
     integer allocations    True
  allocation <= forecast    True
no invalid product price    True
  all stores represented    True
  all models represented    True
no duplicate store-model    True

## Important limitation
This is Phase 4A only. It is a transparent greedy allocation prototype, not yet the final business optimizer. Inventory availability, store-level stock on hand, transfers, EOL/markdown decisions, and baseline-vs-optimized simulation will be added in later phases.
