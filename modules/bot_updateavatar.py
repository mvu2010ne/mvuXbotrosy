import os
import requests
import tempfile
import uuid
from datetime import datetime
from zlapi.models import *
from config import ADMIN

# Hàm gửi tin nhắn với định dạng (giả định từ ví dụ trước)
def send_message_with_style(client, text, thread_id, thread_type, ttl=60000, color="#db342e"):
    try:
        from .models import Message, MessageStyle, MultiMsgStyle
        base_length = len(text)
        adjusted_length = base_length + 355
        style = MultiMsgStyle([
            MessageStyle(offset=0, length=adjusted_length, style="color", color=color, auto_format=False),
            MessageStyle(offset=0, length=adjusted_length, style="bold", size="8", auto_format=False)
        ])
        msg = Message(text=text, style=style)
        return client.send(msg, thread_id=thread_id, thread_type=thread_type, ttl=ttl)
    except Exception as e:
        return None

# Hàm tải ảnh từ URL và lưu vào tệp tạm
def download_image(url):
    try:
        response = requests.get(url, stream=True)
        if response.status_code != 200:
            raise Exception(f"Không thể tải ảnh từ {url}. Mã trạng thái: {response.status_code}")
        
        # Tạo tệp tạm với tên ngẫu nhiên
        temp_file = os.path.join(tempfile.gettempdir(), f"zalo_avatar_{uuid.uuid4().hex}.jpg")
        with open(temp_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return temp_file
    except Exception as e:
        raise Exception(f"Lỗi khi tải ảnh: {str(e)}")

# Hàm xử lý cập nhật ảnh đại diện
def update_avatar(client, image_url, thread_id, thread_type):
    temp_file = None
    try:
        # Tải ảnh từ URL
        temp_file = download_image(image_url)
        
        # Kiểm tra thông tin tài khoản hiện tại
        user_info = client.fetchAccountInfo()
        current_avatar = user_info.avatar if user_info.avatar else "Không có"
        
        # Cập nhật ảnh đại diện
        result = client.changeAccountAvatar(temp_file, width=500, height=500)
        new_avatar = result.avatar if hasattr(result, 'avatar') and result.avatar else "Không rõ"
        
        # Gửi thông báo thành công
        send_message_with_style(
            client,
            f"✅ Đã cập nhật ảnh đại diện!\n📍 **Ảnh cũ**: {current_avatar}\n🖼️ **Ảnh mới**: {new_avatar}\n⏰ **Thời gian**: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}",
            thread_id,
            thread_type,
            color="#00ff00"
        )
    except ZaloAPIException as e:
        send_message_with_style(
            client,
            f"🔴 Lỗi khi cập nhật ảnh đại diện: {str(e)}",
            thread_id,
            thread_type
        )
    except Exception as e:
        send_message_with_style(
            client,
            f"🔴 Lỗi: {str(e)}",
            thread_id,
            thread_type
        )
    finally:
        # Xóa tệp tạm nếu tồn tại
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass

# Hàm xử lý lệnh bot.updateavatar
def handle_update_avatar_command(message, message_object, thread_id, thread_type, author_id, client):
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
    """Xử lý lệnh bot.updateavatar <URL ảnh> hoặc reply tin nhắn chứa ảnh."""
    # Kiểm tra quyền admin
    if str(author_id) not in ["7805327471649584311", client.uid]:
        return send_message_with_style(
            client,
            "🔴 Chỉ admin hoặc bot được sử dụng lệnh!",
            thread_id,
            thread_type
        )

    image_url = None
    PREFIX = "bot."  # Giả định prefix lệnh

    # Trường hợp 1: Reply một tin nhắn chứa ảnh
    if message_object.refMessage and hasattr(message_object, 'photo'):
        try:
            image_url = message_object.photo.get('normalUrl') or message_object.photo.get('thumbUrl') or message_object.photo.get('hdUrl')
            if not image_url:
                return send_message_with_style(
                    client,
                    "🔴 Tin nhắn reply không chứa ảnh hợp lệ!",
                    thread_id,
                    thread_type
                )
        except:
            return send_message_with_style(
                client,
                "🔴 Lỗi khi lấy ảnh từ tin nhắn reply!",
                thread_id,
                thread_type
            )
    
    # Trường hợp 2: Cung cấp URL ảnh trong nội dung lệnh
    else:
        parts = message.strip().split(maxsplit=1)
        if len(parts) < 2:
            return send_message_with_style(
                client,
                f"🔴 Vui lòng cung cấp URL ảnh hoặc reply một tin nhắn chứa ảnh!\nVí dụ: {PREFIX}updateavatar <URL>",
                thread_id,
                thread_type
            )
        image_url = parts[1]

    # Cập nhật ảnh đại diện
    update_avatar(client, image_url, thread_id, thread_type)

# Đăng ký lệnh
def get_mitaizl():
    return {
        'bot.updateavatar': handle_update_avatar_command
    }