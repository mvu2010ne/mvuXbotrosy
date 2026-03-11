from zlapi import ZaloAPIException
from zlapi.models import Message, MessageStyle, MultiMsgStyle, ThreadType
import requests
import tempfile
import os
# Thông tin mô tả
des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Thay đổi avatar nhóm Zalo bằng link ảnh",
    'tính năng': [
        "🔧 Thay đổi avatar nhóm bằng cách gửi link ảnh.",
        "🔔 Thông báo lỗi nếu cú pháp sai hoặc ảnh không tải được."
    ],
    'hướng dẫn sử dụng': [
        "📌 Ví dụ: group.avatar https://example.com/image.jpg",
        "🔔 Lưu ý: Bạn phải có quyền thay đổi avatar nhóm."
    ]
}

def send_message_with_style(client, text, thread_id, thread_type, ttl=60000, color="#db342e"):
    """Gửi tin nhắn với định dạng màu sắc và in đậm."""
    base_length = len(text)
    adjusted_length = base_length + 355  # Tăng độ dài để style áp dụng đầy đủ
    style = MultiMsgStyle([
        MessageStyle(offset=0, length=adjusted_length, style="color", color=color, auto_format=False),
        MessageStyle(offset=0, length=adjusted_length, style="bold", size="8", auto_format=False)
    ])
    msg = Message(text=text, style=style)
    client.send(msg, thread_id=thread_id, thread_type=thread_type, ttl=ttl)

def handle_changeavatar_command(message, message_object, thread_id, thread_type, author_id, client):
    # Kiểm tra lệnh đầu vào
    print(f"Nhận lệnh: {message}")

    # Gửi phản ứng "✅" để xác nhận
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    # Kiểm tra xem lệnh có trong nhóm không
    if thread_type != ThreadType.GROUP:
        send_message_with_style(client, "🔴 Lệnh này chỉ có thể sử dụng trong nhóm!", thread_id, thread_type)
        return

    msg_error = "🔴 Cú pháp không hợp lệ! Vui lòng sử dụng: group.avatar <link ảnh>"

    try:
        # Tách tin nhắn và kiểm tra
        parts = message.split()
        print(f"Các phần của tin nhắn: {parts}")
        if len(parts) < 2:
            send_message_with_style(client, msg_error, thread_id, thread_type)
            return

        # Lấy và kiểm tra URL ảnh
        imageUrl = parts[1]
        print(f"URL ảnh: {imageUrl}")
        if not imageUrl.startswith("http://") and not imageUrl.startswith("https://"):
            send_message_with_style(client, "🔴 Link ảnh không hợp lệ! Vui lòng dùng link bắt đầu bằng http:// hoặc https://", thread_id, thread_type)
            return

        # Tải ảnh từ URL
        try:
            print("Đang tải ảnh từ URL...")
            response = requests.get(imageUrl, timeout=10)
            print(f"Mã trạng thái HTTP: {response.status_code}")
            if response.status_code != 200:
                send_message_with_style(client, f"🔴 Không thể tải ảnh từ {imageUrl}. Mã lỗi: {response.status_code}", thread_id, thread_type)
                return
            image_data = response.content
            print(f"Kích thước ảnh: {len(image_data)} bytes")
        except Exception as e:
            print(f"Lỗi khi tải ảnh: {str(e)}")
            send_message_with_style(client, f"🔴 Lỗi khi tải ảnh: {str(e)}", thread_id, thread_type)
            return

        # Lưu ảnh vào file tạm
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            temp_file.write(image_data)
            temp_file_path = temp_file.name
            print(f"Đã lưu ảnh vào: {temp_file_path}")

        # Thay đổi avatar nhóm
        try:
            print(f"Đang thay đổi avatar cho nhóm {thread_id} với file {temp_file_path}")
            result = client.changeGroupAvatar(filePath=temp_file_path, groupId=thread_id)
            if isinstance(result, dict) and 'error_code' in result:
                error_code = result['error_code']
                if error_code == 0:
                    send_message_with_style(client, "🟢 Avatar nhóm đã được cập nhật thành công!", thread_id, thread_type)
                else:
                    error_message = result.get('error_message', 'Unknown error')
                    send_message_with_style(client, f"🔴 Lỗi khi thay đổi avatar: {error_message} (Mã lỗi: {error_code})", thread_id, thread_type)
            else:
                send_message_with_style(client, "🟢 Avatar nhóm đã được cập nhật thành công!", thread_id, thread_type)

        except ZaloAPIException as e:
            print(f"Lỗi ZaloAPIException: {str(e)}")
            send_message_with_style(client, f"🔴 Lỗi khi thay đổi avatar: {str(e)}", thread_id, thread_type)
        finally:
            # Xóa file tạm
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                print(f"Đã xóa file tạm: {temp_file_path}")

    except Exception as e:
        print(f"Lỗi chung: {str(e)}")
        send_message_with_style(client, f"🔴 Đã xảy ra lỗi: {str(e)}", thread_id, thread_type)
# Tích hợp vào hệ thống lệnh
def get_mitaizl():
    return {
        'group.avatar': handle_changeavatar_command
    }

