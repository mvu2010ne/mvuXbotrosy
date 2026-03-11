from zlapi import ZaloAPI
from zlapi.models import *
import time
import random
import os
import requests  # Để tải ảnh từ URL
from io import BytesIO
from deep_translator import GoogleTranslator
from urllib.parse import quote

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Tạo ảnh từ mô tả bằng API Pollinations.",
    'tính năng': [
        "🎨 Dịch mô tả sang tiếng Anh và tạo ảnh qua API Pollinations.",
        "🖼️ Gửi ảnh với thời gian tồn tại 60 giây (tự xóa).",
        "✅ Gửi phản ứng xác nhận khi nhận lệnh hợp lệ.",
        "⚠️ Thông báo lỗi nếu không nhập mô tả hoặc API gặp sự cố."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh art <mô tả> để tạo ảnh.",
        "📌 Ví dụ: art Một cánh đồng hoa dưới ánh hoàng hôn.",
        "✅ Nhận ảnh được tạo trong tin nhắn."
    ]
}

# Danh sách admin (giữ nguyên nếu cần kiểm tra quyền truy cập)
ADMIN_IDS = {"3299675674241805615", "987654321"}

# Global session cho HTTP
session = requests.Session()

# API Pollinations: https://image.pollinations.ai/prompt/{prompt}
BASE_API_URL = "https://image.pollinations.ai/prompt/"

def translate_to_english(text):
    try:
        # Dịch nội dung sang tiếng Anh
        translated_text = GoogleTranslator(source='auto', target='en').translate(text)
        return translated_text
    except Exception as e:
        print(f"Lỗi khi dịch: {e}")
        return text  # Nếu lỗi, trả về text gốc

def create_image(message, message_object, thread_id, thread_type, author_id, self):
    # Phản ứng ngay khi nhận lệnh
    action = "✅"
    self.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    # Kiểm tra xem người dùng có nhập mô tả hay không
    prompt = message.strip().replace("create_image", "").strip()
    if not prompt:
        # Nếu không có mô tả, yêu cầu người dùng nhập nội dung
        self.sendMessage(Message("❗ Bạn chưa cung cấp mô tả. Vui lòng gửi mô tả để tạo ảnh."), thread_id, thread_type, ttl=10000)
        return

    # Nếu người dùng chỉ nhập lệnh 've', yêu cầu nhập mô tả
    if prompt.lower() == 've':
        self.sendMessage(Message("❗ Bạn chưa cung cấp mô tả. Vui lòng gửi mô tả để tạo ảnh."), thread_id, thread_type, ttl=10000)
        return

    # Dịch nội dung sang tiếng Anh
    translated_prompt = translate_to_english(prompt)
    print(f"Mô tả gốc: {prompt} -> Dịch: {translated_prompt}")

    # URL encode mô tả đã dịch và xây dựng URL API
    encoded_prompt = quote(translated_prompt)
    api_url = BASE_API_URL + encoded_prompt

    try:
        # Gọi API Pollinations (trả về ảnh trực tiếp dưới dạng binary)
        response = session.get(api_url, timeout=10)
        if response.status_code == 200:
            # Lưu ảnh vào file tạm
            temp_image_path = "temp_image.jpg"
            with open(temp_image_path, 'wb') as f:
                f.write(response.content)
            
            # Gửi ảnh cho người dùng với TTL 60 giây
            self.sendLocalImage(
                imagePath=temp_image_path,
                thread_id=thread_id,
                thread_type=thread_type,
                message=Message("Đây là ảnh bạn yêu cầu!"),
                ttl=60000
            )
            os.remove(temp_image_path)
            print("Ảnh đã được gửi thành công!")
        else:
            print(f"Lỗi khi tạo ảnh (HTTP {response.status_code}): {response.text}")
            self.sendMessage(Message("❗ Không thể tạo ảnh. Vui lòng thử lại sau."), thread_id, thread_type)
    except Exception as e:
        print(f"Đã xảy ra lỗi khi gọi API Pollinations: {e}")
        self.sendMessage(Message("❗ Đã xảy ra lỗi khi tạo ảnh. Vui lòng thử lại sau."), thread_id, thread_type)

def get_mitaizl():
    return {
        'art': create_image  # Đảm bảo tên hàm chính xác
    }
