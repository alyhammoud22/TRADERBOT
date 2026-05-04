import MetaTrader5 as mt5
import pandas as pd
from bot.utils.config import SYMBOL


def get_rates(n=100):
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, n)

    if rates is None:
        return None

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")

    return df


def get_positions():
    positions = mt5.positions_get(symbol=SYMBOL)

    if positions is None:
        return []

    return positions


def get_account():
    acc = mt5.account_info()

    if acc is None:
        return None

    return {
        "balance": acc.balance,
        "equity": acc.equity,
        "profit": acc.profit
    }