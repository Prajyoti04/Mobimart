"""
phase2_analysis.py
-------------------
Main entry point for Phase 2. Loads the actual Phase 1 data, runs the full
store-profiling pipeline, writes data/store_profiles.csv, and produces the
plots under reports/phase2/.

Usage:
    python3 phase2_analysis.py
"""

from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from store_profiling import (
    load_phase1_data, build_full_store_profile, CATEGORY_ORDER, CATEGORY_SHARE_COL
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports" / "phase2"

PROFILE_OUTPUT_COLS = [
    "store_id", "store_name", "city", "tier", "location_type", "store_segment",
    "total_units_sold", "total_sales_value",
    "average_weekly_units", "average_weekly_revenue", "average_selling_price",
    "keypad_share", "entry_share", "budget_share", "midrange_share",
    "upper_mid_share", "premium_share", "flagship_share",
    "premium_index", "midrange_index", "budget_index",
    "top_5_model_share", "festive_lift",
    "mean_weekly_units", "median_weekly_units", "max_weekly_units",
    "std_weekly_units", "demand_volatility",
]


def plot_category_mix(profile: pd.DataFrame, path: Path):
    example_ids = ["ST001", "ST002", "ST021"]  # premium BLR, mixed BLR, tier-3 value
    example_labels = {
        "ST001": "ST001 (Premium BLR)",
        "ST002": "ST002 (Mixed BLR)",
        "ST021": "ST021 (Tier-3 Value)",
    }
    subset = profile[profile["store_id"].isin(example_ids)].set_index("store_id")
    share_cols = list(CATEGORY_SHARE_COL.values())

    fig, ax = plt.subplots(figsize=(9, 5.5))
    bottom = np.zeros(len(example_ids))
    colors = plt.cm.viridis(np.linspace(0.1, 0.9, len(share_cols)))
    for col, color in zip(share_cols, colors):
        values = [subset.loc[sid, col] * 100 for sid in example_ids]
        ax.bar([example_labels[s] for s in example_ids], values, bottom=bottom, label=col.replace("_share", ""), color=color)
        bottom += np.array(values)

    ax.set_ylabel("Share of units sold (%)")
    ax.set_title("Category Mix Comparison: Premium vs. Mixed vs. Value Store")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_store_asp(profile: pd.DataFrame, path: Path):
    df = profile.sort_values("average_selling_price", ascending=False)
    fig, ax = plt.subplots(figsize=(11, 6))
    colors = df["store_segment"].map({"Premium": "#2b6cb0", "Balanced": "#d69e2e", "Value": "#38a169"})
    ax.bar(df["store_id"], df["average_selling_price"], color=colors)
    ax.set_ylabel("Average selling price (Rs)")
    ax.set_title("Average Selling Price by Store (color = segment)")
    ax.tick_params(axis="x", rotation=90, labelsize=7)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in ["#2b6cb0", "#d69e2e", "#38a169"]]
    ax.legend(handles, ["Premium", "Balanced", "Value"], loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_revenue(profile: pd.DataFrame, path: Path):
    df = profile.sort_values("total_sales_value", ascending=False)
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.bar(df["store_id"], df["total_sales_value"] / 1e5)
    ax.set_ylabel("Total 52-week revenue (Rs, lakhs)")
    ax.set_title("Total Revenue by Store (52-week history)")
    ax.tick_params(axis="x", rotation=90, labelsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_festive_lift(profile: pd.DataFrame, path: Path):
    df = profile.sort_values("festive_lift", ascending=False)
    fig, ax = plt.subplots(figsize=(11, 6))
    colors = df["store_segment"].map({"Premium": "#2b6cb0", "Balanced": "#d69e2e", "Value": "#38a169"})
    ax.bar(df["store_id"], df["festive_lift"], color=colors)
    ax.axhline(1.0, color="gray", linestyle="--", linewidth=1)
    ax.set_ylabel("Festive lift (festive avg weekly units / normal avg weekly units)")
    ax.set_title("Festive Sensitivity by Store")
    ax.tick_params(axis="x", rotation=90, labelsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_segments(profile: pd.DataFrame, path: Path):
    fig, ax = plt.subplots(figsize=(8, 6))
    colors = profile["store_segment"].map({"Premium": "#2b6cb0", "Balanced": "#d69e2e", "Value": "#38a169"})
    ax.scatter(profile["average_selling_price"], profile["premium_index"] * 100, c=colors, s=90, edgecolor="black")
    for _, row in profile.iterrows():
        ax.annotate(row["store_id"], (row["average_selling_price"], row["premium_index"] * 100),
                    fontsize=6, xytext=(3, 3), textcoords="offset points")
    ax.set_xlabel("Average selling price (Rs)")
    ax.set_ylabel("Premium index (%) — premium+flagship unit share")
    ax.set_title("Store Segmentation: ASP vs. Premium Index")
    handles = [plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=c, markersize=9, markeredgecolor="black")
               for c in ["#2b6cb0", "#d69e2e", "#38a169"]]
    ax.legend(handles, ["Premium", "Balanced", "Value"], loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading Phase 1 data (read-only)...")
    stores, products, sales = load_phase1_data()

    print("Running store profiling pipeline...")
    result = build_full_store_profile(stores, products, sales)
    profile = result["profile"]

    out_path = DATA_DIR / "store_profiles.csv"
    profile[PROFILE_OUTPUT_COLS].to_csv(out_path, index=False)
    print(f"  -> {out_path} ({len(profile)} rows)")

    print("Generating plots...")
    plot_category_mix(profile, REPORTS_DIR / "category_mix.png")
    plot_store_asp(profile, REPORTS_DIR / "store_asp.png")
    plot_revenue(profile, REPORTS_DIR / "store_revenue.png")
    plot_festive_lift(profile, REPORTS_DIR / "festive_lift.png")
    plot_segments(profile, REPORTS_DIR / "store_segments.png")
    print(f"  -> saved 5 plots to {REPORTS_DIR}")

    # Save supporting tables useful for the README / later phases
    result["top_affinity"].to_csv(DATA_DIR / "store_product_top_affinity.csv", index=False)
    result["festive_by_category"].to_csv(DATA_DIR / "festive_lift_by_category.csv", index=False)

    print("\nDone. Run validate_phase2.py next.")
    return result


if __name__ == "__main__":
    main()
