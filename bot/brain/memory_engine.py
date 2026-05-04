"""
Memory Engine — Trade and decision history with context.

Extends the trade DB with:
- Entry reason & market context
- Exit reason
- Strategy used
- Allows system learning from past decisions
"""

import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parent.parent.parent / "trades.db"
logger = logging.getLogger(__name__)


@contextmanager
def _get_conn():
    """Managed SQLite connection with WAL mode."""
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


def init_memory_schema():
    """Initialize memory-tracking columns in trades table."""
    with _get_conn() as conn:
        # Check if memory columns exist
        c = conn.cursor()
        c.execute("PRAGMA table_info(trades)")
        columns = {row[1] for row in c.fetchall()}
        
        # Add memory columns if missing
        if "entry_reason" not in columns:
            try:
                conn.execute("ALTER TABLE trades ADD COLUMN entry_reason TEXT")
                logger.info("Added entry_reason column")
            except Exception as e:
                logger.warning(f"entry_reason column creation: {e}")
        
        if "entry_context" not in columns:
            try:
                conn.execute("ALTER TABLE trades ADD COLUMN entry_context TEXT")
                logger.info("Added entry_context column")
            except Exception as e:
                logger.warning(f"entry_context column creation: {e}")
        
        if "exit_reason" not in columns:
            try:
                conn.execute("ALTER TABLE trades ADD COLUMN exit_reason TEXT")
                logger.info("Added exit_reason column")
            except Exception as e:
                logger.warning(f"exit_reason column creation: {e}")
        
        if "strategy_name" not in columns:
            try:
                conn.execute("ALTER TABLE trades ADD COLUMN strategy_name TEXT")
                logger.info("Added strategy_name column")
            except Exception as e:
                logger.warning(f"strategy_name column creation: {e}")


def log_trade_entry(ticket: int, signal_reason: str, context_str: str, strategy: str):
    """Log entry reason and market context for a trade."""
    try:
        with _get_conn() as conn:
            conn.execute(
                """
                UPDATE trades
                SET entry_reason = ?, entry_context = ?, strategy_name = ?
                WHERE ticket = ?
                """,
                (signal_reason, context_str, strategy, ticket)
            )
        logger.debug(f"Trade entry logged: ticket={ticket} strategy={strategy}")
    except Exception as exc:
        logger.error(f"log_trade_entry failed: {exc}")


def log_trade_exit(ticket: int, exit_reason: str):
    """Log exit reason for a trade."""
    try:
        with _get_conn() as conn:
            conn.execute(
                """
                UPDATE trades
                SET exit_reason = ?
                WHERE ticket = ?
                """,
                (exit_reason, ticket)
            )
        logger.debug(f"Trade exit logged: ticket={ticket} reason={exit_reason}")
    except Exception as exc:
        logger.error(f"log_trade_exit failed: {exc}")


def get_trade_memory(ticket: int) -> dict:
    """Retrieve full memory for a trade."""
    try:
        with _get_conn() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT entry_reason, entry_context, exit_reason, strategy_name, profit, status
                FROM trades
                WHERE ticket = ?
                """,
                (ticket,)
            )
            row = c.fetchone()
            if row:
                return {
                    "entry_reason": row[0],
                    "entry_context": row[1],
                    "exit_reason": row[2],
                    "strategy": row[3],
                    "profit": row[4],
                    "status": row[5],
                }
    except Exception as exc:
        logger.error(f"get_trade_memory failed: {exc}")
    
    return {}


def get_winning_trades(limit=50) -> list:
    """Get profitable closed trades for analysis."""
    try:
        with _get_conn() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT ticket, entry_reason, strategy_name, profit
                FROM trades
                WHERE status = 'closed' AND profit > 0
                ORDER BY time DESC
                LIMIT ?
                """,
                (limit,)
            )
            return c.fetchall()
    except Exception as exc:
        logger.error(f"get_winning_trades failed: {exc}")
    
    return []


def get_losing_trades(limit=50) -> list:
    """Get losing closed trades for analysis."""
    try:
        with _get_conn() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT ticket, entry_reason, strategy_name, profit
                FROM trades
                WHERE status = 'closed' AND profit < 0
                ORDER BY time DESC
                LIMIT ?
                """,
                (limit,)
            )
            return c.fetchall()
    except Exception as exc:
        logger.error(f"get_losing_trades failed: {exc}")
    
    return []


def get_trade_stats() -> dict:
    """Get performance statistics from closed trades."""
    try:
        with _get_conn() as conn:
            c = conn.cursor()
            
            # Total closed trades
            c.execute("SELECT COUNT(*) FROM trades WHERE status = 'closed'")
            total_closed = c.fetchone()[0]
            
            # Winning trades
            c.execute("SELECT COUNT(*) FROM trades WHERE status = 'closed' AND profit > 0")
            wins = c.fetchone()[0]
            
            # Losing trades
            c.execute("SELECT COUNT(*) FROM trades WHERE status = 'closed' AND profit < 0")
            losses = c.fetchone()[0]
            
            # Total P&L
            c.execute("SELECT SUM(profit) FROM trades WHERE status = 'closed'")
            total_pnl = c.fetchone()[0] or 0.0
            
            # Avg win / loss
            c.execute("SELECT AVG(profit) FROM trades WHERE status = 'closed' AND profit > 0")
            avg_win = c.fetchone()[0] or 0.0
            
            c.execute("SELECT AVG(profit) FROM trades WHERE status = 'closed' AND profit < 0")
            avg_loss = c.fetchone()[0] or 0.0
            
            return {
                "total_closed": total_closed,
                "wins": wins,
                "losses": losses,
                "win_rate": (wins / total_closed * 100) if total_closed > 0 else 0.0,
                "total_pnl": total_pnl,
                "avg_win": avg_win,
                "avg_loss": abs(avg_loss),
            }
    except Exception as exc:
        logger.error(f"get_trade_stats failed: {exc}")
    
    return {}
