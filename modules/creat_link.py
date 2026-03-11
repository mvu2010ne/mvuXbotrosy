import re
from zlapi.models import Message

# Danh sách ID admin được phép sử dụng lệnh
ADMIN_IDS = {"3299675674241805615", "4659517556814668238"}  # Thay thế bằng ID admin thực tế

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Gửi liên kết đến người dùng hoặc nhóm với hình ảnh tùy chỉnh",
    'tính năng': [
        "📨 Gửi liên kết đến người dùng hoặc nhóm với tiêu đề, hình ảnh và mô tả tùy chỉnh.",
        "🔍 Kiểm tra định dạng URL và xử lý các lỗi liên quan.",
        "🔗 Gửi liên kết kèm hình ảnh minh họa, tiêu đề và mô tả.",
        "🔔 Thông báo lỗi cụ thể nếu cú pháp lệnh không chính xác."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh sendlink <link>|<link ảnh nền>|<title>|<domain>|<des> để gửi liên kết với hình ảnh tùy chỉnh.",
        "📌 Ví dụ: sendlink https://example.com|https://example.com/image.jpg|Tiêu đề|https://example.com|Mô tả để gửi liên kết với hình ảnh và mô tả.",
        "✅ Nhận thông báo trạng thái và kết quả gửi liên kết ngay lập tức."
    ]
}

url_pattern = re.compile(
    r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
)

def send_link(message, message_object, thread_id, thread_type, author_id, client):
    # Kiểm tra quyền admin
    if str(author_id) not in ADMIN_IDS:
        client.sendMessage(
            Message(text="🚫 Bạn không có quyền sử dụng lệnh này!"),
            thread_id, thread_type
        )
        return

    parts = message.split('|')
    if len(parts) < 5:
        client.sendMessage(
            Message(text="creatlink link  | link_ảnh_nền  | tiêu_đề  | tên_miền  | mô_tả"),
            thread_id, thread_type
        )
        return

    possible_urls = re.findall(url_pattern, parts[0])
    if not possible_urls:
        client.sendMessage(
            Message(text="🚫 Không tìm thấy URL hợp lệ! Vui lòng cung cấp một URL hợp lệ."),
            thread_id, thread_type
        )
        return
    
    link_url = possible_urls[0].strip()
    thumbnail_url = parts[1].strip()
    title = parts[2].strip()
    domain_url = parts[3].strip()
    desc = parts[4].strip()

    client.sendLink(
        linkUrl=link_url, 
        title=title, 
        thread_id=thread_id, 
        thread_type=thread_type, 
        domainUrl=domain_url, 
        desc=desc, 
        thumbnailUrl=thumbnail_url, 
        ttl=600000
    )

def get_mitaizl():
    return {
        'creatlink': send_link
    }
