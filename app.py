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
MY_CHAT_ID = "929066398" # <--- METS TON ID ICI
bot = telebot.TeleBot(TOKEN)

@app.route('/')
def health(): return "Bot Gold/Silver Pro Active", 200

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

# --- GÉNÉRATEUR DE RAPPORT ---
def get_full_report():
    gold_t = yf.Ticker("GC=F").history(period="5d")
    silver_t = yf.Ticker("SI=F").history(period="5d")
    fx_t = yf.Ticker("USDCHF=X").history(period="5d")

    rate = fx_t['Close'].iloc[-1]
    g_usd = gold_t['Close'].iloc[-1]
    s_usd = silver_t['Close'].iloc[-1]
    etf_chf = get_etf_price()

    to_kilo = 32.1507
    g_chf, s_chf = g_usd * rate, s_usd * rate
    s_kg_chf = s_chf * to_kilo
    
    _, var_g_str = get_variation_raw(g_usd, gold_t['Close'].iloc[-2])
    _, var_s_str = get_variation_raw(s_usd, silver_t['Close'].iloc[-2])

    report = (
        "🕒 **RAPPORT MARCHÉ**\n"
        "━━━━━━━━━━━━━━━\n"
        "🇨🇭 **EN FRANCS SUISSES (CHF)**\n"
        f"🟡 Or oz : `{g_chf:.2f} CHF`\n"
        f"⚪️ Argent oz : `{s_chf:.2f} CHF`\n"
        f"⚪️ Argent kg : `{f'{s_kg_chf:.2f}'.replace(',', '')} CHF`\n"
        f"📉 ETF ZKB (ZSILC) : `{etf_chf:.2f} CHF`\n\n"
        "🇺🇸 **EN DOLLARS (USD)**\n"
        f"🟡 Or oz : `${g_usd:.2f}`\n"
        f"⚪️ Argent oz : `${s_usd:.2f}`\n"
        f"⚪️ Argent kg : `${f'{s_usd * to_kilo:.2f}'.replace(',', '')}`\n"
        "━━━━━━━━━━━━━━━\n"
        f"🟡 Var. Or : {var_g_str}\n"
        f"⚪️ Var. Arg : {var_s_str}\n"
        f"⚖️ **Ratio Or/Arg : {g_usd/s_usd:.2f}**"
    )
    return report

# --- ALERTES DE MANIPULATION ET AUTOMATISATION ---
def monitor():
    last_g = None
    last_s = None
    
    while True:
        try:
            # 1. Envoi du rapport horaire (toutes les 60 min)
            report = get_full_report()
            if MY_CHAT_ID != "929066398":
                bot.send_message(MY_CHAT_ID, report, parse_mode='Markdown')
            
            # 2. Détection de manipulation (mouvement > 2% en 1h)
            current_g = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1]
            current_s = yf.Ticker("SI=F").history(period="1d")['Close'].iloc[-1]
            
            if last_g and last_s:
                var_g, _ = get_variation_raw(current_g, last_g)
                var_s, _ = get_variation_raw(current_s, last_s)
                
                # Alerte si variation absolue > 2%
                if abs(var_g) >= 2.0 or abs(var_s) >= 2.0:
                    alert_msg = "🚨 **ALERTE MANIPULATION / VOLATILITÉ** 🚨\n\n"
                    if abs(var_g) >= 2.0: alert_msg += f"🟡 Or : {var_g:.2f}% en 1h !\n"
                    if abs(var_s) >= 2.0: alert_msg += f"⚪️ Argent : {var_s:.2f}% en 1h !\n"
                    bot.send_message(MY_CHAT_ID, alert_msg, parse_mode='Markdown')
            
            last_g, last_s = current_g, current_s
            
        except Exception as e:
            print(f"Erreur monitor: {e}")
            
        time.sleep(3600) # Attente 1 heure

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
        r = f_t['Close'].iloc[-1]
        poids_arg_kg = (38 * 0.0311035) + (100 / 1000) + 6.0
        val_or = (g_t['Close'].iloc[-1] * r) * 5
        val_arg = (s_t['Close'].iloc[-1] * r * 32.1507) * poids_arg_kg
        res = f"🏦 **VALEUR DU COFFRE**\n━━━━━━━━━━━━━━━\n🟡 **OR** : `{val_or:.2f} CHF`\n⚪️ **ARGENT** : `{val_arg:.2f} CHF`\n━━━━━━━━━━━━━━━\n💰 **TOTAL : {val_or + val_arg:.2f} CHF**"
        bot.reply_to(message, res, parse_mode='Markdown')
    except Exception as e: bot.reply_to(message, f"Erreur coffre : {e}")

if __name__ == "__main__":
    threading.Thread(target=monitor, daemon=True).start()
    bot.infinity_polling()
