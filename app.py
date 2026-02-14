import os
import telebot
import threading
import yfinance as yf
import time
import pandas as pd
from flask import Flask

# --- 1. CONFIGURATION ---
app = Flask(__name__)
TOKEN = os.environ.get('TELEGRAM_TOKEN')
# N'oubliez pas de mettre votre ID numérique ici
MY_CHAT_ID = os.environ.get('MY_CHAT_ID', '929066398') 
bot = telebot.TeleBot(TOKEN)

@app.route('/')
def health(): return "Bot en ligne", 200

def get_market_status():
    try:
        # Récupération des métaux (en USD) et du taux de change USD/CHF
        gold = yf.Ticker("GC=F").history(period="5d", interval="1h")
        silver = yf.Ticker("SI=F").history(period="5d", interval="1h")
        usd_chf = yf.Ticker("USDCHF=X").history(period="1d")['Close'].iloc[-1]
        
        g_usd = gold['Close'].iloc[-1]
        s_usd = silver['Close'].iloc[-1]
        
        # Conversion en CHF
        g_chf = g_usd * usd_chf
        s_chf = s_usd * usd_chf
        
        ratio = g_usd / s_usd
        
        # Données volume pour l'argent
        last_vol = silver['Volume'].iloc[-1]
        avg_vol = silver['Volume'].mean()
        price_change = ((s_usd - silver['Close'].iloc[-2]) / silver['Close'].iloc[-2]) * 100
        
        return g_usd, g_chf, s_usd, s_chf, ratio, last_vol, avg_vol, price_change, usd_chf
    except Exception as e:
        print(f"Erreur data : {e}")
        return None

# --- 2. SURVEILLANCE ET ALERTES ---
def auto_monitor():
    while True:
        data = get_market_status()
        if data and MY_CHAT_ID != "929066398":
            g_u, g_c, s_u, s_c, r, vol, avg_v, change, rate = data
            
            report = (f"🕒 **Rapport Horaire (CHF/USD)**\n\n"
                      f"🟡 **Or** : `{g_c:.2f} CHF` (${g_u:.2f})\n"
                      f"⚪️ **Argent** : `{s_c:.2f} CHF` (${s_u:.2f})\n"
                      f"⚖️ **Ratio** : `{r:.2f}`\n"
                      f"📉 **Change** : 1 USD = `{rate:.4f} CHF`\n"
                      f"📊 **Vol. Arg** : `{int(vol)}`")
            
            try:
                bot.send_message(MY_CHAT_ID, report, parse_mode='Markdown')
            except: pass

            # ALERTE MANIPULATION
            if vol > (avg_v * 2.5) and change < -1.5:
                alert = (f"🚨 **ALERTE MANIPULATION** 🚨\n"
                         f"Volume suspect sur l'Argent !\n"
                         f"Chute : `{change:.2f}%` | Vol : `{int(vol)}`")
                bot.send_message(MY_CHAT_ID, alert, parse_mode='Markdown')

        time.sleep(3600)

# --- 3. COMMANDES ---
@bot.message_handler(commands=['start', 'check'])
def manual_check(message):
    data = get_market_status()
    if data:
        g_u, g_c, s_u, s_c, r, vol, avg_v, change, rate = data
        text = (f"📊 **Cours Actuels**\n\n"
                f"🟡 **Or** : `{g_c:.2f} CHF`\n"
                f"⚪️ **Argent** : `{s_c:.2f} CHF`\n"
                f"⚖️ **Ratio Au/Ag** : `{r:.2f}`\n\n"
                f"💵 1 USD = `{rate:.4f} CHF`")
        bot.reply_to(message, text, parse_mode='Markdown')
    else:
        bot.reply_to(message, "Erreur de connexion aux marchés.")

@bot.message_handler(commands=['id'])
def show_id(message):
    bot.reply_to(message, f"Votre ID : `{message.chat.id}`")

if __name__ == "__main__":
    threading.Thread(target=auto_monitor, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
