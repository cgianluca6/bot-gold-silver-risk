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
MY_CHAT_ID = "929066398E" # <--- METS TON ID ICI
bot = telebot.TeleBot(TOKEN)

@app.route('/')
def health(): return "Bot Gold/Silver Pro Ready", 200

# --- RÉCUPÉRATION ETF ---
def get_etf_price():
    url = "https://www.finanzen.ch/etf/swisscanto-ch-silver-etf-eah-ch0183136024"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        price_tag = soup.find("span", class_="price-section__current-value")
        if price_tag:
            txt = price_tag.text.replace("'", "").replace("CHF", "").replace(" ", "").strip()
            return float(txt)
        return 0.0
    except: return 0.0

def get_variation_raw(current, previous):
    if not previous or previous == 0: return 0.0, "0.00%"
    var = ((current - previous) / previous) * 100
    icon = "📈 +" if var > 0 else "📉 "
    return var, f"{icon}{var:.2f}%"

# --- RAPPORT MARCHÉ ---
def get_full_report():
    try:
        gold_t = yf.Ticker("GC=F").history(period="5d")
        silver_t = yf.Ticker("SI=F").history(period="5d")
        fx_t = yf.Ticker("USDCHF=X").history(period="5d")

        rate = fx_t['Close'].iloc[-1]
        g_usd = gold_t['Close'].iloc[-1]
        s_usd = silver_t['Close'].iloc[-1]
        etf_chf = get_etf_price()

        to_kilo = 32.1507
        g_chf, s_chf = g_usd * rate, s_usd * rate
        
        _, var_g_str = get_variation_raw(g_usd, gold_t['Close'].iloc[-2])
        _, var_s_str = get_variation_raw(s_usd, silver_t['Close'].iloc[-2])

        report = (
            "🕒 **RAPPORT MARCHÉ**\n"
            "━━━━━━━━━━━━━━━\n"
            "🇨🇭 **EN FRANCS SUISSES (CHF)**\n"
            f"🟡 Or oz : `{g_chf:.2f} CHF`\n"
            f"⚪️ Argent oz : `{s_chf:.2f} CHF`\n"
            f"⚪️ Argent kg : `{f'{s_chf * to_kilo:.2f}'.replace(',', '')} CHF`\n"
            f"📉 ETF ZKB : `{etf_chf:.2f} CHF`\n\n"
            "🇺🇸 **EN DOLLARS (USD)**\n"
            f"🟡 Or oz : `${g_usd:.2f}`\n"
            f"⚪️ Argent oz : `${s_usd:.2f}`\n"
            "━━━━━━━━━━━━━━━\n"
            f"🟡 Var. Or : {var_g_str}\n"
            f"⚪️ Var. Arg : {var_s_str}\n"
            f"⚖️ **Ratio Or/Arg : {g_usd/s_usd:.2f}**"
        )
        return report
    except Exception as e: return f"Erreur : {e}"

# --- AUTOMATISATION ET ALERTES ---
def monitor():
    last_g, last_s = None, None
    while True:
        try:
            if MY_CHAT_ID != "929066398":
                bot.send_message(MY_CHAT_ID, get_full_report(), parse_mode='Markdown')
                
                curr_g = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1]
                curr_s = yf.Ticker("SI=F").history(period="1d")['Close'].iloc[-1]
                if last_g and last_s:
                    v_g, _ = get_variation_raw(curr_g, last_g)
                    v_s, _ = get_variation_raw(curr_s, last_s)
                    if abs(v_g) >= 2.0 or abs(v_s) >= 2.0:
                        bot.send_message(MY_CHAT_ID, f"🚨 **ALERTE MOUVEMENT BRUTAL**\nOr: {v_g:.2f}% | Arg: {v_s:.2f}%")
                last_g, last_s = curr_g, curr_s
        except: pass
        time.sleep(3600)

# --- COMMANDES ---
@bot.message_handler(commands=['check', 'start'])
def manual_check(message):
    bot.reply_to(message, get_full_report(), parse_mode='Markdown')

@bot.message_handler(commands=['coffre'])
def calcul_coffre(message):
    try:
        # On récupère 2 jours de données pour comparer avec hier
        g_t = yf.Ticker("GC=F").history(period="2d")
        s_t = yf.Ticker("SI=F").history(period="2d")
        f_t = yf.Ticker("USDCHF=X").history(period="2d")
        
        # Données Actuelles
        r_now = f_t['Close'].iloc[-1]
        p_g_now = g_t['Close'].iloc[-1] * r_now
        p_s_now = s_t['Close'].iloc[-1] * r_now
        
        # Données d'hier
        r_old = f_t['Close'].iloc[-2]
        p_g_old = g_t['Close'].iloc[-2] * r_old
        p_s_old = s_t['Close'].iloc[-2] * r_old

        # Poids Argent Total en kg
        kg_arg = (38 * 0.0311035) + (100 / 1000) + 6.0
        
        # Valeurs Actuelles
        v_or_now = 5 * p_g_now
        v_arg_now = kg_arg * p_s_now * 32.1507
        total_now = v_or_now + v_arg_now

        # Valeurs Hier
        v_or_old = 5 * p_g_old
        v_arg_old = kg_arg * p_s_old * 32.1507
        total_old = v_or_old + v_arg_old

        # Variation 24h
        diff_chf = total_now - total_old
        diff_pct = (diff_chf / total_old) * 100
        signe = "+" if diff_chf > 0 else ""
        icon = "📈" if diff_chf > 0 else "📉"

        res = (
            "🏦 **DÉTAIL DU COFFRE (CHF)**\n"
            "━━━━━━━━━━━━━━━\n"
            "🟡 **OR PHYSIQUE**\n"
            f"• 5 oz : `{v_or_now:.2f} CHF`\n\n"
            "⚪️ **ARGENT PHYSIQUE**\n"
            f"• 38 oz, 100g, 6
