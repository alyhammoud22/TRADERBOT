# bot/utils/config.py

MT5_PATH = ""  # optional (leave empty if MT5 already installed normally)

LOGIN = 0
PASSWORD = ""
SERVER = ""

SYMBOL = "XAUUSD"
TIMEFRAME = "M1"
STRATEGY = "structure"  # options: "structure", "ema"

# ─────────────────────────────────────────────────────────────────────────────
# RISK MANAGEMENT PARAMETERS
# ─────────────────────────────────────────────────────────────────────────────

# Dynamic lot sizing: risk this % of account per trade (e.g., 1.0 = 1%)
RISK_PERCENT = 1.0

# Minimum lot size (MT5-dependent, typically 0.01)
MIN_LOT = 0.01

# Maximum spread threshold in pips (for XAUUSD, typically 0.1 pips = 1$ on standard)
MAX_SPREAD = 0.5

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
    if STRATEGY not in ["structure", "ema"]:
        errors.append(f"⚠️  Invalid STRATEGY: {STRATEGY}")
    
    return errors

# Check config on import
_errors = validate_config()
if _errors:
    import logging
    logger = logging.getLogger(__name__)
    for error in _errors:
        logger.warning(error)