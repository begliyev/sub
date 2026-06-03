import telebot
import requests
import base64
import json
import uuid
from datetime import datetime, timedelta

# 🔐 KENDİ BİLGİLERİNİZ YERLEŞTİRİLDİ
API_TOKEN = '8975976985:AAEo1LH9uOR68_8WJpGSAXlin0xCZRtZOfM'
ADMIN_ID = '6644058515'
GITHUB_TOKEN = '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'
GITHUB_REPO = 'begliyev/sub'

bot = telebot.TeleBot(API_TOKEN)

# GitHub'dan Dosya Okuma Fonksiyonu
def get_github_file(path):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        res = r.json()
        content = base64.b64decode(res['content']).decode('utf-8')
        return content, res['sha']
    return "{}", None

# GitHub'a Dosya Yazma/Güncelleme Fonksiyonu
def update_github_file(path, content, sha=None):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    data = {
        "message": "Vortix Veri Güncellemesi",
        "content": base64.b64encode(content.encode('utf-8')).decode('utf-8')
    }
    if sha:
        data["sha"] = sha
    requests.put(url, headers=headers, json=data)

# 👋 /START KOMUTU
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "👋 **Vortix Pure GitHub VPN Havuz Botuna Hoş Geldiniz!**\n\n"
        "➕ **Link Eklemek İçin Format:**\n"
        "`/add [vpn_linki] [gün] [gb_limiti]`\n\n"
        "📋 **Havuzunuzu Görmek İçin:** /havuz\n"
        "📢 **Kanalları Yönetmek İçin:** /kanal"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

# ➕ /ADD KOMUTU (LİNK EKLEME)
@bot.message_handler(commands=['add'])
def add_link(message):
    parts = message.text.split()
    if len(parts) < 4:
        bot.reply_to(message, "❌ Hatalı format. Örnek:\n`/add vless://link-detaylari 30 100`")
        return
    
    config_data = parts[1]
    duration = parts[2]
    gb_limit = parts[3]
    
    protocol = "VPN"
    if "://" in config_data:
        protocol = config_data.split("://")[0].upper()
        
    user_id = str(message.chat.id)
    sub_id = str(uuid.uuid4())[:8] # 8 haneli kısa benzersiz ID
    expire_date = (datetime.now() + timedelta(days=int(duration))).strftime("%Y-%m-%d")

    # 1. db.json dosyasını güncelle (Havuz veritabanı)
    db_content, sha = get_github_file("db.json")
    try: db = json.loads(db_content)
    except: db = {}
        
    if user_id not in db: db[user_id] = []
        
    new_sub = {
        "id": sub_id,
        "protocol": protocol,
        "config": config_data,
        "gb": gb_limit,
        "expire": expire_date
    }
    db[user_id].append(new_sub)
    update_github_file("db.json", json.dumps(db, indent=4), sha)
    
    # 2. v2ray programlarının okuyacağı ham Base64 dosyasını oluşturuyoruz ({id}.txt şeklinde)
    b64_config = base64.b64encode(config_data.encode('utf-8')).decode('utf-8')
    _, txt_sha = get_github_file(f"{sub_id}.txt")
    update_github_file(f"{sub_id}.txt", b64_config, txt_sha)
    
    # 3. Kullanıcıya VPN'siz GitHub Pages linkini teslim ediyoruz
    sub_link = f"https://begliyev.github.io/sub/{sub_id}.txt"
    
    resp = (
        f"✅ **Havuzunuza Başarıyla Eklendi!**\n\n"
        f"🌐 **VPN Gerektirmeyen Abonelik Linkiniz:**\n`{sub_link}`\n\n"
        f"👑 **Profil:** BegliyevSubs\n"
        f"📊 Protokol: {protocol}\n"
        f"📅 Süre: {duration} Gün\n"
        f"💾 Kota: {gb_limit} GB"
    )
    bot.reply_to(message, resp, parse_mode="Markdown")

# 📋 /HAVUZ KOMUTU (LİNKLERİ LİSTELEME VE SİLME SEÇENEĞİ)
@bot.message_handler(commands=['havuz'])
def show_pool(message):
    user_id = str(message.chat.id)
    db_content, _ = get_github_file("db.json")
    
    try: db = json.loads(db_content)
    except: db = {}

    if user_id not in db or len(db[user_id]) == 0:
        bot.reply_to(message, "📭 Havuzunuzda aktif link bulunmuyor.")
        return

    resp = "📋 **Havuzunuzdaki Aktif Linkler:**\n\n"
    for sub in db[user_id]:
        link = f"https://begliyev.github.io/sub/{sub['id']}.txt"
        resp += f"🔹 **[{sub['protocol']}]** Kalan: {sub['expire']}\n🔗 `{link}`\n🗑️ Silmek için: `/delete {sub['id']}`\n\n"
        
    bot.reply_to(message, resp, parse_mode="Markdown")

# 🗑️ /DELETE KOMUTU (LİNK SİLME)
@bot.message_handler(commands=['delete'])
def delete_link(message):
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ Silmek için link ID'sini belirtin.\nÖrnek: `/delete a1b2c3d4`")
        return
        
    target_id = parts[1]
    user_id = str(message.chat.id)
    db_content, sha = get_github_file("db.json")
    
    try: db = json.loads(db_content)
    except: db = {}
    
    if user_id in db:
        updated_list = [sub for sub in db[user_id] if sub['id'] != target_id]
        if len(updated_list) < len(db[user_id]):
            db[user_id] = updated_list
            update_github_file("db.json", json.dumps(db, indent=4), sha)
            
            # GitHub'daki txt dosyasının da içini boşaltıyoruz
            _, txt_sha = get_github_file(f"{target_id}.txt")
            if txt_sha:
                update_github_file(f"{target_id}.txt", "Deaktif", txt_sha)
                
            bot.reply_to(message, "🗑️ Link havuzdan başarıyla kaldırıldı.")
            return
            
    bot.reply_to(message, "❌ Belirtilen ID'ye sahip bir link bulunamadı.")

# 📢 /KANAL KOMUTU (KANAL YÖNETİMİ)
@bot.message_handler(commands=['kanal'])
def manage_channel(message):
    if str(message.chat.id) != ADMIN_ID:
        bot.reply_to(message, "❌ Bu komut sadece bot sahibine özeldir.")
        return
        
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "📢 **Kanala Duyuru Gönderme Formatı:**\n`/kanal @kanaladi Gidecek Mesaj Metni`")
        return
        
    target_channel = parts[1]
    channel_msg = parts[2]
    
    try:
        bot.send_message(target_channel, channel_msg)
        bot.reply_to(message, f"✅ Mesaj başarıyla {target_channel} kanalına iletildi!")
    except Exception as e:
        bot.reply_to(message, f"❌ Kanala mesaj gönderilemedi.\nBotun o kanalda **Yönetici (Admin)** yetkisi olduğundan emin olun.\nHata: {str(e)}")

bot.infinity_polling()
  
