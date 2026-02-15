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
def health(): return "Bot Gold/Silver Pro Active", 200

# --- RÉCUPÉRATION ETF ---
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
        g_t = yf.Ticker("GC=F").history(period="5d")
        s_t = yf.Ticker("SI=F").history(period="5d")
        f_t = yf.Ticker("USDCHF=X").history(period="5d")

        rate = f_t['Close'].iloc[-1]
        g_usd = g_t['Close'].iloc[-1]
        s_usd = s_t['Close'].iloc[-1]
        etf_chf = get_etf_price()
        to_kilo = 32.1507

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
                bot.send_message(MY_CHAT_ID, get_full_report(), parse_mode='Markdown')
                t_g = yf.Ticker("GC=F").history(period="1d")
                t_s = yf.Ticker("SI=F").history(period="1d")
                if not t_g.empty and not t_s.empty:
                    cg, cs = t_g['Close'].iloc[-1], t_s['Close'].iloc[-1]
                    if last_g is not None and last_s is not None:
                        vg, vs = ((cg-last_g)/last_g)*100, ((cs-last_s)/last_s)*100
                        if abs(vg) >= 2.0 or abs(vs) >= 2.0:
                            alert = "🚨 **ALERTE MANIPULATION** 🚨\n\n"
                            if abs(vg) >= 2.0: alert += f"🟡 Or : {vg:+.2f}%\n"
                            if abs(vs) >= 2.0: alert += f"⚪ Argent : {vs:+.2f}%\n"
                            bot.send_message(MY_CHAT_ID, alert, parse_mode='Markdown')
                    last_g, last_s = cg, cs
        except: pass
        time.sleep(3600)

# --- COMMANDES ---

@bot.message_handler(commands=['check', 'start'])
def manual_check(message):
    if str(message.chat.id) != str(MY_CHAT_ID):
        bot.reply_to(message, "❌ Accès refusé.")
        return
    bot.reply_to(message, get_full_report(), parse_mode='Markdown')

@bot.message_handler(commands=['coffre'])
def calcul_coffre(message):
    if str(message.chat.id) != str(MY_CHAT_ID):
        bot.reply_to(message, "❌ Accès réservé.")
        return
    try:
        g_data = yf.Ticker("GC=F").history(period="5d")
        s_data = yf.Ticker("SI=F").history(period="5d")
        f_data = yf.Ticker("USDCHF=X").history(period="5d")

        # PRIX ACTUELS (Maintenant)
        r_now = f_data['Close'].iloc[-1]
        p_oz_g = g_data['Close'].iloc[-1] * r_now
        p_oz_s = s_data['Close'].iloc[-1] * r_now
        p_kg_s = p_oz_s * 32.1507
        p_gr_s = p_kg_s / 1000

        # PRIX HIER (Pour variation)
        r_old = f_data['Close'].iloc[-2]
        p_oz_g_old = g_data['Close'].iloc[-2] * r_old
        p_oz_s_old = s_data['Close'].iloc[-2] * r_old
        p_kg_s_old = p_oz_s_old * 32.1507
        p_gr_s_old = p_kg_s_old / 1000

        # CALCUL INVENTAIRE ACTUEL
        v_5or = 5 * p_oz_g
        v_38arg = 38 * p_oz_s
        v_100g = 100 * p_gr_s
        v_6kg = 6 * p_kg_s
        total_now = v_5or + v_38arg + v_100g + v_6kg

        # CALCUL INVENTAIRE HIER
        old_total = (5 * p_oz_g_old) + (38 * p_oz_s_old) + (100 * p_gr_s_old) + (6 * p_kg_s_old)
        
        diff_chf = total_now - old_total
        diff_perc = (diff_chf / old_total) * 100

        res = (
            "🏦 **INVENTAIRE DÉTAILLÉ DU COFFRE**\n"
            "━━━━━━━━━━━━━━━\n"
            "🟡 **OR PHYSIQUE**\n"
            f"• 5 oz d'or : `{v_5or:.2f} CHF`\n\n"
            "⚪ **ARGENT PHYSIQUE**\n"
            f"• 38 oz argent : `{v_38arg:.2f} CHF`\n"
            f"• 100 g argent : `{v_100g:.2f} CHF`\n"
            f"• 6 kg argent : `{v_6kg:.2f} CHF`\n"
            "━━━━━━━━━━━━━━━\n"
            f"💰 **TOTAL : {total_now:.2f} CHF**\n\n"
            f"{'📈' if diff_chf > 0 else '📉'} **Variation 24h :**\n"
            f"`{diff_chf:+.2f} CHF` ({diff_perc:+.2f}%)"
        )
        bot.reply_to(message, res, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, "⚠️ Erreur technique lors du calcul.")

if __name__ == "__main__":
    threading.Thread(target=monitor, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
