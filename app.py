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

    low, high = -0.99, 3.0
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
# SIDEBAR – USER INPUTS
# =========================
st.sidebar.divider()
st.sidebar.subheader("Strategy Parameters")

INVESTMENT_PER_TRADE = st.sidebar.number_input(
    "Investment per Trade (₹)",
    min_value=1000,
    step=1000,
    value=10000
)

CHARGES_PER_TRADE = st.sidebar.number_input(
    "Charges per Trade (₹)",
    min_value=0,
    step=5,
    value=25
)

# =========================
# SIDEBAR – RETURN METRIC
# =========================
st.sidebar.divider()
return_metric = st.sidebar.radio(
    "Return Metric",
    ["XIRR", "CAGR"],
    horizontal=True
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
# NORMALIZE TRADE LOG (OLD + NEW CSVs)
# =========================
if "charges" not in trades.columns:
    trades["charges"] = CHARGES_PER_TRADE

if "holding_days" not in trades.columns:
    trades["holding_days"] = (
        trades["exit_date"] - trades["entry_date"]
    ).dt.days

if "index" not in trades.columns:
    trades["index"] = "Strategy"

for col in ["entry_price", "exit_price", "quantity", "pnl", "charges"]:
    trades[col] = pd.to_numeric(trades[col], errors="coerce")

# =========================
# NORMALIZE CAPITAL TIMELINE
# =========================
capital["capital_deployed"] = pd.to_numeric(
    capital["capital_deployed"], errors="coerce"
)

capital = capital.dropna(subset=["capital_deployed"])
capital = capital.sort_values("Date")

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
# XIRR
# =========================
cashflows = []

for _, row in trades.iterrows():
    cashflows.append((row["entry_date"], -INVESTMENT_PER_TRADE))
    cashflows.append(
        (
            row["exit_date"],
            row["quantity"] * row["exit_price"] - CHARGES_PER_TRADE
        )
    )

cashflow_df = (
    pd.DataFrame(cashflows, columns=["date", "amount"])
    .sort_values("date")
)

xirr = calculate_xirr(cashflow_df) * 100

# =========================
# CAGR
# =========================
start_capital = capital["capital_deployed"].iloc[0]
end_capital = capital["capital_deployed"].iloc[-1]

start_date = capital["Date"].iloc[0]
end_date = capital["Date"].iloc[-1]

years = (end_date - start_date).days / 365

if years > 0 and start_capital > 0:
    cagr = ((end_capital / start_capital) ** (1 / years) - 1) * 100
else:
    cagr = 0

# =========================
# DISPLAY HEADER METRICS
# =========================
c1, c2, c3, c4 = st.columns(4)
c5, c6, c7 = st.columns(3)

with c1:
    st.metric("Total Trades", total_trades)

with c2:
    st.metric("Total Charges (L)", f"{total_charges / 1e5:.2f}")

with c3:
    st.metric("Net P&L (L)", f"{net_pnl / 1e5:.2f}")

with c4:
    st.metric("Win Rate (%)", f"{win_rate:.2f}")

with c5:
    st.metric("Avg Holding Days", f"{avg_holding:.2f}")

with c6:
    st.metric("Max Capital (L)", f"{max_capital / 1e5:.2f}")

with c7:
    value = xirr if return_metric == "XIRR" else cagr
    st.metric(f"Strategy {return_metric} (%)", f"{value:.2f}")

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
# EQUITY CURVE
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

st.plotly_chart(fig_equity, use_container_width=True)

# =========================
# CAPITAL DEPLOYMENT CURVE
# =========================
capital_df = (
    capital
    .groupby("Date")
    .last()
    .reset_index()
)

capital_df["capital_lakhs"] = capital_df["capital_deployed"].apply(to_lakhs)

st.subheader("💰 Capital Deployment Curve")

fig_capital = px.line(
    capital_df,
    x="Date",
    y="capital_lakhs",
    labels={"capital_lakhs": "Capital (₹ Lakhs)"}
)

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

st.plotly_chart(fig_year, use_container_width=True)
