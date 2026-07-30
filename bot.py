#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🤖 Instagram Account Creator Bot - FULLY AUTOMATIC
With auto Chrome/Chromium setup for Railway/Server
"""

import sys
import os
import sqlite3
import logging
import time
import threading
import random
import string
import json
import subprocess
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

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8912256780:AAFB2USiTYVAYieHVbU1w_QygKs1G1o8Et0"                     # ← Your bot token from @BotFather
ADMIN_ID = 8279891640               # ← Your Telegram user ID

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not set")
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
logger = logging.getLogger("InstaCreatorBot")

# ==================== FIND CHROME ====================
def find_chrome():
    """Find Chrome/Chromium executable path"""
    chrome_paths = [
        '/usr/bin/google-chrome',
        '/usr/bin/chromium',
        '/usr/bin/chromium-browser',
        '/snap/bin/chromium',
        '/usr/local/bin/chromium',
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',  # macOS
        'C:/Program Files/Google/Chrome/Application/chrome.exe',  # Windows
        'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',  # Windows
    ]
    
    for path in chrome_paths:
        if os.path.exists(path):
            logger.info(f"✅ Chrome found at: {path}")
            return path
    
    # Try with which command
    try:
        result = subprocess.run(['which', 'google-chrome'], capture_output=True, text=True)
        if result.returncode == 0:
            path = result.stdout.strip()
            if path:
                logger.info(f"✅ Chrome found at: {path}")
                return path
    except:
        pass
    
    try:
        result = subprocess.run(['which', 'chromium'], capture_output=True, text=True)
        if result.returncode == 0:
            path = result.stdout.strip()
            if path:
                logger.info(f"✅ Chrome found at: {path}")
                return path
    except:
        pass
    
    logger.error("❌ Chrome not found!")
    return None

# ==================== INSTALL CHROME ON RAILWAY ====================
def install_chrome():
    """Install Chrome on Railway/Ubuntu"""
    logger.info("Installing Chrome...")
    try:
        subprocess.run(['apt-get', 'update', '-y'], check=True, capture_output=True)
        subprocess.run(['apt-get', 'install', '-y', 'wget', 'gnupg', 'unzip'], check=True, capture_output=True)
        subprocess.run(['wget', '-q', '-O', '-', 'https://dl-ssl.google.com/linux/linux_signing_key.pub'], check=True)
        subprocess.run(['apt-get', 'install', '-y', 'google-chrome-stable'], check=True, capture_output=True)
        logger.info("✅ Chrome installed successfully")
        return True
    except Exception as e:
        # Try installing Chromium instead
        try:
            subprocess.run(['apt-get', 'install', '-y', 'chromium-browser'], check=True, capture_output=True)
            logger.info("✅ Chromium installed successfully")
            return True
        except Exception as e2:
            logger.error(f"❌ Failed to install Chrome: {e2}")
            return False

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
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.driver = None
        self.wait = None
        
    def setup_driver(self):
        chrome_path = find_chrome()
        
        if not chrome_path:
            logger.info("Chrome not found, attempting to install...")
            if not install_chrome():
                logger.error("Could not install Chrome")
                return False
            chrome_path = find_chrome()
            if not chrome_path:
                logger.error("Chrome not found even after installation")
                return False
        
        chrome_options = Options()
        chrome_options.binary_location = chrome_path
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        if self.headless:
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--window-size=1920x1080")
        else:
            chrome_options.add_argument("--window-size=1280x720")
        
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            service = Service()
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 20)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            logger.info("✅ Driver setup successful")
            return True
        except Exception as e:
            logger.error(f"Driver setup failed: {e}")
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
                result["message"] = "Driver setup failed. Chrome not available."
                return result
            
            credentials = self.generate_credentials()
            result.update(credentials)
            
            self.driver.get("https://www.instagram.com/accounts/emailsignup/")
            time.sleep(3)
            
            try:
                cookie_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Accept')]")
                cookie_btn.click()
                time.sleep(1)
            except:
                pass
            
            email_field = self.wait.until(EC.presence_of_element_located((By.NAME, "emailOrPhone")))
            email_field.send_keys(credentials["email"])
            time.sleep(0.5)
            
            name_field = self.driver.find_element(By.NAME, "fullName")
            name_field.send_keys(credentials["username"].title())
            time.sleep(0.5)
            
            username_field = self.driver.find_element(By.NAME, "username")
            username_field.send_keys(credentials["username"])
            time.sleep(0.5)
            
            password_field = self.driver.find_element(By.NAME, "password")
            password_field.send_keys(credentials["password"])
            time.sleep(0.5)
            
            signup_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Sign up')]")
            signup_btn.click()
            time.sleep(3)
            
            current_url = self.driver.current_url
            if 'challenge' in current_url or 'captcha' in current_url.lower():
                if bot_instance and chat_id:
                    screenshot_path = f"captcha_{int(time.time())}.png"
                    self.driver.save_screenshot(screenshot_path)
                    
                    caption = f"""🧩 <b>CAPTCHA Detected!</b>

Please solve the CAPTCHA and send me the answer.

⏳ You have 60 seconds to respond."""
                    
                    with open(screenshot_path, 'rb') as photo:
                        bot_instance.send_photo(chat_id, photo, caption=caption, parse_mode='HTML')
                    
                    os.remove(screenshot_path)
                    
                    start_time = time.time()
                    solved = False
                    while time.time() - start_time < 60:
                        if chat_id in captcha_answers:
                            answer = captcha_answers.pop(chat_id)
                            try:
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
                            except:
                                pass
                        time.sleep(1)
                    
                    if not solved:
                        result["message"] = "CAPTCHA solving timed out"
                        self.driver.quit()
                        return result
            else:
                result["success"] = True
                result["message"] = "Account created successfully!"
                self.driver.quit()
                return result
            
            result["success"] = True
            result["message"] = "Account created successfully!"
            self.driver.quit()
            return result
            
        except Exception as e:
            result["message"] = f"Error: {e}"
            if self.driver:
                self.driver.quit()
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
    creator = InstagramCreator(headless=False)
    
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

@bot.message_handler(func=lambda m: True)
def handle_all_messages(message):
    chat_id = message.chat.id
    text = message.text.strip()
    
    if text.isdigit() and 4 <= len(text) <= 6:
        captcha_answers[chat_id] = text
        safe_send(chat_id, f"✅ CAPTCHA answer received: {text}\n⏳ Submitting...")
        return
    
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

# ==================== RAILWAY SETUP ====================
def railway_setup():
    logger.info("Checking Chrome installation...")
    chrome_path = find_chrome()
    if not chrome_path:
        logger.info("Chrome not found, installing...")
        install_chrome()
    else:
        logger.info(f"✅ Chrome found at: {chrome_path}")

# ==================== MAIN ====================
if __name__ == "__main__":
    logger.info("🚀 Instagram Creator Bot starting...")
    
    railway_setup()
    
    try:
        bot.get_me()
        logger.info("✅ Token is valid.")
    except Exception as e:
        logger.critical(f"❌ Invalid token: {e}")
        sys.exit(1)
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            logger.critical(f"💥 Polling crashed: {e}")
            time.sleep(5)
            logger.info("🔄 Restarting polling...")