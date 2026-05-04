"""
Market Context Module — Unified market analysis for decision intelligence.

Provides real-time market conditions:
- Trend detection (HTF EMA)
- Volatility regime
- Session detection
- Spread quality
"""

import MetaTrader5 as mt5
import pandas as pd
import logging
from datetime import datetime, timezone

from bot.utils.config import SYMBOL, HTF_PERIOD, ATR_LOW_VOL_THRESHOLD, ATR_HIGH_VOL_THRESHOLD, MAX_SPREAD

logger = logging.getLogger(__name__)


class MarketContext:
    """Immutable market context snapshot."""
    
    def __init__(self):
        self.trend = None  # "bullish" | "bearish" | "sideways"
        self.volatility = None  # "low" | "normal" | "high"
        self.spread_pips = 0.0
        self.spread_acceptable = False
        self.session = None  # "asia" | "london" | "ny" | "other"
        self.current_price = 0.0
        self.h1_ema50 = 0.0
        self.atr14 = 0.0
        self.timestamp = None
        
    def __repr__(self):
        return (
            f"MarketContext(trend={self.trend}, vol={self.volatility}, "
            f"spread={self.spread_pips:.2f}pips, session={self.session})"
        )


def _get_htf_trend(price: float) -> str:
    """
    Determine trend from H1 EMA50.
    Returns: "bullish" | "bearish" | "sideways"
    """
    rates_h1 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1, 0, 100)
    if rates_h1 is None or len(rates_h1) < 50:
        return "sideways"  # No data
    
    df_h1 = pd.DataFrame(rates_h1)
    df_h1["ema50"] = df_h1["close"].ewm(span=HTF_PERIOD, adjust=False).mean()
    
    h1_ema50 = df_h1.iloc[-1]["ema50"]
    
    if pd.isna(h1_ema50):
        return "sideways"
    
    # Trend detection
    if price > h1_ema50 * 1.001:  # 0.1% above
        return "bullish"
    elif price < h1_ema50 * 0.999:  # 0.1% below
        return "bearish"
    else:
        return "sideways"


def _get_volatility_regime() -> str:
    """
    Determine volatility regime from ATR(14) ratio.
    Returns: "low" | "normal" | "high"
    """
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 100)
    if rates is None or len(rates) < 14:
        return "normal"  # Default
    
    df = pd.DataFrame(rates)
    df["hl"] = df["high"] - df["low"]
    df["hc"] = (df["high"] - df["close"].shift()).abs()
    df["lc"] = (df["low"] - df["close"].shift()).abs()
    df["tr"] = df[["hl", "hc", "lc"]].max(axis=1)
    df["atr"] = df["tr"].rolling(14).mean()
    
    current_atr = df.iloc[-1]["atr"]
    avg_atr = df["atr"].mean()
    
    if pd.isna(current_atr) or avg_atr <= 0:
        return "normal"
    
    atr_ratio = current_atr / avg_atr
    
    if atr_ratio < ATR_LOW_VOL_THRESHOLD:
        return "low"
    elif atr_ratio > ATR_HIGH_VOL_THRESHOLD:
        return "high"
    else:
        return "normal"


def _detect_session() -> str:
    """
    Detect current trading session based on UTC time.
    Returns: "asia" | "london" | "ny" | "other"
    
    Sessions (approximate UTC):
    - Asia: 22:00 - 08:00
    - London: 08:00 - 17:00
    - NY: 13:00 - 22:00
    """
    now_utc = datetime.now(timezone.utc)
    hour = now_utc.hour
    
    # Simple session detection (can be enhanced)
    if 22 <= hour or hour < 8:
        return "asia"
    elif 8 <= hour < 17:
        return "london"
    elif 13 <= hour < 22:
        return "ny"
    else:
        return "other"


def _get_spread_info() -> tuple:
    """
    Get current spread in pips.
    Returns: (spread_pips, is_acceptable)
    """
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        return (0.0, False)
    
    sym = mt5.symbol_info(SYMBOL)
    if sym is None:
        return (0.0, False)
    
    spread = tick.ask - tick.bid
    point = sym.point
    spread_pips = spread / point if point > 0 else 0.0
    
    is_acceptable = spread_pips <= MAX_SPREAD
    
    return (spread_pips, is_acceptable)


def get_market_context() -> MarketContext:
    """
    Analyze current market and return unified context.
    """
    ctx = MarketContext()
    
    # Get current price
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        logger.warning("get_market_context: no tick data")
        return ctx
    
    ctx.current_price = tick.ask
    
    # Get H1 EMA50
    rates_h1 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1, 0, 100)
    if rates_h1 is not None and len(rates_h1) >= 50:
        df_h1 = pd.DataFrame(rates_h1)
        df_h1["ema50"] = df_h1["close"].ewm(span=HTF_PERIOD, adjust=False).mean()
        h1_ema50 = df_h1.iloc[-1]["ema50"]
        if not pd.isna(h1_ema50):
            ctx.h1_ema50 = h1_ema50
    
    # Get ATR14
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 100)
    if rates is not None and len(rates) >= 14:
        df = pd.DataFrame(rates)
        df["hl"] = df["high"] - df["low"]
        df["hc"] = (df["high"] - df["close"].shift()).abs()
        df["lc"] = (df["low"] - df["close"].shift()).abs()
        df["tr"] = df[["hl", "hc", "lc"]].max(axis=1)
        df["atr"] = df["tr"].rolling(14).mean()
        current_atr = df.iloc[-1]["atr"]
        if not pd.isna(current_atr):
            ctx.atr14 = current_atr
    
    # Analyze conditions
    ctx.trend = _get_htf_trend(ctx.current_price)
    ctx.volatility = _get_volatility_regime()
    ctx.spread_pips, ctx.spread_acceptable = _get_spread_info()
    ctx.session = _detect_session()
    ctx.timestamp = datetime.now(timezone.utc)
    
    logger.debug(f"Market context: {ctx}")
    
    return ctx
