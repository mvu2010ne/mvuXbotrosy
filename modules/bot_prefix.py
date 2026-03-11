import sys
import os  # Thêm dòng này
from config import ADMIN, PREFIX
from zlapi.models import Message, MultiMsgStyle, MessageStyle

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🔧 Quản lý các lệnh cơ bản của bot, bao gồm reset bot, thay đổi prefix và xóa prefix.",
    'tính năng': [
        "🔄 Lệnh reset: Khởi động lại bot với thông báo thành công và cập nhật prefix mới.",
        "🔧 Lệnh bot.setprefix: Thay đổi prefix của bot và lưu vào file config.py.",
        "🗑️ Lệnh bot.delprefix: Xóa giá trị prefix, thiết lập prefix thành chuỗi rỗng.",
        "🔒 Kiểm tra quyền admin: Chỉ admin có thể thực hiện các lệnh này.",
        "📢 Gửi thông báo lỗi chi tiết nếu xảy ra sự cố trong quá trình thực thi."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh bot.reset để khởi động lại bot.",
        "📌 Gửi lệnh bot.setprefix <prefix_mới> để thay đổi prefix. Ví dụ: bot.setprefix !",
        "🗑️ Gửi lệnh bot.delprefix để xóa giá trị prefix.",
        "⚠️ Lưu ý: Chỉ admin (được định nghĩa trong config.py) có thể sử dụng các lệnh này."
    ]
}


def is_admin(author_id):
    return author_id in ADMIN

def update_prefix(new_prefix):
    """Cập nhật prefix trong file config.py"""
    try:
        # Mở file config.py và đọc nội dung
        with open('config.py', 'r') as file:
            lines = file.readlines()

        # Ghi lại file với prefix mới
        with open('config.py', 'w') as file:
            for line in lines:
                if line.strip().startswith('PREFIX ='):
                    file.write(f'PREFIX = "{new_prefix}"\n')  # Cập nhật dòng PREFIX
                else:
                    file.write(line)
    except Exception as e:
        raise RuntimeError(f"Không thể cập nhật PREFIX: {str(e)}")

def handle_reset_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh bot.reset bot"""
    if not is_admin(author_id):
        noquyen = "❌ Bạn không có quyền để thực hiện điều này!"
        client.replyMessage(Message(text=noquyen), message_object, thread_id, thread_type, ttl=60000)
        return

    try:
        # Thông báo bot.reset với icon thành công và TTL 60 giây
        msg = "✅ Đã reset thành công, lệnh đang khởi động và cập nhật PREFIX mới \n"
        styles = MultiMsgStyle([
            MessageStyle(offset=0, length=len(msg), style="color", color="#db342e", auto_format=False),
            MessageStyle(offset=0, length=len(msg), style="bold", size="16", auto_format=False)
        ])
        client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=60000)

        # Khởi động lại bot
        python_exe = sys.executable
        os.execl(python_exe, python_exe, *sys.argv)  # Dòng này cần 'os' nên bạn phải import os

    except Exception as e:
        # Log lỗi nếu xảy ra
        import traceback
        error_msg = f"❌ Lỗi xảy ra khi reset bot: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(error_msg)
        client.replyMessage(Message(text=error_msg), message_object, thread_id, thread_type, ttl=60000)

def handle_change_prefix(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh đổi prefix"""
    if not is_admin(author_id):
        noquyen = "❌ Bạn không có quyền để thực hiện điều này!"
        client.replyMessage(Message(text=noquyen), message_object, thread_id, thread_type, ttl=60000)
        return

    try:
        # Lấy prefix mới từ tin nhắn
        new_prefix = message.split(' ')[1]
        if not new_prefix:
            client.replyMessage(Message(text="❌ Vui lòng nhập prefix mới."), message_object, thread_id, thread_type, ttl=60000)
            return

        # Cập nhật prefix và thông báo thành công
        update_prefix(new_prefix)
        client.replyMessage(Message(text=f"✅ Prefix đã được đổi thành: {new_prefix}"), message_object, thread_id, thread_type, ttl=60000)

        # Reset lại bot sau khi đổi prefix
        handle_reset_command(message, message_object, thread_id, thread_type, author_id, client)

    except IndexError:
        client.replyMessage(Message(text="❌ Lỗi: Vui lòng cung cấp prefix hợp lệ!"), message_object, thread_id, thread_type, ttl=60000)
    except Exception as e:
        error_msg = f"❌ Lỗi khi đổi PREFIX: {str(e)}"
        print(error_msg)
        client.replyMessage(Message(text=error_msg), message_object, thread_id, thread_type, ttl=60000)

def handle_remove_prefix(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh xóa giá trị prefix (thiết lập PREFIX thành chuỗi rỗng)"""
    if not is_admin(author_id):
        noquyen = "❌ Bạn không có quyền để thực hiện điều này!"
        client.replyMessage(Message(text=noquyen), message_object, thread_id, thread_type, ttl=60000)
        return

    try:
        # Cập nhật prefix thành chuỗi rỗng
        update_prefix("")
        client.replyMessage(Message(text="✅ Đã xóa giá trị prefix. Prefix hiện tại là: (trống)"), message_object, thread_id, thread_type, ttl=60000)
        # Reset lại bot sau khi xóa prefix
        handle_reset_command(message, message_object, thread_id, thread_type, author_id, client)
    except Exception as e:
        error_msg = f"❌ Lỗi khi xóa PREFIX: {str(e)}"
        print(error_msg)
        client.replyMessage(Message(text=error_msg), message_object, thread_id, thread_type, ttl=60000)

def handle_get_prefix(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh bot.prefix để xem prefix hiện tại"""
    try:
        # Lấy prefix hiện tại từ config
        current_prefix = PREFIX
        if current_prefix:
            msg = f"✅ Prefix hiện tại là: {current_prefix}"
        else:
            msg = "✅ Prefix hiện tại là: (trống)"
        
        # Gửi thông báo với định dạng
        styles = MultiMsgStyle([
            MessageStyle(offset=0, length=len(msg), style="color", color="#db342e", auto_format=False),
            MessageStyle(offset=0, length=len(msg), style="bold", size="16", auto_format=False)
        ])
        client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=60000)

    except Exception as e:
        error_msg = f"❌ Lỗi khi xem PREFIX: {str(e)}"
        print(error_msg)
        client.replyMessage(Message(text=error_msg), message_object, thread_id, thread_type, ttl=60000)

def get_mitaizl():
    """Trả về các lệnh bot hỗ trợ"""
    return {
        'bot.reset': handle_reset_command,      # Lệnh reset bot
        'bot.setprefix': handle_change_prefix,  # Lệnh đổi prefix
        'bot.delprefix': handle_remove_prefix,  # Lệnh xóa giá trị prefix
        'bot.prefix': handle_get_prefix         # Lệnh xem prefix hiện tại
    }
