"""Step 3: score every customer on RFM and group them into segments.

"Today" is the day after the last transaction in the data (2011-12-10).
Output: data/processed/rfm_customers.csv, reports/segment_summary.csv, images/segment_share.png
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from plotstyle import BLUE, INK, INK_SOFT, ORANGE, apply_style, clean_axes
from rfm import SEGMENT_ORDER, assign_segment, build_rfm, score_rfm
from utils import IMAGES, PROCESSED, REPORTS, save_metrics

apply_style()
sales = pd.read_csv(PROCESSED / "sales_clean.csv.gz", parse_dates=["InvoiceDate"])
returns = pd.read_csv(PROCESSED / "returns_clean.csv.gz", parse_dates=["InvoiceDate"])

snapshot = sales["InvoiceDate"].max().normalize() + pd.Timedelta(days=1)
rfm = assign_segment(score_rfm(build_rfm(sales, returns, snapshot)))
rfm.drop(columns=["last_purchase"]).to_csv(PROCESSED / "rfm_customers.csv", index=False)
customers_dropped_net_zero = int(sales["CustomerID"].nunique() - len(rfm))

summary = (
    rfm.groupby("segment")
    .agg(
        customers=("CustomerID", "count"),
        revenue=("monetary", "sum"),
        avg_recency_days=("recency", "mean"),
        avg_orders=("frequency", "mean"),
        avg_spend=("monetary", "mean"),
        total_orders=("frequency", "sum"),
        gross_spend=("gross_spend", "sum"),
        return_value=("return_value", "sum"),
    )
    .reindex(SEGMENT_ORDER)
)
summary["pct_customers"] = summary["customers"] / summary["customers"].sum() * 100
summary["pct_revenue"] = summary["revenue"] / summary["revenue"].sum() * 100
summary["avg_order_value"] = summary["revenue"] / summary["total_orders"]
summary["returns_pct_of_sales"] = summary["return_value"] / summary["gross_spend"] * 100
summary = summary.drop(columns=["total_orders", "return_value", "gross_spend"]).round(1)
summary.to_csv(REPORTS / "segment_summary.csv")
print(summary.to_string())

# --- Chart: share of customers vs share of revenue, by segment ----------------------------
plot = summary.sort_values("pct_revenue")
y = np.arange(len(plot))
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.barh(y + 0.19, plot["pct_customers"], height=0.36, color=BLUE, label="% of customers")
ax.barh(y - 0.19, plot["pct_revenue"], height=0.36, color=ORANGE, label="% of net revenue")
for yi, v in zip(y, plot["pct_revenue"]):
    ax.text(v + 0.6, yi - 0.19, f"{v:.0f}%", va="center", color=INK, fontsize=9)
ax.set_yticks(y)
ax.set_yticklabels(plot.index)
ax.set_xlabel("Share of total (%)")
ax.set_title("Champions are a minority of customers but most of the revenue")
ax.legend(frameon=False, loc="lower right")
clean_axes(ax, grid_axis="x")
fig.tight_layout()
fig.savefig(IMAGES / "segment_share.png", dpi=150)
plt.close(fig)

save_metrics({
    "snapshot_date": str(snapshot.date()),
    "customers_scored": int(len(rfm)),
    "customers_dropped_returned_95pct_or_more": customers_dropped_net_zero,
    "net_revenue_scored": float(rfm["monetary"].sum()),
    "segments": {
        name: {
            "customers": int(row["customers"]),
            "pct_customers": float(row["pct_customers"]),
            "pct_revenue": float(row["pct_revenue"]),
            "avg_recency_days": float(row["avg_recency_days"]),
            "avg_orders": float(row["avg_orders"]),
            "avg_spend": float(row["avg_spend"]),
            "returns_pct_of_sales": float(row["returns_pct_of_sales"]),
        }
        for name, row in summary.iterrows()
    },
})
