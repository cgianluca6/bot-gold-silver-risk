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
# ⚙️ CONFIGURATION DU BOT & INVENTAIRES
# ==========================================
app = Flask(__name__)
TOKEN = os.environ.get('TELEGRAM_TOKEN')
MY_CHAT_ID = "929066398"  # <--- METS TON ID ICI

bot = telebot.TeleBot(TOKEN)

# 🏦 TON COFFRE PHYSIQUE (Métaux)
COFFRE = {
    "or_oz": 5,
    "argent_oz": 38,
    "argent_g": 100,
    "argent_kg": 6
}

# 📊 TON PORTEFEUILLE BOURSE (Actions, Fonds, ETF)
BOURSE = {
    "Nvidia": {
        "nom": "Nvidia", 
        "unites": 4, 
        "ticker": "NVDA", 
        "devise": "USD"
    },
    "Pictet": {
        "nom": "Pictet Sicav", 
        "unites": 2, 
        "ticker": "0P0000YUS1.F", # Code interne Yahoo pour le fonds Pictet CHF
        "fallback": ["PIWA.SW", "0P0000YUS1.SW", "LU0843168575.SW"],
        "devise": "CHF"
    },
    "Ethereum": {
        "nom": "Share Ethereum", 
        "unites": 25, 
        "ticker": "AETH.SW", 
        "devise": "CHF"
    },
    "Swisscanto": {
        "nom": "Swisscanto EAH", 
        "unites": 58, 
        "ticker": "ZSILHC.SW", 
        "devise": "CHF"
    },
    "Raiffeisen": {
        "nom": "Raiffeisen Solid Gold", 
        "unites": 2, 
        "ticker": "RGLDOH.SW", 
        "devise": "CHF"
    },
    "UBS": {
        "nom": "UBS GOLD hCHF", 
        "unites": 4, 
        "ticker": "AUCHAH.SW", 
        "devise": "CHF"
    }
}

# ==========================================
# 🛡️ SÉCURITÉ (DÉCORATEUR)
# ==========================================
def acces_restreint(func):
    """Filtre de sécurité pour empêcher les inconnus d'utiliser le bot."""
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        if str(message.chat.id) != str(MY_CHAT_ID):
            bot.reply_to(message, "❌ Accès refusé.")
            return
        return func(message, *args, **kwargs)
    return wrapper

# ==========================================
# 📊 FONCTIONS DE MARCHÉ (YAHOO FINANCE)
# ==========================================
def get_single_asset_data(ticker):
    """Récupère le prix actuel et celui de la veille pour les actions."""
    try:
        data = yf.Ticker(ticker).history(period="5d")
        if len(data) >= 2:
            return data['Close'].iloc[-1], data['Close'].iloc[-2]
        elif len(data) == 1:
            return data['Close'].iloc[-1], data['Close'].iloc[-1]
    except:
        pass
    return None, None

def get_etf_price():
    """Pour le rapport métaux général."""
    try:
        data = yf.Ticker("ZSILHC.SW").history(period="5d")
        if not data.empty:
            return data['Close'].iloc[-1]
    except Exception as e:
        print(f"⚠️ Erreur ETF : {e}")
    return 0.0

def get_market_data():
    """Récupère les données métaux et de change."""
    try:
        g_data = yf.Ticker("GC=F").history(period="5d")
        s_data = yf.Ticker("SI=F").history(period="5d")
        fx_data = yf.Ticker("USDCHF=X").history(period="5d")

        return {
            "g_usd": g_data['Close'].iloc[-1],
            "g_usd_old": g_data['Close'].iloc[-2],
            "s_usd": s_data['Close'].iloc[-1],
            "s_usd_old": s_data['Close'].iloc[-2],
            "rate": fx_data['Close'].iloc[-1],
            "rate_old": fx_data['Close'].iloc[-2]
        }
    except Exception as e:
        print(f"⚠️ Erreur marché : {e}")
        return None

# ==========================================
# 📈 COMMANDES TELEGRAM
# ==========================================
@bot.message_handler(commands=['check', 'start'])
@acces_restreint
def manual_check(message):
    data = get_market_data()
    if not data:
        bot.reply_to(message, "⚠️ Impossible de joindre le marché.")
        return

    etf_chf = get_etf_price()
    g_chf = data["g_usd"] * data["rate"]
    s_chf = data["s_usd"] * data["rate"]
    
    v_g = ((data["g_usd"] - data["g_usd_old"]) / data["g_usd_old"]) * 100
    v_s = ((data["s_usd"] - data["s_usd_old"]) / data["s_usd_old"]) * 100

    report = (
        "🕒 **RAPPORT MARCHÉ (MÉTAUX)**\n"
        "━━━━━━━━━━━━━━━\n"
        "🇨🇭 **EN FRANCS SUISSES (CHF)**\n"
        f"🟡 Or oz : `{g_chf:.2f} CHF`\n"
        f"⚪ Argent oz : `{s_chf:.2f} CHF`\n"
        f"⚪ Argent kg : `{s_chf * 32.1507:.2f} CHF`\n"
        f"📉 ETF ZKB (ZSILHC) : `{etf_chf:.2f} CHF`\n\n"
        "🇺🇸 **EN DOLLARS (USD)**\n"
        f"🟡 Or oz : `${data['g_usd']:.2f}`\n"
        f"⚪ Argent oz : `${data['s_usd']:.2f}`\n"
        "━━━━━━━━━━━━━━━\n"
        f"🟡 Var. Or : {'📈' if v_g > 0 else '📉'} {v_g:+.2f}%\n"
        f"⚪ Var. Arg : {'📈' if v_s > 0 else '📉'} {v_s:+.2f}%\n"
        f"⚖️ **Ratio Or/Arg : {data['g_usd']/data['s_usd']:.2f}**"
    )
    bot.reply_to(message, report, parse_mode='Markdown')

@bot.message_handler(commands=['coffre'])
@acces_restreint
def calcul_coffre(message):
    data = get_market_data()
    if not data:
        return bot.reply_to(message, "⚠️ Erreur de calcul.")

    p_oz_g = data["g_usd"] * data["rate"]
    p_oz_s = data["s_usd"] * data["rate"]
    p_kg_s = p_oz_s * 32.1507
    p_g_s = p_kg_s / 1000

    p_oz_g_old = data["g_usd_old"] * data["rate_old"]
    p_oz_s_old = data["s_usd_old"] * data["rate_old"]
    p_kg_s_old = p_oz_s_old * 32.1507
    p_g_s_old = p_kg_s_old / 1000

    v_or_oz = COFFRE["or_oz"] * p_oz_g
    v_arg_oz = COFFRE["argent_oz"] * p_oz_s
    v_arg_g = COFFRE["argent_g"] * p_g_s
    v_arg_kg = COFFRE["argent_kg"] * p_kg_s
    
    total_now = v_or_oz + v_arg_oz + v_arg_g + v_arg_kg
    total_old = (COFFRE["or_oz"] * p_oz_g_old) + (COFFRE["argent_oz"] * p_oz_s_old) + \
                (COFFRE["argent_g"] * p_g_s_old) + (COFFRE["argent_kg"] * p_kg_s_old)
                
    diff_chf = total_now - total_old
    diff_perc = (diff_chf / total_old) * 100 if total_old > 0 else 0

    res = (
        "🏦 **INVENTAIRE DU COFFRE (PHYSIQUE)**\n"
        "━━━━━━━━━━━━━━━\n"
        f"🟡 {COFFRE['or_oz']} oz d'or : `{v_or_oz:.2f} CHF`\n"
        f"⚪ {COFFRE['argent_oz']} oz argent : `{v_arg_oz:.2f} CHF`\n"
        f"⚪ {COFFRE['argent_g']} g argent : `{v_arg_g:.2f} CHF`\n"
        f"⚪ {COFFRE['argent_kg']} kg argent : `{v_arg_kg:.2f} CHF`\n"
        "━━━━━━━━━━━━━━━\n"
        f"💰 **TOTAL : {total_now:.2f} CHF**\n"
        f"{'📈' if diff_chf >= 0 else '📉'} **Var 24h :** `{diff_chf:+.2f} CHF` ({diff_perc:+.2f}%)"
    )
    bot.reply_to(message, res, parse_mode='Markdown')

@bot.message_handler(commands=['bourse'])
@acces_restreint
def calcul_bourse(message):
    bot.send_message(message.chat.id, "⏳ *Calcul du portefeuille en cours...*", parse_mode="Markdown")
    
    try:
        fx = yf.Ticker("USDCHF=X").history(period="5d")
        rate_now, rate_old = fx['Close'].iloc[-1], fx['Close'].iloc[-2]
    except:
        rate_now, rate_old = 0.88, 0.88 
        
    lignes = []
    total_chf_now, total_chf_old = 0.0, 0.0
    
    for key, actif in BOURSE.items():
        prix_now, prix_old = None, None
        
        tickers_to_try = [actif["ticker"]]
        if "fallback" in actif:
            tickers_to_try.extend(actif["fallback"])
            
        for t in tickers_to_try:
            prix_now, prix_old = get_single_asset_data(t)
            if prix_now is not None:
                break
                
        # Format des unités sans ".0"
        unites_format = int(actif['unites']) if float(actif['unites']).is_integer() else actif['unites']
            
        if prix_now is None or prix_now == 0.0:
            lignes.append(f"⚠️ **{actif['nom']}** : *Cotation introuvable*")
            continue
            
        # Conversion
        if actif["devise"] == "USD":
            val_now_chf = prix_now * rate_now * actif["unites"]
            val_old_chf = prix_old * rate_old * actif["unites"]
        else:
            val_now_chf = prix_now * actif["unites"]
            val_old_chf = prix_old * actif["unites"]
            
        total_chf_now += val_now_chf
        total_chf_old += val_old_chf
        
        # Variation
        diff_chf = val_now_chf - val_old_chf
        perc = (diff_chf / val_old_chf) * 100 if val_old_chf > 0 else 0
        icone_var = "📈" if diff_chf >= 0 else "📉"
        sym_devise = "$" if actif["devise"] == "USD" else "CHF"
        
        if prix_old == prix_now and prix_now > 0:
             var_text = "➖ `Var 24h non dispo`"
        else:
             var_text = f"Var 24h: {icone_var} `{diff_chf:+.2f} CHF` ({perc:+.2f}%)"
        
        lignes.append(
            f"🔹 **{actif['nom']}** ({unites_format} unités)\n"
            f"   Cours: `{prix_now:.2f} {sym_devise}` ➔ `{val_now_chf:.2f} CHF`\n"
            f"   {var_text}\n"
        )
                      
    diff_totale = total_chf_now - total_chf_old
    perc_total = (diff_totale / total_chf_old) * 100 if total_chf_old > 0 else 0
    icone_totale = "🟢" if diff_totale >= 0 else "🔴"
    
    texte = (
        "📊 **PORTEFEUILLE BOURSE**\n"
        "━━━━━━━━━━━━━━━\n" +
        "\n".join(lignes) +
        "━━━━━━━━━━━━━━━\n"
        f"💰 **TOTAL : {total_chf_now:.2f} CHF**\n"
        f"{icone_totale} **Var 24h :** `{diff_totale:+.2f} CHF` ({perc_total:+.2f}%)"
    )
    
    bot.send_message(message.chat.id, texte, parse_mode='Markdown')

# ==========================================
# 🚨 ALARMES & THREAD DE FOND
# ==========================================
def monitor():
    last_g, last_s = None, None
    while True:
        try:
            if MY_CHAT_ID != "TON_ID_NUMERIQUE":
                data = get_market_data()
                if data:
                    cg, cs = data["g_usd"], data["s_usd"]
                    if last_g is not None and last_s is not None:
                        vg = ((cg - last_g) / last_g) * 100
                        vs = ((cs - last_s) / last_s) * 100
                        if abs(vg) >= 2.0 or abs(vs) >= 2.0:
                            bot.send_message(MY_CHAT_ID, f"🚨 **ALERTE MARCHÉ**\nOr: {vg:+.2f}% | Arg: {vs:+.2f}%", parse_mode='Markdown')
                    last_g, last_s = cg, cs
        except Exception:
            pass
        time.sleep(3600)

@app.route('/')
def health(): return "Bot Actif", 200

if __name__ == "__main__":
    threading.Thread(target=monitor, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(timeout=10, long_polling_timeout=5), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
