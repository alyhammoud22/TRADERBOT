import MetaTrader5 as mt5
import pandas as pd
import logging

from bot.utils.config import SYMBOL

logger = logging.getLogger(__name__)

# Module-level state: remember the last bar we fired a signal on.
# Prevents re-firing the same crossover signal on every loop tick.
_last_signal_bar_time = None


def get_signal():
    """
    EMA crossover strategy.
    
    Logic:
    1. Get M1 rates
    2. Calculate EMA10 and EMA50
    3. Check for crossover
    4. Prevent duplicate signals on same candle
    
    Returns: "BUY" | "SELL" | None
    
    NOTE: Market filters (HTF trend, spread, volatility) are applied
          by the Brain Engine, not here.
    """
    global _last_signal_bar_time

    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 100)
    if rates is None or len(rates) < 50:
        logger.warning("ema.get_signal: insufficient data")
        return None

    df = pd.DataFrame(rates)

    # EMA calculation (adjust=False = true recursive EMA, standard trading convention)
    df["ema10"] = df["close"].ewm(span=10, adjust=False).mean()
    df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()

    last = df.iloc[-1]
    prev = df.iloc[-2]

    current_bar_time = last["time"]

    # ── Guard: only fire once per M1 bar ──────────────────────────────────
    if current_bar_time == _last_signal_bar_time:
        return None

    # ── Signal detection ──────────────────────────────────────────────────
    signal = None

    if prev["ema10"] < prev["ema50"] and last["ema10"] > last["ema50"]:
        # Bullish crossover: EMA10 crosses above EMA50
        if last["close"] > last["ema50"]:
            signal = "BUY"

    elif prev["ema10"] > prev["ema50"] and last["ema10"] < last["ema50"]:
        # Bearish crossover: EMA10 crosses below EMA50
        if last["close"] < last["ema50"]:
            signal = "SELL"

    if signal:
        _last_signal_bar_time = current_bar_time  # lock bar — no re-fire
        logger.info(f"EMA signal: {signal}")

    return signal