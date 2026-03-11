from zlapi import ZaloAPIException
from zlapi.models import Message, MessageStyle, MultiMsgStyle, ThreadType
import requests

# Thông tin mô tả
des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Tạo và vô hiệu hóa link nhóm Zalo",
    'tính năng': [
        "🔧 Tạo link mời mới cho nhóm bằng lệnh group.newlink.",
        "🔧 Vô hiệu hóa link mời nhóm bằng lệnh group.dislink.",
        "🔔 Thông báo lỗi nếu cú pháp sai hoặc không có quyền."
    ],
    'hướng dẫn sử dụng': [
        "📌 Ví dụ: group.newlink",
        "📌 Ví dụ: group.dislink",
        "🔔 Lưu ý: Bạn phải có quyền quản trị nhóm để sử dụng các lệnh này."
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

def handle_newlink_command(message, message_object, thread_id, thread_type, author_id, client):
    # Kiểm tra lệnh đầu vào
    print(f"Nhận lệnh: {message}")

    # Gửi phản ứng "✅" để xác nhận
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    # Kiểm tra xem lệnh có trong nhóm không
    if thread_type != ThreadType.GROUP:
        send_message_with_style(client, "🔴 Lệnh này chỉ có thể sử dụng trong nhóm!", thread_id, thread_type)
        return

    try:
        # Gọi hàm newlink để tạo link mới
        print(f"Đang tạo link mới cho nhóm {thread_id}")
        result = client.newlink(grid=thread_id)
        print(f"Full API response: {result}")  # In ra toàn bộ kết quả trả về từ API cho mục đích debug

        if result.get("success"):
            new_link = result.get("new_link")
            if new_link:
                send_message_with_style(client, f"🟢 Link nhóm mới đã được tạo: {new_link}", thread_id, thread_type)
            else:
                send_message_with_style(client, "🟢 Link nhóm đã được tạo nhưng không nhận được URL mới. Vui lòng kiểm tra trong cài đặt nhóm!", thread_id, thread_type)
        else:
            error_code = result.get("error_code")
            error_message = result.get("error_message", "Lỗi không xác định")
            if error_code == 1337:
                send_message_with_style(client, "🟢 Đã đổi link nhóm thành công! Vui lòng kiểm tra trong cài đặt nhóm để lấy link mới.", thread_id, thread_type)
            else:
                send_message_with_style(client, f"🔴 Lỗi khi tạo link: {error_message} (Mã lỗi: {error_code})", thread_id, thread_type)

    except ZaloAPIException as e:
        print(f"Lỗi ZaloAPIException: {str(e)}")
        send_message_with_style(client, f"🔴 Lỗi khi tạo link: {str(e)}", thread_id, thread_type)
    except Exception as e:
        print(f"Lỗi chung: {str(e)}")
        send_message_with_style(client, f"🔴 Đã xảy ra lỗi: {str(e)}", thread_id, thread_type)

def handle_dislink_command(message, message_object, thread_id, thread_type, author_id, client):
    # Kiểm tra lệnh đầu vào
    print(f"Nhận lệnh: {message}")

    # Gửi phản ứng "✅" để xác nhận
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    # Kiểm tra xem lệnh có trong nhóm không
    if thread_type != ThreadType.GROUP:
        send_message_with_style(client, "🔴 Lệnh này chỉ có thể sử dụng trong nhóm!", thread_id, thread_type)
        return

    try:
        # Gọi hàm dislink để vô hiệu hóa link
        print(f"Đang vô hiệu hóa link cho nhóm {thread_id}")
        result = client.dislink(grid=thread_id)
        
        if result.get("success"):
            send_message_with_style(client, "🟢 Link nhóm đã được vô hiệu hóa thành công!", thread_id, thread_type)
        else:
            error_code = result.get("error_code")
            error_message = result.get("error_message", "Lỗi không xác định")
            send_message_with_style(client, f"🔴 Lỗi khi vô hiệu hóa link: {error_message} (Mã lỗi: {error_code})", thread_id, thread_type)

    except ZaloAPIException as e:
        print(f"Lỗi ZaloAPIException: {str(e)}")
        send_message_with_style(client, f"🔴 Lỗi khi vô hiệu hóa link: {str(e)}", thread_id, thread_type)
    except Exception as e:
        print(f"Lỗi chung: {str(e)}")
        send_message_with_style(client, f"🔴 Đã xảy ra lỗi: {str(e)}", thread_id, thread_type)

# Tích hợp vào hệ thống lệnh
def get_mitaizl():
    return {
        'group.newlink': handle_newlink_command,
        'group.dislink': handle_dislink_command
    }