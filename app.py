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

# --- RÉCUPÉRATION ETF ZKB (VIA yahoo FINANCE) ---
def get_etf_price():
    # Ticker officiel Yahoo pour la classe CHF (18313602)
    ticker_reel = "ZSILHC.SW" 
    
    try:
        # On interroge Yahoo Finance
        etf = yf.Ticker(ticker_reel)
        data = etf.history(period="1d")
        
        if not data.empty:
            return data['Close'].iloc[-1]
        
        # Sécurité si le marché est fermé (on prend le dernier cours connu sur 5 jours)
        data_back = etf.history(period="5d")
        if not data_back.empty:
            return data_back['Close'].iloc[-1]
            
    except Exception as e:
        print(f"Erreur de récupération : {e}")
        
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
            if str(MY_CHAT_ID) != "929066398":
                t_g = yf.Ticker("GC=F").history(period="1d")
                t_s = yf.Ticker("SI=F").history(period="1d")
                if not t_g.empty and not t_s.empty:
                    cg, cs = t_g['Close'].iloc[-1], t_s['Close'].iloc[-1]
                    if last_g is not None and last_s is not None:
                        vg, vs = ((cg-last_g)/last_g)*100, ((cs-last_s)/last_s)*100
                        if abs(vg) >= 2.0 or abs(vs) >= 2.0:
                            bot.send_message(MY_CHAT_ID, f"🚨 **ALERTE**\nOr: {vg:+.2f}% | Arg: {vs:+.2f}%", parse_mode='Markdown')
                    last_g, last_s = cg, cs
        except: pass
        time.sleep(3600)

# --- COMMANDES (SÉCURITÉ STRICTE) ---

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

        r_now = f_data['Close'].iloc[-1]
        p_oz_g, p_oz_s = g_data['Close'].iloc[-1] * r_now, s_data['Close'].iloc[-1] * r_now
        p_kg_s = p_oz_s * 32.1507
        p_gr_s = p_kg_s / 1000

        r_old = f_data['Close'].iloc[-2]
        p_oz_g_old, p_oz_s_old = g_data['Close'].iloc[-2] * r_old, s_data['Close'].iloc[-2] * r_old
        p_kg_s_old = p_oz_s_old * 32.1507
        p_gr_s_old = p_kg_s_old / 1000

        # Calcul Totaux
        total_now = (5 * p_oz_g) + (38 * p_oz_s) + (100 * p_gr_s) + (6 * p_kg_s)
        old_total = (5 * p_oz_g_old) + (38 * p_oz_s_old) + (100 * p_gr_s_old) + (6 * p_kg_s_old)
        
        diff_chf = total_now - old_total
        diff_perc = (diff_chf / old_total) * 100

        res = (
            "🏦 **INVENTAIRE DU COFFRE**\n"
            "━━━━━━━━━━━━━━━\n"
            f"🟡 5 oz d'or : `{5 * p_oz_g:.2f} CHF`\n"
            f"⚪ 38 oz argent : `{38 * p_oz_s:.2f} CHF`\n"
            f"⚪ 100 g argent : `{100 * p_gr_s:.2f} CHF`\n"
            f"⚪ 6 kg argent : `{6 * p_kg_s:.2f} CHF`\n"
            "━━━━━━━━━━━━━━━\n"
            f"💰 **TOTAL : {total_now:.2f} CHF**\n\n"
            f"{'📈' if diff_chf > 0 else '📉'} **Variation 24h :**\n"
            f"`{diff_chf:+.2f} CHF` ({diff_perc:+.2f}%)"
        )
        bot.reply_to(message, res, parse_mode='Markdown')
    except:
        bot.reply_to(message, "⚠️ Erreur calcul coffre.")

if __name__ == "__main__":
    threading.Thread(target=monitor, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
