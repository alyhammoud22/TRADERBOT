import MetaTrader5 as mt5
import pandas as pd
import logging
import time

from bot.utils.config import SYMBOL, MAX_SPREAD

logger = logging.getLogger(__name__)


# =============================================================================
# ATR CALCULATION
# =============================================================================

def get_atr(n=100, period=14) -> float:
    """
    Calculate ATR(14) from M1 rates.
    Returns the current ATR value.
    """
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, n)
    if rates is None or len(rates) < period:
        logger.warning("get_atr: insufficient data")
        return 0.0
    
    df = pd.DataFrame(rates)
    df["hl"] = df["high"] - df["low"]
    df["hc"] = (df["high"] - df["close"].shift()).abs()
    df["lc"] = (df["low"] - df["close"].shift()).abs()
    df["tr"] = df[["hl", "hc", "lc"]].max(axis=1)
    df["atr"] = df["tr"].rolling(period).mean()
    
    current_atr = df.iloc[-1]["atr"]
    
    if pd.isna(current_atr):
        logger.warning("get_atr: NaN result")
        return 0.0
    
    return float(current_atr)


# =============================================================================
# SL/TP CALCULATION (ATR-BASED)
# =============================================================================

def calculate_sl_tp_from_atr() -> tuple:
    """
    Calculate SL and TP in points based on ATR(14).
    - SL = 1.2 * ATR
    - TP = 2.0 * ATR
    
    Returns:
        (sl_points, tp_points) tuple
    """
    atr = get_atr()
    
    if atr <= 0:
        logger.warning("calculate_sl_tp_from_atr: invalid ATR")
        return (300, 600)  # Fallback to defaults
    
    sym = mt5.symbol_info(SYMBOL)
    if sym is None:
        logger.error("calculate_sl_tp_from_atr: symbol_info() returned None")
        return (300, 600)
    
    point = sym.point
    if point <= 0:
        logger.error("calculate_sl_tp_from_atr: invalid point")
        return (300, 600)
    
    atr_points = atr / point
    
    # SL and TP based on ATR
    sl_points = int(1.2 * atr_points)
    tp_points = int(2.0 * atr_points)
    
    # Ensure minimum values
    sl_points = max(sl_points, 50)
    tp_points = max(tp_points, 100)
    
    logger.info(f"ATR-based SL/TP: ATR={atr:.5f} → SL={sl_points}pts TP={tp_points}pts")
    
    return (sl_points, tp_points)


# =============================================================================
# EXECUTION VALIDATION
# =============================================================================

def validate_execution(order_type: str, requested_price: float, max_slippage_usd: float = 1.0) -> bool:
    """
    Re-validate execution conditions before order send.

    Checks:
    1. Current spread is acceptable  (dollar spread, not pip-divided)
    2. Price hasn't moved too far from request  (dollar slippage)
    3. Tick data is fresh (< 2 seconds old)

    Args:
        order_type: "BUY" or "SELL"
        requested_price: Price we intended to execute at
        max_slippage_usd: Max acceptable price movement in dollars (default $1.00)

    Returns:
        True if all checks pass, False otherwise
    """

    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        logger.error("validate_execution: symbol_info_tick returned None")
        return False

    # ── Check 1: Spread (dollar spread) ──────────────────────────────────
    spread_usd = tick.ask - tick.bid

    from bot.utils.config import MAX_SPREAD
    if spread_usd > MAX_SPREAD:
        logger.warning(
            f"validate_execution REJECTED: spread=${spread_usd:.2f} > ${MAX_SPREAD}"
        )
        return False

    # ── Check 2: Slippage (dollar movement) ──────────────────────────────
    current_price = tick.ask if order_type == "BUY" else tick.bid
    slippage_usd = abs(current_price - requested_price)

    if slippage_usd > max_slippage_usd:
        logger.warning(
            f"validate_execution REJECTED: slippage=${slippage_usd:.2f} > ${max_slippage_usd}"
        )
        return False

    # ── Check 3: Price freshness ──────────────────────────────────────────
    tick_age = time.time() - tick.time
    if tick_age > 2.0:
        logger.warning(f"validate_execution REJECTED: tick age={tick_age:.1f}s > 2s")
        return False

    logger.debug(
        f"validate_execution OK: spread=${spread_usd:.2f} slippage=${slippage_usd:.2f} tick_age={tick_age:.2f}s"
    )
    return True


# =============================================================================
# POSITION MANAGEMENT (BREAK-EVEN + TRAILING STOP)
# =============================================================================

def _modify_position_sl(ticket: int, new_sl: float) -> bool:
    """
    Modify the SL of an open position.
    Returns True if successful, False otherwise.
    """
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": ticket,
        "sl": new_sl,
    }
    
    result = mt5.order_send(request)
    
    if result is None:
        logger.error(f"_modify_position_sl failed: order_send returned None")
        return False
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.warning(
            f"_modify_position_sl failed (ticket={ticket}): retcode={result.retcode}"
        )
        return False
    
    logger.info(f"Position SL modified: ticket={ticket} new_sl={new_sl:.5f}")
    return True


def manage_open_trades():
    """
    Manage all open positions for break-even and trailing stop.
    
    Logic:
    1. When price moves +1 ATR in profit → Move SL to entry price (break-even)
    2. When price moves +1.5 ATR in profit → Trail SL behind price (distance = 1 ATR)
    
    Called periodically (e.g., every sync_profit cycle).
    """
    positions = mt5.positions_get(symbol=SYMBOL)
    
    if not positions:
        logger.debug("manage_open_trades: no open positions")
        return
    
    atr = get_atr()
    if atr <= 0:
        logger.warning("manage_open_trades: invalid ATR, skipping")
        return
    
    sym = mt5.symbol_info(SYMBOL)
    if sym is None:
        logger.error("manage_open_trades: symbol_info returned None")
        return
    
    point = sym.point
    atr_distance = atr  # 1 ATR
    
    for pos in positions:
        if pos.symbol != SYMBOL:
            continue
        
        ticket = pos.ticket
        entry_price = pos.price_open
        current_price = pos.price_current
        profit = pos.profit
        is_buy = (pos.type == 0)
        
        logger.debug(
            f"Position {ticket}: entry={entry_price:.5f} current={current_price:.5f} "
            f"profit=${profit:.2f} ATR={atr:.5f}"
        )
        
        # ── Break-even logic: +1 ATR profit → SL to entry ──────────────────
        if profit > atr:
            if is_buy:
                # For BUY: SL should move to entry_price (break-even)
                if pos.sl < entry_price - point:
                    _modify_position_sl(ticket, entry_price)
                    logger.info(f"ticket={ticket} | Break-even SL set to entry {entry_price:.5f}")
            else:
                # For SELL: SL should move to entry_price (break-even)
                if pos.sl > entry_price + point:
                    _modify_position_sl(ticket, entry_price)
                    logger.info(f"ticket={ticket} | Break-even SL set to entry {entry_price:.5f}")
        
        # ── Trailing stop logic: +1.5 ATR profit → Trail SL ────────────────
        if profit > 1.5 * atr:
            if is_buy:
                # For BUY: Trail SL below current price by 1 ATR
                new_sl = current_price - atr_distance
                if new_sl > pos.sl + point:  # Only move SL higher
                    _modify_position_sl(ticket, new_sl)
                    logger.info(f"ticket={ticket} | Trailing SL updated to {new_sl:.5f}")
            else:
                # For SELL: Trail SL above current price by 1 ATR
                new_sl = current_price + atr_distance
                if new_sl < pos.sl - point:  # Only move SL lower
                    _modify_position_sl(ticket, new_sl)
                    logger.info(f"ticket={ticket} | Trailing SL updated to {new_sl:.5f}")