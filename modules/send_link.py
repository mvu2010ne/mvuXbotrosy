import re
import threading
import time
import json
from zlapi.models import Message, ThreadType

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Gửi tin nhắn và liên kết đến tất cả nhóm",
    'tính năng': [
        "📨 Gửi tin nhắn và liên kết đến tất cả nhóm, trừ các nhóm bị loại trừ.",
        "🔒 Kiểm tra quyền admin trước khi thực hiện lệnh.",
        "🔗 Gửi liên kết kèm hình ảnh minh họa, tiêu đề và mô tả.",
        "⏳ Gửi tin nhắn với khoảng cách thời gian cố định giữa các lần gửi.",
        "🔍 Kiểm tra định dạng URL và xử lý các lỗi liên quan."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh send.link <link>|<link ảnh nền>|<title>|<domain>|<des> để gửi tin nhắn và liên kết đến tất cả nhóm.",
        "📌 Ví dụ: send.link https://example.com|https://example.com/image.jpg|Tiêu đề|https://example.com|Mô tả để gửi liên kết với hình ảnh và mô tả.",
        "✅ Nhận thông báo trạng thái và kết quả gửi tin nhắn ngay lập tức."
    ]
}

# Danh sách admin
ADMIN_IDS = {"3299675674241805615", "1632905559702714318"}

# Regex kiểm tra URL
url_pattern = re.compile(
    r'http[s]?://(?:[a-zA-Z0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
)

def get_excluded_group_ids(filename="danhsachnhom.json"):
    """Đọc tệp JSON và trả về tập hợp các group_id cần loại trừ."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            groups = json.load(f)
            return {grp.get("group_id") for grp in groups if "group_id" in grp}
    except Exception as e:
        print(f"Lỗi khi đọc file {filename}: {e}")
        return set()

def send_link_to_group(client, link_url, thumbnail_url, title, domain_url, desc, thread_id):
    """Gửi một liên kết có hình ảnh đến một nhóm cụ thể."""
    try:
        client.sendLink(
            linkUrl=link_url,
            title=title,
            thread_id=thread_id,
            thread_type=ThreadType.GROUP,
            domainUrl=domain_url,
            desc=desc,
            thumbnailUrl=thumbnail_url,
            ttl=600000
        )
        print(f"Đã gửi link đến nhóm {thread_id}")
    except Exception as e:
        print(f"Lỗi khi gửi link đến nhóm {thread_id}: {e}")

def start_sendlink(client, link_url, thumbnail_url, title, domain_url, desc, thread_id, thread_type):
    """Gửi link đến tất cả nhóm không nằm trong danh sách loại trừ."""
    try:
        excluded_group_ids = get_excluded_group_ids()
        all_groups = client.fetchAllGroups()
        allowed_thread_ids = [gid for gid in all_groups.gridVerMap.keys() if gid not in excluded_group_ids]
        print(f"Đang gửi link đến {len(allowed_thread_ids)} nhóm (đã loại trừ các nhóm không cho phép).")

        for group_id in allowed_thread_ids:
            try:
                send_link_to_group(client, link_url, thumbnail_url, title, domain_url, desc, group_id)
                time.sleep(3)  # Độ trễ 3 giây giữa các lần gửi
            except Exception as e:
                print(f"Lỗi khi gửi link đến nhóm {group_id}: {e}")

        # Thông báo hoàn thành
        client.sendMessage(
            Message(text="✅ Hoàn thành gửi link đến tất cả nhóm!"),
            thread_id,
            thread_type,
            ttl=300000
        )
        print("Đã hoàn thành gửi link đến tất cả nhóm.")
    except Exception as e:
        client.sendMessage(
            Message(text=f"🚫 Lỗi khi gửi link: {e}"),
            thread_id,
            thread_type,
            ttl=300000
        )
        print(f"Lỗi trong quá trình gửi link: {e}")

def sendl2_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh send.link để gửi link đến tất cả nhóm."""
    print(f"[START] Xử lý command send.link từ author_id: {author_id} trong thread: {thread_id}")

    # Kiểm tra quyền admin
    if author_id not in ADMIN_IDS:
        client.sendMessage(
            Message(text="🚫 Bạn không có quyền sử dụng lệnh này!"),
            thread_id,
            thread_type,
            ttl=30000
        )
        print("Quyền hạn không đủ. Dừng command.")
        return

    # Thêm phản ứng
    try:
        client.sendReaction(message_object, "⚡", thread_id, thread_type, reactionType=75)
        print("Đã thêm phản ứng ngay khi nhận lệnh.")
    except Exception as e:
        print(f"Lỗi khi thêm phản ứng: {e}")

    # Xử lý cú pháp lệnh
    parts = message[7:].strip().split('|')
    if len(parts) < 5:
        client.sendMessage(
            Message(text="🚫 Cú pháp không chính xác! Vui lòng nhập: send.link <link>|<link ảnh nền>|<title>|<domain>|<des>"),
            thread_id,
            thread_type,
            ttl=30000
        )
        print("Cú pháp không chính xác. Dừng command.")
        return

    possible_urls = re.findall(url_pattern, parts[0])
    if not possible_urls:
        client.sendMessage(
            Message(text="🚫 Không tìm thấy URL hợp lệ! Vui lòng cung cấp một URL hợp lệ."),
            thread_id,
            thread_type,
            ttl=30000
        )
        print("Không tìm thấy URL hợp lệ. Dừng command.")
        return

    link_url = possible_urls[0].strip()
    thumbnail_url = parts[1].strip()
    title = parts[2].strip()
    domain_url = parts[3].strip()
    desc = parts[4].strip()

    print(f"Command hợp lệ: link_url = {link_url}, title = {title}")

    # Thông báo bắt đầu gửi
    client.sendMessage(
        Message(text="⏳ Đang bắt đầu gửi link đến các nhóm..."),
        thread_id,
        thread_type,
        ttl=300000
    )

    # Khởi chạy gửi link trong một thread riêng
    threading.Thread(
        target=start_sendlink,
        args=(client, link_url, thumbnail_url, title, domain_url, desc, thread_id, thread_type),
        daemon=True
    ).start()

def get_mitaizl():
    return {
        'send.link': sendl2_command
    }