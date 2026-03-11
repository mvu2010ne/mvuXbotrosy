from zlapi.models import Message
import requests
import os
import time
import json
from langdetect import detect
import subprocess
import tempfile
# ===================== CẤU HÌNH =====================
AUSYNC_API_KEY = "L8hPNfx2DcGOVQFzzhP42HQoDePErds8SWmdU8sPs5zhnkTPFSmLIECXVRL1qCWsG5cP1DEtLgICvf7W1sQqJA"
# Danh sách giọng nói: key (tên lệnh, viết thường, không dấu) → (voice_id, tên hiển thị đẹp)
VOICE_CONFIG = {
    "huanhoahong": (659415, "Huấn Hoa Hồng"), # Giọng mặc định
    "gaibac": (651342, "Gái Bắc"),
    "gaixinh": (659483, "Gái Xinh"),
    "gaimientay": (659508, "Gái Miền Tây"),
    "btv": (660066, "BTV Thu Huyền"),
    "beat": (691633, "Beat Đỏ"),
    "bn": (694213, "Bích Ngọc"),
    "nbt": (754094, "Nobita"),
    "lcc": (754100, "Lý Công công"),
    "bachtuyet": (756178, "Bạch Tuyết"),
    "chunghandong": (756172, "Chung Hân Đồng"),
    "krixi": (756164, "Krixi"),
    "nguyanhlac": (756158, "Ngụy Anh Lạc"),
    "nuphandien": (756157, "Nữ Phản Diện"),
}
# Giọng mặc định
DEFAULT_VOICE_KEY = "gaibac"
DEFAULT_VOICE_ID = VOICE_CONFIG[DEFAULT_VOICE_KEY][0]
VOICE_ID_STORAGE = "user_voices.txt" # Giữ lại nếu sau này muốn hỗ trợ giọng cá nhân
# ==============================================================================
des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Chuyển đổi văn bản thành giọng nói siêu tự nhiên (AusyncLab).",
    'tính năng': [
        "🗣️ Tự động phát hiện ngôn ngữ (hỗ trợ tiếng Việt & tiếng Anh tốt nhất).",
        "🎙️ Giọng đọc siêu tự nhiên, hỗ trợ chọn giọng: Huấn Hoa Hồng (mặc định), Gái Bắc.",
        "📤 Gửi trực tiếp voice tương thích Zalo.",
        "📥 Hỗ trợ reply tin nhắn hoặc nhập trực tiếp sau lệnh read."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi: read <tên giọng> <nội dung>",
        " Ví dụ: read huanhoahong Xin chào mọi người",
        " Ví dụ: read gaibac Chào các bạn miền Bắc",
        " Hoặc chỉ: read Xin chào (dùng giọng mặc định)",
        "📌 Reply tin nhắn + lệnh: read hoặc read <tên giọng>",
        "📋 Xem danh sách giọng: read list",
        "✅ Nhận ngay file voice tự nhiên."
    ]
}
# ==================== LẤY THÔNG TIN GIỌNG NÓI ====================
def get_voice_info(voice_key):
    voice_key = voice_key.lower().strip()
    return VOICE_CONFIG.get(voice_key, VOICE_CONFIG[DEFAULT_VOICE_KEY])
# ====================== TEXT TO SPEECH (INSTANT) ======================
def instant_tts_ausync(text, voice_id=DEFAULT_VOICE_ID, speed=1.10):
    print(f"[TTS] Bắt đầu tạo giọng nói | Voice ID: {voice_id} | Tốc độ: {speed}x | Độ dài text: {len(text)} ký tự")
    url = "https://api.ausynclab.io/api/v1/speech/text-to-speech"
    headers = {
        "accept": "application/json",
        "X-API-Key": AUSYNC_API_KEY,
        "Content-Type": "application/json"
    }
    lang = "vi"
    try:
        detected = detect(text)
        print(f"[TTS] Phát hiện ngôn ngữ: {detected}")
        if detected.startswith("en"):
            lang = "en"
    except Exception as e:
        print(f"[TTS] Lỗi detect ngôn ngữ: {e} → dùng mặc định 'vi'")
    payload = {
        "audio_name": f"zl_read_{int(time.time())}",
        "text": text,
        "voice_id": voice_id,
        "speed": speed,
        "model_name": "myna-2",
        "language": lang
    }
    try:
        print("[TTS] Đang gửi yêu cầu POST tới AusyncLab...")
        r = requests.post(url, json=payload, headers=headers, timeout=60)
        print(f"[TTS] POST response: {r.status_code}")
        if r.status_code != 200:
            error_msg = f"API lỗi {r.status_code} - {r.text}"
            print(f"[TTS] LỖI: {error_msg}")
            return {"success": False, "error": error_msg}
       
        audio_id = r.json().get("result", {}).get("audio_id")
        if not audio_id:
            print("[TTS] Không nhận được audio_id từ response")
            return {"success": False, "error": "Không nhận được audio_id"}
        print(f"[TTS] Nhận audio_id: {audio_id} → Bắt đầu polling...")
        detail_url = f"https://api.ausynclab.io/api/v1/speech/{audio_id}"
        for i in range(80):
            time.sleep(3)
            print(f"[TTS] Polling lần {i+1}/80...")
            info = requests.get(detail_url, headers=headers, timeout=15)
            if info.status_code == 200:
                data = info.json().get("result", {})
                state = data.get("state")
                print(f"[TTS] Trạng thái: {state}")
                if state == "SUCCEED":
                    audio_url = data.get("audio_url") or data.get("audio_url_stream")
                    print(f"[TTS] THÀNH CÔNG! URL âm thanh: {audio_url}")
                    return {"success": True, "url": audio_url}
                elif state == "FAILED":
                    print("[TTS] Xử lý thất bại trên server Ausync")
                    return {"success": False, "error": "Ausync xử lý thất bại"}
            else:
                print(f"[TTS] Lỗi khi polling: {info.status_code}")
        print("[TTS] HẾT THỜI GIAN polling")
        return {"success": False, "error": "Timeout chờ xử lý"}
    except Exception as e:
        print(f"[TTS] Exception: {str(e)}")
        return {"success": False, "error": str(e)}
# ====================== UPLOAD LÊN UGUU (CHUYỂN AAC CHO ZALO) ======================
def upload_to_uguu(wav_url):
    print(f"[UGUU] Bắt đầu upload | URL gốc: {wav_url}")
    try:
        print("[UGUU] Đang tải file .wav từ Ausync...")
        wav_data = requests.get(wav_url, timeout=60).content
        print(f"[UGUU] Tải thành công, kích thước: {len(wav_data)} bytes")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_data)
            wav_path = f.name
        aac_path = wav_path.replace(".wav", ".aac")
        print(f"[UGUU] Đang chuyển đổi sang .aac → {aac_path}")
        subprocess.run([
            "ffmpeg", "-y", "-i", wav_path,
            "-c:a", "aac", "-b:a", "96k",
            "-ar", "44100", aac_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("[UGUU] Chuyển đổi AAC thành công")
        print("[UGUU] Đang upload .aac lên uguu.se...")
        with open(aac_path, "rb") as f:
            files = {'files[]': ('voice.aac', f, 'audio/aac')}
            r = requests.post("https://uguu.se/upload.php", files=files, timeout=60)
        os.remove(wav_path)
        os.remove(aac_path)
        print("[UGUU] Đã dọn file tạm")
        if r.status_code == 200:
            data = r.json()
            if data.get("success"):
                final_url = data["files"][0]["url"]
                print(f"[UGUU] Upload thành công! URL cuối: {final_url}")
                return final_url
        print(f"[UGUU] Upload thất bại, response: {r.text}")
    except Exception as e:
        print(f"[UGUU] Lỗi: {str(e)}")
    print("[UGUU] Dùng fallback URL gốc")
    return wav_url
# ========================= XỬ LÝ LỆNH READ =========================
def handle_read_command(message, message_object, thread_id, thread_type, author_id, client):
    print(f"\n=== [READ COMMAND] Từ user {author_id} | Thread {thread_id} ===")
    content = message_object.content.strip().lower()
    parts = content.split()
    
    if len(parts) >= 2 and parts[1] == "list":
        # Xử lý lệnh read list: hiển thị danh sách giọng nói
        voice_list = "\n".join([f"• {key}: {display_name}" for key, (_, display_name) in VOICE_CONFIG.items()])
        default_info = f"Giọng mặc định: {VOICE_CONFIG[DEFAULT_VOICE_KEY][1]} ({DEFAULT_VOICE_KEY})"
        list_message = f"📋 Danh sách giọng nói hỗ trợ:\n{voice_list}\n\n{default_info}\n\nSử dụng: read <tên giọng> <nội dung>"
        client.send(Message(text=list_message), thread_id=thread_id, thread_type=thread_type)
        print("[READ LIST] Đã gửi danh sách giọng nói")
        return
    
    # Xử lý lệnh read thông thường
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
    # Xác định nội dung cần đọc và giọng nói
    is_reply = hasattr(message_object, 'quote') and message_object.quote
    quoted_text = ""
    if is_reply:
        if hasattr(message_object.quote, 'msg') and message_object.quote.msg:
            quoted_text = message_object.quote.msg.strip()
        elif hasattr(message_object.quote, 'content') and message_object.quote.content:
            quoted_text = message_object.quote.content.strip()
    # Phân tích lệnh
    content = message_object.content.strip()
    parts = content.split()
   
    voice_key = DEFAULT_VOICE_KEY
    text = ""
    if len(parts) >= 2:
        first_word = parts[1].lower()
        if first_word in VOICE_CONFIG:
            voice_key = first_word
            text = " ".join(parts[2:]).strip() if len(parts) > 2 else quoted_text
        else:
            text = " ".join(parts[1:]).strip()
    else:
        text = quoted_text # Không có nội dung sau "read" → dùng nội dung reply
    if not text:
        send_error_message(thread_id, thread_type, client, "Vui lòng nhập nội dung hoặc reply tin nhắn cần đọc.")
        return
    if len(text) > 1500:
        send_error_message(thread_id, thread_type, client, "Nội dung tối đa 1500 ký tự thôi nha!")
        return
    # Lấy thông tin giọng nói
    voice_id, voice_display_name = get_voice_info(voice_key)
    print(f"[READ] Sử dụng giọng: {voice_key} → {voice_display_name} (ID: {voice_id}) | Nội dung: '{text[:100]}...'")
    # Thông báo đang tạo với tên giọng đẹp
    client.send(Message(text=f"Đang tạo giọng nói của {voice_display_name}... "),
                thread_id=thread_id, thread_type=thread_type)
    result = instant_tts_ausync(text, voice_id=voice_id, speed=1.10)
    if result["success"]:
        final_url = upload_to_uguu(result["url"])
        try:
            size = int(requests.head(final_url, timeout=15).headers.get('content-length', 150000))
        except:
            size = 150000
        client.sendRemoteVoice(
            voiceUrl=final_url,
            thread_id=thread_id,
            thread_type=thread_type,
            fileSize=size,
            ttl=60000
        )
        print("[READ] Đã gửi voice thành công!\n")
    else:
        error = result.get('error', 'Lỗi không xác định')
        send_error_message(thread_id, thread_type, client, f"Không tạo được giọng nói:\n{error}")
        print(f"[READ] TTS thất bại: {error}\n")
# ========================= GỬI LỖI =========================
def send_error_message(thread_id, thread_type, client, text="Lỗi rồi nha..."):
    print(f"[ERROR] Gửi lỗi: {text}")
    client.send(Message(text=text), thread_id=thread_id, thread_type=thread_type)
# ========================= ĐĂNG KÝ LỆNH =========================
def get_mitaizl():
    return {
        'read': handle_read_command
    }