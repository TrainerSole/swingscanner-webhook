"""
================================================
TRADINGVIEW → TELEGRAM WEBHOOK SERVER
Receives alerts from TradingView v6 indicator
and instantly sends formatted signals to Telegram
================================================
Deploy this on Render.com (free tier)
Then point your TradingView alerts to its URL
================================================
"""

from flask import Flask, request, jsonify
import requests
import json
import os
from datetime import datetime

app = Flask(__name__)

# ─────────────────────────────────────────────
# CREDENTIALS — set these as Environment
# Variables on Render, never hardcode here
# ─────────────────────────────────────────────
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN",   "YOUR_TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")
WEBHOOK_SECRET   = os.environ.get("WEBHOOK_SECRET",   "swingv6secret")

# ─────────────────────────────────────────────
# SEND TELEGRAM
# ─────────────────────────────────────────────
def send_telegram(message):
    url     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       message,
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

# ─────────────────────────────────────────────
# HEALTH CHECK — Render needs this
# ─────────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "running",
        "service": "SwingScanner V6 Webhook",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

# ─────────────────────────────────────────────
# WEBHOOK ENDPOINT — TradingView posts here
# ─────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        # Verify secret key to prevent spam
        secret = request.args.get("secret", "")
        if secret != WEBHOOK_SECRET:
            return jsonify({"error": "Unauthorized"}), 401

        # Parse the incoming data from TradingView
        # TradingView sends plain text or JSON
        raw = request.data.decode("utf-8")
        print(f"Received webhook: {raw}")

        # Try JSON first, fall back to plain text
        try:
            data = json.loads(raw)
            ticker = data.get("ticker", "UNKNOWN")
            close  = data.get("close",  "N/A")
            time_  = data.get("time",   "N/A")
            setup  = data.get("setup",  "SWING")
        except:
            # Plain text format from TradingView
            # Expected: "SWING SIGNAL: AAPL | Score 8+/10 | Entry: 187.42"
            raw_clean = raw.strip()
            ticker = "UNKNOWN"
            close  = "N/A"

            # Try to parse ticker from message
            if ":" in raw_clean:
                parts = raw_clean.split("|")
                if len(parts) > 0:
                    first = parts[0].strip()
                    if ":" in first:
                        ticker = first.split(":")[-1].strip()
            if "{{ticker}}" not in raw_clean:
                ticker = raw_clean.split("|")[0].replace("SWING SIGNAL:", "").strip() if "|" in raw_clean else ticker
            if "{{close}}" not in raw_clean and "Entry:" in raw_clean:
                try:
                    close = raw_clean.split("Entry:")[-1].split("|")[0].strip()
                except:
                    pass

            time_ = datetime.now().strftime("%I:%M %p")
            setup = "SWING"

        # Format the Telegram alert
        now      = datetime.now()
        date_str = now.strftime("%A %B %d, %Y")
        time_str = now.strftime("%I:%M %p ET")

        message = (
            f"🚨 <b>LIVE SIGNAL FIRED</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📊 <b>{ticker}</b>\n"
            f"💰 Entry:  ${close}\n"
            f"📈 Setup:  {setup}\n"
            f"⏰ Time:   {time_str}\n"
            f"📅 Date:   {date_str}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"✅ Score 8+/10 — All v6 rules passed\n"
            f"🎯 Hold: 2-5 Days | Check chart for\n"
            f"   entry zone, target and stop loss\n"
            f"━━━━━━━━━━━━━━━\n"
            f"⚠️ Confirm on TradingView before trading"
        )

        success = send_telegram(message)

        if success:
            print(f"Signal sent to Telegram: {ticker} @ {close}")
            return jsonify({"status": "success", "ticker": ticker}), 200
        else:
            print(f"Failed to send Telegram message")
            return jsonify({"status": "telegram_error"}), 500

    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({"error": str(e)}), 500

# ─────────────────────────────────────────────
# TEST ENDPOINT — send a test message
# Visit: https://your-app.onrender.com/test
# ─────────────────────────────────────────────
@app.route("/test", methods=["GET"])
def test():
    msg = (
        f"🧪 <b>Webhook Test Successful!</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Your SwingScanner V6 webhook server\n"
        f"is connected and ready to receive\n"
        f"TradingView alerts.\n"
        f"━━━━━━━━━━━━━━━\n"
        f"✅ Telegram: Connected\n"
        f"✅ Server: Running\n"
        f"✅ Ready for live signals"
    )
    success = send_telegram(msg)
    if success:
        return jsonify({"status": "test message sent to Telegram"})
    else:
        return jsonify({"status": "error — check your Telegram credentials"})

# ─────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
