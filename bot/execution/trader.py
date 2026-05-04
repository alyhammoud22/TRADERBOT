import MetaTrader5 as mt5
import time
import logging
from datetime import datetime, timedelta, timezone

from bot.utils.config import SYMBOL
from bot.database.db import (
    insert_trade,
    update_trade_profit,
    close_trade,
    get_open_tickets,
)
from bot.brain.memory_engine import log_trade_entry, log_trade_exit
from bot.execution.risk_engine import calculate_dynamic_lot, can_trade_safe
from bot.execution.execution_manager import (
    calculate_sl_tp_from_atr,
    validate_execution,
    manage_open_trades,
)

# Module logger
logger = logging.getLogger(__name__)

# Risk management constants
MAX_TRADES = 1
COOLDOWN_SECONDS = 300
ORDER_RETRY_ATTEMPTS = 2

_last_trade_time: float = 0.0


# =============================================================================
# GUARDS
# =============================================================================

def can_trade() -> bool:
    """Check cooldown and position cap."""
    global _last_trade_time

    elapsed = time.time() - _last_trade_time
    if elapsed < COOLDOWN_SECONDS:
        remaining = int(COOLDOWN_SECONDS - elapsed)
        logger.warning(f"Trade blocked: cooldown active ({remaining}s remaining)")
        return False

    positions = mt5.positions_get(symbol=SYMBOL)
    open_count = len(positions) if positions else 0

    if open_count >= MAX_TRADES:
        logger.warning(f"Trade blocked: position cap reached ({open_count}/{MAX_TRADES})")
        return False

    return True


def is_trading_allowed() -> bool:
    """Block new entries if drawdown > 5%."""
    acc = mt5.account_info()
    if acc is None:
        logger.error("is_trading_allowed: account_info() returned None")
        return False

    if acc.balance > 0 and acc.equity < acc.balance * 0.95:
        logger.error(
            f"Drawdown limit hit — equity={acc.equity:.2f}, balance={acc.balance:.2f}"
        )
        return False

    return True


def _check_spread(tick) -> bool:
    """Check if spread is within limits."""
    if tick is None:
        return False
    
    from bot.utils.config import MAX_SPREAD
    
    sym = mt5.symbol_info(SYMBOL)
    if sym is None:
        return False
    
    spread = tick.ask - tick.bid
    point = sym.point
    spread_pips = spread / point if point > 0 else 0
    
    if spread_pips > MAX_SPREAD:
        logger.warning(f"Spread too high: {spread_pips:.2f} pips / {MAX_SPREAD} threshold")
        return False
    
    logger.debug(f"Spread check: {spread_pips:.2f} pips (OK)")
    return True


# =============================================================================
# ORDER EXECUTION WITH RETRY
# =============================================================================

def send_order(order_type: str, lot: float = None, sl_points: int = None, 
               tp_points: int = None, entry_reason: str = "", strategy: str = ""):
    """
    Send market order with ATR-based SL/TP and full validation.
    
    Includes:
    - Risk engine checks
    - Execution validation (slippage, price freshness)
    - Retry logic (2 attempts)
    - Memory logging (entry reason, strategy)
    
    Args:
        order_type: "BUY" | "SELL"
        lot: Optional lot size (auto-calculated if None)
        sl_points: Optional SL in points (ATR-based if None)
        tp_points: Optional TP in points (ATR-based if None)
        entry_reason: Why this trade was entered (for memory)
        strategy: Which strategy generated signal (for memory)
    """
    global _last_trade_time

    logger.info(f"Trade attempt | {order_type} | reason={entry_reason}")

    # ── Risk Engine Master Check ──────────────────────────────────────────
    if not can_trade_safe():
        logger.warning("Trade blocked: risk engine check failed")
        return None

    if not can_trade():
        return None

    if not is_trading_allowed():
        return None

    # ── Get live price ────────────────────────────────────────────────────
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        logger.error("send_order: symbol_info_tick returned None")
        return None

    # ── Spread Check ──────────────────────────────────────────────────────
    if not _check_spread(tick):
        logger.warning("Trade blocked: spread too high")
        return None

    price = tick.ask if order_type == "BUY" else tick.bid

    sym = mt5.symbol_info(SYMBOL)
    if sym is None:
        logger.error("send_order: symbol_info returned None")
        return None

    point = sym.point

    # ── Calculate SL/TP from ATR if not provided ──────────────────────────
    if sl_points is None or tp_points is None:
        sl_points, tp_points = calculate_sl_tp_from_atr()
    
    # ── Calculate dynamic lot if not provided ──────────────────────────────
    if lot is None:
        lot = calculate_dynamic_lot(sl_points)
    
    logger.info(f"Trade params | {order_type} | lot={lot:.2f} | SL={sl_points}pts | TP={tp_points}pts")

    # ── Execution Validation ──────────────────────────────────────────────
    if not validate_execution(order_type, price):
        logger.warning("Trade blocked: execution validation failed")
        return None

    # ── SL / TP Calculation ───────────────────────────────────────────────
    if order_type == "BUY":
        sl = price - sl_points * point
        tp = price + tp_points * point
        if sl >= price or tp <= price:
            logger.error(f"Invalid SL/TP for BUY: price={price} sl={sl} tp={tp}")
            return None
    else:
        sl = price + sl_points * point
        tp = price - tp_points * point
        if sl <= price or tp >= price:
            logger.error(f"Invalid SL/TP for SELL: price={price} sl={sl} tp={tp}")
            return None

    logger.info(f"Order params: {order_type} price={price:.5f} sl={sl:.5f} tp={tp:.5f}")

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": lot,
        "type": mt5.ORDER_TYPE_BUY if order_type == "BUY" else mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": 123456,
        "comment": "XAU BOT",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    # ── Order Send with Retry ─────────────────────────────────────────────
    result = None
    for attempt in range(ORDER_RETRY_ATTEMPTS):
        result = mt5.order_send(request)
        
        if result is None:
            logger.error(f"order_send attempt {attempt+1}: returned None")
            if attempt < ORDER_RETRY_ATTEMPTS - 1:
                time.sleep(0.5)
            continue
        
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            break
        else:
            logger.warning(f"order_send attempt {attempt+1}: retcode={result.retcode} comment={result.comment}")
            if attempt < ORDER_RETRY_ATTEMPTS - 1:
                time.sleep(0.5)
    
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.error(f"Trade FAILED after {ORDER_RETRY_ATTEMPTS} attempts")
        return result

    # ── Trade Success ─────────────────────────────────────────────────────
    logger.info(f"Trade OPENED: ticket={result.order} | {order_type} | price={price:.5f}")
    print(f"✅ TRADE OPENED: {order_type} ticket={result.order}")

    insert_trade(result.order, order_type, lot, price, 0)
    
    # Log entry reason and strategy to memory
    if entry_reason or strategy:
        log_trade_entry(result.order, entry_reason, "", strategy)
    
    _last_trade_time = time.time()

    return result


# =============================================================================
# POSITION MANAGEMENT
# =============================================================================

def close_all_positions():
    """Close all open positions with proper profit tracking."""
    positions = mt5.positions_get(symbol=SYMBOL)
    if not positions:
        logger.info("close_all_positions: no open positions")
        return

    for pos in positions:
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick is None:
            logger.error(f"close_all_positions: no tick data for ticket={pos.ticket}")
            continue

        order_type = mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY
        price = tick.bid if pos.type == 0 else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": SYMBOL,
            "volume": pos.volume,
            "type": order_type,
            "position": pos.ticket,
            "price": price,
            "deviation": 20,
            "magic": 123456,
            "comment": "Close Trade",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)

        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Failed to close ticket={pos.ticket}: {result}")
            continue

        # Get realized profit from deal history
        realized = _get_realized_profit(pos.ticket)
        close_trade(pos.ticket, realized)
        log_trade_exit(pos.ticket, "emergency_close")
        logger.info(f"Closed ticket={pos.ticket} | realized={realized:.2f}")


# =============================================================================
# PROFIT SYNC & MANAGEMENT
# =============================================================================

def _get_realized_profit(position_ticket: int) -> float:
    """Get actual realized profit from MT5 deal history."""
    from_dt = datetime.now(timezone.utc) - timedelta(hours=48)
    to_dt = datetime.now(timezone.utc) + timedelta(hours=1)
    try:
        deals = mt5.history_deals_get(from_dt, to_dt, position=position_ticket)
        if deals:
            return sum(d.profit for d in deals)
    except Exception as exc:
        logger.warning(f"_get_realized_profit failed (ticket={position_ticket}): {exc}")
    return 0.0


def sync_profit():
    """
    Sync P&L, detect SL/TP closes, manage break-even and trailing stops.
    Called every loop cycle (60s).
    """
    positions = mt5.positions_get(symbol=SYMBOL)

    if positions is None:
        logger.warning("sync_profit: positions_get returned None")
        return

    live_tickets = {pos.ticket for pos in positions}

    # Update floating P&L for live positions
    for pos in positions:
        update_trade_profit(pos.ticket, pos.profit)
        logger.debug(f"Synced floating P&L: ticket={pos.ticket} profit={pos.profit:.2f}")

    # Detect SL/TP auto-closes
    db_open = get_open_tickets()
    for ticket in db_open - live_tickets:
        realized = _get_realized_profit(ticket)
        close_trade(ticket, realized)
        log_trade_exit(ticket, "sl_tp_close")
        logger.info(f"SL/TP close detected: ticket={ticket} realized={realized:.2f}")
    
    # Manage break-even and trailing stops
    manage_open_trades()