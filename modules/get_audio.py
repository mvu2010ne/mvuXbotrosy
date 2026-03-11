import json
import urllib.parse
import re
from zlapi.models import Message

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Lấy URL video và gửi lại tệp âm thanh từ video.",
    'tính năng': [
        "✅ Tự động trích xuất URL video từ tin nhắn hoặc tin nhắn reply chứa video",
        "🎵 Chuyển đổi video thành tệp âm thanh (voice) để gửi đi",
        "📡 Hỗ trợ nhiều nền tảng video như YouTube, Vimeo, Facebook, TikTok, và các trang khác",
        "🚀 Gửi tệp âm thanh nhanh chóng qua mạng với phản hồi tự động",
        "❌ Thông báo lỗi chi tiết nếu không thể trích xuất URL hoặc gửi tệp âm thanh"
    ],
    'hướng dẫn sử dụng': [
        "📩 Dùng lệnh 'getvoice' kèm theo link video hoặc reply tin nhắn chứa video để lấy tệp âm thanh từ video.",
        "📌 Ví dụ: getvoice https://youtube.com/abc123 hoặc reply tin nhắn video với lệnh getvoice.",
        "✅ Nhận thông báo trạng thái và kết quả ngay lập tức."
    ]
}

def handle_getvoice_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản ứng ngay khi người dùng soạn đúng lệnh
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    # Kiểm tra nếu tin nhắn là phản hồi chứa video
    if message_object.quote:
        attach = message_object.quote.attach
        if attach:
            try:
                attach_data = json.loads(attach)
            except json.JSONDecodeError as e:
                print(f"Lỗi khi phân tích JSON: {str(e)}")
                return

            video_url = attach_data.get('hdUrl') or attach_data.get('href')
            if video_url:
                # Gửi voice từ video
                send_voice_from_video(video_url, thread_id, thread_type, client, message_object)
            else:
                send_error_message(thread_id, thread_type, client, "Không tìm thấy URL video.", message_object)
        else:
            send_error_message(thread_id, thread_type, client, "Vui lòng reply tin nhắn chứa video.", message_object)
    else:
        # Kiểm tra nếu tin nhắn là một link video trực tiếp
        video_url = extract_video_url(message)
        if video_url:
            # Gửi voice từ video
            send_voice_from_video(video_url, thread_id, thread_type, client, message_object)
        else:
            send_error_message(thread_id, thread_type, client, "Vui lòng gửi link video hợp lệ.", message_object)

def extract_video_url(message):
    """Trích xuất URL video từ tin nhắn."""
    # Biểu thức chính quy linh hoạt để nhận dạng mọi loại URL video
    video_url_pattern = r"https?://[^\s]+(?:youtube\.com|vimeo\.com|dailymotion\.com|facebook\.com|tiktok\.com|vkontakte\.ru|vimeo\.com|twitch\.tv|soundcloud\.com|...)"  # Có thể mở rộng danh sách các tên miền video ở đây.
    
    # Tìm kiếm URL trong tin nhắn
    match = re.search(video_url_pattern, message)
    if match:
        return match.group(0)
    return None

def send_voice_from_video(video_url, thread_id, thread_type, client, message_object):
    try:
        # Sử dụng URL video làm nguồn voice
        fake_file_size = 5 * 1024 * 1024  # Giả lập kích thước 5 MB
        # Gửi voice từ video
        client.sendRemoteVoice(video_url, thread_id, thread_type, fileSize=fake_file_size)
    except Exception as e:
        print(f"Lỗi khi gửi voice từ video: {str(e)}")
        send_error_message(thread_id, thread_type, client, "Không thể gửi voice từ video này.", message_object)

def send_error_message(thread_id, thread_type, client, error_message="Lỗi không xác định.", message_object=None):
    if hasattr(client, 'send'):
        # Gửi tin nhắn lỗi kèm reply nếu có
        if message_object:
            client.send(Message(text=error_message), thread_id=thread_id, thread_type=thread_type, reply_to=message_object)
        else:
            client.send(Message(text=error_message), thread_id=thread_id, thread_type=thread_type)
    else:
        print("Client không hỗ trợ gửi tin nhắn.")

def get_mitaizl():
    return {
        'getaudio': handle_getvoice_command
    }
    
    