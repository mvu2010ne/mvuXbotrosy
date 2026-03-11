import time
import random
import json
import requests
import threading
import os
from zlapi import ZaloAPI
from zlapi.models import Message, ThreadType, User, Group
from datetime import datetime
import pytz
from PIL import Image
from io import BytesIO
import tempfile
from config import ADMIN  # Import ADMIN từ config.py

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Tự động gửi ảnh ngẫu nhiên kèm câu thơ từ thotinh.txt cho nhóm, lưu tên và ID nhóm vào cài đặt.",
    'tính năng': [
        "📷 Gửi ảnh ngẫu nhiên từ file girl1.txt dưới dạng PNG với kích thước gốc.",
        "📜 Gửi kèm một câu thơ ngẫu nhiên từ file thotinh.txt.",
        "🔄 Khởi chạy tính năng tự động trong một luồng riêng cho mỗi nhóm.",
        "🔔 Thông báo lỗi cụ thể nếu có vấn đề xảy ra khi xử lý yêu cầu.",
        "🔛 Bật/tắt tính năng tự động gửi ảnh kèm thơ cho từng nhóm bằng lệnh.",
        "⏱️ Tùy chỉnh thời gian cách nhau (phút) giữa mỗi lần gửi, lưu vào auto_image_time_setting.json.",
        "🗑️ Tự động xóa file ảnh tạm sau khi gửi, ảnh tự xóa sau 60 giây.",
        "📋 Lưu tên nhóm và ID nhóm vào auto_image_time_setting.json để dễ quản lý."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh 'tudonganh on <phút>' để bật tính năng tự động gửi ảnh kèm thơ cho nhóm hiện tại, với <phút> là thời gian cách nhau giữa các lần gửi (tính bằng phút).",
        "📴 Gửi lệnh 'tudonganh off' để tắt tính năng tự động gửi ảnh kèm thơ cho nhóm hiện tại.",
        "📋 Gửi lệnh 'tudonganh list' để xem danh sách tất cả nhóm, bao gồm tên nhóm, ID nhóm và trạng thái bật/tắt.",
        "📌 Ví dụ: 'tudonganh on 1' để bật gửi ảnh kèm thơ mỗi phút.",
        "✅ Nhận thông báo trạng thái và kết quả ngay lập tức.",
        "⚠️ Lưu ý: Đảm bảo file girl1.txt và thotinh.txt tồn tại với các link ảnh và thơ hợp lệ."
    ]
}

# Múi giờ Việt Nam
VN_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

# Dictionary lưu trữ trạng thái và luồng cho từng nhóm
image_group_settings = {}

# Khóa đồng bộ để bảo vệ đọc/ghi file
SETTINGS_LOCK = threading.Lock()

# Tạo session HTTP riêng cho tập lệnh này
image_session = requests.Session()
image_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'image/jpeg,image/png,*/*;q=0.8',
    'Referer': 'https://example.com/'
})

def fetch_poems():
    """Lấy danh sách cặp thơ từ file thotinh.txt, mỗi cặp gồm hai dòng ghép bằng \\n."""
    txt_file = 'thotinh1.txt'
    try:
        if not os.path.exists(txt_file):
            print(f"[Image] ERROR: File {txt_file} không tồn tại!")
            return []
        
        with open(txt_file, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]  # Loại bỏ dòng trống
        
        # Ghép các dòng thành cặp thơ (mỗi cặp 2 dòng)
        poems = []
        for i in range(0, len(lines), 2):
            if i + 1 < len(lines):  # Đảm bảo có đủ 2 dòng cho một cặp
                poems.append(f"{lines[i]}\n{lines[i+1]}")
            else:
                print(f"[Image] WARNING: Dòng thơ lẻ cuối file bị bỏ qua: {lines[i]}")
        
        if not poems:
            print(f"[Image] ERROR: Không tìm thấy cặp thơ hợp lệ trong {txt_file}!")
            return []
        
        return poems
    except Exception as e:
        print(f"[Image] Lỗi khi đọc file thotinh.txt: {e}")
        return []

def check_url(url):
    """Kiểm tra URL trước khi tải."""
    try:
        response = image_session.head(url, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def download_image(image_url):
    """Tải ảnh từ URL và lưu vào file tạm dưới dạng PNG, giữ nguyên kích thước gốc."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'image/jpeg,image/png,*/*;q=0.8',
        'Referer': 'https://example.com/'
    }

    try:
        if not check_url(image_url):
            print(f"[Image] ERROR: URL không hợp lệ: {image_url}")
            return None

        image_response = image_session.get(image_url, headers=headers, stream=True, timeout=30)
        image_response.raise_for_status()

        content_type = image_response.headers.get('Content-Type', '').lower()
        if 'image/gif' in content_type:
            print(f"[Image] WARNING: GIF không được hỗ trợ: {image_url}")
            return None

        suffix = '.png'
        image_data = BytesIO(image_response.content)
        image = Image.open(image_data)

        if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3] if image.mode == 'RGBA' else image.getchannel('A'))
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')

        orig_width, orig_height = image.size
        new_width, new_height = orig_width, orig_height  # Giữ nguyên kích thước gốc

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            image_path = tmp.name
            image.save(image_path, format='PNG', optimize=True, quality=85)

        file_size = os.path.getsize(image_path)
        print(f"[Image] Ảnh từ URL: {image_url}")
        print(f"- Định dạng gốc: {content_type}")
        print(f"- Định dạng lưu: PNG")
        print(f"- Độ phân giải: {new_width}x{new_height} pixels")
        print(f"- Kích thước tệp: {file_size} bytes ({file_size / 1024:.2f} KB)")

        return {
            'path': image_path,
            'width': new_width,
            'height': new_height
        }
    except Exception as e:
        print(f"[Image] ERROR: Lỗi khi tải ảnh: {str(e)}")
        return None

def load_image_links():
    """Đọc danh sách link ảnh từ file girl1.txt."""
    txt_file = 'girl1.txt'
    if not os.path.exists(txt_file):
        print(f"[Image] ERROR: File {txt_file} không tồn tại!")
        return []
    with open(txt_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    image_links = [line.strip() for line in lines if line.strip()]
    return image_links

def load_group_settings():
    """Đọc cài đặt nhóm từ file auto_image_time_setting.json."""
    with SETTINGS_LOCK:
        try:
            if os.path.exists("auto_image_time_setting.json"):
                with open("auto_image_time_setting.json", "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"[Image] Lỗi khi đọc file auto_image_time_setting.json: {e}")
            return {}

def save_group_settings(settings):
    """Lưu cài đặt nhóm vào file auto_image_time_setting.json."""
    with SETTINGS_LOCK:
        try:
            with open("auto_image_time_setting.json", "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
            print(f"[Image] Successfully saved settings: {settings}")
        except Exception as e:
            print(f"[Image] Error saving auto_image_time_setting.json: {e}")
            raise

def send_image_with_poem(client, thread_id):
    """Gửi một ảnh ngẫu nhiên kèm câu thơ đến một nhóm."""
    try:
        # Lấy link ảnh ngẫu nhiên
        image_links = load_image_links()
        if not image_links:
            print(f"[Image] ERROR: Không có link ảnh nào trong file girl1.txt!")
            return False

        selected_url = random.choice(image_links)
        image_info = download_image(selected_url)
        if not image_info:
            print(f"[Image] ERROR: Không tải được ảnh từ {selected_url}")
            return False

        # Lấy câu thơ ngẫu nhiên
        poems = fetch_poems()
        poem = random.choice(poems) if poems else "Không thể lấy câu thơ lúc này!"

        # Gửi ảnh kèm thơ
        image_path = image_info['path']
        try:
            with Image.open(image_path) as img:
                img.verify()
            result = client.sendLocalImage(
                imagePath=image_path,
                thread_id=thread_id,
                thread_type=ThreadType.GROUP,
                width=image_info['width'],
                height=image_info['height'],
                message=Message(text=f"📜 {poem}"),
                ttl=int(image_group_settings.get(thread_id, {}).get('delay_minutes', 1) * 60 * 1000)
            )
            if isinstance(result, (User, Group)) or (hasattr(result, 'error_code') and result.error_code == 0):
                print(f"[Image] INFO: Đã gửi ảnh kèm thơ thành công đến {thread_id}")
                return True
            else:
                print(f"[Image] ERROR: Không gửi được ảnh: {getattr(result, 'error_message', 'Unknown error')}")
                return False
        except Exception as e:
            print(f"[Image] ERROR: Lỗi khi gửi ảnh: {str(e)}")
            return False
        finally:
            if os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except Exception as e:
                    print(f"[Image] ERROR: Lỗi khi xóa file tạm {image_path}: {str(e)}")
    except Exception as e:
        print(f"[Image] ERROR: Lỗi trong quá trình gửi ảnh kèm thơ: {e}")
        return False

def auto_send(client, thread_id, delay_minutes):
    """Chạy vòng lặp tự động gửi ảnh kèm thơ cho một nhóm cụ thể."""
    stop_event = threading.Event()
    image_group_settings[thread_id]['stop_event'] = stop_event
    
    while image_group_settings.get(thread_id, {}).get('enabled', False) and not stop_event.is_set():
        try:
            send_image_with_poem(client, thread_id)
            for _ in range(int(delay_minutes * 60)):
                if stop_event.is_set() or not image_group_settings.get(thread_id, {}).get('enabled', False):
                    break
                time.sleep(1)
        except Exception as e:
            print(f"[Image] Lỗi trong quá trình tự động gửi cho nhóm {thread_id}: {e}")
            time.sleep(1)
    print(f"[Image] Đã dừng tự động gửi ảnh kèm thơ cho nhóm {thread_id}")

def start_auto(client, thread_id, delay_minutes):
    """Khởi chạy chức năng tự động gửi ảnh kèm thơ cho một nhóm."""
    try:
        # Lấy thông tin nhóm
        group_info = client.fetchGroupInfo(thread_id)
        group = group_info.gridInfoMap[str(thread_id)]
        group_name = group.name
        group_id = group.groupId
        
        # Đọc cài đặt hiện tại
        settings = load_group_settings()
        
        if thread_id not in image_group_settings or not image_group_settings[thread_id].get('enabled', False):
            image_group_settings[thread_id] = {
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
            image_group_settings[thread_id]['thread'].start()
            
            # Cập nhật file cài đặt
            settings[str(thread_id)] = {
                'enabled': True,
                'delay_minutes': delay_minutes,
                'group_id': group_id,
                'group_name': group_name
            }
            save_group_settings(settings)
            
            return f"✅✅✅ THÀNH CÔNG ✅✅✅\nĐã bật tính năng tự động gửi ảnh cho {group_name}, gửi mỗi {delay_minutes} phút ✅🚀"
        else:
            return f"✅✅✅ THÀNH CÔNG ✅✅✅\nTính năng tự động gửi ảnh kèm thơ đã được bật cho nhóm {group_name} (ID: {group_id})! 😊"
    except Exception as e:
        print(f"[Image] Lỗi khi khởi chạy tự động gửi cho nhóm {thread_id}: {e}")
        return f"❌❌❌ THẤT BẠI ❌❌❌\nLỗi khi bật tính năng tự động gửi ảnh kèm thơ: {str(e)} 😔"

def stop_auto(thread_id):
    """Tắt chức năng tự động gửi ảnh kèm thơ cho một nhóm."""
    try:
        settings = load_group_settings()
        # Lấy thông tin nhóm từ settings nếu có, để giữ nguyên group_name và group_id
        current_config = settings.get(str(thread_id), {'enabled': False, 'delay_minutes': 1.0, 'group_id': str(thread_id), 'group_name': 'Unknown'})
        if thread_id in image_group_settings and image_group_settings[thread_id].get('enabled', False):
            image_group_settings[thread_id]['enabled'] = False
            if 'stop_event' in image_group_settings[thread_id]:
                image_group_settings[thread_id]['stop_event'].set()
            image_group_settings[thread_id]['thread'] = None
        settings[str(thread_id)] = {
            'enabled': False,
            'delay_minutes': current_config.get('delay_minutes', 1.0),
            'group_id': current_config.get('group_id', str(thread_id)),
            'group_name': current_config.get('group_name', 'Unknown')
        }
        save_group_settings(settings)
        return f"✅✅✅ THÀNH CÔNG ✅✅✅\nĐã tắt tính năng tự động gửi ảnh kèm thơ cho nhóm {current_config['group_name']} (ID: {current_config['group_id']}) ✅"
    except PermissionError as e:
        print(f"[Image] Permission error when stopping auto for group {thread_id}: {e}")
        return f"❌❌❌ THẤT BẠI ❌❌❌\nLỗi: Không có quyền ghi cài đặt. Vui lòng kiểm tra quyền truy cập file! 😔"
    except Exception as e:
        print(f"[Image] Error when stopping auto for group {thread_id}: {e}")
        return f"❌❌❌ THẤT BẠI ❌❌❌\nLỗi: {str(e)}. Vui lòng thử lại hoặc liên hệ hỗ trợ! 😔"

def initialize_groups(client):
    """Khởi tạo các nhóm đã được lưu trong auto_image_time_setting.json."""
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
                        print(f"[Image] Lỗi khi cập nhật thông tin nhóm {thread_id}: {e}")
                start_auto(client, thread_id_int, delay_minutes)
            except ValueError:
                print(f"[Image] Lỗi khi khởi tạo nhóm {thread_id}: ID hoặc delay không hợp lệ")

def handle_auto_image(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh bật/tắt/list tính năng tự động gửi ảnh kèm thơ, chỉ dành cho admin."""
    # Gửi phản hồi emoji "✅" xác nhận đã nhận lệnh
    action = "✅ "
    try:
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    except Exception as e:
        print(f"[Image] Lỗi khi gửi reaction: {e}")

    # Kiểm tra quyền admin
    if author_id not in ADMIN:
        response_text = "❌❌❌ THẤT BẠI ❌❌❌\nBạn không có quyền sử dụng lệnh này! Chỉ admin mới được phép."
        response_message = Message(text=response_text)
        client.replyMessage(response_message, message_object, thread_id, thread_type, ttl=20000)
        return

    parts = message.lower().strip().split()
    if len(parts) >= 2 and parts[0] == "autoimg":
        command = parts[1]
        if command == "on" and len(parts) == 3:
            try:
                delay_minutes = float(parts[2])
                if delay_minutes <= 0:
                    response_text = "❌❌❌ THẤT BẠI ❌❌❌\nThời gian cách nhau phải lớn hơn 0 phút!"
                else:
                    response_text = start_auto(client, thread_id, delay_minutes)
            except ValueError:
                response_text = "❌❌❌ THẤT BẠI ❌❌❌\nThời gian cách nhau phải là một số!"
        elif command == "off":
            response_text = stop_auto(thread_id)
        elif command == "list":
            settings = load_group_settings()
            group_list = [
                f"📌 Nhóm: {conf['group_name']} (ID: {conf['group_id']}) | Mỗi {conf['delay_minutes']} phút | {'Bật' if conf.get('enabled', False) else 'Tắt'}"
                for tid, conf in settings.items()
            ]
            if group_list:
                response_text = f"✅✅✅ THÀNH CÔNG ✅✅✅\nDanh sách nhóm:\n\n" + "\n".join(group_list)
            else:
                response_text = f"✅✅✅ THÀNH CÔNG ✅✅✅\nKhông có nhóm nào được lưu."
        else:
            response_text = "❌❌❌ THẤT BẠI ❌❌❌\nLệnh không hợp lệ! Dùng:\n- autoimg on <phút>\n- autoimg off\n- autoimg list"
    else:
        response_text = "❌❌❌ THẤT BẠI ❌❌❌\nLệnh không hợp lệ! Dùng:\n- autoimg on <phút>\n- autoimg off\n- autoimg list"

    response_message = Message(text=response_text)
    client.replyMessage(response_message, message_object, thread_id, thread_type, ttl=20000)

def get_mitaizl():
    """Trả về các lệnh và hàm khởi tạo của bot."""
    return {
        'autoimg': handle_auto_image,
        'on_start_image': initialize_groups
    }
    