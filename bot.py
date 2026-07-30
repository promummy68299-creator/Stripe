#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🤖 Instagram Account Creator Bot - Railway Ready with Chrome Setup
Everything in one file - No environment variables needed!
"""

import sys
import os
import sqlite3
import logging
import time
import threading
import random
import string
import subprocess
import json
import shutil
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import requests
import telebot
from telebot import types

# ==================== ALL CONFIGURATION HERE ====================
BOT_TOKEN = "8912256780:AAFB2USiTYVAYieHVbU1w_QygKs1G1o8Et0"                     # ← Your bot token from @BotFather
ADMIN_ID = 8279891640               # ← Your Telegram user ID

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not set! Please add your bot token.")
    sys.exit(1)

# ==================== DELETE WEBHOOK ====================
try:
    requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", timeout=5)
except:
    pass

# ==================== LOGGING ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("InstaBot")

# ==================== CHROME INSTALLER FOR RAILWAY ====================
def install_chrome_railway():
    """Install Chrome on Railway/Ubuntu - robust version"""
    logger.info("📦 Installing Chrome on Railway...")
    try:
        # Update packages
        subprocess.run(['apt-get', 'update', '-y'], check=True, capture_output=True, timeout=60)
        logger.info("✅ Apt update done")
        
        # Install dependencies
        subprocess.run(['apt-get', 'install', '-y', 'wget', 'gnupg', 'unzip', 'curl'], check=True, capture_output=True, timeout=60)
        logger.info("✅ Dependencies installed")
        
        # Install Chromium (more likely to work on Railway)
        subprocess.run(['apt-get', 'install', '-y', 'chromium-browser'], check=True, capture_output=True, timeout=120)
        logger.info("✅ Chromium installed successfully!")
        
        # Check if installed
        if os.path.exists('/usr/bin/chromium-browser'):
            logger.info("✅ Chromium found at /usr/bin/chromium-browser")
            return True
        elif os.path.exists('/usr/bin/chromium'):
            logger.info("✅ Chromium found at /usr/bin/chromium")
            return True
        else:
            # Try to find chromium
            try:
                result = subprocess.run(['which', 'chromium-browser'], capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and result.stdout.strip():
                    logger.info(f"✅ Chromium found at: {result.stdout.strip()}")
                    return True
            except:
                pass
            return False
            
    except Exception as e:
        logger.error(f"❌ Chromium install failed: {e}")
        
        # Try alternative - Google Chrome
        try:
            logger.info("🔄 Trying Google Chrome instead...")
            subprocess.run(['apt-get', 'install', '-y', 'wget', 'gnupg'], check=True, capture_output=True, timeout=30)
            subprocess.run(['wget', '-q', '-O', '-', 'https://dl-ssl.google.com/linux/linux_signing_key.pub'], check=True, timeout=30)
            subprocess.run(['apt-get', 'install', '-y', 'google-chrome-stable'], check=True, capture_output=True, timeout=120)
            
            if os.path.exists('/usr/bin/google-chrome'):
                logger.info("✅ Google Chrome installed!")
                return True
        except Exception as e2:
            logger.error(f"❌ Google Chrome install failed: {e2}")
            
        return False

def find_chrome_path():
    """Find Chrome/Chromium executable path"""
    paths = [
        '/usr/bin/chromium-browser',
        '/usr/bin/chromium',
        '/usr/bin/google-chrome',
        '/usr/bin/google-chrome-stable',
        '/snap/bin/chromium',
        '/snap/bin/google-chrome',
        '/usr/local/bin/chromium',
        '/usr/local/bin/google-chrome',
    ]
    
    # Check common paths
    for path in paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            logger.info(f"✅ Found Chrome at: {path}")
            return path
    
    # Try which command
    for cmd in ['chromium-browser', 'chromium', 'google-chrome', 'google-chrome-stable']:
        try:
            result = subprocess.run(['which', cmd], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                path = result.stdout.strip()
                logger.info(f"✅ Found Chrome at: {path}")
                return path
        except:
            pass
    
    return None

def setup_chrome():
    """Complete Chrome setup - install if needed"""
    logger.info("🔍 Checking for Chrome/Chromium...")
    
    # First try to find existing Chrome
    chrome_path = find_chrome_path()
    if chrome_path:
        logger.info(f"✅ Chrome already available at: {chrome_path}")
        return chrome_path
    
    # Try to install
    logger.info("⚠️ Chrome not found. Installing...")
    if install_chrome_railway():
        chrome_path = find_chrome_path()
        if chrome_path:
            logger.info(f"✅ Chrome installed at: {chrome_path}")
            return chrome_path
    
    logger.error("❌ Could not find or install Chrome")
    return None

# ==================== DATABASE ====================
DB_PATH = "instagram_accounts.db"
db_lock = threading.Lock()

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        with db_lock:
            cur = self.conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    email TEXT NOT NULL,
                    password TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL
                )
            """)
            self.conn.commit()

    def save_account(self, telegram_id: int, username: str, email: str, password: str, status: str = 'created'):
        with db_lock:
            cur = self.conn.cursor()
            cur.execute("""
                INSERT INTO accounts (telegram_id, username, email, password, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (telegram_id, username, email, password, status, datetime.utcnow().isoformat()))
            self.conn.commit()
            return cur.lastrowid

    def get_accounts(self, telegram_id: int) -> list:
        with db_lock:
            cur = self.conn.cursor()
            cur.execute("SELECT * FROM accounts WHERE telegram_id = ? ORDER BY created_at DESC", (telegram_id,))
            return cur.fetchall()

    def get_account_count(self, telegram_id: int) -> int:
        with db_lock:
            cur = self.conn.cursor()
            cur.execute("SELECT COUNT(*) FROM accounts WHERE telegram_id = ?", (telegram_id,))
            return cur.fetchone()[0]

    def delete_account(self, account_id: int) -> bool:
        with db_lock:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
            self.conn.commit()
            return cur.rowcount > 0

db = Database()

# ==================== CAPTCHA ANSWERS STORAGE ====================
captcha_answers = {}

# ==================== INSTAGRAM CREATOR ====================
class InstagramCreator:
    def __init__(self):
        self.driver = None
        self.wait = None
        
    def setup_driver(self):
        chrome_path = setup_chrome()
        
        if not chrome_path:
            logger.error("❌ No Chrome available")
            return False
        
        try:
            options = Options()
            options.binary_location = chrome_path
            
            # Critical options for Railway
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-software-rasterizer")
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1920x1080")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-features=VizDisplayCompositor")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Set user agent
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # Create service
            service = Service()
            
            # Create driver
            self.driver = webdriver.Chrome(service=service, options=options)
            self.wait = WebDriverWait(self.driver, 30)
            
            # Remove webdriver flag
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("✅ Driver setup successful")
            return True
            
        except Exception as e:
            logger.error(f"❌ Driver setup failed: {e}")
            return False

    def generate_credentials(self):
        random_suffix = ''.join(random.choices(string.digits, k=6))
        username = f"user_{random_suffix}"
        email = f"{username}@tempmail.com"
        password = ''.join(random.choices(string.ascii_letters + string.digits + "!@#$%", k=12))
        return {
            "username": username,
            "email": email,
            "password": password
        }

    def create_account(self, bot_instance=None, chat_id=None) -> dict:
        result = {"success": False, "message": "", "username": "", "email": "", "password": ""}
        
        try:
            if not self.setup_driver():
                result["message"] = "Chrome not available. Please ensure Chrome is installed."
                return result
            
            credentials = self.generate_credentials()
            result.update(credentials)
            
            # Instagram signup
            self.driver.get("https://www.instagram.com/accounts/emailsignup/")
            time.sleep(5)
            
            # Accept cookies if present
            try:
                cookie_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Accept')]")
                cookie_btn.click()
                time.sleep(2)
            except:
                pass
            
            # Fill email
            email_field = self.wait.until(EC.presence_of_element_located((By.NAME, "emailOrPhone")))
            email_field.clear()
            email_field.send_keys(credentials["email"])
            time.sleep(1)
            
            # Full name
            name_field = self.driver.find_element(By.NAME, "fullName")
            name_field.clear()
            name_field.send_keys(credentials["username"].title())
            time.sleep(1)
            
            # Username
            username_field = self.driver.find_element(By.NAME, "username")
            username_field.clear()
            username_field.send_keys(credentials["username"])
            time.sleep(1)
            
            # Password
            password_field = self.driver.find_element(By.NAME, "password")
            password_field.clear()
            password_field.send_keys(credentials["password"])
            time.sleep(1)
            
            # Submit
            signup_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Sign up')]")
            signup_btn.click()
            time.sleep(5)
            
            # Check for CAPTCHA
            current_url = self.driver.current_url
            if 'challenge' in current_url or 'captcha' in current_url.lower():
                if bot_instance and chat_id:
                    logger.info("CAPTCHA detected! Sending to user...")
                    screenshot_path = f"captcha_{int(time.time())}.png"
                    self.driver.save_screenshot(screenshot_path)
                    
                    caption = f"""🧩 <b>CAPTCHA Detected!</b>

Please solve the CAPTCHA and send me the answer (numbers only).

⏳ You have 60 seconds to respond."""
                    
                    with open(screenshot_path, 'rb') as photo:
                        bot_instance.send_photo(chat_id, photo, caption=caption, parse_mode='HTML')
                    
                    try:
                        os.remove(screenshot_path)
                    except:
                        pass
                    
                    start_time = time.time()
                    solved = False
                    while time.time() - start_time < 60:
                        if chat_id in captcha_answers:
                            answer = captcha_answers.pop(chat_id)
                            try:
                                # Find CAPTCHA input
                                inputs = self.driver.find_elements(By.TAG_NAME, "input")
                                for inp in inputs:
                                    if inp.is_displayed() and inp.get_attribute('type') in ['text', 'search', None]:
                                        inp.clear()
                                        inp.send_keys(answer)
                                        inp.send_keys("\n")
                                        break
                                time.sleep(3)
                                if 'challenge' not in self.driver.current_url:
                                    solved = True
                                    break
                            except Exception as e:
                                logger.error(f"CAPTCHA submission error: {e}")
                        time.sleep(1)
                    
                    if not solved:
                        result["message"] = "CAPTCHA solving timed out"
                        self.driver.quit()
                        return result
            
            result["success"] = True
            result["message"] = "Account created successfully!"
            self.driver.quit()
            return result
            
        except Exception as e:
            result["message"] = f"Error: {e}"
            logger.error(f"Account creation error: {e}")
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            return result

# ==================== TELEGRAM BOT ====================
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

def safe_send(chat_id: int, text: str, reply_markup=None) -> bool:
    try:
        bot.send_message(chat_id, text, parse_mode=None, reply_markup=reply_markup)
        return True
    except Exception as e:
        logger.error(f"Send failed: {e}")
        return False

def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton("🆕 Create Account")
    btn2 = types.KeyboardButton("📋 My Accounts")
    btn3 = types.KeyboardButton("📊 Stats")
    btn4 = types.KeyboardButton("❓ Help")
    markup.add(btn1, btn2, btn3, btn4)
    return markup

# ==================== COMMAND HANDLERS ====================

@bot.message_handler(commands=['start', 'help'])
def cmd_start(message):
    text = """🤖 <b>Instagram Account Creator Bot</b>

<b>FULLY AUTOMATIC!</b>
Just press the button and account will be created!

<b>How it works:</b>
1. Press "Create Account" button
2. Bot automatically generates username, email, password
3. If CAPTCHA appears, solve and send answer
4. Account is saved in database

<b>Commands:</b>
/create - Create new account
/list - List your accounts
/stats - View stats

⚠️ For educational purposes only!"""
    safe_send(message.chat.id, text, main_menu())

@bot.message_handler(commands=['create'])
def cmd_create(message):
    chat_id = message.chat.id
    
    count = db.get_account_count(chat_id)
    if count >= 50:
        safe_send(chat_id, "❌ You have reached the limit of 50 accounts.", main_menu())
        return
    
    safe_send(chat_id, "⏳ Creating account... This may take a minute.", main_menu())
    
    thread = threading.Thread(target=create_account_thread, args=(chat_id,))
    thread.daemon = True
    thread.start()

def create_account_thread(chat_id):
    creator = InstagramCreator()
    
    result = creator.create_account(bot, chat_id)
    
    if result["success"]:
        account_id = db.save_account(chat_id, result["username"], result["email"], result["password"], 'created')
        
        text = f"""✅ <b>Account Created!</b>

👤 Username: @{result['username']}
📧 Email: {result['email']}
🔒 Password: <code>{result['password']}</code>
🆔 Account ID: {account_id}

{result['message']}"""
        safe_send(chat_id, text, main_menu())
    else:
        safe_send(chat_id, f"❌ Account creation failed: {result['message']}", main_menu())

@bot.message_handler(commands=['list'])
def cmd_list(message):
    chat_id = message.chat.id
    accounts = db.get_accounts(chat_id)
    
    if not accounts:
        safe_send(chat_id, "📭 No accounts yet. Press 'Create Account' to create one.", main_menu())
        return
    
    text = f"📋 <b>Your Accounts ({len(accounts)})</b>\n\n"
    for acc in accounts:
        text += f"🆔 <b>{acc['id']}</b>\n"
        text += f"👤 @{acc['username']}\n"
        text += f"📧 {acc['email']}\n"
        text += f"🔒 <code>{acc['password']}</code>\n"
        text += f"📊 Status: {acc['status']}\n"
        text += "-" * 20 + "\n"
    
    safe_send(chat_id, text, main_menu())

@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    chat_id = message.chat.id
    accounts = db.get_account_count(chat_id)
    
    text = f"""📊 <b>Your Statistics</b>

👤 Total Accounts: {accounts}
📊 Limit: 50 accounts
🔄 Used: {accounts}/50

<b>Mode:</b> Fully Automatic
<b>CAPTCHA:</b> Manual Solving (sent to you)

<b>Commands:</b>
/create - Create new account
/list - List all accounts"""
    safe_send(chat_id, text, main_menu())

# ==================== CAPTCHA ANSWER HANDLER ====================
@bot.message_handler(func=lambda m: True)
def handle_all_messages(message):
    chat_id = message.chat.id
    text = message.text.strip()
    
    # Check if this is a CAPTCHA answer (numbers only, 4-6 digits)
    if text.isdigit() and 4 <= len(text) <= 6:
        captcha_answers[chat_id] = text
        safe_send(chat_id, f"✅ CAPTCHA answer received: {text}\n⏳ Submitting...")
        return
    
    # Check for button presses
    if text == '🆕 Create Account':
        cmd_create(message)
    elif text == '📋 My Accounts':
        cmd_list(message)
    elif text == '📊 Stats':
        cmd_stats(message)
    elif text == '❓ Help':
        cmd_start(message)
    else:
        safe_send(chat_id, "❓ Unknown. Use /help or press buttons.", main_menu())

# ==================== MAIN ====================
if __name__ == "__main__":
    logger.info("🚀 Instagram Creator Bot starting...")
    
    # Setup Chrome first
    logger.info("🔧 Setting up Chrome...")
    chrome_path = setup_chrome()
    if chrome_path:
        logger.info(f"✅ Chrome is ready at: {chrome_path}")
    else:
        logger.warning("⚠️ Chrome setup failed. Bot will try to install on demand.")
    
    # Validate token
    try:
        bot.get_me()
        logger.info("✅ Token is valid.")
    except Exception as e:
        logger.critical(f"❌ Invalid token: {e}")
        sys.exit(1)
    
    # Start polling
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            logger.critical(f"💥 Polling crashed: {e}")
            time.sleep(5)
            logger.info("🔄 Restarting polling...")