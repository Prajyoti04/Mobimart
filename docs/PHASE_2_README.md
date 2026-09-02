# MobiMart — Phase 2: Store Profiling & Historical Demand Analysis

This phase profiles the 25 stores using only the **actual** Phase 1 data
(`data/stores.csv`, `data/products.csv`, `data/sales_history.csv`). No
sales data was regenerated, edited, or reweighted for this analysis — every
number below is computed directly from the 78,000-row sales history.

## What "store profiling" means here

Phase 1 built stores with *designed* affinities (`premium_affinity`,
`budget_affinity`, etc. in `stores.csv`) and then simulated demand from
them. Phase 2 asks the reverse question: **if we only had the resulting
sales history — no knowledge of how it was generated — what would we
conclude about each store?** This is the same exercise a real MobiMart
analyst would do with real POS data, and it's the layer the allocation
engine (Phase 3+) will actually consume.

## Files produced

```
data/
    store_profiles.csv                  one row per store, all metrics below
    store_product_top_affinity.csv      each store's top over-indexing models
    festive_lift_by_category.csv        festive lift split by product category
src/
    store_profiling.py                  metric computation functions (reusable)
    phase2_analysis.py                  orchestrator — builds profiles + plots
    validate_phase2.py                  validation report
reports/phase2/
    category_mix.png
    store_asp.png
    store_revenue.png
    festive_lift.png
    store_segments.png
PHASE_2_README.md
```

Run with:
```bash
cd src
python3 phase2_analysis.py
python3 validate_phase2.py
```

---

## 1. Metrics calculated

For every store: `total_units_sold`, `total_sales_value`,
`average_weekly_units`, `average_weekly_revenue`, `average_selling_price`,
7 category unit-shares (keypad → flagship), 3 orientation indices
(`premium_index`, `midrange_index`, `budget_index`), `top_5_model_share`
(demand concentration), `festive_lift`, and weekly velocity stats
(`mean_weekly_units`, `median_weekly_units`, `max_weekly_units`,
`std_weekly_units`, `demand_volatility` = coefficient of variation).

Category shares are computed from actual units sold and sum to **1.0000**
for every one of the 25 stores (validated).

## 2. Orientation indices are derived from actual sales, not copied

```
premium_index  = premium_share + flagship_share      (from real units sold)
midrange_index = midrange_share + upper_mid_share
budget_index   = budget_share + entry_share + keypad_share
```

These are **not** the `premium_affinity` / `budget_affinity` columns from
`stores.csv` — they're recomputed from what actually sold. The two turn out
to be directionally consistent (as they should be, since affinity drove the
simulated demand), which is itself a useful sanity check that the Phase 1
generator behaved as designed:

| store | designed `premium_affinity` (stores.csv) | actual `premium_index` (sales-derived) |
|---|---|---|
| ST001 (Indiranagar Premium Mall) | 0.423 | **0.227** |
| ST021 (Ballari Local Market) | 0.014 | **0.003** |

(Actual indices are lower than designed affinities in absolute terms
because affinity is a *demand weighting* factor among several — price
elasticity and lifecycle timing also shape what ultimately sells — but the
**ranking** is preserved: stores.csv's affinity order and the sales-derived
order agree store-for-store in this dataset.)

## 3. Evidence that stores are not interchangeable

**Category mix — three example stores** (see `reports/phase2/category_mix.png`):

| store | keypad | entry | budget | midrange | upper-mid | premium | flagship |
|---|---|---|---|---|---|---|---|
| ST001 Premium Mall, Bangalore | 4.6% | 18.2% | 22.5% | 18.7% | 13.4% | 18.2% | 4.5% |
| ST002 Mixed, Bangalore | 7.5% | 18.2% | 23.1% | 24.9% | 16.1% | 6.2% | 3.9% |
| ST021 Tier-3 Value, Ballari | 14.6% | 29.2% | 39.9% | 9.1% | 6.8% | 0.2% | 0.1% |

ST001 sells premium+flagship phones at roughly **67x** the *share* rate of
ST021 (22.7% vs. 0.34% of units).

**Average selling price** (`reports/phase2/store_asp.png`): ranges from
**Rs 17,644** (ST022, Kalaburagi Town Center) to **Rs 40,388**
(ST005, Electronic City Tech Park Hub) — a **2.3x** spread across the chain.

**Revenue** (`reports/phase2/store_revenue.png`): the top-grossing store,
ST003 (MG Road Premium Mall), generated **Rs 15.13 crore** in 52 weeks vs.
the lowest, well under half that — driven by a combination of higher ASP
*and* higher volume, not just one factor.

**Demand concentration** (top-5-model share of a store's own units): ranges
from **28.3%** (ST004 — broad, diversified demand across many models) to
**60.3%** (ST022 — demand concentrated in a handful of hero SKUs). This
matters directly for future allocation: concentrated-demand stores are more
exposed to a single stockout, diversified stores less so.

## 4. Product-level store affinity

```
affinity_score(store, model) =
    (store's share of ITS OWN units sold that this model represents)
    /
    (chain-wide share of TOTAL units sold that this model represents)
```

A score of 1.0 means the store sells that model at exactly the chain-average
rate; >1 means it over-indexes; <1 means it under-indexes. This is a
standard retail "category index" metric, computed only for
(store, model) pairs with at least 15 units sold (to avoid a single lucky
sale producing a meaningless spike).

Example — each store's top over-indexing products:

| store | model | category | affinity_score | units sold |
|---|---|---|---|---|
| ST001 (Premium, Bangalore) | Kryon Orbit 2 | Premium | **5.67x** | 31 |
| ST001 | Halex Crest | Premium | 4.16x | 201 |
| ST021 (Value, Ballari) | Corvo Pulse | Entry | **2.96x** | 39 |
| ST021 | Ferno Sol | Budget | 2.57x | 117 |
| ST021 | Nubira Crest | Keypad | 1.92x | 146 |

Full table: `data/store_product_top_affinity.csv`. This is exactly the kind
of signal a future allocation engine would use to decide which store gets
priority on a constrained SKU — but that engine is out of scope for Phase 2.

## 5. Festive sensitivity

Chain-wide, festive weeks (Dussehra wk6, Diwali wk9) lift average weekly
units by **4.34x** vs. non-festive weeks — but this is not uniform:

**Highest festive lift:**
| store | segment | festive_lift |
|---|---|---|
| ST015 (Davangere Local Market) | Value | 5.28x |
| ST021 (Ballari Local Market) | Value | 5.22x |
| ST020 (Shivamogga Local Market) | Value | 5.01x |

**Lowest festive lift:**
| store | segment | festive_lift |
|---|---|---|
| ST023 (Udupi Local Market) | Value | 3.30x |
| ST008 (Yeshwanthpur Suburban Mall) | Premium | 3.49x |
| ST003 (MG Road Premium Mall) | Premium | 3.53x |

Segment averages: **Value 4.51x**, **Balanced 4.34x**, **Premium 3.99x** —
Value-oriented stores are, on average, more festive-sensitive than Premium
stores, consistent with the Phase 1 design (budget/mid-range categories
were given a stronger festive multiplier). Note this isn't perfectly clean
(ST023 is a Value store with the single lowest lift in the chain) —
reported honestly rather than smoothed over.

**By category** (`data/festive_lift_by_category.csv`):

| category | festive_lift |
|---|---|
| Flagship | 6.06x |
| Budget | 5.12x |
| Entry | 4.98x |
| Upper-mid | 3.29x |
| Premium | 3.33x |
| Keypad | 3.44x |
| Mid-range | 2.99x |

This is noisier than the store-level pattern (Flagship shows the single
highest lift, which runs against the general "budget lifts more" design
intent) — category-level festive lift is computed over fewer, lower-volume
observations than store-level lift, so it's more sensitive to which specific
high-value flagship launches happened to land near a festive week. Flagged
here rather than hidden.

## 6. Weekly sales velocity

Chain-wide `mean_weekly_units` per store ranges from ~27 (ST012) to ~81
(ST003). `demand_volatility` (coefficient of variation of weekly units)
ranges from **0.51** (ST003 — most stable, highest-volume store) to **0.81**
(ST015 — most volatile). In general, the highest-volume Premium stores
(ST003, ST008, ST006) show the *lowest* volatility, while smaller Value
stores (ST015, ST021, ST020) show the *highest* — smaller absolute volumes
combined with lumpy festive spikes produce proportionally bigger swings.
This is exactly the kind of store where safety-stock logic will matter most
in later phases.

## 7. Store segmentation

**Method: rule-based (Option A)**, chosen over clustering because the
underlying signal turned out to have an unambiguous natural break — a
K-means model would have re-derived the same split with far less
transparency for a business audience.

The cutoffs were chosen by inspecting the actual distribution of
`premium_index` and `budget_index` across the 25 stores (see
`store_profiling.py::segment_stores_rule_based` docstring): `premium_index`
drops from **0.101 to 0.068** exactly between the 8th- and 9th-ranked
store — a clean gap, not an arbitrary round number — which is where the
Premium/non-Premium threshold sits.

```
premium_index >= 0.10   -> "Premium"
budget_index  >= 0.65   -> "Value"
otherwise               -> "Balanced"
```

**Result: 8 Premium, 1 Balanced, 16 Value.**

- **Premium** = ST001-ST008 — exactly the 8 Bangalore stores. Mean ASP
  Rs 36,302, mean premium_index 14.2%, mean festive_lift 3.99x.
- **Balanced** = ST019 (Mangaluru Town Center) — the one store that doesn't
  cleanly fit either bucket (mean ASP Rs 29,902, premium_index 5.2%).
- **Value** = the remaining 16 Tier 2/3 stores. Mean ASP Rs 22,650, mean
  budget_index 77.4%, mean festive_lift 4.51x.

That the segmentation exactly reproduces the Tier-1/Bangalore boundary
(rather than being told to) is itself validation that Phase 1's designed
store differences are actually showing up in simulated sales behavior.

See `reports/phase2/store_segments.png` for the ASP-vs-premium_index
scatter that shows the visual separation.

---

## Validation results (from `validate_phase2.py`, actual run)

```
[PASS] Exactly 25 store profiles
[PASS] No duplicate store_id in store_profiles
[PASS] Every Phase 1 store is represented
[PASS] No unexpected store IDs in store_profiles
[PASS] No unexpected model IDs in sales_history
[PASS] No unexpected store IDs in sales_history
[PASS] No missing critical metrics
[PASS] Category shares sum to ~1.0 for every store (min=1.0000, max=1.0000)
[PASS] All category shares are within [0, 1]
[PASS] premium_index == premium_share + flagship_share
[PASS] budget_index == budget_share + entry_share + keypad_share
[PASS] midrange_index == midrange_share + upper_mid_share
[PASS] average_selling_price consistent with total_sales_value/total_units_sold
[PASS] average_weekly_units consistent with total_units_sold / num_weeks
[PASS] total_units_sold in store_profiles matches raw sales_history aggregation
[PASS] festive_lift is non-negative and finite for all stores
[PASS] Chain-wide average festive_lift > 1 (mean festive_lift=4.34)
[PASS] No impossible negative values in numeric profile columns
[PASS] top_5_model_share within [0, 1]
[PASS] Every store has exactly one segment assigned
[PASS] All segment labels are from the expected set

Segment counts: Value 16, Premium 8, Balanced 1

OVERALL RESULT: ALL CHECKS PASSED
```

---

## Assumptions made

1. **Festive weeks** used here are the same two fixed weeks defined in
   Phase 1 (week 6 = Dussehra, week 9 = Diwali) — Phase 2 does not
   redefine or discover festive weeks independently.
2. **Segmentation thresholds** (`premium_index >= 0.10`,
   `budget_index >= 0.65`) were picked from the natural gap in this
   dataset's actual distribution, not fixed a priori — re-running Phase 1
   with a different seed would require re-inspecting the distribution
   before reusing these exact cutoffs.
3. **Affinity score minimum volume floor** of 15 units was chosen
   arbitrarily as "high enough to not be a fluke, low enough to include
   most stores' real top performers" — a stricter or looser floor would
   shift the specific models shown in `store_product_top_affinity.csv`
   without changing the overall conclusion.
4. **Demand volatility** uses coefficient of variation (std/mean) rather
   than raw standard deviation specifically so stores of very different
   sizes can be compared on the same volatility scale.

## Was any Phase 1 data modified?

**No.** `stores.csv`, `products.csv`, and `sales_history.csv` are read-only
inputs to this phase; no rows were added, removed, or altered. All new
outputs (`store_profiles.csv`, `store_product_top_affinity.csv`,
`festive_lift_by_category.csv`) are new files, not modifications to
Phase 1 files.

---

**Phase 2 is complete.** No allocation engine, forecasting model,
end-of-life logic, markdown/transfer/hold optimization, baseline,
simulation, or dashboard has been built. Waiting for approval before
starting Phase 3.
