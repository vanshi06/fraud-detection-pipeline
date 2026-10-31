import pandas as pd

# ---------------------------------------------------
# 1. LOAD THE DATA
# ---------------------------------------------------
df = pd.read_csv(
    "include/RAW/messy_transactions.csv",
    dtype={"customer_id": str, "transaction_id": str}
)

print("Rows loaded:", len(df))

# ---------------------------------------------------
# 2. LOOK AT THE PROBLEMS BEFORE CLEANING
# ---------------------------------------------------
print("\nNulls per column (before):")
print(df.isna().sum())

print("\nDuplicate transaction_ids:", df.duplicated(subset="transaction_id").sum())

# ---------------------------------------------------
# 3. REMOVE DUPLICATE TRANSACTION IDS
# ---------------------------------------------------
rows_before_dedup = len(df)
df = df.drop_duplicates(subset="transaction_id", keep="first")
print("\nRows after removing duplicates:", len(df))

# ---------------------------------------------------
# 4. CLEAN THE amount COLUMN
#    remove $ , and EUR, then turn it into real numbers
# ---------------------------------------------------
df["amount"] = df["amount"].astype(str)
df["amount"] = df["amount"].str.replace("$", "", regex=False)
df["amount"] = df["amount"].str.replace(",", "", regex=False)
df["amount"] = df["amount"].str.replace(" EUR", "", regex=False)
df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

print("\namount nulls after cleaning:", df["amount"].isna().sum())
print(df["amount"].describe())

# ---------------------------------------------------
# 5. CLEAN THE merchant_name COLUMN
#    remove extra spaces, make lowercase, remove "fraud_" prefix
# ---------------------------------------------------
df["merchant_name"] = df["merchant_name"].str.strip()
df["merchant_name"] = df["merchant_name"].str.lower()
df["merchant_name"] = df["merchant_name"].str.replace("fraud_", "", regex=False)

print("\nmerchant_name sample:")
print(df["merchant_name"].head())

# ---------------------------------------------------
# 6. CLEAN THE DATES
#    some dates are in different formats, turn them all into real dates
# ---------------------------------------------------
raw_dates = df["transaction_date"].astype(str)

d1 = pd.to_datetime(raw_dates, format="%Y-%m-%d %H:%M:%S", errors="coerce")  # 2019-03-04 01:34:16
d2 = pd.to_datetime(raw_dates, format="%Y-%m-%d", errors="coerce")           # 2019-03-04
d3 = pd.to_datetime(raw_dates, format="%m/%d/%Y %H:%M", errors="coerce")     # 03/04/2019 01:34 (US style, has a time)
d4 = pd.to_datetime(raw_dates, format="%d-%b-%Y", errors="coerce")           # 04-Mar-2019
d5 = pd.to_datetime(raw_dates, format="%d/%m/%Y", errors="coerce")           # 04/03/2019 (day first, no time)

# take the first format that worked for each row
df["transaction_date"] = d1.fillna(d2).fillna(d3).fillna(d4).fillna(d5)

print("\nDates that could not be read:", df["transaction_date"].isna().sum())
print("Earliest date:", df["transaction_date"].min())
print("Latest date:  ", df["transaction_date"].max())

# ---------------------------------------------------
# 7. FILL MISSING category WITH "unknown"
# ---------------------------------------------------
df["category"] = df["category"].fillna("unknown")

# ---------------------------------------------------
# 8. FLAG (NOT DELETE) VERY LARGE AMOUNTS AS OUTLIERS
# ---------------------------------------------------
q1 = df["amount"].quantile(0.25)
q3 = df["amount"].quantile(0.75)
iqr = q3 - q1
upper_limit = q3 + 1.5 * iqr

df["is_outlier"] = df["amount"] > upper_limit
print("\nOutlier upper limit:", upper_limit)
print("Number of outliers flagged:", df["is_outlier"].sum())

# ---------------------------------------------------
# 9. SPLIT INTO CLEAN ROWS AND QUARANTINE ROWS
#    a row goes to quarantine if amount, customer_id or date is still missing
# ---------------------------------------------------
bad_rows = df["amount"].isna() | df["customer_id"].isna() | df["transaction_date"].isna()

quarantine_df = df[bad_rows]
clean_df = df[~bad_rows]

print("\nRows quarantined:", len(quarantine_df))
print("Rows clean:", len(clean_df))

# ---------------------------------------------------
# 10. CHECK THE ROW COUNTS ADD UP
# ---------------------------------------------------
rows_removed_as_duplicates = rows_before_dedup - len(df)
total_check = len(clean_df) + len(quarantine_df) + rows_removed_as_duplicates
print("\nRows in originally:", rows_before_dedup)
print("clean + quarantine + duplicates =", total_check)

# ---------------------------------------------------
# 11. SAVE THE RESULTS
# ---------------------------------------------------
clean_df.to_csv("include/RAW/clean_transactions.csv", index=False)
quarantine_df.to_csv("include/RAW/quarantine_transactions.csv", index=False)

print("\nSaved clean_transactions.csv and quarantine_transactions.csv")
