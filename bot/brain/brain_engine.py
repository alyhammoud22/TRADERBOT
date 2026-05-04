"""
Trading Brain Engine — Unified decision intelligence.

Combines all signals, market context, and risk checks into a single decision.
Returns structured decision with confidence and reasoning.
"""

import logging
from typing import Optional

from bot.brain.market_context import get_market_context, MarketContext
from bot.engine.strategy_engine import get_signal
from bot.execution.risk_engine import can_trade_safe
from bot.utils.config import STRATEGY

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
    2. Check risk gates
    3. Get strategy signal
    4. Validate signal against context
    5. Calculate confidence
    6. Return final decision
    """
    decision = TradeDecision()
    
    # ───────────────────────────────────────────────────────────────────────
    # 1. MARKET CONTEXT
    # ───────────────────────────────────────────────────────────────────────
    try:
        ctx = get_market_context()
        decision.context = ctx
    except Exception as exc:
        logger.error(f"market_context failed: {exc}")
        decision.reasons.append(f"Market context error: {exc}")
        return decision
    
    # ───────────────────────────────────────────────────────────────────────
    # 2. SPREAD CHECK (earliest gate)
    # ───────────────────────────────────────────────────────────────────────
    if not ctx.spread_acceptable:
        decision.signal = "NONE"
        decision.confidence = 0
        decision.allow_trade = False
        decision.reasons.append(f"Spread too high ({ctx.spread_pips:.2f}pips)")
        logger.warning(f"Decision rejected: {decision}")
        return decision
    
    # ───────────────────────────────────────────────────────────────────────
    # 3. VOLATILITY CHECK
    # ───────────────────────────────────────────────────────────────────────
    if ctx.volatility == "low":
        decision.signal = "NONE"
        decision.confidence = 0
        decision.allow_trade = False
        decision.reasons.append("Volatility too low — no quality signal")
        logger.warning(f"Decision rejected: {decision}")
        return decision
    
    if ctx.volatility == "high":
        decision.signal = "NONE"
        decision.confidence = 0
        decision.allow_trade = False
        decision.reasons.append("Volatility too high — too risky")
        logger.warning(f"Decision rejected: {decision}")
        return decision
    
    # ───────────────────────────────────────────────────────────────────────
    # 4. GET STRATEGY SIGNAL
    # ───────────────────────────────────────────────────────────────────────
    try:
        raw_signal = get_signal(STRATEGY)
        decision.strategy_used = STRATEGY
    except Exception as exc:
        logger.error(f"Strategy signal failed: {exc}")
        decision.reasons.append(f"Strategy error: {exc}")
        return decision
    
    if raw_signal is None:
        decision.signal = "NONE"
        decision.confidence = 0
        decision.allow_trade = False
        decision.reasons.append(f"No {STRATEGY} signal")
        return decision
    
    decision.signal = raw_signal
    
    # ───────────────────────────────────────────────────────────────────────
    # 5. TREND VALIDATION
    # ───────────────────────────────────────────────────────────────────────
    trend_aligned = False
    
    if raw_signal == "BUY" and ctx.trend == "bullish":
        trend_aligned = True
        decision.reasons.append("BUY aligned with bullish trend")
    elif raw_signal == "SELL" and ctx.trend == "bearish":
        trend_aligned = True
        decision.reasons.append("SELL aligned with bearish trend")
    elif ctx.trend == "sideways":
        # In sideways, only accept if H1 price clearly on right side of EMA50
        if raw_signal == "BUY" and ctx.current_price > ctx.h1_ema50:
            trend_aligned = True
            decision.reasons.append("BUY above H1 EMA50 in sideways")
        elif raw_signal == "SELL" and ctx.current_price < ctx.h1_ema50:
            trend_aligned = True
            decision.reasons.append("SELL below H1 EMA50 in sideways")
        else:
            decision.reasons.append(f"Sideways trend, {raw_signal} not aligned with H1 EMA50")
    else:
        decision.reasons.append(f"{raw_signal} NOT aligned with {ctx.trend} trend")
    
    if not trend_aligned:
        decision.signal = "NONE"
        decision.confidence = 0
        decision.allow_trade = False
        logger.warning(f"Decision rejected: {decision}")
        return decision
    
    # ───────────────────────────────────────────────────────────────────────
    # 6. RISK GATE
    # ───────────────────────────────────────────────────────────────────────
    try:
        if not can_trade_safe():
            decision.signal = "NONE"
            decision.confidence = 0
            decision.allow_trade = False
            decision.reasons.append("Risk engine gate rejected trade")
            logger.warning(f"Decision rejected: {decision}")
            return decision
    except Exception as exc:
        logger.error(f"Risk engine check failed: {exc}")
        decision.reasons.append(f"Risk check error: {exc}")
        return decision
    
    # ───────────────────────────────────────────────────────────────────────
    # 7. CALCULATE CONFIDENCE
    # ───────────────────────────────────────────────────────────────────────
    confidence = 70  # Base confidence for aligned signal
    
    # Volatility bonus (normal = preferred)
    if ctx.volatility == "normal":
        confidence += 10
        decision.reasons.append("Normal volatility regime")
    
    # Session bonus (some sessions perform better)
    if ctx.session in ["london", "ny"]:
        confidence += 5
        decision.reasons.append(f"Good trading session: {ctx.session}")
    
    decision.confidence = min(100, confidence)
    
    # ───────────────────────────────────────────────────────────────────────
    # 8. FINAL DECISION
    # ───────────────────────────────────────────────────────────────────────
    decision.allow_trade = True
    decision.reasons.append(f"Trade approved with {decision.confidence}% confidence")
    
    logger.info(f"Decision approved: {decision}")
    
    return decision
