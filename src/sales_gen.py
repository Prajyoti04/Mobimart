"""
sales_gen.py
------------
Generates 52 weeks of weekly sales_history.csv for every (store, model)
combination, using a reproducible demand model that combines:

  1. Store base demand      -> footfall_index * store_size_factor
  2. Category affinity      -> store's premium/midrange/budget/keypad weights
  3. Price elasticity       -> more expensive phones sell fewer units, all else equal
  4. Product lifecycle      -> launch -> growth -> peak -> decline -> EOL curve,
                                peaking ~8-10 weeks after launch (per-model)
  5. Successor cannibalization -> once a successor launches, the predecessor's
                                curve is pulled down proportionally to the
                                successor's own ramp-up
  6. Festive season spikes  -> Dussehra/Diwali weeks get 3-4x multipliers that
                                vary by store and category
  7. Stochastic noise       -> Poisson-sampled units around the modelled mean,
                                plus a chance of a "no sale that week" zero,
                                so the data isn't mechanically smooth
"""

from datetime import date, timedelta
import numpy as np
import pandas as pd

NUM_WEEKS = 52

SIZE_FACTOR = {"Small": 0.7, "Medium": 1.0, "Large": 1.45}

CATEGORY_TO_AFFINITY_COL = {
    "Flagship":  "premium_affinity",
    "Premium":   "premium_affinity",
    "Upper-mid": "midrange_affinity",
    "Mid-range": "midrange_affinity",
    "Budget":    "budget_affinity",
    "Entry":     "budget_affinity",
    "Keypad":    "keypad_affinity",
}

# Festive weeks: fixed, documented historical windows for the chosen 52-week
# period starting 2024-09-02 (Monday). Week numbers are 1-indexed.
#   Week 6  (week_start 2024-10-07) -> Dussehra week
#   Week 9  (week_start 2024-10-28) -> Diwali week
FESTIVE_WEEKS = {
    6: dict(name="Dussehra", base_multiplier=2.6),
    9: dict(name="Diwali", base_multiplier=3.6),
}

# category -> relative sensitivity to festive uplift (budget/mid respond more)
FESTIVE_CATEGORY_SENSITIVITY = {
    "Keypad": 0.9,
    "Entry": 1.15,
    "Budget": 1.30,
    "Mid-range": 1.20,
    "Upper-mid": 1.00,
    "Premium": 0.85,
    "Flagship": 0.75,
}


def week_start_dates(start_date: date, num_weeks: int = NUM_WEEKS):
    return [start_date + timedelta(weeks=i) for i in range(num_weeks)]


def _lifecycle_multiplier(weeks_since_launch: np.ndarray, peak_week_offset: float, decline_rate: float,
                           has_launched: np.ndarray) -> np.ndarray:
    """
    Vectorized lifecycle curve for a single product across all weeks.

    - Before launch: 0 (product not yet on shelves)
    - Ramp (0 -> peak_week_offset): smooth S-curve growth to 1.0
    - Peak plateau (peak .. peak+3): stays near 1.0 with slight variation
    - Decline: exponential decay at the model's own decline_rate
    """
    mult = np.zeros_like(weeks_since_launch, dtype=float)

    ramp_mask = has_launched & (weeks_since_launch <= peak_week_offset)
    # smooth growth: sigmoid-ish ramp reaching ~1.0 at peak_week_offset
    t = np.clip(weeks_since_launch[ramp_mask] / max(peak_week_offset, 1), 0, 1)
    mult[ramp_mask] = 0.15 + 0.85 * (t ** 1.4)

    plateau_mask = has_launched & (weeks_since_launch > peak_week_offset) & (weeks_since_launch <= peak_week_offset + 3)
    mult[plateau_mask] = 1.0

    decline_mask = has_launched & (weeks_since_launch > peak_week_offset + 3)
    weeks_into_decline = weeks_since_launch[decline_mask] - (peak_week_offset + 3)
    mult[decline_mask] = np.exp(-decline_rate * weeks_into_decline)

    return mult


def generate_sales_history(stores_df: pd.DataFrame, products_df: pd.DataFrame,
                            start_date: date = date(2024, 9, 2), seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    weeks = np.arange(1, NUM_WEEKS + 1)
    week_dates = week_start_dates(start_date, NUM_WEEKS)

    # Pre-compute successor launch-week lookup for cannibalization
    launch_week_by_model = dict(zip(products_df["model_id"], products_df["launch_week"]))

    all_rows = []

    for _, store in stores_df.iterrows():
        size_factor = SIZE_FACTOR[store["store_size"]]
        store_base = store["footfall_index"] * size_factor

        # per-store random "store personality" seed so combos aren't uniform
        store_rng = np.random.default_rng(seed + hash(store["store_id"]) % 100000)

        for _, prod in products_df.iterrows():
            affinity_col = CATEGORY_TO_AFFINITY_COL[prod["category"]]
            category_affinity = store[affinity_col]

            # price elasticity: higher price -> naturally lower unit volume
            price_factor = (15000 / max(prod["price"], 1000)) ** 0.55

            # a fixed, reproducible per-(store,model) "appeal" draw so some
            # combinations are naturally low/high demand (not every model
            # sells at every store)
            combo_seed = abs(hash((store["store_id"], prod["model_id"], seed))) % (2**32)
            combo_rng = np.random.default_rng(combo_seed)
            appeal = combo_rng.lognormal(mean=0.0, sigma=0.55)  # median ~1.0, long right tail

            base_weekly_mean = store_base * category_affinity * price_factor * appeal * 22.0

            weeks_since_launch = weeks - prod["launch_week"]
            has_launched = weeks_since_launch >= 0

            lifecycle_mult = _lifecycle_multiplier(
                weeks_since_launch, prod["peak_week_offset"], prod["decline_rate"], has_launched
            )

            # --- cannibalization: if this product has a successor, pull its
            # demand down once the successor has launched, proportional to
            # the successor's own ramp-up curve ---
            successor_id = prod.get("successor_model_id")
            cannibal_mult = np.ones(NUM_WEEKS)
            if pd.notna(successor_id) and successor_id in launch_week_by_model:
                succ_launch = launch_week_by_model[successor_id]
                succ_weeks_since_launch = weeks - succ_launch
                succ_has_launched = succ_weeks_since_launch >= 0
                # reuse the same shape as a generic ramp to approximate the
                # successor's growth (peak offset ~9 weeks is a reasonable default)
                succ_ramp = _lifecycle_multiplier(
                    succ_weeks_since_launch, 9, 0.06, succ_has_launched
                )
                # predecessor demand shrinks as successor ramp grows,
                # bottoming out around 25% of its own baseline curve
                cannibal_mult = 1.0 - 0.75 * np.clip(succ_ramp, 0, 1)

            combined_mult = lifecycle_mult * cannibal_mult

            # --- festive multiplier ---
            festive_mult = np.ones(NUM_WEEKS)
            for wk, info in FESTIVE_WEEKS.items():
                idx = wk - 1
                cat_sensitivity = FESTIVE_CATEGORY_SENSITIVITY[prod["category"]]
                store_variation = 0.85 + 0.3 * store_rng.random()  # per-store variation
                festive_mult[idx] = 1.0 + (info["base_multiplier"] - 1.0) * cat_sensitivity * store_variation

            expected_units = base_weekly_mean * combined_mult * festive_mult

            # stochastic draw: Poisson noise around the expected mean,
            # with a floor of 0 and integer units.
            units = combo_rng.poisson(lam=np.clip(expected_units, 0, None))

            # some very-low-appeal combos should genuinely have zero-sale
            # weeks even outside lifecycle edges -> already naturally occurs
            # via Poisson when lambda is small; no extra hack needed.

            sales_value = units * prod["price"]

            for i in range(NUM_WEEKS):
                all_rows.append((
                    week_dates[i].isoformat(),
                    weeks[i],
                    store["store_id"],
                    prod["model_id"],
                    int(units[i]),
                    float(sales_value[i]),
                    1 if weeks[i] in FESTIVE_WEEKS else 0,
                ))

    df = pd.DataFrame(all_rows, columns=[
        "week_start", "week_number", "store_id", "model_id",
        "units_sold", "sales_value", "is_festive_week"
    ])
    return df


if __name__ == "__main__":
    from stores_gen import generate_stores
    from products_gen import generate_products

    stores_df = generate_stores()
    products_df = generate_products()
    sales_df = generate_sales_history(stores_df, products_df)
    print(sales_df.shape)
    print(sales_df.head())
    print("Total units:", sales_df["units_sold"].sum())
