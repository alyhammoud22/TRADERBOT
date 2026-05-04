import time
import logging

from bot.mt5_connector import connect, shutdown, is_connected
from bot.brain.brain_engine import make_trading_decision
from bot.brain.memory_engine import init_memory_schema
from bot.execution.trader import send_order, sync_profit
from bot.utils.config import validate_config
from bot.database.db import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    # ──────────────────────────────────────────────────────────────────────
    # INITIALIZATION
    # ──────────────────────────────────────────────────────────────────────
    
    # Validate config
    config_errors = validate_config()
    if config_errors:
        for err in config_errors:
            logger.warning(err)

    # Initialize database and memory schema
    init_db()
    init_memory_schema()

    print("🚀 XAUUSD Trading Bot — Production Grade")
    logger.info("Bot initialization started")

    # Connect to MT5
    if not connect():
        logger.critical("Initial MT5 connection failed. Exiting.")
        raise SystemExit(1)

    MAX_RECONNECT_ATTEMPTS = 5
    reconnect_attempts = 0

    try:
        while True:
            # ──────────────────────────────────────────────────────────────
            # CONNECTION CHECK
            # ──────────────────────────────────────────────────────────────
            if not is_connected():
                logger.warning("MT5 connection lost — attempting reconnect...")

                if reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
                    logger.critical("Max reconnect attempts reached. Shutting down.")
                    break

                if connect():
                    reconnect_attempts = 0
                    logger.info("Reconnected to MT5 successfully.")
                else:
                    reconnect_attempts += 1
                    logger.warning(
                        f"Reconnect attempt {reconnect_attempts}/{MAX_RECONNECT_ATTEMPTS} failed."
                    )
                    time.sleep(5)
                    continue

            # ──────────────────────────────────────────────────────────────
            # MAIN TRADING CYCLE
            # ──────────────────────────────────────────────────────────────
            try:
                # ── Brain Decision ────────────────────────────────────────
                decision = make_trading_decision()
                
                logger.debug(f"Decision: {decision.to_dict()}")
                
                # ── Execute if decision allows ────────────────────────────
                if decision.allow_trade and decision.signal != "NONE":
                    logger.info(
                        f"🎯 Trading signal: {decision.signal} | "
                        f"Confidence: {decision.confidence}% | "
                        f"Trend: {decision.context.trend}"
                    )
                    print(
                        f"🎯 Signal: {decision.signal} | "
                        f"Confidence: {decision.confidence}%"
                    )
                    
                    # Send order with strategy context
                    send_order(
                        decision.signal,
                        entry_reason=" | ".join(decision.reasons),
                        strategy=decision.strategy_used
                    )
                else:
                    reason = " | ".join(decision.reasons) if decision.reasons else "no signal"
                    logger.debug(f"Signal rejected: {reason}")
                
                # ── Profit Sync ───────────────────────────────────────────
                sync_profit()

            except Exception as exc:
                logger.error(f"Error in main loop: {exc}", exc_info=True)

            # Wait before next cycle
            time.sleep(60)

    except KeyboardInterrupt:
        print("\n⛔ Bot stopped by user")
        logger.info("Bot stopped by KeyboardInterrupt")

    finally:
        shutdown()
        logger.info("MT5 shutdown complete")