import json
import os
import requests
import urllib.parse
from zlapi.models import Message

# Thư mục lưu ảnh
IMAGE_DIR = 'downloadimg'

# Hàm kiểm tra Content-Type của URL
def get_content_type(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        return response.headers.get('Content-Type', '')
    except Exception as e:
        print(f"Lỗi khi lấy Content-Type: {e}")
        return ''

# Hàm kiểm tra URL có phải ảnh hợp lệ không
def is_valid_image_url(url):
    content_type = get_content_type(url)
    return content_type.startswith('image/')

# Hàm xử lý lệnh lưu ảnh
def handle_save_image_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản hồi emoji "✅" xác nhận đã nhận lệnh
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    print("==> Vào lệnh handle_save_image_command")

    # Kiểm tra nếu tin nhắn có reply
    if not message_object.quote:
        client.sendMessage(
            Message(text="⭕ Vui lòng reply vào một tin nhắn chứa ảnh!"),
            thread_id, thread_type, ttl=60000
        )
        return

    # Lấy thông tin ảnh từ quote.attach
    attach = message_object.quote.attach
    print(f"Debug: Quote attach: {attach}")
    if not attach:
        client.sendMessage(
            Message(text="⭕ Tin nhắn reply không chứa ảnh hoặc nội dung hợp lệ!"),
            thread_id, thread_type, ttl=60000
        )
        return

    try:
        attach_data = json.loads(attach) if isinstance(attach, str) else attach
        print(f"Debug: Parsed attach_data: {attach_data}")
        image_url = attach_data.get('hdUrl') or attach_data.get('normalUrl') or attach_data.get('oriUrl') or attach_data.get('href')
        if not image_url:
            raise KeyError("Không tìm thấy URL ảnh trong quote.attach")
        image_url = urllib.parse.unquote(image_url.replace("\\/", "/"))
        print(f"Debug: Image URL: {image_url}")
    except json.JSONDecodeError as e:
        client.sendMessage(
            Message(text=f"⭕ Lỗi phân tích dữ liệu ảnh: {str(e)}"),
            thread_id, thread_type, ttl=60000
        )
        return
    except KeyError as e:
        client.sendMessage(
            Message(text=f"⭕ Lỗi: Không thể lấy URL ảnh từ tin nhắn reply: {str(e)}"),
            thread_id, thread_type, ttl=60000
        )
        return

    # Kiểm tra Content-Type
    content_type = get_content_type(image_url)
    print(f"Debug: Content-Type: {content_type}")
    if not is_valid_image_url(image_url):
        client.sendMessage(
            Message(text=f"⭕ URL không phải ảnh hợp lệ: Content-Type {content_type}"),
            thread_id, thread_type, ttl=60000
        )
        return

    try:
        # Tải ảnh
        print("==> Đang tải ảnh...")
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()

        # Tạo thư mục images nếu chưa tồn tại
        os.makedirs(IMAGE_DIR, exist_ok=True)

        # Tạo tên file duy nhất dựa trên thời gian hoặc ID
        file_name = f"image_{author_id}_{thread_id}_{message_object.id}.jpg"
        file_path = os.path.join(IMAGE_DIR, file_name)

        # Lưu ảnh vào thư mục images
        with open(file_path, 'wb') as f:
            f.write(response.content)
        print(f"Debug: Ảnh đã lưu tại: {file_path}")

        # Gửi thông báo thành công
        client.sendMessage(
            Message(text=f"✅ Ảnh đã được lưu vào thư mục {IMAGE_DIR} với tên {file_name}!"),
            thread_id, thread_type, ttl=60000
        )

    except requests.exceptions.RequestException as e:
        client.sendMessage(
            Message(text=f"⭕ Lỗi khi tải ảnh: {str(e)}"),
            thread_id, thread_type, ttl=60000
        )
        print(f"Debug: RequestException: {e}")
    except Exception as e:
        client.sendMessage(
            Message(text=f"⭕ Lỗi khi lưu ảnh: {str(e)}"),
            thread_id, thread_type, ttl=60000
        )
        print(f"Debug: Exception: {e}")

# Đăng ký lệnh
def get_mitaizl():
    return {
        'save': handle_save_image_command
    }