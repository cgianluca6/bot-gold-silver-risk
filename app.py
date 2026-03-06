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
MY_CHAT_ID = "929066398" 

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
    "Pictet": {"nom": "Pictet Water", "unites": 2, "ticker": "0P0000YUS1.F", "devise": "CHF", "fallback_val": 550.0},
    "Ethereum": {"nom": "Share Ethereum", "unites": 25, "ticker": "AETH.SW", "devise": "CHF"},
    "Swisscanto": {"nom": "Swisscanto EAH", "unites": 58, "ticker": "ZSILHC.SW", "devise": "CHF"},
    "Raiffeisen": {"nom": "Raiffeisen Gold", "unites": 2, "ticker": "RGLDOH.SW", "devise": "CHF"},
    "UBS": {"nom": "UBS GOLD hCHF", "unites": 4, "ticker": "AUCHAH.SW", "devise": "CHF"}
}

# 🔍 MARGES DE RACHAT (SPREAD)
MARGE_RACHAT_OR = 0.97    # -3%
MARGE_RACHAT_ARGENT = 0.85 # -15%

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
        etf = yf.Ticker("ZSILHC.SW").history(period="5d")
        return {
            "rate": fx['Close'].iloc[-1], "rate_old": fx['Close'].iloc[-2],
            "g_usd": gold['Close'].iloc[-1], "g_usd_old": gold['Close'].iloc[-2],
            "s_usd": silver['Close'].iloc[-1], "s_usd_old": silver['Close'].iloc[-2],
            "etf_chf": etf['Close'].iloc[-1] if not etf.empty else 0.0
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
    if not m: return bot.reply_to(message, "⚠️ Erreur marché.")
    
    g_chf = m["g_usd"] * m["rate"]
    s_chf = m["s_usd"] * m["rate"]
    vg = ((m["g_usd"] - m["g_usd_old"]) / m["g_usd_old"]) * 100
    vs = ((m["s_usd"] - m["s_usd_old"]) / m["s_usd_old"]) * 100

    res = (
        "🕒 **RAPPORT MARCHÉ**\n"
        "━━━━━━━━━━━━━━━\n"
        "🇨🇭 **EN FRANCS (CHF)**\n"
        f"🟡 Or oz : `{g_chf:.2f} CHF`\n"
        f"⚪ Argent oz : `{s_chf:.2f} CHF`\n"
        f"⚪ Argent kg : `{s_chf * 32.1507:.2f} CHF`\n"
        f"📉 ETF ZKB : `{m['etf_chf']:.2f} CHF`\n\n"
        "🇺🇸 **EN DOLLARS (USD)**\n"
        f"🟡 Or oz : `${m['g_usd']:.2f}`\n"
        f"⚪ Argent oz : `${m['s_usd']:.2f}`\n\n"
        "📊 **VARIATIONS 24H**\n"
        f"🟡 Or : {vg:+.2f}%\n"
        f"⚪ Argent : {vs:+.2f}%\n"
        f"⚖️ Ratio Or/Arg : `{m['g_usd']/m['s_usd']:.2f}`"
    )
    bot.reply_to(message, res, parse_mode='Markdown')

@bot.message_handler(commands=['coffre'])
@acces_restreint
def coffre(message):
    m = get_market_essentials()
    if not m: return
    
    # Prix Actuels
    p_oz_g = m["g_usd"] * m["rate"]
    p_oz_s = m["s_usd"] * m["rate"]
    p_kg_s = p_oz_s * 32.1507
    p_g_s = p_kg_s / 1000

    # Prix Veille
    p_oz_g_old = m["g_usd_old"] * m["rate_old"]
    p_oz_s_old = m["s_usd_old"] * m["rate_old"]
    total_old = (COFFRE["or_oz"] * p_oz_g_old) + (COFFRE["argent_oz"] * p_oz_s_old) + \
                (COFFRE["argent_g"] * (p_oz_s_old*32.15/1000)) + (COFFRE["argent_kg"] * (p_oz_s_old*32.15))

    # Calcul Valeur Achat (Valeur Marché / Spot)
    v_or = COFFRE["or_oz"] * p_oz_g
    v_arg = (COFFRE["argent_oz"] * p_oz_s) + (COFFRE["argent_g"] * p_g_s) + (COFFRE["argent_kg"] * p_kg_s)
    total_achat = v_or + v_arg

    # Calcul Valeur Vente (Rachat comptoir)
    total_vente = (v_or * MARGE_RACHAT_OR) + (v_arg * MARGE_RACHAT_ARGENT)

    diff = total_achat - total_old
    perc = (diff / total_old) * 100 if total_old > 0 else 0

    res = (
        "🏦 **DÉTAILS DU COFFRE**\n"
        "━━━━━━━━━━━━━━━\n"
        f"🟡 Or : `{v_or:.2f} CHF`\n"
        f"⚪ Argent : `{v_arg:.2f} CHF`\n"
        "━━━━━━━━━━━━━━━\n"
        f"📈 **Valeur Marché : {total_achat:.2f} CHF**\n"
        f"💰 **Valeur de Vente : {total_vente:.2f} CHF**\n\n"
        f"{'📈' if diff>=0 else '📉'} Var 24h : `{diff:+.2f} CHF` ({perc:+.2f}%)"
    )
    bot.reply_to(message, res, parse_mode='Markdown')

@bot.message_handler(commands=['bourse'])
@acces_restreint
def bourse(message):
    m = get_market_essentials()
    if not m: return
    lignes = []
    total_now, total_old = 0.0, 0.0
    
    for k, a in BOURSE.items():
        p_now, p_old = get_asset_data(a["ticker"], is_pictet=(k=="Pictet"))
        u = int(a['unites']) if float(a['unites']).is_integer() else a['unites']
        
        if p_now:
            c_now = p_now * m["rate"] if a["devise"] == "USD" else p_now
            c_old = p_old * m["rate_old"] if a["devise"] == "USD" else p_old
            v_now, v_old = c_now * a["unites"], c_old * a["unites"]
            total_now += v_now
            total_old += v_old
            diff = v_now - v_old
            perc = (diff/v_old)*100 if v_old > 0 else 0
            lignes.append(f"🔹 **{a['nom']}** ({u})\n   `{v_now:.2f} CHF` | {'📈' if diff>=0 else '📉'} `{diff:+.2f}` ({perc:+.2f}%)")
        else:
            if k == "Pictet":
                v_est = a["fallback_val"] * a["unites"]
                total_now += v_est
                total_old += v_est
                lignes.append(f"⚠️ **{a['nom']}** ({u}) : Indisponible\n   *Estimé : {v_est:.2f} CHF*")
            else:
                lignes.append(f"⚠️ **{a['nom']}** ({u}) : Indisponible")
                
    diff_t = total_now - total_old
    perc_t = (diff_t/total_old)*100 if total_old > 0 else 0
    res = (f"📊 **DÉTAILS BOURSE**\n━━━━━━━━━━━━━━━\n" + "\n".join(lignes) + 
           f"\n━━━━━━━━━━━━━━━\n💰 **SOUS-TOTAL : {total_now:.2f} CHF**\n"
           f"{'🟢' if diff_t>=0 else '🔴'} Var 24h : `{diff_t:+.2f} CHF` ({perc_t:+.2f}%)")
    bot.reply_to(message, res, parse_mode='Markdown')

@bot.message_handler(commands=['total'])
@acces_restreint
def total_patrimoine(message):
    m = get_market_essentials()
    if not m: return
    
    # Coffre (Valeur Marché)
    p_oz_g, p_oz_s = m["g_usd"] * m["rate"], m["s_usd"] * m["rate"]
    val_c = (COFFRE["or_oz"] * p_oz_g) + (COFFRE["argent_oz"] * p_oz_s) + \
            (COFFRE["argent_g"] * (p_oz_s*32.15/1000)) + (COFFRE["argent_kg"] * (p_oz_s*32.15))
    
    # Bourse
    val_b = 0.0
    for k, a in BOURSE.items():
        p_now, _ = get_asset_data(a["ticker"], is_pictet=(k=="Pictet"))
        if p_now:
            c_now = p_now * m["rate"] if a["devise"] == "USD" else p_now
            val_b += (c_now * a["unites"])
        elif k == "Pictet":
            val_b += (a["fallback_val"] * a["unites"])

    res = (
        "🌍 **PATRIMOINE GLOBAL**\n"
        "━━━━━━━━━━━━━━━\n"
        f"🏦 Coffre (Marché) : `{val_c:.2f} CHF`\n"
        f"📊 Bourse : `{val_b:.2f} CHF`\n"
        "━━━━━━━━━━━━━━━\n"
        f"💰 **TOTAL : {val_c + val_b:.2f} CHF**"
    )
    bot.reply_to(message, res, parse_mode='Markdown')

# ==========================================
# 🚀 RUN
# ==========================================
@app.route('/')
def health(): return "OK", 200

if __name__ == "__main__":
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
