from zlapi.models import Message, MultiMsgStyle, MessageStyle
from config import ADMIN  # Import the ADMIN set from config.py

# Description of the admin command
des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Quản lý chế độ admin cho bot",
    'tính năng': [
        "🔒 Bật chế độ admin: Chỉ người dùng có ID được phép sử dụng bot.",
        "🔓 Tắt chế độ admin: Cho phép tất cả mọi người sử dụng bot.",
        "🔔 Thông báo trạng thái chế độ admin."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh admin on để bật chế độ admin (chỉ ID trong danh sách admin).",
        "📩 Gửi lệnh admin off để tắt chế độ admin (tất cả mọi người có thể dùng).",
        "📌 Ví dụ: admin on hoặc admin off.",
        "✅ Nhận thông báo trạng thái ngay lập tức."
    ]
}

def send_message_with_style(client, text, thread_id, thread_type, color="#db342e"):
    """Send a message with styled formatting."""
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
    client.send(
        Message(text=text, style=style),
        thread_id=thread_id,
        thread_type=thread_type,
        ttl=60000
    )

def handle_admin_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản hồi emoji "✅" xác nhận đã nhận lệnh
    action = "✅ "
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    """Handle the admin command to toggle admin mode."""
    # Check if the author_id is in the ADMIN set
    if author_id not in ADMIN:
        error_message = "❌❌❌ THẤT BẠI ❌❌❌\n🚫 Chỉ QTV Cấp cao mới có quyền sử dụng lệnh này!"
        send_message_with_style(client, error_message, thread_id, thread_type)
        return

    # Parse the command
    text = message.split()
    if len(text) < 2:
        error_message = "⭕ Vui lòng chỉ định hành động: admin on/off"
        send_message_with_style(client, error_message, thread_id, thread_type)
        return

    action = text[1].lower()
    
    # Handle 'on' action
    if action == "on":
        if client.admin_mode:
            message_text = "⚠️ Chế độ admin đã được bật trước đó!"
        else:
            client.admin_mode = True
            message_text = "✅✅✅ THÀNH CÔNG ✅✅✅ \nChế độ admin đã được bật. Chỉ QTV Cấp cao có thể sử dụng bot."
        send_message_with_style(client, message_text, thread_id, thread_type)
    
    # Handle 'off' action
    elif action == "off":
        if not client.admin_mode:
            message_text = "⚠️⚠️⚠️⚠ \nChế độ admin đã được tắt trước đó!"
        else:
            client.admin_mode = False
            message_text = "🔓 Chế độ admin đã được tắt. Tất cả mọi người có thể sử dụng bot."
        send_message_with_style(client, message_text, thread_id, thread_type)
    
    # Handle invalid action
    else:
        error_message = "❌❌❌ THẤT BẠI ❌❌❌ \nHành động không hợp lệ. Sử dụng: admin on/off"
        send_message_with_style(client, error_message, thread_id, thread_type)

# Register the command
def get_mitaizl():
    return {
        'admin': handle_admin_command
    }