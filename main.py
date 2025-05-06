from flask import Flask, request
import requests
import os

app = Flask(__name__)

# === CONFIG ===
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

RISK_PERCENT = 1  # 1% risk per trade
TP_DISTANCE = 100  # Take Profit distance
SL_DISTANCE = 100  # Stop Loss distance

current_balance = 1000  # Default balance at startup

# === FUNCTIONS ===
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Telegram Error: {e}")

# === ROUTES ===
@app.route('/')
def home():
    return 'Bot is running! 🚀'

@app.route('/webhook', methods=['POST'])
def webhook():
    global current_balance

    print("Webhook received!")

    data = request.json
    symbol = data.get('ticker')
    price = float(data.get('close'))
    side = data.get('action', 'SELL')

    # Safe lot size
    if price > 0 and current_balance > 0:
        risk_amount = current_balance * (RISK_PERCENT / 100)
        lot_size = round(risk_amount / price, 3)
    else:
        lot_size = 0.01

    # Calculate TP and SL
    if side.upper() == "SELL":
        tp = round(price - TP_DISTANCE, 2)
        sl = round(price + SL_DISTANCE, 2)
    else:  # BUY
        tp = round(price + TP_DISTANCE, 2)
        sl = round(price - SL_DISTANCE, 2)

    emoji = "🔴" if side.upper() == "SELL" else "🟢"

    message = f"""{emoji} {side.upper()} signal on {symbol}
💵 Entry: {price}
📊 Lot Size: {lot_size}
🎯 TP: {tp}
🛑 SL: {sl}
"""

    send_telegram_message(message)
    return 'Signal Sent!'

@app.route('/balance', methods=['POST'])
def update_balance():
    global current_balance

    data = request.json
    new_balance = float(data.get('balance'))

    if new_balance > 0:
        current_balance = new_balance
        send_telegram_message(f"✅ Balance updated to ${current_balance}")
        return 'Balance Updated!'
    else:
        return 'Invalid balance value!', 400

# === RUN SERVER ===
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
