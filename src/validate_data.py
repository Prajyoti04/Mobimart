"""
validate_data.py
-----------------
Validates the generated MobiMart Phase 1 dataset against the requirements
in the assignment. Prints a report and returns a non-zero exit code if any
hard check fails.

Run:
    python3 validate_data.py
"""

from pathlib import Path
import sys
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

FESTIVE_WEEK_NUMBERS = {6, 9}  # must match sales_gen.FESTIVE_WEEKS


def load_data():
    stores = pd.read_csv(DATA_DIR / "stores.csv")
    products = pd.read_csv(DATA_DIR / "products.csv")
    sales = pd.read_csv(DATA_DIR / "sales_history.csv", parse_dates=["week_start"])
    return stores, products, sales


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}" + (f" — {detail}" if detail else ""))
    return condition


def main():
    stores, products, sales = load_data()
    all_ok = True

    print("=" * 70)
    print("MOBIMART PHASE 1 — DATA VALIDATION REPORT")
    print("=" * 70)

    # --- 1. Store count -----------------------------------------------
    all_ok &= check("Store count == 25", len(stores) == 25, f"actual={len(stores)}")
    tier1_count = (stores["tier"] == "Tier 1").sum()
    all_ok &= check("Bangalore (Tier 1) store count == 8", tier1_count == 8, f"actual={tier1_count}")

    # --- 2. Product count -----------------------------------------------
    all_ok &= check("Product count ~= 60", 55 <= len(products) <= 65, f"actual={len(products)}")

    # --- 3. Historical period --------------------------------------------
    num_weeks = sales["week_number"].nunique()
    all_ok &= check("Historical period == 52 weeks", num_weeks == 52, f"actual={num_weeks}")

    # --- 4. Price range ----------------------------------------------------
    pmin, pmax = products["price"].min(), products["price"].max()
    all_ok &= check(
        "Price range within approx Rs 6,000 - Rs 1,50,000",
        pmin >= 5900 and pmax <= 150100,
        f"actual range = Rs {pmin:,.0f} - Rs {pmax:,.0f}"
    )

    # --- 5. Store differentiation -------------------------------------------
    merged = sales.merge(products[["model_id", "category", "price"]], on="model_id")
    merged = merged.merge(stores[["store_id", "tier", "location_type"]], on="store_id")

    def category_group(cat):
        if cat in ("Flagship", "Premium"):
            return "Premium+Flagship"
        if cat in ("Upper-mid", "Mid-range"):
            return "Mid-range"
        return "Budget/Entry/Keypad"

    merged["cat_group"] = merged["category"].apply(category_group)
    tier_mix = merged.groupby(["tier", "cat_group"])["units_sold"].sum().unstack(fill_value=0)
    tier_mix_share = tier_mix.div(tier_mix.sum(axis=1), axis=0)
    print("\nUnit-share by tier and category group:")
    print((tier_mix_share * 100).round(1).astype(str) + "%")

    premium_share_t1 = tier_mix_share.loc["Tier 1", "Premium+Flagship"] if "Tier 1" in tier_mix_share.index else 0
    premium_share_t3 = tier_mix_share.loc["Tier 3", "Premium+Flagship"] if "Tier 3" in tier_mix_share.index else 0
    all_ok &= check(
        "Tier 1 stores have materially higher premium/flagship share than Tier 3",
        premium_share_t1 > premium_share_t3 * 1.3,
        f"Tier1={premium_share_t1:.1%} vs Tier3={premium_share_t3:.1%}"
    )

    budget_share_t1 = tier_mix_share.loc["Tier 1", "Budget/Entry/Keypad"] if "Tier 1" in tier_mix_share.index else 0
    budget_share_t3 = tier_mix_share.loc["Tier 3", "Budget/Entry/Keypad"] if "Tier 3" in tier_mix_share.index else 0
    all_ok &= check(
        "Tier 3 stores have materially higher budget/entry/keypad share than Tier 1",
        budget_share_t3 > budget_share_t1 * 1.2,
        f"Tier3={budget_share_t3:.1%} vs Tier1={budget_share_t1:.1%}"
    )

    # --- 6. Festive spike ----------------------------------------------------
    weekly_units = sales.groupby("week_number")["units_sold"].sum()
    non_festive_avg = weekly_units[~weekly_units.index.isin(FESTIVE_WEEK_NUMBERS)].mean()
    festive_avg = weekly_units[weekly_units.index.isin(FESTIVE_WEEK_NUMBERS)].mean()
    festive_ratio = festive_avg / non_festive_avg
    print(f"\nAvg weekly units — non-festive: {non_festive_avg:,.1f} | festive weeks: {festive_avg:,.1f} "
          f"(ratio {festive_ratio:.2f}x)")
    all_ok &= check(
        "Festive weeks show materially higher sales than normal weeks (>=1.8x)",
        festive_ratio >= 1.8,
        f"ratio={festive_ratio:.2f}x"
    )

    # --- 7. Cannibalization ---------------------------------------------------
    print("\nCannibalization evidence (predecessor vs successor, 6wk windows around successor launch):")
    lineage_pairs = products.dropna(subset=["successor_model_id"])[["model_id", "successor_model_id"]]
    cannibal_examples = []
    for _, row in lineage_pairs.iterrows():
        pred_id, succ_id = row["model_id"], row["successor_model_id"]
        succ_launch_week = products.loc[products["model_id"] == succ_id, "launch_week"].values[0]
        if succ_launch_week < 7 or succ_launch_week > 46:
            continue  # need room on both sides within the 52-week window
        pred_sales = sales[sales["model_id"] == pred_id]
        before = pred_sales[(pred_sales["week_number"] >= succ_launch_week - 6) &
                             (pred_sales["week_number"] < succ_launch_week)]["units_sold"].sum()
        after = pred_sales[(pred_sales["week_number"] >= succ_launch_week) &
                            (pred_sales["week_number"] < succ_launch_week + 6)]["units_sold"].sum()
        if before > 0:
            pct_change = (after - before) / before * 100
            cannibal_examples.append((pred_id, succ_id, succ_launch_week, before, after, pct_change))

    cannibal_df = pd.DataFrame(cannibal_examples, columns=[
        "predecessor", "successor", "succ_launch_week", "units_before", "units_after", "pct_change"
    ]).sort_values("pct_change")
    print(cannibal_df.head(10).to_string(index=False))

    declined_count = (cannibal_df["pct_change"] < 0).sum()
    total_examinable = len(cannibal_df)
    if total_examinable > 0:
        avg_decline = cannibal_df.loc[cannibal_df["pct_change"] < 0, "pct_change"].mean()
    else:
        avg_decline = float("nan")
    all_ok &= check(
        "Majority of examinable predecessor models decline after successor launch",
        total_examinable > 0 and declined_count / total_examinable >= 0.6,
        f"{declined_count}/{total_examinable} declined, avg decline where declined = {avg_decline:.1f}%"
    )

    # --- 8. Data integrity -----------------------------------------------------
    all_ok &= check("No negative units_sold", (sales["units_sold"] >= 0).all())
    all_ok &= check("No fractional units_sold", (sales["units_sold"] == sales["units_sold"].astype(int)).all())
    all_ok &= check("No invalid store_id references", sales["store_id"].isin(stores["store_id"]).all())
    all_ok &= check("No invalid model_id references", sales["model_id"].isin(products["model_id"]).all())
    all_ok &= check("No missing critical values in sales_history",
                     not sales[["week_start", "store_id", "model_id", "units_sold", "sales_value"]].isnull().values.any())

    price_lookup = products.set_index("model_id")["price"]
    expected_value = sales["model_id"].map(price_lookup) * sales["units_sold"]
    value_mismatch = (sales["sales_value"] - expected_value).abs() > 0.01
    all_ok &= check("sales_value == units_sold x price for all rows", not value_mismatch.any(),
                     f"{value_mismatch.sum()} mismatched rows")

    all_ok &= check("No duplicate (store_id, model_id, week_number) rows",
                     not sales.duplicated(subset=["store_id", "model_id", "week_number"]).any())

    expected_rows = len(stores) * len(products) * sales["week_number"].nunique()
    all_ok &= check("Row count == stores x products x weeks", len(sales) == expected_rows,
                     f"actual={len(sales)}, expected={expected_rows}")

    print("\n" + "=" * 70)
    print("OVERALL RESULT:", "ALL CHECKS PASSED" if all_ok else "SOME CHECKS FAILED")
    print("=" * 70)

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
