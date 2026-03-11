import time
from zlapi.models import Message, MessageStyle, MultiMsgStyle
from config import ADMIN

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Bỏ chặn người dùng khỏi nhóm",
    'tính năng': [
        "📨 Bỏ chặn người dùng khỏi nhóm dựa trên UID hoặc số điện thoại.",
        "🔍 Kiểm tra và phân loại UID hoặc số điện thoại.",
        "🛠️ Thực hiện bỏ chặn người dùng khỏi nhóm.",
        "🔔 Thông báo lỗi cụ thể nếu có vấn đề xảy ra khi xử lý yêu cầu.",
        "🎨 Định dạng văn bản với màu sắc và kích thước font chữ."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh group.unbanuser <UID/số điện thoại> để bỏ chặn người dùng khỏi nhóm.",
        "📌 Ví dụ: group.unbanuser 0123456789 để bỏ chặn người dùng có số điện thoại 0123456789 khỏi nhóm.",
        "✅ Nhận thông báo trạng thái và kết quả ngay lập tức."
    ]
}

def send_message_with_style(client, text, thread_id, thread_type, ttl=None, color="#db342e"):
    """Gửi tin nhắn với định dạng màu sắc và in đậm."""
    base_length = len(text)
    adjusted_length = base_length + 355  # Tăng độ dài để đảm bảo style được áp dụng đầy đủ
    style = MultiMsgStyle([
        MessageStyle(offset=0, length=adjusted_length, style="color", color=color, auto_format=False),
        MessageStyle(offset=0, length=adjusted_length, style="bold", size="8", auto_format=False)
    ])
    msg = Message(text=text, style=style)
    if ttl is not None:
        client.sendMessage(msg, thread_id, thread_type, ttl=ttl)
    else:
        client.sendMessage(msg, thread_id, thread_type)

def handle_adduser_command(message, message_object, thread_id, thread_type, author_id, client):
    text = message.split()
    if len(text) < 2:
        send_message_with_style(
            client,
            "Vui lòng nhập UID hoặc số điện thoại người dùng cần bỏ chặn khỏi nhóm.",
            thread_id,
            thread_type
        )
        return

    content = text[1]
    if content.isdigit() and (len(content) == 10 or len(content) == 11):
        # Xử lý khi người dùng nhập số điện thoại
        phone_number = content
        try:
            user_info = client.fetchPhoneNumber(phone_number)
            if user_info and hasattr(user_info, 'uid'):
                user_id = user_info.uid
                user_name = user_info.zalo_name
                client.addUsersToGroup(user_id, thread_id)
                send_message = f"Bỏ chặn thành công {user_name} khỏi nhóm."
            else:
                send_message = "Không tìm thấy người dùng với số điện thoại này."
        except Exception as e:
            send_message = f"Lỗi khi bỏ chặn người dùng từ số điện thoại: {str(e)}"
    else:
        # Xử lý khi người dùng nhập UID
        formatted_user_id = f"{content}_0"
        try:
            client.addUsersToGroup(content, thread_id)
            time.sleep(1)
            author_info = client.fetchUserInfo(formatted_user_id)
            if isinstance(author_info, dict) and 'changed_profiles' in author_info:
                user_data = author_info['changed_profiles'].get(content, {})
                author_name = user_data.get('zaloName', 'Không rõ tên.')
                send_message = f"Đã bỏ chặn thành công {author_name} khỏi nhóm."
            else:
                send_message = "Đã bỏ chặn nhưng không lấy được thông tin."
        except Exception as e:
            send_message = f"Lỗi khi bỏ chặn người dùng từ UID: {str(e)}"

    send_message_with_style(client, send_message, thread_id, thread_type)

def get_mitaizl():
    return {
        'group.unbanuser': handle_adduser_command
    }
