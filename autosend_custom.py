import time
import random
import json
import os
from zlapi.models import Message, ThreadType
from datetime import datetime, timedelta
import pytz
import threading

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Tự động gửi tin nhắn quảng cáo sản phẩm vào các khung giờ cố định",
    'tính năng': [
        "🕒 Gửi tin nhắn vào các khung giờ cố định hàng ngày.",
        "🖼️ Gửi ảnh cố định cùng tin nhắn từ tệp cục bộ.",
        "🔍 Lọc và gửi tin nhắn đến các nhóm không nằm trong danh sách loại trừ.",
        "🔄 Khởi chạy tính năng tự động trong một luồng riêng.",
        "🔔 Thông báo lỗi cụ thể nếu có vấn đề xảy ra khi xử lý yêu cầu."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh quangcao để bật tính năng tự động gửi tin nhắn quảng cáo theo các khung giờ cố định.",
        "📌 Ví dụ: quangcao để bật tính năng tự động gửi tin nhắn.",
        "✅ Nhận thông báo trạng thái và kết quả ngay lập tức."
    ]
}

# Các khung giờ gửi tin nhắn cố định
TIME_SLOTS = {"00:26", "10:30", "12:30", "14:30", "16:30", "18:30", "20:30", "22:30"}

# Nội dung tin nhắn cố định
FIXED_MESSAGE = """box acc zalo Thuy Tram 🐰
box 1 : 550 tv https://zalo.me/g/dkewqq283
box 2 : 750 tv https://zalo.me/g/fzgtpk513
box 4 : 570 tv https://zalo.me/g/gddkle366
box 6 : 820 tv https://zalo.me/g/zfoztf820
box 7 : 750 tv https://zalo.me/g/xrzxdm881 
box 8 : 780 tv https://zalo.me/g/ofryrj572
box 10 : 880 tv https://zalo.me/g/gvaxgb527
box 13 : 570 tv https://zalo.me/g/zmoqnl500
box 14 : 670 tv https://zalo.me/g/hbvyfx787
box 15 : 940 tv https://zalo.me/g/vpmsht865
box 16 : 590 tv https://zalo.me/g/wtxlfa710
box 17 : 710 tv https://zalo.me/g/kmdnan744
box 19 : 820 tv https://zalo.me/g/eoztxc233
box 22 : 700 tv  https://zalo.me/g/nyrbwo348
box 23 : 1k tv https://zalo.me/g/jajqgq027
box 24 : 1k tv ( 130 mem chờ duyệt)
https://zalo.me/g/uajjaf639
box 25 : 930 tv https://zalo.me/g/cbyajv562
box 26 : 880 tv https://zalo.me/g/tspnlf353
box 27 : 860 tv https://zalo.me/g/oasanq204
box 28 : 940 tv https://zalo.me/g/rharew088"""

# Đường dẫn ảnh cục bộ
FIXED_IMAGE_PATH = "quangcao.jpg"

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
    """Gửi ảnh cố định từ tệp cục bộ và tin nhắn cố định đến một nhóm."""
    message_text = f"🕒 BÂY GIỜ LÀ {current_time_str} \n{FIXED_MESSAGE}"
    message = Message(text=message_text)
    
    # Kiểm tra xem ảnh cục bộ có tồn tại không
    if not os.path.exists(FIXED_IMAGE_PATH):
        print(f"Không tìm thấy ảnh tại {FIXED_IMAGE_PATH} cho thread_id {thread_id}")
        return
    
    try:
        client.sendLocalImage(
            FIXED_IMAGE_PATH,
            thread_id=thread_id,
            thread_type=ThreadType.GROUP,
            width=2566,
            height=972,
            message=message,
            ttl=600000
        )
    except Exception as e:
        print(f"Lỗi khi gửi tin nhắn đến {thread_id}: {e}")

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
                print(f"Lỗi trong quá trình tự động gửi: {e}")
        time.sleep(30)

def start_auto(client):
    """Khởi chạy chức năng tự động gửi tin nhắn."""
    try:
        # Lấy danh sách group id từ file để loại trừ
        excluded_group_ids = get_excluded_group_ids()
        allowed_thread_ids = get_allowed_groups(client, excluded_group_ids)
        auto_send(client, allowed_thread_ids)
    except Exception as e:
        print(f"Lỗi khi khởi tạo tự động gửi: {e}")

def handle_autosend_start(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh bật tính năng tự động gửi tin nhắn."""
    threading.Thread(target=start_auto, args=(client,), daemon=True).start()
    response_message = Message(text="Đã bật tính năng tự động gửi quảng cáo theo thời gian đã định ✅🚀")
    client.replyMessage(response_message, message_object, thread_id, thread_type)

def handle_send_now(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh gửi tin nhắn quảng cáo ngay lập tức."""
    try:
        excluded_group_ids = get_excluded_group_ids()
        allowed_thread_ids = get_allowed_groups(client, excluded_group_ids)
        current_time_str = datetime.now(VN_TZ).strftime("%H:%M")
        
        for tid in allowed_thread_ids:
            send_message_to_group(client, tid, current_time_str)
            time.sleep(2)  # Delay giữa các nhóm
            
        response_message = Message(text="Đã gửi tin nhắn quảng cáo ngay lập tức đến tất cả nhóm ✅🚀")
        client.replyMessage(response_message, message_object, thread_id, thread_type)
    except Exception as e:
        response_message = Message(text=f"Lỗi khi gửi tin nhắn ngay lập tức: {e}")
        client.replyMessage(response_message, message_object, thread_id, thread_type)

def get_mitaizl():
    return {
        'quangcao': handle_autosend_start,
        'sendnow': handle_send_now
    }