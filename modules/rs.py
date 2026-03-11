import sys
import os
import json
import random
from datetime import datetime
from zoneinfo import ZoneInfo
from config import ADMIN
from zlapi.models import Message, MultiMsgStyle, MessageStyle, ThreadType

# Danh sách màu
COLORS = [
    "#db342e",  # Đỏ đậm
    "#15a85f",  # Xanh lá đậm
    "#f27806",  # Cam đậm
    "#f7b503"   # Vàng đậm
]

RESET_INFO_FILE = "reset_info.json"
vietnam_tz = ZoneInfo("Asia/Ho_Chi_Minh")

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Khởi động lại bot và thông báo trạng thái trong nhóm.",
    'tính năng': [
        "🔄 Khởi động lại bot với lệnh đơn giản.",
        "🔒 Chỉ admin được phép sử dụng lệnh này.",
        "📝 Ghi lại ID nhóm vào file JSON trước khi khởi động lại.",
        "🔔 Gửi thông báo xác nhận trước khi reset và thông báo khởi động thành công vào nhóm.",
        "⚠️ Ghi log chi tiết để debug nếu có lỗi."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh `rs` để khởi động lại bot.",
        "📌 Ví dụ: `rs`.",
        "✅ Nhận thông báo trước khi reset và thông báo khởi động thành công trong nhóm."
    ]
}

def is_admin(author_id):
    return author_id in ADMIN

def save_reset_info(thread_id):
    reset_info = {"thread_id": thread_id}
    try:
        with open(RESET_INFO_FILE, "w", encoding="utf-8") as f:
            json.dump(reset_info, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def load_reset_info():
    if not os.path.exists(RESET_INFO_FILE):
        return None
    try:
        with open(RESET_INFO_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except Exception:
        return None

def clear_reset_info():
    if os.path.exists(RESET_INFO_FILE):
        try:
            os.remove(RESET_INFO_FILE)
        except Exception:
            pass

def send_styled_message(client, text, thread_id, thread_type, message_object=None, ttl=None):
    try:
        # Chọn ngẫu nhiên một màu từ danh sách COLORS
        selected_color = random.choice(COLORS)
        msg = Message(text=text)
        styles = MultiMsgStyle([
            MessageStyle(offset=0, length=len(text), style="color", color=selected_color, auto_format=False),
            MessageStyle(offset=0, length=len(text), style="bold", size="16", auto_format=False)
        ])
        msg.style = styles
        if message_object:
            client.replyMessage(msg, message_object, thread_id, thread_type, ttl=ttl)
        else:
            client.sendMessage(msg, thread_id, thread_type, ttl=ttl)
        return True
    except Exception:
        return False

def handle_reset_command(message, message_object, thread_id, thread_type, author_id, client):
    if not is_admin(author_id):
        msg = "🚫 Chỉ admin mới được phép khởi động lại bot!"
        send_styled_message(client, msg, thread_id, thread_type, message_object, ttl=60000)
        client.sendReaction(message_object, "❎", thread_id, thread_type, reactionType=97)
        return

    try:
        save_reset_info(thread_id)
        msg = f"🆘 Bot Shinn đã nhận lệnh khởi động lại thành công!\n🔂 Đang tải lại toàn bộ cấu hình đăng nhập..."
        style = MultiMsgStyle([
            MessageStyle(offset=0, length=len(msg), style="color", color=random.choice(COLORS), auto_format=False),
            MessageStyle(offset=0, length=len(msg), style="bold", size="16", auto_format=False)
        ])
        client.replyMessage(Message(text=msg, style=style), message_object, thread_id, thread_type, ttl=8000)
        client.sendReaction(message_object, "⭕", thread_id, thread_type, reactionType=75)

        # Gửi GIF sau tin nhắn văn bản
        GIF_FILE_PATH = "modules/cache/reset.gif"
        # Lấy kích thước thực của GIF

        client.sendLocalGif(
            GIF_FILE_PATH,
            message_object,
            thread_id,
            thread_type,
            gifName="reset.gif",
            width=384,
            height=216,
            ttl=7000  # 15 giây để hiển thị đầy đủ GIF 12 giây
        )

        python = sys.executable
        os.execl(python, python, *sys.argv)

    except Exception as e:
        msg = f"🚫 Lỗi khi khởi động lại bot: {str(e)}"
        send_styled_message(client, msg, thread_id, thread_type, message_object, ttl=60000)
        client.sendReaction(message_object, "❎", thread_id, thread_type, reactionType=97)

def get_mitaizl():
    return {
        'rs': handle_reset_command
    }