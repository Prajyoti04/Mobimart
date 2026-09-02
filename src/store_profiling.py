"""
store_profiling.py
-------------------
Phase 2: computes a full store-profiling table from the actual Phase 1
sales_history.csv, stores.csv, and products.csv. No data is regenerated or
altered here — this module only reads and aggregates.

All functions take/return pandas DataFrames so they can be tested and
reused independently of the CLI entry point (phase2_analysis.py).
"""

from pathlib import Path
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

CATEGORY_ORDER = ["Keypad", "Entry", "Budget", "Mid-range", "Upper-mid", "Premium", "Flagship"]
CATEGORY_SHARE_COL = {
    "Keypad": "keypad_share",
    "Entry": "entry_share",
    "Budget": "budget_share",
    "Mid-range": "midrange_share",
    "Upper-mid": "upper_mid_share",
    "Premium": "premium_share",
    "Flagship": "flagship_share",
}

FESTIVE_WEEK_NUMBERS = {6, 9}  # must match Phase 1 src/sales_gen.py FESTIVE_WEEKS


def load_phase1_data():
    stores = pd.read_csv(DATA_DIR / "stores.csv")
    products = pd.read_csv(DATA_DIR / "products.csv")
    sales = pd.read_csv(DATA_DIR / "sales_history.csv", parse_dates=["week_start"])
    return stores, products, sales


def _merged_sales(sales: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    return sales.merge(
        products[["model_id", "category", "price", "brand", "model_name"]],
        on="model_id", how="left"
    )


# ---------------------------------------------------------------------------
# Section 2: base performance metrics + category shares
# ---------------------------------------------------------------------------

def compute_base_metrics(stores: pd.DataFrame, merged: pd.DataFrame) -> pd.DataFrame:
    num_weeks = merged["week_number"].nunique()

    agg = merged.groupby("store_id").agg(
        total_units_sold=("units_sold", "sum"),
        total_sales_value=("sales_value", "sum"),
    ).reset_index()

    agg["average_weekly_units"] = agg["total_units_sold"] / num_weeks
    agg["average_weekly_revenue"] = agg["total_sales_value"] / num_weeks
    agg["average_selling_price"] = np.where(
        agg["total_units_sold"] > 0,
        agg["total_sales_value"] / agg["total_units_sold"],
        0.0
    )

    profile = stores[["store_id", "store_name", "city", "tier", "location_type"]].merge(
        agg, on="store_id", how="left"
    )
    return profile


def compute_category_shares(merged: pd.DataFrame) -> pd.DataFrame:
    cat_units = merged.groupby(["store_id", "category"])["units_sold"].sum().unstack(fill_value=0)
    for cat in CATEGORY_ORDER:
        if cat not in cat_units.columns:
            cat_units[cat] = 0
    cat_units = cat_units[CATEGORY_ORDER]

    totals = cat_units.sum(axis=1)
    shares = cat_units.div(totals.replace(0, np.nan), axis=0).fillna(0.0)
    shares = shares.rename(columns=CATEGORY_SHARE_COL)
    shares = shares.reset_index()
    return shares


# ---------------------------------------------------------------------------
# Section 3: premium / budget / midrange indices (from ACTUAL sales, not
# copied store affinities)
# ---------------------------------------------------------------------------

def compute_orientation_indices(shares: pd.DataFrame) -> pd.DataFrame:
    """
    premium_index   = premium_share + flagship_share
    midrange_index  = midrange_share + upper_mid_share
    budget_index    = budget_share + entry_share + keypad_share

    These are computed purely from actual units sold at each store (the
    category shares above), which is the whole point of Phase 2: verifying
    that real sales behavior matches -- or diverges from -- the Phase 1
    store affinities, rather than restating those affinities.
    """
    out = shares.copy()
    out["premium_index"] = out["premium_share"] + out["flagship_share"]
    out["midrange_index"] = out["midrange_share"] + out["upper_mid_share"]
    out["budget_index"] = out["budget_share"] + out["entry_share"] + out["keypad_share"]
    return out[["store_id", "premium_index", "midrange_index", "budget_index"]]


# ---------------------------------------------------------------------------
# Section 4: demand concentration (top-5 model share)
# ---------------------------------------------------------------------------

def compute_demand_concentration(merged: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    records = []
    for store_id, grp in merged.groupby("store_id"):
        model_units = grp.groupby("model_id")["units_sold"].sum().sort_values(ascending=False)
        total = model_units.sum()
        top_share = model_units.head(top_n).sum() / total if total > 0 else 0.0
        records.append((store_id, top_share))
    return pd.DataFrame(records, columns=["store_id", f"top_{top_n}_model_share"])


# ---------------------------------------------------------------------------
# Section 5: product-level store affinity (store_model_demand / overall_model_demand)
# ---------------------------------------------------------------------------

def compute_store_model_affinity(merged: pd.DataFrame) -> pd.DataFrame:
    """
    affinity_score(store, model) =
        (store's share of its own total units that this model represents)
        /
        (chain-wide share of total units that this model represents)

    i.e. a normalized index-of-100 style score:
      score = (store_model_units / store_total_units) / (model_total_units / chain_total_units)

    score > 1  -> store over-indexes on this model relative to the chain
    score == 1 -> store sells this model at exactly the chain-average rate
    score < 1  -> store under-indexes on this model

    This mirrors a standard "category index" retail metric and is a
    defensible, explainable measure for future allocation use (not built
    here, per scope).
    """
    store_totals = merged.groupby("store_id")["units_sold"].sum()
    model_totals = merged.groupby("model_id")["units_sold"].sum()
    chain_total = merged["units_sold"].sum()

    store_model = merged.groupby(["store_id", "model_id"])["units_sold"].sum().reset_index()
    store_model["store_total"] = store_model["store_id"].map(store_totals)
    store_model["model_total"] = store_model["model_id"].map(model_totals)

    store_share_of_model = store_model["units_sold"] / store_model["model_total"].replace(0, np.nan)
    model_share_of_chain = store_model["model_total"] / chain_total

    store_share_within_store = store_model["units_sold"] / store_model["store_total"].replace(0, np.nan)
    model_share_within_chain = store_model["model_total"] / chain_total

    store_model["affinity_score"] = (
        store_share_within_store / model_share_within_chain.replace(0, np.nan)
    ).fillna(0.0)

    return store_model[["store_id", "model_id", "units_sold", "affinity_score"]]


def top_affinity_products_per_store(affinity_df: pd.DataFrame, products: pd.DataFrame,
                                     min_units: int = 15, top_n: int = 3) -> pd.DataFrame:
    """Returns each store's top over-indexing products (with a minimum
    volume floor so a single lucky sale doesn't produce a meaningless
    'infinite' affinity score)."""
    df = affinity_df[affinity_df["units_sold"] >= min_units].merge(
        products[["model_id", "brand", "model_name", "category"]], on="model_id", how="left"
    )
    df = df.sort_values(["store_id", "affinity_score"], ascending=[True, False])
    return df.groupby("store_id").head(top_n).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Section 6: festive sensitivity
# ---------------------------------------------------------------------------

def compute_festive_lift(merged: pd.DataFrame) -> pd.DataFrame:
    festive = merged[merged["week_number"].isin(FESTIVE_WEEK_NUMBERS)]
    normal = merged[~merged["week_number"].isin(FESTIVE_WEEK_NUMBERS)]

    festive_avg = festive.groupby("store_id")["units_sold"].sum() / len(FESTIVE_WEEK_NUMBERS)
    normal_avg = normal.groupby("store_id")["units_sold"].sum() / (merged["week_number"].nunique() - len(FESTIVE_WEEK_NUMBERS))

    lift = (festive_avg / normal_avg.replace(0, np.nan)).rename("festive_lift").reset_index()
    lift.columns = ["store_id", "festive_lift"]
    return lift


def compute_festive_lift_by_category(merged: pd.DataFrame) -> pd.DataFrame:
    festive = merged[merged["week_number"].isin(FESTIVE_WEEK_NUMBERS)]
    normal = merged[~merged["week_number"].isin(FESTIVE_WEEK_NUMBERS)]

    festive_avg = festive.groupby("category")["units_sold"].sum() / len(FESTIVE_WEEK_NUMBERS)
    normal_avg = normal.groupby("category")["units_sold"].sum() / (merged["week_number"].nunique() - len(FESTIVE_WEEK_NUMBERS))

    lift = (festive_avg / normal_avg.replace(0, np.nan)).reindex(CATEGORY_ORDER).rename("festive_lift")
    return lift.reset_index().rename(columns={"index": "category"})


# ---------------------------------------------------------------------------
# Section 7: weekly sales velocity / volatility
# ---------------------------------------------------------------------------

def compute_store_velocity(merged: pd.DataFrame) -> pd.DataFrame:
    weekly = merged.groupby(["store_id", "week_number"])["units_sold"].sum().reset_index()
    stats = weekly.groupby("store_id")["units_sold"].agg(
        mean_weekly_units="mean",
        median_weekly_units="median",
        max_weekly_units="max",
        std_weekly_units="std",
    ).reset_index()
    stats["std_weekly_units"] = stats["std_weekly_units"].fillna(0.0)
    stats["demand_volatility"] = np.where(
        stats["mean_weekly_units"] > 0,
        stats["std_weekly_units"] / stats["mean_weekly_units"],
        0.0
    )  # coefficient of variation -- comparable across stores of different sizes
    return stats


def compute_store_category_velocity(merged: pd.DataFrame) -> pd.DataFrame:
    weekly = merged.groupby(["store_id", "category", "week_number"])["units_sold"].sum().reset_index()
    stats = weekly.groupby(["store_id", "category"])["units_sold"].agg(
        mean_weekly_units="mean",
        std_weekly_units="std",
    ).reset_index()
    stats["std_weekly_units"] = stats["std_weekly_units"].fillna(0.0)
    stats["cv"] = np.where(stats["mean_weekly_units"] > 0,
                            stats["std_weekly_units"] / stats["mean_weekly_units"], 0.0)
    return stats


def compute_store_model_velocity(merged: pd.DataFrame) -> pd.DataFrame:
    weekly = merged.groupby(["store_id", "model_id", "week_number"])["units_sold"].sum().reset_index()
    stats = weekly.groupby(["store_id", "model_id"])["units_sold"].agg(
        mean_weekly_units="mean",
        std_weekly_units="std",
    ).reset_index()
    stats["std_weekly_units"] = stats["std_weekly_units"].fillna(0.0)
    stats["cv"] = np.where(stats["mean_weekly_units"] > 0,
                            stats["std_weekly_units"] / stats["mean_weekly_units"], 0.0)
    return stats


# ---------------------------------------------------------------------------
# Section 8: store segmentation (rule-based, explainable)
# ---------------------------------------------------------------------------

def segment_stores_rule_based(profile: pd.DataFrame) -> pd.Series:
    """
    Simple, explainable rule-based segmentation using two actual observed
    signals: premium_index (share of units that are premium/flagship) and
    average_selling_price (ASP).

    Thresholds are chosen from the natural break points in the *actual*
    distribution of premium_index across the 25 stores (see
    phase2_analysis.py, which prints the distribution used to pick these
    cutoffs), not arbitrary round numbers.

    Rules (evaluated in order):
      - premium_index >= 0.10  -> "Premium"
      - budget_index  >= 0.65  -> "Value"
      - otherwise             -> "Balanced"
    """
    def classify(row):
        if row["premium_index"] >= 0.10:
            return "Premium"
        if row["budget_index"] >= 0.65:
            return "Value"
        return "Balanced"

    return profile.apply(classify, axis=1)


def build_full_store_profile(stores: pd.DataFrame, products: pd.DataFrame, sales: pd.DataFrame) -> dict:
    """
    Runs the full Phase 2 pipeline and returns a dict of all intermediate
    and final DataFrames so the analysis script and validator can both use
    them without recomputing.
    """
    merged = _merged_sales(sales, products)

    base = compute_base_metrics(stores, merged)
    shares = compute_category_shares(merged)
    indices = compute_orientation_indices(shares)
    concentration = compute_demand_concentration(merged, top_n=5)
    festive_lift = compute_festive_lift(merged)
    velocity = compute_store_velocity(merged)

    profile = base.merge(shares, on="store_id") \
                  .merge(indices, on="store_id") \
                  .merge(concentration, on="store_id") \
                  .merge(festive_lift, on="store_id") \
                  .merge(velocity, on="store_id")

    profile["store_segment"] = segment_stores_rule_based(profile)

    affinity = compute_store_model_affinity(merged)
    top_affinity = top_affinity_products_per_store(affinity, products)
    festive_by_category = compute_festive_lift_by_category(merged)
    category_velocity = compute_store_category_velocity(merged)
    model_velocity = compute_store_model_velocity(merged)

    return dict(
        profile=profile,
        merged=merged,
        affinity=affinity,
        top_affinity=top_affinity,
        festive_by_category=festive_by_category,
        category_velocity=category_velocity,
        model_velocity=model_velocity,
    )
