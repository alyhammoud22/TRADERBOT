"""
Trading Brain Engine — Unified decision intelligence.

Combines all signals, market context, and risk checks into a single decision.
Returns structured decision with confidence and reasoning.
"""

import logging
from typing import Optional

from bot.brain.market_context import get_market_context, MarketContext
from bot.engine.strategy_engine import get_signal
from bot.execution.risk_engine import can_trade_safe, check_daily_loss_limit, check_daily_trades_limit, check_kill_switch, get_risk_status
from bot.utils.config import STRATEGY, BYPASS_TREND_FILTER
from bot.utils.debug import debug_log, debug_brain_decision, debug_rejection

logger = logging.getLogger(__name__)


class TradeDecision:
    """Structured trade decision with reasoning."""
    
    def __init__(self):
        self.signal: Optional[str] = None  # "BUY" | "SELL" | "NONE"
        self.confidence: int = 0  # 0-100
        self.allow_trade: bool = False
        self.reasons: list = []  # Why decision was made/rejected
        self.context: Optional[MarketContext] = None
        self.strategy_used: str = ""
    
    def __repr__(self):
        reason_text = " | ".join(self.reasons) if self.reasons else "no reasons"
        return (
            f"TradeDecision(signal={self.signal}, confidence={self.confidence}, "
            f"allow_trade={self.allow_trade}, [{reason_text}])"
        )
    
    def to_dict(self):
        """Convert to dictionary for logging."""
        return {
            "signal": self.signal,
            "confidence": self.confidence,
            "allow_trade": self.allow_trade,
            "reasons": self.reasons,
            "trend": self.context.trend if self.context else None,
            "volatility": self.context.volatility if self.context else None,
            "spread_pips": self.context.spread_pips if self.context else 0.0,
            "strategy": self.strategy_used,
        }


def make_trading_decision() -> TradeDecision:
    """
    Main brain decision logic.

    Returns: TradeDecision object with signal and reasoning.

    Flow:
    1. Get market context
    2. Spread gate
    3. Volatility gate
    4. Get strategy signal
    5. Trend validation
    6. Risk gate
    7. Confidence calculation
    8. Final approval
    """
    decision = TradeDecision()

    # === DEBUG HEADER =====================================================
    print("\n" + "=" * 68)
    print("  BRAIN ENGINE  ---  make_trading_decision() START")
    print("=" * 68)
    # ======================================================================

    # ------------------------------------------------------------------
    # STEP 1: MARKET CONTEXT
    # ------------------------------------------------------------------
    print("\n  [STEP 1]  Fetching market context...")
    try:
        ctx = get_market_context()
        decision.context = ctx
        print(f"  [STEP 1 PASS]  trend={ctx.trend}  |  vol={ctx.volatility}"
              f"  |  spread=${ctx.spread_pips:.4f}  |  session={ctx.session}")
    except Exception as exc:
        print(f"  [STEP 1 FAIL]  market_context raised exception: {exc}")
        logger.error(f"market_context failed: {exc}")
        decision.reasons.append(f"Market context error: {exc}")
        debug_rejection(f"Market context error: {exc}")
        return decision

    # ------------------------------------------------------------------
    # STEP 2: SPREAD CHECK
    # ------------------------------------------------------------------
    from bot.utils.config import MAX_SPREAD as _MAX_SPREAD
    print(f"\n  [STEP 2]  Spread check"
          f"  |  spread=${ctx.spread_pips:.4f}"
          f"  |  MAX_SPREAD=${_MAX_SPREAD}"
          f"  |  acceptable={ctx.spread_acceptable}")
    if not ctx.spread_acceptable:
        print(f"  [STEP 2 FAIL]  SPREAD GATE REJECTED  ---  bot returns here, strategy NOT called")
        decision.signal = "NONE"
        decision.confidence = 0
        decision.allow_trade = False
        decision.reasons.append(f"Spread too high (${ctx.spread_pips:.4f} USD)")
        logger.warning(f"Decision rejected: {decision}")
        debug_rejection(f"Spread too high: ${ctx.spread_pips:.4f} USD")
        return decision
    print(f"  [STEP 2 PASS]  Spread acceptable, continuing...")

    # ------------------------------------------------------------------
    # STEP 3: VOLATILITY CHECK
    # ------------------------------------------------------------------
    print(f"\n  [STEP 3]  Volatility check  |  volatility=\'{ctx.volatility}\'  |  need \'normal\'")
    if ctx.volatility == "low":
        print(f"  [STEP 3 FAIL]  VOLATILITY TOO LOW  ---  bot returns here, strategy NOT called")
        decision.signal = "NONE"
        decision.confidence = 0
        decision.allow_trade = False
        decision.reasons.append("Volatility too low")
        logger.warning(f"Decision rejected: {decision}")
        debug_rejection("Volatility too low", {"volatility": ctx.volatility})
        return decision
    if ctx.volatility == "high":
        print(f"  [STEP 3 FAIL]  VOLATILITY TOO HIGH  ---  bot returns here, strategy NOT called")
        decision.signal = "NONE"
        decision.confidence = 0
        decision.allow_trade = False
        decision.reasons.append("Volatility too high")
        logger.warning(f"Decision rejected: {decision}")
        debug_rejection("Volatility too high", {"volatility": ctx.volatility})
        return decision
    print(f"  [STEP 3 PASS]  Volatility normal, continuing...")

    # ------------------------------------------------------------------
    # STEP 4: CALL STRATEGY
    # ------------------------------------------------------------------
    print(f"\n  [STEP 4]  Calling strategy")
    print(f"  [STEP 4]  ACTIVE STRATEGY = \'{STRATEGY}\'")
    print(f"  [STEP 4]  >>> strategy_engine.get_signal(\'{STRATEGY}\') called NOW <<<")
    print(f"  [STEP 4]  momentum_scalp output begins:")
    print()
    try:
        raw_signal = get_signal(STRATEGY)
        decision.strategy_used = STRATEGY
        print()
        print(f"  [STEP 4]  strategy_engine returned: raw_signal = {raw_signal!r}")
    except Exception as exc:
        print(f"  [STEP 4 FAIL]  get_signal() raised exception: {exc}")
        logger.error(f"Strategy signal failed: {exc}")
        decision.reasons.append(f"Strategy error: {exc}")
        debug_rejection(f"Strategy error", {"error": str(exc)})
        return decision

    if raw_signal is None:
        print(f"  [STEP 4 DONE]  Strategy returned None --- no signal this candle")
        decision.signal = "NONE"
        decision.confidence = 0
        decision.allow_trade = False
        decision.reasons.append(f"No {STRATEGY} signal")
        logger.debug(f"No signal from {STRATEGY}")
        return decision

    print(f"  [STEP 4 PASS]  Signal received: {raw_signal}  ---  continuing...")
    decision.signal = raw_signal

    # ------------------------------------------------------------------
    # STEP 5: TREND VALIDATION  (bypassable via BYPASS_TREND_FILTER)
    # ------------------------------------------------------------------
    print(f"\n  [STEP 5]  Trend alignment"
          f"  |  signal={raw_signal}"
          f"  |  H1_trend=\'{ctx.trend}\'"
          f"  |  price={ctx.current_price:.3f}"
          f"  |  H1_EMA50={ctx.h1_ema50:.3f}"
          f"  |  BYPASS_TREND_FILTER={BYPASS_TREND_FILTER}")

    if BYPASS_TREND_FILTER:
        # Validation mode: skip HTF alignment check entirely so execution
        # pipeline can be verified. Re-enable before live trading.
        print(f"  [STEP 5 SKIP]  BYPASS_TREND_FILTER=True  ---  trend gate disabled, passing through")
        decision.reasons.append(f"Trend filter bypassed (validation mode) | H1={ctx.trend}")
    else:
        trend_aligned = False

        if raw_signal == "BUY" and ctx.trend == "bullish":
            trend_aligned = True
            decision.reasons.append("BUY aligned with bullish trend")
        elif raw_signal == "SELL" and ctx.trend == "bearish":
            trend_aligned = True
            decision.reasons.append("SELL aligned with bearish trend")
        elif ctx.trend == "sideways":
            if raw_signal == "BUY" and ctx.current_price > ctx.h1_ema50:
                trend_aligned = True
                decision.reasons.append("BUY above H1 EMA50 in sideways")
            elif raw_signal == "SELL" and ctx.current_price < ctx.h1_ema50:
                trend_aligned = True
                decision.reasons.append("SELL below H1 EMA50 in sideways")
            else:
                decision.reasons.append(f"Sideways: {raw_signal} not aligned with H1 EMA50")
        else:
            decision.reasons.append(f"{raw_signal} NOT aligned with {ctx.trend} trend")

        if not trend_aligned:
            print(f"  [STEP 5 FAIL]  TREND MISMATCH  |  signal={raw_signal}  H1_trend={ctx.trend}")
            decision.signal = "NONE"
            decision.confidence = 0
            decision.allow_trade = False
            logger.warning(f"Decision rejected: {decision}")
            debug_rejection(f"Signal NOT aligned with trend", {"signal": raw_signal, "trend": ctx.trend})
            return decision
        print(f"  [STEP 5 PASS]  Trend aligned, continuing...")

    # ------------------------------------------------------------------
    # STEP 6: RISK GATE
    # ------------------------------------------------------------------
    print(f"\n  [STEP 6]  Risk engine gate...")
    try:
        if not can_trade_safe():
            print(f"  [STEP 6 FAIL]  RISK ENGINE BLOCKED  ---  check kill switch / daily loss / trade count")
            decision.signal = "NONE"
            decision.confidence = 0
            decision.allow_trade = False
            decision.reasons.append("Risk engine gate rejected trade")
            logger.warning(f"Decision rejected: {decision}")
            debug_rejection("Risk engine check failed", {"reason": "One or more risk checks blocked trading"})
            return decision
        print(f"  [STEP 6 PASS]  Risk engine approved, continuing...")
    except Exception as exc:
        print(f"  [STEP 6 FAIL]  Risk engine raised exception: {exc}")
        logger.error(f"Risk engine check failed: {exc}")
        decision.reasons.append(f"Risk check error: {exc}")
        debug_rejection("Risk engine error", {"error": str(exc)})
        return decision

    # ------------------------------------------------------------------
    # STEP 7: CONFIDENCE CALCULATION
    # ------------------------------------------------------------------
    print(f"\n  [STEP 7]  Calculating confidence score...")
    confidence = 70

    if ctx.volatility == "normal":
        confidence += 10
        decision.reasons.append("Normal volatility regime")

    if ctx.session in ["london", "ny"]:
        confidence += 5
        decision.reasons.append(f"Good trading session: {ctx.session}")

    decision.confidence = min(100, confidence)
    print(f"  [STEP 7 DONE]  confidence={decision.confidence}%")

    # ------------------------------------------------------------------
    # STEP 8: FINAL APPROVAL
    # ------------------------------------------------------------------
    decision.allow_trade = True
    decision.reasons.append(f"Trade approved with {decision.confidence}% confidence")
    logger.info(f"Decision approved: {decision}")

    print(f"\n  [STEP 8 PASS]  *** TRADE APPROVED ***  signal={decision.signal}  confidence={decision.confidence}%")
    print("=" * 68 + "\n")

    debug_brain_decision(decision.signal, decision.confidence, decision.allow_trade, decision.reasons)

    return decision
