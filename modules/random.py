import random
from zlapi.models import Message

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "random min > max",
    'tính năng': [
        "🎲 Tạo số ngẫu nhiên trong khoảng giá trị từ min đến max người dùng nhập.",
        "📨 Gửi phản hồi với số ngẫu nhiên đã tạo.",
        "🔔 Thông báo lỗi cụ thể nếu cú pháp lệnh không hợp lệ hoặc giá trị nhập không hợp lệ."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh random <min> <max> để tạo số ngẫu nhiên.",
        "📌 Ví dụ: random 1 100 để tạo số ngẫu nhiên từ 1 đến 100.",
        "✅ Nhận thông báo số ngẫu nhiên đã tạo ngay lập tức."
    ]
}

def handle_random_command(message, message_object, thread_id, thread_type, author_id, client):
    lenhcanlay = message.split()
    
    # Kiểm tra cú pháp lệnh
    if len(lenhcanlay) != 3:
        error_message = Message(text="Cú pháp không hợp lệ. Vui lòng nhập: random <min> <max>")
        client.replyMessage(error_message, message_object, thread_id, thread_type)
        return
    
    try:
        # Chuyển min và max thành kiểu số nguyên
        min_value = int(lenhcanlay[1])
        max_value = int(lenhcanlay[2])
        
        # Kiểm tra điều kiện min < max
        if min_value >= max_value:
            error_message = Message(text="Số min phải lớn hơn số max")
            client.replyMessage(error_message, message_object, thread_id, thread_type)
            return
        
        # Tạo số ngẫu nhiên trong khoảng từ min đến max
        random_number = random.randint(min_value, max_value)
        response_message = f"Số ngẫu nhiên từ {min_value} đến {max_value} là: {random_number}"
        
        # Gửi kết quả
        message_to_send = Message(text=response_message)
        client.replyMessage(message_to_send, message_object, thread_id, thread_type)
    
    except ValueError:
        error_message = Message(text="Giá trị không hợp lệ. Vui lòng nhập số.")
        client.replyMessage(error_message, message_object, thread_id, thread_type)

def get_mitaizl():
    return {
        'random': handle_random_command
    }
