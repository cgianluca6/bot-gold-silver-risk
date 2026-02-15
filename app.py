import os
import telebot
import threading
import yfinance as yf
import time
import requests
from bs4 import BeautifulSoup
from flask import Flask

# --- INITIALISATION ---
app = Flask(__name__)
TOKEN = os.environ.get('TELEGRAM_TOKEN')
MY_CHAT_ID = "929066398" # <--- METS TON ID ICI
bot = telebot.TeleBot(TOKEN)

@app.route('/')
def health(): return "Bot Gold/Silver Pro Active", 200

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

# --- GÉNÉRATEUR DE RAPPORT ---
def get_full_report():
    try:
        g_t = yf.Ticker("GC=F").history(period="5d")
        s_t = yf.Ticker("SI=F").history(period="5d")
        f_t = yf.Ticker("USDCHF=X").history(period="5d")

        rate = f_t['Close'].iloc[-1]
        g_usd = g_t['Close'].iloc[-1]
        s_usd = s_t['Close'].iloc[-1]
        etf_chf = get_etf_price()

        to_kilo = 32.1507
        g_chf, s_chf = g_usd * rate, s_usd * rate
        
        # Variations Spot %
        v_g = ((g_usd - g_t['Close'].iloc[-2]) / g_t['Close'].iloc[-2]) * 100
        v_s = ((s_usd - s_t['Close'].iloc[-2]) / s_t['Close'].iloc[-2]) * 100

        report = (
            "🕒 **RAPPORT MARCHÉ COMPLET**\n"
            "━━━━━━━━━━━━━━━\n"
            "🇨🇭 **EN FRANCS SUISSES (CHF)**\n"
            f"🟡 Or oz : `{g_chf:.2f} CHF`\n"
            f"⚪️ Argent oz : `{s_chf:.2f} CHF`\n"
            f"⚪️ Argent kg : `{f'{s_chf * to_kilo:.2f}'.replace(',', '')} CHF`\n"
            f"📉 ETF ZKB : `{etf_chf:.2f} CHF`\n\n"
            "🇺🇸 **EN DOLLARS (USD)**\n"
            f"🟡 Or oz : `${g_usd:.2f}`\n"
            f"⚪️ Argent oz : `${s_usd:.2f}`\n"
            f"⚪️ Argent kg : `${f'{s_usd * to_kilo:.2f}'.replace(',', '')}`\n"
            "━━━━━━━━━━━━━━━\n"
            f"🟡 Var. Or : {'📈' if v_g > 0 else '📉'} {v_g:+.2f}%\n"
            f"⚪️ Var. Arg : {'📈' if v_s > 0 else '📉'} {v_s:+.2f}%\n"
            f"⚖️ **Ratio Or/Arg : {g_usd/s_usd:.2f}**"
        )
        return report
    except Exception as e: return f"Erreur rapport : {e}"

# --- AUTOMATISATION ET ALERTES ---
def monitor():
    last_g, last_s = None, None
    while True:
        try:
            if MY_CHAT_ID != "929066398":
                # 1. Rapport horaire automatique
                bot.send_message(MY_CHAT_ID, get_full_report(), parse_mode='Markdown')
                
                # 2. Détection de manipulation (> 2% en 1h)
                curr_g = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1]
                curr_s = yf.Ticker("SI=F").history(period="1d")['Close'].iloc[-1]
                
                if last_g and last_s:
                    v_g = ((curr_g - last_g) / last_g) * 100
                    v_s = ((curr_s - last_s) / last_s) * 100
                    if abs(v_g) >= 2.0 or abs(v_s) >= 2.0:
                        bot.send_message(MY_CHAT_ID, f"🚨 **ALERTE MANIPULATION**\nMouvement brutal détecté :\nOr: {v_g:+.2f}% | Arg: {v_s:+.2f}%", parse_mode='Markdown')
                
                last_g, last_s = curr_g, curr_s
        except: pass
        time.sleep(3600) # Boucle toutes les heures

# --- COMMANDES ---
@bot.message_handler(commands=['check', 'start'])
def manual_check(message):
    bot.reply_to(message, get_full_report(), parse_mode='Markdown')

@bot.message_handler(commands=['coffre'])
def calcul_coffre(message):
    try:
        g_t = yf.Ticker("GC=F").history(period="2d")
        s_t = yf.Ticker("SI=F").history(period="2d")
        f_t = yf.Ticker("USDCHF=X").history(period="2d")
        
        r_now, r_old = f_t['Close'].iloc[-1], f_t['Close'].iloc[-2]
        p_g_now, p_g_old = g_t['Close'].iloc[-1] * r_now, g_t['Close'].iloc[-2] * r_old
        p_s_now, p_s_old = s_t['Close'].iloc[-1] * r_now, s_t['Close'].iloc[-2] * r_old

        kg_arg = (38 * 0.0311035) + 0.1 + 6.0
        
        # Valeurs actuelles détaillées
        v_or_5oz = 5 * p_g_now
        v_arg_total = kg_arg * p_s_now * 32.1507
        total_now = v_or_5oz + v_arg_total
        
        # Variation 24h
        total_old = (5 * p_g_old) + (kg_arg * p_s_old * 32.1507)
        diff_chf = total_now - total_old

        res = (
            "🏦 **DÉTAIL DU COFFRE (CHF)**\n"
            "━━━━━━━━━━━━━━━\n"
            f"🟡 **OR** (5 oz) : `{v_or_5oz:.2f} CHF`\n"
            f"⚪ **ARGENT** ({kg_arg:.3f} kg) : `{v_arg_total:.2f} CHF`\n"
            "━━━━━━━━━━━━━━━\n"
            f"💰 **TOTAL : {total_now:.2f} CHF**\n\n"
            f"{'📈' if diff_chf > 0 else '📉'} **Variation 24h :**\n"
            f"`{diff_chf:+.2f} CHF` ({ (diff_chf/total_old)*100:+.2f}%)"
        )
        bot.reply_to(message, res, parse_mode='Markdown')
    except: bot.reply_to(message, "⚠️ Erreur calcul coffre")

# --- LANCEMENT ---
if __name__ == "__main__":
    threading.Thread(target=monitor, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
