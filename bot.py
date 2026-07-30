#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🤖 Instagram Boost Bot - Telegram Version
Converted from try.py to Telegram Bot
"""

import sys
import os
import sqlite3
import logging
import time
import threading
import zipfile
import io
import subprocess
from datetime import datetime
import requests
import telebot
from telebot import types
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys

# ==================== CONFIG ====================
BOT_TOKEN = "8912256780:AAFB2USiTYVAYieHVbU1w_QygKs1G1o8Et0"                     # Your bot token from @BotFather
ADMIN_ID = 8279891640               # Your Telegram user ID

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
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("InstaBoostBot")

# ==================== DATABASE ====================
DB_PATH = "boost_accounts.db"
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
                CREATE TABLE IF NOT EXISTS cookies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    cookie_string TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    account_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            self.conn.commit()

    def add_cookie(self, telegram_id: int, cookie_string: str):
        with db_lock:
            cur = self.conn.cursor()
            cur.execute("""
                INSERT INTO cookies (telegram_id, cookie_string, status, created_at)
                VALUES (?, ?, ?, ?)
            """, (telegram_id, cookie_string, 'pending', datetime.utcnow().isoformat()))
            self.conn.commit()
            return cur.lastrowid

    def get_pending_cookies(self, telegram_id: int) -> list:
        with db_lock:
            cur = self.conn.cursor()
            cur.execute("SELECT * FROM cookies WHERE telegram_id = ? AND status = 'pending'", (telegram_id,))
            return cur.fetchall()

    def get_all_cookies(self, telegram_id: int) -> list:
        with db_lock:
            cur = self.conn.cursor()
            cur.execute("SELECT * FROM cookies WHERE telegram_id = ?", (telegram_id,))
            return cur.fetchall()

    def update_cookie_status(self, cookie_id: int, status: str):
        with db_lock:
            cur = self.conn.cursor()
            cur.execute("UPDATE cookies SET status = ? WHERE id = ?", (status, cookie_id))
            self.conn.commit()

    def add_result(self, telegram_id: int, account_id: int, status: str):
        with db_lock:
            cur = self.conn.cursor()
            cur.execute("""
                INSERT INTO results (telegram_id, account_id, status, created_at)
                VALUES (?, ?, ?, ?)
            """, (telegram_id, account_id, status, datetime.utcnow().isoformat()))
            self.conn.commit()

    def get_results(self, telegram_id: int) -> list:
        with db_lock:
            cur = self.conn.cursor()
            cur.execute("SELECT * FROM results WHERE telegram_id = ? ORDER BY created_at DESC", (telegram_id,))
            return cur.fetchall()

    def delete_cookie(self, cookie_id: int) -> bool:
        with db_lock:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM cookies WHERE id = ?", (cookie_id,))
            self.conn.commit()
            return cur.rowcount > 0

    def delete_all_cookies(self, telegram_id: int) -> int:
        with db_lock:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM cookies WHERE telegram_id = ?", (telegram_id,))
            self.conn.commit()
            return cur.rowcount

db = Database()

# ==================== CHROMEDRIVER SETUP ====================
CHROMEDRIVER_PATH = os.path.join(os.getcwd(), "chromedriver.exe")

def get_chrome_version():
    try:
        if os.name == 'nt':  # Windows
            cmd = r'reg query "HKEY_CURRENT_USER\Software\Google\Chrome\BLBeacon" /v version 2>nul'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout:
                return result.stdout.strip().split()[-1]
        else:  # Linux/Mac
            result = subprocess.run(['google-chrome', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip().split()[-1]
    except:
        pass
    return "133.0.6943.126"

def download_chromedriver(chrome_version):
    if not chrome_version:
        chrome_version = "133.0.6943.126"
    
    for url in [
        f"https://storage.googleapis.com/chrome-for-testing-public/{chrome_version}/win64/chromedriver-win64.zip",
        f"https://storage.googleapis.com/chrome-for-testing-public/{chrome_version}/win32/chromedriver-win32.zip"
    ]:
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 200:
                with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                    for fn in z.namelist():
                        if fn.endswith('chromedriver.exe') or fn.endswith('chromedriver'):
                            with open(CHROMEDRIVER_PATH, 'wb') as f:
                                f.write(z.read(fn))
                            os.chmod(CHROMEDRIVER_PATH, 0o755)
                            return True
        except:
            continue
    return False

def ensure_chromedriver():
    if os.path.exists(CHROMEDRIVER_PATH):
        return True
    logger.info("Downloading ChromeDriver...")
    return download_chromedriver(get_chrome_version())

# ==================== COOKIE PARSER ====================
def parse_cookie_string(cookie_string):
    cookies = []
    for pair in cookie_string.replace('\n', ';').split(';'):
        pair = pair.strip()
        if '=' in pair:
            name, value = pair.split('=', 1)
            if name.strip() and value.strip():
                cookies.append({
                    'name': name.strip(),
                    'value': value.strip(),
                    'domain': '.instagram.com'
                })
    return cookies

# ==================== DRIVER ====================
def create_driver():
    try:
        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36')
        
        prefs = {
            'credentials_enable_service': False,
            'profile.password_manager_enabled': False,
            'profile.default_content_setting_values.notifications': 2
        }
        options.add_experimental_option('prefs', prefs)
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(executable_path=CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", { get: () => undefined });'
        })
        return driver
    except Exception as e:
        logger.error(f"Driver error: {e}")
        return None

# ==================== BOOST FUNCTIONS ====================
def js_click(driver, elem, name):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", elem)
        return True
    except:
        return False

def click_button(driver, texts, label):
    for txt in texts:
        selectors = [
            f"//button[text()='{txt}']",
            f"//button[contains(text(), '{txt}')]",
            f"//div[@role='button'][contains(., '{txt}')]",
            f"//span[contains(text(), '{txt}')]",
            f"//div[contains(text(), '{txt}')]",
            f"//*[@role='button'][contains(., '{txt}')]",
            f"//*[@aria-label='{txt}']",
        ]
        for sel in selectors:
            try:
                elems = driver.find_elements(By.XPATH, sel)
                for elem in elems:
                    if elem.is_displayed():
                        if js_click(driver, elem, label):
                            time.sleep(2)
                            return True
            except:
                continue
    return False

def close_popup(driver):
    for sel in [
        "//*[@aria-label='Close']",
        "//*[@aria-label='close']",
        "//div[@role='button'][.//*[local-name()='svg']]",
        "//button[contains(text(), 'Not Now')]",
        "//button[contains(text(), 'Skip')]"
    ]:
        try:
            for elem in driver.find_elements(By.XPATH, sel):
                if elem.is_displayed():
                    driver.execute_script("arguments[0].click();", elem)
                    time.sleep(0.5)
                    return True
        except:
            pass
    try:
        from selenium.webdriver.common.action_chains import ActionChains
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(0.3)
    except:
        pass
    return False

def find_and_click_boost(driver):
    for i in range(5):
        driver.execute_script(f"window.scrollBy(0, {400 + i*200});")
        time.sleep(1)
    return click_button(driver, ['Boost', 'Boost post', 'Boost Post'], 'BOOST')

def navigate_to_posts_page(driver):
    urls = [
        "https://business.facebook.com/latest/instagram_account/instagram_posts",
        "https://business.facebook.com/latest/instagram_account",
        "https://business.facebook.com/latest/home",
    ]
    for url in urls:
        driver.get(url)
        time.sleep(5)
        if 'login' not in driver.current_url.lower():
            return True
    return False

# ==================== PROCESS ACCOUNT ====================
def process_boost(cookie_string, account_id, chat_id):
    """Process a single account boost"""
    result = {"success": False, "message": "", "steps": []}
    driver = None
    
    try:
        # Step 1: Create browser
        result["steps"].append("Creating browser...")
        driver = create_driver()
        if not driver:
            result["message"] = "Driver creation failed"
            return result
        result["steps"].append("✅ Browser created")
        
        # Step 2: Login with cookies
        result["steps"].append("Logging in with cookies...")
        driver.get('https://www.instagram.com/')
        time.sleep(4)
        driver.delete_all_cookies()
        
        cookies = parse_cookie_string(cookie_string)
        for c in cookies:
            try:
                driver.add_cookie({'name': c['name'], 'value': c['value'], 'domain': '.instagram.com'})
            except:
                try:
                    driver.add_cookie({'name': c['name'], 'value': c['value']})
                except:
                    pass
        
        driver.refresh()
        time.sleep(5)
        result["steps"].append("✅ Logged in")
        
        # Step 3: Facebook Business Authorization
        result["steps"].append("Authorizing Facebook Business...")
        fb_url = "https://business.facebook.com/business/loginpage/?next=https%3A%2F%2Fbusiness.facebook.com%2Flatest%2Fhome&login_options%5B0%5D=IG"
        driver.get(fb_url)
        time.sleep(5)
        
        existing_handles = set(driver.window_handles)
        if not click_button(driver, ['Continue with Instagram', 'Instagram'], 'Continue with Instagram'):
            result["message"] = "Continue with Instagram button not found"
            return result
        
        # Wait for OAuth tab
        new_handle = None
        for i in range(20):
            time.sleep(1)
            diff = set(driver.window_handles) - existing_handles
            if diff:
                new_handle = list(diff)[0]
                break
        
        if not new_handle:
            result["message"] = "OAuth tab not opened"
            return result
        
        driver.switch_to.window(new_handle)
        time.sleep(5)
        
        if not click_button(driver, ['Continue as', 'Log in as', 'Allow', 'Authorize'], 'Auth'):
            from selenium.webdriver.common.action_chains import ActionChains
            ActionChains(driver).send_keys(Keys.ENTER).perform()
            time.sleep(3)
        
        time.sleep(8)
        
        # Find FB dashboard
        for handle in driver.window_handles:
            driver.switch_to.window(handle)
            time.sleep(1)
            if 'business.facebook.com' in driver.current_url and 'login' not in driver.current_url.lower():
                break
        
        for _ in range(5):
            close_popup(driver)
            time.sleep(0.5)
        
        result["steps"].append("✅ Authorized")
        
        # Step 4: 1st Boost
        result["steps"].append("Finding 1st Boost...")
        if not navigate_to_posts_page(driver):
            result["message"] = "Cannot access posts page"
            return result
        
        if not find_and_click_boost(driver):
            result["message"] = "1st Boost button not found"
            return result
        result["steps"].append("✅ 1st Boost clicked")
        
        # Step 5: Continue popup
        result["steps"].append("Clicking Continue...")
        time.sleep(3)
        if not click_button(driver, ['Continue', 'Next', 'Submit'], 'Continue Popup'):
            from selenium.webdriver.common.action_chains import ActionChains
            ActionChains(driver).send_keys(Keys.ENTER).perform()
            time.sleep(2)
        time.sleep(3)
        result["steps"].append("✅ Continue clicked")
        
        # Step 6: Continue as User
        result["steps"].append("Handling Continue as User...")
        all_tabs = driver.window_handles
        if len(all_tabs) > 1:
            driver.switch_to.window(all_tabs[-1])
            time.sleep(4)
            
            if not click_button(driver, ['Continue as', 'Continue', 'Log in as', 'OK'], 'Continue as User'):
                from selenium.webdriver.common.action_chains import ActionChains
                ActionChains(driver).send_keys(Keys.ENTER).perform()
                time.sleep(2)
            
            time.sleep(4)
            if len(driver.window_handles) > 1:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                time.sleep(2)
        
        result["steps"].append("✅ Continue as User done")
        
        # Step 7: 2nd Boost
        result["steps"].append("Finding 2nd Boost...")
        if not navigate_to_posts_page(driver):
            result["message"] = "Cannot access posts page for 2nd boost"
            return result
        
        if not find_and_click_boost(driver):
            result["message"] = "2nd Boost button not found"
            return result
        result["steps"].append("✅ 2nd Boost clicked")
        
        # Step 8: Continue + OK
        result["steps"].append("Clicking Continue and OK...")
        time.sleep(3)
        if not click_button(driver, ['Continue', 'Next', 'Submit'], 'Continue 2nd'):
            from selenium.webdriver.common.action_chains import ActionChains
            ActionChains(driver).send_keys(Keys.ENTER).perform()
            time.sleep(2)
        time.sleep(3)
        
        for _ in range(3):
            close_popup(driver)
            time.sleep(0.5)
        
        if click_button(driver, ['OK', 'Ok', 'Confirm', 'Done', 'Submit', 'Publish', 'Continue'], 'OK BUTTON'):
            result["steps"].append("✅ OK clicked!")
        else:
            try:
                from selenium.webdriver.common.by import By
                for sel in ["//button[contains(@class, 'primary')]", "//button[@type='submit']"]:
                    elems = driver.find_elements(By.XPATH, sel)
                    for elem in elems:
                        if elem.is_displayed():
                            js_click(driver, elem, 'OK (blue)')
                            time.sleep(2)
                            break
            except:
                pass
        
        time.sleep(3)
        
        # Cleanup
        for _ in range(5):
            close_popup(driver)
            time.sleep(0.5)
        
        result["success"] = True
        result["message"] = "✅ Boost completed successfully!"
        
        # Update database
        db.update_cookie_status(account_id, 'success')
        db.add_result(chat_id, account_id, 'success')
        
        return result
        
    except Exception as e:
        result["message"] = f"❌ Error: {str(e)[:200]}"
        db.update_cookie_status(account_id, 'failed')
        db.add_result(chat_id, account_id, 'failed')
        return result
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

# ==================== TELEGRAM BOT ====================
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

def safe_send(chat_id: int, text: str, reply_markup=None):
    try:
        bot.send_message(chat_id, text, parse_mode=None, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Send failed: {e}")

def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton("➕ Add Cookie"),
        types.KeyboardButton("📋 My Cookies"),
        types.KeyboardButton("🚀 Run Boost"),
        types.KeyboardButton("📊 Stats"),
        types.KeyboardButton("🗑️ Delete All")
    )
    return markup

# ==================== COMMANDS ====================

@bot.message_handler(commands=['start', 'help'])
def cmd_start(message):
    text = """🤖 <b>Instagram Boost Bot</b>

I can automate Instagram post boosting using cookies!

<b>How it works:</b>
1. Add your Instagram cookies
2. Run boost
3. Get results

<b>Commands:</b>
/add_cookie - Add Instagram cookie
/list_cookies - View your cookies
/run_boost - Run boost on all cookies
/stats - View stats
/delete_all - Delete all cookies

<b>⚠️ Note:</b>
• Cookies must be from Instagram
• Format: name1=value1; name2=value2
• For educational purposes only!"""
    safe_send(message.chat.id, text, main_menu())

@bot.message_handler(commands=['add_cookie'])
def cmd_add_cookie(message):
    chat_id = message.chat.id
    msg = safe_send(chat_id, "📝 Send me your Instagram cookie string:\n\nFormat: name1=value1; name2=value2")
    bot.register_next_step_handler(msg, save_cookie)

def save_cookie(message):
    chat_id = message.chat.id
    cookie_string = message.text.strip()
    
    # Basic validation
    if '=' not in cookie_string:
        safe_send(chat_id, "❌ Invalid cookie format. Must contain '=' signs.\n\nExample: sessionid=abc123; csrftoken=xyz")
        return
    
    # Save to database
    account_id = db.add_cookie(chat_id, cookie_string)
    safe_send(chat_id, f"✅ Cookie #{account_id} saved successfully!\n\nUse /list_cookies to see all.", main_menu())

@bot.message_handler(commands=['list_cookies'])
def cmd_list_cookies(message):
    chat_id = message.chat.id
    cookies = db.get_all_cookies(chat_id)
    
    if not cookies:
        safe_send(chat_id, "📭 No cookies found. Use /add_cookie to add one.", main_menu())
        return
    
    text = f"📋 <b>Your Cookies ({len(cookies)})</b>\n\n"
    for c in cookies:
        text += f"🆔 <b>{c['id']}</b>\n"
        text += f"📊 Status: {c['status']}\n"
        text += f"📅 {c['created_at'][:10]}\n"
        text += "-" * 20 + "\n"
    
    safe_send(chat_id, text, main_menu())

@bot.message_handler(commands=['run_boost'])
def cmd_run_boost(message):
    chat_id = message.chat.id
    
    # Check ChromeDriver
    if not ensure_chromedriver():
        safe_send(chat_id, "❌ ChromeDriver setup failed. Please try again later.")
        return
    
    cookies = db.get_pending_cookies(chat_id)
    if not cookies:
        safe_send(chat_id, "📭 No pending cookies found. Add cookies first with /add_cookie", main_menu())
        return
    
    safe_send(chat_id, f"🚀 Starting boost on {len(cookies)} accounts... This may take a few minutes.", main_menu())
    
    # Run in background
    thread = threading.Thread(target=run_boost_thread, args=(chat_id, cookies))
    thread.daemon = True
    thread.start()

def run_boost_thread(chat_id, cookies):
    results = []
    total = len(cookies)
    success_count = 0
    
    for i, cookie in enumerate(cookies, 1):
        safe_send(chat_id, f"🔄 Processing account {i}/{total}...")
        
        result = process_boost(cookie['cookie_string'], cookie['id'], chat_id)
        
        if result["success"]:
            success_count += 1
            status = "✅ SUCCESS"
        else:
            status = "❌ FAILED"
        
        # Send step details
        steps_text = "\n".join(result["steps"]) if result["steps"] else "No steps recorded"
        safe_send(chat_id, f"📋 Account #{i}\nStatus: {status}\nMessage: {result['message']}\n\nSteps:\n{steps_text}")
        
        time.sleep(3)
    
    # Final summary
    summary = f"""📊 <b>Boost Summary</b>

✅ Success: {success_count}/{total}
❌ Failed: {total - success_count}/{total}
📈 Rate: {(success_count/total)*100:.1f}%

Check your Instagram posts to verify boosts!"""
    safe_send(chat_id, summary, main_menu())

@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    chat_id = message.chat.id
    cookies = db.get_all_cookies(chat_id)
    results = db.get_results(chat_id)
    
    total_cookies = len(cookies)
    pending = len([c for c in cookies if c['status'] == 'pending'])
    success_results = len([r for r in results if r['status'] == 'success'])
    failed_results = len([r for r in results if r['status'] == 'failed'])
    
    text = f"""📊 <b>Your Statistics</b>

<b>Cookies:</b>
• Total: {total_cookies}
• Pending: {pending}

<b>Results:</b>
• Success: {success_results}
• Failed: {failed_results}
• Total: {len(results)}

<b>Commands:</b>
/add_cookie - Add new cookie
/list_cookies - View cookies
/run_boost - Run boost
/delete_all - Delete all cookies"""
    safe_send(chat_id, text, main_menu())

@bot.message_handler(commands=['delete_all'])
def cmd_delete_all(message):
    chat_id = message.chat.id
    count = db.delete_all_cookies(chat_id)
    safe_send(chat_id, f"🗑️ Deleted {count} cookies.", main_menu())

# ==================== BUTTON HANDLERS ====================

@bot.message_handler(func=lambda m: m.text == '➕ Add Cookie')
def btn_add_cookie(message):
    cmd_add_cookie(message)

@bot.message_handler(func=lambda m: m.text == '📋 My Cookies')
def btn_list_cookies(message):
    cmd_list_cookies(message)

@bot.message_handler(func=lambda m: m.text == '🚀 Run Boost')
def btn_run_boost(message):
    cmd_run_boost(message)

@bot.message_handler(func=lambda m: m.text == '📊 Stats')
def btn_stats(message):
    cmd_stats(message)

@bot.message_handler(func=lambda m: m.text == '🗑️ Delete All')
def btn_delete_all(message):
    cmd_delete_all(message)

@bot.message_handler(func=lambda m: True)
def fallback(message):
    safe_send(message.chat.id, "❓ Unknown command. Use /help to see available commands.", main_menu())

# ==================== MAIN ====================
if __name__ == "__main__":
    logger.info("🚀 Instagram Boost Bot starting...")
    
    # Check ChromeDriver
    ensure_chromedriver()
    
    try:
        bot.get_me()
        logger.info("✅ Token valid")
    except Exception as e:
        logger.critical(f"❌ Invalid token: {e}")
        sys.exit(1)
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            logger.critical(f"💥 Polling crashed: {e}")
            time.sleep(5)