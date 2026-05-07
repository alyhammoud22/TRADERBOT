"""
strategy_engine.py — Signal Router
====================================

Routes the brain_engine's strategy request to the correct strategy module.
Each strategy must expose:

    def get_signal() -> "BUY" | "SELL" | None

To switch strategy:
  1. Change STRATEGY = "momentum_scalp" in bot/utils/config.py
  2. No other file needs to change.

Strategy Status
---------------
  momentum_scalp  ✅  ACTIVE   — EMA + Momentum + Candle Strength (M1 scalping)
  ema             💤  DISABLED — EMA10/50 crossover (kept for reference, do not delete)
  structure       💤  DISABLED — Higher Highs / Lower Lows (kept for reference, do not delete)
"""

# Active import
from bot.strategy import momentum_scalp

# Preserved imports — disabled but NOT deleted
# Uncomment and add to routing dict below to re-enable either strategy.
# from bot.strategy import ema
# from bot.strategy import structure


def get_signal(strategy_name: str):
    """
    Route to the named strategy and return its signal.

    Args:
        strategy_name: Must match a key in the routing table below.

    Returns:
        "BUY" | "SELL" | None
    """

    # ── Active strategy ───────────────────────────────────────────────────
    if strategy_name == "momentum_scalp":
        return momentum_scalp.get_signal()

    # ── Disabled strategies (preserved, not deleted) ──────────────────────
    # if strategy_name == "ema":
    #     return ema.get_signal()
    #
    # if strategy_name == "structure":
    #     return structure.get_signal()

    # ── Unknown strategy name ─────────────────────────────────────────────
    import logging
    logging.getLogger(__name__).error(
        f"strategy_engine: unknown strategy '{strategy_name}'. "
        f"Available: 'momentum_scalp'. "
        f"Check STRATEGY setting in bot/utils/config.py."
    )
    return None