import os
import telebot
import threading
import yfinance as yf
import time
import requests
from bs4 import BeautifulSoup
from flask import Flask

# --- CONFIGURATION ---
app = Flask(__name__)
TOKEN = os.environ.get('TELEGRAM_TOKEN')
MY_CHAT_ID = "929066398" # <--- METS TON ID ICI
bot = telebot.TeleBot(TOKEN)

@app.route('/')
def health(): return "Bot Gold/Silver Pro Ready", 200

# --- SCRAPING ETF ---
def get_etf_price():
    url = "https://www.finanzen.ch/etf/swisscanto-ch-silver-etf-eah-ch0183136024"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        price_tag = soup.find("span", class_="price-section__current-value")
        if price_tag:
            return float(price_tag.text.replace("'", "").replace("CHF", "").replace(" ", "").strip())
    except: pass
    return 0.0

# --- GÉNÉRATEUR DE RAPPORT (CHECK) ---
def get_full_report():
    try:
        g_t = yf.Ticker("GC=F").history(period="2d")
        s_t = yf.Ticker("SI=F").history(period="2d")
        f_t = yf.Ticker("USDCHF=X").history(period="2d")

        rate = f_t['Close'].iloc[-1]
        g_usd = g_t['Close'].iloc[-1]
        s_usd = s_t['Close'].iloc[-1]
        etf_chf = get_etf_price()
        to_kilo = 32.1507

        report = (
            "🕒 **RAPPORT MARCHÉ**\n"
            "━━━━━━━━━━━━━━━\n"
            "🇨🇭 **EN FRANCS SUISSES (CHF)**\n"
            f"🟡 Or oz : `{g_usd * rate:.2f} CHF`\n"
            f"⚪ Argent oz : `{s_usd * rate:.2f} CHF`\n"
            f"⚪ Argent kg : `{f'{s_usd * rate * to_kilo:.2f}'.replace(',', '')} CHF`\n"
            f"📉 ETF ZKB : `{etf_chf:.2f} CHF`\n\n"
            "🇺🇸 **EN DOLLARS (USD)**\n"
            f"🟡 Or oz : `${g_usd:.2f}`\n"
            f"⚪ Argent oz : `${s_usd:.2f}`\n"
            "━━━━━━━━━━━━━━━\n"
            f"⚖️ **Ratio Or/Arg : {g_usd/s_usd:.2f}**"
        )
        return report
    except Exception as e: return f"⚠️ Erreur marché : {e}"

# --- MONITORING ET ALERTES ---
def monitor():
    last_g, last_s = None, None
    while True:
        try:
            if MY_CHAT_ID != "929066398":
                bot.send_message(MY_CHAT_ID, get_full_report(), parse_mode='Markdown')
                
                # Alertes Manipulation (Mouvement > 2% en 1h)
                c_g = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1]
                c_s = yf.Ticker("SI=F").history(period="1d")['Close'].iloc[-1]
                if last_g and last_s:
                    v_g = ((c_g - last_g) / last_g) * 100
                    v_s = ((c_s - last_s) / last_s) * 100
                    if abs(v_g) >= 2.0 or abs(v_s) >= 2.0:
                        bot.send_message(MY_CHAT_ID, f"🚨 **ALERTE MANIPULATION**\nOr: {v_g:+.2f}% | Arg: {v_s:+.2f}%", parse_mode='Markdown')
                last_g, last_s = c_g, c_s
        except: pass
        time.sleep(3600)

# --- COMMANDES ---
@bot.message_handler(commands=['check', 'start'])
def manual_check(message):
    bot.reply_to(message, get_full_report(), parse_mode='Markdown')

@bot.message_handler(commands=['coffre'])
def calcul_coffre(message):
    try:
        # Données Spot temps réel
        g_now = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1]
        s_now = yf.Ticker("SI=F").history(period="1d")['Close'].iloc[-1]
        rate = yf.Ticker("USDCHF=X").history(period="1d")['Close'].iloc[-1]

        # Prix Unitaires CHF
        p_oz_g = g_now * rate
        p_oz_s = s_now * rate
        p_kg_s = p_oz_s * 32.1507
        p_gr_s = p_kg_s / 1000

        # Détail des lignes
        v_5oz_or = 5 * p_oz_g
        v_38oz_arg = 38 * p_oz_s
        v_100g_arg = 100 * p_gr_s
        v_6kg_arg = 6 * p_kg_s

        total_arg = v_38oz_arg + v_100g_arg + v_6kg_arg
        total_gen = v_5oz_or + total_arg

        res = (
            "🏦 **INVENTAIRE DÉTAILLÉ DU COFFRE**\n"
            "━━━━━━━━━━━━━━━\n"
            "🟡 **OR**\n"
            f"• 5 oz d'or : `{v_5oz_or:.2f} CHF`\n\n"
            "⚪ **ARGENT**\n"
            f"• 38 oz d'argent : `{v_38oz_arg:.2f} CHF`\n"
            f"• 100 g d'argent : `{v_100g_arg:.2f} CHF`\n"
            f"• 6 kg d'argent : `{v_6kg_arg:.2f} CHF`\n"
            "━━━━━━━━━━━━━━━\n"
            f"💰 **TOTAL ARGENT : {total_arg:.2f} CHF**\n"
            f"🏆 **VALEUR TOTALE : {total_gen:.2f} CHF**"
        )
        bot.reply_to(message, res, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, "⚠️ Erreur de calcul : impossible de récupérer les prix actuels.")

# --- LANCEMENT ---
if __name__ == "__main__":
    threading.Thread(target=monitor, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
