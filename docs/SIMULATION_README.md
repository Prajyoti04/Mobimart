# MobiMart Simulation

Six-week stochastic stress test of the Phase 4B optimizer against the Phase 4C naive baseline.

- 4 demand scenarios: normal 1.00×, high 1.35×, low 0.70×, festive 4.00×
- 10 runs per scenario
- 6 weeks per run
- Random seed: 42
- Demand noise: multiplicative Normal(1.0, 0.18)
- Starting stock: Phase 4B optimized allocation vs Phase 4C naive allocation

## Results

   scenario  runs  avg_demand_units  avg_sold_units  avg_stockout_units  avg_revenue  avg_ending_inventory_units  avg_service_level_pct  baseline_avg_sold_units  baseline_avg_stockout_units  baseline_avg_revenue  baseline_avg_ending_inventory_units  baseline_service_level_pct  optimizer_revenue_lift_pct  service_level_delta_pp  stockout_reduction_pct
    festive    10           23472.1           610.0             22862.1   14522600.0                         0.0               2.598915                    606.0                      22866.1            14343000.0                                  0.0                    2.581873                    1.252179                0.017042                0.017493
high_demand    10            7605.1           610.0              6995.1   14522600.0                         3.3               8.021349                    606.0                       6999.1            14343000.0                                  0.7                    7.968750                    1.252179                0.052599                0.057150
 low_demand    10            3714.4           610.0              3104.4   14522600.0                       133.7              16.422994                    606.0                       3108.4            14343000.0                                 54.1                   16.315303                    1.252179                0.107692                0.128684
     normal    10            5575.7           610.0              4965.7   14522600.0                        25.8              10.940907                    606.0                       4969.7            14343000.0                                  4.8                   10.869163                    1.252179                0.071744                0.080488

## Validation

                   check  passed
   4 scenarios simulated    True
    10 runs per scenario    True
         6 weeks per run    True
      no negative demand    True
          sold <= demand    True
stockout = demand - sold    True
     service level 0-100    True

This is a stress-test simulation, not a forecast of actual future sales. The project data does not include realized future demand, purchase orders, supplier lead times, or physical warehouse inventory.
