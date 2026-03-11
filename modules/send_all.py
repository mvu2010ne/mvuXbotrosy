import re
import threading
import time
import random
import json
from zlapi.models import Message, ThreadType, MessageStyle, MultiMsgStyle

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Gửi tin nhắn đến tất cả nhóm không nằm trong danh sách loại trừ",
    'tính năng': [
        "📨 Gửi tin nhắn đến tất cả nhóm, trừ các nhóm được liệt kê trong danhsachnhom.json.",
        "🔒 Kiểm tra quyền admin trước khi thực hiện lệnh.",
        "🔍 Kiểm tra định dạng URL và xử lý các lỗi liên quan.",
        "🔗 Gửi tin nhắn với màu sắc ngẫu nhiên và in đậm cho các phần không phải đường link.",
        "⏳ Gửi tin nhắn với khoảng cách thời gian cố định giữa các lần gửi."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh send.all <nội dung> để gửi tin nhắn đến tất cả nhóm không bị loại trừ.",
        "📌 Ví dụ: send.all Chào các bạn! để gửi tin nhắn 'Chào các bạn!' đến các nhóm.",
        "✅ Nhận thông báo trạng thái và kết quả gửi tin nhắn ngay lập tức."
    ]
}

# Danh sách màu
COLORS = [
    "#db342e",  # Đỏ đậm
    "#15a85f",  # Xanh lá đậm
    "#f27806",  # Cam đậm
    "#f7b503"   # Vàng đậm
]

# Danh sách admin
ADMIN_IDS = {"3299675674241805615"}

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

# Gửi tin nhắn với định dạng màu sắc ngẫu nhiên và in đậm cho các phần không phải là đường link
def send_message_with_style(client, text, thread_id, thread_type, ttl=None):
    url_pattern = r'(https?://\S+)'
    parts = re.split(url_pattern, text)
    styles = []
    current_offset = 0

    # Chọn ngẫu nhiên một màu từ danh sách COLORS
    selected_color = random.choice(COLORS)

    # Áp dụng style cho phần không phải là đường link
    for part in parts:
        part_length = len(part)
        if re.match(url_pattern, part):  # Nếu đây là đường link, không áp dụng style
            pass
        else:
            if part_length > 0:
                styles.append(MessageStyle(offset=current_offset, length=part_length, style="color", color=selected_color, auto_format=False))
                styles.append(MessageStyle(offset=current_offset, length=part_length, style="font", size="30", auto_format=False))
        current_offset += part_length

    # Gửi tin nhắn với style đã áp dụng
    if styles:
        msg = Message(text=text, style=MultiMsgStyle(styles))
    else:
        msg = Message(text=text)
    
    if ttl is not None:
        client.sendMessage(msg, thread_id, thread_type, ttl=ttl)
    else:
        client.sendMessage(msg, thread_id, thread_type)

# Gửi phản hồi tin nhắn với định dạng màu sắc ngẫu nhiên và in đậm
def send_reply_with_style(client, text, message_object, thread_id, thread_type, ttl=None):
    base_length = len(text)
    selected_color = random.choice(COLORS)
    style = MultiMsgStyle([
        MessageStyle(offset=0, length=base_length, style="color", color=selected_color, auto_format=False),
        MessageStyle(offset=0, length=base_length, style="bold", size="8", auto_format=False)
    ])
    msg = Message(text=text, style=style)

    if ttl is not None:
        client.replyMessage(msg, message_object, thread_id, thread_type, ttl=ttl)
    else:
        client.replyMessage(msg, message_object, thread_id, thread_type)

# Gửi phản hồi tin nhắn với phần prefix và content có định dạng khác nhau
def send_reply_with_custom_style(client, prefix, content, message_object, thread_id, thread_type, ttl=None):
    full_text = prefix + content
    prefix_length = len(prefix)
    selected_color = random.choice(COLORS)
    style = MultiMsgStyle([
        MessageStyle(offset=0, length=prefix_length, style="color", color=selected_color, auto_format=False),
        MessageStyle(offset=0, length=prefix_length, style="bold", size="8", auto_format=False)
    ])
    msg = Message(text=full_text, style=style)

    if ttl is not None:
        client.replyMessage(msg, message_object, thread_id, thread_type, ttl=ttl)
    else:
        client.replyMessage(msg, message_object, thread_id, thread_type)

# Hàm gửi tin nhắn tới tất cả các nhóm (trừ nhóm bị loại trừ)
def start_sendall(client, content):
    try:
        # Lấy danh sách nhóm bị loại trừ từ tệp danhsachnhom.json
        excluded_group_ids = get_excluded_group_ids()
        # Lấy danh sách nhóm được phép gửi
        allowed_thread_ids = get_allowed_groups(client, excluded_group_ids)

        for thread_id in allowed_thread_ids:
            try:
                # Gửi tin nhắn đến các nhóm
                send_message_with_style(client, content, thread_id, ThreadType.GROUP, ttl=300000)
                print(f"Đã gửi tin nhắn đến nhóm {thread_id}")
                time.sleep(0.55)  # Thêm khoảng thời gian chờ giữa các lần gửi
            except Exception as e:
                print(f"Lỗi khi gửi tin nhắn đến nhóm {thread_id}: {e}")
    except Exception as e:
        print(f"Lỗi trong quá trình gửi tin nhắn: {e}")

# Hàm xử lý lệnh gửi tin nhắn đến tất cả nhóm
def handle_sendall_command(message, message_object, thread_id, thread_type, author_id, client):
    action = "✅"  # Gửi phản ứng ngay khi người dùng soạn đúng lệnh
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    try:
        # Kiểm tra quyền admin
        if author_id not in ADMIN_IDS:
            send_reply_with_style(client, "Bạn không có quyền thực hiện lệnh này.", message_object, thread_id, thread_type, ttl=30000)
            return

        # Kiểm tra xem lệnh có bắt đầu bằng "send.all" hoặc "send.all" không
        if message.lower().startswith("send.all") or message.lower().startswith("send.all"):
            # Trích xuất nội dung sau lệnh
            if message.lower().startswith("send.all"):
                content = message[8:].strip()
            else:
                content = message[9:].strip()

            if not content:
                send_reply_with_style(client, "Vui lòng nhập nội dung để gửi!", message_object, thread_id, thread_type, ttl=30000)
                return

            # Khởi chạy gửi tin nhắn trong một luồng mới
            threading.Thread(target=start_sendall, args=(client, content), daemon=True).start()

            # Phản hồi cho người dùng biết lệnh đang được thực hiện
            prefix = "Đang gửi nội dung đến toàn bộ nhóm :\n "
            send_reply_with_custom_style(client, prefix, content, message_object, thread_id, thread_type, ttl=180000)
        else:
            print("Không phải lệnh sendall, bỏ qua.")
    except Exception as e:
        print(f"Lỗi khi xử lý lệnh sendall: {e}")

# Hàm trả về các lệnh mà bot có thể xử lý
def get_mitaizl():
    return {
        'send.all': handle_sendall_command
    }