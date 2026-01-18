import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(layout="wide", page_title="Strategy Performance Dashboard")

# =========================
# LOAD DATA
# =========================
trades = pd.read_csv("trade_log.csv", parse_dates=["entry_date", "exit_date"])
capital = pd.read_csv("capital_timeline.csv", parse_dates=["Date"])

STARTING_CAPITAL = 300000  # user input if needed

# =========================
# SIDEBAR
# =========================
st.sidebar.header("Settings")
show_pct = st.sidebar.checkbox("Show PnL in Percentage (%)", False)

# =========================
# PREP DATA
# =========================
trades["year"] = trades["exit_date"].dt.year
trades["month"] = trades["exit_date"].dt.month
trades["month_name"] = trades["exit_date"].dt.strftime("%b")

# Monthly PnL
monthly_pnl = (
    trades.groupby(["year", "month", "month_name"])["pnl"]
    .sum()
    .reset_index()
)

# Pivot table
pnl_pivot = monthly_pnl.pivot(
    index="year", columns="month_name", values="pnl"
).fillna(0)

# Ensure month order
month_order = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
pnl_pivot = pnl_pivot.reindex(columns=month_order, fill_value=0)

pnl_pivot["Total"] = pnl_pivot.sum(axis=1)

# =========================
# EQUITY CURVE
# =========================
trades = trades.sort_values("exit_date")
trades["equity"] = STARTING_CAPITAL + trades["pnl"].cumsum()

equity_df = trades[["exit_date", "equity"]].rename(columns={"exit_date": "Date"})

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
total_return_pct = (total_profit / STARTING_CAPITAL) * 100
avg_monthly = monthly_pnl["pnl"].mean()

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Profit", f"₹{total_profit:,.0f}")
col2.metric("Total Return", f"{total_return_pct:.2f}%")
col3.metric("Max Capital Used", f"₹{max_capital:,.0f}")
col4.metric("Max Drawdown", f"₹{max_dd:,.0f}")

st.divider()

# =========================
# MONTHLY & YEARLY TABLE
# =========================
st.subheader("📊 Monthly & Yearly PnL Summary")

display_table = pnl_pivot.copy()

if show_pct:
    display_table = (display_table / STARTING_CAPITAL) * 100

st.dataframe(display_table.style.format("{:.2f}"))

# =========================
# EQUITY CURVE CHART
# =========================
st.subheader("📈 Equity Curve")

fig_equity = px.line(
    equity_df,
    x="Date",
    y="equity",
    labels={"equity": "Equity (₹)"},
)

st.plotly_chart(fig_equity, use_container_width=True)

# =========================
# CAPITAL DEPLOYED CURVE
# =========================
st.subheader("💰 Capital Deployed Over Time")

fig_cap = px.line(
    capital_curve,
    x="Date",
    y="capital_deployed",
    labels={"capital_deployed": "Capital Deployed (₹)"},
)

st.plotly_chart(fig_cap, use_container_width=True)

# =========================
# YEARLY PNL
# =========================
st.subheader("📅 Yearly PnL")

yearly = trades.groupby("year")["pnl"].sum().reset_index()

fig_year = px.bar(
    yearly,
    x="year",
    y="pnl",
    labels={"pnl": "PnL (₹)", "year": "Year"},
)

st.plotly_chart(fig_year, use_container_width=True)
