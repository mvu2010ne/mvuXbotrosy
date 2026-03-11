import time
import random
import requests
import json
from zlapi.models import Message, ThreadType
from datetime import datetime, timedelta
import pytz
import threading

# Thông tin mô tả bot
des = {
    'tác giả': "Vinh",
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
TIME_SLOTS = [
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


def send_link_to_group2(client, thread_id, current_time_str):
    """
    Gửi tin nhắn đến nhóm bằng cách gọi phương thức sendLink của client.
    Lưu ý: Phương thức sendLink phải được cung cấp bởi API của bạn.
    """
    # Các giá trị cố định cho tin nhắn
    random_link = "https://zalo.me/g/hbiugw682"
    thumbnail_url = "https://f62-zpg-r.zdn.vn/jpg/3725249952901539185/80e154a227e7acb9f5f6.jpg"
    title = "CLAN PricelessAOV"
    domain_url = "zalo.me"
    desc = "Liên hệ admin Minh Vũ Shinn Cte để vào clan"
    
    try:
        client.sendLink(
            linkUrl=random_link,
            title=title,
            thread_id=thread_id,
            thread_type=ThreadType.GROUP,
            domainUrl=domain_url,
            desc=desc,
            thumbnailUrl=thumbnail_url,
            ttl=600000
        )
    except Exception as e:
        print(f"Error sending link to {thread_id}: {e}")


def auto_send2(client, allowed_thread_ids):
    """
    Vòng lặp tự động gửi tin nhắn theo khung giờ định sẵn (sử dụng sendLink).
    """
    last_sent_time = None
    while True:
        now = datetime.now(VN_TZ)
        current_time_str = now.strftime("%H:%M")
        if current_time_str in TIME_SLOTS and (last_sent_time is None or now - last_sent_time >= timedelta(minutes=1)):
            try:
                for thread_id in allowed_thread_ids:
                    send_link_to_group2(client, thread_id, current_time_str)
                    time.sleep(2)  # Delay giữa các nhóm
                last_sent_time = now
            except Exception as e:
                print(f"Error during auto send: {e}")
        time.sleep(30)


def start_auto2(client):
    """
    Khởi chạy chức năng tự động gửi tin nhắn sử dụng sendLink.
    """
    try:
        excluded_group_ids = get_excluded_group_ids()
        allowed_thread_ids = get_allowed_groups(client, excluded_group_ids)
        auto_send2(client, allowed_thread_ids)
    except Exception as e:
        print(f"Error initializing auto-send2: {e}")


def handle_autosend_start2(message, message_object, thread_id, thread_type, author_id, client):
    """
    Xử lý lệnh bật tính năng tự động gửi tin nhắn (sử dụng sendLink).
    """
    threading.Thread(target=start_auto2, args=(client,), daemon=True).start()
    response_message = Message(text="Đã bật tính năng tự động rải link (send_link) theo thời gian đã định ✅🚀")
    client.replyMessage(response_message, message_object, thread_id, thread_type)


def get_mitaizl():
    return {'autosend_on2': handle_autosend_start2}
