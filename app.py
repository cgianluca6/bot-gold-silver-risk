import os
import telebot
import threading
import yfinance as yf
from flask import Flask

# Serveur pour que l'hébergeur sache que le bot est vivant
app = Flask(__name__)
@app.route('/')
def health(): return "Bot Active"

TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)

def check_market():
    try:
        g = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1]
        s = yf.Ticker("SI=F").history(period="1d")['Close'].iloc[-1]
        return g, s, (g / s)
    except: return None, None, None

@bot.message_handler(commands=['start', 'risk'])
def start(message):
    g, s, r = check_market()
    if g:
        bot.reply_to(message, f"🟡 Or: ${g:.2f}\n⚪️ Arg: ${s:.2f}\n⚖️ Ratio: {r:.2f}")
    else:
        bot.reply_to(message, "Erreur de récupération des données.")

if __name__ == "__main__":
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 8080))
