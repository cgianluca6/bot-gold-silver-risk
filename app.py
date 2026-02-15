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
        # On récupère 5 jours pour garantir d'avoir l'historique nécessaire aux variations
        g_t = yf.Ticker("GC=F").history(period="5d")
        s_t = yf.Ticker("SI=F").history(period="5d")
        f_t = yf.Ticker("USDCHF=X").history(period="5d")

        rate = f_t['Close'].iloc[-1]
        g_usd = g_t['Close'].iloc[-1]
        s_usd = s_t['Close'].iloc[-1]
        etf_chf = get_etf_price()

        to_kilo = 32.1507
        g_chf, s_chf = g_usd * rate, s_usd * rate
        
        # Variation 24h Spot %
        v_g = ((g_usd - g_t['Close'].iloc[-2]) / g_t['Close'].iloc[-2]) * 100
        v_s = ((s_usd - s_t['Close'].iloc[-2]) / s_t['Close'].iloc[-2]) * 100

        report = (
            "🕒 **RAPPORT MARCHÉ COMPLET**\n"
            "━━━━━━━━━━━━━━━\n"
            "🇨🇭 **EN FRANCS SUISSES (CHF)**\n"
            f"🟡 Or oz : `{g_chf:.2f} CHF`\n"
            f"⚪ Argent oz : `{s_chf:.2f} CHF`\n"
            f"⚪ Argent kg : `{f'{s_chf * to_kilo:.2f}'.replace(',', '')} CHF`\n"
            f"📉 ETF ZKB : `{etf_chf:.2f} CHF`\n\n"
            "🇺🇸 **EN DOLLARS (USD)**\n"
            f"🟡 Or oz : `${g_usd:.2f}`\n"
            f"⚪ Argent oz : `${s_usd:.2f}`\n"
            f"⚪ Argent kg : `${f'{s_usd * to_kilo:.2f}'.replace(',', '')}`\n"
            "━━━━━━━━━━━━━━━\n"
            f"🟡 Var. Or : {'📈' if v_g > 0 else '📉'} {v_g:+.2f}%\n"
            f"⚪ Var. Arg : {'📈' if v_s > 0 else '📉'} {v_s:+.2f}%\n"
            f"⚖️ **Ratio Or/Arg : {g_usd/s_usd:.2f}**"
        )
        return report
    except Exception as e: return f"⚠️ Erreur marché : {e}"

# --- AUTOMATISATION ET ALERTES CONTRE LA MANIPULATION ---
def monitor():
    last_g_price = None
    last_s_price = None
    
    while True:
        try:
            if MY_CHAT_ID != "929066398":
                # 1. Envoi du rapport horaire automatique
                bot.send_message(MY_CHAT_ID, get_full_report(), parse_mode='Markdown')
                
                # 2. Détection de manipulation brutale (comparaison prix H vs prix H-1)
                ticker_g = yf.Ticker("GC=F").history(period="1d")
                ticker_s = yf.Ticker("SI=F").history(period="1d")
                
                if not ticker_g.empty and not ticker_s.empty:
                    current_g = ticker_g['Close'].iloc[-1]
                    current_s = ticker_s['Close'].iloc[-1]
                    
                    if last_g_price and last_s_price:
                        var_g = ((current_g - last_g_price) / last_g_price) * 100
                        var_s = ((current_s - last_s_price) / last_s_price) * 100
                        
                        # Seuil d'alerte à 2.0%
                        if abs(var_g) >= 2.0 or abs(var_s) >= 2.0:
                            alert = "🚨 **ALERTE MANIPULATION COURS PAPIER** 🚨\n\n"
                            alert += "Mouvement anormal détecté en 1 heure :\n"
                            if abs(var_g) >= 2.0: alert += f"🟡 Or : {var_g:+.2f}%\n"
                            if abs(var_s) >= 2.0: alert += f"⚪ Argent : {var_s:+.2f}%\n"
                            bot.send_message(MY_CHAT_ID, alert, parse_mode='Markdown')
                    
                    last_g_price = current_g
                    last_s_price = current_s
        except Exception as e:
            print(f"Erreur monitor: {e}")
            
        time.sleep(3600) # Analyse toutes les heures

# --- COMMANDES ---
@bot.message_handler(commands=['check', 'start'])
def manual_check(message):
    bot.reply_to(message, get_full_report(), parse_mode='Markdown')

@bot.message_handler(commands=['coffre'])
def calcul_coffre(message):
    try:
        g_t = yf.Ticker("GC=F").history(period="5d")
        s_t = yf.Ticker("SI=F").history(period="5d")
        f_t = yf.Ticker("USDCHF=X").history(period="5d")
        
        r_now = f_t['Close'].iloc[-1]
        p_g_now = g_t['Close'].iloc[-1] * r_now
        p_s_now = s_t['Close'].iloc[-1] * r_now
        
        # Sécurité pour le calcul de la variation (hier)
        r_old = f_t['Close'].iloc[-2]
        p_g_old = g_t['Close'].iloc[-2] * r_old
        p_s_old = s_t['Close'].iloc[-2] * r_old

        kg_arg = (38 * 0.0311035) + 0.1 + 6.0
        
        total_now = (5 * p_g_now) + (kg_arg * p_s_now * 32.1507)
        total_old = (5 * p_g_old) + (kg_arg * p_s_old * 32.1507)
        diff_chf = total_now - total_old

        res = (
            "🏦 **DÉTAIL DU COFFRE (CHF)**\n"
            "━━━━━━━━━━━━━━━\n"
            f"🟡 **OR** (5 oz) : `{5 * p_g_now:.2f} CHF`\n"
            f"⚪ **ARGENT** ({kg_arg:.3f} kg) : `{kg_arg * p_s_now * 32.1507:.2f} CHF`\n"
            "━━━━━━━━━━━━━━━\n"
            f"💰 **TOTAL : {total_now:.2f} CHF**\n\n"
            f"{'📈' if diff_chf > 0 else '📉'} **Variation 24h :**\n"
            f"`{diff_chf:+.2f} CHF` ({ (diff_chf/total_old)*100:+.2f}%)"
        )
        bot.reply_to(message, res, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, "⚠️ Erreur calcul coffre. Attendez l'ouverture des marchés.")

# --- LANCEMENT ---
if __name__ == "__main__":
    threading.Thread(target=monitor, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
