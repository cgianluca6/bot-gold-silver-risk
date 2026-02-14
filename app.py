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
def health(): return "Bot Actif", 200

def get_data():
    try:
        # Tickers : GC=F (Or), SI=F (Argent), ZSIL.SW (ETF ZKB sur SIX), USDCHF=X (Change)
        gold_t = yf.Ticker("GC=F").history(period="2d")
        silver_t = yf.Ticker("SI=F").history(period="2d")
        etf_t = yf.Ticker("ZSIL.SW").history(period="2d")
        fx_t = yf.Ticker("USDCHF=X").history(period="1d")

        # Prix de base (USD)
        g_usd = gold_t['Close'].iloc[-1]
        s_usd = silver_t['Close'].iloc[-1]
        rate = fx_t['Close'].iloc[-1]
        etf_chf = etf_t['Close'].iloc[-1]
        
        # Conversions
        to_kilo = 32.1507
        g_chf = g_usd * rate
        s_chf = s_usd * rate
        s_kilo_chf = (s_usd * to_kilo) * rate
        s_kilo_usd = s_usd * to_kilo
        
        ratio = g_usd / s_usd
        
        # Calcul variation ETF pour alerte
        etf_prev = etf_t['Close'].iloc[-2]
        etf_change = ((etf_chf - etf_prev) / etf_prev) * 100
        
        return {
            "g_usd": g_usd, "g_chf": g_chf,
            "s_usd": s_usd, "s_chf": s_chf,
            "s_kilo_usd": s_kilo_usd, "s_kilo_chf": s_kilo_chf,
            "etf": etf_chf, "etf_change": etf_change,
            "rate": rate, "ratio": ratio,
            "vol": silver_t['Volume'].iloc[-1]
        }
    except Exception as e:
        print(f"Erreur extraction : {e}")
        return None

def monitor():
    while True:
        d = get_data()
        if d and MY_CHAT_ID != "929066398":
            # CONSTRUCTION DU MESSAGE UNIQUE
            msg = (
                f"🕒 **RAPPORT HORAIRE**\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🇨🇭 **FRANCS SUISSES (CHF)**\n"
                f"🟡 Or l'once : `{d['g_chf']:.2f} CHF`\n"
                f"⚪️ Argent l'once : `{d['s_chf']:.2f} CHF`\n"
                f"⚪️ Argent le kilo : `{d['s_kilo_chf']:,.2f} CHF`\n"
                f"📈 ETF ZKB : `{d['etf']:.2f} CHF`\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🇺🇸 **DOLLARS (USD)**\n"
                f"🟡 Or l'once : `${d['g_usd']:.2f}`\n"
                f"⚪️ Argent l'once : `${d['s_usd']:.2f}`\n"
                f"⚪️ Argent le kilo : `${d['s_kilo_usd']:,.2f}`\n"
                f"━━━━━━━━━━━━━━━\n"
                f"⚖️ **Ratio Or/Argent : {d['ratio']:.2f}**\n"
                f"📈 Change : 1$ = `{d['rate']:.4f} CHF`"
            )
            
            try:
                bot.send_message(MY_CHAT_ID, msg, parse_mode='Markdown')
                
                # Alertes immédiates
                if abs(d['etf_change']) > 2.0:
                    bot.send_message(MY_CHAT_ID, f"⚠️ **ALERTE ETF ZKB**\nMouvement de `{d['etf_change']:.2f}%` détecté !")
            except:
                pass
        
        time.sleep(3600)

@bot.message_handler(commands=['check', 'start'])
def check(message):
    d = get_data()
    if d:
        bot.reply_to(message, f"📊 **Direct**\nOr : `{d['g_chf']:.2f} CHF`\nArg Kg : `{d['s_kilo_chf']:,.2f} CHF`", parse_mode='Markdown')

if __name__ == "__main__":
    threading.Thread(target=monitor, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
