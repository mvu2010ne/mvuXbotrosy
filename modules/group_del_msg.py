from zlapi.models import *
from zlapi import Message, ThreadType, MultiMsgStyle, MessageStyle
from config import PREFIX, ADMIN
import time
import random

# Danh sách màu
COLORS = [
    "#db342e",  # Đỏ đậm
    "#15a85f",  # Xanh lá đậm
    "#f27806",  # Cam đậm
    "#f7b503"# Vàng đậm
]

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🔍 Xóa tin nhắn gần đây trong nhóm Zalo.",
    'tính năng': [
        "🗑️ Xóa tối đa 50 tin nhắn gần nhất trong nhóm.",
        "✅ Kiểm tra quyền admin trước khi thực hiện lệnh.",
        "📊 Theo dõi và báo cáo số lượng tin nhắn xóa thành công hoặc thất bại.",
        "⚠️ Thông báo lỗi nếu không có tin nhắn hoặc cú pháp sai."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh xoa để xóa tin nhắn trong nhóm.",
        "📌 Ví dụ: xoa (không cần tham số).",
        "✅ Nhận thông báo kết quả xóa tin nhắn nếu là admin."
    ]
}

def handle_go_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản ứng ngay khi người dùng soạn đúng lệnh
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    
    if author_id not in ADMIN:
        noquyen = "Bạn không có quyền thực hiện hành động này. Vui lòng liên hệ với quản trị viên!"
        style_noquyen = MultiMsgStyle([
            MessageStyle(offset=0, length=len(noquyen), style="color", color=random.choice(COLORS), auto_format=False),
            MessageStyle(offset=0, length=len(noquyen), style="bold", size="16", auto_format=False),
        ])
        client.replyMessage(Message(text=noquyen, style=style_noquyen),
                            message_object, thread_id, thread_type, ttl=20000)
        return

    num_to_delete = 50
    try:
        group_data = client.getRecentGroup(thread_id)
        if not group_data or not hasattr(group_data, 'groupMsgs'):
            no_messages = "Hiện tại không có tin nhắn nào để xóa trong nhóm"
            style_no_messages = MultiMsgStyle([
                MessageStyle(offset=0, length=len(no_messages), style="color", color=random.choice(COLORS), auto_format=False),
                MessageStyle(offset=0, length=len(no_messages), style="bold", size="16", auto_format=False),
            ])
            client.replyMessage(Message(text=no_messages, style=style_no_messages),
                                message_object, thread_id, thread_type, ttl=10000)
            return
        
        messages_to_delete = group_data.groupMsgs
        if not messages_to_delete:
            no_messages = "Không có tin nhắn nào để xóa!"
            style_no_messages = MultiMsgStyle([
                MessageStyle(offset=0, length=len(no_messages), style="color", color=random.choice(COLORS), auto_format=False),
                MessageStyle(offset=0, length=len(no_messages), style="bold", size="16", auto_format=False),
            ])
            client.replyMessage(Message(text=no_messages, style=style_no_messages),
                                message_object, thread_id, thread_type, ttl=10000)
            return
    except Exception as e:
        error_message = f"Lỗi khi lấy tin nhắn: {str(e)}"
        style_error = MultiMsgStyle([
            MessageStyle(offset=0, length=len(error_message), style="color", color=random.choice(COLORS), auto_format=False),
            MessageStyle(offset=0, length=len(error_message), style="bold", size="16", auto_format=False),
        ])
        client.replyMessage(Message(text=error_message, style=style_error),
                            message_object, thread_id, thread_type)
        return

    if len(messages_to_delete) < num_to_delete:
        not_enough_messages = f"Chỉ có {len(messages_to_delete)} tin nhắn sẵn có để xóa."
        style_not_enough = MultiMsgStyle([
            MessageStyle(offset=0, length=len(not_enough_messages), style="color", color=random.choice(COLORS), auto_format=False),
            MessageStyle(offset=0, length=len(not_enough_messages), style="bold", size="16", auto_format=False),
        ])
        client.replyMessage(Message(text=not_enough_messages, style=style_not_enough),
                            message_object, thread_id, thread_type, ttl=10000)
        num_to_delete = len(messages_to_delete)
    
    deleted_count = 0
    failed_count = 0

    for i in range(num_to_delete):
        msg = messages_to_delete[-(i + 1)]
        print(f"Đang cố gắng xóa tin nhắn: {msg['msgId']}, UID: {msg['uidFrom']}, Nội dung: {msg['content']}, Trạng thái: {msg['status']}")
        user_id = str(msg['uidFrom']) if msg['uidFrom'] != '0' else author_id
        try:
            deleted_msg = client.deleteGroupMsg(msg['msgId'], user_id, msg['cliMsgId'], thread_id)
            if deleted_msg.status == 0:
                deleted_count += 1
            else:
                failed_count += 1
                print(f"Không thể xóa tin nhắn với ID {msg['msgId']}. Trạng thái trả về: {deleted_msg.status}")
        except Exception as e:
            failed_count += 1
            print(f"Lỗi khi xóa tin nhắn với ID {msg['msgId']}: {str(e)}")
        time.sleep(1)  # Thêm delay sau mỗi lần xóa tin nhắn

    if failed_count > 0:
        summary_message = f"Đã xóa {deleted_count} tin nhắn thành công\nKhông thể xóa {failed_count} tin nhắn do đã quá thời gian."
    else:
        summary_message = f"Đã xóa {deleted_count} tin nhắn thành công!"
    
    style_summary = MultiMsgStyle([
        MessageStyle(offset=0, length=len(summary_message), style="color", color=random.choice(COLORS), auto_format=False),
        MessageStyle(offset=0, length=len(summary_message), style="bold", size="16", auto_format=False),
    ])
    client.replyMessage(Message(text=summary_message, style=style_summary),
                        message_object, thread_id, thread_type, ttl=10000)

def get_mitaizl():
    return {
        'group.delmsg': handle_go_command
    }