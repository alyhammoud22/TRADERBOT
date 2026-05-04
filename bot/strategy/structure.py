import MetaTrader5 as mt5
import pandas as pd
from bot.utils.config import SYMBOL, HTF_PERIOD, ATR_LOW_VOL_THRESHOLD, ATR_HIGH_VOL_THRESHOLD


def _max_consecutive_up(values) -> int:
    """
    Count the longest consecutive run where values[i] > values[i-1].
    FIX: original code counted ANY higher value over the window (not consecutive),
         which could fire in sideways markets. This counts strict consecutive runs.
    """
    best = streak = 0
    for i in range(1, len(values)):
        if values[i] > values[i - 1]:
            streak += 1
            if streak > best:
                best = streak
        else:
            streak = 0
    return best


def _max_consecutive_down(values) -> int:
    """Count the longest consecutive run where values[i] < values[i-1]."""
    best = streak = 0
    for i in range(1, len(values)):
        if values[i] < values[i - 1]:
            streak += 1
            if streak > best:
                best = streak
        else:
            streak = 0
    return best


def _apply_market_filters(df_m1):
    """
    Apply critical market filters before confirming signal.
    Returns filter data dict if all pass, None otherwise.
    """
    
    # ─ Filter 1: Higher Timeframe Trend (H1 EMA50) ────────────────────────
    rates_h1 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1, 0, 100)
    if rates_h1 is None:
        return None
    
    df_h1 = pd.DataFrame(rates_h1)
    df_h1["ema50"] = df_h1["close"].ewm(span=HTF_PERIOD, adjust=False).mean()
    h1_ema50 = df_h1.iloc[-1]["ema50"]
    h1_close = df_h1.iloc[-1]["close"]
    
    # ─ Filter 2: Volatility Filter (ATR Regime) ──────────────────────────
    df_m1["hl"]  = df_m1["high"] - df_m1["low"]
    df_m1["hc"]  = (df_m1["high"] - df_m1["close"].shift()).abs()
    df_m1["lc"]  = (df_m1["low"]  - df_m1["close"].shift()).abs()
    df_m1["tr"]  = df_m1[["hl", "hc", "lc"]].max(axis=1)
    df_m1["atr"] = df_m1["tr"].rolling(14).mean()
    
    avg_atr = df_m1["atr"].mean()
    current_atr = df_m1.iloc[-1]["atr"]
    
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
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 50)
    if rates is None:
        return None

    df = pd.DataFrame(rates)

    # ── Apply market filters first ──────────────────────────────────────
    filters = _apply_market_filters(df)
    if filters is None:
        return None

    recent_highs = df["high"].values[-10:]
    recent_lows  = df["low"].values[-10:]
    last_close   = df["close"].values[-1]

    hh_streak = _max_consecutive_up(recent_highs)    # consecutive Higher Highs
    hl_streak = _max_consecutive_up(recent_lows)     # consecutive Higher Lows
    lh_streak = _max_consecutive_down(recent_highs)  # consecutive Lower Highs
    ll_streak = _max_consecutive_down(recent_lows)   # consecutive Lower Lows

    signal = None

    # BUY: genuine uptrend structure + HTF alignment
    if hh_streak >= 3 and hl_streak >= 3:
        if last_close > recent_lows[-5]:
            # HTF trend filter: allow BUY only if price > H1 EMA50
            if last_close > filters["htf_ema50"]:
                signal = "BUY"

    # SELL: genuine downtrend structure + HTF alignment
    # elif prevents BUY and SELL from being returned simultaneously
    elif lh_streak >= 3 and ll_streak >= 3:
        if last_close < recent_highs[-5]:
            # HTF trend filter: allow SELL only if price < H1 EMA50
            if last_close < filters["htf_ema50"]:
                signal = "SELL"

    return signal