import json
import urllib.parse
import re
from zlapi.models import Message
import whisper
from moviepy.editor import VideoFileClip
import urllib.request
import os
import tempfile
import mimetypes

des = {
    'tác giả': "Minh Vũ Shinn Cte (modified for speech-to-text with Whisper)",
    'mô tả': "Lấy URL video hoặc file âm thanh/video và chuyển âm thanh thành văn bản.",
    'tính năng': [
        "✅ Tự động nhận diện và xử lý file âm thanh hoặc video từ tin nhắn reply",
        "📝 Chuyển đổi âm thanh từ video hoặc file âm thanh thành văn bản bằng Whisper",
        "📡 Hỗ trợ URL video từ YouTube, Vimeo, Facebook, TikTok, v.v.",
        "🚀 Gửi văn bản được chuyển đổi nhanh chóng qua mạng",
        "❌ Thông báo lỗi chi tiết nếu không thể xử lý file hoặc URL"
    ],
    'hướng dẫn sử dụng': [
        "📩 Dùng lệnh 'getvoice' kèm URL video hoặc reply tin nhắn chứa file âm thanh/video.",
        "📌 Ví dụ: getvoice https://youtube.com/abc123 hoặc reply tin nhắn chứa file với lệnh getvoice.",
        "✅ Nhận văn bản được chuyển đổi và thông báo trạng thái ngay lập tức."
    ]
}

def handle_getvoice_command(message, message_object, thread_id, thread_type, author_id, client):
    print("Tiến trình: Nhận lệnh 'getvoice' từ người dùng.")
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    
    if message_object.quote:
        print("Tiến trình: Kiểm tra tin nhắn reply chứa file âm thanh hoặc video.")
        attach = message_object.quote.attach
        if attach:
            try:
                attach_data = json.loads(attach)
                print("Tiến trình: Phân tích dữ liệu JSON từ tin nhắn reply.")
            except json.JSONDecodeError as e:
                print(f"Lỗi khi phân tích JSON: {str(e)}")
                send_error_message(thread_id, thread_type, client, "Lỗi khi phân tích dữ liệu file.", message_object)
                return

            # Kiểm tra loại file (âm thanh hoặc video)
            file_url = attach_data.get('hdUrl') or attach_data.get('href')
            file_name = attach_data.get('filename', '')
            mime_type = mimetypes.guess_type(file_name)[0] or attach_data.get('mime_type', '')

            if 'audio' in mime_type:
                print(f"Tiến trình: Phát hiện file âm thanh: {file_url}")
                transcribe_audio_from_file(file_url, thread_id, thread_type, client, message_object)
            elif 'video' in mime_type or file_url:
                print(f"Tiến trình: Phát hiện file video hoặc URL: {file_url}")
                transcribe_audio_from_video(file_url, thread_id, thread_type, client, message_object)
            else:
                print("Tiến trình: Không xác định được loại file.")
                send_error_message(thread_id, thread_type, client, "File không phải âm thanh hoặc video.", message_object)
        else:
            print("Tiến trình: Tin nhắn reply không chứa file.")
            send_error_message(thread_id, thread_type, client, "Vui lòng reply tin nhắn chứa file âm thanh hoặc video.", message_object)
    else:
        print("Tiến trình: Kiểm tra tin nhắn chứa URL video trực tiếp.")
        video_url = extract_video_url(message)
        if video_url:
            print(f"Tiến trình: Tìm thấy URL video trực tiếp: {video_url}")
            transcribe_audio_from_video(video_url, thread_id, thread_type, client, message_object)
        else:
            print("Tiến trình: Không tìm thấy URL video hợp lệ trong tin nhắn.")
            send_error_message(thread_id, thread_type, client, "Vui lòng gửi link video hợp lệ.", message_object)

def extract_video_url(message):
    print("Tiến trình: Trích xuất URL video từ tin nhắn.")
    video_url_pattern = r"https?://[^\s]+(?:youtube\.com|vimeo\.com|dailymotion\.com|facebook\.com|tiktok\.com|vkontakte\.ru|vimeo\.com|twitch\.tv|soundcloud\.com|...)"
    match = re.search(video_url_pattern, message)
    if match:
        print(f"Tiến trình: URL video được trích xuất: {match.group(0)}")
        return match.group(0)
    print("Tiến trình: Không tìm thấy URL video trong tin nhắn.")
    return None

def transcribe_audio_from_file(audio_url, thread_id, thread_type, client, message_object):
    try:
        print("Tiến trình: Đã xác nhận sử dụng thư viện Whisper.")
        print("Tiến trình: Tải mô hình Whisper.")
        model = whisper.load_model("base")
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio_file:
            temp_audio_path = temp_audio_file.name
            print(f"Tiến trình: Tạo tệp âm thanh tạm thời tại: {temp_audio_path}")
            
            print(f"Tiến trình: Tải file âm thanh từ URL: {audio_url}")
            urllib.request.urlretrieve(audio_url, temp_audio_path)
            print(f"Tiến trình: Tải file âm thanh hoàn tất, lưu tại: {temp_audio_path}")

            audio_size = os.path.getsize(temp_audio_path)
            print(f"Tiến trình: Kích thước tệp âm thanh: {audio_size} bytes")
            if audio_size == 0:
                print("Tiến trình: Tệp âm thanh rỗng.")
                raise Exception("Tệp âm thanh rỗng.")

            print("Tiến trình: Chuyển đổi âm thanh thành văn bản bằng Whisper.")
            result = model.transcribe(temp_audio_path, language='vi')
            text = result["text"]
            print(f"Tiến trình: Văn bản được chuyển đổi: {text}")

            print("Tiến trình: Gửi văn bản được chuyển đổi đến người dùng.")
            if message_object:
                client.replyMessage(Message(text=f"Văn bản được chuyển đổi: {text}"), message_object, thread_id, thread_type)
            else:
                client.send(Message(text=f"Văn bản được chuyển đổi: {text}"), thread_id=thread_id, thread_type=thread_type)
            
            print(f"Tiến trình: Xóa tệp tạm thời: {temp_audio_path}")
            os.remove(temp_audio_path)
            print("Tiến trình: Hoàn tất quá trình xử lý.")

    except Exception as e:
        print(f"Lỗi khi chuyển đổi âm thanh: {str(e)}")
        send_error_message(thread_id, thread_type, client, f"Không thể chuyển đổi âm thanh: {str(e)}", message_object)

def transcribe_audio_from_video(video_url, thread_id, thread_type, client, message_object):
    try:
        print("Tiến trình: Đã xác nhận sử dụng thư viện Whisper.")
        print("Tiến trình: Tải mô hình Whisper.")
        model = whisper.load_model("base")
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio_file:
            temp_audio_path = temp_audio_file.name
            print(f"Tiến trình: Tạo tệp âm thanh tạm thời tại: {temp_audio_path}")
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video_file:
            print(f"Tiến trình: Tải video từ URL: {video_url}")
            try:
                urllib.request.urlretrieve(video_url, temp_video_file.name)
                print(f"Tiến trình: Tải video hoàn tất, lưu tại: {temp_video_file.name}")
            except urllib.error.HTTPError as e:
                print(f"Lỗi khi tải video: {str(e)}")
                raise Exception(f"Không thể tải video: {str(e)}")
            
            video = VideoFileClip(temp_video_file.name)
            if not video.audio:
                print("Tiến trình: Video không chứa âm thanh.")
                raise Exception("Video không chứa âm thanh.")
            print("Tiến trình: Trích xuất âm thanh từ video.")
            video.audio.write_audiofile(temp_audio_path)
            video.close()
            print("Tiến trình: Trích xuất âm thanh hoàn tất.")

            audio_size = os.path.getsize(temp_audio_path)
            print(f"Tiến trình: Kích thước tệp âm thanh: {audio_size} bytes")
            if audio_size == 0:
                print("Tiến trình: Tệp âm thanh rỗng.")
                raise Exception("Tệp âm thanh rỗng.")

            print("TiЛучше trình: Chuyển đổi âm thanh thành văn bản bằng Whisper.")
            result = model.transcribe(temp_audio_path, language='vi')
            text = result["text"]
            print(f"Tiến trình: Văn bản được chuyển đổi: {text}")

            print("Tiến trình: Gửi văn bản được chuyển đổi đến người dùng.")
            if message_object:
                client.replyMessage(Message(text=f"Văn bản được chuyển đổi: {text}"), message_object, thread_id, thread_type)
            else:
                client.send(Message(text=f"Văn bản được chuyển đổi: {text}"), thread_id=thread_id, thread_type=thread_type)
            
            print(f"Tiến trình: Xóa tệp tạm thời: {temp_audio_path}")
            os.remove(temp_audio_path)
            print(f"Tiến trình: Xóa tệp tạm thời: {temp_video_file.name}")
            os.remove(temp_video_file.name)
            print("Tiến trình: Hoàn tất quá trình xử lý.")

    except Exception as e:
        print(f"Lỗi khi chuyển đổi âm thanh từ video: {str(e)}")
        send_error_message(thread_id, thread_type, client, f"Không thể chuyển đổi âm thanh từ video: {str(e)}", message_object)

def send_error_message(thread_id, thread_type, client, error_message="Lỗi không xác định.", message_object=None):
    print(f"Tiến trình: Gửi thông báo lỗi: {error_message}")
    if hasattr(client, 'send'):
        if message_object:
            client.replyMessage(Message(text=error_message), message_object, thread_id, thread_type)
        else:
            client.send(Message(text=error_message), thread_id=thread_id, thread_type=thread_type)
    else:
        print("Lỗi: Client không hỗ trợ gửi tin nhắn.")

def get_mitaizl():
    print("Tiến trình: Trả về cấu hình lệnh 'getvoice'.")
    return {
        'getvoice': handle_getvoice_command
    }