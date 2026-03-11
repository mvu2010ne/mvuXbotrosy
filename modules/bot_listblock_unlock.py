from datetime import datetime
import time
from zlapi.models import *

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

def handle_blocked_members_list(message, message_object, thread_id, thread_type, author_id, bot):
    """ Lấy danh sách tên và ID thành viên bị chặn trong nhóm. """
    bot.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
    
    try:
        result = bot.get_blocked_members(thread_id)
        if not result["success"]:
            error_msg = f"Lỗi: {result['error_message']}"
            send_message_with_style(bot, error_msg, thread_id, thread_type)
            return

        # Truy cập đúng danh sách blocked_members từ cấu trúc API
        blocked_members = result["blocked_members"]["data"]["blocked_members"]
        total_blocked = len(blocked_members)
        if total_blocked == 0:
            send_message_with_style(bot, "Không có thành viên nào bị chặn.", thread_id, thread_type)
            return

        msg = f"DANH SÁCH THÀNH VIÊN BỊ CHẶN:\nTổng số: {total_blocked}\n\n"
        for count, member in enumerate(blocked_members, 1):
            member_id = member.get("id")
            member_name = member.get("zaloName", "Không xác định")[:30] + "..." if len(member.get("zaloName", "")) > 30 else member.get("zaloName", "Không xác định")
            msg += f"{count}. Tên: {member_name}\n UID: {member_id}\n\n"

        send_long_message(bot, msg, thread_id, thread_type, color="#000000")

    except Exception as e:
        error_msg = f"Lỗi: {e}"
        send_message_with_style(bot, error_msg, thread_id, thread_type)

def handle_unblock_member(message, message_object, thread_id, thread_type, author_id, bot):
    """ Mở chặn thành viên nhóm dựa trên UID. """
    bot.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)

    try:
        uids = message.split()[1:]  # Bỏ qua lệnh đầu tiên (bot.unblock)
        if not uids:
            send_message_with_style(bot, "Vui lòng cung cấp UID của thành viên cần mở chặn.", thread_id, thread_type)
            return

        # Lấy thông tin tên của các thành viên dựa trên UID
        names = []
        for uid in uids:
            try:
                info_response = bot.fetchUserInfo(uid)
                profiles = info_response.unchanged_profiles or info_response.changed_profiles
                info = profiles.get(str(uid))
                if info:
                    names.append(info.zaloName)
                else:
                    names.append("Không xác định")
            except Exception:
                names.append("Không xác định")

        result = bot.remove_blocked_member(thread_id, uids)
        if result["success"]:
            # Tạo thông báo với danh sách tên
            success_msg = f"Đã mở chặn thành công: {', '.join(names)}"
            send_message_with_style(bot, success_msg, thread_id, thread_type, color="#008000")
        else:
            error_msg = f"Lỗi khi mở chặn: {result['error_message']}"
            send_message_with_style(bot, error_msg, thread_id, thread_type)
    except Exception as e:
        error_msg = f"Đã xảy ra lỗi khi mở chặn thành viên: {e}"
        send_message_with_style(bot, error_msg, thread_id, thread_type)

def get_mitaizl():
    """ Trả về mapping các lệnh của bot. """
    return {
        'bot.blockedlist': handle_blocked_members_list,
        'bot.unblock': handle_unblock_member
    }