import os
import telebot
import threading
import yfinance as yf
import time
from flask import Flask

app = Flask(__name__)
TOKEN = os.environ.get('TELEGRAM_TOKEN')
MY_CHAT_ID = "929066398" 
bot = telebot.TeleBot(TOKEN)

@app.route('/')
def health(): return "Bot en ligne", 200

def get_variation(current, previous):
    if previous is None or previous == 0: return "0.00%"
    var = ((current - previous) / previous) * 100
    icon = "📈 +" if var > 0 else "📉 "
    return f"{icon}{var:.2f}%"

def get_full_report():
    try:
        # On demande 5 jours pour être sûr d'avoir des données même le lundi matin
        gold_t = yf.Ticker("GC=F").history(period="5d")
        silver_t = yf.Ticker("SI=F").history(period="5d")
        etf_t = yf.Ticker("ZSILC.SW").history(period="5d") # Ticker CHF
        fx_t = yf.Ticker("USDCHF=X").history(period="5d")

        # Sécurité : Vérifier si on a assez de données
        if len(gold_t) < 1 or len(fx_t) < 1:
            return "⚠️ Marchés fermés ou données indisponibles."

        # Prix Actuels (Dernière ligne)
        rate = fx_t['Close'].iloc[-1]
        g_usd = gold_t['Close'].iloc[-1]
        s_usd = silver_t['Close'].iloc[-1]
        etf_chf = etf_t['Close'].iloc[-1] if not etf_t.empty else 0
        
        # Prix Précédents (Avant-dernière ligne si elle existe)
        has_prev = len(gold_t) >= 2
        rate_prev = fx_t['Close'].iloc[-2] if has_prev else rate
        g_usd_prev = gold_t['Close'].iloc[-2] if has_prev else g_usd
        s_usd_prev = silver_t['Close'].iloc[-2] if has_prev else s_usd
        etf_prev = etf_t['Close'].iloc[-2] if (not etf_t.empty and len(etf_t) >= 2) else etf_chf

        # Calculs CHF
        to_kilo = 32.1507
        g_chf = g_usd * rate
        s_chf = s_usd * rate
        s_kilo_chf = s_chf * to_kilo
        
        # Variations
        var_g = get_variation(g_chf, g_usd_prev * rate_prev)
        var_s = get_variation(s_chf, s_usd_prev * rate_prev)
        var_k = get_variation(s_kilo_chf, (s_usd_prev * to_kilo) * rate_prev)
        var_etf = get_variation(etf_chf, etf_prev)

        ratio = g_usd / s_usd

        report = (
            "🕒 **RAPPORT HORAIRE DES COURS**\n"
            "━━━━━━━━━━━━━━━\n"
            "🇨🇭 **EN FRANCS SUISSES (CHF)**\n"
            f"🟡 Or l'once : `{g_chf:.2f} CHF` ({var_g})\n"
            f"⚪️ Argent l'once : `{s_chf:.2f} CHF` ({var_s})\n"
            f"⚪️ Argent le kilo : `{s_kilo_chf:,.2f} CHF` ({var_k})\n"
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
        return f"⚠️ Erreur : {str(e)}"

def monitor():
    while True:
        if MY_CHAT_ID != "929066398":
            report = get_full_report()
            try:
                bot.send_message(MY_CHAT_ID, report, parse_mode='Markdown')
            except: pass
        time.sleep(3600)

@bot.message_handler(commands=['check', 'start'])
def manual_check(message):
    bot.reply_to(message, get_full_report(), parse_mode='Markdown')

if __name__ == "__main__":
    threading.Thread(target=monitor, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
