from datetime import datetime
import time
from zlapi.models import *

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Bot hỗ trợ lấy danh sách bạn bè của tài khoản Zalo và gửi danh sách cho người dùng.",
    'tính năng': [
        "📋 Lấy danh sách bạn bè của tài khoản Zalo và gửi danh sách chi tiết.",
        "🔔 Thông báo kết quả lấy danh sách với thời gian sống (TTL) khác nhau.",
        "🔍 Lấy thông tin chi tiết về bạn bè bao gồm tên, số điện thoại, giới tính, ngày sinh và thời gian tạo.",
        "🔒 Chỉ quản trị viên mới có quyền sử dụng lệnh này."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh để bot lấy danh sách bạn bè của tài khoản Zalo.",
        "📌 Bot sẽ gửi thông tin chi tiết về từng người bạn trong danh sách.",
        "✅ Nhận thông báo trạng thái lấy danh sách ngay lập tức."
    ]
}

def send_message_with_style(client, text, thread_id, thread_type, color="#db342e"):
    """ Gửi tin nhắn với định dạng màu sắc và font chữ. """
    base_length = len(text)
    adjusted_length = base_length + 355
    style = MultiMsgStyle([
        MessageStyle(
            offset=0, length=adjusted_length, style="color", color=color, auto_format=False,
        ),
        MessageStyle(
            offset=0, length=adjusted_length, style="font", size="6", auto_format=False
        )
    ])
    client.send(Message(text=text, style=style), thread_id=thread_id, thread_type=thread_type, ttl=60000)

def send_long_message(client, text, thread_id, thread_type, color="#000000", max_length=1500, delay=5):
    """ Nếu nội dung quá dài, chia thành nhiều phần và gửi với thời gian trễ giữa các phần. """
    chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
    for chunk in chunks:
        send_message_with_style(client, chunk, thread_id, thread_type, color)
        time.sleep(delay)

def handle_list_friends(message, message_object, thread_id, thread_type, author_id, bot):
    """ Lấy danh sách bạn bè của bot và gửi danh sách cho người dùng. Định dạng ví dụ: DANH SÁCH BẠN BÈ: Tổng số bạn bè: <số bạn bè> 1. Tên: <tên bạn bè> SĐT: <số điện thoại> Giới tính: <giới tính> Ngày sinh: <dob> Thời gian tạo: <createdTs> 2. ... """
    # Gửi phản ứng khi nhận lệnh
    bot.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)

    try:
        friends = bot.fetchAllFriends()
        total_friends = len(friends)
    except Exception as e:
        error_msg = f"Đã xảy ra lỗi khi lấy danh sách bạn bè: {e}"
        send_message_with_style(bot, error_msg, thread_id, thread_type)
        return

    msg = f"DANH SÁCH BẠN BÈ:\nTổng số bạn bè: {total_friends}\n\n"
    count = 1
    for friend in friends:
        # Giới hạn tên bạn bè nếu quá 30 ký tự
        friend_name = friend.zaloName[:30] + "..." if len(friend.zaloName) > 30 else friend.zaloName
        # Sử dụng userId của friend để lấy thông tin chi tiết
        friend_id = friend.userId
        try:
            info_response = bot.fetchUserInfo(friend_id)
            # Ưu tiên lấy thông tin từ unchanged_profiles, nếu không có thì dùng changed_profiles
            profiles = info_response.unchanged_profiles or info_response.changed_profiles
            info = profiles.get(str(friend_id))
        except Exception as e:
            # Nếu không lấy được thông tin chi tiết, bỏ qua người bạn này
            continue

        phone = info.phoneNumber if info.phoneNumber else "Ẩn"
        if friend_id == bot.uid:
            phone = "Ẩn"
        created_ts = info.createdTs
        if isinstance(created_ts, int):
            created_ts_formatted = datetime.fromtimestamp(created_ts).strftime("%H:%M %d/%m/%Y")
        else:
            created_ts_formatted = str(created_ts)
        gender = "Nam" if info.gender == 0 else "Nữ" if info.gender == 1 else "Không xác định"
        dob = info.sdob if hasattr(info, "sdob") and info.sdob else "Chưa cập nhật"

        msg += (
            f"{count}. Tên: {friend_name}\n"
            f" SĐT: {phone}\n"
            f" Giới tính: {gender}\n"
            f" Ngày sinh: {dob}\n"
            f" Thời gian tạo: {created_ts_formatted}\n\n"
        )
        count += 1

    send_long_message(bot, msg, thread_id, thread_type, color="#000000", max_length=1500, delay=5)

def get_mitaizl():
    """ Trả về mapping các lệnh của bot. """
    return {
        'bot.friendlist': handle_list_friends
    }
