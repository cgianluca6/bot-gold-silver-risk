import os
import telebot
import threading
import yfinance as yf
import time
from flask import Flask

# --- 1. CONFIGURATION ---
app = Flask(__name__)
TOKEN = os.environ.get('TELEGRAM_TOKEN')
# REMPLACEZ par votre ID numérique obtenu via /id
MY_CHAT_ID = "929066398" 
bot = telebot.TeleBot(TOKEN)

@app.route('/')
def health(): return "Bot Gold/Silver CHF-USD Ready", 200

def get_market_status():
    try:
        # Récupération des données
        gold = yf.Ticker("GC=F").history(period="2d")
        silver = yf.Ticker("SI=F").history(period="2d")
        usd_chf_ticker = yf.Ticker("USDCHF=X").history(period="1d")
        
        g_once_usd = gold['Close'].iloc[-1]
        s_once_usd = silver['Close'].iloc[-1]
        rate = usd_chf_ticker['Close'].iloc[-1]
        
        # Facteur de conversion Once -> Kilo (32.1507)
        to_kilo = 32.1507
        
        return {
            "rate": rate,
            "ratio": g_once_usd / s_once_usd,
            "g_once_usd": g_once_usd,
            "g_once_chf": g_once_usd * rate,
            "s_once_usd": s_once_usd,
            "s_once_chf": s_once_usd * rate,
            "s_kilo_usd": s_once_usd * to_kilo,
            "s_kilo_chf": (s_once_usd * to_kilo) * rate,
            "vol": silver['Volume'].iloc[-1],
            "avg_vol": yf.Ticker("SI=F").history(period="5d")['Volume'].mean()
        }
    except Exception as e:
        print(f"Erreur data : {e}")
        return None

# --- 2. SURVEILLANCE ET ALERTES ---
def auto_monitor():
    while True:
        d = get_market_status()
        if d and MY_CHAT_ID != "929066398":
            # Construction du message avec les deux blocs bien séparés
            msg = (
                f"🕒 **RAPPORT HORAIRE DES COURS**\n\n"
                f"🇨🇭 **PRIX EN FRANCS SUISSES (CHF)**\n"
                f"🟡 Or l'once : `{d['g_once_chf']:.2f} CHF`\n"
                f"⚪️ Argent l'once : `{d['s_once_chf']:.2f} CHF`\n"
                f"⚪️ Argent le kilo : `{d['s_kilo_chf']:,.2f} CHF`\n\n"
                f"🇺🇸 **PRIX EN DOLLARS (USD)**\n"
                f"🟡 Or l'once : `${d['g_once_usd']:.2f}`\n"
                f"⚪️ Argent l'once : `${d['s_once_usd']:.2f}`\n"
                f"⚪️ Argent le kilo : `${d['s_kilo_usd']:,.2f}`\n\n"
                f"⚖️ **Ratio Or/Arg** : `{d['ratio']:.2f}`\n"
                f"📈 **Change** : 1$ = `{d['rate']:.4f} CHF`"
            )
            
            try:
                bot.send_message(MY_CHAT_ID, msg, parse_mode='Markdown')
            except: pass

            # Alerte Manipulation
            if d['vol'] > (d['avg_vol'] * 2.5):
                alert = (f"🚨 **ALERTE VOLUME COMEX**\n"
                         f"Volume massif sur l'argent papier !\n"
                         f"Volume : `{int(d['vol'])}`")
                bot.send_message(MY_CHAT_ID, alert, parse_mode='Markdown')

        time.sleep(3600)

# --- 3. COMMANDES ---
@bot.message_handler(commands=['start', 'check'])
def manual_check(message):
    d = get_market_status()
    if d:
        text = (
            f"📊 **COURS ACTUELS**\n\n"
            f"🇨🇭 `{d['g_once_chf']:.2f} CHF` (Or/Oz)\n"
            f"🇨🇭 `{d['s_kilo_chf']:,.2f} CHF` (Arg/Kg)\n\n"
            f"🇺🇸 `${d['g_once_usd']:.2f}` (Or/Oz)\n"
            f"🇺🇸 `${d['s_kilo_usd']:,.2f}` (Arg/Kg)"
        )
        bot.reply_to(message, text, parse_mode='Markdown')
    else:
        bot.reply_to(message, "Données indisponibles.")

@bot.message_handler(commands=['id'])
def show_id(message):
    bot.reply_to(message, f"Votre ID : `{message.chat.id}`")

if __name__ == "__main__":
    threading.Thread(target=auto_monitor, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
