"""
products_gen.py
----------------
Generates the product master data (products.csv) for MobiMart Phase 1.

Design notes
------------
~60 fictional phone models spread across 7 categories with realistic price
bands (overall range roughly Rs 6,000 - Rs 1,50,000, per the assignment).

Models are organised into "lineages" per brand, e.g.:

    Nubira Spark -> Nubira Spark 2 -> Nubira Spark 3

Each lineage has a `successor_model_id` chain. Some models in each lineage
launch *before* the 52-week data window (they are already mature/declining
at week 1), and some launch *during* the window (new launches), so that the
dataset contains genuine mid-window launch + cannibalization events as
required by the assignment.

lifecycle_stage in products.csv is a descriptive label for where the model
sits at the *end* of the 52-week window (New / Growth / Peak / Mature /
Decline / EOL). The actual week-by-week demand curve is computed later in
sales_gen.py using launch_week and a per-model peak-week parameter.
"""

import numpy as np
import pandas as pd
from datetime import date, timedelta

CATEGORY_PRICE_BANDS = {
    "Keypad":     (6000, 8500),
    "Entry":      (8500, 15000),
    "Budget":     (15000, 25000),
    "Mid-range":  (25000, 45000),
    "Upper-mid":  (45000, 70000),
    "Premium":    (70000, 100000),
    "Flagship":   (100000, 150000),
}

CATEGORY_ORDER = list(CATEGORY_PRICE_BANDS.keys())

BRANDS = ["Nubira", "Vantix", "Corvo", "Zentro", "Kryon", "Orbil", "Halex", "Ferno"]

FAMILY_NAME_POOL = [
    "Spark", "Nova", "Edge", "Prime", "Air", "Max", "Neo", "Pulse", "Zen",
    "Core", "Flux", "Vibe", "Glide", "Orbit", "Ray", "Bolt", "Halo",
    "Drift", "Ace", "Pixel", "Wave", "Sol", "Ember", "Volt", "Loop",
    "Arc", "Fuse", "Peak", "Zephyr", "Crest",
]

# Rough distribution of ~60 models across categories (must sum to ~60)
CATEGORY_MODEL_COUNTS = {
    "Keypad": 4,
    "Entry": 9,
    "Budget": 12,
    "Mid-range": 13,
    "Upper-mid": 10,
    "Premium": 7,
    "Flagship": 5,
}

NUM_WEEKS = 52


def _lineage_name(brand, family, gen):
    if gen == 1:
        return f"{brand} {family}"
    return f"{brand} {family} {gen}"


def generate_products(seed: int = 42, start_date: date = date(2024, 9, 2)) -> pd.DataFrame:
    """
    start_date: the Monday that week 1 of the sales history begins on.
    Used to translate launch_week (which may be negative, i.e. launched
    before the data window) into a calendar launch_date.
    """
    rng = np.random.default_rng(seed)

    records = []
    model_num = 1
    brand_cycle = 0

    family_pool = list(FAMILY_NAME_POOL)
    rng.shuffle(family_pool)
    family_pool_idx = 0

    for category, count in CATEGORY_MODEL_COUNTS.items():
        lo, hi = CATEGORY_PRICE_BANDS[category]

        # Group models in this category into lineages of 1-3 (predecessor
        # -> successor chains), so cannibalization has something to act on.
        remaining = count
        while remaining > 0:
            lineage_len = min(remaining, rng.choice([1, 2, 3], p=[0.35, 0.40, 0.25]))
            brand = BRANDS[brand_cycle % len(BRANDS)]
            brand_cycle += 1
            family_name = family_pool[family_pool_idx % len(family_pool)]
            family_pool_idx += 1

            # Decide when the *first* model of this lineage launched.
            # Many lineages started well before the data window (they're
            # already in the market); some start the lineage mid-window.
            first_launch_week = int(rng.choice(
                [-52, -40, -30, -20, -10, -4, 1, 6, 12],
                p=[0.16, 0.14, 0.14, 0.12, 0.12, 0.10, 0.10, 0.06, 0.06]
            ))

            prev_model_id = None
            gen_launch_week = first_launch_week
            lineage_model_ids = []

            for gen in range(1, lineage_len + 1):
                model_id = f"MD{model_num:03d}"
                model_num += 1

                price = float(rng.uniform(lo, hi))
                # later generations in a lineage are usually priced a bit
                # higher than their predecessor (successor premium)
                if gen > 1:
                    price *= (1 + rng.uniform(0.02, 0.08))
                price = round(min(price, 150000), -2)  # round to nearest 100

                launch_week = gen_launch_week
                launch_date = start_date + timedelta(weeks=launch_week - 1)

                # per-model lifecycle shape parameters used later by sales_gen
                peak_week_offset = int(rng.integers(8, 11))  # 8-10 weeks to peak, per assignment
                decline_rate = round(float(rng.uniform(0.04, 0.09)), 4)

                model_name = _lineage_name(brand, family_name, gen)

                records.append(dict(
                    model_id=model_id,
                    brand=brand,
                    model_name=model_name,
                    category=category,
                    price=price,
                    launch_week=launch_week,
                    launch_date=launch_date.isoformat(),
                    successor_model_id=None,  # filled in once we know the next gen's id
                    peak_week_offset=peak_week_offset,
                    decline_rate=decline_rate,
                ))
                lineage_model_ids.append(model_id)

                if prev_model_id is not None:
                    # link previous model's successor to this one
                    for r in records:
                        if r["model_id"] == prev_model_id:
                            r["successor_model_id"] = model_id
                prev_model_id = model_id

                # next generation launches somewhat after this one (9-15 months later),
                # but clipped to stay broadly within/near our window for realism
                gen_launch_week = gen_launch_week + int(rng.integers(38, 56))

            remaining -= lineage_len

    df = pd.DataFrame(records)

    # lifecycle_stage as of the END of the 52-week window (week 52)
    def stage_at_end(row):
        weeks_live = NUM_WEEKS - row["launch_week"]
        if row["launch_week"] > NUM_WEEKS:
            return "Not Yet Launched"
        if weeks_live < 0:
            return "Not Yet Launched"
        if weeks_live <= 2:
            return "Launch"
        if weeks_live <= row["peak_week_offset"]:
            return "Growth"
        if weeks_live <= row["peak_week_offset"] + 4:
            return "Peak"
        if row["successor_model_id"] is not None and weeks_live > row["peak_week_offset"] + 4:
            return "Decline"
        if weeks_live > row["peak_week_offset"] + 30:
            return "End-of-Life"
        return "Decline" if weeks_live > row["peak_week_offset"] + 4 else "Mature"

    df["lifecycle_stage"] = df.apply(stage_at_end, axis=1)

    # sanity trim/pad to land close to 60 (assignment says "approximately")
    return df.reset_index(drop=True)


FIELD_DESCRIPTIONS = {
    "model_id": "Unique product identifier (MD001, MD002, ...)",
    "brand": "Fictional phone brand",
    "model_name": "Model name, including generation suffix for successors (e.g. 'Nubira Spark 2')",
    "category": "Price/positioning category: Keypad, Entry, Budget, Mid-range, Upper-mid, Premium, Flagship",
    "price": "MRP in INR",
    "launch_week": "Week number (1-52) the model launched within the data window; values <=0 mean it launched before the window (already on sale at week 1)",
    "launch_date": "Calendar date corresponding to launch_week",
    "successor_model_id": "model_id of the direct successor in this lineage, if any (used for cannibalization logic)",
    "peak_week_offset": "Weeks after launch at which the model reaches peak demand (8-10 typical, per assignment)",
    "decline_rate": "Per-week exponential decline rate applied after peak",
    "lifecycle_stage": "Descriptive lifecycle stage as of the end of the 52-week window",
}

if __name__ == "__main__":
    df = generate_products()
    print(df.shape)
    print(df[["model_id", "brand", "model_name", "category", "price", "launch_week", "successor_model_id"]].head(15))
