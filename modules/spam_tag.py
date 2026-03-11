from zlapi.models import *
import os
import time
import threading
from zlapi.models import MultiMsgStyle, Mention, MessageStyle
from config import ADMIN

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Tự động réo tên người bị tag và spam tin nhắn từ file '5c.txt'.",
    'tính năng': [
        "🔍 Kiểm tra quyền hạn của người dùng trước khi thực hiện lệnh",
        "🔗 Xác định nhiều người bị tag để thực hiện spam",
        "📝 Đọc nội dung từ file '5c.txt' để gửi tin nhắn",
        "📩 Tự động gửi tin nhắn réo tên liên tục với khoảng thời gian ngắn",
        "⏰ Giới hạn thời gian chạy tối đa để tránh spam vô hạn",
        "🛑 Hỗ trợ dừng quá trình réo tên khi có lệnh từ quản trị viên"
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh spam.tag [@người cần bem] để bắt đầu réo tên.",
        "📌 Ví dụ: spam.tag @username1 @username2 để réo tên nhiều người, spam.tag stop để dừng.",
        "✅ Nhận thông báo trạng thái và kết quả ngay lập tức."
    ]
}

is_reo_running = False
MAX_RUNTIME = 300  # Thời gian chạy tối đa (giây), ví dụ: 5 phút

def send_message_with_style(client, text, thread_id, thread_type, color="#db342e"):
    """
    Gửi tin nhắn với định dạng màu sắc.
    """
    base_length = len(text)
    adjusted_length = base_length + 355
    style = MultiMsgStyle([
        MessageStyle(
            offset=0,
            length=adjusted_length,
            style="color",
            color=color,
            auto_format=False,
        ),
        MessageStyle(
            offset=0,
            length=adjusted_length,
            style="bold",
            size="8",
            auto_format=False
        )
    ])
    client.send(Message(text=text, style=style), thread_id=thread_id, thread_type=thread_type, ttl=10000)

def stop_reo(client, message_object, thread_id, thread_type):
    global is_reo_running
    is_reo_running = False
    send_message_with_style(client, "Đã dừng réo tên!", thread_id, thread_type)

def handle_reo_command(message, message_object, thread_id, thread_type, author_id, client):
    global is_reo_running

    if author_id not in ADMIN:
        send_message_with_style(client, "⭕ Chửi chết cụ 1 con chó được tag \n❌ Mày không có quyền", thread_id, thread_type)
        return

    command_parts = message.split()
    if len(command_parts) < 1 or command_parts[0].lower() != "spam.tag":
        send_message_with_style(client, "Sai cú pháp! Dùng: spam.tag [@người cần bem] hoặc spam.tag stop", thread_id, thread_type)
        return

    # Kiểm tra lệnh stop
    if len(command_parts) > 1 and command_parts[1].lower() == "stop":
        if not is_reo_running:
            send_message_with_style(client, "⚠️ Không có quá trình réo tên nào đang chạy!", thread_id, thread_type)
        else:
            stop_reo(client, message_object, thread_id, thread_type)
        return

    # Kiểm tra tag người dùng
    if not message_object.mentions:
        send_message_with_style(client, "Hãy tag ít nhất một người để réo tên!", thread_id, thread_type)
        return

    # Kiểm tra file 5c.txt trước
    try:
        with open("5c.txt", "r", encoding="utf-8") as file:
            Ngon = file.readlines()
    except FileNotFoundError:
        send_message_with_style(client, "Không tìm thấy file 5c.txt!", thread_id, thread_type)
        return

    if not Ngon:
        send_message_with_style(client, "File 5c.txt không có nội dung nào để gửi!", thread_id, thread_type)
        return

    # Lấy danh sách người được tag
    tagged_users = [mention['uid'] for mention in message_object.mentions]
    tagged_count = len(tagged_users)
    message_count = len(Ngon)

    # Thông báo chi tiết khi bắt đầu
    send_message_with_style(
        client,
        f"🚀 Bắt đầu réo tên {tagged_count} người với {message_count} tin nhắn!\n"
        f"Thời gian chạy tối đa: {MAX_RUNTIME} giây.",
        thread_id,
        thread_type
    )

    is_reo_running = True
    start_time = time.time()

    def reo_loop():
        global is_reo_running  # Khai báo global ngay đầu hàm
        while is_reo_running and (time.time() - start_time) < MAX_RUNTIME:
            for noidung in Ngon:
                if not is_reo_running or (time.time() - start_time) >= MAX_RUNTIME:
                    break
                # Gửi tin nhắn cho từng người được tag
                for user_id in tagged_users:
                    mention = Mention(user_id, length=0, offset=0)
                    client.send(
                        Message(text=f" {noidung}", mention=mention),
                        thread_id,
                        thread_type,
                        ttl=5000
                    )
                time.sleep(5)
        if is_reo_running:  # Nếu dừng do hết thời gian
            send_message_with_style(client, "⏰ Hết thời gian réo tên!", thread_id, thread_type)
            is_reo_running = False

    reo_thread = threading.Thread(target=reo_loop)
    reo_thread.start()

def get_mitaizl():
    return {
        'spam.tag': handle_reo_command
    }