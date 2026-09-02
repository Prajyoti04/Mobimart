# Phase 5C — Store-Level Inventory Transfer Recommendations

## Purpose
When a predecessor is being phased out and a successor is active, identify stores where remaining predecessor inventory should be redirected/managed alongside the successor.

## Signal design
The transfer priority combines:
- successor's recent demand at the store (strongest signal),
- predecessor's recent demand,
- successor's share of the store's historical units.

Recommended units are capped using recent predecessor demand and a successor-demand proxy.

## Results
- Actionable transfer lines: 25
- Stores receiving recommendations: 16
- Successor models involved: 7
- Recommended transfer units: 32
- Indicative successor-value exposure: ₹854,800.00

## Validation
                                   check  passed
        all transfer successor IDs valid    True
               all predecessor IDs valid    True
             transfer units non-negative    True
                     no transfer to self    True
                        all stores valid    True
no duplicate store-predecessor-successor    True

## Important interpretation
This is a **planning recommendation**, not a physical warehouse transfer order. The dataset does not contain warehouse stock by location, inter-store transfer cost, logistics capacity, or actual on-hand inventory. In production those constraints must be added before executing a transfer.
