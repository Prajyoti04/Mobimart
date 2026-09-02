"""
data_generator.py
------------------
Main entry point for MobiMart Phase 1: generates stores.csv, products.csv,
and sales_history.csv into the ../data/ directory.

Usage:
    python3 data_generator.py
"""

from pathlib import Path
from datetime import date

from stores_gen import generate_stores
from products_gen import generate_products
from sales_gen import generate_sales_history

SEED = 42
START_DATE = date(2024, 9, 2)  # Monday - week 1 of the 52-week history

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("Generating store master data...")
    stores_df = generate_stores(seed=SEED)
    stores_path = DATA_DIR / "stores.csv"
    stores_df.to_csv(stores_path, index=False)
    print(f"  -> {stores_path} ({len(stores_df)} rows)")

    print("Generating product master data...")
    products_df = generate_products(seed=SEED, start_date=START_DATE)
    products_path = DATA_DIR / "products.csv"
    # Keep a clean, assignment-aligned column order for the CSV, plus the
    # extra lifecycle-shape fields used internally by the sales generator.
    col_order = [
        "model_id", "brand", "model_name", "category", "price",
        "launch_week", "launch_date", "lifecycle_stage", "successor_model_id",
        "peak_week_offset", "decline_rate",
    ]
    products_df[col_order].to_csv(products_path, index=False)
    print(f"  -> {products_path} ({len(products_df)} rows)")

    print("Generating 52 weeks of sales history (this uses stores.csv x products.csv x 52 weeks)...")
    sales_df = generate_sales_history(stores_df, products_df, start_date=START_DATE, seed=SEED)
    sales_path = DATA_DIR / "sales_history.csv"
    sales_df.to_csv(sales_path, index=False)
    print(f"  -> {sales_path} ({len(sales_df)} rows)")

    print("\nDone. Run validate_data.py next to check data quality.")


if __name__ == "__main__":
    main()
