from zlapi.models import Message, MessageStyle, MultiMsgStyle
from config import ADMIN
import time


def send_reply_with_style(client, text, message_object, thread_id, thread_type, ttl=None, color="#db342e"):
    """
    Gửi tin nhắn phản hồi với định dạng màu sắc và in đậm.
    """
    base_length = len(text)
    adjusted_length = base_length + 355
    style = MultiMsgStyle([
        MessageStyle(offset=0, length=adjusted_length, style="color", color=color, auto_format=False),
        MessageStyle(offset=0, length=adjusted_length, style="bold", size="8", auto_format=False)
    ])
    msg = Message(text=text, style=style)
    if ttl is not None:
        client.replyMessage(msg, message_object, thread_id, thread_type, ttl=ttl)
    else:
        client.replyMessage(msg, message_object, thread_id, thread_type)

def is_admin(author_id):
    return author_id in ADMIN

def handle_accept_friend_command(message, message_object, thread_id, thread_type, author_id, client):
    """
    Xử lý lệnh chấp nhận lời mời kết bạn từ một ID người dùng cụ thể.
    Lệnh: `accept <user_id>`
    """
    action = "✅ "
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    if not is_admin(author_id):
        action = "❌"
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
        error_message = "❌❌❌ THẤT BẠI ❌❌❌\nBạn không có quyền sử dụng lệnh này! Chỉ admin mới được phép."
        send_reply_with_style(client, error_message, message_object, thread_id, thread_type)
        return

    # Tách lệnh và tham số (ID người dùng)
    command_parts = message.strip().split()
    if len(command_parts) < 2:
        action = "❌"
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
        error_message = "❌❌❌ THẤT BẠI ❌❌❌\nVui lòng cung cấp ID người dùng! Cú pháp: bot.accept <user_id>"
        send_reply_with_style(client, error_message, message_object, thread_id, thread_type)
        return

    user_id = command_parts[1]  # Lấy ID người dùng từ tham số

    try:
        # Gọi hàm acceptFriendRequest từ Zalo API
        user = client.acceptFriendRequest(userId=user_id, language="vi")
        user_name = user.zaloName if user and hasattr(user, 'zaloName') else "Người dùng không xác định"

        success_message = (
            f"✅✅✅ THÀNH CÔNG ✅✅✅\nĐã chấp nhận lời mời kết bạn từ {user_name} ({user_id}).\n✔️ Thao tác thành công!"
        )
        send_reply_with_style(client, success_message, message_object, thread_id, thread_type)

        action = "🎉"
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    except Exception as e:
        error_message = f"❌❌❌ THẤT BẠI ❌❌❌\nLỗi khi chấp nhận lời mời kết bạn từ {user_id}: {str(e)}"
        send_reply_with_style(client, error_message, message_object, thread_id, thread_type)
        print(f"⚠️ Lỗi: {str(e)}")

        action = "❌"
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

def get_mitaizl():
    return {
        'bot.accept': handle_accept_friend_command
    }