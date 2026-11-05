"""Step 2: exploratory analysis of the cleaned sales.

Output: images/monthly_revenue.png, reports/top_products.csv, headline numbers in key_metrics.json
"""
import matplotlib.pyplot as plt
import pandas as pd

from plotstyle import BLUE, INK_SOFT, apply_style, clean_axes
from utils import IMAGES, PROCESSED, REPORTS, save_metrics

apply_style()
sales = pd.read_csv(PROCESSED / "sales_clean.csv.gz", parse_dates=["InvoiceDate"])
returns = pd.read_csv(PROCESSED / "returns_clean.csv.gz", parse_dates=["InvoiceDate"])

# --- Revenue by month -------------------------------------------------------------
# Net sales = sales minus returns, so a cancelled order does not count as revenue.
monthly = (
    sales.groupby(sales["InvoiceDate"].dt.to_period("M"))["Revenue"].sum()
    .sub(returns.groupby(returns["InvoiceDate"].dt.to_period("M"))["ReturnValue"].sum(), fill_value=0)
)
peak_month = monthly.idxmax()
last_month = monthly.index[-1]  # December 2011 only runs to the 9th

fig, ax = plt.subplots(figsize=(9, 4.2))
colors = [BLUE] * len(monthly)
bars = ax.bar(monthly.index.astype(str), monthly.values / 1000, color=colors, width=0.65)
bars[-1].set_alpha(0.45)  # partial month: visibly lighter
bars[-1].set_hatch("//")
ax.set_ylabel("Net sales (GBP thousands)")
ax.set_title("Net sales peak in November 2011; December 2011 covers only 9 days")
ax.annotate(f"{peak_month}: £{monthly.max() / 1000:,.0f}k", (list(monthly.index).index(peak_month), monthly.max() / 1000),
            textcoords="offset points", xytext=(0, 6), ha="center", color=INK_SOFT, fontsize=9)
plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
clean_axes(ax)
fig.tight_layout()
fig.savefig(IMAGES / "monthly_revenue.png", dpi=150)
plt.close(fig)

# --- Headline numbers (all net of returns) --------------------------------------------------
per_customer = sales.groupby("CustomerID").agg(revenue=("Revenue", "sum"), invoices=("InvoiceNo", "nunique"))
per_customer["revenue"] -= returns.groupby("CustomerID")["ReturnValue"].sum().reindex(per_customer.index).fillna(0)
per_customer = per_customer.sort_values("revenue", ascending=False)
top20_n = int(round(len(per_customer) * 0.2))
top20_share = per_customer["revenue"].head(top20_n).sum() / per_customer["revenue"].sum()

by_country = sales.groupby("Country")["Revenue"].sum().sub(returns.groupby("Country")["ReturnValue"].sum(), fill_value=0)
uk_share = by_country["United Kingdom"] / by_country.sum()
repeat_share = (per_customer["invoices"] >= 2).mean()
return_rate = returns["ReturnValue"].sum() / sales["Revenue"].sum()
net_sales = sales["Revenue"].sum() - returns["ReturnValue"].sum()

by_product = sales.groupby("StockCode")["Revenue"].sum().sub(returns.groupby("StockCode")["ReturnValue"].sum(), fill_value=0)
units = sales.groupby("StockCode")["Quantity"].sum().sub(returns.groupby("StockCode")["Quantity"].sum().abs(), fill_value=0)
names = sales.groupby("StockCode")["Description"].agg(lambda s: s.mode().iloc[0])
top_products = (
    pd.DataFrame({"description": names, "net_revenue": by_product, "net_units": units})
    .dropna(subset=["description"])
    .sort_values("net_revenue", ascending=False)
    .head(10)
    .round(1)
    .reset_index()
)
top_products.to_csv(REPORTS / "top_products.csv", index=False)

save_metrics({
    "net_sales_total": float(net_sales),
    "peak_month": str(peak_month),
    "peak_month_net_sales": float(monthly.max()),
    "top20pct_customer_net_revenue_share": float(top20_share),
    "uk_net_revenue_share": float(uk_share),
    "repeat_customer_share": float(repeat_share),
    "return_value_pct_of_sales": float(return_rate),
    "median_orders_per_customer": float(per_customer["invoices"].median()),
})
print(f"net sales GBP {net_sales:,.0f}; peak month {peak_month}: GBP {monthly.max():,.0f}")
print(f"top 20% of customers = {top20_share:.1%} of net revenue")
print(f"UK share = {uk_share:.1%}; repeat customers = {repeat_share:.1%}; returns = {return_rate:.1%} of gross sales")
