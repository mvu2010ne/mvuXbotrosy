from zlapi.models import Message
from config import ADMIN


des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Gửi tin nhắn riêng đến người dùng với số lần lặp",
    'tính năng': [
        "📨 Gửi tin nhắn riêng đến người dùng với số lần lặp cụ thể.",
        "🔒 Kiểm tra quyền admin trước khi thực hiện lệnh.",
        "🔍 Xử lý cú pháp lệnh và kiểm tra các giá trị hợp lệ.",
        "🔔 Thông báo lỗi cụ thể nếu cú pháp lệnh không chính xác hoặc giá trị không hợp lệ."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh send.user <user_id> <message> <times> để gửi tin nhắn riêng đến người dùng với số lần lặp.",
        "📌 Ví dụ: send.user 123456789 Hello 5 để gửi tin nhắn 'Hello' đến người dùng có ID 123456789 5 lần.",
        "✅ Nhận thông báo trạng thái và kết quả gửi tin nhắn ngay lập tức."
    ]
}

def is_admin(author_id):
    return author_id in ADMIN

def handle_senduser_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản ứng ngay khi người dùng soạn đúng lệnh
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    
    try:
        if not is_admin(author_id):
            msg = "• Bạn Không Có Quyền! Chỉ có admin mới có thể sử dụng được lệnh này."
            client.replyMessage(Message(text=msg), message_object, thread_id, thread_type, ttl=20000)
            return
        
        # Phân tích cú pháp lệnh
        command_parts = message.split(' ', 2)
        if len(command_parts) < 3:
            client.replyMessage(Message(text="Lệnh không hợp lệ. Vui lòng sử dụng định dạng: send.user <user_id> <message> <times>"), message_object, thread_id, thread_type)
            return
        
        target_user_id = command_parts[1]  # ID người nhận
        
        # Tách nội dung tin nhắn và số lần gửi
        msg_content, *times_part = command_parts[2].rsplit(' ', 1)
        
        try:
            times = int(times_part[0])  # Số lần gửi
            if times <= 0:
                raise ValueError("Số lần phải lớn hơn 0.")
        except (IndexError, ValueError):
            client.replyMessage(Message(text="Số lần gửi phải là một số nguyên dương."), message_object, thread_id, thread_type)
            return
        
        # Gửi tin nhắn lặp
        for _ in range(times):
            msg = Message(text=msg_content.strip())  # Gửi nội dung tin nhắn mà không đánh số
            client.send(msg, target_user_id, ttl=300000)
        
        response = f"Đã gửi tin nhắn đến người dùng {target_user_id} {times} lần: {msg_content.strip()}"
        client.replyMessage(Message(text=response), message_object, thread_id, thread_type, ttl=500000)
    
    except Exception as e:
        error_message = f"Lỗi: {str(e)}"
        client.send(Message(text=error_message), thread_id=thread_id, thread_type=thread_type)

def get_mitaizl():
    return { 'send.user': handle_senduser_command }
