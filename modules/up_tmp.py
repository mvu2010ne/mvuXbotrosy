import requests
import urllib.parse
import os
import json
from zlapi.models import Message

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🔍 Upload bất kỳ loại tệp nào lên tmpfiles.org.",
    'tính năng': [
        "📤 Hỗ trợ upload mọi loại tệp (ảnh, video, voice, tài liệu, v.v.).",
        "🔗 Tạo liên kết tải về từ tmpfiles.org sau khi upload thành công.",
        "✅ Xử lý file từ tin nhắn trực tiếp hoặc tin nhắn trích dẫn.",
        "⚠️ Thông báo lỗi chi tiết nếu upload thất bại."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh up.tmp kèm file bất kỳ hoặc trích dẫn tin nhắn chứa file.",
        "📌 Ví dụ: up.tmp (kèm file hoặc trích dẫn).",
        "✅ Nhận liên kết tải file từ tmpfiles.org nếu thành công."
    ]
}

TMPFILES_API_URL = 'https://tmpfiles.org/api/v1/upload'

def handle_upload_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        # Xử lý file từ tin nhắn trực tiếp
        media_url = None
        if hasattr(message_object, 'content') and isinstance(message_object.content, dict):
            media_url = message_object.content.get('href', '').replace("\\/", "/")

        # Xử lý file từ tin nhắn trích dẫn
        if not media_url and getattr(message_object, 'quote', None):
            attach = getattr(message_object.quote, 'attach', None)
            if attach:
                try:
                    attach_data = json.loads(attach)
                    media_url = attach_data.get('hdUrl') or attach_data.get('href')
                except json.JSONDecodeError:
                    send_error_message("Phân tích JSON thất bại.", thread_id, thread_type, client)
                    return

        # Kiểm tra và xử lý URL file
        if media_url:
            media_url = urllib.parse.unquote(media_url)
            tmpfiles_link = upload_to_tmpfiles(media_url)
            if tmpfiles_link:
                send_success_message(f"File đã được upload: {tmpfiles_link}", thread_id, thread_type, client)
            else:
                send_error_message("Lỗi khi upload file lên tmpfiles.org.", thread_id, thread_type, client)
        else:
            send_error_message("Không tìm thấy liên kết file trong tin nhắn hoặc tin nhắn trích dẫn.", thread_id, thread_type, client)
    except Exception as e:
        print(f"Lỗi khi xử lý lệnh upload: {str(e)}")
        send_error_message("Đã xảy ra lỗi khi xử lý lệnh.", thread_id, thread_type, client)

def upload_to_tmpfiles(media_url):
    print(f"Bắt đầu tải file từ URL: {media_url}")
    try:
        # Tải file về tạm thời
        print("Gửi yêu cầu GET để tải file...")
        response = requests.get(media_url, stream=True)
        print(f"Phản hồi GET: Mã trạng thái {response.status_code}")
        response.raise_for_status()

        # Lấy tên file và loại nội dung
        filename = os.path.basename(urllib.parse.urlparse(media_url).path)
        if not filename:
            filename = "temp_file"
            print("Không tìm thấy tên file trong URL, sử dụng tên mặc định: temp_file")
        else:
            print(f"Tên file được trích xuất: {filename}")
        temp_file_path = f"temp_{filename}"
        print(f"Lưu file tạm tại: {temp_file_path}")

        # Lưu file tạm
        with open(temp_file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print(f"File tạm đã được lưu thành công tại: {temp_file_path}")

        # Upload file lên tmpfiles.org
        content_type = response.headers.get('Content-Type', 'application/octet-stream')
        print(f"Content-Type của file: {content_type}")
        print(f"Bắt đầu upload file lên {TMPFILES_API_URL}")
        with open(temp_file_path, 'rb') as f:
            files = {'file': (filename, f, content_type)}
            upload_response = requests.post(TMPFILES_API_URL, files=files)
        print(f"Phản hồi từ API tmpfiles.org: Mã trạng thái {upload_response.status_code}")

        # Xóa file tạm
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            print(f"File tạm đã được xóa: {temp_file_path}")

        if upload_response.status_code == 200:
            print(f"Upload thành công, phản hồi: {upload_response.text}")
            return upload_response.json().get('data', {}).get('url')
        else:
            print(f"Upload thất bại, mã trạng thái: {upload_response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"Lỗi khi gọi API tmpfiles.org: {str(e)}")
        return None
    except Exception as e:
        print(f"Lỗi không xác định trong quá trình upload: {str(e)}")
        return None
    finally:
        # Đảm bảo xóa file tạm nếu có lỗi
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            print(f"File tạm đã được xóa trong khối finally: {temp_file_path}")

def send_success_message(message, thread_id, thread_type, client):
    success_message = Message(text=message)
    try:
        client.send(success_message, thread_id, thread_type)
    except Exception as e:
        print(f"Lỗi khi gửi tin nhắn thành công: {str(e)}")

def send_error_message(message, thread_id, thread_type, client):
    error_message = Message(text=message)
    try:
        client.send(error_message, thread_id, thread_type)
    except Exception as e:
        print(f"Lỗi khi gửi tin nhắn lỗi: {str(e)}")

def get_mitaizl():
    return {
        'up.tmp': handle_upload_command
    }