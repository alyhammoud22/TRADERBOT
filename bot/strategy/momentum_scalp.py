"""
momentum_scalp.py — EMA + Momentum + Candle Strength Strategy
==============================================================

Designed for:
  - XAUUSD M1 scalping
  - High-frequency signal generation
  - Fast execution pipeline validation
  - Deterministic, debuggable logic

Signal Logic
------------
BUY:
  1. EMA20 > EMA50  (short-term trend above medium-term trend)
  2. Current candle is bullish  (close > open)
  3. Candle body > average body of last N candles  (real momentum, not noise)
  4. Close is within top 30% of candle range  (price closing strong, buyers in control)

SELL:
  1. EMA20 < EMA50
  2. Current candle is bearish  (close < open)
  3. Candle body > average body of last N candles
  4. Close is within bottom 30% of candle range  (sellers in control)

Design Decisions
----------------
- No per-bar lock: signals CAN re-fire across the same candle direction run.
  This is intentional for pipeline validation. Toggle LOCK_TO_BAR to restrict.
- All filter checks are printed in detail so you can see EXACTLY why each
  candle passes or fails in the terminal.
- The brain_engine still applies its own trend/spread/volatility gates on top.
  This strategy only answers: "Is THIS candle a quality entry candle?"
"""

import MetaTrader5 as mt5
import pandas as pd
import logging
from datetime import datetime

from bot.utils.config import SYMBOL

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# TUNING PARAMETERS
# Adjust these to control signal frequency and quality.
# ─────────────────────────────────────────────────────────────────────────────

# How many M1 bars to load
LOOKBACK_BARS = 100

# EMA periods
EMA_FAST = 20
EMA_SLOW = 50

# How many bars to average for "typical" body size
BODY_AVERAGE_PERIOD = 14

# Body must be this many times larger than average (1.0 = same size, 0.8 = 80%)
# Lower = more signals. Raise to 1.2+ to filter weak candles.
BODY_STRENGTH_MULTIPLIER = 0.8

# Close must be in top/bottom N% of the candle range for momentum confirmation
# 0.30 = top/bottom 30%. Higher = stricter (fewer signals). Lower = looser.
MOMENTUM_ZONE = 0.30

# If True: only one signal per M1 bar (prevents spam within a bar)
# If False: signal fires every loop cycle the conditions are met (more trades)
# Set to False for pipeline validation, True for real trading.
LOCK_TO_BAR = False

# ─────────────────────────────────────────────────────────────────────────────
# MODULE STATE
# ─────────────────────────────────────────────────────────────────────────────

_last_signal_bar_time = None   # used only when LOCK_TO_BAR = True
_signal_count = 0              # lifetime counter for debug visibility


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _print_separator():
    print(f"\n  {'─' * 62}")


def _log_header(bar_time, current_price):
    """Print the strategy evaluation header for this candle."""
    ts = datetime.utcfromtimestamp(bar_time).strftime("%H:%M:%S")
    print(f"\n  ┌{'─' * 62}┐")
    print(f"  │  📊 MOMENTUM SCALP  │  Bar: {ts} UTC  │  Price: {current_price:.3f}  │")
    print(f"  └{'─' * 62}┘")


def _log_ema(ema_fast_val, ema_slow_val, aligned, direction):
    """Print EMA status with pass/fail."""
    diff = ema_fast_val - ema_slow_val
    icon = "✅" if aligned else "❌"
    print(f"  {icon}  EMA CHECK     │  EMA{EMA_FAST}: {ema_fast_val:.3f}  │  EMA{EMA_SLOW}: {ema_slow_val:.3f}  │  Δ {diff:+.3f}  →  {direction}")


def _log_candle(open_, close, high, low, is_bullish):
    """Print candle direction check."""
    body = abs(close - open_)
    candle_range = high - low if (high - low) > 0 else 0.0001
    icon = "✅" if is_bullish is not None else "❌"
    direction = "BULLISH" if is_bullish else "BEARISH" if is_bullish is False else "DOJI"
    print(f"  {icon}  CANDLE        │  O: {open_:.3f}  C: {close:.3f}  │  Body: {body:.4f}  │  {direction}")


def _log_body_strength(body, avg_body, threshold, passed):
    """Print body size comparison."""
    ratio = body / avg_body if avg_body > 0 else 0.0
    icon = "✅" if passed else "❌"
    print(
        f"  {icon}  BODY STRENGTH │  Body: {body:.4f}  │  Avg({BODY_AVERAGE_PERIOD}): {avg_body:.4f}  │"
        f"  Ratio: {ratio:.2f}x  │  Need ≥ {BODY_STRENGTH_MULTIPLIER:.2f}x  →  {'PASS' if passed else 'FAIL'}"
    )


def _log_momentum(close, high, low, zone_pct, passed, side):
    """Print close position within candle range."""
    candle_range = high - low
    if candle_range <= 0:
        position_pct = 0.5
    else:
        position_pct = (close - low) / candle_range

    icon = "✅" if passed else "❌"
    if side == "BUY":
        note = f"Top {int(MOMENTUM_ZONE * 100)}% zone ≥ {1 - MOMENTUM_ZONE:.2f}  →  close at {position_pct:.2f}"
    else:
        note = f"Bot {int(MOMENTUM_ZONE * 100)}% zone ≤ {MOMENTUM_ZONE:.2f}  →  close at {position_pct:.2f}"

    print(f"  {icon}  MOMENTUM      │  {note}  │  {'PASS' if passed else 'FAIL'}")


def _log_decision(signal, reason=""):
    """Print the final decision."""
    global _signal_count
    if signal:
        _signal_count += 1
        color_tag = "🟢 BUY" if signal == "BUY" else "🔴 SELL"
        print(f"\n  ══► SIGNAL #{_signal_count}: {color_tag}  (momentum_scalp)\n")
        logger.info(f"momentum_scalp signal #{_signal_count}: {signal}")
    else:
        print(f"\n  ──► NO SIGNAL  │  Blocked by: {reason}\n")
        logger.debug(f"momentum_scalp: no signal — {reason}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN SIGNAL FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def get_signal():
    """
    Momentum Scalp Strategy.

    Returns: "BUY" | "SELL" | None

    All filter checks are printed to stdout so you can trace every decision
    in the terminal without opening a debugger.

    The brain_engine applies its own spread / trend / volatility gates after
    this returns. This function ONLY evaluates candle-level signal quality.
    """
    global _last_signal_bar_time

    # ── 1. Fetch price data ───────────────────────────────────────────────
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, LOOKBACK_BARS)

    if rates is None or len(rates) < BODY_AVERAGE_PERIOD + 5:
        logger.warning(
            f"momentum_scalp: insufficient data "
            f"(got {len(rates) if rates is not None else 0} bars, "
            f"need {BODY_AVERAGE_PERIOD + 5})"
        )
        return None

    df = pd.DataFrame(rates)

    # ── 2. Calculate indicators ───────────────────────────────────────────
    df["ema_fast"] = df["close"].ewm(span=EMA_FAST, adjust=False).mean()
    df["ema_slow"] = df["close"].ewm(span=EMA_SLOW, adjust=False).mean()
    df["body"]     = (df["close"] - df["open"]).abs()
    df["avg_body"] = df["body"].rolling(BODY_AVERAGE_PERIOD).mean()

    last = df.iloc[-1]

    # ── 3. Per-bar lock (optional) ────────────────────────────────────────
    current_bar_time = last["time"]
    if LOCK_TO_BAR and current_bar_time == _last_signal_bar_time:
        # Silent return — already evaluated this exact bar
        return None

    # ── 4. Extract values ─────────────────────────────────────────────────
    open_price  = last["open"]
    close_price = last["close"]
    high_price  = last["high"]
    low_price   = last["low"]
    ema_fast    = last["ema_fast"]
    ema_slow    = last["ema_slow"]
    body        = last["body"]
    avg_body    = last["avg_body"]

    # Guard: NaN check (happens on first few bars after startup)
    if pd.isna(ema_fast) or pd.isna(ema_slow) or pd.isna(avg_body):
        logger.warning("momentum_scalp: NaN in indicators — not enough bars warmed up yet")
        return None

    # Guard: degenerate candle (spread-only bar, no real price movement)
    candle_range = high_price - low_price
    if candle_range < 0.0001:
        logger.debug("momentum_scalp: degenerate candle (range < 0.0001) — skip")
        return None

    # ── 5. Print evaluation header ────────────────────────────────────────
    _log_header(current_bar_time, close_price)

    # ── 6. EMA direction ─────────────────────────────────────────────────
    ema_bullish = ema_fast > ema_slow
    ema_bearish = ema_fast < ema_slow

    if ema_bullish:
        ema_direction = "BULLISH ALIGNED"
    elif ema_bearish:
        ema_direction = "BEARISH ALIGNED"
    else:
        ema_direction = "FLAT (no edge)"

    _log_ema(ema_fast, ema_slow, ema_bullish or ema_bearish, ema_direction)

    if not (ema_bullish or ema_bearish):
        _log_decision(None, "EMAs flat — no directional edge")
        return None

    # ── 7. Candle direction ───────────────────────────────────────────────
    candle_bullish = close_price > open_price
    candle_bearish = close_price < open_price
    candle_is_doji = not (candle_bullish or candle_bearish)

    _log_candle(open_price, close_price, high_price, low_price, 
                True if candle_bullish else (False if candle_bearish else None))

    if candle_is_doji:
        _log_decision(None, "Doji candle — no directional conviction")
        return None

    # ── 8. Body strength ─────────────────────────────────────────────────
    body_threshold = avg_body * BODY_STRENGTH_MULTIPLIER
    body_strong    = body >= body_threshold

    _log_body_strength(body, avg_body, body_threshold, body_strong)

    if not body_strong:
        _log_decision(None, f"Body too small ({body:.4f} < {body_threshold:.4f})")
        return None

    # ── 9. Momentum zone (close position within bar) ───────────────────────
    close_position = (close_price - low_price) / candle_range  # 0.0 = low, 1.0 = high

    # BUY path
    if ema_bullish and candle_bullish:
        momentum_ok = close_position >= (1.0 - MOMENTUM_ZONE)
        _log_momentum(close_price, high_price, low_price, close_position, momentum_ok, "BUY")

        if not momentum_ok:
            _log_decision(None, f"Close not in top {int(MOMENTUM_ZONE * 100)}% of range ({close_position:.2f})")
            return None

        # All checks passed → BUY
        if LOCK_TO_BAR:
            _last_signal_bar_time = current_bar_time

        _log_decision("BUY")
        return "BUY"

    # SELL path
    elif ema_bearish and candle_bearish:
        momentum_ok = close_position <= MOMENTUM_ZONE
        _log_momentum(close_price, high_price, low_price, close_position, momentum_ok, "SELL")

        if not momentum_ok:
            _log_decision(None, f"Close not in bottom {int(MOMENTUM_ZONE * 100)}% of range ({close_position:.2f})")
            return None

        # All checks passed → SELL
        if LOCK_TO_BAR:
            _last_signal_bar_time = current_bar_time

        _log_decision("SELL")
        return "SELL"

    # Direction mismatch (EMA bullish but candle bearish, or vice versa)
    else:
        if ema_bullish and candle_bearish:
            reason = "EMA bullish but candle bearish — counter-trend candle, skip"
        else:
            reason = "EMA bearish but candle bullish — counter-trend candle, skip"

        print(f"  ❌  DIRECTION    │  EMA and candle disagree — no trade")
        _log_decision(None, reason)
        return None