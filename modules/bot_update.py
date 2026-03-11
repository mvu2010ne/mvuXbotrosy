from zlapi import ZaloAPIException
from zlapi.models import Message, MessageStyle, MultiMsgStyle
from datetime import datetime
from config import PREFIX
from config import ADMIN
# Mô tả tập lệnh
des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🔧 Cập nhật thông tin tài khoản Zalo của Bot",
    'tính năng': [
        "📝 Thay đổi tên, ngày sinh và giới tính tài khoản Zalo.",
        "✅ Kiểm tra cú pháp và định dạng dữ liệu trước khi cập nhật.",
        "🔔 Gửi thông báo trạng thái thành công hoặc lỗi chi tiết.",
        "⚠️ Thông báo lỗi nếu định dạng không đúng hoặc API thất bại."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh bot.update name=<tên> dob=<YYYY-MM-DD> gender=<0/1>.",
        "📌 Ví dụ: bot.update name=Nguyễn Văn A dob=1990-01-01 gender=0",
        "✅ Nhận thông báo xác nhận khi cập nhật thành công."
    ]
}

# Hàm gửi tin nhắn với định dạng màu sắc và in đậm
def send_message_with_style(client, text, thread_id, thread_type, ttl=60000, color="#db342e"):
    """Gửi tin nhắn với định dạng màu sắc và in đậm."""
    base_length = len(text)
    adjusted_length = base_length + 355  # Tăng độ dài để đảm bảo style được áp dụng đầy đủ
    style = MultiMsgStyle([
        MessageStyle(offset=0, length=adjusted_length, style="color", color=color, auto_format=False),
        MessageStyle(offset=0, length=adjusted_length, style="bold", size="8", auto_format=False)
    ])
    msg = Message(text=text, style=style)
    client.send(msg, thread_id=thread_id, thread_type=thread_type, ttl=ttl)

# Hàm xử lý lệnh changeinfo
def handle_changeinfo_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh changeinfo để thay đổi thông tin tài khoản Zalo."""
    # Gửi phản ứng "✅" để xác nhận lệnh
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    # Thông báo lỗi cú pháp
    msg_error = f"🔴 Cú pháp lệnh không hợp lệ! Vui lòng sử dụng: {PREFIX}bot.update name=<tên> dob=<ngày sinh> gender=<giới tính>"
    # Replace undefined all_admin_ids with ADMIN check
    if author_id not in ADMIN:
        error_message = "Bạn không có quyền sử dụng lệnh này."
        style_error = MultiMsgStyle([
            MessageStyle(offset=0, length=len(error_message), style="color", color="#db342e", auto_format=False),
            MessageStyle(offset=0, length=len(error_message), style="bold", size="16", auto_format=False),
        ])
        client.replyMessage(Message(text=error_message, style=style_error), message_object, thread_id, thread_type, ttl=30000)
        return
    try:
        # Tách tin nhắn thành các phần
        parts = message.split()
        params = {}

        # Trích xuất các tham số từ tin nhắn
        for part in parts[1:]:  # Bỏ qua phần tiền tố lệnh (ví dụ: {PREFIX}changeinfo)
            if '=' in part:
                key, value = part.split('=', 1)
                params[key.lower()] = value
            else:
                send_message_with_style(client, msg_error, thread_id, thread_type)
                return

        # Kiểm tra xem có đủ tham số không
        required_params = ['name', 'dob', 'gender']
        if not all(param in params for param in required_params):
            send_message_with_style(client, msg_error, thread_id, thread_type)
            return

        # Lấy giá trị từ params
        name = params['name']
        dob = params['dob']
        gender = params['gender']

        # Kiểm tra định dạng ngày sinh
        try:
            datetime.strptime(dob, '%Y-%m-%d')
        except ValueError:
            send_message_with_style(client, "🔴 Ngày sinh không hợp lệ! Vui lòng nhập theo định dạng YYYY-MM-DD.", thread_id, thread_type)
            return

        # Kiểm tra giá trị giới tính
        if gender not in ['0', '1']:
            send_message_with_style(client, "🔴 Giới tính không hợp lệ! Vui lòng nhập 0 cho Nam hoặc 1 cho Nữ.", thread_id, thread_type)
            return
        gender = int(gender)  # Chuyển đổi sang số nguyên để phù hợp với changeAccountSetting

        # Gọi phương thức changeAccountSetting
        try:
            result = client.changeAccountSetting(name=name, dob=dob, gender=gender)
            # Kiểm tra kết quả trả về
            if isinstance(result, dict) and 'error_code' in result:
                error_code = result['error_code']
                error_message = result.get('error_message', 'Unknown error')
                send_message_with_style(client, f"🔴 Lỗi khi thay đổi thông tin: {error_message} (Mã lỗi: {error_code})", thread_id, thread_type)
            else:
                send_message_with_style(client, "🟢 Thông tin tài khoản đã được cập nhật thành công!", thread_id, thread_type)
        except ZaloAPIException as e:
            send_message_with_style(client, f"🔴 Đã xảy ra lỗi khi thay đổi thông tin: {str(e)}", thread_id, thread_type)
        except Exception as e:
            send_message_with_style(client, f"🔴 Đã xảy ra lỗi: {str(e)}", thread_id, thread_type)

    except Exception as e:
        send_message_with_style(client, f"🔴 Đã xảy ra lỗi: {str(e)}", thread_id, thread_type)

# Đăng ký lệnh
def get_mitaizl():
    return {
        'bot.update': handle_changeinfo_command
    }