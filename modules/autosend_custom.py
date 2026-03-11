import time
import random
import json
import os
import requests
from zlapi.models import Message, ThreadType
from datetime import datetime, timedelta
import pytz
import threading
import re

# Tệp lưu trữ các bộ tin nhắn
MESSAGE_SETS_FILE = "message_sets.json"

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Tự động gửi tin nhắn quảng cáo sản phẩm vào các khung giờ cố định",
    'tính năng': [
        "🕒 Gửi tin nhắn vào các khung giờ cố định hàng ngày với nội dung và ảnh tùy chỉnh theo khung giờ.",
        "🖼️ Gửi ảnh cố định trước tin nhắn từ tệp cục bộ hoặc URL, với nội dung tin nhắn hiển thị dưới ảnh.",
        "🔍 Lọc và gửi tin nhắn đến các nhóm không nằm trong danh sách loại trừ.",
        "🔄 Khởi chạy tính năng tự động trong một luồng riêng.",
        "🔔 Thông báo lỗi cụ thể nếu có vấn đề xảy ra khi xử lý yêu cầu.",
        "📩 Lệnh addset tạo mới một bộ khung giờ, tin nhắn, và ảnh, lưu vào tệp JSON.",
        "📩 Lệnh sendset <tên_bộ> gửi ngay tin nhắn và ảnh của bộ được chỉ định.",
        "📋 Lệnh listsets hiển thị danh sách tên các bộ tin nhắn.",
        "💾 Lưu trữ và đọc các bộ tin nhắn từ tệp message_sets.json."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh quangcao để bật tính năng tự động gửi tin nhắn quảng cáo theo các khung giờ cố định.",
        "📩 Gửi lệnh addset <tên_bộ> | <khung_giờ1,khung_giờ2,...> | <đường_dẫn_ảnh> | <chiều_rộng> | <chiều_cao> | <nội_dung_tin_nhắn> để tạo bộ mới.",
        "📩 Gửi lệnh sendset <tên_bộ> để gửi ngay tin nhắn và ảnh của bộ được chỉ định.",
        "📋 Gửi lệnh listsets để hiển thị danh sách tên các bộ tin nhắn.",
        "📌 Ví dụ: addset set3 | 10:00,12:00 | quangcao3.jpg | 1200 | 600 | Quảng cáo sản phẩm mới\nLink: https://example.com",
        "📌 Ví dụ: sendset set3",
        "✅ Nhận thông báo trạng thái và kết quả ngay lập tức."
    ]
}

def load_message_sets():
    """Đọc message_sets từ tệp JSON, nếu không tồn tại thì trả về danh sách rỗng."""
    try:
        if os.path.exists(MESSAGE_SETS_FILE):
            with open(MESSAGE_SETS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Chuyển time_slot từ list thành set
                for ms in data:
                    ms['time_slot'] = set(ms['time_slot'])
                return data
        return []
    except Exception as e:
        print(f"Lỗi khi đọc tệp {MESSAGE_SETS_FILE}: {e}")
        return []

def save_message_sets(message_sets):
    """Ghi message_sets vào tệp JSON."""
    try:
        # Chuyển time_slot từ set thành list để lưu JSON
        data = [
            {**ms, 'time_slot': list(ms['time_slot'])}
            for ms in message_sets
        ]
        with open(MESSAGE_SETS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Lỗi khi ghi tệp {MESSAGE_SETS_FILE}: {e}")

# Khởi tạo message_sets từ tệp JSON
message_sets = load_message_sets()

# Múi giờ Việt Nam
VN_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

def get_excluded_group_ids():
    """Đọc tệp danhsachnhom.json và trả về tập hợp các group_id."""
    try:
        with open("danhsachnhom.json", "r", encoding="utf-8") as f:
            groups = json.load(f)
            return {grp.get("group_id") for grp in groups}
    except Exception as e:
        print(f"Lỗi khi đọc file danhsachnhom.json: {e}")
        return set()

def get_allowed_groups(client, excluded_group_ids):
    """Lọc danh sách nhóm không nằm trong danh sách loại trừ."""
    all_groups = client.fetchAllGroups()
    return {gid for gid in all_groups.gridVerMap.keys() if gid not in excluded_group_ids}

def send_message_to_group(client, thread_id, current_time_str, message_set, image_path=None):
    """Gửi ảnh và tin nhắn từ bộ được chỉ định đến một nhóm, ảnh ở trên, tin nhắn ở dưới."""
    # Sử dụng image_path từ tham số nếu được cung cấp, nếu không dùng từ message_set
    image_path = image_path or message_set['image_path']
    image_width = message_set['width']
    image_height = message_set['height']
    
    # Kiểm tra xem ảnh cục bộ có tồn tại không
    if not os.path.exists(image_path):
        print(f"Không tìm thấy ảnh tại {image_path} cho thread_id {thread_id}")
        return
    
    try:
        # Tạo biến message
        message = Message(text=message_set['message'])
        # Gửi ảnh và tin nhắn
        client.sendLocalImage(
            image_path,
            thread_id=thread_id,
            thread_type=ThreadType.GROUP,
            message=message,
            width=image_width,
            height=image_height,
            ttl=600000
        )
    except Exception as e:
        print(f"Lỗi khi gửi tin nhắn đến {thread_id}: {e}")

def auto_send(client, allowed_thread_ids):
    """Chạy vòng lặp tự động gửi tin nhắn theo các khung giờ định sẵn."""
    if not message_sets:
        print("Không có bộ tin nhắn nào được định nghĩa.")
        return
    last_sent_time = None
    while True:
        now = datetime.now(VN_TZ)
        current_time_str = now.strftime("%H:%M")
        for message_set in message_sets:
            if current_time_str in message_set['time_slot'] and (last_sent_time is None or now - last_sent_time >= timedelta(minutes=1)):
                try:
                    for thread_id in allowed_thread_ids:
                        send_message_to_group(client, thread_id, current_time_str, message_set)
                        time.sleep(2)  # Delay giữa các nhóm
                    last_sent_time = now
                except Exception as e:
                    print(f"Lỗi trong quá trình tự động gửi: {e}")
        time.sleep(30)

def start_auto(client):
    """Khởi chạy chức năng tự động gửi tin nhắn."""
    try:
        if not message_sets:
            print("Không có bộ tin nhắn nào được định nghĩa để gửi tự động.")
            return
        excluded_group_ids = get_excluded_group_ids()
        allowed_thread_ids = get_allowed_groups(client, excluded_group_ids)
        auto_send(client, allowed_thread_ids)
    except Exception as e:
        print(f"Lỗi khi khởi tạo tự động gửi: {e}")

def handle_autosend_start(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh bật tính năng tự động gửi tin nhắn."""
    if not message_sets:
        response_message = Message(text="Không có bộ tin nhắn nào được định nghĩa. Vui lòng thêm bộ bằng lệnh addset.")
        client.replyMessage(response_message, message_object, thread_id, thread_type)
        return
    threading.Thread(target=start_auto, args=(client,), daemon=True).start()
    response_message = Message(text="Đã bật tính năng tự động gửi quảng cáo theo thời gian đã định ✅🚀")
    client.replyMessage(response_message, message_object, thread_id, thread_type)

def handle_send_set(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh gửi ngay tin nhắn và ảnh của bộ được chỉ định: sendset <tên_bộ>"""
    try:
        parts = message.split(" ", 1)
        if len(parts) != 2:
            response_message = Message(text="Cú pháp không hợp lệ. Sử dụng: sendset <tên_bộ>")
            client.replyMessage(response_message, message_object, thread_id, thread_type)
            return
        
        set_name = parts[1].strip()
        message_set = next((ms for ms in message_sets if ms['name'] == set_name), None)
        if not message_set:
            response_message = Message(text=f"Không tìm thấy bộ tin nhắn {set_name}.")
            client.replyMessage(response_message, message_object, thread_id, thread_type)
            return
        
        # Kiểm tra ảnh trước khi gửi
        image_path = message_set['image_path']
        if not os.path.exists(image_path):
            response_message = Message(text=f"Lỗi: Không tìm thấy ảnh tại {image_path} cho bộ {set_name}.")
            client.replyMessage(response_message, message_object, thread_id, thread_type)
            return
        
        # Gửi thông báo bắt đầu
        start_message = Message(text=f"Bắt đầu gửi tin nhắn của bộ {set_name} đến tất cả nhóm... ⏳")
        client.replyMessage(start_message, message_object, thread_id, thread_type)
        
        excluded_group_ids = get_excluded_group_ids()
        allowed_thread_ids = get_allowed_groups(client, excluded_group_ids)
        current_time_str = datetime.now(VN_TZ).strftime("%H:%M")
        
        for tid in allowed_thread_ids:
            send_message_to_group(client, tid, current_time_str, message_set)
            time.sleep(2)  # Delay giữa các nhóm
        
        # Gửi thông báo hoàn thành
        response_message = Message(text=f"Đã gửi tin nhắn của bộ {set_name} đến tất cả nhóm thành công ✅🚀")
        client.replyMessage(response_message, message_object, thread_id, thread_type)
    except Exception as e:
        response_message = Message(text=f"Lỗi khi gửi tin nhắn của bộ {set_name}: {e}")
        client.replyMessage(response_message, message_object, thread_id, thread_type)

def validate_time_slot(time_str):
    """Kiểm tra định dạng khung giờ HH:MM."""
    time_pattern = re.compile(r"^\d{2}:\d{2}$")
    return bool(time_pattern.match(time_str))

def handle_add_set(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh tạo bộ mới: addset <tên_bộ> | <khung_giờ1,khung_giờ2,...> | <đường_dẫn_ảnh> | <chiều_rộng> | <chiều_cao> | <nội_dung_tin_nhắn>"""
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    try:
        # Tách lệnh thành các phần, giữ nội dung tin nhắn ở cuối
        parts = message.split("|", 5)
        if len(parts) != 6:
            response_message = Message(text="Cú pháp không hợp lệ. Sử dụng: addset tên_bộ | khung_giờ1,khung_giờ2,... | đường_dẫn_ảnh | chiều_rộng | chiều_cao | nội_dung_tin_nhắn")
            client.replyMessage(response_message, message_object, thread_id, thread_type)
            return
        
        # Lấy tên bộ từ parts[0], bỏ từ 'addset'
        set_name = parts[0].strip().split(" ", 1)
        if len(set_name) < 2:
            response_message = Message(text="Cú pháp không hợp lệ. Thiếu tên bộ sau 'addset'.")
            client.replyMessage(response_message, message_object, thread_id, thread_type)
            return
        set_name = set_name[1].strip()  # Lấy tên bộ sau từ 'addset'
        
        # Lấy các tham số còn lại
        time_slots_str = parts[1].strip()
        image_path = parts[2].strip()
        width_str = parts[3].strip()
        height_str = parts[4].strip()
        message_content = parts[5].strip()  # Nội dung tin nhắn, giữ nguyên \n
        
        # Kiểm tra tên bộ
        if any(ms['name'] == set_name for ms in message_sets):
            response_message = Message(text=f"Bộ {set_name} đã tồn tại. Vui lòng chọn tên khác.")
            client.replyMessage(response_message, message_object, thread_id, thread_type)
            return
        
        # Kiểm tra khung giờ
        time_slots = set(time_slots_str.split(","))
        if not all(validate_time_slot(ts.strip()) for ts in time_slots):
            response_message = Message(text="Khung giờ không hợp lệ. Định dạng: HH:MM, ví dụ: 10:00,12:00")
            client.replyMessage(response_message, message_object, thread_id, thread_type)
            return
        
        # Kiểm tra chiều rộng và chiều cao
        try:
            width = int(width_str)
            height = int(height_str)
            if width <= 0 or height <= 0:
                raise ValueError
        except ValueError:
            response_message = Message(text="Chiều rộng và chiều cao phải là số nguyên dương.")
            client.replyMessage(response_message, message_object, thread_id, thread_type)
            return
        
        # Xử lý ảnh: URL hoặc cục bộ
        local_image_path = image_path
        if image_path.startswith(('http://', 'https://')):
            # Tải ảnh từ URL
            local_image_path = f"downloaded_{set_name}.jpg"
            try:
                response = requests.get(image_path, stream=True)
                if response.status_code == 200:
                    with open(local_image_path, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                else:
                    response_message = Message(text=f"Không thể tải ảnh từ {image_path}. Mã trạng thái: {response.status_code}")
                    client.replyMessage(response_message, message_object, thread_id, thread_type)
                    return
            except Exception as e:
                response_message = Message(text=f"Lỗi khi tải ảnh từ {image_path}: {e}")
                client.replyMessage(response_message, message_object, thread_id, thread_type)
                return
        else:
            # Kiểm tra ảnh cục bộ
            if not os.path.exists(image_path):
                response_message = Message(text=f"Không tìm thấy ảnh tại {image_path}.")
                client.replyMessage(response_message, message_object, thread_id, thread_type)
                return
        
        # Thêm bộ mới
        new_set = {
            'name': set_name,
            'time_slot': time_slots,
            'message': message_content,
            'image_path': local_image_path,
            'width': width,
            'height': height
        }
        message_sets.append(new_set)
        save_message_sets(message_sets)
        
        response_message = Message(text=f"Đã tạo bộ {set_name} thành công và lưu vào {MESSAGE_SETS_FILE} ✅")
        client.replyMessage(response_message, message_object, thread_id, thread_type)
    except Exception as e:
        response_message = Message(text=f"Lỗi khi tạo bộ mới: {e}")
        client.replyMessage(response_message, message_object, thread_id, thread_type)

def handle_list_sets(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh hiển thị danh sách tên các bộ tin nhắn."""
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    try:
        if not message_sets:
            response_message = Message(text="Hiện tại không có bộ tin nhắn nào.")
        else:
            set_names = [ms['name'] for ms in message_sets]
            response_text = "Danh sách tên các bộ tin nhắn:\n" + "\n".join(f"- {name}" for name in set_names)
            response_message = Message(text=response_text)
        client.replyMessage(response_message, message_object, thread_id, thread_type)
    except Exception as e:
        response_message = Message(text=f"Lỗi khi hiển thị danh sách bộ: {e}")
        client.replyMessage(response_message, message_object, thread_id, thread_type)

def handle_del_set(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh xóa bộ tin nhắn: delset <tên_bộ>"""
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    try:
        parts = message.split(" ", 1)
        if len(parts) != 2:
            response_message = Message(text="Cú pháp không hợp lệ. Sử dụng: delset <tên_bộ>")
            client.replyMessage(response_message, message_object, thread_id, thread_type)
            return
        
        set_name = parts[1].strip()
        global message_sets
        message_set = next((ms for ms in message_sets if ms['name'] == set_name), None)
        if not message_set:
            response_message = Message(text=f"Không tìm thấy bộ tin nhắn {set_name}.")
            client.replyMessage(response_message, message_object, thread_id, thread_type)
            return
        
        message_sets = [ms for ms in message_sets if ms['name'] != set_name]
        save_message_sets(message_sets)
        
        response_message = Message(text=f"Đã xóa bộ tin nhắn {set_name} thành công ✅")
        client.replyMessage(response_message, message_object, thread_id, thread_type)
    except Exception as e:
        response_message = Message(text=f"Lỗi khi xóa bộ {set_name}: {e}")
        client.replyMessage(response_message, message_object, thread_id, thread_type)

def get_mitaizl():
    return {
        'quangcao': handle_autosend_start,
        'addset': handle_add_set,
        'sendset': handle_send_set,
        'listsets': handle_list_sets,
        'delset': handle_del_set
    }