import MetaTrader5 as mt5
import logging
from datetime import datetime, timezone
from bot.utils.config import (
    RISK_PERCENT,
    MIN_LOT,
    MAX_DAILY_LOSS,
    MAX_DAILY_TRADES,
    KILL_SWITCH_DRAWDOWN_PERCENT,
    SYMBOL,
)
from bot.database.db import get_trades

logger = logging.getLogger(__name__)


def calculate_dynamic_lot(sl_distance_points: int) -> float:
    """
    Calculate lot size based on risk % and SL distance.
    
    Args:
        sl_distance_points: Stop loss distance in points
    
    Returns:
        Lot size (respects MIN_LOT)
    """
    acc = mt5.account_info()
    if acc is None:
        logger.error("calculate_dynamic_lot: account_info() returned None")
        return MIN_LOT
    
    sym = mt5.symbol_info(SYMBOL)
    if sym is None:
        logger.error("calculate_dynamic_lot: symbol_info() returned None")
        return MIN_LOT
    
    balance = acc.balance
    if balance <= 0:
        logger.warning("calculate_dynamic_lot: balance <= 0, returning MIN_LOT")
        return MIN_LOT
    
    # Risk amount = balance * risk_percent / 100
    risk_amount = balance * (RISK_PERCENT / 100.0)
    
    # Point value (typically 1.0 for gold = $1 per point)
    point_value = sym.trade_tick_value if sym.trade_tick_value > 0 else 1.0
    
    # Lot size = risk_amount / (SL distance * point_value)
    if sl_distance_points <= 0:
        logger.warning("calculate_dynamic_lot: invalid SL distance")
        return MIN_LOT
    
    lot = risk_amount / (sl_distance_points * point_value)
    
    # Round to minimum and log
    lot = max(lot, MIN_LOT)
    
    # Round to standard increments (typically 0.01)
    lot = round(lot / 0.01) * 0.01
    
    logger.info(
        f"Dynamic lot calculated: balance={balance:.2f} risk%={RISK_PERCENT} "
        f"sl_dist={sl_distance_points} → lot={lot:.2f}"
    )
    
    return lot


def _get_daily_trades():
    """
    Get all trades closed today from database.
    Returns list of (ticket, profit, status) tuples.
    """
    try:
        all_trades = get_trades(limit=1000)
        if not all_trades:
            return []
        
        today = datetime.now(timezone.utc).date()
        today_trades = []
        
        for trade in all_trades:
            # trade is (id, ticket, type, volume, price, profit, status, time)
            trade_time = trade[7]  # time column
            if isinstance(trade_time, str):
                trade_date = datetime.fromisoformat(trade_time).date()
            else:
                # Fallback for other datetime formats
                trade_date = today  # Assume recent if can't parse
            
            if trade_date == today:
                today_trades.append(trade)
        
        return today_trades
    except Exception as exc:
        logger.error(f"_get_daily_trades failed: {exc}")
        return []


def check_daily_loss_limit() -> tuple:
    """
    Check if today's closed trades exceeded loss limit.
    Returns (is_allowed: bool, amount: float, limit: float, reason: str)
    """
    today_trades = _get_daily_trades()
    
    total_loss = 0.0
    closed_count = 0
    
    for trade in today_trades:
        # trade is (id, ticket, type, volume, price, profit, status, time)
        status = trade[6]  # status column
        profit = trade[5]  # profit column
        
        if status == "closed":
            closed_count += 1
            if profit < 0:
                total_loss += abs(profit)
    
    if total_loss > MAX_DAILY_LOSS:
        reason = f"Daily loss limit exceeded: ${total_loss:.2f} / ${MAX_DAILY_LOSS:.2f}"
        logger.warning(reason)
        return (False, total_loss, MAX_DAILY_LOSS, reason)
    
    reason = f"Daily loss check OK: ${total_loss:.2f} / ${MAX_DAILY_LOSS:.2f} ({closed_count} closed)"
    logger.debug(reason)
    return (True, total_loss, MAX_DAILY_LOSS, reason)


def check_daily_trades_limit() -> tuple:
    """
    Check if max daily trades exceeded.
    Returns (is_allowed: bool, count: int, limit: int, reason: str)
    """
    today_trades = _get_daily_trades()
    
    trade_count = len(today_trades)
    
    if trade_count >= MAX_DAILY_TRADES:
        reason = f"Max daily trades reached: {trade_count} / {MAX_DAILY_TRADES}"
        logger.warning(reason)
        return (False, trade_count, MAX_DAILY_TRADES, reason)
    
    reason = f"Daily trades check OK: {trade_count} / {MAX_DAILY_TRADES}"
    logger.debug(reason)
    return (True, trade_count, MAX_DAILY_TRADES, reason)


def check_kill_switch() -> tuple:
    """
    Emergency kill switch: block trading if equity drawdown exceeds threshold.
    Returns (is_allowed: bool, drawdown_percent: float, threshold: float, reason: str)
    """
    acc = mt5.account_info()
    if acc is None:
        logger.error("check_kill_switch: account_info() returned None")
        return (True, 0.0, KILL_SWITCH_DRAWDOWN_PERCENT, "Account info unavailable")
    
    if acc.balance <= 0:
        logger.warning("check_kill_switch: balance <= 0")
        return (True, 0.0, KILL_SWITCH_DRAWDOWN_PERCENT, "Invalid account balance")
    
    drawdown_percent = ((acc.balance - acc.equity) / acc.balance) * 100.0
    
    if drawdown_percent > KILL_SWITCH_DRAWDOWN_PERCENT:
        reason = f"🚨 KILL SWITCH ACTIVATED: {drawdown_percent:.2f}% / {KILL_SWITCH_DRAWDOWN_PERCENT}% threshold"
        logger.critical(reason)
        return (False, drawdown_percent, KILL_SWITCH_DRAWDOWN_PERCENT, reason)
    
    reason = f"Kill switch OK: {drawdown_percent:.2f}% / {KILL_SWITCH_DRAWDOWN_PERCENT}%"
    logger.debug(reason)
    return (True, drawdown_percent, KILL_SWITCH_DRAWDOWN_PERCENT, reason)


def can_trade_safe() -> bool:
    """
    Master risk check: all risk gates must pass.
    Returns True if safe to trade, False otherwise.
    
    Also exported as functions with detailed returns for debugging:
    - check_kill_switch() -> (bool, drawdown, threshold, reason)
    - check_daily_loss_limit() -> (bool, amount, limit, reason)
    - check_daily_trades_limit() -> (bool, count, limit, reason)
    """
    
    # Check 1: Kill switch (highest priority)
    is_allowed, _, _, _ = check_kill_switch()
    if not is_allowed:
        return False
    
    # Check 2: Daily loss limit
    is_allowed, _, _, _ = check_daily_loss_limit()
    if not is_allowed:
        return False
    
    # Check 3: Daily trades limit
    is_allowed, _, _, _ = check_daily_trades_limit()
    if not is_allowed:
        return False
    
    return True


def get_risk_status() -> dict:
    """
    Get detailed risk status for debug output.
    Returns dict with all risk checks and their details.
    """
    kill_ok, drawdown, kill_threshold, _ = check_kill_switch()
    loss_ok, loss_amount, max_loss, _ = check_daily_loss_limit()
    trades_ok, trades_count, max_trades, _ = check_daily_trades_limit()
    
    return {
        "kill_switch_active": not kill_ok,
        "drawdown_percent": drawdown,
        "kill_switch_threshold": kill_threshold,
        "daily_loss_ok": loss_ok,
        "daily_loss_amount": loss_amount,
        "max_daily_loss": max_loss,
        "daily_trades_ok": trades_ok,
        "daily_trades": trades_count,
        "max_daily_trades": max_trades,
    }
