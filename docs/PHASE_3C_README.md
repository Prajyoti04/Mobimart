# Phase 3C — Business-Signal Forecast Prototype

## Goal
Improve the Phase 3B forecast without introducing heavy ML or expensive tuning.

### Prototype universe
- Stores: 5 (ST001, ST002, ST003, ST004, ST005)
- Models: 10 (MD002, MD003, MD001, MD004, MD005, MD006, MD007, MD008, MD009, MD010)
- Backtest cutoffs: [36, 40, 44, 48]
- Forecast weeks: [37, 41, 45, 49]
- Forecast observations: 200

## Methods

**Baseline:** four-week rolling mean.

**Phase 3C enhanced:** a conservative weighted recent-demand signal plus capped business adjustments:
- recent demand: weighted moving average
- trend: blended with the 4-week baseline and capped at ±15%
- lifecycle: small launch/maturity adjustment, capped
- successor effect: observed predecessor decline after successor launch, capped
- festive effect: observed category lift, capped at 1.35x
- store/model affinity: only a mild 15% shrinkage toward neutral
- pre-launch products: not eligible and forecast at zero

All adjustments use information available no later than the forecast cutoff.

## Results

      baseline_4wk  phase3c_enhanced
MAE       0.433750          0.451371
RMSE      0.878030          0.889404
WAPE      0.657197          0.683896

## By forecast week

 forecast_week  baseline_MAE  phase3c_MAE  baseline_WAPE  phase3c_WAPE
            37         0.345     0.351515       0.663462      0.675990
            41         0.585     0.594324       1.008621      1.024697
            45         0.445     0.429527       0.585526      0.565168
            49         0.360     0.430119       0.461538      0.551435

## Interpretation

This is still a prototype. The purpose is to determine whether business-aware adjustments improve over the simple baseline. If Phase 3C does not beat the baseline consistently, the baseline should be retained rather than forcing complexity.

## No leakage
No future actual sales are used to construct forecasts at a cutoff. Actual demand is accessed only after the forecast is produced for evaluation.
