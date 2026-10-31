"""
Project 3 - Fraud Detection Pipeline
Step 1: Extraction + Messy Data Injection

Reads the real Kaggle credit card fraud dataset (fraudTrain.csv), samples it
down to a manageable size, and deliberately injects realistic data quality
issues so the downstream cleaning module has genuine problems to solve.

Run from the project root:
    python include/extraction/generate_messy_transactions.py
"""

import random
from pathlib import Path

import numpy as np
import pandas as pd

# Reproducibility: the same "random" mess every run
random.seed(42)
np.random.seed(42)

# ---- Config ----
SAMPLE_SIZE = 10_000

# Find fraudTrain.csv anywhere inside the include/ folder, so the exact
# folder name/casing (raw, RAW, data/raw ...) does not matter.
INCLUDE_DIR = Path(__file__).resolve().parent.parent
_matches = list(INCLUDE_DIR.rglob("fraudTrain.csv"))
if not _matches:
    raise FileNotFoundError(f"Could not find fraudTrain.csv anywhere inside {INCLUDE_DIR}")
INPUT_PATH = _matches[0]
OUTPUT_PATH = INPUT_PATH.parent / "messy_transactions.csv"

NULL_RATE = 0.04
DUPLICATE_RATE = 0.02
MALFORMED_DATE_RATE = 0.05
CURRENCY_INCONSISTENCY_RATE = 0.06
OUTLIER_RATE = 0.01
MERCHANT_TYPO_RATE = 0.05


def load_and_sample(input_path: Path, n: int) -> pd.DataFrame:
    print(f"Reading {input_path} ...")
    df = pd.read_csv(input_path)
    print(f"Full dataset shape: {df.shape}")

    df_sample = df.sample(n=min(n, len(df)), random_state=42).reset_index(drop=True)

    df_sample = df_sample.rename(columns={
        "trans_num": "transaction_id",
        "trans_date_trans_time": "transaction_date",
        "merchant": "merchant_name",
        "amt": "amount",
        "cc_num": "customer_id",
        "is_fraud": "is_fraud_actual",
        "merch_lat": "merchant_lat",
        "merch_long": "merchant_long",
        "lat": "customer_lat",
        "long": "customer_long",
    })

    cols_to_keep = [
        "transaction_id", "transaction_date", "customer_id",
        "merchant_name", "category", "amount", "is_fraud_actual",
        "customer_lat", "customer_long", "merchant_lat", "merchant_long",
    ]
    return df_sample[cols_to_keep]


def inject_nulls(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    nullable_cols = ["merchant_name", "amount", "category", "customer_id"]
    n_nulls_per_col = int(len(df) * NULL_RATE)

    for col in nullable_cols:
        # object dtype lets us put NaN into any column (even integer ones)
        df[col] = df[col].astype(object)
        null_idx = np.random.choice(df.index, size=n_nulls_per_col, replace=False)
        df.loc[null_idx, col] = np.nan

    print(f"Injected nulls into {nullable_cols} (~{NULL_RATE:.0%} each)")
    return df


def inject_duplicate_transaction_ids(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    n_dupes = int(len(df) * DUPLICATE_RATE)
    dupe_rows = df.sample(n=n_dupes, random_state=1).copy()

    # Slightly different amount = a "double charge" rather than a pure copy
    dupe_rows["amount"] = dupe_rows["amount"].apply(
        lambda x: x if pd.isna(x) else round(float(x) * random.uniform(0.98, 1.02), 2)
    )

    df = pd.concat([df, dupe_rows], ignore_index=True)
    print(f"Injected {n_dupes} duplicate transaction_ids")
    return df


def inject_malformed_dates(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    n_malformed = int(len(df) * MALFORMED_DATE_RATE)
    idx = np.random.choice(df.index, size=n_malformed, replace=False)

    def scramble_date(value):
        if pd.isna(value):
            return value
        try:
            dt = pd.to_datetime(value)
        except Exception:
            return value

        variant = random.choice(["us_format", "text_month", "no_time", "slashes", "garbage"])
        if variant == "us_format":
            return dt.strftime("%m/%d/%Y %H:%M")
        elif variant == "text_month":
            return dt.strftime("%d-%b-%Y")
        elif variant == "no_time":
            return dt.strftime("%Y-%m-%d")
        elif variant == "slashes":
            return dt.strftime("%d/%m/%Y")
        return "00/00/0000"

    df["transaction_date"] = df["transaction_date"].astype(object)
    df.loc[idx, "transaction_date"] = df.loc[idx, "transaction_date"].apply(scramble_date)
    print(f"Injected {n_malformed} malformed/inconsistent date formats")
    return df


def inject_currency_inconsistencies(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    n_affected = int(len(df) * CURRENCY_INCONSISTENCY_RATE)
    idx = np.random.choice(df.index, size=n_affected, replace=False)

    def format_variant(value):
        if pd.isna(value):
            return value
        value = float(value)
        style = random.choice(["dollar_sign", "comma_thousands", "eur_suffix", "rounded_int"])
        if style == "dollar_sign":
            return f"${value:.2f}"
        elif style == "comma_thousands":
            return f"{value:,.2f}"
        elif style == "eur_suffix":
            return f"{value:.2f} EUR"
        return str(int(round(value)))

    # amount becomes a mixed text/number column on purpose:
    # this is exactly the mess the cleaning module has to fix
    df["amount"] = df["amount"].astype(object)
    df.loc[idx, "amount"] = df.loc[idx, "amount"].apply(format_variant)
    print(f"Injected {n_affected} currency formatting inconsistencies")
    return df


def inject_amount_outliers(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    n_outliers = int(len(df) * OUTLIER_RATE)
    idx = np.random.choice(df.index, size=n_outliers, replace=False)

    def make_outlier(value):
        if pd.isna(value):
            return value
        try:
            numeric_val = float(str(value).replace("$", "").replace(",", "").replace(" EUR", ""))
        except ValueError:
            return value
        return round(numeric_val * random.uniform(50, 200), 2)

    df.loc[idx, "amount"] = df.loc[idx, "amount"].apply(make_outlier)
    print(f"Injected {n_outliers} extreme outlier amounts")
    return df


def inject_merchant_typos(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    n_affected = int(len(df) * MERCHANT_TYPO_RATE)
    idx = np.random.choice(df.index, size=n_affected, replace=False)

    def mangle(name):
        if pd.isna(name):
            return name
        name = str(name)
        variant = random.choice(["extra_space", "case", "prefix_strip", "trailing_chars"])
        if variant == "extra_space":
            return "  " + name + "   "
        elif variant == "case":
            return name.upper() if random.random() > 0.5 else name.lower()
        elif variant == "prefix_strip":
            return name.replace("fraud_", "").replace("Fraud_", "")
        return name + random.choice(["!!", "..", "_2", "-x"])

    df["merchant_name"] = df["merchant_name"].astype(object)
    df.loc[idx, "merchant_name"] = df.loc[idx, "merchant_name"].apply(mangle)
    print(f"Injected {n_affected} merchant name typos/formatting issues")
    return df


def main():
    print("Starting messy data generation...")
    df = load_and_sample(INPUT_PATH, SAMPLE_SIZE)

    df = inject_nulls(df)
    df = inject_duplicate_transaction_ids(df)
    df = inject_malformed_dates(df)
    df = inject_currency_inconsistencies(df)
    df = inject_amount_outliers(df)
    df = inject_merchant_typos(df)

    df.to_csv(OUTPUT_PATH, index=False)

    print("\n--- Summary ---")
    print(f"Final row count (incl. duplicates): {len(df)}")
    print(f"Saved messy dataset to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
