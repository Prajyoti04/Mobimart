# MobiMart — Phase 1: Synthetic Dataset

Reproducible 52-week weekly sales dataset for 25 Karnataka stores x ~60 phone
models, built for the Mirai Labs Software Developer Intern assessment
(Assignment B). This phase produces **only** the dataset — no allocation,
forecasting, EOL, dashboard, or simulation logic is included.

Random seed: **42** (used everywhere — store generation, product generation,
and the sales simulation). Re-running `data_generator.py` reproduces the
exact same files byte-for-byte.

Data window: **52 weeks, starting Monday 2024-09-02** through 2025-08-25.

## Project structure

```
data/
    stores.csv           25 rows
    products.csv         60 rows
    sales_history.csv    78,000 rows (25 stores x 60 models x 52 weeks)
src/
    stores_gen.py         store master data generator
    products_gen.py       product master data + lineage/successor generator
    sales_gen.py          core weekly demand simulation
    data_generator.py     orchestrator — run this to (re)build data/
    validate_data.py      validation report — run this after generating
PHASE_1_README.md
```

To regenerate and validate:
```bash
cd src
python3 data_generator.py
python3 validate_data.py
```

---

## 1. Store segmentation (`stores.csv`)

25 stores: **8 in Bangalore (Tier 1)**, and 17 across Tier 2/3 towns —
Mysore, Hubli, Tumkur, Davangere, Belagavi, Mangaluru, Shivamogga, Ballari,
Kalaburagi, Udupi, Hassan, Vijayapura.

Each store carries:

| Field | Meaning |
|---|---|
| `footfall_index` | Relative weekly foot traffic (1.0 = average) |
| `income_index` | Relative purchasing power of the catchment area |
| `store_size` | Small / Medium / Large |
| `premium_affinity`, `midrange_affinity`, `budget_affinity`, `keypad_affinity` | Sum to 1; how the store's demand naturally splits across price tiers |

Affinities are drawn per store from a Dirichlet distribution whose base
vector is shifted by tier and income, so a Tier-1 mall store lands around
35-40% premium/flagship affinity while a Tier-3 local-market store lands
below 5%, with individual-store variation layered on top rather than every
store in a tier looking identical. Example:

| store | tier / type | premium_affinity | budget_affinity |
|---|---|---|---|
| ST001 Indiranagar Premium Mall | Tier 1 | 0.423 | 0.194 |
| ST003 MG Road Premium Mall | Tier 1 | 0.385 | 0.200 |
| ST013 Tumkur Local Market | Tier 3 | 0.016 | 0.408 |
| ST021 Ballari Local Market | Tier 3 | 0.014 | 0.515 |

These affinities are **used directly** by the sales generator (they multiply
base demand for the matching product category) — they aren't decorative.

## 2. Product master data (`products.csv`)

60 fictional models across 7 categories (Keypad, Entry, Budget, Mid-range,
Upper-mid, Premium, Flagship), priced from **Rs 6,300 to Rs 1,50,000**.

Models are grouped into brand "lineages" of 1-3 generations, e.g.:

```
Vantix Halo  ->  Vantix Halo 2  ->  Vantix Halo 3
```

linked via `successor_model_id`. Roughly a third of lineages launch entirely
within the 52-week window (giving genuine "new phone launch" events); the
rest have a predecessor already on sale at week 1 with the successor
launching mid-window, which is what drives the cannibalization checks below.

Each product also stores `peak_week_offset` (8-10 weeks, randomized per
model per the assignment's "peaks in 8-10 weeks" spec) and `decline_rate`
(per-model, so lifecycle curves aren't identical across products).

## 3. Sales history (`sales_history.csv`)

78,000 rows = 25 stores x 60 models x 52 weeks. Columns:
`week_start, week_number, store_id, model_id, units_sold, sales_value, is_festive_week`.
`sales_value = units_sold x price` exactly (verified in validation).

### Demand model

For each (store, model) pair, expected weekly units are built as:

```
expected_units =
    footfall_index x store_size_factor        # store scale
  x category_affinity                          # store's fit for this product's category
  x price_elasticity_factor                    # cheaper phones move more units
  x per_combo_appeal                            # fixed random draw -> some combos are naturally hot/cold sellers
  x lifecycle_multiplier(week)                  # launch -> growth -> peak -> decline curve
  x cannibalization_multiplier(week)            # shrinks once a successor has launched
  x festive_multiplier(week)                    # 1.0 in normal weeks
```

Actual `units_sold` is then a **Poisson draw** around that expected value
(seeded, reproducible), which is what keeps sales integer, non-negative, and
naturally "lumpy" rather than smooth — 72% of all rows are zero-unit weeks,
i.e. most models don't sell at most stores in most weeks, exactly as real
retail data looks.

### Lifecycle

Each model ramps from launch to its own `peak_week_offset` (8-10 weeks),
holds briefly, then decays exponentially at its own `decline_rate`. No two
models share an identical curve.

### Cannibalization

When a model has a `successor_model_id`, its multiplier is pulled down
(toward ~25% of its own curve) in proportion to how far along the
successor's own ramp-up is — so cannibalization phases in gradually as the
new model gains share, rather than an instant cliff.

**Actual measured evidence** (6-week window before vs. after successor
launch, from the generated data):

| predecessor | successor | successor launch (week) | units before | units after | change |
|---|---|---|---|---|---|
| MD018 | MD019 | 14 | 339 | 130 | -61.7% |
| MD029 | MD030 | 13 | 74 | 31 | -58.1% |
| MD045 | MD046 | 17 | 59 | 27 | -54.2% |
| MD020 | MD021 | 35 | 251 | 135 | -46.2% |
| MD009 | MD010 | 39 | 215 | 124 | -42.3% |

Across all 13 lineage pairs where both sides had at least 6 weeks of
before/after data inside the 52-week window, **13/13 (100%) declined**, with
an average decline of **-43.4%** in the six weeks following the successor's
launch.

### Festive season

Two fixed, documented festive weeks:

- **Week 6** (week_start **2024-10-07**) — Dussehra, base multiplier 2.6x
- **Week 9** (week_start **2024-10-28**) — Diwali, base multiplier 3.6x

The multiplier is further scaled per **category** (budget/mid-range get a
bigger relative lift than flagship, per the assignment) and per **store**
(a small random per-store variation), so the spike is not a flat constant
applied everywhere.

**Actual measured result:** average weekly units in the two festive weeks =
**4,895.5** vs. **1,138.8** in an average non-festive week — a **4.30x**
uplift, consistent with the assignment's stated 3-4x range.

### Store mix differentiation

Actual unit-share by tier and category group, computed from the generated
data:

| Tier | Budget/Entry/Keypad | Mid-range/Upper-mid | Premium/Flagship |
|---|---|---|---|
| Tier 1 (Bangalore) | 50.9% | 35.0% | **14.1%** |
| Tier 2 | 69.4% | 26.1% | 4.5% |
| Tier 3 | 81.5% | 17.4% | **1.1%** |

Tier-1 stores sell premium/flagship phones at roughly **12-13x** the rate of
Tier-3 stores (share basis), and Tier-3 stores lean far more heavily into
budget/entry/keypad, matching the assignment's requirement that stores are
not interchangeable.

---

## Validation results (from `validate_data.py`, actual run)

```
[PASS] Store count == 25
[PASS] Bangalore (Tier 1) store count == 8
[PASS] Product count ~= 60 (actual = 60)
[PASS] Historical period == 52 weeks
[PASS] Price range within approx Rs 6,000 - Rs 1,50,000 (actual: Rs 6,300 - Rs 150,000)
[PASS] Tier 1 stores have materially higher premium/flagship share than Tier 3
[PASS] Tier 3 stores have materially higher budget/entry/keypad share than Tier 1
[PASS] Festive weeks show materially higher sales than normal weeks (ratio = 4.30x)
[PASS] Majority of examinable predecessor models decline after successor launch (13/13, avg -43.4%)
[PASS] No negative units_sold
[PASS] No fractional units_sold
[PASS] No invalid store_id references
[PASS] No invalid model_id references
[PASS] No missing critical values
[PASS] sales_value == units_sold x price for all rows (0 mismatches)
[PASS] No duplicate (store_id, model_id, week_number) rows
[PASS] Row count == stores x products x weeks (78,000 == 78,000)

OVERALL RESULT: ALL CHECKS PASSED
```

---

## Assumptions made

1. **Data window**: chose a specific real 52-week Monday-anchored calendar
   (2024-09-02 to 2025-08-25) so festive weeks could be tied to real
   Dussehra/Diwali dates. Any 52-week window would work equally well for
   later phases.
2. **Festive weeks**: only Dussehra and Diwali are modeled as major spikes
   (as explicitly named in the assignment). Other regional
   festivals/holidays are not separately modeled in Phase 1.
3. **Keypad phone pricing**: the assignment gives an overall price range of
   Rs 6,000-1,50,000 *and* lists "Keypad" as a category; real keypad phones
   are usually cheaper than Rs 6,000, but to satisfy both constraints as
   written, Keypad models are priced at the low end of the stated range
   (~Rs 6,000-8,500) rather than below it.
4. **Lineage launch timing**: roughly a third of lineages start their first
   generation before the data window (already mature/declining at week 1),
   and the rest launch within it — this was necessary to have both "already
   established" products and genuine "new launch" events in the same
   52-week snapshot, per the assignment's realism requirements.
5. **appeal/noise model**: used a fixed per-(store, model) log-normal
   "appeal" draw plus Poisson sampling for weekly noise — this is one
   reasonable choice among several equally valid stochastic demand models;
   it was chosen because it naturally produces non-negative integers,
   long-tailed "hit vs. niche" product variation, and zero-sale weeks
   without any manual patching.
6. **Store name/location list**: city and location-type names are
   representative/fictional placements within real Karnataka cities, not
   actual MobiMart-branded storefronts.

---

**Phase 1 is complete.** No forecasting, allocation, EOL, markdown/transfer
logic, baseline, simulation, dashboard, or Streamlit UI has been built.
Waiting for approval before starting Phase 2.
