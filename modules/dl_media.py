import os
import json
import random
import requests
from zlapi import ZaloAPI
from zlapi.models import Message

des = {
    'tác giả': "Xuân Bách",
    'mô tả': "Gửi ảnh hoặc video từ đường link do người dùng cung cấp.",
    'tính năng': [
        "📤 Hỗ trợ gửi ảnh (.jpg, .jpeg, .png, .gif) và video (.mp4, .mov) từ URL.",
        "⏳ Tải xuống và gửi media tự động.",
        "🔍 Kiểm tra định dạng file trước khi gửi.",
        "🖼️ Hỗ trợ gửi ảnh trực tiếp từ máy chủ.",
        "🎥 Gửi video từ link với ảnh thu nhỏ mặc định.",
        "⚡ Xử lý nhanh chóng và phản hồi ngay lập tức.",
        "❌ Thông báo lỗi cụ thể nếu đường link không hợp lệ hoặc không thể tải xuống."
    ],
    'hướng dẫn sử dụng': [
        "📩 Dùng lệnh 'media [link ảnh/video]' để gửi media từ đường link.",
        "📌 Ví dụ: media https://example.com/image.jpg để gửi ảnh.",
        "📌 Ví dụ: media https://example.com/video.mp4 để gửi video.",
        "✅ Nhận phản hồi ngay khi media được gửi thành công."
    ]
}

def download_media(link, file_extension):
    try:
        response = requests.get(link, stream=True)
        response.raise_for_status()
        file_path = f"temp_media.{file_extension}"
        with open(file_path, 'wb') as media_file:
            for chunk in response.iter_content(1024):
                media_file.write(chunk)
        return file_path
    except Exception as e:
        print(f"Lỗi khi tải media: {str(e)}")
        return None


def handle_media_command(message, message_object, thread_id, thread_type, author_id, client):
    try:

        link = message.split()[1] if len(message.split()) > 1 else None
        if not link:
            client.send(
                Message(text="Vui lòng cung cấp liên kết media (ảnh hoặc video)."),
                thread_id=thread_id,
                thread_type=thread_type
            )
            return


        if link.endswith(('.jpg', '.jpeg', '.png', '.gif')):

            file_path = download_media(link, "jpg")
            if file_path:
                client.sendLocalImage(file_path, thread_id=thread_id, thread_type=thread_type)
                os.remove(file_path)
            else:
                raise ValueError("Lỗi khi tải ảnh.")
        elif link.endswith(('.mp4', '.mov')):
            client.sendRemoteVideo(
                videoUrl=link,
                thumbnailUrl="https://i.imgur.com/tAmVhh5.mp4", 
                duration=15000, 
                thread_id=thread_id,
                thread_type=thread_type,
                message=Message(text=""),
                width=1080,
                height=1920
            )
        else:
            client.send(
                Message(text="Liên kết không hợp lệ. Chỉ hỗ trợ ảnh (.jpg, .jpeg, .png, .gif) và video (.mp4, .mov)."),
                thread_id=thread_id,
                thread_type=thread_type
            )
    except Exception as e:
        error_message = f"Lỗi xảy ra: {str(e)}"
        client.send(
            Message(text=error_message),
            thread_id=thread_id,
            thread_type=thread_type
        )

def get_mitaizl():
    return {
        'dlmedia': handle_media_command
    }