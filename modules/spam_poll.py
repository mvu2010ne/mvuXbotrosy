from zlapi.models import Message
from config import PREFIX, ADMIN
import time
import threading
import os

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Quản lý cuộc khảo sát tự động",
    'tính năng': [
        "📨 Bắt đầu và dừng cuộc khảo sát tự động.",
        "🔍 Kiểm tra quyền admin trước khi thực hiện lệnh.",
        "🔄 Khởi động và quản lý cuộc khảo sát dựa trên các câu hỏi trong file caption.txt.",
        "🔔 Thông báo lỗi cụ thể nếu cú pháp lệnh không chính xác hoặc giá trị không hợp lệ."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh spam.poll <hành động> để quản lý cuộc khảo sát.",
        "📌 Ví dụ: spam.poll on @nguoitag để bắt đầu cuộc khảo sát tự động cho người được tag, warpoll off để dừng cuộc khảo sát.",
        "✅ Nhận thông báo trạng thái và kết quả ngay lập tức."
    ]
}

# Biến toàn cục dùng để kiểm soát trạng thái khảo sát
is_polling = False

def stop_polling(client, message_object, thread_id, thread_type):
    global is_polling
    is_polling = False
    client.replyMessage(
        Message(text="Đã dừng cuộc khảo sát. Để khởi động lại, vui lòng sử dụng lệnh:\n'spam.poll on <tag người dùng>'"),
        message_object,
        thread_id,
        thread_type
    )

def handle_warpoll_command(message, message_object, thread_id, thread_type, author_id, client):
    global is_polling

    # Kiểm tra quyền hạn
    if author_id not in ADMIN:
        noquyen = "Bạn không có quyền sử dụng lệnh này. Vui lòng liên hệ quản trị viên để được hỗ trợ."
        client.replyMessage(Message(text=noquyen), message_object, thread_id, thread_type)
        return

    # Kiểm tra cú pháp lệnh
    command_parts = message.split()
    if len(command_parts) < 2:
        usage = (
            "Sử dụng lệnh:\n"
            "• 'spam.poll on <tag người dùng>' để bắt đầu cuộc khảo sát,\n"
            "• 'spam.poll off' để dừng cuộc khảo sát."
        )
        client.replyMessage(Message(text=usage), message_object, thread_id, thread_type)
        return

    action = command_parts[1].lower()
    if action == "off":
        stop_polling(client, message_object, thread_id, thread_type)
        return

    if action != "on":
        usage = (
            "Lệnh không hợp lệ.\n"
            "Sử dụng: 'spam.poll on <tag người dùng>' để bắt đầu cuộc khảo sát hoặc 'spam.poll off' để dừng."
        )
        client.replyMessage(Message(text=usage), message_object, thread_id, thread_type)
        return

    # Xác định user_id từ mention hoặc quote
    user_id = None
    if message_object.mentions:
        user_id = message_object.mentions[0]['uid']
    elif message_object.quote:
        user_id = str(message_object.quote.ownerId)
    else:
        usage = "Vui lòng tag một người dùng. Ví dụ: 'warpoll on @username'."
        client.replyMessage(Message(text=usage), message_object, thread_id, thread_type)
        return

    # Lấy thông tin của người được tag để lấy tên hiển thị
    try:
        author_info = client.fetchUserInfo(user_id)
        if isinstance(author_info, dict) and 'changed_profiles' in author_info:
            user_data = author_info['changed_profiles'].get(user_id, {})
            username = user_data.get('zaloName', 'không xác định')
        else:
            username = "Người dùng không xác định"
    except Exception:
        username = "Người dùng không xác định"

    # Đọc nội dung file caption.txt chứa danh sách câu hỏi/caption cho cuộc khảo sát
    try:
        file_path = os.path.join("modules", "cache", "caption.txt")
        with open(file_path, "r", encoding="utf-8") as file:
            captions = file.readlines()
        captions = [caption.strip() for caption in captions if caption.strip()]
    except FileNotFoundError:
        client.replyMessage(
            Message(text="Không tìm thấy file caption.txt. Vui lòng kiểm tra lại cấu hình và đảm bảo file tồn tại."),
            message_object,
            thread_id,
            thread_type
        )
        return

    if not captions:
        client.replyMessage(
            Message(text="File caption.txt không có nội dung. Vui lòng thêm nội dung vào file để tạo cuộc khảo sát."),
            message_object,
            thread_id,
            thread_type
        )
        return

    # Bật chế độ khảo sát
    is_polling = True

    def poll_loop():
        index = 0
        while is_polling:
            # Tạo câu hỏi khảo sát bằng cách ghép tên người dùng và nội dung từ file
            question = f"{username} {captions[index]}"
            try:
                client.createPoll(
                    question=question,
                    options=["Cái Djt Mẹ Chúng Mày ", "hi"],
                    groupId=thread_id
                )
                # Tiếp tục vòng lặp qua danh sách captions
                index = (index + 1) % len(captions)
                time.sleep(0.1)
            except Exception as e:
                client.replyMessage(
                    Message(text=f"Lỗi khi tạo cuộc khảo sát: {str(e)}"),
                    message_object,
                    thread_id,
                    thread_type
                )
                break

    poll_thread = threading.Thread(target=poll_loop)
    poll_thread.start()

def get_mitaizl():
    return {
        'spam.poll': handle_warpoll_command
    }
