from zlapi.models import Message
import requests
import os
import time
import json
from langdetect import detect
import re
import subprocess
import tempfile
import shutil

# ===================== CẤU HÌNH =====================
AUSYNC_API_KEY = "L8hPNfx2DcGOVQFzzhP42HQoDePErds8SWmdU8sPs5zhnkTPFSmLIECXVRL1qCWsG5cP1DEtLgICvf7W1sQqJA"
DEFAULT_VOICE_ID = 651342
VOICE_ID_STORAGE = "user_voices.txt"
# ====================================================

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Chuyển văn bản thành giọng nói siêu tự nhiên + Upload giọng riêng của bạn.",
    'tính năng': [
        "voice <tốc độ> <nội dung> → Đọc bằng giọng cá nhân với tốc độ chỉ định",
        "uploadvoice + file âm thanh → Upload giọng của bạn lên AusyncLab (chỉ cần 5-10s)"
    ],
    'hướng dẫn sử dụng': [
        "voice Xin chào mọi người mình là Minh Vũ Shinn Cte (tốc độ mặc định 1.10)",
        "voice 1.5 Xin chào (tốc độ 1.5x)",
        "voice 0.8 Xin chào (tốc độ 0.8x)",
        "uploadvoice → reply/gửi kèm file âm thanh 5-15 giây"
    ]
}

# ==================== LƯU & LẤY VOICE_ID CÁ NHÂN ====================
def save_user_voice_id(author_id, voice_id):
    with open(VOICE_ID_STORAGE, "a", encoding="utf-8") as f:
        f.write(f"{author_id}:{voice_id}\n")

def get_user_voice_id(author_id):
    if not os.path.exists(VOICE_ID_STORAGE):
        return None
    with open(VOICE_ID_STORAGE, "r", encoding="utf-8") as f:
        for line in f.readlines():
            if line.strip():
                uid, vid = line.strip().split(":", 1)
                if uid == str(author_id):
                    return int(vid)
    return None
# ====================================================================

# ====================== TEXT TO SPEECH (INSTANT) ======================
def instant_tts_ausync(text, author_id=None, speed=1.10):
    voice_id = get_user_voice_id(author_id) or DEFAULT_VOICE_ID

    url = "https://api.ausynclab.io/api/v1/speech/text-to-speech"
    headers = {
        "accept": "application/json",
        "X-API-Key": AUSYNC_API_KEY,
        "Content-Type": "application/json"
    }

    lang = "vi"
    try:
        detected = detect(text)
        if detected.startswith("en"): lang = "en"
    except:
        pass

    payload = {
        "audio_name": f"zl_{int(time.time())}",
        "text": text,  # Bỏ smart_ssml
        "voice_id": voice_id,
        "speed": speed,  # Sử dụng speed từ tham số
        "model_name": "myna-1",
        "language": lang
    }

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        if r.status_code != 200:
            return {"success": False, "error": f"API lỗi {r.status_code}"}

        audio_id = r.json().get("result", {}).get("audio_id")
        if not audio_id:
            return {"success": False, "error": "Không nhận được audio_id"}

        # Polling chờ hoàn thành (tối đa 20 giây)
        detail_url = f"https://api.ausynclab.io/api/v1/speech/{audio_id}"
        for _ in range(50):
            time.sleep(3)
            info = requests.get(detail_url, headers=headers, timeout=10)
            if info.status_code == 200:
                data = info.json().get("result", {})
                if data.get("state") == "SUCCEED":
                    audio_url = data.get("audio_url") or data.get("audio_url_stream")
                    return {"success": True, "url": audio_url}
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}
# ====================================================================

# ====================== UPLOAD GIỌNG CÁ NHÂN ======================
def upload_personal_voice(audio_path, author_id, thread_id, thread_type, client):
    url = "https://api.ausynclab.io/api/v1/voices/register"
    headers = {"X-API-Key": AUSYNC_API_KEY, "accept": "application/json"}

    params = {
        "name": f"Giọng của {author_id}",
        "language": "vi",
        "gender": "FEMALE",
        "age": "YOUNG",
        "use_case": "CASUAL"
    }

    try:
        with open(audio_path, "rb") as f:
            files = {"audio_file": f}
            client.send(Message(text="Đang upload & huấn luyện giọng của bạn... (30-90 giây)"), 
                        thread_id=thread_id, thread_type=thread_type)

            r = requests.post(url, headers=headers, params=params, files=files, timeout=90)

        if r.status_code == 200:
            voice_id = r.json().get("result", {}).get("id")
            if voice_id:
                save_user_voice_id(author_id, voice_id)
                msg = f"Upload giọng thành công!\n" \
                      f"Voice ID: `{voice_id}`\n" \
                      f"Từ giờ bạn dùng lệnh `voice` sẽ tự động đọc bằng giọng của chính mình!"
                client.send(Message(text=msg), thread_id=thread_id, thread_type=thread_type)
            else:
                send_error_message(thread_id, thread_type, client, "Upload thành công nhưng không lấy được ID.")
        else:
            err = r.json().get("message", r.text)
            send_error_message(thread_id, thread_type, client, f"Upload thất bại:\n{err}")
    except Exception as e:
        send_error_message(thread_id, thread_type, client, f"Lỗi upload: {str(e)}")
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)
# ====================================================================

# ========================= LỆNH VOICE =========================
def handle_voice_command(message, message_object, thread_id, thread_type, author_id, client):
    client.sendReaction(message_object, "Đang xử lý", thread_id, thread_type, reactionType=75)

    content = message_object.content.strip()
    parts = content.split(maxsplit=2)  # Thay đổi từ split(maxsplit=1) thành split(maxsplit=2)
    
    if len(parts) < 2 or not parts[1].strip():
        send_error_message(thread_id, thread_type, client, "Dùng: voice <tốc độ> <nội dung cần đọc>\nVí dụ: voice 1.5 Xin chào\nvoice Xin chào (tốc độ mặc định 1.10)")
        return

    # Kiểm tra nếu phần tử thứ 2 có phải là số không
    try:
        # Thử chuyển phần tử thứ 2 thành số float
        speed = float(parts[1])
        # Nếu thành công, lấy nội dung từ phần tử thứ 3
        if len(parts) >= 3:
            text = parts[2].strip()
        else:
            send_error_message(thread_id, thread_type, client, "Thiếu nội dung cần đọc")
            return
    except ValueError:
        # Nếu không phải số, dùng tốc độ mặc định và lấy toàn bộ phần còn lại làm nội dung
        speed = 1.10
        text = content[5:].strip()  # Bỏ "voice " ở đầu

    if not text:
        send_error_message(thread_id, thread_type, client, "Thiếu nội dung cần đọc")
        return

    if len(text) > 1500:
        send_error_message(thread_id, thread_type, client, "Tối đa 1500 ký tự thôi nha!")
        return

    client.send(Message(text=f"Đang tạo giọng nói (tốc độ: {speed}x)..."), thread_id=thread_id, thread_type=thread_type)

    result = instant_tts_ausync(text, author_id, speed)

    if result["success"]:
        final_url = upload_to_uguu(result["url"])

        try:
            size = int(requests.head(final_url, timeout=10).headers.get('content-length', 150000))
        except:
            size = 150000

        client.sendRemoteVoice(
            voiceUrl=final_url,
            thread_id=thread_id,
            thread_type=thread_type,
            fileSize=size,
            ttl=60000
        )
    else:
        send_error_message(thread_id, thread_type, client, f"Không tạo được voice:\n{result.get('error')}")

# ======================= LỆNH UPLOADVOICE =======================
def handle_uploadvoice_command(message, message_object, thread_id, thread_type, author_id, client):
    client.sendReaction(message_object, "Đang xử lý", thread_id, thread_type, reactionType=75)

    # Kiểm tra có attachment âm thanh không
    audio_att = None
    for att in message_object.attachments or []:
        if att.type in ["audio", "voice", "file"]:
            if att.path and os.path.exists(att.path):
                # Kiểm tra định dạng
                if att.path.lower().endswith(('.mp3', '.wav', '.m4a', '.ogg')):
                    audio_att = att
                    break

    if not audio_att or not audio_att.path:
        send_error_message(thread_id, thread_type, client,
            "Cách dùng:\n"
            "• Gửi file âm thanh (mp3/wav) kèm lệnh `uploadvoice`\n"
            "• Hoặc reply file âm thanh rồi gõ `uploadvoice`\n"
            "File nên dài 5-15 giây, nói rõ ràng, không nhạc nền.")
        return

    # Copy file tạm để xử lý
    temp_path = f"temp_voice_{author_id}_{int(time.time())}.mp3"
    try:
        import shutil
        shutil.copy2(audio_att.path, temp_path)
    except:
        send_error_message(thread_id, thread_type, client, "Không đọc được file âm thanh.")
        return

    upload_personal_voice(temp_path, author_id, thread_id, thread_type, client)

# ========================= SEND ERROR =========================
def send_error_message(thread_id, thread_type, client, text):
    client.send(Message(text=text), thread_id=thread_id, thread_type=thread_type)

def upload_to_uguu(wav_url):
    try:
        # 1. Tải .wav
        wav_data = requests.get(wav_url, timeout=15).content
        
        # 2. Chuyển .wav → .aac đúng chuẩn Zalo (bitrate 64k-96k)
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_data)
            wav_path = f.name
        
        aac_path = wav_path.replace(".wav", ".aac")
        subprocess.run([
            "ffmpeg", "-y", "-i", wav_path,
            "-c:a", "aac", "-b:a", "96k",
            "-ar", "44100", aac_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # 3. Upload .aac lên uguu
        with open(aac_path, "rb") as f:
            files = {'files[]': ('voice.aac', f, 'audio/aac')}
            r = requests.post("https://uguu.se/upload.php", files=files, timeout=20)
        
        # Dọn dẹp
        os.remove(wav_path)
        os.remove(aac_path)
        
        if r.status_code == 200:
            data = r.json()
            if data.get("success"):
                return data["files"][0]["url"]
    except Exception as e:
        print("Uguu fix lỗi:", e)
    
    return wav_url  # fallback
        
# ========================= ĐĂNG KÝ LỆNH =========================
def get_mitaizl():
    return {
        'voice': handle_voice_command,
        'uploadvoice': handle_uploadvoice_command
    }