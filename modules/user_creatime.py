from zlapi import ZaloAPIException
from zlapi.models import Message, MessageStyle, MultiMsgStyle
from datetime import datetime
from config import PREFIX

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🔍 Lấy thông tin tài khoản Zalo của người dùng.",
    'tính năng': [
        "📋 Thu thập thông tin như tên Zalo và ngày tham gia từ UID hoặc mention.",
        "🎨 Gửi thông tin với định dạng màu sắc và in đậm.",
        "✅ Hỗ trợ lấy thông tin của chính người gửi, UID nhập tay hoặc người được tag.",
        "⚠️ Thông báo lỗi nếu cú pháp sai hoặc không lấy được thông tin."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh user.creattime để lấy thông tin của chính bạn.",
        "📩 Gửi user.creattime <UID> hoặc user.creattime @tag để lấy thông tin của người khác.",
        "📌 Ví dụ: user.creattime hoặc user.creattime 123456789 hoặc user.creattime @username.",
        "✅ Nhận thông tin tài khoản Zalo trong tin nhắn."
    ]
}

def send_message_with_style(client, text, thread_id, thread_type, ttl=60000, color="#db342e"):
    """Gửi tin nhắn với định dạng màu sắc và in đậm."""
    base_length = len(text)
    adjusted_length = base_length + 355  
    style = MultiMsgStyle([
        MessageStyle(offset=0, length=adjusted_length, style="color", color=color, auto_format=False),
        MessageStyle(offset=0, length=adjusted_length, style="bold", size="8", auto_format=False)
    ])
    msg = Message(text=text, style=style)
    client.send(msg, thread_id=thread_id, thread_type=thread_type, ttl=ttl)

def handle_infouser_command(message, message_object, thread_id, thread_type, author_id, client):
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    msg_error = "🔴 Cú pháp đúng: Zalo [Tag người dùng]"
    try:
        if message_object.mentions:
            author_id = message_object.mentions[0]['uid']
        elif message[3:].strip().isnumeric():
            author_id = message[3:].strip()
        elif message.strip() == f"{PREFIX}user.creattime":
            author_id = author_id
        else:
            send_message_with_style(client, msg_error, thread_id, thread_type)
            return

        try:
            info = client.fetchUserInfo(author_id)
            info = info.unchanged_profiles or info.changed_profiles
            info = info[str(author_id)]
            userName = info.zaloName if info.zaloName else "Người dùng"
            createTime = info.createdTs
            if isinstance(createTime, int):
                createTime = datetime.fromtimestamp(createTime).strftime("%d/%m/%Y")
            else:
                createTime = "Không xác định"
            msg = f'📅 Người dùng "{userName}" đã tham gia Zalo từ {createTime}'
            send_message_with_style(client, msg, thread_id, thread_type)
        except ZaloAPIException:
            send_message_with_style(client, msg_error, thread_id, thread_type)
        except Exception:
            send_message_with_style(client, "Đã xảy ra lỗi", thread_id, thread_type)
    except Exception:
        send_message_with_style(client, "Đã xảy ra lỗi", thread_id, thread_type)

def get_mitaizl():
    return {
        'user.creattime': handle_infouser_command
    }
