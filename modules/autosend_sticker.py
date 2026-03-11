import time
import random
import json
from zlapi.models import Message, ThreadType
from datetime import datetime
import pytz
import threading
import os

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Tự động gửi sticker định kỳ cho nhóm, lưu tên và ID nhóm vào cài đặt.",
    'tính năng': [
        "😊 Gửi sticker ngẫu nhiên từ danh sách trong file datasticker.json.",
        "🔄 Khởi chạy tính năng tự động trong một luồng riêng cho mỗi nhóm.",
        "🔔 Thông báo lỗi cụ thể nếu có vấn đề xảy ra khi xử lý yêu cầu.",
        "🔛 Bật/tắt tính năng tự động gửi sticker cho từng nhóm bằng lệnh.",
        "⏱️ Tùy chỉnh thời gian cách nhau (phút) giữa mỗi lần gửi, lưu vào autosend_time_setting.json.",
        "📋 Lưu tên nhóm và ID nhóm vào autosend_time_setting.json để dễ quản lý."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh 'tudongsticker on <phút>' để bật tính năng tự động gửi sticker cho nhóm hiện tại, với <phút> là thời gian cách nhau giữa các lần gửi (tính bằng phút).",
        "📴 Gửi lệnh 'tudongsticker off' để tắt tính năng tự động gửi sticker cho nhóm hiện tại.",
        "📋 Gửi lệnh 'tudongsticker list' để xem danh sách nhóm đang bật tự động, bao gồm tên nhóm và ID nhóm.",
        "📌 Ví dụ: 'tudongsticker on 1' để bật gửi sticker mỗi phút.",
        "✅ Nhận thông báo trạng thái và kết quả ngay lập tức.",
        "⚠️ Lưu ý: stickerType được đặt mặc định là 1. Nếu cần giá trị khác, hãy cập nhật hàm send_sticker_to_group."
    ]
}

# Múi giờ Việt Nam
VN_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

# Dictionary lưu trữ trạng thái và luồng cho từng nhóm
group_settings = {}

def load_stickers():
    """Đọc danh sách sticker từ file datasticker.json."""
    try:
        with open("data/datasticker.json", "r", encoding="utf-8") as f:
            stickers = json.load(f)
            return stickers
    except Exception as e:
        print(f"Lỗi khi đọc file datasticker.json: {e}")
        return []

def load_group_settings():
    """Đọc cài đặt nhóm từ file autosend_time_setting.json."""
    try:
        if os.path.exists("autosend_time_setting.json"):
            with open("autosend_time_setting.json", "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Lỗi khi đọc file autosend_time_setting.json: {e}")
        return {}

def save_group_settings(settings):
    try:
        with open("autosend_time_setting.json", "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        print(f"Successfully saved settings: {settings}")
    except Exception as e:
        print(f"Error saving autosend_time_setting.json: {e}")
        raise

def send_sticker_to_group(client, thread_id, sticker_id, cate_id):
    """Gửi sticker đến một nhóm."""
    try:
        client.sendSticker(
            stickerType=1,
            stickerId=sticker_id,
            cateId=cate_id,
            thread_id=thread_id,
            thread_type=ThreadType.GROUP,
            ttl=int(group_settings.get(thread_id, {}).get('delay_minutes', 1) * 60 * 1000)
        )
    except Exception as e:
        print(f"Lỗi khi gửi sticker đến {thread_id}: {e}")

def auto_send(client, thread_id, delay_minutes):
    """Chạy vòng lặp tự động gửi sticker cho một nhóm cụ thể."""
    stickers = load_stickers()
    stop_event = threading.Event()
    group_settings[thread_id]['stop_event'] = stop_event
    
    while group_settings.get(thread_id, {}).get('enabled', False) and not stop_event.is_set():
        try:
            if stickers:
                sticker = random.choice(stickers)
                sticker_id = sticker.get("id")
                cate_id = sticker.get("catId")
                send_sticker_to_group(client, thread_id, sticker_id, cate_id)
            for _ in range(int(delay_minutes * 60)):
                if stop_event.is_set() or not group_settings.get(thread_id, {}).get('enabled', False):
                    break
                time.sleep(1)
        except Exception as e:
            print(f"Lỗi trong quá trình tự động gửi cho nhóm {thread_id}: {e}")
            time.sleep(1)
    print(f"Đã dừng tự động gửi sticker cho nhóm {thread_id}")

def start_auto(client, thread_id, delay_minutes):
    """Khởi chạy chức năng tự động gửi sticker cho một nhóm."""
    try:
        # Lấy thông tin nhóm
        group_info = client.fetchGroupInfo(thread_id)
        group = group_info.gridInfoMap[str(thread_id)]
        group_name = group.name
        group_id = group.groupId
        
        # Đọc cài đặt hiện tại
        settings = load_group_settings()
        
        if thread_id not in group_settings or not group_settings[thread_id].get('enabled', False):
            group_settings[thread_id] = {
                'enabled': True,
                'delay_minutes': delay_minutes,
                'group_id': group_id,
                'group_name': group_name,
                'thread': threading.Thread(
                    target=auto_send,
                    args=(client, thread_id, delay_minutes),
                    daemon=True
                )
            }
            group_settings[thread_id]['thread'].start()
            
            # Cập nhật file cài đặt
            settings[str(thread_id)] = {
                'enabled': True,
                'delay_minutes': delay_minutes,
                'group_id': group_id,
                'group_name': group_name
            }
            save_group_settings(settings)
            
            return f"Đã bật tính năng tự động gửi sticker cho nhóm {group_name} (ID: {group_id}), gửi mỗi {delay_minutes} phút ✅🚀"
        else:
            return f"Tính năng tự động gửi sticker đã được bật cho nhóm {group_name} (ID: {group_id})! 😊"
    except Exception as e:
        print(f"Lỗi khi khởi chạy tự động gửi cho nhóm {thread_id}: {e}")
        return f"Lỗi khi bật tính năng tự động gửi sticker: {str(e)} 😔"

def stop_auto(thread_id):
    try:
        settings = load_group_settings()
        # Lấy thông tin nhóm từ settings nếu có, để giữ nguyên group_name và group_id
        current_config = settings.get(str(thread_id), {'enabled': False, 'delay_minutes': 1.0, 'group_id': str(thread_id), 'group_name': 'Unknown'})
        if thread_id in group_settings and group_settings[thread_id].get('enabled', False):
            group_settings[thread_id]['enabled'] = False
            if 'stop_event' in group_settings[thread_id]:
                group_settings[thread_id]['stop_event'].set()
            group_settings[thread_id]['thread'] = None
        settings[str(thread_id)] = {
            'enabled': False,
            'delay_minutes': current_config.get('delay_minutes', 1.0),
            'group_id': current_config.get('group_id', str(thread_id)),
            'group_name': current_config.get('group_name', 'Unknown')
        }
        save_group_settings(settings)
        return f"Đã tắt tính năng tự động gửi sticker cho nhóm {current_config['group_name']} (ID: {current_config['group_id']}) ✅"
    except PermissionError as e:
        print(f"Permission error when stopping auto for group {thread_id}: {e}")
        return "Lỗi: Không có quyền ghi cài đặt. Vui lòng kiểm tra quyền truy cập file! 😔"
    except Exception as e:
        print(f"Error when stopping auto for group {thread_id}: {e}")
        return f"Lỗi: {str(e)}. Vui lòng thử lại hoặc liên hệ hỗ trợ! 😔"

def initialize_groups(client):
    """Khởi tạo các nhóm đã được lưu trong autosend_time_setting.json."""
    settings = load_group_settings()
    for thread_id, config in settings.items():
        if config.get('enabled', False):
            try:
                thread_id_int = int(thread_id)
                delay_minutes = float(config.get('delay_minutes', 1))
                # Cập nhật group_name nếu thiếu
                if 'group_name' not in config or config['group_name'] == 'Unknown':
                    try:
                        group_info = client.fetchGroupInfo(thread_id_int)
                        group = group_info.gridInfoMap[str(thread_id_int)]
                        config['group_name'] = group.name
                        config['group_id'] = group.groupId
                        settings[thread_id] = config
                        save_group_settings(settings)
                    except Exception as e:
                        print(f"Lỗi khi cập nhật thông tin nhóm {thread_id}: {e}")
                start_auto(client, thread_id_int, delay_minutes)
            except ValueError:
                print(f"Lỗi khi khởi tạo nhóm {thread_id}: ID hoặc delay không hợp lệ")

def handle_autosend_sticker(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản hồi emoji "✅" xác nhận đã nhận lệnh
    action = "✅ "
    try:
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    except Exception as e:
        print(f"Lỗi khi gửi reaction: {e}")
    """Xử lý lệnh bật/tắt/list tính năng tự động gửi sticker, chỉ dành cho admin."""
    # ID admin được phép sử dụng lệnh
    ADMIN_ID = "3299675674241805615"

    # Kiểm tra quyền admin
    if author_id != ADMIN_ID:
        response_text = "⛔ Bạn không có quyền sử dụng lệnh này! Chỉ admin mới được phép."
        response_message = Message(text=response_text)
        client.replyMessage(response_message, message_object, thread_id, thread_type, ttl=20000)
        return

    parts = message.lower().strip().split()
    if len(parts) >= 2 and parts[0] == "autostk":
        command = parts[1]
        if command == "on" and len(parts) == 3:
            try:
                delay_minutes = float(parts[2])
                if delay_minutes <= 0:
                    response_text = "⛔ Thời gian cách nhau phải lớn hơn 0 phút!"
                else:
                    response_text = start_auto(client, thread_id, delay_minutes)
            except ValueError:
                response_text = "⛔ Thời gian cách nhau phải là một số!"
        elif command == "off":
            response_text = stop_auto(thread_id)
        elif command == "list":
            settings = load_group_settings()
            active_groups = [
                f"📌 Nhóm: {conf['group_name']} (ID: {conf['group_id']}) | Mỗi {conf['delay_minutes']} phút"
                for tid, conf in settings.items()
                if conf.get('enabled', False)
            ]
            if active_groups:
                response_text = "📋 Danh sách nhóm đang bật tự động gửi sticker:\n\n" + "\n".join(active_groups)
            else:
                response_text = "🔕 Không có nhóm nào đang bật tự động gửi sticker."
        else:
            response_text = "❓ Lệnh không hợp lệ! Dùng:\n- autostk on <phút>\n- autostk off\n- autostk list"
    else:
        response_text = "❓ Lệnh không hợp lệ! Dùng:\n- autostk on <phút>\n- autostk off\n- autostk list"

    response_message = Message(text=response_text)
    client.replyMessage(response_message, message_object, thread_id, thread_type, ttl=20000)

def get_mitaizl():
    return {
        'autostk': handle_autosend_sticker,
        'on_start': initialize_groups
    }