# Debug Trace System — Implementation Complete ✅

## Overview
A full real-time debug trace system has been added to your trading bot. Now you can see EXACTLY why trades execute or are rejected at every step.

---

## 1. NEW DEBUG UTILITIES MODULE

**File:** `bot/utils/debug.py`

Created a comprehensive debug helper with:
- **Colored output** (GREEN/RED/YELLOW/CYAN) for terminal clarity
- **Structured logging functions** for clean output
- **Market context display**
- **Brain decision tracking**
- **Risk engine status visualization**
- **Execution logging** (parameters + results)
- **Rejection reasons** with details

### Key Functions:
```
debug_header(timestamp, loop_id)          → Print loop start
debug_footer()                             → Print loop end
debug_log(title, data_dict, level)        → Generic structured output
debug_market_context(...)                 → Market conditions
debug_brain_decision(...)                 → Decision + confidence
debug_risk_checks(...)                    → Risk engine status
debug_execution(...)                      → Order parameters
debug_execution_result(...)               → Success/failure
debug_rejection(reason, details)          → Trade rejection reasons
```

---

## 2. MAIN.PY LOOP — FULL DEBUG TRACE

**File:** `main.py`

The main trading loop now prints a complete trace for each iteration:

```
────────────────────────────────────────────────────────────────────────
[LOOP START] 2026-05-04 14:32:15
════════════════════════════════════════════════════════════════════════

──────────────────────────── MARKET STATE ────────────────────────────
MARKET CONTEXT:
  • Trend: BULLISH
  • Volatility: NORMAL
  • Session: LONDON
  • Spread: 1.50 pips
  • Price: 2345.67890

──────────────────────────── BRAIN DECISION ────────────────────────────
BRAIN DECISION:
  • Signal: BUY (green)
  • Confidence: 85%
  • Allow Trade: True

REASONS:
  1. BUY aligned with bullish trend
  2. Normal volatility regime
  3. Good trading session: london
  4. Trade approved with 85% confidence

──────────────────────────── RISK ENGINE ────────────────────────────────
RISK ENGINE:
  • Kill Switch: ✅ OK (green)
  • Daily Loss: ✅ OK (green)
  • Daily Trades: ✅ OK (green)
  • Loss Status: $0.00 / $500.00
  • Trades Today: 1 / 5
  • Drawdown: 2.15%

──────────────────────────── EXECUTION ────────────────────────────────
EXECUTION PARAMETERS:
  • Order Type: BUY (green)
  • Lot Size: 0.10
  • Entry Price: 2345.67890
  • Stop Loss: 2330.67890 (15.00000 away)
  • Take Profit: 2360.67890 (15.00000 away)
  • Reason: BUY aligned with bullish trend | Normal volatility regime

EXECUTION RESULT:
  • Status: ✅ SUCCESS (green)
  • Ticket: 123456789
  • Comment: BUY at 2345.67890

──────────────────────────── HOUSEKEEPING ────────────────────────────
Profit sync completed

[LOOP END] ════════════════════════════════════════════════════════════
```

---

## 3. BRAIN ENGINE — DEBUG DECISION TRACE

**File:** `bot/brain/brain_engine.py`

Added imports:
```python
from bot.utils.debug import (
    debug_log, 
    debug_brain_decision, 
    debug_rejection
)
```

Now when a decision is made:

1. **If APPROVED**: Prints colored decision block with:
   - Signal (BUY/SELL/NONE with color)
   - Confidence percentage
   - Reason chain (why it passed all gates)

2. **If REJECTED**: Prints rejection reason at each gate:
   - Spread too high
   - Volatility too low/high
   - No strategy signal
   - Signal NOT aligned with trend
   - Risk engine blocked it

Example rejection output:
```
❌ TRADE REJECTED
Reason: Signal NOT aligned with trend
  • signal: SELL
  • trend: bullish
```

---

## 4. RISK ENGINE — DETAILED STATUS REPORTING

**File:** `bot/execution/risk_engine.py`

**Changed functions to return tuples with details:**

```python
# OLD: Returns bool
check_kill_switch() -> bool

# NEW: Returns detailed tuple
check_kill_switch() -> tuple
    (is_allowed: bool, drawdown: float, threshold: float, reason: str)

check_daily_loss_limit() -> tuple
    (is_allowed: bool, amount: float, limit: float, reason: str)

check_daily_trades_limit() -> tuple
    (is_allowed: bool, count: int, limit: int, reason: str)
```

**New function:**
```python
get_risk_status() -> dict
```
Returns full risk status for debug output:
```python
{
    "kill_switch_active": False,
    "drawdown_percent": 2.15,
    "kill_switch_threshold": 5.0,
    "daily_loss_ok": True,
    "daily_loss_amount": 0.00,
    "max_daily_loss": 500.00,
    "daily_trades_ok": True,
    "daily_trades": 1,
    "max_daily_trades": 5,
}
```

**Master function updated:**
```python
can_trade_safe() -> bool
```
Still returns simple bool, but internally uses the new tuple functions.
Now works seamlessly with the debug system.

---

## 5. TRADER — EXECUTION LOGGING

**File:** `bot/execution/trader.py`

**Added imports:**
```python
from bot.utils.debug import (
    debug_execution, 
    debug_execution_result, 
    debug_rejection,
    debug_risk_checks,
)
```

**Before send_order():**
1. Gets full risk status
2. Prints risk engine check with colors
3. Shows each rejection reason with ✗ mark

**Example risk block:**
```
RISK ENGINE:
  • Kill Switch: ✅ OK
  • Daily Loss: ✅ OK
  • Daily Trades: ✅ OK
  • Loss Status: $0.00 / $500.00
  • Trades Today: 1 / 5
  • Drawdown: 2.15%
```

**Before order submission:**
Prints order parameters:
```
EXECUTION PARAMETERS:
  • Order Type: BUY
  • Lot Size: 0.10
  • Entry Price: 2345.67890
  • Stop Loss: 2330.67890 (15.00000 away)
  • Take Profit: 2360.67890 (15.00000 away)
  • Reason: [entry reason here]
```

**After execution attempt:**
Shows result with ticket or error:
```
✅ SUCCESS (green)
  • Status: ✅ SUCCESS
  • Ticket: 123456789
  • Comment: BUY at 2345.67890
```

OR on failure:
```
❌ FAILED (red)
  • Status: ❌ FAILED
  • Return Code: 10011
  • Error: [MT5 error message]
```

---

## 6. COLOR SYSTEM

Terminal output uses ANSI colors:

- **GREEN** (`\033[92m`) → Success, OK, allowed
- **RED** (`\033[91m`) → Failed, blocked, error
- **YELLOW** (`\033[93m`) → Warning
- **CYAN** (`\033[96m`) → Section headers
- **BLUE** (`\033[94m`) → Loop start/end
- **BOLD** (`\033[1m`) → Emphasis

Supported on:
- ✅ Windows Terminal (modern)
- ✅ Linux/Mac terminals
- ✅ Most modern terminals with ANSI support

---

## 7. USAGE EXAMPLE

Run the bot normally:
```bash
python main.py
```

You'll now see:
1. **Loop header** with timestamp
2. **Market conditions** (trend, volatility, session, spread)
3. **Brain decision** (signal, confidence, reasons)
4. **Risk engine status** (kill switch, daily loss, daily trades)
5. **Execution details** (parameters) OR rejection reasons
6. **Execution result** (success with ticket OR failure with error)
7. **Loop footer**

All happens in real time for each bot cycle!

---

## 8. KEY FEATURES

✅ **NO TRADING LOGIC CHANGES** — Only added debug visibility
✅ **Structured output** — Easy to read, no spam
✅ **Color-coded** — Instant visual feedback
✅ **Full trace** — See every decision point
✅ **Rejection tracking** — Know EXACTLY why trades don't execute
✅ **Risk visibility** — Kill switch, daily loss, trade limits all shown
✅ **Reusable helpers** — `debug_log()`, `debug_execution()`, etc.
✅ **Clean code** — Follows bot conventions

---

## 9. TROUBLESHOOTING

**Q: Colors not showing?**
A: Install `colorama` on Windows:
```bash
pip install colorama
```
Or just accept the ANSI codes (they work in most terminals).

**Q: Too much output?**
A: Adjust logging level in main.py:
```python
logging.basicConfig(level=logging.WARNING)  # Hide debug logs
```

**Q: Need to see even more?**
A: Each module logs to logger, check `logs/` folder or terminal output.

---

## 10. INTEGRATION CHECKLIST

- ✅ `bot/utils/debug.py` created
- ✅ `main.py` loop updated with headers/footers/market display
- ✅ `brain_engine.py` imports debug + prints decisions
- ✅ `risk_engine.py` functions return detailed tuples
- ✅ `trader.py` imports debug + prints execution flow
- ✅ All rejection paths have debug output
- ✅ Color support enabled (fallback to text if needed)

---

## Summary

You now have **complete real-time visibility** into:
1. Why each trading decision was made (or rejected)
2. Why each trade executed (or why it was blocked)
3. Current market conditions and risk status
4. Exact order parameters and results

All with **clean, colored, structured output** that's easy to read and follow!

Time to debug like a pro. 🚀
