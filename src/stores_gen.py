"""
stores_gen.py
-------------
Generates the store master data (stores.csv) for MobiMart Phase 1.

Design notes
------------
25 stores across Karnataka:
    - 8 stores in Bangalore (Tier 1)
    - 17 stores spread across Tier 2/3 cities (Mysore, Hubli, Tumkur,
      Davangere, and other suitable Karnataka towns)

Each store gets a "personality" made up of:
    footfall_index    -> relative weekly foot traffic (drives volume)
    income_index      -> relative purchasing power of catchment area
    store_size        -> Small / Medium / Large (drives SKU depth/volume)
    premium_affinity, midrange_affinity, budget_affinity, keypad_affinity
                      -> probability weights (sum to 1) describing how much
                         of this store's natural demand falls into each
                         broad price category. This is what makes a premium
                         Bangalore mall store behave completely differently
                         from a tier-3 value market store.

These affinities are NOT decorative -- the sales generator directly
multiplies base demand by the relevant affinity for a product's category,
so the store mix genuinely shapes what sells where.
"""

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Static location data
# ---------------------------------------------------------------------------

BANGALORE_LOCATIONS = [
    ("Indiranagar",        "Premium Mall"),
    ("Koramangala",        "High Street"),
    ("MG Road",            "Premium Mall"),
    ("Whitefield (ITPL)",  "Tech Park Hub"),
    ("Electronic City",    "Tech Park Hub"),
    ("Jayanagar",          "High Street"),
    ("Rajajinagar",        "Metro Market"),
    ("Yeshwanthpur",       "Suburban Mall"),
]

TIER2_3_LOCATIONS = [
    ("Mysore",      "Town Center"),
    ("Mysore",      "Local Market"),
    ("Hubli",       "Town Center"),
    ("Hubli",       "Highway Store"),
    ("Tumkur",      "Local Market"),
    ("Tumkur",      "Town Center"),
    ("Davangere",   "Local Market"),
    ("Davangere",   "Town Center"),
    ("Belagavi",    "Town Center"),
    ("Mangaluru",   "High Street"),
    ("Mangaluru",   "Town Center"),
    ("Shivamogga",  "Local Market"),
    ("Ballari",     "Local Market"),
    ("Kalaburagi",  "Town Center"),
    ("Udupi",       "Local Market"),
    ("Hassan",      "Local Market"),
    ("Vijayapura",  "Town Center"),
]

# location_type -> (footfall base, income base, size weighting) baseline hints
LOCATION_PROFILE = {
    "Premium Mall":    dict(footfall=(0.75, 1.05), income=(1.15, 1.45), size_bias=("Large", "Medium")),
    "Tech Park Hub":   dict(footfall=(0.55, 0.85), income=(1.05, 1.35), size_bias=("Medium", "Large")),
    "High Street":     dict(footfall=(0.85, 1.20), income=(0.90, 1.20), size_bias=("Medium", "Large")),
    "Metro Market":    dict(footfall=(0.70, 1.00), income=(0.80, 1.05), size_bias=("Medium", "Small")),
    "Suburban Mall":   dict(footfall=(0.60, 0.90), income=(0.85, 1.10), size_bias=("Medium", "Small")),
    "Town Center":     dict(footfall=(0.50, 0.80), income=(0.65, 0.90), size_bias=("Medium", "Small")),
    "Local Market":    dict(footfall=(0.40, 0.70), income=(0.55, 0.80), size_bias=("Small", "Medium")),
    "Highway Store":   dict(footfall=(0.35, 0.60), income=(0.60, 0.85), size_bias=("Small", "Medium")),
}

STORE_SIZES = ["Small", "Medium", "Large"]


def _draw_affinities(rng, tier, income_index):
    """
    Build a Dirichlet-flavoured affinity vector (premium, midrange, budget,
    keypad) that sums to 1, biased by tier/income so that:
      - high income + tier 1  -> strong premium/flagship pull
      - low income + tier 3   -> strong budget/keypad pull
    """
    if tier == 1:
        base = np.array([0.34, 0.34, 0.24, 0.08])
    elif tier == 2:
        base = np.array([0.16, 0.32, 0.36, 0.16])
    else:  # tier 3
        base = np.array([0.07, 0.23, 0.42, 0.28])

    # income pulls weight toward premium/midrange and away from keypad
    income_shift = (income_index - 1.0) * 0.18
    base = base + np.array([income_shift, income_shift * 0.5, -income_shift * 0.4, -income_shift * 0.6])
    base = np.clip(base, 0.02, None)

    # Small amount of per-store random personality on top of the tier baseline
    noise = rng.dirichlet(base * 12)  # concentration keeps it close to `base`
    weights = 0.7 * (base / base.sum()) + 0.3 * noise
    weights = weights / weights.sum()
    return weights  # order: premium, midrange, budget, keypad


def generate_stores(seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    records = []
    store_num = 1

    all_locations = (
        [(city, ltype, 1) for city, ltype in BANGALORE_LOCATIONS]
        + [(city, ltype, (2 if city in ("Mysore", "Hubli", "Mangaluru", "Belagavi") else 3))
           for city, ltype in TIER2_3_LOCATIONS]
    )

    for city, location_type, tier in all_locations:
        store_id = f"ST{store_num:03d}"
        profile = LOCATION_PROFILE[location_type]

        footfall_index = round(float(rng.uniform(*profile["footfall"])), 3)
        income_index = round(float(rng.uniform(*profile["income"])), 3)

        size_choices = profile["size_bias"]
        store_size = rng.choice(size_choices, p=[0.6, 0.4] if len(size_choices) == 2 else None)

        premium, midrange, budget, keypad = _draw_affinities(rng, tier, income_index)

        store_name = f"MobiMart {city} - {location_type}"

        records.append(dict(
            store_id=store_id,
            store_name=store_name,
            city=city,
            tier=f"Tier {tier}",
            location_type=location_type,
            store_size=store_size,
            footfall_index=footfall_index,
            income_index=income_index,
            premium_affinity=round(float(premium), 4),
            midrange_affinity=round(float(midrange), 4),
            budget_affinity=round(float(budget), 4),
            keypad_affinity=round(float(keypad), 4),
        ))
        store_num += 1

    df = pd.DataFrame(records)
    assert len(df) == 25, f"Expected 25 stores, got {len(df)}"
    return df


FIELD_DESCRIPTIONS = {
    "store_id": "Unique store identifier (ST001-ST025)",
    "store_name": "Human readable store name (city + location type)",
    "city": "Karnataka city the store is located in",
    "tier": "Tier 1 (Bangalore), Tier 2, or Tier 3 city classification",
    "location_type": "Nature of the retail location (mall, high street, town center, etc.)",
    "store_size": "Small / Medium / Large physical store footprint",
    "footfall_index": "Relative weekly footfall vs. an average store (1.0 = average)",
    "income_index": "Relative purchasing power of the store's catchment area (1.0 = average)",
    "premium_affinity": "Share of natural demand this store gives to Premium/Flagship phones",
    "midrange_affinity": "Share of natural demand this store gives to Mid-range/Upper-mid phones",
    "budget_affinity": "Share of natural demand this store gives to Entry/Budget phones",
    "keypad_affinity": "Share of natural demand this store gives to Keypad phones",
}

if __name__ == "__main__":
    df = generate_stores()
    print(df.head(10))
    print(df.shape)
