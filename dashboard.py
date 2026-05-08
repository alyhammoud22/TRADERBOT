import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

from bot.database.db import get_trades, init_db
from bot.utils.mt5_data import get_rates, get_positions, get_account
from bot.mt5_connector import connect, get_price
from bot.execution.trader import close_all_positions
from bot.utils.config import STRATEGY, SYMBOL

# =============================================================================
# PAGE CONFIG — must be the very first Streamlit call (fixes StreamlitAPIException)
# =============================================================================
st.set_page_config(
    page_title="XAUUSD Pro Bot",
    layout="wide",
    page_icon="🚀",
)

# Auto-refresh every 5 seconds
st_autorefresh(interval=5000, key="autorefresh")

# =============================================================================
# ONE-TIME SESSION INITIALISATION
# FIX: init_db() and connect() were called on every 5s refresh — now run once.
# =============================================================================
if "db_ready" not in st.session_state:
    init_db()
    st.session_state.db_ready = True

if "mt5_connected" not in st.session_state:
    st.session_state.mt5_connected = connect()

# =============================================================================
# SIDEBAR — read-only config display
# FIX: removed editable lot/sl/tp inputs that were never passed to send_order().
#      Dashboard is READ-ONLY. To change settings, edit bot/utils/config.py.
# =============================================================================
with st.sidebar:
    st.header("⚙️ Bot Configuration")
    st.info("ℹ️ This panel is **read-only**. Edit `bot/utils/config.py` and restart the bot to change settings.")
    st.write(f"**Symbol:** `{SYMBOL}`")
    st.write(f"**Strategy:** `{STRATEGY}`")
    st.write("**Lot:** `0.01` (fixed)")
    st.write("**SL:** `300 pts`")
    st.write("**TP:** `600 pts`")
    st.write("**Cooldown:** `300 s`")
    st.write("**Max Positions:** `1`")
    st.write("**Drawdown Limit:** `5%`")

# =============================================================================
# HEADER & CONNECTION STATUS
# =============================================================================
st.title("🚀 XAUUSD Pro Trading Bot — Dashboard")

connected = st.session_state.mt5_connected
if connected:
    st.caption("🟢 **MT5 Connected** | Bot runs independently via `main.py` | Dashboard is **read-only**")
else:
    st.caption("🔴 **MT5 Disconnected** | Dashboard is **read-only**")

# =============================================================================
# EMERGENCY CLOSE — the only action the dashboard may take on MT5
# =============================================================================
st.subheader("🚨 Emergency Control")
col_btn, col_info = st.columns([1, 4])
with col_btn:
    if st.button("❌ Close All Trades", type="primary"):
        close_all_positions()
        st.success("Close-all orders sent to MT5.")
with col_info:
    st.warning("Immediately sends market-close orders for all open positions on this symbol.")

st.divider()

# =============================================================================
# ACCOUNT METRICS
# =============================================================================
st.subheader("💰 Account Overview")
acc = get_account()
if acc:
    c1, c2, c3 = st.columns(3)
    c1.metric("Balance",      f"${acc['balance']:,.2f}")
    c2.metric("Equity",       f"${acc['equity']:,.2f}")
    c3.metric("Floating P&L", f"${acc['profit']:+,.2f}")
else:
    st.error("Could not retrieve account info — MT5 disconnected?")

st.divider()

# =============================================================================
# LIVE PRICE & RECENT SIGNAL
# Dashboard is READ-ONLY: signal intelligence is in the Trading Brain (main.py)
# =============================================================================
price = get_price()

col_price, col_signal = st.columns(2)

with col_price:
    st.subheader("📡 Live Price")
    if price:
        p1, p2 = st.columns(2)
        p1.metric("Bid", f"{price['bid']:.3f}")
        p2.metric("Ask", f"{price['ask']:.3f}")
    else:
        st.error("No price data")

with col_signal:
    st.subheader("🎯 Recent Signal")
    # Show the most recent trade's type
    recent_trades = get_trades(limit=1)
    if recent_trades:
        recent_trade = recent_trades[0]
        # Trade tuple: (id, ticket, type, volume, price, profit, status, time)
        trade_type = recent_trade[2]  # "BUY" or "SELL"
        if trade_type == "BUY":
            st.success("🟢 BUY SIGNAL")
        elif trade_type == "SELL":
            st.error("🔴 SELL SIGNAL")
        else:
            st.info("⏳ NO SIGNAL")
    else:
        st.info("⏳ NO SIGNAL")

st.divider()

# =============================================================================
# OPEN POSITIONS
# =============================================================================
st.subheader("📦 Open Positions")
positions = get_positions()
if positions:
    pos_rows = [
        {
            "Ticket":        p.ticket,
            "Type":          "BUY" if p.type == 0 else "SELL",
            "Volume":        p.volume,
            "Open Price":    p.price_open,
            "Current Price": p.price_current,
            "Profit":        p.profit,
        }
        for p in positions
    ]
    st.dataframe(pd.DataFrame(pos_rows), use_container_width=True)
else:
    st.info("No open trades")

st.divider()

# =============================================================================
# MARKET CHART
# FIX: renamed from `df` to `df_rates` to avoid collision with trade history df.
# =============================================================================
st.subheader("📊 Market Chart (M1 — last 100 bars)")
df_rates = get_rates()
if df_rates is not None:
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=df_rates["time"],
                open=df_rates["open"],
                high=df_rates["high"],
                low=df_rates["low"],
                close=df_rates["close"],
            )
        ]
    )
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        margin=dict(l=0, r=0, t=30, b=0),
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# =============================================================================
# TRADE HISTORY & ANALYTICS
# =============================================================================
st.subheader("📜 Trade History")

trades = get_trades(limit=500)

if trades:
    # Dynamic column detection — does not break if schema gains extra columns.
    # Column order from DB: id, ticket, type, volume, price, profit, status, time
    EXPECTED_COLS = ["ID", "Ticket", "Type", "Volume", "Entry Price", "Profit", "Status", "Time"]

    num_cols = len(trades[0])
    if num_cols == len(EXPECTED_COLS):
        columns = EXPECTED_COLS
    elif num_cols == len(EXPECTED_COLS) - 1:
        # Old schema without 'status'
        columns = [c for c in EXPECTED_COLS if c != "Status"]
    else:
        # Fallback: generic column names
        columns = [f"col_{i}" for i in range(num_cols)]

    df_trades = pd.DataFrame(trades, columns=columns)
    
    # ── Fix: Handle missing "Profit" column ───────────────────────────────
    # If the dynamic column detection failed to create "Profit", try to identify it.
    profit_col = None
    if "Profit" in df_trades.columns:
        profit_col = "Profit"
    else:
        # Try alternative column names or positions
        for col in df_trades.columns:
            if col.lower() == "profit":
                profit_col = col
                break
        # If still not found, check if 6th column (index 5) is profit
        if profit_col is None and len(df_trades.columns) >= 6:
            profit_col = df_trades.columns[5]
    
    if profit_col:
        df_trades[profit_col] = pd.to_numeric(df_trades[profit_col], errors="coerce")
        # Rename to "Profit" for consistency if needed
        if profit_col != "Profit":
            df_trades = df_trades.rename(columns={profit_col: "Profit"})
    else:
        st.error("⚠️ Could not identify 'Profit' column in trade data. Database schema may be corrupt.")
        st.write("Debug info — actual columns:", df_trades.columns.tolist())

    st.dataframe(df_trades, use_container_width=True)

    # ── Analytics — closed trades only ───────────────────────────────────
    # FIX: was computing win/loss on ALL trades, counting open (profit=0) as losses.
    #      Now restricted to status='closed' rows only.
    if profit_col and ("Profit" in df_trades.columns or profit_col in df_trades.columns):
        profit_column = "Profit" if "Profit" in df_trades.columns else profit_col
        
        if "Status" in df_trades.columns:
            df_closed = df_trades[df_trades["Status"] == "closed"].copy()
        else:
            df_closed = df_trades.copy()  # old schema: include all

        total_closed = len(df_closed)
        wins         = len(df_closed[df_closed[profit_column] > 0])
        losses       = len(df_closed[df_closed[profit_column] < 0])
        total_pnl    = df_closed[profit_column].sum()
        win_rate     = (wins / total_closed * 100) if total_closed > 0 else 0.0
    else:
        total_closed = wins = losses = total_pnl = win_rate = 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Trades",   len(df_trades))
    c2.metric("Closed Trades",  total_closed)
    c3.metric("Win Rate",       f"{win_rate:.1f}%")
    c4.metric("Losses",         losses)
    c5.metric("Realized P&L",   f"${total_pnl:.2f}")

else:
    st.info("No trades recorded yet.")