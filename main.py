import time
import logging

from bot.mt5_connector import connect, shutdown, is_connected
from bot.engine.strategy_engine import get_signal
from bot.execution.trader import send_order, sync_profit
from bot.execution.risk_engine import can_trade_safe, check_kill_switch
from bot.utils.config import STRATEGY, validate_config
from bot.database.db import init_db

# Single authoritative logging configuration for the entire process.
# trader.py and other modules use getLogger(__name__) — no basicConfig there.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    # ── Config validation ─────────────────────────────────────────────────
    config_errors = validate_config()
    if config_errors:
        for err in config_errors:
            logger.warning(err)

    # ── DB initialisation ─────────────────────────────────────────────────
    init_db()

    print("🚀 XAUUSD Bot Started")
    logger.info(f"Strategy: {STRATEGY}")

    # ── Initial MT5 connection ────────────────────────────────────────────
    if not connect():
        logger.critical("Initial MT5 connection failed. Exiting.")
        raise SystemExit(1)

    MAX_RECONNECT_ATTEMPTS = 5
    reconnect_attempts     = 0

    try:
        while True:
            # ── Connection guard ──────────────────────────────────────────
            if not is_connected():
                logger.warning("MT5 connection lost — attempting reconnect...")

                # FIX: was `> max` which allowed 6 attempts. Correct is `>=`.
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

            # ── Master Risk Check (Kill Switch) ───────────────────────────
            if not check_kill_switch():
                logger.critical("🚨 Kill switch triggered. STOPPING ALL TRADING.")
                print("🛑 EMERGENCY STOP - Kill switch active")
                break

            # ── Main trading cycle ────────────────────────────────────────
            try:
                signal = get_signal(STRATEGY)

                if signal:
                    logger.info(f"Signal: {signal}")
                    print(f"🎯 Signal: {signal}")
                    
                    # ── Pre-trade risk check ──────────────────────────────
                    if not can_trade_safe():
                        logger.warning(f"Signal {signal} blocked by risk engine")
                        print("⚠️  Signal blocked by risk management")
                    else:
                        send_order(signal)
                else:
                    print("⏳ No signal")

                sync_profit()

            except Exception as exc:
                logger.error(f"Error in main loop: {exc}", exc_info=True)

            time.sleep(60)

    except KeyboardInterrupt:
        print("\n⛔ Bot stopped by user")
        logger.info("Bot stopped by KeyboardInterrupt")

    finally:
        shutdown()
        logger.info("MT5 shutdown complete")