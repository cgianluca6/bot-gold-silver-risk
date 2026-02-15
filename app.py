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

# --- RÉCUPÉRATION ETF (SÉCURISÉE) ---
def get_etf_price():
    url = "https://www.finanzen.ch/etf/swisscanto-ch-silver-etf-eah-ch0183136024"
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        price_tag = soup.find("span", class_="price-section__current-value")
        if price_tag:
            txt = price_tag.get_text(strip=True).replace("'", "").replace("CHF", "").replace(" ", "")
            return float(txt)
    except: pass
    return 0.0

# --- GÉNÉRATEUR DE RAPPORT MARCHÉ ---
def get_full_report():
    try:
        # On prend 5 jours pour garantir d'avoir "hier" même le lundi
        g_t = yf.Ticker("GC=F").history(period="5d")
        s_t = yf.Ticker("SI=F").history(period="5d")
        f_t = yf.Ticker("USDCHF=X").history(period="5d")

        rate = f_t['Close'].iloc[-1]
        g_usd = g_t['Close'].iloc[-1]
        s_usd = s_t['Close'].iloc[-1]
        etf_chf = get_etf_price()
        to_kilo = 32.1507

        # Variations Marché 24h
        v_g = ((g_usd - g_t['Close'].iloc[-2]) / g_t['Close'].iloc[-2]) * 100
        v_s = ((s_usd - s_t['Close'].iloc[-2]) / s_t['Close'].iloc[-2]) * 100

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
            f"🟡 Var. Or : {'📈' if v_g > 0 else '📉'} {v_g:+.2f}%\n"
            f"⚪ Var. Arg : {'📈' if v_s > 0 else '📉'} {v_s:+.2f}%\n"
            f"⚖️ **Ratio Or/Arg : {g_usd/s_usd:.2f}**"
        )
        return report
    except Exception as e: return f"⚠️ Erreur Marché : {e}"

# --- MONITORING & ALERTES ---
def monitor():
    last_g, last_s = None, None
    while True:
        try:
            if MY_CHAT_ID != "929066398":
                # Rapport horaire
                bot.send_message(MY_CHAT_ID, get_full_report(), parse_mode='Markdown')
                
                # Alerte Manipulation (2% en 1h)
                ticker_g = yf.Ticker("GC=F").history(period="1d")
                ticker_s = yf.Ticker("SI=F").history(period="1d")
                if not ticker_g.empty and not ticker_s.empty:
                    c_g, c_s = ticker_g['Close'].iloc[-1], ticker_s['Close'].iloc[-1]
                    if last_g and last_s:
                        vg = ((c_g - last_g) / last_g) * 100
                        vs = ((c_s - last_s) / last_s) * 100
                        if abs(vg) >= 2.0 or abs(vs) >= 2.0:
                            bot.send_message(MY_CHAT_ID, f"🚨 **ALERTE MANIPULATION**\nOr: {vg:+.2f}% | Arg: {vs:+.2f}%", parse_mode='Markdown')
                    last_g, last_s = c_g, c_s
        except: pass
        time.sleep(3600)

# --- COMMANDE COFFRE (DÉTAILLÉ + VARIATION 24H) ---
@bot.message_handler(commands=['coffre'])
def calcul_coffre(message):
    try:
        g_data = yf.Ticker("GC=F").history(period="5d")
        s_data = yf.Ticker("SI=F").history(period="5d")
        f_data = yf.Ticker("USDCHF=X").history(period="5d")

        # Actuel
        r_now = f_data['Close'].iloc[-1]
        p_g_now, p_s_now = g_data['Close'].iloc[-1] * r_now, s_data['Close'].iloc[-1] * r_now
        # Hier
        r_old = f_data['Close'].iloc[-2]
        p_g_old, p_s_old = g_data['Close'].iloc[-2] * r_old, s_data['Close'].iloc[-2] * r_old

        kg_arg = (38 * 0.0311035) + 0.1 + 6.0
        
        # Valeurs actuelles détaillées
        v_5oz_or = 5 * p_g_now
        v_38oz_arg = 38 * p_s_now
        v_100g_arg = 0.1 * p_s_now * 32.1507
        v_6kg_arg = 6 * p_s_now * 32.1507
        
        total_now = v_5oz_or + v_38oz_arg + v_100g_arg + v_6kg_arg
        total_old = (5 * p_g_old) + (kg_arg * p_s_old * 32.1507)
        diff_chf = total_now - total_old

        res = (
            "🏦 **INVENTAIRE DU COFFRE**\n"
            "━━━━━━━━━━━━━━━\n"
            f"🟡 5 oz d'or : `{v_5oz_or:.2f} CHF`\n"
            f"⚪ 38 oz argent : `{v_38oz_arg:.2f} CHF`\n"
            f"⚪ 100 g argent : `{v_100g_arg:.2f} CHF`\n"
            f"⚪ 6 kg argent : `{v_6kg_arg:.2f} CHF`\n"
            "━━━━━━━━━━━━━━━\n"
            f"💰 **TOTAL : {total_now:.2f} CHF**\n\n"
            f"{'📈' if diff_chf > 0 else '📉'} **Variation 24h :**\n"
            f"`{diff_chf:+.2f} CHF` ({ (diff_chf/total_old)*100:+.2f}%)"
        )
        bot.reply_to(message, res, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"⚠️ Erreur prix : Marchés fermés ou problème de connexion Yahoo.")

@bot.message_handler(commands=['check', 'start'])
def manual_check(message):
    bot.reply_to(message, get_full_report(), parse_mode='Markdown')

if __name__ == "__main__":
    threading.Thread(target=monitor, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
