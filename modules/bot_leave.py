from zlapi.models import Message, ZaloAPIException, MessageStyle, MultiMsgStyle
from config import ADMIN, IMEI
import time

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Bot hỗ trợ rời khỏi nhóm Zalo theo lệnh một cách tự động.",
    'tính năng': [
        "⚠ Xử lý lệnh rời khỏi nhóm Zalo từ người dùng.",
        "🔔 Thông báo kết quả rời khỏi nhóm với thời gian sống (TTL) khác nhau.",
        "🔍 Xử lý các phản hồi từ API Zalo và hiển thị thông báo lỗi chi tiết.",
        "🔒 Chỉ quản trị viên mới có quyền sử dụng lệnh này."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh để bot rời khỏi nhóm Zalo.",
        "📌 Chỉ quản trị viên có thể sử dụng lệnh này để rời nhóm.",
        "✅ Nhận thông báo trạng thái rời khỏi nhóm ngay lập tức."
    ]
}

def send_reply_with_style(client, text, message_object, thread_id, thread_type, ttl=None, color="#db342e"):
    """ Gửi tin nhắn phản hồi với định dạng màu sắc và in đậm. """
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

def handle_leave_group_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản hồi emoji "✅" xác nhận đã nhận lệnh
    action = "✅ "
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    if author_id not in ADMIN:
        action = "❌"
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
        msg = "❌❌❌ THẤT BẠI ❌❌❌\nBạn không có quyền sử dụng lệnh này! Chỉ admin mới được phép."
        send_reply_with_style(client, msg, message_object, thread_id, thread_type, ttl=30000)
        return
    
    try:
        farewell_msg = "✅✅✅ THÀNH CÔNG ✅✅✅\nBot Mya đã nhận được lệnh rời khỏi nhóm!\n✔️ Bot đã rời khỏi nhóm thành công!"
        send_reply_with_style(client, farewell_msg, message_object, thread_id, thread_type, ttl=86400000)
        action = "🎉"
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
        time.sleep(2)
        client.leaveGroup(thread_id, imei=IMEI)
    except ZaloAPIException as e:
        action = "❌"
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
        msg = f"❌❌❌ THẤT BẠI ❌❌❌\nLỗi khi rời nhóm: {e}"
        send_reply_with_style(client, msg, message_object, thread_id, thread_type, ttl=30000)
    except Exception as e:
        action = "❌"
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
        msg = f"❌❌❌ THẤT BẠI ❌❌❌\nLỗi không xác định: {e}"
        send_reply_with_style(client, msg, message_object, thread_id, thread_type, ttl=30000)

def get_mitaizl():
    return {
        'bot.leave': handle_leave_group_command
    }