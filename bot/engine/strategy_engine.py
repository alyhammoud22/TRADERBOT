from bot.strategy import ema, structure


def get_signal(strategy_name):

    if strategy_name == "ema":
        return ema.get_signal()

    if strategy_name == "structure":
        return structure.get_signal()

    return None