"""Step 4: do the segments actually predict who comes back? (the churn-risk question)

We pretend today is 2011-09-09, score customers using only data before that date, then
check who placed at least one order in the next ~3 months (2011-09-09 to 2011-12-09,
the last day in the data). If the segments are useful, repurchase rates should differ a lot.

Output: reports/holdout_by_segment.csv, images/repurchase_by_segment.png
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from plotstyle import BLUE, INK, INK_SOFT, apply_style, clean_axes
from rfm import SEGMENT_ORDER, assign_segment, build_rfm, score_rfm
from utils import IMAGES, PROCESSED, REPORTS, save_metrics

CUTOFF = pd.Timestamp("2011-09-09")

apply_style()
sales = pd.read_csv(PROCESSED / "sales_clean.csv.gz", parse_dates=["InvoiceDate"])
returns = pd.read_csv(PROCESSED / "returns_clean.csv.gz", parse_dates=["InvoiceDate"])

# Score on the past only (build_rfm ignores anything on or after the cutoff).
past = assign_segment(score_rfm(build_rfm(sales, returns, CUTOFF)))

# What happened next: orders and net spend in the window after the cutoff.
future_sales = sales[sales["InvoiceDate"] >= CUTOFF]
future_returns = returns[returns["InvoiceDate"] >= CUTOFF]
orders_after = future_sales.groupby("CustomerID")["InvoiceNo"].nunique().rename("orders_after")
spend_after = (
    future_sales.groupby("CustomerID")["Revenue"].sum()
    .sub(future_returns.groupby("CustomerID")["ReturnValue"].sum(), fill_value=0)
    .rename("net_spend_after")
)
past = past.merge(orders_after, on="CustomerID", how="left").merge(spend_after, on="CustomerID", how="left")
past["orders_after"] = past["orders_after"].fillna(0)
past["net_spend_after"] = past["net_spend_after"].fillna(0)
past["came_back"] = past["orders_after"] > 0


def wilson_ci(successes: pd.Series, n: pd.Series, z: float = 1.96):
    """95% confidence interval for a proportion (better than +/- for small groups)."""
    p = successes / n
    centre = (p + z**2 / (2 * n)) / (1 + z**2 / n)
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / (1 + z**2 / n)
    return centre - half, centre + half


result = (
    past.groupby("segment")
    .agg(customers=("CustomerID", "count"), came_back=("came_back", "sum"),
         avg_net_spend_after=("net_spend_after", "mean"), total_net_spend_after=("net_spend_after", "sum"))
    .reindex(SEGMENT_ORDER)
)
result["repurchase_rate_pct"] = result["came_back"] / result["customers"] * 100
low, high = wilson_ci(result["came_back"], result["customers"])
result["ci_low_pct"], result["ci_high_pct"] = low * 100, high * 100
result["pct_of_future_spend"] = result["total_net_spend_after"] / result["total_net_spend_after"].sum() * 100
result = result.round(1)
result.to_csv(REPORTS / "holdout_by_segment.csv")
print(result.to_string())

overall = past["came_back"].mean() * 100
print(f"\noverall repurchase rate: {overall:.1f}% of {len(past)} customers scored at {CUTOFF.date()}")

# --- Chart ----------------------------------------------------------------------------------
plot = result.sort_values("repurchase_rate_pct")
y = np.arange(len(plot))
fig, ax = plt.subplots(figsize=(9, 4.4))
err = np.array([plot["repurchase_rate_pct"] - plot["ci_low_pct"], plot["ci_high_pct"] - plot["repurchase_rate_pct"]])
ax.barh(y, plot["repurchase_rate_pct"], height=0.5, color=BLUE, xerr=err,
        error_kw={"ecolor": INK_SOFT, "elinewidth": 1, "capsize": 3})
for yi, v, hi in zip(y, plot["repurchase_rate_pct"], plot["ci_high_pct"]):
    ax.text(hi + 1.2, yi, f"{v:.0f}%", va="center", color=INK, fontsize=9)
ax.set_yticks(y)
ax.set_yticklabels([f"{s} (n={int(n)})" for s, n in zip(plot.index, plot["customers"])])
ax.set_xlim(0, 105)
ax.set_xlabel("Customers who ordered again in the next 3 months (%), with 95% interval")
ax.set_title("Segments built in September predict who actually came back")
clean_axes(ax, grid_axis="x")
fig.tight_layout()
fig.savefig(IMAGES / "repurchase_by_segment.png", dpi=150)
plt.close(fig)

save_metrics({
    "holdout_cutoff": str(CUTOFF.date()),
    "holdout_customers": int(len(past)),
    "holdout_overall_repurchase_pct": float(overall),
    "holdout": {
        name: {
            "customers": int(row["customers"]),
            "repurchase_rate_pct": float(row["repurchase_rate_pct"]),
            "ci_low_pct": float(row["ci_low_pct"]),
            "ci_high_pct": float(row["ci_high_pct"]),
            "avg_net_spend_after": float(row["avg_net_spend_after"]),
            "pct_of_future_spend": float(row["pct_of_future_spend"]),
        }
        for name, row in result.iterrows()
    },
})
