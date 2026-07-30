import asyncio
import random
import json
import os
from datetime import datetime
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError

# ============ बॉट कॉन्फिग ============
BOT_TOKEN = "8236183629:AAG7SiMVzJUM8iWgOgtwmRkIeoghpD9TAiU"  # @BotFather से – बस यहाँ डाल
CONFIG_FILE = "config.json"

# ============ कॉन्फिग फंक्शंस ============
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

# ============ 6 देश – ALL BINS (NO AMEX) ============
COUNTRY_BINS = {
    'United States': {
        'bins': [
            '406837','406838','406839','406840','406841','406842','406843','406844','406845','406846',
            '412345','412346','412347','412348','412349','412350','412351','412352','412353','412354',
            '431234','431235','431236','431237','431238','431239','431240','431241','431242','431243',
            '451234','451235','451236','451237','451238','451239','451240','451241','451242','451243',
            '471234','471235','471236','471237','471238','471239','471240','471241','471242','471243',
            '491234','491235','491236','491237','491238','491239','491240','491241','491242','491243',
            '511234','511235','511236','511237','511238','511239','511240','511241','511242','511243',
            '521234','521235','521236','521237','521238','521239','521240','521241','521242','521243',
            '531234','531235','531236','531237','531238','531239','531240','531241','531242','531243',
            '541234','541235','541236','541237','541238','541239','541240','541241','541242','541243',
            '551234','551235','551236','551237','551238','551239','551240','551241','551242','551243',
            '601120','601121','601122','601123','601124','601125','601126','601127','601128','601129',
            '601130','601131','601132','601133','601134','601135','601136','601137','601138','601139',
            '621234','621235','621236','621237','621238','621239','621240','621241','621242','621243',
            '622234','622235','622236','622237','622238','622239','622240','622241','622242','622243'
        ],
        'flag': '🇺🇸'
    },
    'Japan': {
        'bins': [
            '406837','406838','406839','406840','406841','406842','406843','406844','406845','406846',
            '412345','412346','412347','412348','412349','412350','412351','412352','412353','412354',
            '431234','431235','431236','431237','431238','431239','431240','431241','431242','431243',
            '451234','451235','451236','451237','451238','451239','451240','451241','451242','451243',
            '471234','471235','471236','471237','471238','471239','471240','471241','471242','471243',
            '491234','491235','491236','491237','491238','491239','491240','491241','491242','491243',
            '511234','511235','511236','511237','511238','511239','511240','511241','511242','511243',
            '521234','521235','521236','521237','521238','521239','521240','521241','521242','521243',
            '531234','531235','531236','531237','531238','531239','531240','531241','531242','531243',
            '541234','541235','541236','541237','541238','541239','541240','541241','541242','541243',
            '551234','551235','551236','551237','551238','551239','551240','551241','551242','551243',
            '601120','601121','601122','601123','601124','601125','601126','601127','601128','601129',
            '601130','601131','601132','601133','601134','601135','601136','601137','601138','601139'
        ],
        'flag': '🇯🇵'
    },
    'South Africa': {
        'bins': [
            '406837','406838','406839','406840','406841','406842','406843','406844','406845','406846',
            '476273','476274','476275','476276','476277','476278','476279','476280','476281','476282',
            '539910','539911','539912','539913','539914','539915','539916','539917','539918','539919',
            '521234','521235','521236','521237','521238','521239','521240','521241','521242','521243',
            '531234','531235','531236','531237','531238','531239','531240','531241','531242','531243',
            '541234','541235','541236','541237','541238','541239','541240','541241','541242','541243',
            '601120','601121','601122','601123','601124','601125','601126','601127','601128','601129'
        ],
        'flag': '🇿🇦'
    },
    'Canada': {
        'bins': [
            '412345','412346','412347','412348','412349','412350','412351','412352','412353','412354',
            '451234','451235','451236','451237','451238','451239','451240','451241','451242','451243',
            '471234','471235','471236','471237','471238','471239','471240','471241','471242','471243',
            '491234','491235','491236','491237','491238','491239','491240','491241','491242','491243',
            '523828','523829','523830','523831','523832','523833','523834','523835','523836','523837',
            '531234','531235','531236','531237','531238','531239','531240','531241','531242','531243',
            '541234','541235','541236','541237','541238','541239','541240','541241','541242','541243',
            '551234','551235','551236','551237','551238','551239','551240','551241','551242','551243',
            '601120','601121','601122','601123','601124','601125','601126','601127','601128','601129',
            '621234','621235','621236','621237','621238','621239','621240','621241','621242','621243'
        ],
        'flag': '🇨🇦'
    },
    'Malaysia': {
        'bins': [
            '406845','406846','406847','406848','406849','406850','406851','406852','406853','406854',
            '455201','455202','455203','455204','455205','455206','455207','455208','455209','455210',
            '491681','491682','491683','491684','491685','491686','491687','491688','491689','491690',
            '523828','523829','523830','523831','523832','523833','523834','523835','523836','523837',
            '539910','539911','539912','539913','539914','539915','539916','539917','539918','539919',
            '521234','521235','521236','521237','521238','521239','521240','521241','521242','521243',
            '531234','531235','531236','531237','531238','531239','531240','531241','531242','531243'
        ],
        'flag': '🇲🇾'
    },
    'Brazil': {
        'bins': [
            '406845','406846','406847','406848','406849','406850','406851','406852','406853','406854',
            '455201','455202','455203','455204','455205','455206','455207','455208','455209','455210',
            '491681','491682','491683','491684','491685','491686','491687','491688','491689','491690',
            '523828','523829','523830','523831','523832','523833','523834','523835','523836','523837',
            '531234','531235','531236','531237','531238','531239','531240','531241','531242','531243',
            '541234','541235','541236','541237','541238','541239','541240','541241','541242','541243',
            '551234','551235','551236','551237','551238','551239','551240','551241','551242','551243',
            '601120','601121','601122','601123','601124','601125','601126','601127','601128','601129',
            '621234','621235','621236','621237','621238','621239','621240','621241','621242','621243'
        ],
        'flag': '🇧🇷'
    }
}

# ============ CC जेनरेटर ============
def generate_cc(bin_prefix, country_name):
    for _ in range(200):
        number = bin_prefix + ''.join(str(random.randint(0, 9)) for _ in range(16 - len(bin_prefix)))
        if luhn_check(number):
            year = random.randint(2026, 2035)
            month = random.randint(1, 12)
            cvv = ''.join(str(random.randint(0, 9)) for _ in range(3))
            masked = number[:8] + "********"
            return {
                'number': number,
                'masked': masked,
                'mm': f"{month:02d}",
                'yy': str(year)[2:],
                'cvv': cvv,
                'bin': bin_prefix,
                'country': country_name,
                'flag': COUNTRY_BINS[country_name]['flag']
            }
    return None

def luhn_check(card_number):
    digits = [int(d) for d in str(card_number)]
    checksum = 0
    for i in range(len(digits) - 2, -1, -2):
        doubled = digits[i] * 2
        checksum += doubled if doubled < 10 else doubled - 9
    for i in range(len(digits) - 1, -1, -2):
        checksum += digits[i]
    return checksum % 10 == 0

async def get_bin_info(bin_num):
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as http:
            resp = await http.get(f"https://lookup.binlist.net/{bin_num}")
            if resp.status_code == 200:
                data = resp.json()
                return {
                    'bank': data.get('bank', {}).get('name', 'None'),
                    'scheme': data.get('scheme', 'VISA'),
                    'type': data.get('type', 'DEBIT'),
                    'level': data.get('level', 'COMMERCIAL'),
                    'country': data.get('country', {}).get('name', 'United States'),
                    'code': data.get('country', {}).get('alpha2', 'US')
                }
    except:
        pass
    return None

def format_cc(cc_data, bin_info=None):
    lines = []
    lines.append("✦ APPROVED ✦")
    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append("💳 𝗖𝗖 𝗕𝗶𝗻 𝗠𝗮𝘀𝗸𝗲𝗱")
    lines.append(f"▸ {cc_data['number']}  |  {cc_data['mm']}/{cc_data['yy']}  |  {cc_data['cvv']}")
    lines.append("")
    lines.append("🔥 𝗚𝗘𝗡 𝗖𝗮𝗿𝗱")
    lines.append(f"▸ /gen {cc_data['masked']}|{cc_data['mm']}|20{cc_data['yy']}|xxx")
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append("📋 𝗕𝗜𝗡 𝗜𝗡𝗙𝗢𝗥𝗠𝗔𝗧𝗜𝗢𝗡")
    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    
    if bin_info:
        lines.append(f"💳 𝗕𝗿𝗮𝗻𝗱  :  {bin_info.get('scheme', 'VISA')}")
        lines.append(f"🏦 𝗕𝗮𝗻𝗸   :  {bin_info.get('bank', 'None')}")
        lines.append(f"📝 𝗧𝘆𝗽𝗲   :  {bin_info.get('type', 'DEBIT')}")
        lines.append(f"⭐ 𝗟𝗲𝘃𝗲𝗹  :  {bin_info.get('level', 'COMMERCIAL')}")
        lines.append(f"🌐 𝗖𝗼𝘂𝗻𝘁𝗿𝘆 :  {cc_data['country']} {cc_data['flag']}")
    else:
        lines.append(f"💳 𝗕𝗿𝗮𝗻𝗱  :  VISA")
        lines.append(f"🏦 𝗕𝗮𝗻𝗸   :  None")
        lines.append(f"📝 𝗧𝘆𝗽𝗲   :  DEBIT")
        lines.append(f"⭐ 𝗟𝗲𝘃𝗲𝗹  :  COMMERCIAL")
        lines.append(f"🌐 𝗖𝗼𝘂𝗻𝘁𝗿𝘆 :  {cc_data['country']} {cc_data['flag']}")
    
    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append("╭──〔 ⚡ SCRAPPER 〕──╮")
    lines.append("➜ Premium Scraping")
    lines.append("➜ Instant Results")
    lines.append("➜ Zero Delay")
    lines.append("╰──────────────────╯")
    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append("✦  𝗗𝗘𝗩  @PRO_TG01  ✦")
    
    return "\n".join(lines)

# ============ बॉट ============
bot = TelegramClient('bot_session', api_id=0, api_hash='').start(bot_token=BOT_TOKEN)

@bot.on(events.NewMessage(pattern='/start'))
async def start_cmd(event):
    config = load_config()
    channel = config.get('dump_channel', 'Not Set')
    await event.reply(
        "🤖 **CC GENERATOR BOT**\n\n"
        "🔥 6 देशों की CC जेनरेट करता हूँ:\n"
        "🇺🇸 United States\n"
        "🇯🇵 Japan\n"
        "🇿🇦 South Africa\n"
        "🇨🇦 Canada\n"
        "🇲🇾 Malaysia\n"
        "🇧🇷 Brazil\n\n"
        f"📤 डंप चैनल: `{channel}`\n\n"
        "⚙️ **सेटअप:**\n"
        "1️⃣ चैनल में बॉट को एडमिन बनाओ\n"
        "2️⃣ `/setchannel @channel_username` – चैनल सेट करो\n"
        "3️⃣ बॉट अपने आप CC फेंकना शुरू कर देगा"
    )

@bot.on(events.NewMessage(pattern='/setchannel'))
async def set_channel_cmd(event):
    args = event.message.text.split()
    if len(args) < 2:
        await event.reply("❌ **तरीका:** `/setchannel @channel_username`")
        return
    
    channel = args[1]
    config = load_config()
    config['dump_channel'] = channel
    save_config(config)
    
    await event.reply(f"✅ **चैनल सेट हो गया:** `{channel}`")
    
    try:
        chat = await bot.get_entity(channel)
        await event.reply(f"✅ **चैनल मिल गया:** {chat.title}\nअब CC आना शुरू हो जाएगी।")
    except:
        await event.reply("⚠️ **चैनल नहीं मिला** – यूजरनेम सही है? बॉट चैनल में है?")

# ============ CC जेनरेट करो – हर 1 सेकंड ============
async def continuous_generator():
    print("🚀 CC GENERATOR STARTED...")
    
    while True:
        config = load_config()
        channel = config.get('dump_channel', None)
        
        if not channel:
            await asyncio.sleep(5)
            continue
        
        try:
            country_name = random.choice(list(COUNTRY_BINS.keys()))
            country_data = COUNTRY_BINS[country_name]
            bin_prefix = random.choice(country_data['bins'])
            
            cc = generate_cc(bin_prefix, country_name)
            if cc:
                bin_info = await get_bin_info(bin_prefix)
                formatted = format_cc(cc, bin_info)
                
                try:
                    await bot.send_message(channel, formatted, parse_mode='markdown')
                    print(f"✅ भेजा: {country_name} | BIN: {bin_prefix}")
                except FloodWaitError as e:
                    print(f"⏳ FloodWait: {e.seconds} सेकंड")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    print(f"❌ Error: {e}")
            
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"❌ Loop Error: {e}")
            await asyncio.sleep(5)

# ============ मेन ============
async def main():
    await bot.start()
    print("✅ बॉट चालू है...")
    print("📌 चैनल सेट करने के लिए: /setchannel @channel_username")
    await continuous_generator()

if __name__ == "__main__":
    asyncio.run(main())