# Phase 4B — Supply-Constrained Allocation

Phase 4A allowed each store-model to consume its full forecast independently.
Phase 4B adds a **finite product-level weekly supply pool**.

## Prototype supply assumption
For each product:
`available_units = max(ceil(70% × chain forecast), 1)`

This is a modeling assumption for the prototype because the supplied Phase 1 data does not contain a future purchase-order/inventory-on-hand table. It prevents double-counting the same product inventory across stores.

## Allocation
The engine jointly respects:
- ₹4 crore capital budget
- store-model forecast ceiling
- product-level available supply
- integer units

Candidates are ranked by transparent priority-per-rupee.

## Result
- Budget: ₹40,000,000
- Spend: ₹14,522,600.00
- Budget utilization: 36.31%
- Units allocated: 610
- Product supply pools: 60

## Validation
                       check  passed
          budget <= ₹4 crore    True
          integer allocation    True
  allocation <= store demand    True
allocation <= product supply    True
      no negative allocation    True
               all 25 stores    True
               all 60 models    True
    no duplicate store-model    True

## Top allocations
store_id model_id  category   price  forecast_units  available_units  allocated_units  allocated_value
   ST008    MD050   Premium 97100.0            6.00               14                6         582600.0
   ST001    MD052   Premium 96000.0            5.25               14                5         480000.0
   ST006    MD050   Premium 97100.0            3.25               14                3         291300.0
   ST008    MD052   Premium 96000.0            3.50               14                3         288000.0
   ST023    MD012     Entry  9100.0           27.00              132               27         245700.0
   ST006    MD016    Budget 23300.0           10.75               69               10         233000.0
   ST006    MD021    Budget 25200.0            8.25               62                8         201600.0
   ST018    MD021    Budget 25200.0            8.50               62                8         201600.0
   ST001    MD038 Mid-range 39900.0            5.00               37                5         199500.0
   ST003    MD038 Mid-range 39900.0            5.00               37                5         199500.0
   ST003    MD050   Premium 97100.0            2.75               14                2         194200.0
   ST007    MD050   Premium 97100.0            2.00               14                2         194200.0
   ST003    MD052   Premium 96000.0            2.50               14                2         192000.0
   ST010    MD016    Budget 23300.0            8.50               69                8         186400.0
   ST024    MD016    Budget 23300.0            8.00               69                8         186400.0

## Next
Phase 4C should compare this optimizer with the naive baseline and quantify whether the allocation improves capital productivity / forecast fill while respecting constraints.
