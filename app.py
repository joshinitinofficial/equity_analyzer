import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# =========================
# LAKHS HELPER
# =========================
def to_lakhs(x):
    return x / 1e5

st.set_page_config(
    layout="wide",
    page_title="Strategy Performance Dashboard"
)

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

starting_capital = st.sidebar.number_input(
    "Starting Capital (₹)",
    min_value=1,
    value=300000,
    step=50000
)

show_pct = st.sidebar.checkbox(
    "Show PnL in Percentage (%)", False
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
# BASIC SANITY CHECKS
# =========================
required_trade_cols = {"entry_date", "exit_date", "pnl"}
required_cap_cols = {"Date", "capital_deployed"}

if not required_trade_cols.issubset(trades.columns):
    st.error(f"trade_log.csv missing columns: {required_trade_cols - set(trades.columns)}")
    st.stop()

if not required_cap_cols.issubset(capital.columns):
    st.error(f"capital_timeline.csv missing columns: {required_cap_cols - set(capital.columns)}")
    st.stop()

# =========================
# PREP DATA
# =========================
trades = trades.sort_values("exit_date")

trades["year"] = trades["exit_date"].dt.year
trades["month"] = trades["exit_date"].dt.month
trades["month_name"] = trades["exit_date"].dt.strftime("%b")

# =========================
# MONTHLY PNL
# =========================
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

display_table = pnl_pivot.copy()
if show_pct:
    display_table = (display_table / starting_capital) * 100

# =========================
# EQUITY CURVE (LAKHS)
# =========================
trades["equity"] = starting_capital + trades["pnl"].cumsum()
trades["equity_lakhs"] = trades["equity"].apply(to_lakhs)

equity_df = trades[["exit_date", "equity_lakhs"]].rename(
    columns={"exit_date": "Date"}
)

# =========================
# DRAWDOWN
# =========================
equity_df["peak"] = equity_df["equity"].cummax()
equity_df["drawdown"] = equity_df["equity"] - equity_df["peak"]
max_dd = equity_df["drawdown"].min()

# =========================
# CAPITAL DEPLOYED
# =========================
capital_curve = (
    capital.groupby("Date")["capital_deployed"]
    .last()
    .reset_index()
)

max_capital = capital_curve["capital_deployed"].max()

# =========================
# TOP METRICS
# =========================
total_profit = trades["pnl"].sum()
total_return_pct = (total_profit / starting_capital) * 100
avg_monthly = monthly_pnl["pnl"].mean()

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Profit", f"{total_profit / 1e5:.2f} L")
c2.metric("Total Return", f"{total_return_pct:.2f}%")
c3.metric("Max Capital Deployed", f"{max_capital / 1e5:.2f} L")
c4.metric("Max Drawdown", f"{max_dd / 1e5:.2f} L")

st.divider()

# =========================
# MONTHLY / YEARLY TABLE
# =========================
st.subheader("📅 Monthly & Yearly PnL Summary")
st.dataframe(display_table.style.format("{:.2f}"))

# =========================
# EQUITY CURVE CHART
# =========================
st.subheader("📈 Equity Curve")

fig_equity = px.line(
    equity_df,
    x="Date",
    y="equity_lakhs",
    labels={"equity_lakhs": "Equity (₹ Lakhs)"}
)

fig_equity.update_yaxes(tickformat=".1f")
st.plotly_chart(fig_equity, use_container_width=True)

# =========================
# CAPITAL DEPLOYED CURVE
# =========================
st.subheader("💰 Capital Deployed Over Time")

fig_cap = px.line(
    capital_curve,
    x="Date",
    y="capital_deployed",
    labels={"capital_deployed": "Capital Deployed (₹)"}
)

st.plotly_chart(fig_cap, use_container_width=True)

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
