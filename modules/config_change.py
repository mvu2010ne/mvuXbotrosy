import sys
import os
import json
from zlapi.models import Message, MultiMsgStyle, MessageStyle

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🔧 Quản lý lệnh cập nhật cấu hình IMEI và SESSION_COOKIES của bot.",
    'tính năng': [
        "🔧 Lệnh config: Cập nhật IMEI và SESSION_COOKIES trong config.py, sau đó khởi động lại bot.",
        "🔒 Kiểm tra quyền admin: Chỉ admin có thể thực hiện lệnh này.",
        "📢 Gửi thông báo lỗi chi tiết nếu xảy ra sự cố trong quá trình thực thi."
    ],
    'hướng dẫn sử dụng': [
        "🔧 Gửi lệnh config [{imei}] [{cookie}] để cập nhật IMEI và SESSION_COOKIES. Ví dụ: config new_imei {\"key\":\"value\"}",
        "⚠️ Lưu ý: Chỉ admin (được định nghĩa trong config.py) có thể sử dụng lệnh này."
    ]
}

ADMIN_ID = "3299675674241805615"

def is_admin(author_id):
    """Kiểm tra người dùng có phải admin không"""
    return author_id == ADMIN_ID

def update_config(imei, cookies):
    """Cập nhật IMEI và SESSION_COOKIES trong file config.py"""
    try:
        with open('config.py', 'r') as file:
            lines = file.readlines()

        with open('config.py', 'w') as file:
            for line in lines:
                if line.strip().startswith('IMEI ='):
                    file.write(f'IMEI = "{imei}"\n')
                elif line.strip().startswith('SESSION_COOKIES ='):
                    file.write(f'SESSION_COOKIES = {json.dumps(cookies)}\n')
                else:
                    file.write(line)
    except Exception as e:
        raise RuntimeError(f"Không thể cập nhật config: {str(e)}")

def handle_config_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh config [{imei}] [{cookie}]"""
    if not is_admin(author_id):
        noquyen = "❌ Bạn không có quyền để thực hiện điều này!"
        client.replyMessage(Message(text=noquyen), message_object, thread_id, thread_type, ttl=60000)
        return

    try:
        # Tách lệnh để lấy imei và cookies
        parts = message.split(' ', 2)
        if len(parts) < 3:
            client.replyMessage(Message(text="❌ Vui lòng cung cấp cả IMEI và SESSION_COOKIES! Ví dụ: config new_imei {\"key\":\"value\"}"), message_object, thread_id, thread_type, ttl=60000)
            return

        new_imei = parts[1]
        new_cookies = json.loads(parts[2])

        # Cập nhật config
        update_config(new_imei, new_cookies)

        # Thông báo thành công
        msg = f"✅ Đã cập nhật IMEI: {new_imei} và SESSION_COOKIES. Đang khởi động lại bot..."
        styles = MultiMsgStyle([
            MessageStyle(offset=0, length=len(msg), style="color", color="#db342e", auto_format=False),
            MessageStyle(offset=0, length=len(msg), style="bold", size="16", auto_format=False)
        ])
        client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=60000)

        # Khởi động lại bot
        python_exe = sys.executable
        os.execl(python_exe, python_exe, *sys.argv)

    except json.JSONDecodeError:
        client.replyMessage(Message(text="❌ Lỗi: SESSION_COOKIES phải là định dạng JSON hợp lệ!"), message_object, thread_id, thread_type, ttl=60000)
    except Exception as e:
        import traceback
        error_msg = f"❌ Lỗi khi cập nhật config: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(error_msg)
        client.replyMessage(Message(text=error_msg), message_object, thread_id, thread_type, ttl=60000)

def get_mitaizl():
    """Trả về các lệnh bot hỗ trợ"""
    return {
        'config': handle_config_command  # Lệnh cập nhật IMEI và SESSION_COOKIES
    }