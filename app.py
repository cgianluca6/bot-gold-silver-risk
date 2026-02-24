import os
import time
import threading
import telebot
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from flask import Flask
from functools import wraps

# ==========================================
# ⚙️ CONFIGURATION & INVENTAIRES
# ==========================================
app = Flask(__name__)
TOKEN = os.environ.get('TELEGRAM_TOKEN')
MY_CHAT_ID = "929066398" # <--- METS TON ID ICI

bot = telebot.TeleBot(TOKEN)

# 🏦 COFFRE PHYSIQUE
COFFRE = {
    "or_oz": 5,
    "argent_oz": 38,
    "argent_g": 100,
    "argent_kg": 6
}

# 📊 PORTEFEUILLE BOURSE
BOURSE = {
    "Nvidia": {"nom": "Nvidia", "unites": 4, "ticker": "NVDA", "devise": "USD"},
    "Pictet": {"nom": "Pictet Water", "unites": 2, "ticker": "0P0000YUS1.F", "devise": "CHF"},
    "Ethereum": {"nom": "Share Ethereum", "unites": 25, "ticker": "AETH.SW", "devise": "CHF"},
    "Swisscanto": {"nom": "Swisscanto EAH", "unites": 58, "ticker": "ZSILHC.SW", "devise": "CHF"},
    "Raiffeisen": {"nom": "Raiffeisen Gold", "unites": 2, "ticker": "RGLDOH.SW", "devise": "CHF"},
    "UBS": {"nom": "UBS GOLD hCHF", "unites": 4, "ticker": "AUCHAH.SW", "devise": "CHF"}
}

# ==========================================
# 🛠️ FONCTIONS DE RÉCUPÉRATION SPÉCIALES
# ==========================================

def get_pictet_price_web():
    """Plan B : Extraction directe sur le web pour Pictet Water P CHF."""
    try:
        url = "https://www.wallstreet-online.de/fonds/pictet-water-p-chf"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        # Recherche du prix dans la structure HTML du site
        price_tag = soup.find("div", {"class": "quotebox-price"}) or soup.find("span", {"data-test": "price-value"})
        if price_tag:
            p = price_tag.text.replace("CHF", "").replace(",", ".").replace(" ", "").strip()
            return float(p)
    except:
        pass
    return 0.0

def get_asset_data(ticker, is_pictet=False):
    """Récupère prix actuel et veille via Yahoo ou Scraping."""
    try:
        t = yf.Ticker(ticker)
        data = t.history(period="5d")
        if not data.empty:
            now = data['Close'].iloc[-1]
            old = data['Close'].iloc[-2] if len(data) >= 2 else now
            if now > 0: return now, old
            
        if is_pictet:
            p_web = get_pictet_price_web()
            if p_web > 0: return p_web, p_web
    except:
        if is_pictet:
            p_web = get_pictet_price_web()
            if p_web > 0: return p_web, p_web
    return None, None

def get_market_essentials():
    """Taux de change et métaux de base."""
    try:
        fx = yf.Ticker("USDCHF=X").history(period="5d")
        gold = yf.Ticker("GC=F").history(period="5d")
        silver = yf.Ticker("SI=F").history(period="5d")
        return {
            "rate": fx['Close'].iloc[-1], "rate_old": fx['Close'].iloc[-2],
            "g_usd": gold['Close'].iloc[-1], "g_usd_old": gold['Close'].iloc[-2],
            "s_usd": silver['Close'].iloc[-1], "s_usd_old": silver['Close'].iloc[-2]
        }
    except: return None

# ==========================================
# 🛡️ SÉCURITÉ
# ==========================================
def acces_restreint(func):
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        if str(message.chat.id) != str(MY_CHAT_ID):
            bot.reply_to(message, "❌ Accès privé.")
            return
        return func(message, *args, **kwargs)
    return wrapper

# ==========================================
# 📈 COMMANDES
# ==========================================

@bot.message_handler(commands=['check', 'start'])
@acces_restreint
def check(message):
    m = get_market_essentials()
    if not m: return bot.reply_to(message, "Erreur marché.")
    
    g_chf = m["g_usd"] * m["rate"]
    s_chf = m["s_usd"] * m["rate"]
    vg = ((m["g_usd"] - m["g_usd_old"]) / m["g_usd_old"]) * 100
    
    res = (
        f"🕒 **MARCHÉ EN DIRECT**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🟡 Or : `{g_chf:.2f} CHF` ({vg:+.2f}%)\n"
        f"⚪ Arg : `{s_chf:.2f} CHF` / `{s_chf*32.15:.2f} kg`\n"
        f"⚖️ Ratio : `{m['g_usd']/m['s_usd']:.2f}`"
    )
    bot.reply_to(message, res, parse_mode='Markdown')

@bot.message_handler(commands=['coffre'])
@acces_restreint
def coffre(message):
    m = get_market_essentials()
    if not m: return
    
    p_g, p_s = m["g_usd"] * m["rate"], m["s_usd"] * m["rate"]
    p_g_old, p_s_old = m["g_usd_old"] * m["rate_old"], m["s_usd_old"] * m["rate_old"]
    
    val_now = (COFFRE["or_oz"] * p_g) + (COFFRE["argent_oz"] * p_s) + \
              (COFFRE["argent_g"] * (p_s*32.15/1000)) + (COFFRE["argent_kg"] * (p_s*32.15))
              
    val_old = (COFFRE["or_oz"] * p_g_old) + (COFFRE["argent_oz"] * p_s_old) + \
              (COFFRE["argent_g"] * (p_s_old*32.15/1000)) + (COFFRE["argent_kg"] * (p_s_old*32.15))
    
    diff = val_now - val_old
    perc = (diff/val_old)*100
    
    res = (
        f"🏦 **VOTRE COFFRE**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💰 TOTAL : **{val_now:.2f} CHF**\n"
        f"{'📈' if diff>=0 else '📉'} Var 24h : `{diff:+.2f} CHF` ({perc:+.2f}%)"
    )
    bot.reply_to(message, res, parse_mode='Markdown')

@bot.message_handler(commands=['bourse'])
@acces_restreint
def bourse(message):
    msg_wait = bot.send_message(message.chat.id, "⏳ *Analyse du portefeuille...*", parse_mode="Markdown")
    m = get_market_essentials()
    
    lignes = []
    total_now, total_old = 0.0, 0.0
    
    for k, a in BOURSE.items():
        p_now, p_old = get_asset_data(a["ticker"], is_pictet=(k=="Pictet"))
        unites = int(a['unites']) if float(a['unites']).is_integer() else a['unites']
        
        if p_now:
            c_now = p_now * m["rate"] if a["devise"] == "USD" else p_now
            c_old = p_old * m["rate_old"] if a["devise"] == "USD" else p_old
            
            v_now = c_now * a["unites"]
            v_old = c_old * a["unites"]
            total_now += v_now
            total_old += v_old
            
            diff = v_now - v_old
            perc = (diff/v_old)*100 if v_old > 0 else 0
            
            lignes.append(f"🔹 **{a['nom']}** ({unites} un.)\n   `{v_now:.2f} CHF` | {diff:+.2f} ({perc:+.2f}%)")
        else:
            lignes.append(f"⚠️ **{a['nom']}** : Indisponible")

    diff_t = total_now - total_old
    perc_t = (diff_t/total_old)*100 if total_old > 0 else 0
    
    res = (
        f"📊 **PORTEFEUILLE BOURSE**\n"
        f"━━━━━━━━━━━━━━━\n" + "\n".join(lignes) +
        f"\n━━━━━━━━━━━━━━━\n"
        f"💰 **TOTAL : {total_now:.2f} CHF**\n"
        f"{'🟢' if diff_t>=0 else '🔴'} Var : `{diff_t:+.2f} CHF` ({perc_t:+.2f}%)"
    )
    bot.edit_message_text(res, message.chat.id, msg_wait.message_id, parse_mode='Markdown')

# ==========================================
# 🚀 RUN
# ==========================================
@app.route('/')
def health(): return "OK", 200

if __name__ == "__main__":
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
