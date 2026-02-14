import os
import telebot
import threading
import yfinance as yf
import time
from flask import Flask

app = Flask(__name__)
TOKEN = os.environ.get('TELEGRAM_TOKEN')
# REMPLACEZ par votre ID numérique obtenu via /id
MY_CHAT_ID = "929066398" 
bot = telebot.TeleBot(TOKEN)

@app.route('/')
def health(): return "Bot en ligne", 200

def get_data():
    try:
        # Tickers
        gold_t = yf.Ticker("GC=F").history(period="2d")
        silver_t = yf.Ticker("SI=F").history(period="2d")
        etf_t = yf.Ticker("ZSIL.SW").history(period="2d")
        fx_t = yf.Ticker("USDCHF=X").history(period="1d")

        g_usd = gold_t['Close'].iloc[-1]
        s_usd = silver_t['Close'].iloc[-1]
        rate = fx_t['Close'].iloc[-1]
        etf_chf = etf_t['Close'].iloc[-1]
        
        to_kilo = 32.1507
        ratio = g_usd / s_usd
        
        return {
            "g_usd": g_usd, "g_chf": g_usd * rate,
            "s_usd": s_usd, "s_chf": s_usd * rate,
            "s_kilo_usd": s_usd * to_kilo, "s_kilo_chf": (s_usd * to_kilo) * rate,
            "etf": etf_chf, "rate": rate, "ratio": ratio
        }
    except Exception as e:
        print(f"Erreur : {e}")
        return None

def monitor():
    while True:
        d = get_data()
        if d and MY_CHAT_ID != "929066398":
            # Construction du message sans fioritures pour éviter les bugs Telegram
            msg = (
                "🕒 RAPPORT DES COURS\n"
                "---------------------------\n"
                "🇨🇭 EN FRANCS SUISSES (CHF)\n"
                f"Or l'once : {d['g_chf']:.2f} CHF\n"
                f"Arg l'once : {d['s_chf']:.2f} CHF\n"
                f"Arg le kilo : {d['s_kilo_chf']:.2f} CHF\n"
                f"ETF ZKB : {d['etf']:.2f} CHF\n"
                "\n"
                "🇺🇸 EN DOLLARS (USD)\n"
                f"Or l'once : ${d['g_usd']:.2f}\n"
                f"Arg l'once : ${d['s_usd']:.2f}\n"
                f"Arg le kilo : ${d['s_kilo_usd']:.2f}\n"
                "---------------------------\n"
                f"⚖️ Ratio Or/Arg : {d['ratio']:.2f}\n"
                f"📈 Change : 1$ = {d['rate']:.4f} CHF"
            )
            
            try:
                bot.send_message(MY_CHAT_ID, msg)
            except Exception as e:
                print(f"Erreur envoi message : {e}")
        
        time.sleep(3600)

@bot.message_handler(commands=['check', 'start'])
def check(message):
    d = get_data()
    if d:
        msg = (
            f"📊 DIRECT\n"
            f"Or : {d['g_chf']:.2f} CHF\n"
            f"Arg Kg : {d['s_kilo_chf']:.2f} CHF\n"
            f"Ratio : {d['ratio']:.2f}"
        )
        bot.reply_to(message, msg)

if __name__ == "__main__":
    threading.Thread(target=monitor, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
