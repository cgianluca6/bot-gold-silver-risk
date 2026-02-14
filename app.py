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
def health(): return "Bot Gold/Silver/CHF Ready", 200

def get_market_status():
    try:
        # Récupération des métaux (USD) et du taux USD/CHF
        gold = yf.Ticker("GC=F").history(period="2d")
        silver = yf.Ticker("SI=F").history(period="2d")
        usd_chf_ticker = yf.Ticker("USDCHF=X").history(period="1d")
        
        g_once_usd = gold['Close'].iloc[-1]
        s_once_usd = silver['Close'].iloc[-1]
        rate = usd_chf_ticker['Close'].iloc[-1]
        
        # Facteur de conversion Once Troy -> Kilo (1 kg = 32.1507 onces)
        to_kilo = 32.1507
        
        data = {
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
        return data
    except Exception as e:
        print(f"Erreur data : {e}")
        return None

# --- 2. SURVEILLANCE ET ALERTES AUTOMATIQUES ---
def auto_monitor():
    while True:
        d = get_market_status()
        if d and MY_CHAT_ID != "929066398":
            msg = (
                f"🕒 **RAPPORT HORAIRE DES COURS**\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🇨🇭 **EN FRANCS SUISSES (CHF)**\n"
                f"🟡 Or l'once : `{d['g_once_chf']:.2f} CHF`\n"
                f"⚪️ Argent l'once : `{d['s_once_chf']:.2f} CHF`\n"
                f"⚪️ Argent le kilo : `{d['s_kilo_chf']:,.2f} CHF`\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🇺🇸 **EN DOLLARS (USD)**\n"
                f"🟡 Or l'once : `${d['g_once_usd']:.2f}`\n"
                f"⚪️ Argent l'once : `${d['s_once_usd']:.2f}`\n"
                f"⚪️ Argent le kilo : `${d['s_kilo_usd']:,.2f}`\n"
                f"━━━━━━━━━━━━━━━\n"
                f"⚖️ **Ratio Or/Arg** : `{d['ratio']:.2f}`\n"
                f"📈 **Taux** : 1$ = `{d['rate']:.4f} CHF`"
            )
            
            try:
                bot.send_message(MY_CHAT_ID, msg, parse_mode='Markdown')
            except: pass

            # Alerte Manipulation (Volume > 2.5x la moyenne)
            if d['vol'] > (d['avg_vol'] * 2.5):
                alert = (f"🚨 **ALERTE MANIPULATION COMEX**\n"
                         f"Volume massif sur l'argent papier !\n"
                         f"Volume : `{int(d['vol'])}` (Anomalie détectée)")
                bot.send_message(MY_CHAT_ID, alert, parse_mode='Markdown')

        time.sleep(3600) # Attendre 1 heure

# --- 3. COMMANDES ---
@bot.message_handler(commands=['start', 'check'])
def manual_check(message):
    d = get_market_status()
    if d:
        text = (f"📊 **COURS ACTUELS (CHF)**\n\n"
                f"🟡 Or once : `{d['g_once_chf']:.2f} CHF`\n"
                f"⚪️ Arg once : `{d['s_once_chf']:.2f} CHF`\n"
                f"⚪️ Arg kilo : `{d['s_kilo_chf']:,.2f} CHF`\n\n"
                f"⚖️ Ratio : `{d['ratio']:.2f}`")
        bot.reply_to(message, text, parse_mode='Markdown')
    else:
        bot.reply_to(message, "Données indisponibles.")

@bot.message_handler(commands=['id'])
def show_id(message):
    bot.reply_to(message, f"Votre ID : `{message.chat.id}`")

if __name__ == "__main__":
    threading.Thread(target=auto_monitor, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
