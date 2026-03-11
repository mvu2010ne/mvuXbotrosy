from zlapi.models import Message, MultiMsgStyle, MessageStyle

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Hiển thị ID người dùng",
    'tính năng': [
        "📨 Hiển thị ID của người dùng được tag hoặc của chính người soạn lệnh.",
        "🔍 Kiểm tra xem có người dùng được tag trong tin nhắn không.",
        "🎨 Định dạng văn bản với màu sắc và kích thước font chữ.",
        "🔔 Thông báo lỗi cụ thể nếu cú pháp lệnh không chính xác hoặc giá trị không hợp lệ."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh user.uid để hiển thị ID người dùng.",
        "📌 Ví dụ: user.uid để hiển thị ID của người soạn lệnh hoặc người được tag trong tin nhắn.",
        "✅ Nhận thông báo trạng thái và kết quả ngay lập tức."
    ]
}

def handle_meid_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản ứng ngay khi nhận lệnh
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    
    # Nếu có mention, lấy UID của người được tag, ngược lại sử dụng UID của người gửi
    if message_object.mentions:
        tagged_users = message_object.mentions[0]['uid']
    else:
        tagged_users = author_id

    response_message = f"{tagged_users}"
    
    # Tạo định dạng văn bản với màu sắc và font chữ
    style = MultiMsgStyle([
        MessageStyle(offset=0, length=len(response_message), style="color", color="#db342e", auto_format=False),
        MessageStyle(offset=0, length=len(response_message), style="font", size="16", auto_format=False),
    ])
    
    message_to_send = Message(text=response_message, style=style)
    
    # Gửi tin nhắn phản hồi
    client.replyMessage(message_to_send, message_object, thread_id, thread_type)
    
    # Gửi thêm phản ứng sau khi đã gửi phản hồi
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

def get_mitaizl():
    return {
        'user.uid': handle_meid_command
    }
