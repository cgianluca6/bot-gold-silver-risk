import os
import telebot
import threading
import yfinance as yf
import time
from flask import Flask

app = Flask(__name__)
TOKEN = os.environ.get('TELEGRAM_TOKEN')
# REMPLACEZ par votre ID numérique (ex: 12345678)
MY_CHAT_ID = "929066398" 
bot = telebot.TeleBot(TOKEN)

@app.route('/')
def health(): return "Bot Gold/Silver Ready", 200

def get_variation(current, previous):
    if previous == 0: return "0.00%"
    var = ((current - previous) / previous) * 100
    icon = "📈 +" if var > 0 else "📉 "
    return f"{icon}{var:.2f}%"

def get_full_report():
    try:
        # Récupération des données (2 jours pour calculer la variation)
        gold_t = yf.Ticker("GC=F").history(period="2d")
        silver_t = yf.Ticker("SI=F").history(period="2d")
        etf_t = yf.Ticker("ZSILC.SW").history(period="2d")
        fx_t = yf.Ticker("USDCHF=X").history(period="2d")

        # Taux de change et variations
        rate = fx_t['Close'].iloc[-1]
        prev_rate = fx_t['Close'].iloc[-2]
        
        # Données OR
        g_usd = gold_t['Close'].iloc[-1]
        g_chf = g_usd * rate
        prev_g_chf = gold_t['Close'].iloc[-2] * prev_rate
        var_g_chf = get_variation(g_chf, prev_g_chf)

        # Données ARGENT
        s_usd = silver_t['Close'].iloc[-1]
        s_chf = s_usd * rate
        prev_s_chf = silver_t['Close'].iloc[-2] * prev_rate
        var_s_chf = get_variation(s_chf, prev_s_chf)

        # ARGENT AU KILO
        to_kilo = 32.1507
        s_kilo_chf = s_chf * to_kilo
        prev_s_kilo_chf = prev_s_chf * to_kilo
        var_s_kilo_chf = get_variation(s_kilo_chf, prev_s_kilo_chf)

        # ETF ZKB
        etf_chf = etf_t['Close'].iloc[-1]
        var_etf = get_variation(etf_chf, etf_t['Close'].iloc[-2])

        # Ratio et Dollars
        ratio = g_usd / s_usd

        # Construction du message final
        report = (
            "🕒 **RAPPORT HORAIRE DES COURS**\n"
            "━━━━━━━━━━━━━━━\n"
            "🇨🇭 **EN FRANCS SUISSES (CHF)**\n"
            f"🟡 Or l'once : `{g_chf:.2f} CHF` ({var_g_chf})\n"
            f"⚪️ Argent l'once : `{s_chf:.2f} CHF` ({var_s_chf})\n"
            f"⚪️ Argent le kilo : `{s_kilo_chf:,.2f} CHF` ({var_s_kilo_chf})\n"
            f"📉 ETF ZKB : `{etf_chf:.2f} CHF` ({var_etf})\n\n"
            "🇺🇸 **EN DOLLARS (USD)**\n"
            f"🟡 Or l'once : `${g_usd:.2f}`\n"
            f"⚪️ Argent l'once : `${s_usd:.2f}`\n"
            f"⚪️ Argent le kilo : `${s_usd * to_kilo:,.2f}`\n"
            "━━━━━━━━━━━━━━━\n"
            f"⚖️ **Ratio Or/Arg : {ratio:.2f}**\n"
            f"📈 **Change** : 1$ = `{rate:.4f} CHF`"
        )
        return report
    except Exception as e:
        return f"⚠️ Erreur : {e}"

def monitor():
    while True:
        if MY_CHAT_ID != "929066398":
            report = get_full_report()
            try:
                bot.send_message(MY_CHAT_ID, report, parse_mode='Markdown')
            except:
                pass
        time.sleep(3600)

@bot.message_handler(commands=['check', 'start'])
def manual_check(message):
    report = get_full_report()
    bot.reply_to(message, report, parse_mode='Markdown')

if __name__ == "__main__":
    threading.Thread(target=monitor, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
