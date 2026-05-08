# bot/utils/config.py

MT5_PATH = ""  # optional (leave empty if MT5 already installed normally)

LOGIN = 106477756
PASSWORD = "DvR@3sOx"
SERVER = "MetaQuotes-Demo"

SYMBOL = "XAUUSD"
TIMEFRAME = "M1"
STRATEGY = "momentum_scalp"  # options: "momentum_scalp", "structure" (disabled), "ema" (disabled)

# TREND FILTER BYPASS
# -------------------
# When True  -> Step 5 (H1 trend alignment) is SKIPPED entirely.
#               Use during execution pipeline validation so you can confirm
#               trades open/close correctly before re-adding HTF filters.
# When False -> Normal: M1 signal must match H1 trend direction.
#
# WARNING: Set back to False before running with real money.
BYPASS_TREND_FILTER = True

# ─────────────────────────────────────────────────────────────────────────────
# RISK MANAGEMENT PARAMETERS
# ─────────────────────────────────────────────────────────────────────────────

# Dynamic lot sizing: risk this % of account per trade (e.g., 1.0 = 1%)
RISK_PERCENT = 0.01

# Minimum lot size (MT5-dependent, typically 0.01)
MIN_LOT = 0.01

# Maximum spread threshold in DOLLARS (ask - bid), NOT pips.
# XAUUSD spread is quoted in dollars, not pips. Using sym.point to divide
# produces absurd numbers (e.g. $0.17 spread → "17 pips"). Don't do that.
#
# Typical XAUUSD dollar spreads:
#   ECN / raw spread broker : $0.15 – $0.50  → set MAX_SPREAD = 0.80
#   Standard / STP broker   : $0.30 – $1.50  → set MAX_SPREAD = 2.00
#   During news events       : $1.00 – $5.00+ → bot will pause automatically
#
# Start at 3.0 to validate signals fire, then tighten once confirmed.
MAX_SPREAD = 3.0

# Daily loss limit: block trades if today's closed loss exceeds this amount ($)
MAX_DAILY_LOSS = 500.0

# Max simultaneous positions per day
MAX_DAILY_TRADES = 20

# Kill switch: stop trading if equity drops below this % of initial balance
KILL_SWITCH_DRAWDOWN_PERCENT = 5.0

# ─────────────────────────────────────────────────────────────────────────────
# MARKET FILTER PARAMETERS
# ─────────────────────────────────────────────────────────────────────────────

# Higher timeframe trend filter: use EMA50 on H1
HTF_PERIOD = 50

# ATR volatility filter thresholds (ratio to rolling mean)
ATR_LOW_VOL_THRESHOLD = 0.5      # Below this = too quiet, block
ATR_HIGH_VOL_THRESHOLD = 2.0     # Above this = too volatile, block

# Configuration validation
def validate_config():
    """Validate that critical config values are set"""
    errors = []
    
    if LOGIN == 0:
        errors.append("⚠️  LOGIN not configured")
    if not PASSWORD:
        errors.append("⚠️  PASSWORD not configured")
    if not SERVER:
        errors.append("⚠️  SERVER not configured")
    if STRATEGY not in ["momentum_scalp", "structure", "ema"]:
        errors.append(f"⚠️  Invalid STRATEGY: {STRATEGY}")
    
    return errors

# Check config on import
_errors = validate_config()
if _errors:
    import logging
    logger = logging.getLogger(__name__)
    for error in _errors:
        logger.warning(error)