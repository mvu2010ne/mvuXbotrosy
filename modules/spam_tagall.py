
from zlapi.models import *
import os
import time
import threading
from config import ADMIN

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Tự động tag tất cả thành viên trong nhóm và spam tin nhắn từ file '5c.txt'.",
    'tính năng': [
        "🔍 Kiểm tra quyền hạn của người dùng trước khi thực hiện lệnh",
        "🔗 Tự động tag tất cả thành viên trong nhóm",
        "📝 Đọc nội dung từ file '5c.txt' để gửi tin nhắn",
        "📩 Tự động gửi tin nhắn réo tên liên tục với khoảng thời gian ngắn",
        "⏰ Giới hạn thời gian chạy tối đa để tránh spam vô hạn",
        "🛑 Hỗ trợ dừng quá trình tag khi có lệnh từ quản trị viên"
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh spam.notisc để bắt đầu tag tất cả thành viên.",
        "📌 Ví dụ: spam.notisc để tag all, spam.notisc stop để dừng.",
        "✅ Nhận thông báo trạng thái và kết quả ngay lập tức."
    ]
}

is_notisc_running = False
MAX_RUNTIME = 300  # Thời gian chạy tối đa (giây), ví dụ: 5 phút

def stop_notisc(client, message_object, thread_id, thread_type):
    global is_notisc_running
    is_notisc_running = False
    client.send(Message(text="Đã dừng tag all!"), thread_id, thread_type)

def handle_notisc_command(message, message_object, thread_id, thread_type, author_id, client):
    global is_notisc_running

    if author_id not in ADMIN:
        client.send(Message(text="❌ Bạn không có quyền sử dụng lệnh này"), thread_id, thread_type)
        return

    command_parts = message.split()
    if len(command_parts) < 1 or command_parts[0].lower() != "spam.tagall":
        client.send(Message(text="Sai cú pháp! Dùng: spam.tagall hoặc spam.tagall stop"), thread_id, thread_type)
        return

    # Kiểm tra lệnh stop
    if len(command_parts) > 1 and command_parts[1].lower() == "stop":
        if not is_notisc_running:
            client.send(Message(text="⚠️ Không có quá trình tag all nào đang chạy!"), thread_id, thread_type)
        else:
            stop_notisc(client, message_object, thread_id, thread_type)
        return

    # Lấy danh sách thành viên trong nhóm
    try:
        group_info = client.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
        members = group_info.get('memVerList', [])
        if not members:
            client.send(Message(text="Không có thành viên nào trong nhóm để tag."), thread_id, thread_type)
            return
    except Exception as e:
        client.send(Message(text=f"Lỗi khi lấy danh sách thành viên: {str(e)}"), thread_id, thread_type)
        return

    # Kiểm tra file 5c.txt
    try:
        with open("5c.txt", "r", encoding="utf-8") as file:
            Ngon = file.readlines()
    except FileNotFoundError:
        client.send(Message(text="Không tìm thấy file 5c.txt!"), thread_id, thread_type)
        return

    if not Ngon:
        client.send(Message(text="File 5c.txt không có nội dung nào để gửi!"), thread_id, thread_type)
        return

    # Thông báo chi tiết khi bắt đầu
    total_members = len(members)
    message_count = len(Ngon)
    client.send(
        Message(text=f"🚀 Bắt đầu tag {total_members} thành viên với {message_count} tin nhắn!\n"
                     f"Thời gian chạy tối đa: {MAX_RUNTIME} giây."),
        thread_id,
        thread_type
    )

    is_notisc_running = True
    start_time = time.time()

    def notisc_loop():
        global is_notisc_running
        while is_notisc_running and (time.time() - start_time) < MAX_RUNTIME:
            # Tạo danh sách mentions cho tất cả thành viên
            text = ""
            mentions = []
            offset = 0
            for member in members:
                user_id = member.split('_')[0]
                user_name = member.split('_')[1]
                text += f"{user_name} "
                mentions.append(Mention(uid=user_id, offset=offset, length=len(user_name), auto_format=False))
                offset += len(user_name) + 1

            multi_mention = MultiMention(mentions)

            # Gửi tin nhắn với nội dung từ file 5c.txt
            for noidung in Ngon:
                if not is_notisc_running or (time.time() - start_time) >= MAX_RUNTIME:
                    break
                client.send(
                    Message(text=f"{text}{noidung}", mention=multi_mention),
                    thread_id,
                    thread_type,
                    ttl=5000
                )
                time.sleep(5)

        if is_notisc_running:  # Nếu dừng do hết thời gian
            client.send(Message(text="⏰ Hết thời gian tag all!"), thread_id, thread_type)
            is_notisc_running = False

    notisc_thread = threading.Thread(target=notisc_loop)
    notisc_thread.start()

def get_mitaizl():
    return {
        'spam.tagall': handle_notisc_command
    }
