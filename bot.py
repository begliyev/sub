import os
import json
import base64
import random
import string
import requests
from datetime import datetime, timedelta

# Sazlamalar (Dinamik hem okap bilýär, ýöne göni goýduk)
TG_TOKEN = "8837363880:AAGJzAvJ4CKfGRkhwXuODOob3bJ6dyjelO4"
ADMIN_ID = "6644058515"
DB_FILE = "db.json"

def send_tg(chat_id, text):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram iberiş hatasy: {e}")

def generate_sub_id(length=8):
    letters_and_digits = string.ascii_lowercase + string.digits
    return ''.join(random.choice(letters_and_digits) for _ in range(length))

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_db(db_data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db_data, f, indent=4, ensure_ascii=False)

def main():
    # GitHub Actions tarapyndan ugradylan Payload-y okamak
    payload_str = os.getenv("TG_PAYLOAD")
    if not payload_str:
        print("Hata: TG_PAYLOAD tapylmady.")
        return

    try:
        payload = json.loads(payload_str)
    except Exception as e:
        print(f"JSON Parse hatasy: {e}")
        return

    message = payload.get("message", {})
    chat_id = str(message.get("chat", {}).get("id", ""))
    text = message.get("text", "").strip()
    
    if not chat_id or not text:
        return

    is_admin = (chat_id == ADMIN_ID)
    db = load_db()

    # MULTI-STEP STATE (Ädim dolandyryşy)
    states = db.get("_states", {})
    user_state = states.get(chat_id)

    # --- JOGAP BERIŞ ETAPLARY (STATE CONTROLLER) ---
    if user_state:
        step = user_state.get("step")
        
        # 1. ETAP: LINKLERI KABUL EDÝÄRIS (Çäksiz link bar)
        if step == "AWAITING_LINKS":
            user_state["configs"] = text
            user_state["step"] = "AWAITING_PROFILE_NAME"
            states[chat_id] = user_state
            db["_states"] = states
            save_db(db)
            send_tg(chat_id, "👤 **2. Ädim:** Ulgamda görünjek **Profil adyny** ýazyň (Mysaly: *LunexSubs*):")
            return

        # 2. ETAP: PROFIL ADYNY KABUL EDÝÄRIS
        elif step == "AWAITING_PROFILE_NAME":
            user_state["profile_name"] = text
            user_state["step"] = "AWAITING_ANNOUNCE"
            states[chat_id] = user_state
            db["_states"] = states
            save_db(db)
            send_tg(chat_id, "📢 **3. Ädim:** Görünjek **Duyuru kanalyny** ýazyň (Başyna @ goşuň, Mysaly: *@tg_lunex*):")
            return

        # 3. ETAP: KANALY KABUL EDIP FAÝLY ÝASÝARYS
        elif step == "AWAITING_ANNOUNCE":
            announce = text
            profile_name = user_state["profile_name"]
            configs = user_state["configs"]
            duration = int(user_state["duration"])
            gb_limit = int(user_state["gb"])
            
            # ID we Hasaplamalar
            sub_id = generate_sub_id()
            total_bytes = gb_limit * 1024 * 1024 * 1024
            expire_date = datetime.utcnow() + timedelta(days=duration)
            expire_timestamp = int(expire_date.timestamp())
            expire_str = expire_date.strftime("%Y-%m-%d")
            
            clean_channel = announce.replace("@", "")

            # SENIŇ ISLÄN ÖSEN MULTI-CONFIG ŞABLONYŇ
            header_text = (
                f"#profile-title: {profile_name}\n"
                f"#profile-update-interval: 1\n"
                f"#subscription-userinfo: upload=0; download=0; total={total_bytes}; expire={expire_timestamp}\n"
                f"#announce: {announce}📌\n"
                f"#support-url: https://t.me/{clean_channel}\n"
                f"#profile-web-page-url: https://t.me/{clean_channel}\n\n"
                f"{configs}"
            )

            # Base64 Kodlama
            b64_content = base64.b64encode(header_text.encode("utf-8")).decode("utf-8")
            
            # Täze individual faýly döretmek
            with open(f"{sub_id}.txt", "w", encoding="utf-8") as f:
                f.write(b64_content)

            # Maglumaty binýada (Database) goşmak
            if chat_id not in db:
                db[chat_id] = []
            db[chat_id].append({
                "id": sub_id,
                "profile": profile_name,
                "expire": expire_str,
                "gb": gb_limit
            })

            # State-i arassalamak
            if chat_id in states:
                del states[chat_id]
            db["_states"] = states
            save_db(db)

            # Netije Linki
            sub_link = f"https://begliyev.github.io/sub/{sub_id}.txt"
            resp = (
                f"✅ **Abonelik Üstünlikli Döredildi!**\n\n"
                f"🌐 **Sizinkiler üçin sub link:**\n`{sub_link}`\n\n"
                f"🆔 ID: `{sub_id}`\n"
                f"👤 Profil Name: {profile_name}\n"
                f"📅 Möhleti: {duration} Gün ({expire_str})\n"
                f"💾 Kota: {gb_limit} GB"
            )
            send_tg(chat_id, resp)
            return

    # --- NORMAL KOMUTLAR ---
    if text.startswith("/start"):
        welcome = (
            "👋 **Vortix 100x Ösen GitHub VPN Botuna Hoş Geldiňiz!**\n\n"
            "➕ **Täze Ýörite Sub Döretmek:**\n"
            "`/add [gün] [gb]` (Mysal: `/add 30 100`)\n\n"
            "📋 **Havuzyny Görkezmek:** `/havuz`\n"
            "🗑️ **Abonelik Öçürmek:** `/delete [id]`"
        )
        if is_admin:
            welcome += "\n\n📢 **Admin Paneli:**\n`/kanal @kanaladi Habar`"
        send_tg(chat_id, welcome)

    elif text.startswith("/add"):
        parts = text.split()
        if len(parts) < 3:
            send_tg(chat_id, "❌ Ýalňyş format. Doğry ulanyş:\n`/add [gün] [gb]`\n*Mysal üçin:* `/add 30 50`")
            return
        
        db["_states"][chat_id] = {
            "step": "AWAITING_LINKS",
            "duration": parts[1],
            "gb": parts[2]
        }
        save_db(db)
        send_tg(chat_id, "🔗 **1. Ädim:** Bu abuneligiň içine goşmak isleýän **ähli VPN proksi linkleriňizi (vless, vmess, ss, trojan)** aşak-aşagyna goýup, ýekeje hatda ugradyň:")

    elif text.startswith("/havuz"):
        user_subs = db.get(chat_id, [])
        if not user_subs:
            send_tg(chat_id, "📭 Havuzyňyzda häzir işjeň abunelik ýok.")
            return
        
        resp = "📋 **Havuzyňyzdaky Işjeň Linkler:**\n\n"
        for sub in user_subs:
            link = f"https://begliyev.github.io/sub/{sub['id']}.txt"
            resp += f"🔹 **[{sub['profile']}]** Möhleti: {sub['expire']} ({sub['gb']} GB)\n🔗 `{link}`\n🗑️ Öçürmek: `/delete {sub['id']}`\n\n"
        send_tg(chat_id, resp)

    elif text.startswith("/delete"):
        parts = text.split()
        if len(parts) < 2:
            send_tg(chat_id, "❌ Öçürmek üçin ID ýazyň. Mysal: `/delete a1b2c3d4`")
            return
        target_id = parts[1]
        
        if chat_id in db:
            initial_len = len(db[chat_id])
            db[chat_id] = [s for s in db[chat_id] if s["id"] != target_id]
            if len(db[chat_id]) < initial_len:
                if os.path.exists(f"{target_id}.txt"):
                    os.remove(f"{target_id}.txt")
                save_db(db)
                send_tg(chat_id, f"🗑️ `{target_id}` ID-li abonelik ulgamdan doly öçürildi.")
                return
        send_tg(chat_id, "❌ Bu ID-ä degişli link tapylmady.")

    elif text.startswith("/kanal") and is_admin:
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            send_tg(chat_id, "📢 Format: `/kanal @kanaladi Habar`")
            return
        target_channel = parts[1]
        channel_msg = parts[2]
        try:
            send_tg(target_channel, channel_msg)
            send_tg(chat_id, f"✅ Habar **{target_channel}** kanalyna üstünlikli ugradyldy!")
        except Exception as e:
            send_tg(chat_id, f"❌ Hata: {str(e)}")

if __name__ == "__main__":
    main()
          
