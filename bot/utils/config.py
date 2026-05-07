# bot/utils/config.py

MT5_PATH = ""  # optional (leave empty if MT5 already installed normally)

LOGIN = 106477756
PASSWORD = "DvR@3sOx"
SERVER = "MetaQuotes-Demo"

SYMBOL = "XAUUSD"
TIMEFRAME = "M1"
STRATEGY = "momentum_scalp"  # options: "momentum_scalp", "structure" (disabled), "ema" (disabled)
 
# ─────────────────────────────────────────────────────────────────────────────
# RISK MANAGEMENT PARAMETERS
# ─────────────────────────────────────────────────────────────────────────────
 
# Dynamic lot sizing: risk this % of account per trade (e.g., 1.0 = 1%)
RISK_PERCENT = 1.0
 
# Minimum lot size (MT5-dependent, typically 0.01)
MIN_LOT = 0.01
 
# Maximum spread threshold in pips — increased for real XAUUSD broker conditions
# ECN brokers: 0.2–0.8 pips typical. Standard/STP brokers: 1.0–3.0 pips typical.
# Start at 2.0 to validate signals fire, then tighten once confirmed.
MAX_SPREAD = 2.0
 
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