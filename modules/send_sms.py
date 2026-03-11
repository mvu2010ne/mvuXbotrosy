from zlapi import ZaloAPI
from zlapi.models import Message, ThreadType

# Mô tả tập lệnh
des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Gửi tin nhắn đến người dùng Zalo chỉ định qua user_id.",
    'tính năng': [
        "📩 Gửi tin nhắn trực tiếp đến một người dùng dựa trên user_id.",
        "📊 Gửi phản ứng xác nhận khi nhận lệnh send.sms.",
        "🛠 Kiểm tra định dạng lệnh để đảm bảo user_id và nội dung hợp lệ.",
        "📃 Báo kết quả gửi tin nhắn với tên Zalo của người nhận hoặc lỗi nếu có vấn đề."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh send.sms theo sau là user_id và nội dung tin nhắn.",
        "📌 Ví dụ: send.sms 3988082220695381823 Xin chào để gửi tin nhắn 'Xin chào' đến user_id 3988082220695381823.",
        "✅ Nhận thông báo xác nhận với tên Zalo của người nhận hoặc lỗi ngay lập tức."
    ]
}

def send_message_to_user(message, message_object, thread_id, thread_type, author_id, self):
    """
    Lệnh: send.sms <user_id> <nội dung>
    Chức năng: Gửi tin nhắn đến người dùng Zalo chỉ định qua user_id.
    """
    # Gửi phản ứng xác nhận khi nhận lệnh
    action = "✅"
    self.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    # Tách tin nhắn để lấy user_id và nội dung
    parts = message.split(maxsplit=2)
    if len(parts) < 3:
        self.sendMessage(Message("Vui lòng cung cấp user_id và nội dung tin nhắn. Ví dụ: send.sms 3988082220695381823 Xin chào"), thread_id, thread_type)
        return

    command, user_id, content = parts
    try:
        # Kiểm tra user_id có phải là số hợp lệ
        user_id = int(user_id)

        # Gửi tin nhắn đến user_id
        self.sendMessage(Message(content), thread_id=user_id, thread_type=ThreadType.USER)

        # Lấy thông tin người nhận
        try:
            info_response = self.fetchUserInfo(user_id)
            profiles = info_response.unchanged_profiles or info_response.changed_profiles
            info = profiles[str(user_id)]
            username = info.zaloName if hasattr(info, 'zaloName') else "Không xác định"
        except Exception as e:
            username = "Không xác định"
            self.sendMessage(Message(f"⚠️ Cảnh báo: Không thể lấy tên Zalo cho user_id {user_id}: {str(e)}"), thread_id, thread_type)

        # Gửi xác nhận đến người gửi lệnh
        self.sendMessage(Message(f"🟢 Đã gửi tin nhắn đến {username}: {content}"), thread_id, thread_type)

    except ValueError:
        self.sendMessage(Message(f"🔴 Lỗi: user_id '{user_id}' không hợp lệ, phải là số."), thread_id, thread_type)
    except Exception as e:
        self.sendMessage(Message(f"🔴 Lỗi khi gửi tin nhắn đến user_id {user_id}: {str(e)}"), thread_id, thread_type)

def get_mitaizl():
    return {
        'send.sms': send_message_to_user
    }