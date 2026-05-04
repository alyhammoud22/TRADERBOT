import MetaTrader5 as mt5
import time
from datetime import datetime

SYMBOL = "XAUUSD"
LOT = 0.01
DEVIATION = 20


# ---------------------------
# CONNECT MT5
# ---------------------------
def connect():
    if not mt5.initialize():
        print("❌ MT5 init failed")
        return False

    info = mt5.terminal_info()
    if info is None:
        print("❌ No terminal info")
        return False

    print("✅ MT5 Connected")
    return True


# ---------------------------
# OPEN TRADE
# ---------------------------
def open_trade():
    tick = mt5.symbol_info_tick(SYMBOL)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": LOT,
        "type": mt5.ORDER_TYPE_BUY,
        "price": tick.ask,
        "deviation": DEVIATION,
        "magic": 123456,
        "comment": "LIVE_TEST",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print("❌ Order failed:", result.retcode)
        return None

    print(f"✅ Trade opened | ticket: {result.order}")
    return result.order


# ---------------------------
# GET POSITION
# ---------------------------
def get_position(ticket):
    positions = mt5.positions_get(ticket=ticket)
    if positions:
        return positions[0]
    return None


# ---------------------------
# CLOSE TRADE
# ---------------------------
def close_trade(position):
    tick = mt5.symbol_info_tick(SYMBOL)

    close_type = mt5.ORDER_TYPE_SELL if position.type == 0 else mt5.ORDER_TYPE_BUY

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": position.volume,
        "type": close_type,
        "position": position.ticket,
        "price": tick.bid if close_type == mt5.ORDER_TYPE_SELL else tick.ask,
        "deviation": DEVIATION,
        "magic": 123456,
        "comment": "LIVE_TEST_CLOSE",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print("❌ Close failed:", result.retcode)
        return False

    print(f"✅ Trade closed | ticket: {position.ticket}")
    return True


# ---------------------------
# MAIN TEST
# ---------------------------
def run_test():
    print("\n🚀 STARTING LIVE EXECUTION TEST\n")

    if not connect():
        return

    ticket = open_trade()
    if not ticket:
        return

    time.sleep(5)

    position = get_position(ticket)

    if not position:
        print("❌ ERROR: Trade not found in MT5 positions")
        return

    print(f"📊 Trade is live | profit: {position.profit}")

    time.sleep(5)

    if close_trade(position):
        time.sleep(2)

        final_pos = get_position(ticket)

        if final_pos is None:
            print("\n🎯 TEST RESULT: PASS")
            print("✔️ Open Trade: OK")
            print("✔️ Close Trade: OK")
            print("✔️ MT5 Execution: OK")
        else:
            print("\n❌ TEST RESULT: FAIL")
            print("Trade still exists after close")

    mt5.shutdown()


# ---------------------------
# RUN
# ---------------------------
if __name__ == "__main__":
    run_test()