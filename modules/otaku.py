from zlapi.models import Message
import requests
import os
import random

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Gửi ảnh wibu ngẫu nhiên từ danh sách link trong tệp otaku.txt.",
    'tính năng': [
        "📷 Tải và gửi ảnh ngẫu nhiên từ tệp otaku.txt.",
        "✅ Gửi phản ứng xác nhận khi nhận lệnh hợp lệ.",
        "⚡ Gửi ảnh với TTL 60 giây, tự xóa sau khi hiển thị.",
        "⚠️ Thông báo lỗi nếu tệp trống hoặc tải ảnh thất bại."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh otaku để nhận ảnh wibu ngẫu nhiên.",
        "📌 Ví dụ: otaku.",
        "✅ Nhận ảnh trong tin nhắn ngay lập tức."
    ]
}

def handle_anhgai_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản ứng ngay khi người dùng gửi lệnh (giống gai1)
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    # Đọc file text chứa các link ảnh
    txt_file = 'otaku.txt'
    if not os.path.exists(txt_file):
        print(f"File {txt_file} không tồn tại!")
        return

    with open(txt_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Loại bỏ khoảng trắng và dòng trống
    image_links = [line.strip() for line in lines if line.strip()]
    if not image_links:
        print("Không có link ảnh nào trong file otaku.txt!")
        return

    # Chọn ngẫu nhiên một link ảnh
    random_image_url = random.choice(image_links)
    print(f"Đang gửi ảnh từ URL: {random_image_url}")

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }
        image_response = requests.get(random_image_url, headers=headers)
        image_response.raise_for_status()
        image_path = 'temp_image.jpeg'
        with open(image_path, 'wb') as f:
            f.write(image_response.content)

        # Gửi ảnh đã tải xuống (giống gai1: sử dụng ttl và gửi một message rỗng)
        client.sendLocalImage(
            image_path,
            thread_id=thread_id,
            thread_type=thread_type,
            message=Message(text=""),
            ttl=60000
        )
        print("Ảnh đã được gửi thành công!")
        os.remove(image_path)
    except Exception as e:
        print(f"Đã xảy ra lỗi khi gửi ảnh: {e}")
        error_message = Message(text=f"Đã xảy ra lỗi khi gửi ảnh: {str(e)}")
        client.sendMessage(error_message, thread_id, thread_type, ttl=60000)

def get_mitaizl():
    return {
        'otaku': handle_anhgai_command
    }
