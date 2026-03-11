import os
import requests
import json
import uuid
import time
from PIL import Image, ImageFilter  # Import nếu cần xử lý ảnh cục bộ (ở đây chủ yếu dùng API)
from zlapi.models import Message

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🖼️ Làm nét ảnh bằng API bên thứ ba.",
    'tính năng': [
        "📥 Nhận URL ảnh từ tin nhắn hoặc reply.",
        "✨ Gọi API để làm nét ảnh và lưu kết quả tạm thời.",
        "📤 Gửi ảnh đã làm nét kèm thông báo trạng thái.",
        "⚠️ Thông báo lỗi nếu ảnh không hợp lệ hoặc API thất bại."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh up <URL ảnh> hoặc reply vào ảnh và gửi up.",
        "📌 Ví dụ: up https://example.com/image.jpg hoặc reply ảnh rồi gửi up",
        "✅ Nhận ảnh đã làm nét trong tin nhắn."
    ]
}

# Thư mục cache lưu ảnh tạm
CACHE_DIR = 'modules/cache'
os.makedirs(CACHE_DIR, exist_ok=True)

def lam_net_anh(image_url):
    """
    Tải ảnh từ URL thông qua API làm nét và lưu vào cache.
    Trả về đường dẫn file ảnh đã được xử lý hoặc None nếu có lỗi.
    """
    print(f"[INFO] Nhận yêu cầu làm nét ảnh từ link: {image_url}")
    # Xây dựng URL API với tham số link
    api_url = f"https://api.sumiproject.net/lamnet?link={image_url}"
    try:
        response = requests.get(api_url)
        if response.status_code == 200:
            # Lưu ảnh trả về từ API vào cache
            image_path = os.path.join(CACHE_DIR, f"sharpened_{uuid.uuid4().hex}.png")
            with open(image_path, "wb") as f:
                f.write(response.content)
            print(f"[INFO] Ảnh đã được làm nét và lưu vào: {image_path}")
            return image_path
        else:
            print(f"[ERROR] Lỗi khi gọi API, mã HTTP: {response.status_code}")
            return None
    except Exception as e:
        print(f"[ERROR] Lỗi khi gọi API: {e}")
        return None

def handle_lam_net_command(message, message_object, thread_id, thread_type, author_id, client):
    """
    Xử lý lệnh làm nét ảnh từ người dùng.
    - Nếu tin nhắn là reply chứa dữ liệu ảnh, lấy URL ảnh từ trường 'attach' trong dữ liệu JSON.
    - Ngược lại, lấy URL ảnh từ nội dung tin nhắn.
    Sau đó gọi API làm nét và gửi ảnh đã xử lý về cho người dùng.
    """
    image_url = None
    # Kiểm tra tin nhắn reply có chứa dữ liệu ảnh hay không
    if hasattr(message_object, 'quote') and message_object.quote:
        print("[INFO] Nhận dạng tin nhắn reply chứa ảnh.")
        attach = getattr(message_object.quote, 'attach', None)
        if attach:
            try:
                attach_data = json.loads(attach)
                # Lấy URL từ khóa 'hdUrl' hoặc 'href'
                image_url = attach_data.get('hdUrl') or attach_data.get('href')
                if not image_url:
                    client.replyMessage(
                        Message(text="❌ Không tìm thấy link ảnh trong dữ liệu trích dẫn."),
                        message_object, thread_id, thread_type, ttl=60000
                    )
                    return
            except Exception as e:
                print(f"[ERROR] Lỗi khi phân tích JSON: {e}")
                client.replyMessage(
                    Message(text="❌ Lỗi khi đọc dữ liệu ảnh."),
                    message_object, thread_id, thread_type, ttl=60000
                )
                return
        else:
            client.replyMessage(
                Message(text="❌ Không có ảnh trong tin nhắn reply."),
                message_object, thread_id, thread_type, ttl=60000
            )
            return
    else:
        # Nếu không phải reply, lấy URL ảnh từ nội dung tin nhắn (phần sau lệnh)
        content = message.strip().split()
        if len(content) < 2:
            client.replyMessage(
                Message(text="❌ Vui lòng nhập link ảnh hoặc reply vào ảnh."),
                message_object, thread_id, thread_type, ttl=60000
            )
            return
        image_url = content[1]

    # Thông báo cho người dùng biết quá trình đang xử lý
    client.replyMessage(
        Message(text="✨ Đang làm nét ảnh..."),
        message_object, thread_id, thread_type, ttl=60000
    )
    
    # Gọi hàm làm nét ảnh qua API
    image_path = lam_net_anh(image_url)
    
    if image_path and os.path.exists(image_path):
        try:
            print(f"[INFO] Gửi ảnh đã làm nét: {image_path}")
            # Tạo URL ngẫu nhiên cho ảnh (chỉ dùng để bypass API nếu cần)
            random_url = f"https://example.com/{uuid.uuid4().hex}.png"
            success_msg = Message(text="✨ Ảnh đã làm nét xong!")
            # Gán thuộc tính normalUrl cho đối tượng Message
            success_msg.normalUrl = random_url
            
            client.sendLocalImage(
                imagePath=image_path,
                message=success_msg,
                thread_id=thread_id,
                thread_type=thread_type,
                ttl=60000
            )
            
            # Đợi một chút rồi xóa ảnh tạm để tiết kiệm bộ nhớ
            time.sleep(2)
            os.remove(image_path)
            print(f"[INFO] Đã xóa ảnh tạm: {image_path}")
        except Exception as e:
            print(f"[ERROR] Lỗi khi gửi ảnh: {e}")
            client.replyMessage(
                Message(text="❌ Lỗi khi gửi ảnh."),
                message_object, thread_id, thread_type, ttl=60000
            )
    else:
        client.replyMessage(
            Message(text="❌ Lỗi khi làm nét ảnh."),
            message_object, thread_id, thread_type, ttl=60000
        )

def get_mitaizl():
    """
    Hàm trả về dict chứa mapping của các lệnh (ở đây lệnh 'up' dùng để làm nét ảnh).
    """
    return {'up': handle_lam_net_command}


