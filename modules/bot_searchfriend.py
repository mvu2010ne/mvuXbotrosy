from datetime import datetime
import time
from zlapi.models import *

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Bot hỗ trợ tìm kiếm bạn bè trong danh sách bạn bè của tài khoản Zalo theo tên.",
    'tính năng': [
        "🔍 Tìm kiếm bạn bè theo tên (không phân biệt hoa thường).",
        "📋 Hiển thị thông tin bạn bè bao gồm Tên và ID.",
        "🔔 Thông báo kết quả tìm kiếm với thời gian sống (TTL) khác nhau.",
        "🔒 Chỉ quản trị viên mới có quyền sử dụng lệnh này."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh với cú pháp: bot.searchfriend <tên cần tìm>",
        "📌 Bot sẽ trả về danh sách bạn bè khớp với tên tìm kiếm.",
        "✅ Nhận thông báo trạng thái tìm kiếm ngay lập tức."
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

def handle_search_friend(message, message_object, thread_id, thread_type, author_id, bot):
    """ Tìm kiếm bạn bè theo tên và trả về danh sách bạn bè khớp với tên. Định dạng: KẾT QUẢ TÌM KIẾM: Tổng số bạn bè tìm thấy: <số bạn bè> 1. Tên: <tên bạn bè> ID: <ID bạn bè> 2. ... """
    # Gửi phản ứng khi nhận lệnh
    bot.sendReaction(message_object, "🔍", thread_id, thread_type, reactionType=75)

    # Lấy tên cần tìm từ tin nhắn
    search_query = message.strip().split(' ', 1)[1] if len(message.strip().split(' ', 1)) > 1 else ""
    if not search_query:
        error_msg = "Vui lòng cung cấp tên để tìm kiếm! Cú pháp: bot.searchfriend <tên>"
        send_message_with_style(bot, error_msg, thread_id, thread_type, color="#ff0000")
        return

    try:
        friends = bot.fetchAllFriends()
        # Lọc danh sách bạn bè theo tên (không phân biệt hoa thường)
        matching_friends = [
            friend for friend in friends
            if search_query.lower() in friend.zaloName.lower()
        ]
        total_matches = len(matching_friends)
    except Exception as e:
        error_msg = f"Đã xảy ra lỗi khi lấy danh sách bạn bè: {e}"
        send_message_with_style(bot, error_msg, thread_id, thread_type, color="#ff0000")
        return

    if total_matches == 0:
        msg = f"KẾT QUẢ TÌM KIẾM:\nKhông tìm thấy bạn bè nào với tên '{search_query}'."
        send_message_with_style(bot, msg, thread_id, thread_type, color="#000000")
        return

    msg = f"KẾT QUẢ TÌM KIẾM:\nTổng số bạn bè tìm thấy: {total_matches}\n\n"
    count = 1
    for friend in matching_friends:
        # Giới hạn tên bạn bè nếu quá 30 ký tự
        friend_name = friend.zaloName[:30] + "..." if len(friend.zaloName) > 30 else friend.zaloName
        friend_id = friend.userId

        msg += (
            f"{count}. Tên: {friend_name}\n"
            f" ID: {friend_id}\n\n"
        )
        count += 1

    send_long_message(bot, msg, thread_id, thread_type, color="#000000", max_length=1500, delay=5)

def get_mitaizl():
    """ Trả về mapping các lệnh của bot. """
    return {
        'bot.searchfriend': handle_search_friend
    }