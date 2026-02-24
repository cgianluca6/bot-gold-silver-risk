import os
import time
import threading
import telebot
import yfinance as yf
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
    "or_oz": 5.0,
    "argent_oz": 38.0,
    "argent_g": 100.0,
    "argent_kg": 6.0
}

# 📊 TON PORTEFEUILLE BOURSE (Actions, Fonds, ETF)
BOURSE = {
    "Nvidia": {
        "nom": "Nvidia", 
        "unites": 4.0, 
        "ticker": "NVDA", 
        "devise": "USD"
    },
    "Pictet": {
        "nom": "Pictet Sicav (Water)", 
        "unites": 2.0, 
        "ticker": "LU0843168575.SW", # ISIN du fonds
        "fallback": "0P0000YUS1.F",  # Secours si l'ISIN échoue sur Yahoo
        "devise": "CHF"
    },
    "Ethereum": {
        "nom": "Share Ethereum", 
        "unites": 25.0, 
        "ticker": "AETH.SW", 
        "devise": "CHF"
    },
    "Swisscanto": {
        "nom": "Swisscanto EAH", 
        "unites": 58.0, 
        "ticker": "ZSILHC.SW", 
        "devise": "CHF"
    },
    "Raiffeisen": {
        "nom": "Raiffeisen Solid Gold", 
        "unites": 2.0, 
        "ticker": "RGLDOH.SW", 
        "devise": "CHF"
    },
    "UBS": {
        "nom": "UBS GOLD hCHF", 
        "unites": 4.0, 
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
            bot.reply_to(message, "❌ Accès refusé. Ce bot est privé.")
            return
        return func(message, *args, **kwargs)
    return wrapper

# ==========================================
# 📊 FONCTIONS DE MARCHÉ (YAHOO FINANCE)
# ==========================================
def get_single_price(ticker):
    """Récupère le prix d'un seul actif boursier (Action, ETF, Fonds)."""
    try:
        data = yf.Ticker(ticker).history(period="5d")
        if not data.empty:
            return data['Close'].iloc[-1]
    except:
        pass
    return 0.0

def get_etf_price():
    """Récupère la cotation brute de l'ETF Swisscanto EAH CHF pour le rapport général."""
    try:
        data = yf.Ticker("ZSILHC.SW").history(period="5d")
        if not data.empty:
            return data['Close'].iloc[-1]
    except Exception as e:
        print(f"⚠️ Erreur récupération ETF ZSILHC.SW : {e}")
    return 0.0

def get_market_data():
    """Récupère toutes les données de métaux et change."""
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
        print(f"⚠️ Erreur récupération données marché : {e}")
        return None

# ==========================================
# 📈 COMMANDES TELEGRAM
# ==========================================
@bot.message_handler(commands=['check', 'start'])
@acces_restreint
def manual_check(message):
    data = get_market_data()
    if not data:
        bot.reply_to(message, "⚠️ Impossible de joindre le marché actuellement.")
        return

    etf_chf = get_etf_price()
    
    g_chf = data["g_usd"] * data["rate"]
    s_chf = data["s_usd"] * data["rate"]
    s_kg_chf = s_chf * 32.1507
    
    v_g = ((data["g_usd"] - data["g_usd_old"]) / data["g_usd_old"]) * 100
    v_s = ((data["s_usd"] - data["s_usd_old"]) / data["s_usd_old"]) * 100

    report = (
        "🕒 **RAPPORT MARCHÉ (MÉTAUX)**\n"
        "━━━━━━━━━━━━━━━\n"
        "🇨🇭 **EN FRANCS SUISSES (CHF)**\n"
        f"🟡 Or oz : `{g_chf:.2f} CHF`\n"
        f"⚪ Argent oz : `{s_chf:.2f} CHF`\n"
        f"⚪ Argent kg : `{s_kg_chf:.2f} CHF`\n"
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
        bot.reply_to(message, "⚠️ Erreur lors de l'évaluation du coffre.")
        return

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

    total_old = (COFFRE["or_oz"] * p_oz_g_old) + \
                (COFFRE["argent_oz"] * p_oz_s_old) + \
                (COFFRE["argent_g"] * p_g_s_old) + \
                (COFFRE["argent_kg"] * p_kg_s_old)
                
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
        f"💰 **TOTAL : {total_now:.2f} CHF**\n\n"
        f"{'📈' if diff_chf > 0 else '📉'} **Variation 24h :**\n"
        f"`{diff_chf:+.2f} CHF` ({diff_perc:+.2f}%)"
    )
    bot.reply_to(message, res, parse_mode='Markdown')

# --- NOUVELLE COMMANDE : BOURSE ---
@bot.message_handler(commands=['bourse'])
@acces_restreint
def calcul_bourse(message):
    bot.send_message(message.chat.id, "⏳ *Interrogation des marchés boursiers en cours...*", parse_mode="Markdown")
    
    # Récupération du taux de change pour Nvidia
    try:
        fx_data = yf.Ticker("USDCHF=X").history(period="5d")
        rate = fx_data['Close'].iloc[-1]
    except Exception as e:
        print(f"Erreur taux de change: {e}")
        rate = 0.88 # Valeur de secours
        
    lignes = []
    total_chf = 0.0
    
    for key, actif in BOURSE.items():
        prix = get_single_price(actif["ticker"])
        
        # Test du fallback si le premier ticker échoue (fréquent pour les fonds comme Pictet)
        if prix == 0.0 and "fallback" in actif:
            prix = get_single_price(actif["fallback"])
            
        if prix == 0.0:
            lignes.append(f"⚠️ **{actif['nom']}** : *Cotation introuvable*")
            continue
            
        # Conversion automatique USD -> CHF si nécessaire
        prix_chf = prix * rate if actif["devise"] == "USD" else prix
        valeur_totale = prix_chf * actif["unites"]
        total_chf += valeur_totale
        
        symbole_devise = "$" if actif["devise"] == "USD" else "CHF"
        lignes.append(
            f"🔹 **{actif['nom']}** ({actif['unites']}x)\n"
            f"   Cours : `{prix:.2f} {symbole_devise}` ➔ `{valeur_totale:.2f} CHF`"
        )
                      
    texte_bourse = (
        "📊 **PORTEFEUILLE BOURSE**\n"
        "━━━━━━━━━━━━━━━\n" +
        "\n".join(lignes) +
        "\n━━━━━━━━━━━━━━━\n"
        f"💰 **TOTAL BOURSE : {total_chf:.2f} CHF**"
    )
    
    bot.send_message(message.chat.id, texte_bourse, parse_mode='Markdown')

# ==========================================
# 🚨 ALARMES & THREAD DE FOND
# ==========================================
def monitor():
    """Surveille le marché en arrière-plan."""
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
        except Exception as e:
            pass
        time.sleep(3600)

# ==========================================
# 🚀 DÉMARRAGE DES SERVICES
# ==========================================
@app.route('/')
def health(): 
    return "Bot Actif", 200

if __name__ == "__main__":
    threading.Thread(target=monitor, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(timeout=10, long_polling_timeout=5), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
