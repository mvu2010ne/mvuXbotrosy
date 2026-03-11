import time
import random
import requests
import json
from zlapi.models import Message, ThreadType
from datetime import datetime, timedelta
import pytz
import threading

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Tự động gửi tin nhắn vào các khung giờ cố định",
    'tính năng': [
        "🕒 Gửi tin nhắn vào các khung giờ cố định hàng ngày.",
        "🎬 Gửi video ngẫu nhiên từ danh sách cố định.",
        "🔍 Lọc và gửi tin nhắn đến các nhóm không nằm trong danh sách loại trừ.",
        "🔄 Khởi chạy tính năng tự động trong một luồng riêng.",
        "🔔 Thông báo lỗi cụ thể nếu có vấn đề xảy ra khi xử lý yêu cầu."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh tudonggui để bật tính năng tự động gửi tin nhắn theo các khung giờ cố định.",
        "📌 Ví dụ: tudonggui để bật tính năng tự động gửi tin nhắn.",
        "✅ Nhận thông báo trạng thái và kết quả ngay lập tức."
    ]
}

# Các khung giờ gửi tin nhắn cố định
TIME_SLOTS = {"07:00"}

# Nội dung tin nhắn cố định
FIXED_MESSAGE = """"""
# Danh sách URL video cố định
FIXED_VIDEO_URLS = [
]

# Múi giờ Việt Nam
VN_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

def get_excluded_group_ids():
    """
    Đọc tệp danhsachnhom.json và trả về tập hợp các group_id.
    Giả sử tệp chứa danh sách các đối tượng với các khóa "group_id" và "group_name".
    """
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

def send_message_to_group(client, thread_id, current_time_str):
    """Gửi video ngẫu nhiên và tin nhắn cố định đến một nhóm."""
    video_url = random.choice(FIXED_VIDEO_URLS)
    message_text = f"🕒 BÂY GIỜ LÀ {current_time_str} \n{FIXED_MESSAGE}"
    message = Message(text=message_text)
    try:
        client.sendRemoteVideo(
            video_url,
            None,
            duration=10,
            message=message,
            thread_id=thread_id,
            thread_type=ThreadType.GROUP,
            width=1920,
            height=1080,
            ttl=600000
        )
    except Exception as e:
        print(f"Error sending message to {thread_id}: {e}")

def auto_send(client, allowed_thread_ids):
    """Chạy vòng lặp tự động gửi tin nhắn theo khung giờ định sẵn."""
    last_sent_time = None
    while True:
        now = datetime.now(VN_TZ)
        current_time_str = now.strftime("%H:%M")
        if current_time_str in TIME_SLOTS and (last_sent_time is None or now - last_sent_time >= timedelta(minutes=1)):
            try:
                for thread_id in allowed_thread_ids:
                    send_message_to_group(client, thread_id, current_time_str)
                    time.sleep(2)  # Delay giữa các nhóm
                last_sent_time = now
            except Exception as e:
                print(f"Error during auto send: {e}")
        time.sleep(30)

def start_auto(client):
    """Khởi chạy chức năng tự động gửi tin nhắn."""
    try:
        # Lấy danh sách group id từ file để loại trừ
        excluded_group_ids = get_excluded_group_ids()
        allowed_thread_ids = get_allowed_groups(client, excluded_group_ids)
        auto_send(client, allowed_thread_ids)
    except Exception as e:
        print(f"Error initializing auto-send: {e}")

def handle_autosend_start(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh bật tính năng tự động gửi tin nhắn."""
    threading.Thread(target=start_auto, args=(client,), daemon=True).start()
    response_message = Message(text="Đã bật tính năng tự động rải link theo thời gian đã định ✅🚀")
    client.replyMessage(response_message, message_object, thread_id, thread_type)

def get_mitaizl():
    return {
        'autosend_on': handle_autosend_start
    }
