from flask import Flask, request
import requests
import os

app = Flask(__name__)

# === CONFIGURATION ===
RISK_PERCENT = 0.01  # 1% of capital per trade
ACCOUNT_BALANCE = 200.0  # Initial account balance

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
    risk_amount = ACCOUNT_BALANCE * RISK_PERCENT
    price_diff = abs(entry_price - stop_loss)
    contract_value = CONTRACT_SIZE.get(ticker, 1)
    loss_per_lot = price_diff * contract_value
    if loss_per_lot == 0:
        return 0.01  # minimum lot
    lot_size = risk_amount / loss_per_lot
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
    data = request.get_json(force=True)
    if not data:
        return 'No data', 400

    ticker = data.get('ticker')
    price = float(data.get('close'))
    direction = data.get('action', 'BUY').upper()

    atr = get_atr_value(ticker)
    tp, sl = calculate_tp_sl(price, direction, atr)
    lot = calculate_lot_size(ticker, price, sl)

    emoji = "🟢" if direction == "BUY" else "🔴"
    msg = (
        f"{emoji} {direction} signal for {ticker}\n"
        f"💵 Entry: {price}\n"
        f"🎯 TP: {tp}\n"
        f"🛑 SL: {sl}\n"
        f"📊 Lot Size: {lot}"
    )

    send_telegram(msg)

    return 'Signal processed ✅', 200

# === RUN FLASK SERVER ===

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
