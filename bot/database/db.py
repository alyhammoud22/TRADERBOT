import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager

# Absolute path anchored to the project root (TradingBot/trades.db)
DB_PATH = Path(__file__).resolve().parent.parent.parent / "trades.db"

logger = logging.getLogger(__name__)


@contextmanager
def _get_conn():
    """
    Managed SQLite connection.
    - WAL journal mode: allows concurrent reads during writes (fixes dashboard lock).
    - Auto-commit on success, rollback on exception.
    - Always closes the connection.
    """
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize schema. Safe to call multiple times (idempotent)."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket  INTEGER UNIQUE,
                type    TEXT,
                volume  REAL,
                price   REAL,
                profit  REAL,
                status  TEXT DEFAULT 'open',
                time    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Schema migration: add status column to pre-existing databases
        c = conn.cursor()
        c.execute("PRAGMA table_info(trades)")
        columns = [row[1] for row in c.fetchall()]
        if "status" not in columns:
            try:
                conn.execute("ALTER TABLE trades ADD COLUMN status TEXT DEFAULT 'open'")
                logger.info("DB migration: added 'status' column")
            except Exception as exc:
                logger.warning(f"DB migration warning: {exc}")


def insert_trade(ticket, trade_type, volume, price, profit):
    """Insert a new trade. OR IGNORE prevents duplicates on the UNIQUE ticket."""
    try:
        with _get_conn() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO trades (ticket, type, volume, price, profit, status)
                VALUES (?, ?, ?, ?, ?, 'open')
                """,
                (ticket, trade_type, volume, price, profit),
            )
        logger.info(f"Trade inserted: ticket={ticket} type={trade_type} vol={volume}")
    except Exception as exc:
        logger.error(f"insert_trade failed (ticket={ticket}): {exc}")


def get_trades(limit: int = 500):
    """Return the most recent trades, newest first, capped at `limit` rows."""
    try:
        with _get_conn() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT * FROM trades ORDER BY time DESC LIMIT ?", (limit,)
            )
            return c.fetchall()
    except Exception as exc:
        logger.error(f"get_trades failed: {exc}")
        return []


def get_open_tickets() -> set:
    """
    Return the set of ticket IDs currently marked 'open' in the database.
    Used by sync_profit() to detect SL/TP auto-closes.
    """
    try:
        with _get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT ticket FROM trades WHERE status = 'open'")
            return {row[0] for row in c.fetchall()}
    except Exception as exc:
        logger.error(f"get_open_tickets failed: {exc}")
        return set()


def update_trade_profit(ticket, profit):
    """Update the floating P&L for an open position (does NOT change status)."""
    try:
        with _get_conn() as conn:
            conn.execute(
                "UPDATE trades SET profit=? WHERE ticket=?",
                (profit, ticket),
            )
        logger.debug(f"Profit synced: ticket={ticket} profit={profit:.2f}")
    except Exception as exc:
        logger.error(f"update_trade_profit failed (ticket={ticket}): {exc}")


def close_trade(ticket, profit):
    """Mark a trade as 'closed' with its final realized profit."""
    try:
        with _get_conn() as conn:
            conn.execute(
                "UPDATE trades SET profit=?, status='closed' WHERE ticket=?",
                (profit, ticket),
            )
        logger.info(f"Trade closed in DB: ticket={ticket} realized={profit:.2f}")
    except Exception as exc:
        logger.error(f"close_trade failed (ticket={ticket}): {exc}")