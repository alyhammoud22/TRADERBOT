# 🚀 Quick Start Guide — Debug Trace System

**Time to read:** 2 minutes  
**Time to use:** 1 command

---

## What You Got

A **complete debug trace system** showing exactly why trades execute or fail in real-time.

---

## Files You Need to Know About

### Implementation Files (5)
1. ✅ `bot/utils/debug.py` — Debug utilities (NEW)
2. ✅ `main.py` — Main loop with trace (MODIFIED)
3. ✅ `bot/brain/brain_engine.py` — Decision logging (MODIFIED)
4. ✅ `bot/execution/risk_engine.py` — Risk status (MODIFIED)
5. ✅ `bot/execution/trader.py` — Execution trace (MODIFIED)

### Documentation Files (6)
1. 📖 `DEBUG_TRACE_SYSTEM.md` — System overview
2. 📖 `CODE_SNIPPETS_REFERENCE.md` — Copy-paste examples
3. 📖 `IMPLEMENTATION_SUMMARY.md` — Technical details
4. 📖 `VISUAL_OUTPUT_EXAMPLES.md` — Output examples (8 scenarios)
5. 📖 `COMPLETE_IMPLEMENTATION_GUIDE.md` — Full guide
6. 📖 `BEFORE_AND_AFTER.md` — Comparison
7. 📖 `QUICK_START_GUIDE.md` ← You are here

---

## How to Use It

### 1. Run Your Bot
```bash
python main.py
```

That's it! Debug output automatically starts.

### 2. Watch the Output

You'll see something like:

```
════════════════════════════════════════════════════════════════════════
[LOOP START] 2026-05-04 14:32:15

MARKET STATE
  • Trend: BULLISH
  • Volatility: NORMAL
  • Session: LONDON
  • Spread: 1.50 pips

BRAIN DECISION
  • Signal: ✅ BUY
  • Confidence: 85%
  • Allow Trade: ✅ True

EXECUTION PARAMETERS
  • Order Type: ✅ BUY
  • Lot Size: 0.10
  • Entry: 2345.67890
  • SL: 2330.67890
  • TP: 2360.67890

EXECUTION RESULT
  ✅ SUCCESS - Ticket: 123456789

[LOOP END] ════════════════════════════════════════════════════════════
```

### 3. Understand the Output

**Color meanings:**
- 🟢 **GREEN** = Success, OK, passed
- 🔴 **RED** = Failed, blocked, error
- 🟡 **YELLOW** = Warning
- 🔵 **BLUE** = Section markers

**Sections you see:**
1. **[LOOP START]** — Start of trading cycle
2. **MARKET STATE** — Current market conditions
3. **BRAIN DECISION** — What signal was generated
4. **EXECUTION** — Order parameters or rejection reason
5. **HOUSEKEEPING** — Profit sync
6. **[LOOP END]** — End of cycle

---

## Key Info You'll See

### Market State
```
MARKET CONTEXT:
  • Trend: bullish/bearish/sideways
  • Volatility: low/normal/high
  • Session: asia/london/ny
  • Spread: X.XX pips
```
⚠️ **High spread?** → Your trades might get rejected

### Brain Decision
```
BRAIN DECISION:
  • Signal: BUY / SELL / NONE
  • Confidence: 0-100%
  • Allow Trade: True / False
```
❓ **No signal?** → Check REASONS list below

### Risk Engine
```
RISK ENGINE:
  • Kill Switch: ✅ OK  or  ❌ ACTIVE
  • Daily Loss: ✅ OK  or  ❌ BLOCKED
  • Daily Trades: ✅ OK  or  ❌ BLOCKED
```
🚨 **Kill Switch ACTIVE?** → Drawdown too high, trading paused

### Execution Parameters
```
EXECUTION PARAMETERS:
  • Order Type: BUY / SELL
  • Lot Size: X.XX
  • Entry Price: XXXXX.XXXXX
  • Stop Loss: XXXXX.XXXXX
  • Take Profit: XXXXX.XXXXX
```
💡 **Review before order goes out** → Catch mistakes early

### Execution Result
```
EXECUTION RESULT:
  • Status: ✅ SUCCESS  or  ❌ FAILED
  • Ticket: 123456789
  • Comment: BUY at 2345.67890
```
✅ **SUCCESS?** → Trade is live, check your platform

### Rejection Reason
```
❌ TRADE REJECTED
Reason: Daily loss limit exceeded: $515 / $500
```
📊 **Not executing?** → Here's exactly why

---

## Debugging Tips

### "My trade never executes"

1. **Check BRAIN DECISION**
   - Signal: BUY/SELL? Or NONE?
   - If NONE, check REASONS list

2. **Check EXECUTION section**
   - Risk checks passing? (all ✅)
   - Or seeing rejection reason?

3. **Common reasons for rejection:**
   - ❌ Spread too high
   - ❌ Volatility too low
   - ❌ Kill switch active
   - ❌ Daily loss limit hit
   - ❌ Daily trades limit hit
   - ❌ Signal not aligned with trend

### "My trade executed but I didn't expect it"

1. **Check BRAIN DECISION REASONS**
   - Does it make sense?
   - All reasons listed?

2. **Check MARKET STATE**
   - Trend really bullish/bearish?
   - Volatility in range?

3. **Check EXECUTION PARAMETERS**
   - Lot size reasonable?
   - SL/TP appropriate?

### "I want to adjust my trading"

Watch the debug output for patterns:
- Always rejected on **high volatility**? → Lower your vol threshold
- Daily losses **keep hitting limit**? → Adjust max daily loss config
- **Kill switch activating**? → Tighter money management needed
- **Spreads always high**? → Use different broker/session

---

## One-Minute Understanding

The debug system prints **one complete trading cycle** per loop.

In order, you see:
1. **What's happening in market** (MARKET STATE)
2. **What brain decided** (BRAIN DECISION)
3. **What risk engine allows** (RISK ENGINE)
4. **What order would be placed** (EXECUTION PARAMETERS)
5. **What actually happened** (EXECUTION RESULT or REJECTION)

All **color-coded** and **easy to read**.

---

## Configuration Tips

### If output is too fast
Edit `main.py`, add sleep:
```python
time.sleep(1)  # Add at end of loop
```

### If you want less output
Edit `main.py`, change logging level:
```python
logging.basicConfig(level=logging.WARNING)  # Hide DEBUG logs
```

### If colors don't show on Windows
Use **Windows Terminal** (built-in, modern ANSI support)  
Or install: `pip install colorama`

---

## Documentation Order

Read these in order:

1. **This file** (2 min) — You are here
2. **VISUAL_OUTPUT_EXAMPLES.md** (5 min) — See 8 example scenarios
3. **CODE_SNIPPETS_REFERENCE.md** (10 min) — Copy-paste examples
4. **COMPLETE_IMPLEMENTATION_GUIDE.md** (15 min) — Full reference
5. **BEFORE_AND_AFTER.md** (10 min) — See the transformation

---

## What Changed in Your Code

### ✅ NO trading logic changed
- Same buy/sell signals
- Same risk calculations
- Same order execution

### ✅ ONLY added debug output
- Print statements
- Structured formatting
- Color codes

### ✅ 100% backward compatible
- No breaking changes
- Safe to deploy
- Can remove later if needed

---

## Your Next Action

```bash
python main.py
```

Run this ONE command and watch your trading cycle with full debug visibility.

That's all you need to do!

---

## Quick Reference

| Problem | Solution |
|---------|----------|
| Can't see output | Use Windows Terminal or enable colorama |
| Output too fast | Add time.sleep(1) before loop end |
| Too much output | Change logging level to WARNING |
| Want specific info | Read CODE_SNIPPETS_REFERENCE.md |
| Need to understand | Read VISUAL_OUTPUT_EXAMPLES.md |

---

## Pro Tips

1. **Monitor the "Drawdown %" in RISK ENGINE**
   - Tells you how close to kill switch
   - Drawdown > 5% = trading stops

2. **Watch "Loss Status" and "Trades Today"**
   - $X / $500 = how much loss allowed today
   - X / 5 = how many trades allowed today

3. **Check REASONS under BRAIN DECISION**
   - Explains why signal was approved
   - Good for understanding your strategy

4. **Take screenshots of unusual patterns**
   - Save for later analysis
   - Spot recurring issues

---

## You're Ready! 🎉

Start your bot with debug trace:
```bash
python main.py
```

You now have **professional-grade visibility** into your trading bot.

**Enjoy debugging!** 🚀

---

## Need Help?

- 📖 **Understanding output?** → Read VISUAL_OUTPUT_EXAMPLES.md
- 💻 **Copying functions?** → Read CODE_SNIPPETS_REFERENCE.md
- 🔧 **Technical details?** → Read COMPLETE_IMPLEMENTATION_GUIDE.md
- 🔄 **Before/after?** → Read BEFORE_AND_AFTER.md

All documentation is in your TradingBot folder.

---

**Happy trading with full debug visibility!** 🌟
