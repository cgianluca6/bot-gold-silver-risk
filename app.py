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
def health(): return "Bot Gold/Silver CHF-USD Ready", 200

def get_full_report():
    """Récupère et formate toutes les données demandées."""
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

        # Construction du message structuré
        report = (
            "🕒 RAPPORT COMPLET DES COURS\n"
            "---------------------------\n"
            "🇨🇭 EN FRANCS SUISSES (CHF)\n"
            f"🟡 Or l'once : {g_usd * rate:.2f} CHF\n"
            f"⚪️ Argent l'once : {s_usd * rate:.2f} CHF\n"
            f"⚪️ Argent le kilo : {(s_usd * to_kilo) * rate:.2f} CHF\n"
            f"📉 ETF ZKB : {etf_chf:.2f} CHF\n"
            "\n"
            "🇺🇸 EN DOLLARS (USD)\n"
            f"🟡 Or l'once : ${g_usd:.2f}\n"
            f"⚪️ Argent l'once : ${s_usd:.2f}\n"
            f"⚪️ Argent le kilo : ${s_usd * to_kilo:.2f}\n"
            "---------------------------\n"
            f"⚖️ Ratio Or/Arg : {ratio:.2f}\n"
            f"📈 Change : 1$ = {rate:.4f} CHF"
        )
        return report
    except Exception as e:
        print(f"Erreur data : {e}")
        return "⚠️ Erreur lors de la récupération des données boursières."

def monitor():
    """Envoie le rapport complet toutes les heures."""
    while True:
        # On n'envoie que si l'ID est configuré
        if MY_CHAT_ID != "929066398":
            report = get_full_report()
            try:
                bot.send_message(MY_CHAT_ID, report)
            except Exception as e:
                print(f"Erreur envoi auto : {e}")
        
        time.sleep(3600) # 1 heure

# --- COMMANDES MANUELLES ---
@bot.message_handler(commands=['check', 'start'])
def manual_check(message):
    """Répond avec le rapport COMPLET identique au rapport horaire."""
    report = get_full_report()
    bot.reply_to(message, report)

@bot.message_handler(commands=['id'])
def show_id(message):
    bot.reply_to(message, f"Votre ID : {message.chat.id}")

if __name__ == "__main__":
    # Lancement du thread de surveillance
    threading.Thread(target=monitor, daemon=True).start()
    
    # Lancement du polling Telegram
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    
    # Serveur Flask pour Koyeb
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
