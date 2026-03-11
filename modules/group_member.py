from datetime import datetime 
import time
from zlapi.models import *

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Bot hỗ trợ lấy thông tin chi tiết của các thành viên trong nhóm Zalo và gửi danh sách về cho người dùng.",
    'tính năng': [
        "📋 Lấy thông tin toàn bộ thành viên trong nhóm từ danh sách ID thành viên.",
        "🔍 Tạo card thông tin chi tiết cho từng thành viên bao gồm tên, ngày tạo tài khoản và ngày sinh.",
        "📩 Gửi danh sách các card thông tin đến người dùng dưới dạng tin nhắn chia nhỏ nếu quá dài.",
        "🔔 Thông báo kết quả lấy thông tin với thời gian sống (TTL) khác nhau.",
        "🔒 Chỉ quản trị viên mới có quyền sử dụng lệnh này."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh để bot lấy thông tin chi tiết của các thành viên trong nhóm Zalo.",
        "📌 Bot sẽ gửi thông tin chi tiết về từng thành viên trong danh sách.",
        "✅ Nhận thông báo trạng thái lấy thông tin ngay lập tức."
    ]
}

def send_message_with_style(client, text, thread_id, thread_type, color="#db342e"):
    """ Gửi tin nhắn với định dạng màu sắc và font chữ. """
    base_length = len(text)
    adjusted_length = base_length + 355
    style = MultiMsgStyle([
        MessageStyle(
            offset=0,
            length=adjusted_length,
            style="color",
            color=color,
            auto_format=False,
        ),
        MessageStyle(
            offset=0,
            length=adjusted_length,
            style="font",
            size="6",
            auto_format=False
        )
    ])
    client.send(Message(text=text, style=style), thread_id=thread_id, thread_type=thread_type, ttl=60000)

def send_long_message(client, text, thread_id, thread_type, color="#000000", max_length=1500, delay=5):
    """ Nếu nội dung quá dài, chia thành nhiều phần và gửi với thời gian trễ giữa các phần. """
    chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
    for chunk in chunks:
        send_message_with_style(client, chunk, thread_id, thread_type, color)
        time.sleep(delay)

def get_user_card(client, user_id):
    """ Lấy thông tin tài khoản của thành viên và tạo card thông tin với định dạng: Tên: <tên thành viên> (đã rút gọn nếu quá 30 ký tự) Ngày tạo: <thời gian tạo tài khoản, định dạng HH:MM dd/mm/YYYY> Sinh nhật: <ngày sinh> (nếu có) Lưu ý: Loại bỏ hậu tố '_0' khỏi user_id nếu có. """
    try:
        # Loại bỏ hậu tố "_0" nếu có
        if isinstance(user_id, str) and user_id.endswith('_0'):
            user_id = user_id.rsplit('_', 1)[0]
        info = client.fetchUserInfo(user_id)
        info = info.unchanged_profiles or info.changed_profiles
        info = info[str(user_id)]
        userName = info.zaloName[:30] + "..." if len(info.zaloName) > 30 else info.zaloName
        createTime = info.createdTs
        if isinstance(createTime, int):
            createTime = datetime.fromtimestamp(createTime).strftime("%H:%M %d/%m/%Y")
        else:
            createTime = "Không xác định"
        # Date of Birth
        dob = info.dob or info.sdob or "Ẩn"
        if isinstance(dob, int):
            dob = datetime.fromtimestamp(dob).strftime("%d/%m/%Y")
        card = (
            f"Tên: {userName}\n"
            f"Ngày tạo: {createTime}\n"
            f"Sinh nhật: {dob}"
        )
        return card
    except Exception as ex:
        return f"Không thể lấy thông tin của user {user_id}: {ex}\n"

def handle_list_members(message, message_object, thread_id, thread_type, author_id, bot):
    """ Lấy toàn bộ ID thành viên trong nhóm từ memVerList của group_info, sau đó lấy thông tin của từng thành viên và gửi danh sách các card thông tin. Định dạng ví dụ: NHÓM: [tên nhóm] Tổng số thành viên: <số thành viên> 1. Tên: <tên thành viên> Ngày tạo: <ngày tạo tài khoản> Sinh nhật: <ngày sinh> 2. ... """
    # Gửi phản ứng khi nhận lệnh
    bot.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
    try:
        group_info = bot.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
        members = group_info.get('memVerList', [])
        total_members = len(members)
    except Exception as e:
        error_msg = f"Đã xảy ra lỗi khi lấy thông tin nhóm: {e}"
        send_message_with_style(bot, error_msg, thread_id, thread_type)
        return
    group_name = group_info.get("name", "Nhóm không xác định")
    msg = f"NHÓM: {group_name}\nTổng số thành viên: {total_members}\n\n"
    count = 1
    for member_id in members:
        card = get_user_card(bot, member_id)
        msg += f"{count}. {card}\n\n"
        count += 1
    send_long_message(bot, msg, thread_id, thread_type, color="#000000", max_length=1500, delay=5)

def get_mitaizl():
    return {
        'group.member': handle_list_members
    }
