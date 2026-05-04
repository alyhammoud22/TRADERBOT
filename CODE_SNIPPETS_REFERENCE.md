# Debug Trace System — Code Reference

Quick reference for the debug functions and how to use them.

---

## Debug Helpers in bot/utils/debug.py

### 1. Basic Printing Functions

```python
# Print a section divider
debug_section("MARKET STATE")  
# Output: ──── MARKET STATE ────

# Print loop start (with timestamp)
debug_header(timestamp=datetime.now(), loop_id="CYCLE_1")

# Print loop end
debug_footer()
```

### 2. Generic Structured Logging

```python
debug_log(
    title="RISK ENGINE",
    data_dict={
        "Kill Switch": "✅ OK",
        "Daily Loss": "$0.00 / $500.00",
        "Daily Trades": "1 / 5",
    },
    level="INFO"  # "INFO", "SUCCESS", "WARNING", "ERROR"
)
```

### 3. Market Context Display

```python
debug_market_context(
    trend="bullish",
    volatility="normal", 
    session="london",
    spread_pips=1.50,
    current_price=2345.678
)
```

### 4. Brain Decision Display

```python
debug_brain_decision(
    signal="BUY",              # or "SELL" or "NONE"
    confidence=85,             # 0-100
    allow_trade=True,          # bool
    reasons=[                  # list of reason strings
        "BUY aligned with bullish trend",
        "Normal volatility regime",
        "Good trading session: london",
        "Trade approved with 85% confidence"
    ]
)
```

### 5. Risk Engine Status

```python
debug_risk_checks(
    kill_switch_active=False,
    daily_loss_ok=True,
    daily_trades_ok=True,
    daily_loss_amount=0.00,
    max_daily_loss=500.00,
    daily_trades=1,
    max_daily_trades=5,
    drawdown_percent=2.15
)
```

### 6. Execution Parameters

```python
debug_execution(
    order_type="BUY",
    lot=0.10,
    entry_price=2345.67890,
    sl=2330.67890,
    tp=2360.67890,
    reason="BUY signal with bullish trend"
)
```

### 7. Execution Result

```python
# On SUCCESS:
debug_execution_result(
    success=True,
    ticket=123456789,
    comment="BUY at 2345.67890"
)

# On FAILURE:
debug_execution_result(
    success=False,
    retcode=10011,
    error_msg="Volume exceeded — rejected"
)
```

### 8. Rejection Reason

```python
debug_rejection(
    reason="Spread too high",
    details={
        "current_spread": 3.50,
        "max_allowed": 2.00,
        "excess": 1.50
    }
)
```

---

## Integration Examples

### In Brain Engine (brain_engine.py)

```python
from bot.utils.debug import debug_brain_decision, debug_rejection

def make_trading_decision():
    # ... decision logic ...
    
    if not trend_aligned:
        decision.signal = "NONE"
        decision.allow_trade = False
        logger.warning(f"Decision rejected: {decision}")
        
        # ADD THIS:
        debug_rejection(
            f"Signal NOT aligned with trend",
            {"signal": raw_signal, "trend": ctx.trend}
        )
        return decision
    
    # ... more logic ...
    
    # Before returning approved decision:
    debug_brain_decision(
        decision.signal,
        decision.confidence,
        decision.allow_trade,
        decision.reasons
    )
    
    return decision
```

### In Risk Engine (risk_engine.py)

```python
# NEW: Functions return (is_allowed, value1, value2, reason_string)

def check_daily_loss_limit() -> tuple:
    today_trades = _get_daily_trades()
    total_loss = 0.0
    
    for trade in today_trades:
        if trade[6] == "closed" and trade[5] < 0:
            total_loss += abs(trade[5])
    
    if total_loss > MAX_DAILY_LOSS:
        reason = f"Daily loss limit exceeded: ${total_loss:.2f} / ${MAX_DAILY_LOSS:.2f}"
        return (False, total_loss, MAX_DAILY_LOSS, reason)
    
    reason = f"Daily loss check OK: ${total_loss:.2f} / ${MAX_DAILY_LOSS:.2f}"
    return (True, total_loss, MAX_DAILY_LOSS, reason)


# NEW: Helper to get all risk status
def get_risk_status() -> dict:
    kill_ok, drawdown, kill_thresh, _ = check_kill_switch()
    loss_ok, loss_amt, max_loss, _ = check_daily_loss_limit()
    trades_ok, trades_ct, max_trades, _ = check_daily_trades_limit()
    
    return {
        "kill_switch_active": not kill_ok,
        "drawdown_percent": drawdown,
        "kill_switch_threshold": kill_thresh,
        "daily_loss_ok": loss_ok,
        "daily_loss_amount": loss_amt,
        "max_daily_loss": max_loss,
        "daily_trades_ok": trades_ok,
        "daily_trades": trades_ct,
        "max_daily_trades": max_trades,
    }


# Updated to work with new tuple returns
def can_trade_safe() -> bool:
    is_allowed, _, _, _ = check_kill_switch()
    if not is_allowed:
        return False
    
    is_allowed, _, _, _ = check_daily_loss_limit()
    if not is_allowed:
        return False
    
    is_allowed, _, _, _ = check_daily_trades_limit()
    if not is_allowed:
        return False
    
    return True
```

### In Trader (trader.py)

```python
from bot.utils.debug import (
    debug_execution,
    debug_execution_result,
    debug_rejection,
    debug_risk_checks,
)
from bot.execution.risk_engine import get_risk_status

def send_order(order_type, lot=None, sl_points=None, ...):
    
    # DEBUG: Print risk status
    risk_status = get_risk_status()
    debug_risk_checks(
        kill_switch_active=risk_status["kill_switch_active"],
        daily_loss_ok=risk_status["daily_loss_ok"],
        daily_trades_ok=risk_status["daily_trades_ok"],
        daily_loss_amount=risk_status["daily_loss_amount"],
        max_daily_loss=risk_status["max_daily_loss"],
        daily_trades=risk_status["daily_trades"],
        max_daily_trades=risk_status["max_daily_trades"],
        drawdown_percent=risk_status["drawdown_percent"],
    )
    
    # ... validation checks ...
    
    if not can_trade_safe():
        logger.warning("Trade blocked: risk engine check failed")
        debug_rejection("Risk engine check failed - Master gate")
        return None
    
    # ... more validation ...
    
    # DEBUG: Print order parameters before submission
    debug_execution(
        order_type=order_type,
        lot=lot,
        entry_price=price,
        sl=sl,
        tp=tp,
        reason=entry_reason if entry_reason else strategy
    )
    
    # ... submit order ...
    result = mt5.order_send(request)
    
    # DEBUG: Print result
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        debug_execution_result(
            success=True,
            ticket=result.order,
            comment=f"{order_type} at {price:.5f}"
        )
    else:
        debug_execution_result(
            success=False,
            retcode=result.retcode,
            error_msg=result.comment
        )
    
    return result
```

### In Main Loop (main.py)

```python
from bot.utils.debug import (
    debug_header,
    debug_footer,
    debug_section,
    debug_market_context,
)

while True:
    try:
        # LOOP START with timestamp
        loop_timestamp = datetime.now()
        debug_header(timestamp=loop_timestamp)
        
        # Get decision from brain
        decision = make_trading_decision()
        
        # DEBUG: Show market conditions
        if decision.context:
            debug_section("MARKET STATE")
            debug_market_context(
                trend=decision.context.trend,
                volatility=decision.context.volatility,
                session=decision.context.session,
                spread_pips=decision.context.spread_pips,
                current_price=decision.context.current_price,
            )
        
        # BRAIN DECISION already prints via debug_brain_decision()
        
        # Execute if approved
        if decision.allow_trade and decision.signal != "NONE":
            debug_section("EXECUTION")
            send_order(
                decision.signal,
                entry_reason=" | ".join(decision.reasons),
                strategy=decision.strategy_used
            )
            # send_order() prints execution details via debug_execution()
            # and debug_execution_result()
        else:
            debug_section("EXECUTION")
            print(f"⏭️  No trade this cycle")
        
        # Housekeeping
        debug_section("HOUSEKEEPING")
        sync_profit()
        
        # LOOP END
        debug_footer()
        
    except Exception as exc:
        logger.error(f"Main loop error: {exc}", exc_info=True)
        debug_footer()
```

---

## Color System

Colors are defined in debug.py Colors class:

```python
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
```

Use in custom debug output:
```python
print(f"{Colors.GREEN}✅ SUCCESS{Colors.RESET}")
print(f"{Colors.RED}❌ FAILED{Colors.RESET}")
print(f"{Colors.YELLOW}⚠️  WARNING{Colors.RESET}")
```

---

## Output Examples

### Trade Approved Loop
```
════════════════════════════════════════════════════════════════════════
[LOOP START] 2026-05-04 14:32:15
════════════════════════════════════════════════════════════════════════

──── MARKET STATE ────
MARKET CONTEXT:
  • Trend: BULLISH
  • Volatility: NORMAL
  • Session: LONDON
  • Spread: 1.50 pips
  • Price: 2345.67890

──── BRAIN DECISION ────
BRAIN DECISION:
  • Signal: ✅ BUY
  • Confidence: 85%
  • Allow Trade: ✅ True

REASONS:
  1. BUY aligned with bullish trend
  2. Normal volatility regime
  3. Good trading session: london
  4. Trade approved with 85% confidence

──── EXECUTION ────
RISK ENGINE:
  • Kill Switch: ✅ OK
  • Daily Loss: ✅ OK
  • Daily Trades: ✅ OK
  • Drawdown: 2.15%

EXECUTION PARAMETERS:
  • Order Type: ✅ BUY
  • Lot Size: 0.10
  • Entry Price: 2345.67890
  • Stop Loss: 2330.67890
  • Take Profit: 2360.67890

EXECUTION RESULT:
  • Status: ✅ SUCCESS
  • Ticket: 123456789
  • Comment: BUY at 2345.67890

[LOOP END] ════════════════════════════════════════════════════════════
```

### Trade Rejected (Risk Check)
```
════════════════════════════════════════════════════════════════════════
[LOOP START] 2026-05-04 14:33:15
════════════════════════════════════════════════════════════════════════

──── MARKET STATE ────
MARKET CONTEXT:
  • Trend: BULLISH
  • Volatility: NORMAL
  • Session: LONDON
  • Spread: 1.50 pips

──── EXECUTION ────
RISK ENGINE:
  • Kill Switch: ❌ ACTIVE
  • Daily Loss: ❌ BLOCKED
  • Daily Trades: ✅ OK
  • Drawdown: 5.50%

❌ TRADE REJECTED
Reason: Risk engine check failed - Master gate

[LOOP END] ════════════════════════════════════════════════════════════
```

---

## Quick Start Checklist

- ✅ Import debug functions at module top
- ✅ Call `debug_header()` at loop start
- ✅ Call `debug_footer()` at loop end  
- ✅ Call `debug_section()` before each major section
- ✅ Print market context after getting decision
- ✅ Brain engine calls `debug_brain_decision()` on approval or `debug_rejection()` on failure
- ✅ Risk engine returns tuples with detail, use `get_risk_status()` in trader
- ✅ Trader calls `debug_execution()` before order and `debug_execution_result()` after
- ✅ All rejections call `debug_rejection()` with reason + details

Done! Your bot now has full debug visibility. 🚀
