import streamlit as st
import pandas as pd
import plotly.express as px

# =========================
# LAKHS HELPER
# =========================
def to_lakhs(x):
    return x / 1e5

# =========================
# XIRR FUNCTION
# =========================
def calculate_xirr(cashflows):
    dates = cashflows["date"]
    amounts = cashflows["amount"]

    def npv(rate):
        return sum(
            amt / ((1 + rate) ** ((d - dates.iloc[0]).days / 365))
            for amt, d in zip(amounts, dates)
        )

    low, high = -0.99, 5.0
    for _ in range(100):
        mid = (low + high) / 2
        val = npv(mid)
        if abs(val) < 1e-6:
            return mid
        if val > 0:
            low = mid
        else:
            high = mid
    return mid

st.set_page_config(layout="wide", page_title="Strategy Performance Dashboard")
st.title("📊 Strategy Performance Dashboard")

# =========================
# SIDEBAR – FILE UPLOAD
# =========================
st.sidebar.header("Upload Backtest Files")

trade_file = st.sidebar.file_uploader(
    "Upload trade_log.csv", type=["csv"]
)

capital_file = st.sidebar.file_uploader(
    "Upload capital_timeline.csv", type=["csv"]
)

# =========================
# VALIDATION
# =========================
if trade_file is None or capital_file is None:
    st.info("⬅️ Upload both trade_log.csv and capital_timeline.csv to begin analysis.")
    st.stop()

# =========================
# LOAD DATA
# =========================
trades = pd.read_csv(
    trade_file,
    parse_dates=["entry_date", "exit_date"]
)

capital = pd.read_csv(
    capital_file,
    parse_dates=["Date"]
)

# =========================
# SANITY CHECKS
# =========================
required_trade_cols = {
    "entry_date", "exit_date", "entry_price",
    "exit_price", "quantity", "pnl",
    "charges", "holding_days"
}

required_cap_cols = {"Date", "capital_deployed"}

if not required_trade_cols.issubset(trades.columns):
    st.error(f"trade_log.csv missing columns: {required_trade_cols - set(trades.columns)}")
    st.stop()

if not required_cap_cols.issubset(capital.columns):
    st.error(f"capital_timeline.csv missing columns: {required_cap_cols - set(capital.columns)}")
    st.stop()

# =========================
# HEADER METRICS
# =========================
total_trades = len(trades)
total_charges = trades["charges"].sum()
net_pnl = trades["pnl"].sum()
win_rate = (trades["pnl"] > 0).mean() * 100
avg_holding = trades["holding_days"].mean()

max_capital = (
    capital.groupby("Date")["capital_deployed"]
    .last()
    .max()
)

# =========================
# XIRR (TRUE CASHFLOWS)
# =========================
cashflows = []

for _, row in trades.iterrows():
    invested = row["entry_price"] * row["quantity"]
    exit_value = row["exit_price"] * row["quantity"]

    cashflows.append((row["entry_date"], -invested))
    cashflows.append((row["exit_date"], exit_value))

cashflow_df = pd.DataFrame(cashflows, columns=["date", "amount"])
xirr = calculate_xirr(cashflow_df) * 100

# =========================
# DISPLAY HEADER METRICS
# =========================
c1, c2, c3, c4 = st.columns(4)
c5, c6, c7 = st.columns(3)

c1.metric("Total Trades Executed", total_trades)
c2.metric("Total Charges Paid", f"{total_charges / 1e5:.2f} L")
c3.metric("Net P&L", f"{net_pnl / 1e5:.2f} L")
c4.metric("Win Rate", f"{win_rate:.2f}%")

c5.metric("Avg Holding Days", f"{avg_holding:.2f}")
c6.metric("Max Capital Deployed", f"{max_capital / 1e5:.2f} L")
c7.metric("Strategy XIRR", f"{xirr:.2f}%")

st.divider()

# =========================
# MONTHLY / YEARLY PNL
# =========================
trades = trades.sort_values("exit_date")
trades["year"] = trades["exit_date"].dt.year
trades["month"] = trades["exit_date"].dt.month
trades["month_name"] = trades["exit_date"].dt.strftime("%b")

monthly_pnl = (
    trades.groupby(["year", "month", "month_name"])["pnl"]
    .sum()
    .reset_index()
)

month_order = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]

pnl_pivot = (
    monthly_pnl
    .pivot(index="year", columns="month_name", values="pnl")
    .reindex(columns=month_order, fill_value=0)
)

pnl_pivot["Total"] = pnl_pivot.sum(axis=1)

st.subheader("📅 Monthly & Yearly PnL Summary")
st.dataframe(pnl_pivot.style.format("{:.2f}"))

# =========================
# EQUITY CURVE (PURE PnL)
# =========================
trades["equity"] = trades["pnl"].cumsum()
trades["equity_lakhs"] = trades["equity"].apply(to_lakhs)

equity_df = trades[["exit_date", "equity_lakhs"]].rename(
    columns={"exit_date": "Date"}
)

st.subheader("📈 Equity Curve")

fig_equity = px.line(
    equity_df,
    x="Date",
    y="equity_lakhs",
    labels={"equity_lakhs": "Cumulative PnL (₹ Lakhs)"}
)

fig_equity.update_yaxes(tickformat=".1f")
st.plotly_chart(fig_equity, use_container_width=True)

# =====================================================
# 🔥 ADDED: CAPITAL DEPLOYMENT CURVE (ONLY ADDITION)
# =====================================================
capital = capital.sort_values("Date")
capital["capital_lakhs"] = capital["capital_deployed"].apply(to_lakhs)

st.subheader("💰 Capital Deployment Curve")

fig_capital = px.line(
    capital,
    x="Date",
    y="capital_lakhs",
    labels={"capital_lakhs": "Capital Deployed (₹ Lakhs)"}
)

fig_capital.update_yaxes(tickformat=".1f")
st.plotly_chart(fig_capital, use_container_width=True)

# =========================
# YEARLY PNL
# =========================
st.subheader("📊 Yearly PnL")

yearly_pnl = (
    trades.groupby("year")["pnl"]
    .sum()
    .reset_index()
)

yearly_pnl["pnl_lakhs"] = yearly_pnl["pnl"].apply(to_lakhs)

fig_year = px.bar(
    yearly_pnl,
    x="year",
    y="pnl_lakhs",
    labels={"pnl_lakhs": "PnL (₹ Lakhs)", "year": "Year"}
)

fig_year.update_yaxes(tickformat=".1f")
st.plotly_chart(fig_year, use_container_width=True)
