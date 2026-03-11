import time
from zlapi.models import Message, ThreadType
from config import ADMIN

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Gửi spam công việc vào nhóm và riêng tư cho những người được tag",
    'tính năng': [
        "📨 Gửi spam công việc vào nhóm và riêng tư cho những người được tag.",
        "🔒 Kiểm tra quyền admin trước khi thực hiện lệnh.",
        "🔍 Tách nội dung và số lần spam từ cú pháp lệnh.",
        "🔔 Thông báo lỗi cụ thể nếu cú pháp lệnh không chính xác hoặc giá trị không hợp lệ.",
        "🛑 Giới hạn số lần gửi để tránh spam quá mức."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh spam.todouser @nguoitag <nội dung> <số lần> để gửi spam công việc vào nhóm và riêng tư cho những người được tag.",
        "📌 Ví dụ: spam.todouser @nguoitag Hoàn thành báo cáo 5 để gửi spam công việc 'Hoàn thành báo cáo' vào nhóm và riêng tư cho những người được tag 5 lần.",
        "✅ Nhận thông báo trạng thái và kết quả gửi công việc ngay lập tức."
    ]
}

def handle_spamtodo_command(message, message_object, thread_id, thread_type, author_id, client):
    if author_id not in ADMIN:
        client.replyMessage(
            Message(text="m là chó nên k đc xài!=))"), message_object, thread_id, thread_type
        )
        return

    if not message_object.mentions:
        response_message = "Xin chị Minh Vũ Shinn Cte hãy tag con chó để em bem nó."
        client.replyMessage(Message(text=response_message), message_object, thread_id, thread_type, ttl=10000)
        return

    # Lấy danh sách UID người được tag
    tagged_users = [mention['uid'] for mention in message_object.mentions]
    parts = message.split(' ', 2)
    if len(parts) < 3:
        response_message = "Vui lòng cung cấp nội dung và số lần spam công việc. Ví dụ: spam.todouser @nguoitag Nội dung công việc 5"
        client.replyMessage(Message(text=response_message), message_object, thread_id, thread_type, ttl=120000)
        return

    try:
        content_and_count = message.split(' ', 2)[2]
        content, num_repeats_str = content_and_count.rsplit(' ', 1)
        num_repeats = int(num_repeats_str)
    except ValueError:
        response_message = "Số lần phải là một số nguyên."
        client.replyMessage(Message(text=response_message), message_object, thread_id, thread_type, ttl=10000)
        return

    # Gửi todo trong nhóm
    for _ in range(num_repeats):
        client.sendToDo(
            message_object=message_object, content=content, assignees=tagged_users,  # Chỉ định những người được tag
            thread_id=thread_id, thread_type=thread_type, due_date=-1, description="BOT MITAIZL-PROJECT"
        )
        time.sleep(0.2)

    # Gửi todo riêng tư đến từng người được tag
    for tagged_user in tagged_users:
        for _ in range(num_repeats):
            client.sendToDo(
                message_object=message_object, content=content, assignees=[tagged_user],
                thread_id=tagged_user, thread_type=ThreadType.USER, due_date=-1, description="BOT MITAIZL-PROJECT"
            )
            time.sleep(2)

def get_mitaizl():
    return {
        'spam.todouser': handle_spamtodo_command
    }
