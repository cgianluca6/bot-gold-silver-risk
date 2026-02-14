import os
import telebot
import threading
import yfinance as yf
import time
import pandas as pd
from flask import Flask

# --- 1. CONFIGURATION DU SERVEUR (Pour Koyeb) ---
app = Flask(__name__)

@app.route('/')
def health():
    return "Bot en ligne et opérationnel", 200

# --- 2. CONFIGURATION DU BOT ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
# IMPORTANT : Remplacez par votre ID (ex: 12345678) après avoir fait /id
MY_CHAT_ID = "929066398" 
bot = telebot.TeleBot(TOKEN)

def get_market_status():
    """Récupère les données Or, Argent et Volume."""
    try:
        # On récupère l'Or et l'Argent (Futures)
        gold = yf.Ticker("GC=F").history(period="5d", interval="1h")
        silver = yf.Ticker("SI=F").history(period="5d", interval="1h")
        
        g_price = gold['Close'].iloc[-1]
        s_price = silver['Close'].iloc[-1]
        ratio = g_price / s_price
        
        # Données pour le volume et la manipulation
        last_vol = silver['Volume'].iloc[-1]
        avg_vol = silver['Volume'].mean()
        price_change = ((s_price - silver['Close'].iloc[-2]) / silver['Close'].iloc[-2]) * 100
        
        return g_price, s_price, ratio, last_vol, avg_vol, price_change
    except Exception as e:
        print(f"Erreur data : {e}")
        return None

# --- 3. LOGIQUE D'ALERTE ET RAPPORT HORAIRE ---
def auto_monitor():
    while True:
        data = get_market_status()
        if data and MY_CHAT_ID != "VOTRE_ID_NUMERIQUE":
            g, s, r, vol, avg_v, change = data
            
            # A. RAPPORT HORAIRE SYSTEMATIQUE
            report = (f"🕒 **Rapport Horaire Automatique**\n"
                      f"🟡 Or : `${g:.2f}`\n"
                      f"⚪️ Argent : `${s:.2f}`\n"
                      f"⚖️ Ratio : `{r:.2f}`\n"
                      f"📊 Vol. Argent : `{int(vol)}`")
            
            try:
                bot.send_message(MY_CHAT_ID, report, parse_mode='Markdown')
            except Exception as e:
                print(f"Erreur envoi rapport : {e}")

            # B. DÉTECTION DE MANIPULATION (ALERTE FLASH)
            # Si volume > 250% de la moyenne ET baisse de prix > 1.5%
            if vol > (avg_v * 2.5) and change < -1.5:
                alert = (f"🚨 **ALERTE MANIPULATION PAPIER** 🚨\n\n"
                         f"⚠️ Volume anormal détecté sur l'Argent !\n"
                         f"📉 Chute rapide : `{change:.2f}%` en 1h\n"
                         f"📊 Volume : `{int(vol)}` ({(vol/avg_v):.1f}x la moyenne)")
                bot.send_message(MY_CHAT_ID, alert, parse_mode='Markdown')

        # Attendre 1 heure (3600 secondes)
        time.sleep(3600)

# --- 4. COMMANDES MANUELLES ---
@bot.message_handler(commands=['start', 'check'])
def manual_check(message):
    data = get_market_status()
    if data:
        g, s, r, vol, avg_v, change = data
        text = (f"📊 **Statut du Marché**\n\n"
                f"🟡 Or : `${g:.2f}`\n"
                f"⚪️ Argent : `${s:.2f}`\n"
                f"⚖️ Ratio : `{r:.2f}`\n"
                f"📈 Changement (1h) : `{change:.2f}%`")
        bot.reply_to(message, text, parse_mode='Markdown')
    else:
        bot.reply_to(message, "Erreur lors de la récupération des cours.")

@bot.message_handler(commands=['id'])
def show_id(message):
    bot.reply_to(message, f"Votre ID est : `{message.chat.id}`\nCopiez ce nombre dans votre code sur GitHub (variable MY_CHAT_ID).")

# --- 5. LANCEMENT ---
if __name__ == "__main__":
    # 1. Lancement de la surveillance automatique (Thread séparé)
    threading.Thread(target=auto_monitor, daemon=True).start()
    
    # 2. Lancement de l'écoute des messages Telegram (Thread séparé)
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    
    # 3. Lancement du serveur Web pour Koyeb (Thread principal)
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
