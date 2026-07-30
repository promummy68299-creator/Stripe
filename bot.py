import telebot
import random
import time
import requests
from datetime import datetime

# ============ कॉन्फिग ============
BOT_TOKEN = "8722822889:AAEBOVPUGVfTpRnr1aOGho4f7EVo9yUHE8M"  # @BotFather से
ADMIN_ID = 8279891640  # अपनी Chat ID डालो

bot = telebot.TeleBot(BOT_TOKEN)

# ============ BIN DB (Hardcoded) ============
BIN_DB = {
    '4': {'brand': 'VISA', 'type': 'DEBIT', 'level': 'STANDARD', 'bank': 'UNKNOWN', 'country': 'US', 'emoji': '🇺🇸'},
    '5': {'brand': 'MASTERCARD', 'type': 'DEBIT', 'level': 'STANDARD', 'bank': 'UNKNOWN', 'country': 'US', 'emoji': '🇺🇸'},
    '3': {'brand': 'AMEX', 'type': 'CHARGE', 'level': 'PLATINUM', 'bank': 'AMERICAN EXPRESS', 'country': 'US', 'emoji': '🇺🇸'},
    '6': {'brand': 'DISCOVER', 'type': 'DEBIT', 'level': 'STANDARD', 'bank': 'DISCOVER BANK', 'country': 'US', 'emoji': '🇺🇸'},
    '406837': {'brand': 'VISA', 'type': 'DEBIT', 'level': 'STANDARD', 'bank': 'HSBC BANK PLC', 'country': 'UK', 'emoji': '🇬🇧'},
    '515462': {'brand': 'MASTERCARD', 'type': 'DEBIT', 'level': 'GIFT', 'bank': 'BANCORP BANK, THE', 'country': 'US', 'emoji': '🇺🇸'},
    '476273': {'brand': 'MASTERCARD', 'type': 'DEBIT', 'level': 'STANDARD', 'bank': 'STANDARD BANK', 'country': 'ZA', 'emoji': '🇿🇦'},
    '523828': {'brand': 'MASTERCARD', 'type': 'DEBIT', 'level': 'STANDARD', 'bank': 'ROYAL BANK', 'country': 'CA', 'emoji': '🇨🇦'},
    '539910': {'brand': 'MASTERCARD', 'type': 'DEBIT', 'level': 'STANDARD', 'bank': 'MAYBANK', 'country': 'MY', 'emoji': '🇲🇾'},
    '455201': {'brand': 'MASTERCARD', 'type': 'DEBIT', 'level': 'STANDARD', 'bank': 'BANCO DO BRASIL', 'country': 'BR', 'emoji': '🇧🇷'},
    '406893': {'brand': 'VISA', 'type': 'DEBIT', 'level': 'STANDARD', 'bank': 'HDFC BANK', 'country': 'IN', 'emoji': '🇮🇳'},
}

# ============ VBV BINS ============
VBV_BINS = ['406837', '476273', '539910', '455201', '523828', '406893']

def is_vbv(bin_prefix):
    for vbv in VBV_BINS:
        if bin_prefix.startswith(vbv):
            return True
    return False

# ============ LUHN CHECK ============
def luhn_check(card_number):
    digits = [int(d) for d in str(card_number)]
    checksum = 0
    for i in range(len(digits) - 2, -1, -2):
        doubled = digits[i] * 2
        checksum += doubled if doubled < 10 else doubled - 9
    for i in range(len(digits) - 1, -1, -2):
        checksum += digits[i]
    return checksum % 10 == 0

# ============ CC GENERATOR ============
def generate_cc():
    prefixes = ['4', '5']
    prefix = random.choice(prefixes)
    bin_prefix = prefix + ''.join(str(random.randint(0, 9)) for _ in range(5))
    
    for _ in range(200):
        number = bin_prefix + ''.join(str(random.randint(0, 9)) for _ in range(15 - len(bin_prefix)))
        if luhn_check(number):
            year = random.randint(2026, 2035)
            month = random.randint(1, 12)
            cvv = ''.join(str(random.randint(0, 9)) for _ in range(3))
            return {
                'number': number,
                'mm': f"{month:02d}",
                'yy': str(year)[2:],
                'cvv': cvv,
                'bin': bin_prefix
            }
    return None

# ============ BIN INFO ============
def get_bin_info(bin_prefix):
    if bin_prefix in BIN_DB:
        return BIN_DB[bin_prefix]
    first = bin_prefix[0]
    if first in BIN_DB:
        return BIN_DB[first]
    return {'brand': 'UNKNOWN', 'type': 'UNKNOWN', 'level': 'UNKNOWN', 'bank': 'UNKNOWN', 'country': 'UNKNOWN', 'emoji': '🌍'}

# ============ FORMAT ============
def format_result(cc_data, bin_info):
    lines = []
    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"{bin_info['emoji']} **APPROVE CC**")
    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append(f"💳 **CARD:** `{cc_data['number']}`")
    lines.append(f"📅 **EXP:** `{cc_data['mm']}|{cc_data['yy']}`")
    lines.append(f"🔐 **CVV:** `{cc_data['cvv']}`")
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append("**🔍 CHECK**")
    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    
    if luhn_check(cc_data['number']):
        lines.append(f"✅ **Status:** `APPROVED`")
        lines.append(f"📝 **Response:** `Luhn Passed`")
        if is_vbv(cc_data['bin']):
            lines.append(f"🔐 **VBV:** `VBV (3DS)`")
        else:
            lines.append(f"🔐 **VBV:** `Non-VBV`")
    else:
        lines.append(f"❌ **Status:** `DECLINED`")
        lines.append(f"📝 **Response:** `Luhn Failed`")
    
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append("**📋 BIN INFO**")
    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append(f"💳 **Brand:** `{bin_info['brand']}`")
    lines.append(f"📝 **Type:** `{bin_info['type']}`")
    lines.append(f"⭐ **Level:** `{bin_info['level']}`")
    lines.append(f"🏦 **Bank:** `{bin_info['bank']}`")
    lines.append(f"🌐 **Country:** `{bin_info['country']}` {bin_info['emoji']}")
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"🕒 **Time:** `{datetime.now().strftime('%H:%M:%S')}`")
    lines.append(f"🤖 **Bot by:** @Ron875")
    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append("✨ **Premium Channel** ✨")
    
    return "\n".join(lines)

# ============ /START ============
@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.reply_to(message,
        "🤖 **VBV CHECKER BOT (No API)**\n\n"
        "🔥 **Features:**\n"
        "✅ Luhn Algorithm से CC Validate\n"
        "✅ BIN DB से Brand, Bank, Country\n"
        "✅ VBV / Non-VBV Detect\n"
        "✅ Approved CC – सिर्फ Admin DM में\n"
        "✅ Declined CC – कहीं नहीं जाएगी\n\n"
        f"👤 **Admin:** `{ADMIN_ID}`\n\n"
        "⚡ **Bot is running...**"
    )

# ============ /CHECK ============
@bot.message_handler(commands=['check'])
def check_cmd(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ **Usage:** `/check card|mm|yy|cvv`")
        return
    
    try:
        parts = args[1].split('|')
        if len(parts) != 4:
            bot.reply_to(message, "❌ **Format:** `number|mm|yy|cvv`")
            return
        
        number, mm, yy, cvv = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
        cc_data = {'number': number, 'mm': mm, 'yy': yy, 'cvv': cvv, 'bin': number[:6]}
        bin_info = get_bin_info(number[:6])
        
        if luhn_check(number):
            formatted = format_result(cc_data, bin_info)
            bot.reply_to(message, formatted, parse_mode='Markdown')
        else:
            bot.reply_to(message, "❌ **Declined** – Luhn Failed")
            
    except Exception as e:
        bot.reply_to(message, f"❌ **Error:** `{str(e)}`")

# ============ नॉनस्टॉप CC GENERATOR ============
def continuous_generator():
    print("🚀 VBV CHECKER STARTED (No API)...")
    print(f"👤 Admin ID: {ADMIN_ID}")
    
    while True:
        try:
            cc = generate_cc()
            if cc and luhn_check(cc['number']):
                bin_info = get_bin_info(cc['bin'])
                formatted = format_result(cc, bin_info)
                try:
                    bot.send_message(ADMIN_ID, formatted, parse_mode='Markdown')
                    print(f"✅ Approved: {cc['number']}")
                except Exception as e:
                    print(f"❌ Send Error: {e}")
            time.sleep(1)
        except Exception as e:
            print(f"❌ Loop Error: {e}")
            time.sleep(5)

# ============ मेन ============
if __name__ == "__main__":
    import threading
    threading.Thread(target=continuous_generator, daemon=True).start()
    print("✅ बॉट चालू है...")
    bot.infinity_polling()