import MetaTrader5 as mt5
import pandas as pd
import logging

from bot.utils.config import SYMBOL

logger = logging.getLogger(__name__)


def _max_consecutive_up(values) -> int:
    """
    Count the longest consecutive run where values[i] > values[i-1].
    This detects genuine higher highs (not just any higher value).
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


def get_signal():
    """
    Market Structure Strategy.
    
    Logic:
    1. Get M1 candles
    2. Detect consecutive higher highs/lows (uptrend)
    3. Detect consecutive lower highs/lows (downtrend)
    4. Ensure current close is on the right side of recent structure
    
    Returns: "BUY" | "SELL" | None
    
    NOTE: Market filters (HTF trend, spread, volatility) are applied
          by the Brain Engine, not here.
    """
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 50)
    if rates is None or len(rates) < 10:
        logger.warning("structure.get_signal: insufficient data")
        return None

    df = pd.DataFrame(rates)

    recent_highs = df["high"].values[-10:]
    recent_lows  = df["low"].values[-10:]
    last_close   = df["close"].values[-1]

    hh_streak = _max_consecutive_up(recent_highs)    # consecutive Higher Highs
    hl_streak = _max_consecutive_up(recent_lows)     # consecutive Higher Lows
    lh_streak = _max_consecutive_down(recent_highs)  # consecutive Lower Highs
    ll_streak = _max_consecutive_down(recent_lows)   # consecutive Lower Lows

    signal = None

    # BUY: genuine uptrend structure (3+ higher highs AND 3+ higher lows)
    if hh_streak >= 3 and hl_streak >= 3:
        # Confirm: last close above recent lows
        if last_close > recent_lows[-5]:
            signal = "BUY"

    # SELL: genuine downtrend structure (3+ lower highs AND 3+ lower lows)
    # elif prevents both BUY and SELL signals simultaneously
    elif lh_streak >= 3 and ll_streak >= 3:
        # Confirm: last close below recent highs
        if last_close < recent_highs[-5]:
            signal = "SELL"

    if signal:
        logger.info(f"Structure signal: {signal} (HH={hh_streak}, HL={hl_streak}, LH={lh_streak}, LL={ll_streak})")

    return signal