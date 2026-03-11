import sys
import os
import json
import time
import threading
from datetime import datetime
from zoneinfo import ZoneInfo
from config import ADMIN
from zlapi.models import Message, MessageStyle, MultiMsgStyle, ThreadType

AUTO_RESET_SETTING_FILE = "auto_reset_setting.json"
vietnam_tz = ZoneInfo("Asia/Ho_Chi_Minh")

# Dictionary lưu trữ trạng thái tự động reset
auto_reset_setting = {}
# Khóa đồng bộ để bảo vệ đọc/ghi file
SETTINGS_LOCK = threading.Lock()

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Quản lý tính năng tự động reset bot định kỳ.",
    'tính năng': [
        "🔄 Tự động reset bot mỗi 30 phút (hoặc thời gian tùy chỉnh).",
        "🔒 Chỉ admin được phép sử dụng lệnh bật/tắt.",
        "📋 Lưu cài đặt tự động reset vào file auto_reset_setting.json.",
        "🔛 Bật/tắt tính năng tự động reset bằng lệnh.",
        "📊 Kiểm tra trạng thái tự động reset với lệnh status."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh `autors on <phút>` để bật tự động reset bot, với <phút> là thời gian cách nhau (mặc định 30 phút nếu không chỉ định).",
        "📴 Gửi lệnh `autors off` để tắt tự động reset bot.",
        "📋 Gửi lệnh `autors status` để xem trạng thái tự động reset.",
        "📌 Ví dụ: `autors on 30` để bật reset tự động mỗi 30 phút."
    ]
}

def is_admin(author_id):
    return author_id in ADMIN

def load_reset_settings():
    """Đọc cài đặt từ file auto_reset_setting.json."""
    with SETTINGS_LOCK:
        try:
            if os.path.exists(AUTO_RESET_SETTING_FILE):
                with open(AUTO_RESET_SETTING_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {"enabled": False, "delay_minutes": 30.0, "last_start_time": None}
        except Exception as e:
            print(f"[AutoReset] Lỗi khi đọc auto_reset_setting.json: {e}")
            return {"enabled": False, "delay_minutes": 30.0, "last_start_time": None}

def save_reset_settings(settings):
    """Lưu cài đặt vào file auto_reset_setting.json."""
    with SETTINGS_LOCK:
        try:
            with open(AUTO_RESET_SETTING_FILE, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
            print(f"[AutoReset] Đã lưu cài đặt: {settings}")
        except Exception as e:
            print(f"[AutoReset] Lỗi khi lưu auto_reset_setting.json: {e}")
            raise

def send_reply_with_style(client, text, message_object, thread_id, thread_type, ttl=30000, color="#000000"):
    """Gửi tin nhắn phản hồi với định dạng màu sắc và in đậm."""
    base_length = len(text)
    adjusted_length = base_length + 355
    style = MultiMsgStyle([
        MessageStyle(offset=0, length=adjusted_length, style="color", color=color, auto_format=False),
        MessageStyle(offset=0, length=adjusted_length, style="bold", size="8", auto_format=False)
    ])
    msg = Message(text=text, style=style)
    try:
        if message_object:
            print(f"[AutoReset] Trả lời tin nhắn với replyMessage, thread_id: {thread_id}, thread_type: {thread_type}")
            client.replyMessage(msg, message_object, thread_id, thread_type, ttl=ttl)
        else:
            print(f"[AutoReset] Gửi tin nhắn mới với sendMessage, thread_id: {thread_id}, thread_type: {thread_type}")
            client.sendMessage(msg, thread_id, thread_type, ttl=ttl)
        return True
    except Exception as e:
        print(f"[AutoReset] Lỗi khi gửi tin nhắn: {e}")
        return False

def auto_reset(client, delay_minutes):
    """Chạy vòng lặp tự động reset bot."""
    stop_event = threading.Event()
    auto_reset_setting['stop_event'] = stop_event
    default_thread_id = "643794532760252296"  # Nhóm mặc định từ main.py

    while auto_reset_setting.get('enabled', False) and not stop_event.is_set():
        # Lưu thời gian bắt đầu chu kỳ reset
        auto_reset_setting['last_start_time'] = time.time()
        
        # Đợi đủ thời gian delay_minutes trước khi reset
        for _ in range(int(delay_minutes * 60)):
            if stop_event.is_set() or not auto_reset_setting.get('enabled', False):
                break
            time.sleep(1)
        if not auto_reset_setting.get('enabled', False) or stop_event.is_set():
            break
        try:
            msg = "🆘 Bot sẽ tự động khởi động lại sau 5 giây..."
            send_reply_with_style(client, msg, None, default_thread_id, ThreadType.GROUP, ttl=8000)
            time.sleep(5)
            python = sys.executable
            os.execl(python, python, *sys.argv)
        except Exception as e:
            print(f"[AutoReset] Lỗi trong quá trình tự động reset: {e}")
            msg = f"🚫 Lỗi khi tự động reset: {str(e)}"
            send_reply_with_style(client, msg, None, default_thread_id, ThreadType.GROUP, ttl=60000)
            time.sleep(60)  # Đợi 1 phút trước khi thử lại nếu có lỗi
        
        # Lưu cài đặt sau mỗi chu kỳ
        settings = {
            'enabled': auto_reset_setting.get('enabled', False),
            'delay_minutes': delay_minutes,
            'last_start_time': auto_reset_setting['last_start_time']
        }
        save_reset_settings(settings)
    
    print(f"[AutoReset] Đã dừng tự động reset")

def start_auto_reset(client, delay_minutes=30):
    """Khởi chạy chức năng tự động reset bot."""
    print(f"[AutoReset] Bắt đầu start_auto_reset với delay {delay_minutes} phút")
    try:
        # Nếu tính năng đã bật, dừng luồng hiện tại
        if auto_reset_setting.get('enabled', False):
            stop_auto_reset()

        # Cập nhật trạng thái mới
        auto_reset_setting['enabled'] = True
        auto_reset_setting['delay_minutes'] = delay_minutes
        auto_reset_setting['last_start_time'] = time.time()
        auto_reset_setting['thread'] = threading.Thread(
            target=auto_reset,
            args=(client, delay_minutes),
            daemon=True
        )
        auto_reset_setting['thread'].start()
        print(f"[AutoReset] Luồng auto_reset đã khởi động, thread alive: {auto_reset_setting['thread'].is_alive()}")

        # Lưu cài đặt sau khi cập nhật
        settings = {
            'enabled': True,
            'delay_minutes': delay_minutes,
            'last_start_time': auto_reset_setting['last_start_time']
        }
        save_reset_settings(settings)

        return f"✅ Đã bật tự động reset bot, reset mỗi {delay_minutes} phút 🚀"
    except Exception as e:
        print(f"[AutoReset] Lỗi khi khởi chạy tự động reset: {e}")
        return f"😔 Lỗi khi bật tự động reset: {str(e)}"

def stop_auto_reset():
    """Tắt chức năng tự động reset bot."""
    try:
        if auto_reset_setting.get('enabled', False):
            auto_reset_setting['enabled'] = False
            if 'stop_event' in auto_reset_setting:
                auto_reset_setting['stop_event'].set()
            auto_reset_setting['thread'] = None
            auto_reset_setting['last_start_time'] = None
            settings = {
                'enabled': False,
                'delay_minutes': auto_reset_setting.get('delay_minutes', 30.0),
                'last_start_time': None
            }
            save_reset_settings(settings)
            return f"✅ Đã tắt tự động reset bot"
        else:
            return f"😊 Tính năng tự động reset đã tắt trước đó!"
    except Exception as e:
        print(f"[AutoReset] Lỗi khi dừng tự động reset: {e}")
        return f"😔 Lỗi: {str(e)}. Vui lòng thử lại hoặc liên hệ hỗ trợ!"

def initialize_auto_reset(client):
    """Khởi tạo tính năng tự động reset từ cài đặt đã lưu."""
    settings = load_reset_settings()
    if settings.get('enabled', False):
        try:
            delay_minutes = float(settings.get('delay_minutes', 30))
            auto_reset_setting['last_start_time'] = settings.get('last_start_time', None)
            start_auto_reset(client, delay_minutes)
            print(f"[AutoReset] Đã khởi tạo tự động reset với delay {delay_minutes} phút")
        except ValueError:
            print(f"[AutoReset] Lỗi khi khởi tạo: delay không hợp lệ")

def handle_auto_reset(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh bật/tắt/status tính năng tự động reset, chỉ dành cho admin."""
    print(f"[AutoReset] Nhận lệnh: {message}, author_id: {author_id}, thread_id: {thread_id}, thread_type: {thread_type}")
    
    if not is_admin(author_id):
        response_text = "⛔ Chỉ admin mới có quyền sử dụng lệnh này."
        print(f"[AutoReset] Không phải admin, trả lời: {response_text}")
        send_reply_with_style(client, response_text, message_object, thread_id, thread_type, ttl=20000)
        return

    parts = message.lower().strip().split()
    print(f"[AutoReset] Parts: {parts}")
    if len(parts) >= 1 and parts[0] == "autors":
        if len(parts) == 1:
            response_text = "❓ Vui lòng nhập lệnh đầy đủ! Dùng:\n- autors on <phút>\n- autors off\n- autors status"
        else:
            command = parts[1]
            if command == "on":
                try:
                    delay_minutes = float(parts[2]) if len(parts) > 2 else 30.0
                    if delay_minutes <= 0:
                        response_text = "⛔ Thời gian cách nhau phải lớn hơn 0 phút!"
                    else:
                        response_text = start_auto_reset(client, delay_minutes)
                except ValueError:
                    response_text = "⛔ Thời gian cách nhau phải là một số!"
            elif command == "off":
                response_text = stop_auto_reset()
            elif command == "status":
                settings = load_reset_settings()
                status = "Bật" if settings.get('enabled', False) else "Tắt"
                delay = settings.get('delay_minutes', 30.0)
                remaining_text = "Không xác định"
                if status == "Bật" and auto_reset_setting.get('last_start_time'):
                    elapsed = time.time() - auto_reset_setting['last_start_time']
                    remaining_seconds = (delay * 60) - elapsed
                    if remaining_seconds > 0:
                        remaining_minutes = int(remaining_seconds // 60)
                        remaining_secs = int(remaining_seconds % 60)
                        remaining_text = f"{remaining_minutes} phút {remaining_secs} giây"
                    else:
                        remaining_text = "Sắp reset"
                response_text = f"📊 Trạng thái tự động reset: {status}\n⏱️ Thời gian cách nhau: {delay} phút\n⏳ Thời gian còn lại: {remaining_text}"
            else:
                response_text = "❓ Lệnh không hợp lệ! Dùng:\n- autors on <phút>\n- autors off\n- autors status"
    else:
        response_text = "❓ Lệnh không hợp lệ! Dùng:\n- autors on <phút>\n- autors off\n- autors status"

    print(f"[AutoReset] Trả lời: {response_text}")
    send_reply_with_style(client, response_text, message_object, thread_id, thread_type, ttl=20000)

def get_mitaizl():
    """Trả về các lệnh và hàm khởi tạo của bot."""
    return {
        'autors': handle_auto_reset,
        'on_start_auto_reset': initialize_auto_reset
    }
