import os
import telebot
import threading
import yfinance as yf
import time
from flask import Flask

# --- 1. CONFIGURATION ---
app = Flask(__name__)
TOKEN = os.environ.get('TELEGRAM_TOKEN')
# REMPLACEZ par votre ID numérique (ex: 12345678) obtenu via /id
MY_CHAT_ID = "929066398" 
bot = telebot.TeleBot(TOKEN)

@app.route('/')
def health(): return "Bot Gold/Silver Ready", 200

def get_market_status():
    try:
        # Récupération des métaux (USD) et du taux USD/CHF
        gold = yf.Ticker("GC=F").history(period="2d")
        silver = yf.Ticker("SI=F").history(period="2d")
        usd_chf_ticker = yf.Ticker("USDCHF=X").history(period="1d")
        
        g_once_usd = gold['Close'].iloc[-1]
        s_once_usd = silver['Close'].iloc[-1]
        rate = usd_chf_ticker['Close'].iloc[-1]
        
        # Facteur de conversion Once -> Kilo (1 kg = 32.1507 onces troy)
        to_kilo = 32.1507
        
        # Calculs Or
        g_once_chf = g_once_usd * rate
        g_kilo_usd = g_once_usd * to_kilo
        g_kilo_chf = g_kilo_usd * rate
        
        # Calculs Argent
        s_once_chf = s_once_usd * rate
        s_kilo_usd = s_once_usd * to_kilo
        s_kilo_chf = s_kilo_usd * rate
        
        ratio = g_once_usd / s_once_usd
        
        # Données Volume (Manipulation)
        last_vol = silver['Volume'].iloc[-1]
        avg_vol = yf.Ticker("SI=F").history(period="5d")['Volume'].mean()
        
        return {
            "g_once_usd": g_once_usd, "g_once_chf": g_once_chf,
            "g_kilo_usd": g_kilo_usd, "g_kilo_chf": g_kilo_chf,
            "s_once_usd": s_once_usd, "s_once_chf": s_once_chf,
            "s_kilo_usd": s_kilo_usd, "s_kilo_chf": s_kilo_chf,
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
            msg = (
                f"🕒 **Rapport Horaire Marchés**\n\n"
                f"🟡 **OR**\n"
                f"Once: `{data['g_once_chf']:.2f} CHF` | `${data['g_once_usd']:.2f}`\n"
                f"Kilo: `{data['g_kilo_chf']:.0f} CHF` | `${data['g_kilo_usd']:.0f}`\n\n"
                f"⚪️ **ARGENT**\n"
                f"Once: `{data['s_once_chf']:.2f} CHF` | `${data['s_once_usd']:.2f}`\n"
                f"Kilo: `{data['s_kilo_chf']:.0f} CHF` | `${data['s_kilo_usd']:.0f}`\n\n"
                f"⚖️ **Ratio Au/Ag** : `{data['ratio']:.2f}`\n"
                f"📈 **Change** : 1$ = `{data['rate']:.4f} CHF`"
            )
            
            try:
                bot.send_message(MY_CHAT_ID, msg, parse_mode='Markdown')
            except: pass

            # Alerte Manipulation (Volume > 2.5x la moyenne)
            if data['vol'] > (data['avg_vol'] * 2.5):
                alert = (f"🚨 **ALERTE MANIPULATION PAPIER**\n"
                         f"Volume anormal sur l'argent détecté !\n"
                         f"Volume: `{int(data['vol'])}` (Fortes ventes COMEX)")
                bot.send_message(MY_CHAT_ID, alert, parse_mode='Markdown')

        time.sleep(3600) # 1 heure

# --- 3. COMMANDES ---
@bot.message_handler(commands=['start', 'check'])
def manual_check(message):
    data = get_market_status()
    if data:
        text = (f"📊 **Prix du Marché (Kilo)**\n\n"
                f"🟡 Or : `{data['g_kilo_chf']:.2f} CHF`\n"
                f"⚪️ Argent : `{data['s_kilo_chf']:.2f} CHF`\n"
                f"⚖️ Ratio : `{data['ratio']:.2f}`")
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
