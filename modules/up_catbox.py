import requests
import urllib.parse
import os
import json
from zlapi.models import Message

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "📤 Tải video từ tin nhắn reply lên Catbox.",
    'tính năng': [
        "📹 Nhận video từ tin nhắn reply và tải về máy chủ.",
        "📤 Tải video lên Catbox và trả về link tải.",
        "🗑️ Dọn dẹp file tạm sau khi xử lý.",
        "⚠️ Thông báo lỗi nếu video không hợp lệ hoặc tải lên thất bại."
    ],
    'hướng dẫn sử dụng': [
        "📩 Reply vào một video và gửi lệnh up.catbox.",
        "📌 Ví dụ: reply video rồi gửi up.catbox",
        "✅ Nhận link video trên Catbox trong tin nhắn."
    ]
}
# Hàm kiểm tra URL có phải video không
def is_valid_video_url(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        content_type = response.headers.get('Content-Type', '')
        return content_type.startswith('video/')
    except Exception:
        return False

# Hàm tải file lên Catbox
def upload_to_catbox(file_path, content_type='video/mp4'):
    try:
        with open(file_path, 'rb') as f:
            files = {'fileToUpload': (os.path.basename(file_path), f, content_type)}
            data = {'reqtype': 'fileupload'}
            response = requests.post("https://catbox.moe/user/api.php", data=data, files=files)
            if response.status_code == 200:
                return response.text.strip()
            return None
    except Exception:
        return None

# Hàm xử lý lệnh upload video
def handle_uploadvideo_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản ứng "✅" để xác nhận
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    # Kiểm tra xem có reply không
    if not message_object.quote:
        client.sendMessage(Message(text="Vui lòng reply vào một video."), 
                           thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    # Lấy dữ liệu đính kèm từ tin nhắn được reply
    attach = message_object.quote.attach
    if not attach:
        client.sendMessage(Message(text="Tin nhắn được reply không chứa tệp đính kèm."), 
                           thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    # Trích xuất URL từ attach
    media_url = None
    try:
        attach_data = json.loads(attach) if isinstance(attach, str) else attach
        media_url = attach_data.get('hdUrl') or attach_data.get('href')
        if media_url:
            media_url = urllib.parse.unquote(media_url.replace("\\/", "/"))
        else:
            client.sendMessage(Message(text="Không tìm thấy URL trong dữ liệu đính kèm."), 
                               thread_id=thread_id, thread_type=thread_type, ttl=60000)
            return
    except json.JSONDecodeError:
        client.sendMessage(Message(text="Dữ liệu đính kèm không phải định dạng JSON hợp lệ."), 
                           thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return
    except Exception as e:
        client.sendMessage(Message(text=f"Lỗi khi xử lý dữ liệu đính kèm: {e}"), 
                           thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    # Kiểm tra URL có phải video không
    if not is_valid_video_url(media_url):
        client.sendMessage(Message(text="URL không phải video hợp lệ."), 
                           thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    try:
        # Tải video
        video_response = requests.get(media_url)
        if video_response.status_code != 200:
            raise Exception(f"Không tải được video, mã lỗi: {video_response.status_code}")

        video_path = "temp_video.mp4"
        with open(video_path, "wb") as f:
            f.write(video_response.content)

        # Tải lên Catbox
        video_url = upload_to_catbox(video_path, content_type='video/mp4')
        if video_url:
            # Gửi link
            client.sendMessage(Message(text=f"{video_url}"),
                               thread_id=thread_id, thread_type=thread_type, ttl=60000)
        else:
            raise Exception("Không thể tải video lên Catbox.")

    except Exception as e:
        client.sendMessage(Message(text=f"Đã xảy ra lỗi: {e}"),
                           thread_id=thread_id, thread_type=thread_type, ttl=60000)
    finally:
        # Dọn dẹp file tạm
        if os.path.exists("temp_video.mp4"):
            os.remove("temp_video.mp4")

# Định nghĩa lệnh
def get_mitaizl():
    return {
        'up.catbox': handle_uploadvideo_command
    }