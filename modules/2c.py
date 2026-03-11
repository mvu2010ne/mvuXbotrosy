from zlapi.models import *
import os
import time
import threading
from zlapi.models import MultiMsgStyle, MessageStyle
from config import ADMIN

is_war_running = False

des = {
    'tác giả': "Đặng Quang Huy",
    'phiên bản': "1.0.2",
    'mô tả': "Gửi nội dung từ file 2.txt liên tục trong nhóm chat với cơ chế bật/tắt.",
    'tính năng': [
        "📜 Đọc và gửi từng dòng nội dung từ file 2.txt đến nhóm chat.",
        "🔄 Gửi liên tục theo chu kỳ với độ trễ 10 giây giữa các tin nhắn.",
        "🛑 Hỗ trợ bật (on) và tắt (stop) chức năng gửi nội dung.",
        "🔒 Chỉ quản trị viên (admin) được phép sử dụng lệnh.",
        "✅ Phản hồi bằng reaction và thông báo trạng thái gửi/dừng."
    ],
    'hướng dẫn sử dụng': [
        "💬 Gõ lệnh `2c on` để bắt đầu gửi nội dung từ file 2.txt.",
        "🛑 Gõ lệnh `2c stop` để dừng gửi nội dung.",
        "⚠️ Chỉ admin được phép sử dụng lệnh, file 2.txt phải tồn tại và có nội dung."
    ]
}

def stop_war(client, message_object, thread_id, thread_type):
    global is_war_running
    is_war_running = False
    client.replyMessage(Message(text="Đã dừng gửi nội dung."), message_object, thread_id, thread_type)

def handle_war_command(message, message_object, thread_id, thread_type, author_id, client):
    global is_war_running

    if author_id not in ADMIN:
        client.replyMessage(
            Message(text="Con súc vật này mày định làm gì :))?."),
            message_object, thread_id, thread_type
        )
        return

    command_parts = message.split()
    if len(command_parts) < 2:
        client.replyMessage(Message(text="Nhập 2c <on> hoặc 2c <stop> để chửi chết cụ 1 con chó"), message_object, thread_id, thread_type)
        return

    action = command_parts[1].lower()

    if action == "stop":
        if not is_war_running:
            client.replyMessage(
                Message(text="⚠️ **Gửi nội dung đã dừng lại.**"),
                message_object, thread_id, thread_type
            )
        else:
            stop_war(client, message_object, thread_id, thread_type)
        return

    if action != "on":
        client.replyMessage(Message(text="Vui lòng chỉ định lệnh 'on' hoặc 'stop'."), message_object, thread_id, thread_type)
        return

    try:
        with open("2.txt", "r", encoding="utf-8") as file:
            Ngon = file.readlines()
    except FileNotFoundError:
        client.replyMessage(
            Message(text="Không tìm thấy file 2.txt."),
            message_object,
            thread_id,
            thread_type
        )
        return

    if not Ngon:
        client.replyMessage(
            Message(text="File 2.txt không có nội dung nào để gửi."),
            message_object,
            thread_id,
            thread_type
        )
        return

    is_war_running = True

    def war_loop():
        while is_war_running:
            for noidung in Ngon:
                if not is_war_running:
                    break
                client.send(Message(text=noidung), thread_id, thread_type)
                time.sleep(10)

    war_thread = threading.Thread(target=war_loop)
    war_thread.start()
    # Thêm hành động phản hồi
    action = "✅ "
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

def get_mitaizl():
    return {
        '2c': handle_war_command
    }