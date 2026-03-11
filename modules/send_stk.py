from zlapi.models import Message
from config import ADMIN
import time

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Gửi sticker đến nhóm",
    'tính năng': [
        "📨 Gửi sticker đến nhóm dựa trên loại sticker, ID sticker và ID danh mục.",
        "🔒 Kiểm tra quyền admin trước khi thực hiện lệnh.",
        "🔍 Xử lý lỗi và thông báo kết quả gửi sticker."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh sendstk để gửi sticker đến nhóm.",
        "📌 Ví dụ: sendstk để gửi sticker với loại, ID và danh mục đã định sẵn.",
        "✅ Nhận thông báo trạng thái và kết quả gửi sticker ngay lập tức."
    ]
}

def handle_sendstk_command(message, message_object, thread_id, thread_type, author_id, client):
    if author_id not in ADMIN:
        client.replyMessage(
            Message(text="Xin lỗi, bạn không có quyền thực hiện hành động này."),
            message_object, thread_id, thread_type
        )
        return
    
    sticker_type = 3
    sticker_id = "23339"
    category_id = "10425"
    
    try:
        response = client.sendSticker(sticker_type, sticker_id, category_id, thread_id, thread_type)
        if response:
            client.sendMessage(Message(text=""), thread_id, thread_type)
        else:
            client.sendMessage(Message(text="Không thể gửi sticker."), thread_id, thread_type)
    except Exception as e:
        print(f"Error: {e}")
        client.sendMessage(Message(text="lỗi"), thread_id, thread_type)

def get_mitaizl():
    return { 'send.stk': handle_sendstk_command }
