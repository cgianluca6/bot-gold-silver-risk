import os
import telebot
import threading
import yfinance as yf
import time
import requests
from bs4 import BeautifulSoup
from flask import Flask

app = Flask(__name__)
TOKEN = os.environ.get('TELEGRAM_TOKEN')
MY_CHAT_ID = "VOTRE_ID_NUMERIQUE" 
bot = telebot.TeleBot(TOKEN)

@app.route('/')
def health(): return "Bot Gold/Silver Final Optimized", 200

def get_etf_price():
    """Récupère le prix de l'ETF ZSILC sur Finanzen.ch"""
    url = "https://www.finanzen.ch/etf/swisscanto-ch-silver-etf-eah-ch0183136024"
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        # Recherche du prix dans la structure spécifique de Finanzen.ch
        price_tag = soup.select_one('.price-section__current-value')
        if price_tag:
            price_str = price_tag.text.replace("CHF", "").replace(" ", "").replace("'", "").strip()
            return float(price_str)
        return 0.0
    except:
        return 0.0

def get_variation_raw(current, previous):
    if previous is None or previous == 0: return "0.00%"
    var = ((current - previous) / previous) * 100
    icon = "📈 +" if var > 0 else "📉 "
    return f"{icon}{var:.2f}%"

def get_full_report():
    try:
        # Données Marchés
        gold_t = yf.Ticker("GC=F").history(period="5d")
        silver_t = yf.Ticker("SI=F").history(period="5d")
        fx_t = yf.Ticker("USDCHF=X").history(period="5d")

        rate = fx_t['Close'].iloc[-1]
        g_usd = gold_t['Close'].iloc[-1]
        s_usd = silver_t['Close'].iloc[-1]
        
        # PRIX ETF (Finanzen.ch)
        etf_chf = get_etf_price()
        if etf_chf == 0: # Backup si le site est HS
            etf_chf = (s_usd * rate) * 4.65 

        # Calculs CHF
        to_kilo = 32.1507
        g_chf = g_usd * rate
        s_chf = s_usd * rate
        s_kg_chf = s_chf * to_kilo
        
        # Variations (Calculées sur le spot USD pour la précision)
        var_g = get_variation_raw(g_usd, gold_t['Close'].iloc[-2])
        var_s = get_variation_raw(s_usd, silver_t['Close'].iloc[-2])

        # Ratio
        ratio = g_usd / s_usd

        # Nettoyage des milliers (pas de virgule)
        fmt_sk_chf = f"{s_kg_chf:.2f}".replace(",", "")
        fmt_sk_usd = f"{s_usd * to_kilo:.2f}".replace(",", "")

        report = (
            "🕒 **RAPPORT HORAIRE**\n"
            "━━━━━━━━━━━━━━━\n"
            "🇨🇭 **EN FRANCS SUISSES (CHF)**\n"
            f"🟡 Or oz : `{g_chf:.2f} CHF`\n"
            f"⚪️ Argent oz : `{s_chf:.2f} CHF`\n"
            f"⚪️ Argent kg : `{fmt_sk_chf} CHF`\n"
            f"📉 ETF ZKB : `{etf_chf:.2f} CHF`\n\n"
            "🇺🇸 **EN DOLLARS (USD)**\n"
            f"🟡 Or oz : `${g_usd:.2f}`\n"
            f"⚪️ Argent oz : `${s_usd:.2f}`\n"
            f"⚪️ Argent kg : `${fmt_sk_usd}`\n"
            "━━━━━━━━━━━━━━━\n"
            f"🟡 Var. Or : {var_g}\n"
            f"⚪️ Var. Arg : {var_s}\n"
            f"⚖️ **Ratio Or/Arg : {ratio:.2f}**"
        )
        return report
    except Exception as e:
        return f"⚠️ Erreur : {str(e)}"

def monitor():
    while True:
        if MY_CHAT_ID != "VOTRE_ID_NUMERIQUE":
            report = get_full_report()
            try: bot.send_message(MY_CHAT_ID, report, parse_mode='Markdown')
            except: pass
        time.sleep(3600)

@bot.message_handler(commands=['check', 'start'])
def manual_check(message):
    bot.reply_to(message, get_full_report(), parse_mode='Markdown')

if __name__ == "__main__":
    threading.Thread(target=monitor, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
