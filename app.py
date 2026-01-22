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

st.markdown("""
<style>
.metric-card {
    background: #0b1220;
    border-radius: 10px;
    padding: 12px 14px;
    text-align: center;
    border: 1px solid #1f2937;
    min-height: 90px;
}

.metric-title {
    font-size: 13px;
    color: #9ca3af;
    margin-bottom: 4px;
}

.metric-value {
    font-size: 22px;
    font-weight: 700;
    line-height: 1.2;
}

.green { color: #22c55e; }
.blue { color: #3b82f6; }
.red { color: #ef4444; }
.yellow { color: #eab308; }
.white { color: #f9fafb; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
div[data-testid="column"] {
    margin-bottom: -4px;   
    margin-top: 8px;       
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
div[data-testid="stHorizontalBlock"] {
    gap: 8px !important;
    margin-bottom: 8px !important;
}
</style>
""", unsafe_allow_html=True)


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
# SIDEBAR – USER INPUTS (NEW)
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
# ✅ XIRR (USER INPUT DRIVEN – EXACT main.py LOGIC)
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
# DISPLAY HEADER METRICS
# =========================
c1, c2, c3, c4 = st.columns(4)
c5, c6, c7 = st.columns(3)

with c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Total Trades</div>
        <div class="metric-value white">{total_trades}</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Total Charges</div>
        <div class="metric-value red">{total_charges / 1e5:.2f} L</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Net P&L</div>
        <div class="metric-value green">{net_pnl / 1e5:.2f} L</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Win Rate</div>
        <div class="metric-value yellow">{win_rate:.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

with c5:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Avg Holding Days</div>
        <div class="metric-value white">{avg_holding:.2f}</div>
    </div>
    """, unsafe_allow_html=True)

with c6:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Max Capital Deployed</div>
        <div class="metric-value blue">{max_capital / 1e5:.2f} L</div>
    </div>
    """, unsafe_allow_html=True)

with c7:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Strategy XIRR</div>
        <div class="metric-value green">{xirr:.2f}%</div>
    </div>
    """, unsafe_allow_html=True)


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

fig_equity.update_yaxes(tickformat=".1f")
st.plotly_chart(fig_equity, width="stretch")

# =========================
# CAPITAL DEPLOYMENT CURVE (MATCH main.py)
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
    labels={"capital_lakhs": "Capital Deployed (₹ Lakhs)"}
)

fig_capital.update_traces(
    fill="tozeroy",                      
    line=dict(width=2, color="#7dd3fc"), 
    fillcolor="rgba(125, 211, 252, 0.35)" 
)

fig_capital.update_layout(
    plot_bgcolor="#020617",
    paper_bgcolor="#020617",
    font=dict(color="#e5e7eb"),
    xaxis=dict(showgrid=False),
    yaxis=dict(showgrid=True, gridcolor="#1f2937")
)

fig_capital.update_yaxes(tickformat=".1f")

st.plotly_chart(fig_capital, width="stretch")



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
st.plotly_chart(fig_year, width="stretch")
