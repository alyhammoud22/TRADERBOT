import MetaTrader5 as mt5
import pandas as pd
from bot.utils.config import SYMBOL, HTF_PERIOD, ATR_LOW_VOL_THRESHOLD, ATR_HIGH_VOL_THRESHOLD

# Module-level state: remember the last bar we fired a signal on.
# Prevents re-firing the same crossover signal on every 60-second loop tick
# while the M1 candle that triggered it is still the latest bar.
_last_signal_bar_time = None


def _apply_market_filters(df_m1, last_row):
    """
    Apply critical market filters before confirming signal.
    Returns True if all filters pass, False otherwise.
    """
    
    # ─ Filter 1: Higher Timeframe Trend (H1 EMA50) ────────────────────────
    rates_h1 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1, 0, 100)
    if rates_h1 is None:
        return None  # No HTF data
    
    df_h1 = pd.DataFrame(rates_h1)
    df_h1["ema50"] = df_h1["close"].ewm(span=HTF_PERIOD, adjust=False).mean()
    h1_ema50 = df_h1.iloc[-1]["ema50"]
    h1_close = df_h1.iloc[-1]["close"]
    
    # ─ Filter 2: Volatility Filter (ATR Regime) ──────────────────────────
    avg_atr = df_m1["atr"].mean()
    current_atr = last_row["atr"]
    
    if pd.isna(current_atr):
        return None
    
    atr_ratio = current_atr / avg_atr if avg_atr > 0 else 0
    
    if atr_ratio < ATR_LOW_VOL_THRESHOLD:
        return None  # Too quiet
    if atr_ratio > ATR_HIGH_VOL_THRESHOLD:
        return None  # Too volatile
    
    # ─ Filter 3: Spread Check ────────────────────────────────────────────
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        return None
    
    spread = tick.ask - tick.bid
    sym = mt5.symbol_info(SYMBOL)
    if sym is None:
        return None
    
    point = sym.point
    spread_pips = spread / point if point > 0 else 0
    
    from bot.utils.config import MAX_SPREAD
    if spread_pips > MAX_SPREAD:
        return None  # Spread too high
    
    return {"htf_price": h1_close, "htf_ema50": h1_ema50, "spread": spread}


def get_signal():
    global _last_signal_bar_time

    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 100)
    if rates is None:
        return None

    df = pd.DataFrame(rates)

    # adjust=False gives true recursive EMA (standard trading convention)
    df["ema10"] = df["close"].ewm(span=10, adjust=False).mean()
    df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()

    # ATR (14-period)
    df["hl"]  = df["high"] - df["low"]
    df["hc"]  = (df["high"] - df["close"].shift()).abs()
    df["lc"]  = (df["low"]  - df["close"].shift()).abs()
    df["tr"]  = df[["hl", "hc", "lc"]].max(axis=1)
    df["atr"] = df["tr"].rolling(14).mean()

    last = df.iloc[-1]
    prev = df.iloc[-2]

    current_bar_time = last["time"]

    # ── Guard: only fire once per M1 bar ─────────────────────────────────
    if current_bar_time == _last_signal_bar_time:
        return None

    # ── Apply all market filters ─────────────────────────────────────────
    filters = _apply_market_filters(df, last)
    if filters is None:
        return None
    
    # ── Signal detection (elif ensures mutual exclusivity) ────────────────
    signal = None

    if prev["ema10"] < prev["ema50"] and last["ema10"] > last["ema50"]:
        # Bullish crossover with close-above-EMA50 confirmation
        if last["close"] > last["ema50"]:
            # Apply HTF trend filter: allow BUY only if price > H1 EMA50
            if last["close"] > filters["htf_ema50"]:
                signal = "BUY"

    elif prev["ema10"] > prev["ema50"] and last["ema10"] < last["ema50"]:
        # Bearish crossover with close-below-EMA50 confirmation
        if last["close"] < last["ema50"]:
            # Apply HTF trend filter: allow SELL only if price < H1 EMA50
            if last["close"] < filters["htf_ema50"]:
                signal = "SELL"

    if signal:
        _last_signal_bar_time = current_bar_time  # lock bar — no re-fire

    return signal