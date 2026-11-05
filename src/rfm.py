"""RFM logic shared by the main analysis and the holdout validation.

R = Recency   : days since the customer's last purchase (lower is better)
F = Frequency : number of distinct invoices (higher is better)
M = Monetary  : net spend in GBP, sales minus returns (higher is better)
"""
import numpy as np
import pandas as pd

SEGMENT_ORDER = [
    "Champions", "Loyal", "New / Promising", "About to Sleep",
    "At Risk", "Can't Lose", "Hibernating",
]

# Frequency has huge ties (35% of customers bought exactly once), so quintiles would
# split identical customers into different scores. Fixed bins keep ties together:
# 1 invoice, 2, 3, 4-5, 6+  ->  scores 1..5
F_BINS = [0, 1, 2, 3, 5, np.inf]


def build_rfm(sales: pd.DataFrame, returns: pd.DataFrame, snapshot: pd.Timestamp) -> pd.DataFrame:
    """One row per customer, using only activity before `snapshot`.

    Monetary is NET spend (sales minus returns). Gross spend would reward customers
    who bought and then cancelled everything: customers 16446 and 12346 each cancelled
    a single order worth GBP 168k and GBP 77k. Customers who returned 95% or more of
    what they bought (this also covers net spend <= 0) are dropped because they
    effectively never bought anything.
    """
    sales = sales[sales["InvoiceDate"] < snapshot]
    returns = returns[returns["InvoiceDate"] < snapshot]
    rfm = sales.groupby("CustomerID").agg(
        last_purchase=("InvoiceDate", "max"),
        frequency=("InvoiceNo", "nunique"),
        gross_spend=("Revenue", "sum"),
    )
    rfm["return_value"] = returns.groupby("CustomerID")["ReturnValue"].sum().reindex(rfm.index).fillna(0)
    rfm["monetary"] = rfm["gross_spend"] - rfm["return_value"]
    rfm["recency"] = (snapshot - rfm["last_purchase"]).dt.days
    keep = rfm["return_value"] < 0.95 * rfm["gross_spend"]
    return rfm[keep].reset_index()


def score_rfm(rfm: pd.DataFrame) -> pd.DataFrame:
    """Add 1-5 scores (5 = best). R and M use quintiles, F uses the fixed bins above."""
    rfm = rfm.copy()
    rfm["R"] = pd.qcut(rfm["recency"], 5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["F"] = pd.cut(rfm["frequency"], bins=F_BINS, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["M"] = pd.qcut(rfm["monetary"], 5, labels=[1, 2, 3, 4, 5]).astype(int)
    return rfm


def assign_segment(rfm: pd.DataFrame) -> pd.DataFrame:
    """Map R/F/M scores to named segments. Rules are checked top to bottom."""
    r, f, m = rfm["R"], rfm["F"], rfm["M"]
    rules = [
        (r >= 4) & (f >= 4),             # bought recently and often
        (r <= 2) & (f >= 4) & (m >= 4),  # big, frequent buyers who went quiet
        (r >= 3) & (f >= 3),             # solid regulars
        (r >= 4) & (f <= 2),             # recent but few orders so far
        (r <= 2) & (f >= 3),             # used to buy regularly, now quiet
        (r == 3) & (f <= 2),             # middling recency, few orders
    ]
    names = ["Champions", "Can't Lose", "Loyal", "New / Promising", "At Risk", "About to Sleep"]
    rfm = rfm.copy()
    rfm["segment"] = np.select(rules, names, default="Hibernating")
    return rfm
