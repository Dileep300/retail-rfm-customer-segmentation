"""Step 1: clean the raw transactions and log every decision.

Input : data/raw/online_retail.xlsx   (UCI Online Retail, 541,909 rows)
Output: data/processed/sales_clean.csv.gz     valid purchases with a known customer
        data/processed/returns_clean.csv.gz   cancelled / returned lines (kept separate)
        reports/cleaning_log.csv              rows removed at each step
"""
import pandas as pd

from utils import METRICS_FILE, PROCESSED, RAW_FILE, REPORTS, save_metrics

# Stock codes that are fees, postage or manual entries, not products customers chose.
NON_PRODUCT_CODES = {
    "POST", "DOT", "M", "m", "C2", "D", "S",
    "BANK CHARGES", "AMAZONFEE", "CRUK", "B", "PADS",
}

METRICS_FILE.unlink(missing_ok=True)  # start fresh so no stale numbers survive a re-run
df = pd.read_excel(RAW_FILE, sheet_name="Online Retail", dtype={"InvoiceNo": str, "StockCode": str})
log = [("raw rows", len(df), 0)]


def record(step: str, before: int, after: int) -> None:
    log.append((step, after, before - after))


# 1. Three "A" invoices are bad-debt accounting adjustments, not sales.
before = len(df)
df = df[~df["InvoiceNo"].str.startswith("A")]
record("drop bad-debt adjustment invoices (InvoiceNo starts with A)", before, len(df))

# 2. Invoices starting with "C" are cancellations/returns. Keep them apart so we can
#    report return rates later instead of silently deleting them.
is_return = df["InvoiceNo"].str.startswith("C")
returns = df[is_return].copy()
sales = df[~is_return].copy()
log.append(("split off cancellation lines (kept in returns file)", len(sales), len(returns)))

# 3. RFM is per customer, so rows without a CustomerID cannot be used.
before = len(sales)
sales = sales.dropna(subset=["CustomerID"])
record("drop rows with no CustomerID", before, len(sales))

# 4. Exact duplicate lines (same invoice, product, quantity, time, price, customer).
before = len(sales)
sales = sales.drop_duplicates()
record("drop exact duplicate rows", before, len(sales))

# 5. Zero or negative quantity / price are stock write-offs and notes ("damaged", "?").
before = len(sales)
sales = sales[(sales["Quantity"] > 0) & (sales["UnitPrice"] > 0)]
record("drop Quantity <= 0 or UnitPrice <= 0", before, len(sales))

# 6. Postage, fees, discounts and manual entries are not product purchases.
before = len(sales)
sales = sales[~sales["StockCode"].isin(NON_PRODUCT_CODES)]
record("drop non-product stock codes (postage, fees, manual entries)", before, len(sales))

# Final tidy-up on the sales table.
sales["CustomerID"] = sales["CustomerID"].astype(int)
sales["Revenue"] = (sales["Quantity"] * sales["UnitPrice"]).round(2)
sales["InvoiceDate"] = pd.to_datetime(sales["InvoiceDate"])

# Returns table: same customer and product filters, value stored as a positive number.
returns = returns.dropna(subset=["CustomerID"])
returns = returns[~returns["StockCode"].isin(NON_PRODUCT_CODES)]
returns["CustomerID"] = returns["CustomerID"].astype(int)
returns["ReturnValue"] = (returns["Quantity"].abs() * returns["UnitPrice"]).round(2)

sales.to_csv(PROCESSED / "sales_clean.csv.gz", index=False)
returns.to_csv(PROCESSED / "returns_clean.csv.gz", index=False)

log_df = pd.DataFrame(log, columns=["step", "rows_remaining", "rows_removed"])
log_df.to_csv(REPORTS / "cleaning_log.csv", index=False)
print(log_df.to_string(index=False))

save_metrics({
    "raw_rows": int(log[0][1]),
    "clean_rows": int(len(sales)),
    "clean_customers": int(sales["CustomerID"].nunique()),
    "clean_invoices": int(sales["InvoiceNo"].nunique()),
    "rows_dropped_no_customer": int(log_df.loc[log_df.step == "drop rows with no CustomerID", "rows_removed"].iloc[0]),
    "rows_dropped_duplicates": int(log_df.loc[log_df.step == "drop exact duplicate rows", "rows_removed"].iloc[0]),
    "return_lines": int(len(returns)),
    "first_date": str(sales["InvoiceDate"].min().date()),
    "last_date": str(sales["InvoiceDate"].max().date()),
    "gross_sales_total": float(sales["Revenue"].sum()),
})
