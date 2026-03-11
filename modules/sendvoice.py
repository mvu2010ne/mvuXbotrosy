from zlapi.models import Message, ZaloAPIException
import requests
import os
import time
from langdetect import detect
import subprocess
import tempfile
import re

# ===================== CẤU HÌNH =====================
AUSYNC_API_KEY = "zUUVd0MWsd0Q8cybnt6Y49CACGfF_tVpA3SPINzM9K18kUyOwj0KuAUdm6riZe4Ihdhg9kkBlMBWtwmI9ScHTQ"
DEFAULT_VOICE_ID = 651342
VOICE_ID_STORAGE = "user_voices.txt"
# ====================================================

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Gửi voice đến nhóm Zalo khác bằng link (hỗ trợ lệnh trong title chia sẻ link).",
    'tính năng': [
        "sendvoice <nội dung> <link nhóm> → Tạo và gửi voice đến nhóm đích",
        "Hỗ trợ lệnh nằm trong title khi chia sẻ link nhóm",
        "Tự động nhận diện tốc độ (nếu có)",
        "Dùng getiGroup() để lấy ID nhóm chính xác"
    ],
    'hướng dẫn sử dụng': [
        "• Gõ trực tiếp: sendvoice alo alo ai chơi game k https://zalo.me/g/daqzdp079",
        "• Hoặc chia sẻ link nhóm và sửa title thành: sendvoice thằng Minh Vũ Shinn Cte đâu ra đây tao bảo"
    ]
}

# ==================== LƯU & LẤY VOICE_ID CÁ NHÂN ====================
def save_user_voice_id(author_id, voice_id):
    print(f"[DEBUG] Lưu voice ID cho user {author_id}: {voice_id}")
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

# ====================== TEXT TO SPEECH ======================
def instant_tts_ausync(text, author_id=None, speed=1.10):
    voice_id = get_user_voice_id(author_id) or DEFAULT_VOICE_ID
    url = "https://api.ausynclab.io/api/v1/speech/text-to-speech"
    headers = {"accept": "application/json", "X-API-Key": AUSYNC_API_KEY, "Content-Type": "application/json"}
    lang = "vi"
    try:
        detected = detect(text)
        if detected.startswith("en"): lang = "en"
    except: pass

    payload = {
        "audio_name": f"zl_{int(time.time())}",
        "text": text,
        "voice_id": voice_id,
        "speed": speed,
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

        detail_url = f"https://api.ausynclab.io/api/v1/speech/{audio_id}"
        for _ in range(50):
            time.sleep(1.2)
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

# ====================== UPLOAD TO UGUU ======================
def upload_to_uguu(wav_url):
    try:
        wav_data = requests.get(wav_url, timeout=15).content
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_data)
            wav_path = f.name
        aac_path = wav_path.replace(".wav", ".aac")
        subprocess.run([
            "ffmpeg", "-y", "-i", wav_path,
            "-c:a", "aac", "-b:a", "96k", "-ar", "44100", aac_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with open(aac_path, "rb") as f:
            files = {'files[]': ('voice.aac', f, 'audio/aac')}
            r = requests.post("https://uguu.se/upload.php", files=files, timeout=20)
        os.remove(wav_path)
        os.remove(aac_path)
        if r.status_code == 200 and r.json().get("success"):
            return r.json()["files"][0]["url"]
    except Exception as e:
        print(f"[DEBUG] Uguu lỗi: {e}")
    return wav_url  # fallback
# ====================================================================

def send_error_message(thread_id, thread_type, client, text):
    client.send(Message(text=text), thread_id=thread_id, thread_type=thread_type)

# ====================== LỆNH SENDVOICE ======================
def handle_sendvoice_command(message, message_object, thread_id, thread_type, author_id, client):
    print(f"\n[DEBUG] === SENDVOICE COMMAND ===")
    print(f"[DEBUG] User: {author_id} | Nhóm gốc: {thread_id}")

    # Gửi reaction
    try:
        client.sendReaction(message_object, "Đang xử lý...", thread_id, thread_type, reactionType=75)
    except: pass

    # ====================== LẤY NỘI DUNG (HỖ TRỢ TITLE CHIA SẺ LINK) ======================
    raw_text = ""
    group_link_from_href = None

    if hasattr(message_object, 'content'):
        content = message_object.content
        if isinstance(content, str):
            raw_text = content.strip()
            print(f"[DEBUG] Nội dung dạng text: {raw_text}")
        elif isinstance(content, dict):
            title = content.get("title", "").strip()
            href = content.get("href", "")
            print(f"[DEBUG] Tin nhắn chia sẻ link | Title: {title} | Href: {href}")
            raw_text = title
            if href.startswith("https://zalo.me/g/"):
                group_link_from_href = href

    if not raw_text:
        print("[DEBUG] Không có nội dung để xử lý")
        return

    if "sendvoice" not in raw_text.lower():
        print("[DEBUG] Không chứa 'sendvoice' → bỏ qua")
        return

    # Lấy phần sau "sendvoice"
    lower = raw_text.lower()
    cmd_index = lower.find("sendvoice")
    text_after = raw_text[cmd_index + 9:].strip()
    print(f"[DEBUG] Phần sau sendvoice: {text_after}")

    # ====================== TÌM LINK NHÓM ======================
    link_matches = re.findall(r'https?://zalo\.me/g/[a-zA-Z0-9]+', text_after + " " + raw_text)
    if not link_matches and group_link_from_href:
        group_link = group_link_from_href
        print(f"[DEBUG] Dùng link từ href: {group_link}")
    elif link_matches:
        group_link = link_matches[-1]
        print(f"[DEBUG] Link nhóm từ nội dung: {group_link}")
    else:
        send_error_message(thread_id, thread_type, client, "Không tìm thấy link nhóm hợp lệ!")
        return

        # ====================== XỬ LÝ NỘI DUNG & TỐC ĐỘ ======================
    # Loại bỏ từ khóa "sendvoice" (có thể lặp lại), link nhóm và làm sạch
    clean_text = text_after  # text_after là phần sau "sendvoice" đầu tiên

    # Loại bỏ tất cả các từ "sendvoice" (case insensitive)
    clean_text = re.sub(r'\bsendvoice\b', '', clean_text, flags=re.IGNORECASE).strip()

    # Loại bỏ link nhóm (nếu còn sót)
    clean_text = re.sub(r'https?://zalo\.me/g/[a-zA-Z0-9]+', '', clean_text).strip()

    # Loại bỏ khoảng trắng thừa
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()

    parts = clean_text.split()

    # Phát hiện tốc độ nếu có (số ở đầu)
    speed = 1.10
    if parts:
        try:
            potential_speed = float(parts[0].replace(",", "."))
            if 0.5 <= potential_speed <= 3.0:
                speed = potential_speed
                parts = parts[1:]  # Bỏ số tốc độ
                print(f"[DEBUG] Phát hiện tốc độ: {speed}x")
        except ValueError:
            pass  # Không phải số → giữ nguyên

    # Nội dung cuối cùng để đọc
    text = " ".join(parts).strip()

    # Nếu không còn nội dung gì → dùng fallback
    if not text:
        text = "Có người gọi mọi người vào nhóm ơi!"

    if len(text) > 1500:
        send_error_message(thread_id, thread_type, client, "Nội dung quá dài (>1500 ký tự)!")
        return

    print(f"[DEBUG] Nội dung sẽ đọc (sau khi làm sạch): '{text}'")
    print(f"[DEBUG] Tốc độ: {speed}x | Link đích: {group_link}")

    # ====================== TẠO VOICE ======================
    result = instant_tts_ausync(text, author_id, speed)
    if not result["success"]:
        send_error_message(thread_id, thread_type, client, f"Không tạo được voice:\n{result.get('error')}")
        return

    final_url = upload_to_uguu(result["url"])
    try:
        size = int(requests.head(final_url, timeout=10).headers.get('content-length', 150000))
    except:
        size = 150000

    # ====================== LẤY GROUP ID BẰNG getiGroup ======================
    try:
        print(f"[DEBUG] Gọi client.getiGroup({group_link})...")
        group_info = client.getiGroup(group_link)
        print(f"[DEBUG] Response getiGroup: {group_info}")

        if not isinstance(group_info, dict) or 'groupId' not in group_info:
            err = group_info.get('error_message', 'Không có groupId') if isinstance(group_info, dict) else 'Invalid response'
            raise ValueError(err)

        target_thread_id = str(group_info['groupId'])
        print(f"[DEBUG] Group ID đích: {target_thread_id}")

    except ZaloAPIException as e:
        send_error_message(thread_id, thread_type, client, f"Lỗi API Zalo:\n{str(e)}")
        return
    except Exception as e:
        send_error_message(thread_id, thread_type, client, f"Không lấy được ID nhóm:\n{str(e)}")
        return

    # ====================== GỬI VOICE ======================
    try:
        client.sendRemoteVoice(voiceUrl=final_url, thread_id=target_thread_id, thread_type=thread_type, fileSize=size, ttl=60000)
        client.send(Message(text=f"✅ Đã gửi voice thành công!\nNội dung: {text}\nNhóm: {group_link}"), thread_id=thread_id, thread_type=thread_type)
        print("[DEBUG] === SENDVOICE THÀNH CÔNG ===")
    except Exception as e:
        print(f"[ERROR] Lỗi gửi voice: {str(e)}")
        send_error_message(thread_id, thread_type, client, f"Lỗi gửi voice:\n{str(e)}")

# ========================= ĐĂNG KÝ LỆNH =========================
def get_mitaizl():
    return {
        'sendvoice': handle_sendvoice_command
    }