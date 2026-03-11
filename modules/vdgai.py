import random
from zlapi.models import Message
import requests

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🎥 Gửi video ngẫu nhiên từ danh sách trên GitHub.",
    'tính năng': [
        "📥 Tự động lấy danh sách video từ tệp JSON trên GitHub.",
        "🎲 Chọn ngẫu nhiên một video để gửi.",
        "📤 Gửi video với thông tin thumbnail và thời lượng mặc định.",
        "⚠️ Thông báo lỗi nếu không lấy được danh sách hoặc gửi video thất bại."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh vdgai để nhận một video ngẫu nhiên.",
        "📌 Ví dụ: vdgai",
        "✅ Nhận video kèm thông báo trong tin nhắn."
    ]
}

def get_video_links_from_url(url, headers):
    """Lấy danh sách link video từ URL JSON."""
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Kiểm tra lỗi HTTP
        # Giả sử file JSON chứa một danh sách các link video
        return response.json()
    except Exception as e:
        return None, str(e)

def handle_vdgai_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản ứng ngay khi người dùng soạn đúng lệnh
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    uptime_message = ""
    message_to_send = Message(text=uptime_message)
    
    # URL và headers để lấy danh sách video
    listvd = "https://raw.githubusercontent.com/nguyenductai206/list/refs/heads/main/listvideo.json"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }
    
    # Lấy danh sách video từ URL
    result = get_video_links_from_url(listvd, headers)
    if isinstance(result, tuple):
        video_links, error_msg = result
        if not video_links:
            error_message = Message(text=f"Đã xảy ra lỗi khi lấy danh sách video: {error_msg}")
            client.sendMessage(error_message, thread_id, thread_type)
            return
    else:
        video_links = result

    if not video_links:
        error_message = Message(text="Không tìm thấy link video nào từ URL.")
        client.sendMessage(error_message, thread_id, thread_type)
        return

    # Chọn ngẫu nhiên một video từ danh sách
    video_url = random.choice(video_links).strip()  # Loại bỏ ký tự thừa (newline, space...)
    thumbnail_url = '2.jpeg'
    duration = '100'

    try:
        # Gửi video
        client.sendRemoteVideo(
            video_url, 
            thumbnail_url,
            duration=duration,
            message=message_to_send,
            thread_id=thread_id,
            thread_type=thread_type,
            width=1080,
            height=1920,
            ttl=120000
        )
        
    except Exception as e:
        error_message = Message(text=f"Đã xảy ra lỗi khi gửi video: {str(e)}")
        client.sendMessage(error_message, thread_id, thread_type)

def get_mitaizl():
    return {
        'vdgai': handle_vdgai_command  # Đã thay đổi tên từ 'vdgaiv3' thành 'vdgai'
    }
