import MetaTrader5 as mt5
from bot.utils.config import SYMBOL


def connect() -> bool:
    if not mt5.initialize():
        print("MT5 INIT ERROR:", mt5.last_error())
        return False

    if not mt5.symbol_select(SYMBOL, True):
        print("SYMBOL SELECT FAILED:", SYMBOL)
        mt5.shutdown()
        return False

    print(f"MT5 CONNECTED | SYMBOL READY: {SYMBOL}")
    return True


def get_price():
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        return None
    return {"bid": tick.bid, "ask": tick.ask, "last": tick.last}


def shutdown():
    mt5.shutdown()
    print("MT5 SHUTDOWN")


def is_connected() -> bool:
    """
    Check if the MT5 terminal is alive and connected to a broker.
    FIX: mt5.ping() does not exist in the Python API — use terminal_info() instead.
    """
    try:
        info = mt5.terminal_info()
        return info is not None and info.connected
    except Exception:
        return False