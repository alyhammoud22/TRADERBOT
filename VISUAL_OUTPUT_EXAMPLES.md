# Debug Trace Output — Visual Examples

This document shows what you'll see in the terminal when running the bot with the debug trace system.

---

## SCENARIO 1: Trade Approved & Executed Successfully

```
════════════════════════════════════════════════════════════════════════
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
  • Signal: ✅ BUY [GREEN]
  • Confidence: 85%
  • Allow Trade: ✅ True [GREEN]

REASONS:
  1. BUY aligned with bullish trend
  2. Normal volatility regime
  3. Good trading session: london
  4. Trade approved with 85% confidence

──────────────────────────── EXECUTION ────────────────────────────────
RISK ENGINE:
  • Kill Switch: ✅ OK [GREEN]
  • Daily Loss: ✅ OK [GREEN]
  • Daily Trades: ✅ OK [GREEN]
  • Loss Status: $0.00 / $500.00
  • Trades Today: 1 / 5
  • Drawdown: 2.15%

EXECUTION PARAMETERS:
  • Order Type: ✅ BUY [GREEN]
  • Lot Size: 0.10
  • Entry Price: 2345.67890
  • Stop Loss: 2330.67890 (15.00000 away)
  • Take Profit: 2360.67890 (15.00000 away)
  • Reason: BUY aligned with bullish trend | Normal volatility regime | 
            Good trading session: london

🎯 Signal: BUY | Confidence: 85%
✅ TRADE OPENED: BUY ticket=123456789

EXECUTION RESULT:
  • Status: ✅ SUCCESS [GREEN]
  • Ticket: 123456789
  • Comment: BUY at 2345.67890

──────────────────────────── HOUSEKEEPING ────────────────────────────
Profit sync completed

[LOOP END] ════════════════════════════════════════════════════════════
```

---

## SCENARIO 2: Trade Rejected – Spread Too High

```
════════════════════════════════════════════════════════════════════════
[LOOP START] 2026-05-04 14:33:00
════════════════════════════════════════════════════════════════════════

──────────────────────────── MARKET STATE ────────────────────────────
MARKET CONTEXT:
  • Trend: BULLISH
  • Volatility: NORMAL
  • Session: LONDON
  • Spread: 3.50 pips [HIGH]
  • Price: 2346.12345

──────────────────────────── BRAIN DECISION ────────────────────────────
❌ TRADE REJECTED [RED]
Reason: Spread too high: 3.50 pips
  • spread_pips: 3.50
  • max_allowed: 2.00

──────────────────────────── EXECUTION ────────────────────────────────
⏭️  No trade this cycle: Spread too high — exceeds maximum threshold

[LOOP END] ════════════════════════════════════════════════════════════
```

---

## SCENARIO 3: Trade Rejected – Risk Engine (Kill Switch Active)

```
════════════════════════════════════════════════════════════════════════
[LOOP START] 2026-05-04 14:34:30
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
  • Signal: ✅ BUY [GREEN]
  • Confidence: 85%
  • Allow Trade: ✅ True [GREEN]

REASONS:
  1. BUY aligned with bullish trend
  2. Normal volatility regime
  3. Good trading session: london
  4. Trade approved with 85% confidence

──────────────────────────── EXECUTION ────────────────────────────────
RISK ENGINE:
  • Kill Switch: ❌ ACTIVE [RED]
  • Daily Loss: ✅ OK [GREEN]
  • Daily Trades: ✅ OK [GREEN]
  • Loss Status: $125.50 / $500.00
  • Trades Today: 2 / 5
  • Drawdown: 5.50%

❌ TRADE REJECTED [RED]
Reason: Risk engine check failed - Master gate
  • reason: Kill switch activated due to 5.50% drawdown

⏭️  No trade this cycle: Risk engine check failed...

──────────────────────────── HOUSEKEEPING ────────────────────────────
Profit sync completed

[LOOP END] ════════════════════════════════════════════════════════════
```

---

## SCENARIO 4: Trade Rejected – Daily Loss Limit Exceeded

```
════════════════════════════════════════════════════════════════════════
[LOOP START] 2026-05-04 14:35:45
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
  • Signal: ✅ BUY [GREEN]
  • Confidence: 85%
  • Allow Trade: ✅ True [GREEN]

REASONS:
  1. BUY aligned with bullish trend
  2. Normal volatility regime
  3. Good trading session: london
  4. Trade approved with 85% confidence

──────────────────────────── EXECUTION ────────────────────────────────
RISK ENGINE:
  • Kill Switch: ✅ OK [GREEN]
  • Daily Loss: ❌ BLOCKED [RED]
  • Daily Trades: ✅ OK [GREEN]
  • Loss Status: $515.00 / $500.00 [EXCEEDED BY $15.00]
  • Trades Today: 4 / 5
  • Drawdown: 2.15%

❌ TRADE REJECTED [RED]
Reason: Risk engine check failed - Master gate
  • reason: Daily loss limit exceeded: $515.00 / $500.00

⏭️  No trade this cycle: Daily loss limit exceeded...

──────────────────────────── HOUSEKEEPING ────────────────────────────
Profit sync completed

[LOOP END] ════════════════════════════════════════════════════════════
```

---

## SCENARIO 5: No Signal From Strategy

```
════════════════════════════════════════════════════════════════════════
[LOOP START] 2026-05-04 14:36:20
════════════════════════════════════════════════════════════════════════

──────────────────────────── MARKET STATE ────────────────────────────
MARKET CONTEXT:
  • Trend: SIDEWAYS
  • Volatility: NORMAL
  • Session: LONDON
  • Spread: 1.50 pips
  • Price: 2345.67890

──────────────────────────── BRAIN DECISION ────────────────────────────
BRAIN DECISION:
  • Signal: NONE [YELLOW]
  • Confidence: 0%
  • Allow Trade: ❌ False [RED]

REASONS:
  1. No EMA signal

❌ TRADE REJECTED [RED]
Reason: Strategy error
  • error: No signal from EMA strategy

──────────────────────────── EXECUTION ────────────────────────────────
⏭️  No trade this cycle: No EMA signal...

──────────────────────────── HOUSEKEEPING ────────────────────────────
Profit sync completed

[LOOP END] ════════════════════════════════════════════════════════════
```

---

## SCENARIO 6: Signal NOT Aligned With Trend

```
════════════════════════════════════════════════════════════════════════
[LOOP START] 2026-05-04 14:37:10
════════════════════════════════════════════════════════════════════════

──────────────────────────── MARKET STATE ────────────────────────────
MARKET CONTEXT:
  • Trend: BEARISH
  • Volatility: NORMAL
  • Session: LONDON
  • Spread: 1.50 pips
  • Price: 2345.67890

──────────────────────────── BRAIN DECISION ────────────────────────────
BRAIN DECISION:
  • Signal: NONE [YELLOW]
  • Confidence: 0%
  • Allow Trade: ❌ False [RED]

REASONS:
  1. BUY signal generated
  2. BUY NOT aligned with BEARISH trend

❌ TRADE REJECTED [RED]
Reason: Signal NOT aligned with trend
  • signal: BUY
  • trend: bearish

──────────────────────────── EXECUTION ────────────────────────────────
⏭️  No trade this cycle: BUY NOT aligned with bearish trend...

──────────────────────────── HOUSEKEEPING ────────────────────────────
Profit sync completed

[LOOP END] ════════════════════════════════════════════════════════════
```

---

## SCENARIO 7: Volatility Too Low

```
════════════════════════════════════════════════════════════════════════
[LOOP START] 2026-05-04 14:38:40
════════════════════════════════════════════════════════════════════════

──────────────────────────── MARKET STATE ────────────────────────────
MARKET CONTEXT:
  • Trend: BULLISH
  • Volatility: LOW [YELLOW]
  • Session: LONDON
  • Spread: 1.50 pips
  • Price: 2345.67890

──────────────────────────── BRAIN DECISION ────────────────────────────
BRAIN DECISION:
  • Signal: NONE [YELLOW]
  • Confidence: 0%
  • Allow Trade: ❌ False [RED]

REASONS:
  1. Volatility too low — no quality signal

❌ TRADE REJECTED [RED]
Reason: Volatility too low
  • volatility: LOW
  • requirement: NORMAL or HIGH

──────────────────────────── EXECUTION ────────────────────────────────
⏭️  No trade this cycle: Volatility too low...

──────────────────────────── HOUSEKEEPING ────────────────────────────
Profit sync completed

[LOOP END] ════════════════════════════════════════════════════════════
```

---

## SCENARIO 8: Execution Failure (MT5 Error)

```
════════════════════════════════════════════════════════════════════════
[LOOP START] 2026-05-04 14:39:55
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
  • Signal: ✅ BUY [GREEN]
  • Confidence: 85%
  • Allow Trade: ✅ True [GREEN]

REASONS:
  1. BUY aligned with bullish trend
  2. Normal volatility regime
  3. Good trading session: london
  4. Trade approved with 85% confidence

──────────────────────────── EXECUTION ────────────────────────────────
RISK ENGINE:
  • Kill Switch: ✅ OK [GREEN]
  • Daily Loss: ✅ OK [GREEN]
  • Daily Trades: ✅ OK [GREEN]
  • Loss Status: $0.00 / $500.00
  • Trades Today: 1 / 5
  • Drawdown: 2.15%

EXECUTION PARAMETERS:
  • Order Type: ✅ BUY [GREEN]
  • Lot Size: 0.10
  • Entry Price: 2345.67890
  • Stop Loss: 2330.67890 (15.00000 away)
  • Take Profit: 2360.67890 (15.00000 away)
  • Reason: BUY aligned with bullish trend

EXECUTION RESULT:
  • Status: ❌ FAILED [RED]
  • Return Code: 10011
  • Error: TRADE_RETCODE_INVALID_VOLUME

⏭️  No trade this cycle: Order volume rejected by broker...

──────────────────────────── HOUSEKEEPING ────────────────────────────
Profit sync completed

[LOOP END] ════════════════════════════════════════════════════════════
```

---

## Key Color Meanings

| Color | Meaning | Examples |
|-------|---------|----------|
| 🟢 GREEN | Success, OK, Allowed | ✅ BUY, ✅ True, Daily Loss OK, Kill Switch OK |
| 🔴 RED | Failed, Blocked, Error | ❌ SELL, ❌ False, Kill Switch ACTIVE, Trade REJECTED |
| 🟡 YELLOW | Warning, Needs Attention | LOW volatility, SIDEWAYS trend, HIGH spread |
| 🔵 BLUE | Loop start/end markers | [LOOP START], [LOOP END] |
| 🟦 CYAN | Section headers | MARKET STATE, BRAIN DECISION, EXECUTION |

---

## Real-Time Debugging Benefits

✅ **See EXACTLY why each decision is made**
✅ **Know IMMEDIATELY if a trade fails**
✅ **Understand rejection chain** (spread → trend → risk engine)
✅ **Monitor risk status live** (drawdown, daily loss, trade count)
✅ **Verify order parameters** before they're sent
✅ **No more guessing** — everything is visible

---

## Terminal Setup Tips

**Windows:**
- Use **Windows Terminal** (modern, full ANSI support)
- Or Git Bash terminal (also has ANSI support)

**Linux/Mac:**
- Standard terminal works perfectly

**If colors don't show:**
- You can still see the output (just without colors)
- Or install `colorama`: `pip install colorama`

---

## Performance Note

The debug system adds:
- ~2-5ms per loop for text formatting
- Negligible impact on overall bot performance
- All heavy lifting is in the trading logic, not debug output

---

**You now have enterprise-grade visibility into your trading bot!** 🚀
