import os
import telebot
import threading
import yfinance as yf
import time
from flask import Flask

# --- 1. CONFIGURATION ---
app = Flask(__name__)
TOKEN = os.environ.get('TELEGRAM_TOKEN')
# Remplace par ton ID numérique (ex: 12345678)
MY_CHAT_ID = "929066398" 
bot = telebot.TeleBot(TOKEN)

@app.route('/')
def health(): return "Bot en ligne", 200

def get_market_status():
    try:
        # Récupération des métaux (USD) et du taux USD/CHF
        gold = yf.Ticker("GC=F").history(period="2d")
        silver = yf.Ticker("SI=F").history(period="2d")
        usd_chf_ticker = yf.Ticker("USDCHF=X").history(period="1d")
        
        g_usd = gold['Close'].iloc[-1]
        s_usd = silver['Close'].iloc[-1]
        rate = usd_chf_ticker['Close'].iloc[-1]
        
        # Conversions
        g_chf = g_usd * rate
        s_chf = s_usd * rate
        ratio = g_usd / s_usd
        
        # Données pour alertes manipulation (Volume Silver)
        last_vol = silver['Volume'].iloc[-1]
        avg_vol = yf.Ticker("SI=F").history(period="5d")['Volume'].mean()
        
        return {
            "g_usd": g_usd, "g_chf": g_chf,
            "s_usd": s_usd, "s_chf": s_chf,
            "ratio": ratio, "rate": rate,
            "vol": last_vol, "avg_vol": avg_vol
        }
    except Exception as e:
        print(f"Erreur data : {e}")
        return None

# --- 2. SURVEILLANCE ET ALERTES AUTOMATIQUES ---
def auto_monitor():
    while True:
        data = get_market_status()
        if data and MY_CHAT_ID != "929066398":
            # Message horaire
            msg = (f"🕒 **Rapport Horaire**\n\n"
                   f"🟡 **Or (Once)**\n"
                   f"└ `{data['g_chf']:.2f} CHF` | `${data['g_usd']:.2f}`\n\n"
                   f"⚪️ **Argent (Once)**\n"
                   f"└ `{data['s_chf']:.2f} CHF` | `${data['s_usd']:.2f}`\n\n"
                   f"⚖️ **Ratio Au/Ag** : `{data['ratio']:.2f}`\n"
                   f"📉 **Change** : 1$ = `{data['rate']:.4f} CHF`")
            
            try:
                bot.send_message(MY_CHAT_ID, msg, parse_mode='Markdown')
            except: pass

            # Alerte manipulation (Volume > 2x la moyenne)
            if data['vol'] > (data['avg_vol'] * 2.2):
                alert = (f"🚨 **ALERTE MANIPULATION PAPIER**\n"
                         f"Volume suspect détecté sur l'argent !\n"
                         f"Volume actuel : `{int(data['vol'])}`")
                bot.send_message(MY_CHAT_ID, alert, parse_mode='Markdown')

        # Pause de 60 minutes
        time.sleep(3600)

# --- 3. COMMANDES MANUELLES ---
@bot.message_handler(commands=['start', 'check'])
def manual_check(message):
    data = get_market_status()
    if data:
        text = (f"📊 **Cours en Temps Réel**\n\n"
                f"🟡 Or : `{data['g_chf']:.2f} CHF` (${data['g_usd']:.2f})\n"
                f"⚪️ Argent : `{data['s_chf']:.2f} CHF` (${data['s_usd']:.2f})\n"
                f"⚖️ Ratio : `{data['ratio']:.2f}`")
        bot.reply_to(message, text, parse_mode='Markdown')
    else:
        bot.reply_to(message, "Erreur de récupération des données.")

@bot.message_handler(commands=['id'])
def show_id(message):
    bot.reply_to(message, f"Votre ID : `{message.chat.id}`")

if __name__ == "__main__":
    threading.Thread(target=auto_monitor, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
