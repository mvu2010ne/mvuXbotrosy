import os
import requests
from config import ADMIN
from zlapi.models import Message
import urllib.parse

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Bot hỗ trợ tạo link note text và gửi link cho người dùng.",
    'tính năng': [
        "📝 Tạo link note text từ nội dung người dùng nhập.",
        "🌐 Gửi phản hồi với link note text đã được tạo.",
        "🔍 Kiểm tra định dạng nội dung và xử lý nội dung có định dạng code.",
        "🔔 Thông báo kết quả tạo link note với thời gian sống (TTL) khác nhau.",
        "🔒 Chỉ quản trị viên mới có quyền sử dụng lệnh này."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh để bot tạo link note text từ nội dung bạn nhập.",
        "📌 Bot sẽ xử lý và gửi link note text đã được tạo.",
        "✅ Nhận thông báo trạng thái tạo link note ngay lập tức."
    ]
}


def handle_note_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản ứng ngay khi người dùng soạn đúng lệnh
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    # Lấy nội dung từ lệnh
    text = message.split()
    
    if len(text) < 2:
        # Nếu không có nội dung sau lệnh
        error_message = Message(text="Vui lòng nhập text cần cho vào link note.")
        client.sendMessage(error_message, thread_id, thread_type, ttl=30000)
        return

    # Lấy phần nội dung cần note
    content = " ".join(text[1:])
    
    # Kiểm tra nếu nội dung được format như mã
    if content.startswith("`") and content.endswith("`"):
        formatted_content = f"<pre><code>{content[1:-1]}</code></pre>"
    else:
        formatted_content = content

    try:
        # Gửi yêu cầu tạo link note
        data = {
            "status": 200,
            "content": formatted_content,
            "content_type": "application/json",
            "charset": "UTF-8",
            "secret": "mitai project",
            "expiration": "never"
        }
        
        # Gửi yêu cầu POST tới API mock
        response = requests.post("https://api.mocky.io/api/mock", json=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response Text: {response.text}")
        response_data = response.json()

        # Kiểm tra nếu có link trả về
        mock_url = response_data.get("link")
        
        if mock_url:
            response_message = f"Thành công ✅\nDưới đây là link note text của bạn:\nLink: {mock_url}"
        else:
            response_message = "Không thể tạo link note."
    
    except Exception as e:
        # Xử lý lỗi nếu có
        response_message = f"Có lỗi xảy ra: {str(e)}"

    # Gửi phản hồi
    message_to_send = Message(text=response_message)
    client.replyMessage(message_to_send, message_object, thread_id, thread_type)

def get_mitaizl():
    return {
        'note': handle_note_command
    }
