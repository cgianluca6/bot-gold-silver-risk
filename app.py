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
# Ajout d'une valeur de secours (fallback_price) pour Pictet
BOURSE = {
    "Nvidia": {"nom": "Nvidia", "unites": 4, "ticker": "NVDA", "devise": "USD"},
    "Pictet": {"nom": "Pictet Water", "unites": 2, "ticker": "0P0000YUS1.F", "devise": "CHF", "fallback_val": 550.0},
    "Ethereum": {"nom": "Share Ethereum", "unites": 25, "ticker": "AETH.SW", "devise": "CHF"},
    "Swisscanto": {"nom": "Swisscanto EAH", "unites": 58, "ticker": "ZSILHC.SW", "devise": "CHF"},
    "Raiffeisen": {"nom": "Raiffeisen Gold", "unites": 2, "ticker": "RGLDOH.SW", "devise": "CHF"},
    "UBS": {"nom": "UBS GOLD hCHF", "unites": 4, "ticker": "AUCHAH.SW", "devise": "CHF"}
}

# ==========================================
# 🛠️ FONCTIONS DE RÉCUPÉRATION
# ==========================================

def get_pictet_price_web():
    try:
        url = "https://www.wallstreet-online.de/fonds/pictet-water-p-chf"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        price_tag = soup.find("div", {"class": "quotebox-price"}) or soup.find("span", {"data-test": "price-value"})
        if price_tag:
            p = price_tag.text.replace("CHF", "").replace(",", ".").replace(" ", "").strip()
            return float(p)
    except: pass
    return 0.0

def get_asset_data(ticker, is_pictet=False):
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
# 📈 LOGIQUE CALCULS
# ==========================================

def get_valeur_coffre(m):
    p_g, p_s = m["g_usd"] * m["rate"], m["s_usd"] * m["rate"]
    val_now = (COFFRE["or_oz"] * p_g) + (COFFRE["argent_oz"] * p_s) + \
              (COFFRE["argent_g"] * (p_s*32.15/1000)) + (COFFRE["argent_kg"] * (p_s*32.15))
    return val_now

def get_valeur_bourse(m):
    total_now = 0.0
    for k, a in BOURSE.items():
        p_now, _ = get_asset_data(a["ticker"], is_pictet=(k=="Pictet"))
        if p_now:
            c_now = p_now * m["rate"] if a["devise"] == "USD" else p_now
            total_now += (c_now * a["unites"])
        elif k == "Pictet": # Utilisation de la valeur par défaut si Pictet est KO
            total_now += (a["fallback_val"] * a["unites"])
    return total_now

# ==========================================
# 📈 COMMANDES TELEGRAM
# ==========================================

@bot.message_handler(commands=['check', 'start'])
@acces_restreint
def check(message):
    m = get_market_essentials()
    if not m: return bot.reply_to(message, "Erreur marché.")
    g_chf = m["g_usd"] * m["rate"]
    s_chf = m["s_usd"] * m["rate"]
    res = (f"🕒 **MARCHÉ**\n"
           f"🟡 Or : `{g_chf:.2f} CHF`\n"
           f"⚪ Arg : `{s_chf:.2f} CHF`\n"
           f"⚖️ Ratio : `{m['g_usd']/m['s_usd']:.2f}`")
    bot.reply_to(message, res, parse_mode='Markdown')

@bot.message_handler(commands=['coffre'])
@acces_restreint
def coffre(message):
    m = get_market_essentials()
    if not m: return
    val = get_valeur_coffre(m)
    res = f"🏦 **COFFRE PHYSIQUE**\n━━━━━━━━━━━━━━━\n💰 TOTAL : **{val:.2f} CHF**"
    bot.reply_to(message, res, parse_mode='Markdown')

@bot.message_handler(commands=['bourse'])
@acces_restreint
def bourse(message):
    m = get_market_essentials()
    lignes = []
    total_now = 0.0
    for k, a in BOURSE.items():
        p_now, _ = get_asset_data(a["ticker"], is_pictet=(k=="Pictet"))
        u = int(a['unites']) if float(a['unites']).is_integer() else a['unites']
        
        if p_now:
            c_now = p_now * m["rate"] if a["devise"] == "USD" else p_now
            v_now = c_now * a["unites"]
            total_now += v_now
            lignes.append(f"🔹 **{a['nom']}** ({u})\n   `{v_now:.2f} CHF`")
        else:
            if k == "Pictet":
                v_defaut = a["fallback_val"] * a["unites"]
                total_now += v_defaut
                lignes.append(f"⚠️ **{a['nom']}** ({u}) : Indisponible\n   *Estimé : {v_defaut:.2f} CHF*")
            else:
                lignes.append(f"⚠️ **{a['nom']}** ({u}) : Indisponible")
                
    res = f"📊 **BOURSE**\n━━━━━━━━━━━━━━━\n" + "\n".join(lignes) + f"\n━━━━━━━━━━━━━━━\n💰 **TOTAL : {total_now:.2f} CHF**"
    bot.reply_to(message, res, parse_mode='Markdown')

@bot.message_handler(commands=['total'])
@acces_restreint
def total_global(message):
    msg_wait = bot.send_message(message.chat.id, "🔄 *Calcul de la fortune totale...*", parse_mode="Markdown")
    m = get_market_essentials()
    if not m: return
    
    val_c = get_valeur_coffre(m)
    val_b = get_valeur_bourse(m)
    fortune = val_c + val_b
    
    res = (
        f"🌍 **PATRIMOINE GLOBAL**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🏦 Coffre : `{val_c:.2f} CHF`\n"
        f"📊 Bourse : `{val_b:.2f} CHF`\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💰 **TOTAL : {fortune:.2f} CHF**"
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
