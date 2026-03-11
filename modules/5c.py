from zlapi.models import *
import os
import time
import threading
from zlapi.models import MultiMsgStyle, MessageStyle
from config import ADMIN

is_war_running = False

des = {
    'version': "1.0.2",
    'credits': "trBaoDzai",
    'description': "Gửi nội dung từ file 5c.txt liên tục trong nhóm."
}

def stop_war(client, message_object, thread_id, thread_type):
    global is_war_running
    is_war_running = False
    client.replyMessage(Message(text="Sao chị Minh Vũ Shinn Cte lại tha cho con chó này ạ"), message_object, thread_id, thread_type)
    # Kiểm tra nếu tin nhắn chứa từ khóa "5c"
    if "5c stop" in message.lower():
        action = "✅"  # Biểu tượng phản ứng
        try:
            # Gửi phản ứng
            client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
        except Exception as e:
            print(f"Error sending reaction: {e}")

def handle_war_command(message, message_object, thread_id, thread_type, author_id, client):
    global is_war_running
    # Kiểm tra nếu tin nhắn chứa từ khóa "5c"
    if "5c" in message.lower():
        action = "✅"  # Biểu tượng phản ứng
        try:
            # Gửi phản ứng
            client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
        except Exception as e:
            print(f"Error sending reaction: {e}")

    if author_id not in ADMIN:
        client.replyMessage(
            Message(text="Lũ Ngu Tụi Mày Xin Phép Mẹ  Minh Vũ Shinn Cte chưa ??."),
            message_object, thread_id, thread_type
        )
        return

    command_parts = message.split()
    if len(command_parts) < 2:
        client.replyMessage(Message(text="Mẹ Minh Vũ Shinn Cte hãy nhập (5c on hoặc 5c stop) để con chửi chết cụ con chó này ạ."), message_object, thread_id, thread_type)
        return

    action = command_parts[1].lower()

    if action == "stop":
        if not is_war_running:
            client.replyMessage(
                Message(text="⚠️ **Tạm Tha Lũ Đú.**"),
                message_object, thread_id, thread_type
            )
        else:
            stop_war(client, message_object, thread_id, thread_type)
        return

    if action != "on":
        client.replyMessage(Message(text="Vui lòng chỉ định lệnh 'on' hoặc 'stop'."), message_object, thread_id, thread_type)
        return

    try:
        with open("5c.txt", "r", encoding="utf-8") as file:
            Ngon = file.readlines()
    except FileNotFoundError:
        client.replyMessage(
            Message(text="Không tìm thấy file 5c.txt."),
            message_object,
            thread_id,
            thread_type
        )
        return

    if not Ngon:
        client.replyMessage(
            Message(text="File 5c.txt không có nội dung nào để gửi."),
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
                time.sleep(0.50)

    war_thread = threading.Thread(target=war_loop)
    war_thread.start()

def get_mitaizl():
    return {
        '5c': handle_war_command
    }