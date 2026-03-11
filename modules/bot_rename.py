import threading
from zlapi.models import Message, MultiMsgStyle, MessageStyle

# Module metadata
des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Lệnh bot.rename tài khoản",
    'tính năng': [
        "🔄 Đổi tên tài khoản thành tên mới do người dùng cung cấp.",
        "📨 Gửi phản hồi với kết quả đổi tên tài khoản.",
        "🔒 Chỉ người dùng được cấp quyền mới có thể thực hiện lệnh này."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh rm <tên mới> để đổi tên tài khoản.",
        "📌 Ví dụ: rm Tên Mới để đổi tên tài khoản thành Tên Mới.",
        "✅ Nhận thông báo trạng thái đổi tên tài khoản ngay lập tức."
    ]
}

# Hàm xử lý lệnh bot.rename
def handle_rename_command(message, message_object, thread_id, thread_type, author_id, client):
    content = message.strip().split()
    if len(content) < 2:
        error_message = "Vui lòng cung cấp tên mới sau lệnh bot.rename"
        client.replyMessage(
            Message(
                text=error_message,
                style=MultiMsgStyle([
                    MessageStyle(offset=0, length=len(error_message), style="font", size=13, auto_format=False, color="red"),
                    MessageStyle(offset=0, length=len(error_message), style="bold", auto_format=False, color="green")
                ])
            ),
            message_object, thread_id, thread_type, ttl=20000
        )
        return

    new_name = " ".join(content[1:])

    # ID người dùng được cấp quyền
    authorized_id = "3299675674241805615"  # Thay ID này thành ID của bạn
    if author_id != authorized_id:
        error_message = "Bạn không có quyền thực hiện lệnh này."
        client.replyMessage(
            Message(
                text=error_message,
                style=MultiMsgStyle([
                    MessageStyle(offset=0, length=len(error_message), style="font", size=13, auto_format=False, color="orange"),
                    MessageStyle(offset=0, length=len(error_message), style="bold", auto_format=False, color="red")
                ])
            ),
            message_object, thread_id, thread_type, ttl=20000
        )
        return

    def change_name_task():
        try:
            user = client.fetchAccountInfo().profile
            biz = user.bizPkg.label if user.bizPkg.label else {}
            dob = '2008-01-01'  # Ngày sinh mặc định
            gender = int(user.gender) if user.gender else 0  # 0: Nam, 1: Nữ
            client.changeAccountSetting(name=new_name, dob=dob, gender=gender, biz=biz)
            success_message = f"Tên tài khoản đã được đổi thành: {new_name}"
            client.replyMessage(
                Message(
                    text=success_message,
                    style=MultiMsgStyle([
                        MessageStyle(offset=0, length=len(success_message), style="font", size=13, auto_format=False, color="blue"),
                        MessageStyle(offset=0, length=len(success_message), style="bold", auto_format=False, color="green")
                    ])
                ),
                message_object, thread_id, thread_type, ttl=20000
            )
        except Exception as e:
            error_message = f"Lỗi khi đổi tên tài khoản: {e}"
            client.replyMessage(
                Message(
                    text=error_message,
                    style=MultiMsgStyle([
                        MessageStyle(offset=0, length=len(error_message), style="font", size=13, auto_format=False, color="red"),
                        MessageStyle(offset=0, length=len(error_message), style="bold", auto_format=False, color="green")
                    ])
                ),
                message_object, thread_id, thread_type,ttl=20000
            )
    
    threading.Thread(target=change_name_task).start()

# Đăng ký lệnh vào module
def get_mitaizl():
    return {
        'bot.rename': handle_rename_command
    }
