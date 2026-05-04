"""
Debug Trace System for Trading Bot
Provides colored, structured logging for real-time trade visibility
"""

from datetime import datetime
from typing import Dict, Any, Optional

# ANSI Color codes
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def debug_section(title: str, width: int = 80) -> None:
    """Print a section divider with title."""
    divider = "─" * (width - len(title) - 4)
    print(f"\n{Colors.CYAN}{divider} {title} {divider}{Colors.RESET}")


def debug_header(timestamp: Optional[datetime] = None, loop_id: str = "") -> None:
    """Print loop start header with timestamp."""
    if timestamp is None:
        timestamp = datetime.now()
    
    time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}")
    print(f"[LOOP START] {time_str} {loop_id}")
    print(f"{'='*80}{Colors.RESET}\n")


def debug_footer() -> None:
    """Print loop end footer."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}[LOOP END] {'='*78}{Colors.RESET}\n")


def debug_log(title: str, data_dict: Dict[str, Any], level: str = "INFO") -> None:
    """
    Print formatted debug block with key-value pairs.
    
    Args:
        title: Section title
        data_dict: Dictionary of key-value pairs to print
        level: "INFO" | "SUCCESS" | "WARNING" | "ERROR"
    """
    # Determine color based on level
    color_map = {
        "INFO": Colors.WHITE,
        "SUCCESS": Colors.GREEN,
        "WARNING": Colors.YELLOW,
        "ERROR": Colors.RED,
    }
    color = color_map.get(level, Colors.WHITE)
    
    print(f"{color}{Colors.BOLD}{title}:{Colors.RESET}")
    
    for key, value in data_dict.items():
        # Format value based on type
        if isinstance(value, bool):
            formatted_val = f"{Colors.GREEN}True{Colors.RESET}" if value else f"{Colors.RED}False{Colors.RESET}"
        elif isinstance(value, (int, float)) and isinstance(value, bool) is False:
            if isinstance(value, float):
                formatted_val = f"{value:.2f}"
            else:
                formatted_val = str(value)
        else:
            formatted_val = str(value)
        
        print(f"  • {key}: {formatted_val}")


def debug_market_context(trend: str, volatility: str, session: str, spread_pips: float, 
                         current_price: float = None) -> None:
    """Log market context info."""
    data = {
        "Trend": trend.upper(),
        "Volatility": volatility.upper(),
        "Session": session.upper(),
        "Spread": f"{spread_pips:.2f} pips",
    }
    if current_price:
        data["Price"] = f"{current_price:.5f}"
    
    debug_log("MARKET CONTEXT", data)


def debug_brain_decision(signal: str, confidence: int, allow_trade: bool, 
                        reasons: list) -> None:
    """Log brain engine decision."""
    signal_color = ""
    if signal == "BUY":
        signal_color = Colors.GREEN + signal + Colors.RESET
    elif signal == "SELL":
        signal_color = Colors.RED + signal + Colors.RESET
    else:
        signal_color = Colors.YELLOW + signal + Colors.RESET
    
    data = {
        "Signal": signal_color,
        "Confidence": f"{confidence}%",
        "Allow Trade": allow_trade,
    }
    
    debug_log("BRAIN DECISION", data, "INFO" if allow_trade else "WARNING")
    
    if reasons:
        print(f"\n{Colors.BOLD}REASONS:{Colors.RESET}")
        for i, reason in enumerate(reasons, 1):
            print(f"  {i}. {reason}")


def debug_risk_checks(kill_switch_active: bool, daily_loss_ok: bool, 
                     daily_trades_ok: bool, daily_loss_amount: float = None,
                     max_daily_loss: float = None, daily_trades: int = None,
                     max_daily_trades: int = None, drawdown_percent: float = None) -> None:
    """Log risk engine status."""
    data = {
        "Kill Switch": f"{Colors.RED}ACTIVE{Colors.RESET}" if kill_switch_active else f"{Colors.GREEN}OK{Colors.RESET}",
        "Daily Loss": f"{Colors.RED}BLOCKED{Colors.RESET}" if not daily_loss_ok else f"{Colors.GREEN}OK{Colors.RESET}",
        "Daily Trades": f"{Colors.RED}BLOCKED{Colors.RESET}" if not daily_trades_ok else f"{Colors.GREEN}OK{Colors.RESET}",
    }
    
    if daily_loss_amount is not None and max_daily_loss is not None:
        data["Loss Status"] = f"${daily_loss_amount:.2f} / ${max_daily_loss:.2f}"
    
    if daily_trades is not None and max_daily_trades is not None:
        data["Trades Today"] = f"{daily_trades} / {max_daily_trades}"
    
    if drawdown_percent is not None:
        data["Drawdown"] = f"{drawdown_percent:.2f}%"
    
    level = "SUCCESS" if (kill_switch_active is False and daily_loss_ok and daily_trades_ok) else "WARNING"
    debug_log("RISK ENGINE", data, level)


def debug_execution(order_type: str, lot: float, entry_price: float, 
                   sl: float, tp: float, reason: str = "") -> None:
    """Log order parameters before execution."""
    sl_dist = abs(entry_price - sl)
    tp_dist = abs(tp - entry_price)
    
    data = {
        "Order Type": f"{Colors.GREEN if order_type == 'BUY' else Colors.RED}{order_type}{Colors.RESET}",
        "Lot Size": f"{lot:.2f}",
        "Entry Price": f"{entry_price:.5f}",
        "Stop Loss": f"{sl:.5f} ({sl_dist:.5f} away)",
        "Take Profit": f"{tp:.5f} ({tp_dist:.5f} away)",
    }
    
    if reason:
        data["Reason"] = reason
    
    debug_log("EXECUTION PARAMETERS", data, "INFO")


def debug_execution_result(success: bool, ticket: Optional[int] = None, 
                          retcode: Optional[int] = None, comment: str = "", 
                          error_msg: str = "") -> None:
    """Log execution result."""
    if success:
        data = {
            "Status": f"{Colors.GREEN}✅ SUCCESS{Colors.RESET}",
            "Ticket": ticket,
            "Comment": comment if comment else "Trade opened successfully",
        }
        debug_log("EXECUTION RESULT", data, "SUCCESS")
    else:
        data = {
            "Status": f"{Colors.RED}❌ FAILED{Colors.RESET}",
            "Return Code": retcode,
            "Error": error_msg if error_msg else (comment if comment else "Unknown error"),
        }
        debug_log("EXECUTION RESULT", data, "ERROR")


def debug_rejection(reason: str, details: Dict[str, Any] = None) -> None:
    """Log why a trade was rejected."""
    print(f"\n{Colors.RED}{Colors.BOLD}❌ TRADE REJECTED{Colors.RESET}")
    print(f"{Colors.RED}Reason: {reason}{Colors.RESET}")
    
    if details:
        for key, value in details.items():
            print(f"  • {key}: {value}")


def debug_blocking_reason(check_name: str, reason: str) -> None:
    """Log a specific blocking reason."""
    print(f"  {Colors.RED}✗ {check_name}: {reason}{Colors.RESET}")


def format_time_elapsed(seconds: float) -> str:
    """Format elapsed time nicely."""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        minutes = int(seconds / 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
