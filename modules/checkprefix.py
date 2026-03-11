import random
import time
from zlapi.models import Message, MultiMsgStyle, MessageStyle

COLORS = [
    "#db342e",  # Đỏ đậm
    "#15a85f",  # Xanh lá đậm
    "#f27806",  # Cam đậm
    "#f7b503"   # Vàng đậm
]

def handle_check_prefix_command(message, message_object, thread_id, thread_type, author_id, client):
    # Danh sách tất cả các prefix có thể
    prefixes = [
        "/menu", "@menu", "!menu", "#menu", "$menu", "%menu", "^menu", "&menu", "*menu",
        "-menu", "=menu", "+menu", "~menu", "`menu", "|menu", "\\menu", ":menu", ";menu",
        "?menu", ".menu", ",menu", "<menu", ">menu"
    ]
    
    # Tạo nội dung tin nhắn với các prefix
    message_text = "Kiểm tra tất cả prefix:\n" + "\n".join(prefixes)
    
    # Chọn màu ngẫu nhiên từ danh sách COLORS
    random_color = random.choice(COLORS)
    
    # Tạo style với màu ngẫu nhiên
    style = MultiMsgStyle([
        MessageStyle(
            offset=0,
            length=len(message_text),
            style="color",
            color=random_color,
            auto_format=False,
        ),
        MessageStyle(
            offset=0,
            length=len(message_text),
            style="bold",
            size=16,
            auto_format=False,
        ),
    ])
    
    # Tạo đối tượng Message
    formatted_message = Message(text=message_text, style=style)
    
    # Thêm thời gian trễ 0.5 giây
    time.sleep(0.5)
    
    # Gửi tin nhắn với TTL
    client.sendMessage(formatted_message, thread_id, thread_type, ttl=60000)

def get_mitaizl():
    return {
        'checkprefix': handle_check_prefix_command
    }