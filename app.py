import os
import time
import threading
import telebot
import yfinance as yf
from flask import Flask
from functools import wraps

# ==========================================
# ⚙️ CONFIGURATION DU BOT & INVENTAIRE
# ==========================================
app = Flask(__name__)
TOKEN = os.environ.get('TELEGRAM_TOKEN')
MY_CHAT_ID = "TON_ID_NUMERIQUE"  # <--- METS TON ID ICI

bot = telebot.TeleBot(TOKEN)

# 🏦 TON COFFRE PHYSIQUE
# Si tu achètes ou vends, tu n'as plus qu'à changer les chiffres ici !
COFFRE = {
    "or_oz": 5.0,
    "argent_oz": 38.0,
    "argent_g": 100.0,
    "argent_kg": 6.0
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
def get_etf_price():
    """Récupère la cotation brute de l'ETF Swisscanto EAH CHF."""
    try:
        # ZSILHC.SW est le ticker exact pour tes ~131 CHF
        data = yf.Ticker("ZSILHC.SW").history(period="5d")
        if not data.empty:
            return data['Close'].iloc[-1]
    except Exception as e:
        print(f"⚠️ Erreur récupération ETF ZSILHC.SW : {e}")
    return 0.0

def get_market_data():
    """Récupère et calcule toutes les données du marché en une seule passe."""
    try:
        # Période de 5 jours pour esquiver les fermetures du week-end
        g_data = yf.Ticker("GC=F").history(period="5d")
        s_data = yf.Ticker("SI=F").history(period="5d")
        fx_data = yf.Ticker("USDCHF=X").history(period="5d")

        rate = fx_data['Close'].iloc[-1]
        rate_old = fx_data['Close'].iloc[-2]

        return {
            "g_usd": g_data['Close'].iloc[-1],
            "g_usd_old": g_data['Close'].iloc[-2],
            "s_usd": s_data['Close'].iloc[-1],
            "s_usd_old": s_data['Close'].iloc[-2],
            "rate": rate,
            "rate_old": rate_old
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
    
    # Calculs et Variations
    g_chf = data["g_usd"] * data["rate"]
    s_chf = data["s_usd"] * data["rate"]
    s_kg_chf = s_chf * 32.1507
    
    v_g = ((data["g_usd"] - data["g_usd_old"]) / data["g_usd_old"]) * 100
    v_s = ((data["s_usd"] - data["s_usd_old"]) / data["s_usd_old"]) * 100

    report = (
        "🕒 **RAPPORT MARCHÉ**\n"
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

    # Prix actuels en CHF
    p_oz_g = data["g_usd"] * data["rate"]
    p_oz_s = data["s_usd"] * data["rate"]
    p_kg_s = p_oz_s * 32.1507
    p_g_s = p_kg_s / 1000

    # Prix de la veille en CHF (pour variation)
    p_oz_g_old = data["g_usd_old"] * data["rate_old"]
    p_oz_s_old = data["s_usd_old"] * data["rate_old"]
    p_kg_s_old = p_oz_s_old * 32.1507
    p_g_s_old = p_kg_s_old / 1000

    # Valorisation actuelle basée sur le dictionnaire COFFRE
    v_or_oz = COFFRE["or_oz"] * p_oz_g
    v_arg_oz = COFFRE["argent_oz"] * p_oz_s
    v_arg_g = COFFRE["argent_g"] * p_g_s
    v_arg_kg = COFFRE["argent_kg"] * p_kg_s
    
    total_now = v_or_oz + v_arg_oz + v_arg_g + v_arg_kg

    # Valorisation de la veille
    total_old = (COFFRE["or_oz"] * p_oz_g_old) + \
                (COFFRE["argent_oz"] * p_oz_s_old) + \
                (COFFRE["argent_g"] * p_g_s_old) + \
                (COFFRE["argent_kg"] * p_kg_s_old)
                
    diff_chf = total_now - total_old
    diff_perc = (diff_chf / total_old) * 100 if total_old > 0 else 0

    res = (
        "🏦 **INVENTAIRE DU COFFRE**\n"
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

# ==========================================
# 🚨 ALARMES & THREAD DE FOND
# ==========================================
def monitor():
    """Surveille le marché en arrière-plan et alerte si variation > 2%."""
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
                            bot.send_message(MY_CHAT_ID, f"🚨 **ALERTE MARCHÉ**\nVariation soudaine !\nOr: {vg:+.2f}% | Arg: {vs:+.2f}%", parse_mode='Markdown')
                    last_g, last_s = cg, cs
        except Exception as e:
            print(f"⚠️ Erreur Monitoring : {e}")
        
        time.sleep(3600) # Pause de 1 heure

# ==========================================
# 🚀 DÉMARRAGE DES SERVICES (FLASK + BOT)
# ==========================================
@app.route('/')
def health(): 
    return "Bot Gold/Silver Pro Active", 200

if __name__ == "__main__":
    # 1. Lance la surveillance en arrière-plan
    threading.Thread(target=monitor, daemon=True).start()
    
    # 2. Lance l'écoute des messages Telegram
    threading.Thread(target=lambda: bot.infinity_polling(timeout=10, long_polling_timeout=5), daemon=True).start()
    
    # 3. Lance le serveur web pour Koyeb
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
