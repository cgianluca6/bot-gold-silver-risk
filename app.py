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
def health(): return "Bot Gold/Silver/ETF Ready", 200

def get_market_status():
    try:
        # Récupération des données (Futures et ETF Suisse)
        gold = yf.Ticker("GC=F").history(period="2d")
        silver = yf.Ticker("SI=F").history(period="2d")
        etf_silver = yf.Ticker("ZSIL.SW").history(period="2d") # ETF ZKB Silver
        usd_chf_ticker = yf.Ticker("USDCHF=X").history(period="1d")
        
        g_once_usd = gold['Close'].iloc[-1]
        s_once_usd = silver['Close'].iloc[-1]
        etf_price = etf_silver['Close'].iloc[-1]
        rate = usd_chf_ticker['Close'].iloc[-1]
        
        # Facteur de conversion Once -> Kilo (32.1507)
        to_kilo = 32.1507
        
        # Calcul des variations pour alertes
        etf_change = ((etf_price - etf_silver['Close'].iloc[-2]) / etf_silver['Close'].iloc[-2]) * 100
        vol_silver = silver['Volume'].iloc[-1]
        avg_vol_silver = yf.Ticker("SI=F").history(period="5d")['Volume'].mean()
        
        return {
            "rate": rate,
            "ratio": g_once_usd / s_once_usd,
            "g_once_usd": g_once_usd,
            "g_once_chf": g_once_usd * rate,
            "s_once_usd": s_once_usd,
            "s_once_chf": s_once_usd * rate,
            "s_kilo_usd": s_once_usd * to_kilo,
            "s_kilo_chf": (s_once_usd * to_kilo) * rate,
            "etf_price": etf_price,
            "etf_change": etf_change,
            "vol_silver": vol_silver,
            "avg_vol_silver": avg_vol_silver
        }
    except Exception as e:
        print(f"Erreur data : {e}")
        return None

# --- 2. SURVEILLANCE ET ALERTES ---
def auto_monitor():
    while True:
        d = get_market_status()
        if d and MY_CHAT_ID != "929066398":
            # Message horaire formaté selon vos instructions
            msg = (
                f"🕒 **RAPPORT HORAIRE DES COURS**\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🇨🇭 **EN FRANCS SUISSES (CHF)**\n"
                f"🟡 Or l'once : `{d['g_once_chf']:.2f} CHF`\n"
                f"⚪️ Argent l'once : `{d['s_once_chf']:.2f} CHF`\n"
                f"⚪️ Argent le kilo : `{d['s_kilo_chf']:,.2f} CHF`\n"
                f"📉 **ETF ZKB Silver** : `{d['etf_price']:.2f} CHF`\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🇺🇸 **EN DOLLARS (USD)**\n"
                f"🟡 Or l'once : `${d['g_once_usd']:.2f}`\n"
                f"⚪️ Argent l'once : `${d['s_once_usd']:.2f}`\n"
                f"⚪️ Argent le kilo : `${d['s_kilo_usd']:,.2f}`\n"
                f"━━━━━━━━━━━━━━━\n"
                f"⚖️ **Ratio Or/Arg** : `{d['ratio']:.2f}`\n"
                f"📈 **Change** : 1$ = `{d['rate']:.4f} CHF`"
            )
            
            try:
                bot.send_message(MY_CHAT_ID, msg, parse_mode='Markdown')
            except: pass

            # --- ALERTES ---
            # 1. Manipulation Volume COMEX
            if d['vol_silver'] > (d['avg_vol_silver'] * 2.5):
                bot.send_message(MY_CHAT_ID, f"🚨 **ALERTE VOLUME ARGENT**\nVolume papier massif détecté sur le COMEX !")
            
            # 2. Mouvement suspect ETF ZKB (plus de 2% de variation)
            if abs(d['etf_change']) > 2.0:
                bot.send_message(MY_CHAT_ID, f"⚠️ **ALERTE ETF ZKB**\nVariation anormale de l'ETF Silver : `{d['etf_change']:.2f}%`")

        time.sleep(3600)

# --- 3. COMMANDES ---
@bot.message_handler(commands=['start', 'check'])
def manual_check(message):
    d = get_market_status()
    if d:
        text = (
            f"📊 **COURS ACTUELS (CHF)**\n"
            f"🟡 Or/Oz : `{d['g_once_chf']:.2f} CHF`\n"
            f"⚪️ Arg/Oz : `{d['s_once_chf']:.2f} CHF`\n"
            f"⚪️ Arg/Kg : `{d['s_kilo_chf']:,.2f} CHF`\n"
            f"📈 ETF ZKB : `{d['etf_price']:.2f} CHF`"
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
