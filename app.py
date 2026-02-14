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
def health(): return "Bot Gold/Silver Stable Ready", 200

def get_variation(current, previous):
    if previous is None or previous == 0: return "0.00%"
    var = ((current - previous) / previous) * 100
    icon = "📈 +" if var > 0 else "📉 "
    return f"{icon}{var:.2f}%"

def get_full_report():
    try:
        # On récupère 5 jours pour éviter le 0 du week-end
        gold_t = yf.Ticker("GC=F").history(period="5d")
        silver_t = yf.Ticker("SI=F").history(period="5d")
        etf_t = yf.Ticker("ZSIL.SW").history(period="5d")
        fx_t = yf.Ticker("USDCHF=X").history(period="5d")

        if gold_t.empty or fx_t.empty:
            return "⚠️ Données indisponibles (Marchés fermés)."

        # Prix Actuels
        rate = fx_t['Close'].iloc[-1]
        g_usd = gold_t['Close'].iloc[-1]
        s_usd = silver_t['Close'].iloc[-1]
        
        # Correction ETF : si ZSIL.SW est vide, on utilise une estimation
        if not etf_t.empty and etf_t['Close'].iloc[-1] > 0:
            etf_chf = etf_t['Close'].iloc[-1]
            etf_prev = etf_t['Close'].iloc[-2] if len(etf_t) >= 2 else etf_chf
        else:
            # Estimation (ZKB Silver ETF est environ égal à 5oz d'argent)
            etf_chf = (s_usd * rate) * 5 
            etf_prev = etf_chf

        # Variables de calcul
        to_kilo = 32.1507
        g_chf = g_usd * rate
        s_chf = s_usd * rate
        s_kg_chf = s_chf * to_kilo
        
        # Comparaison veille
        has_prev = len(gold_t) >= 2
        r_prev = fx_t['Close'].iloc[-2] if has_prev else rate
        g_prev = gold_t['Close'].iloc[-2] * r_prev if has_prev else g_chf
        s_prev = silver_t['Close'].iloc[-2] * r_prev if has_prev else s_chf
        sk_prev = (silver_t['Close'].iloc[-2] * to_kilo) * r_prev if has_prev else s_kg_chf

        # Formatage sans virgule pour les milliers (remplace , par rien)
        fmt_sk_chf = f"{s_kg_chf:.2f}".replace(",", "")
        fmt_sk_usd = f"{s_usd * to_kilo:.2f}".replace(",", "")

        report = (
            "🕒 **RAPPORT HORAIRE**\n"
            "━━━━━━━━━━━━━━━\n"
            "🇨🇭 **EN FRANCS SUISSES (CHF)**\n"
            f"🟡 Or oz : `{g_chf:.2f} CHF` ({get_variation(g_chf, g_prev)})\n"
            f"⚪️ Argent oz : `{s_chf:.2f} CHF` ({get_variation(s_chf, s_prev)})\n"
            f"⚪️ Argent kg : `{fmt_sk_chf} CHF` ({get_variation(s_kg_chf, sk_prev)})\n"
            f"📉 ETF ZKB : `{etf_chf:.2f} CHF` ({get_variation(etf_chf, etf_prev)})\n\n"
            "🇺🇸 **EN DOLLARS (USD)**\n"
            f"🟡 Or oz : `${g_usd:.2f}`\n"
            f"⚪️ Argent oz : `${s_usd:.2f}`\n"
            f"⚪️ Argent kg : `${fmt_sk_usd}`\n"
            "━━━━━━━━━━━━━━━\n"
            f"⚖️ **Ratio Or/Arg : {g_usd/s_usd:.2f}**\n"
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
