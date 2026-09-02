"""
validate_phase2.py
-------------------
Validates the Phase 2 store-profiling outputs. Run after phase2_analysis.py.

    python3 validate_phase2.py
"""

from pathlib import Path
import sys
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}" + (f" — {detail}" if detail else ""))
    return condition


def main():
    stores = pd.read_csv(DATA_DIR / "stores.csv")
    products = pd.read_csv(DATA_DIR / "products.csv")
    sales = pd.read_csv(DATA_DIR / "sales_history.csv")
    profiles = pd.read_csv(DATA_DIR / "store_profiles.csv")

    all_ok = True

    print("=" * 70)
    print("MOBIMART PHASE 2 — STORE PROFILE VALIDATION REPORT")
    print("=" * 70)

    # --- counts -----------------------------------------------------
    all_ok &= check("Exactly 25 store profiles", len(profiles) == 25, f"actual={len(profiles)}")
    all_ok &= check("No duplicate store_id in store_profiles", not profiles["store_id"].duplicated().any())
    all_ok &= check("Every Phase 1 store is represented",
                     set(stores["store_id"]) == set(profiles["store_id"]))
    all_ok &= check("No unexpected store IDs in store_profiles",
                     set(profiles["store_id"]).issubset(set(stores["store_id"])))

    # --- referenced model/store ids in sales still valid (sanity re-check) ---
    all_ok &= check("No unexpected model IDs in sales_history",
                     set(sales["model_id"]).issubset(set(products["model_id"])))
    all_ok &= check("No unexpected store IDs in sales_history",
                     set(sales["store_id"]).issubset(set(stores["store_id"])))

    # --- missing critical metrics -----------------------------------
    critical_cols = [
        "store_id", "store_name", "city", "tier", "store_segment",
        "total_units_sold", "total_sales_value", "average_weekly_units",
        "average_weekly_revenue", "average_selling_price",
        "keypad_share", "entry_share", "budget_share", "midrange_share",
        "upper_mid_share", "premium_share", "flagship_share",
        "premium_index", "midrange_index", "budget_index",
        "top_5_model_share", "festive_lift", "demand_volatility",
    ]
    missing_mask = profiles[critical_cols].isnull()
    all_ok &= check("No missing critical metrics", not missing_mask.values.any(),
                     f"{missing_mask.values.sum()} missing cells")

    # --- category shares -----------------------------------------------
    share_cols = ["keypad_share", "entry_share", "budget_share", "midrange_share",
                  "upper_mid_share", "premium_share", "flagship_share"]
    share_sum = profiles[share_cols].sum(axis=1)
    all_ok &= check("Category shares sum to ~1.0 for every store",
                     np.allclose(share_sum, 1.0, atol=0.01),
                     f"min={share_sum.min():.4f}, max={share_sum.max():.4f}")
    all_ok &= check("All category shares are within [0, 1]",
                     ((profiles[share_cols] >= -1e-9) & (profiles[share_cols] <= 1 + 1e-9)).all().all())

    # --- indices consistency --------------------------------------------
    recomputed_premium = profiles["premium_share"] + profiles["flagship_share"]
    all_ok &= check("premium_index == premium_share + flagship_share",
                     np.allclose(profiles["premium_index"], recomputed_premium, atol=1e-6))
    recomputed_budget = profiles["budget_share"] + profiles["entry_share"] + profiles["keypad_share"]
    all_ok &= check("budget_index == budget_share + entry_share + keypad_share",
                     np.allclose(profiles["budget_index"], recomputed_budget, atol=1e-6))
    recomputed_mid = profiles["midrange_share"] + profiles["upper_mid_share"]
    all_ok &= check("midrange_index == midrange_share + upper_mid_share",
                     np.allclose(profiles["midrange_index"], recomputed_mid, atol=1e-6))

    # --- revenue consistency ---------------------------------------------
    recomputed_asp = np.where(profiles["total_units_sold"] > 0,
                               profiles["total_sales_value"] / profiles["total_units_sold"], 0.0)
    all_ok &= check("average_selling_price consistent with total_sales_value/total_units_sold",
                     np.allclose(profiles["average_selling_price"], recomputed_asp, atol=0.5))

    num_weeks = sales["week_number"].nunique()
    recomputed_weekly_units = profiles["total_units_sold"] / num_weeks
    all_ok &= check("average_weekly_units consistent with total_units_sold / num_weeks",
                     np.allclose(profiles["average_weekly_units"], recomputed_weekly_units, atol=1e-6))

    # cross-check total_units_sold against raw sales_history directly
    raw_totals = sales.groupby("store_id")["units_sold"].sum()
    merged_check = profiles.set_index("store_id")["total_units_sold"]
    all_ok &= check("total_units_sold in store_profiles matches raw sales_history aggregation",
                     np.allclose(raw_totals.reindex(merged_check.index), merged_check, atol=1e-6))

    # --- festive lift validity --------------------------------------------
    all_ok &= check("festive_lift is non-negative and finite for all stores",
                     np.isfinite(profiles["festive_lift"]).all() and (profiles["festive_lift"] >= 0).all())
    all_ok &= check("Chain-wide average festive_lift > 1 (festive weeks genuinely lift sales)",
                     profiles["festive_lift"].mean() > 1.0,
                     f"mean festive_lift={profiles['festive_lift'].mean():.2f}")

    # --- no impossible negatives -----------------------------------------
    numeric_cols = [c for c in profiles.columns if profiles[c].dtype in (np.float64, np.int64)
                    and c not in ("festive_lift",)]  # festive_lift already checked
    negative_mask = (profiles[numeric_cols] < -1e-9)
    all_ok &= check("No impossible negative values in numeric profile columns",
                     not negative_mask.values.any(),
                     f"{negative_mask.values.sum()} negative cells")

    # --- top_5_model_share sanity ------------------------------------------
    all_ok &= check("top_5_model_share within [0, 1]",
                     ((profiles["top_5_model_share"] >= 0) & (profiles["top_5_model_share"] <= 1)).all())

    # --- segmentation -------------------------------------------------------
    all_ok &= check("Every store has exactly one segment assigned",
                     profiles["store_segment"].notnull().all() and len(profiles) == 25)
    valid_segments = {"Premium", "Balanced", "Value"}
    all_ok &= check("All segment labels are from the expected set",
                     set(profiles["store_segment"].unique()).issubset(valid_segments),
                     f"found: {sorted(profiles['store_segment'].unique())}")

    print("\nSegment counts:")
    print(profiles["store_segment"].value_counts().to_string())

    print("\n" + "=" * 70)
    print("OVERALL RESULT:", "ALL CHECKS PASSED" if all_ok else "SOME CHECKS FAILED")
    print("=" * 70)

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
