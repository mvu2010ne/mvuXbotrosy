import time
from zlapi.models import Message, ThreadType
from config import ADMIN

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Gửi spam công việc vào nhóm và riêng tư cho những người được tag.",
    'tính năng': [
        "📋 Gửi công việc (todo) đến những người được tag trong nhóm.",
        "🔢 Hỗ trợ chỉ định số lần lặp gửi công việc.",
        "🔒 Chỉ admin được phép sử dụng lệnh này.",
        "⚠️ Thông báo lỗi nếu không tag người dùng hoặc định dạng lệnh sai."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh spam.todogroup @nguoitag <nội dung> <số lần> để giao công việc.",
        "📌 Ví dụ: spam.todogroup @user Công việc cần làm 5.",
        "✅ Nhận thông báo trạng thái và công việc được gửi ngay lập tức."
    ]
}

def handle_spamtodo_command(message, message_object, thread_id, thread_type, author_id, client):
    if author_id not in ADMIN:
        client.replyMessage(
            Message(text="Mày có quyền lồn gì mà đòi xài"),
            message_object, thread_id, thread_type
        )
        return

    if not message_object.mentions:
        response_message = "Vui lòng tag người dùng để giao công việc."
        client.replyMessage(Message(text=response_message), message_object, thread_id, thread_type)
        return

    # Lấy danh sách UID người được tag
    tagged_users = [mention['uid'] for mention in message_object.mentions]

    parts = message.split(' ', 2)
    if len(parts) < 3:
        response_message = "Vui lòng cung cấp nội dung và số lần spam công việc. Ví dụ: spam.todogroup @nguoitag Nội dung công việc 5"
        client.replyMessage(Message(text=response_message), message_object, thread_id, thread_type)
        return

    try:
        content_and_count = message.split(' ', 2)[2]
        content, num_repeats_str = content_and_count.rsplit(' ', 1)
        num_repeats = int(num_repeats_str)
    except ValueError:
        response_message = "Số lần phải là một số nguyên."
        client.replyMessage(Message(text=response_message), message_object, thread_id, thread_type)
        return

    # Gửi todo trong nhóm
    for _ in range(num_repeats):
        client.sendToDo(
            message_object=message_object,
            content=content,
            assignees=tagged_users,  # Chỉ định những người được tag
            thread_id=thread_id,
            thread_type=thread_type,
            due_date=-1,
            description="BOT MITAIZL-PROJECT"
        )
        time.sleep(0.001)

def get_mitaizl():
    return {
        'spam.todogroup': handle_spamtodo_command
    }