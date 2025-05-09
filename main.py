from flask import Flask, request
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# === CONFIGURATION ===
RISK_PERCENT = 0.05  # 5% of capital per trade
balance = 200.0  # Initial account balance

# Contract size per symbol
CONTRACT_SIZE = {
    'XAUUSD': 100,     # 1 lot = 100 ounces
    'EURUSD': 100000,  # 1 lot = 100k EUR
    'BTCUSD': 1        # 1 lot = 1 BTC
}

# ATR Multipliers
ATR_MULT_SL = 1.5  # Stop Loss = 1.5 x ATR
ATR_MULT_TP = 3.0  # Take Profit = 3.0 x ATR

# === TELEGRAM (SECURE from Environment Variables) ===
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# === FUNCTIONS ===

def get_atr_value(ticker):
    atr_values = {
        'XAUUSD': 5.0,
        'EURUSD': 0.0020,
        'BTCUSD': 500.0
    }
    return atr_values.get(ticker, 1.0)  # default 1.0

def calculate_tp_sl(entry_price, direction, atr_value):
    sl_distance = ATR_MULT_SL * atr_value
    tp_distance = ATR_MULT_TP * atr_value
    if direction == "BUY":
        sl = entry_price - sl_distance
        tp = entry_price + tp_distance
    else:
        sl = entry_price + sl_distance
        tp = entry_price - tp_distance
    return round(tp, 2), round(sl, 2)

def calculate_lot_size(ticker, entry_price, stop_loss):
    risk_amount = balance * RISK_PERCENT
    price_diff = abs(entry_price - stop_loss)
    contract_value = CONTRACT_SIZE.get(ticker, 1)
    loss_per_lot = price_diff * contract_value
    if loss_per_lot == 0:
        return 0.01  # minimum lot if error
    lot_size = risk_amount / loss_per_lot

    # Force minimum lot sizes
    if ticker == 'XAUUSD' and lot_size < 0.02:
        lot_size = 0.02
    elif ticker == 'EURUSD' and lot_size < 0.03:
        lot_size = 0.03

    return round(lot_size, 3)

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram token or chat id missing.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        r = requests.post(url, data=payload)
        print("Telegram Response:", r.text)
    except Exception as e:
        print("Telegram Error:", e)

# === ROUTES ===

@app.route('/')
def home():
    return 'Bot is running! ✅'

@app.route('/webhook', methods=['POST'])
def webhook():
    global balance
    try:
        data = request.get_json(force=True)
        if not data:
            return 'No data', 400

        ticker = data.get('ticker')
        price = float(data.get('close'))
        action = data.get('action', 'BUY').upper()

        # Entry Signal (Buy/Sell)
        if action in ['BUY', 'SELL']:
            atr = get_atr_value(ticker)
            tp, sl = calculate_tp_sl(price, action, atr)
            lot = calculate_lot_size(ticker, price, sl)

            emoji = "🟢" if action == "BUY" else "🔴"
            msg = (
                f"{emoji} {action} signal for {ticker}\n"
                f"💵 Entry: {price}\n"
                f"📊 Lot Size: {lot}\n"
                f"🎯 TP: {tp}\n"
                f"🛑 SL: {sl}\n"
                f"\nBalance: {balance:.2f} USD"
            )
            send_telegram(msg)

        # TP HIT
        elif action == 'TP HIT':
            profit = balance * RISK_PERCENT * 2  # Approximate TP = 2x risk reward
            balance += profit
            profit_percent = (profit / (balance - profit)) * 100

            msg = (
                f"🎯 TAKE PROFIT HIT on {ticker}!\n"
                f"✅ Profit: +{profit_percent:.2f}%\n"
                f"💵 New Balance: {balance:.2f} USD"
            )
            send_telegram(msg)

        # SL HIT
        elif action == 'SL HIT':
            loss = balance * RISK_PERCENT
            balance -= loss
            loss_percent = (loss / (balance + loss)) * 100

            msg = (
                f"🛑 STOP LOSS HIT on {ticker}.\n"
                f"❌ Loss: -{loss_percent:.2f}%\n"
                f"💵 New Balance: {balance:.2f} USD"
            )
            send_telegram(msg)

        return 'Signal processed ✅', 200

    except Exception as e:
        print(f"Webhook error: {e}")
        return 'Webhook failed ❌', 500

# === RUN FLASK SERVER ===

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
