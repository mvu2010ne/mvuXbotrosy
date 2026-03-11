from zlapi.models import Message, ThreadType
from config import ADMIN
import time

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Thực hiện cuộc gọi hoặc spam cuộc gọi đến người dùng Zalo thông qua UID hoặc tag.",
    'tính năng': [
        "📞 Lệnh 'call' thực hiện một cuộc gọi đến người dùng được chỉ định qua UID hoặc tag.",
        "📲 Lệnh 'spam.call' gửi nhiều cuộc gọi liên tiếp với số lần và khoảng cách thời gian tùy chỉnh.",
        "🔒 Chỉ admin được phép sử dụng các lệnh này để đảm bảo an toàn.",
        "👤 Tự động lấy tên Zalo từ UID để hiển thị trong thông báo.",
        "⚠️ Thông báo lỗi chi tiết nếu UID không hợp lệ, cú pháp sai, hoặc cuộc gọi thất bại.",
        "📊 Báo cáo kết quả spam call với số lần thành công và thất bại."
    ],
    'hướng dẫn sử dụng': [
        "📩 Sử dụng lệnh 'call <UID>' hoặc 'call @tag' để gọi một lần đến người dùng.",
        "📩 Sử dụng lệnh 'spam.call <UID/tag> <số lần> [<delay_time>]' để spam cuộc gọi.",
        "📌 Ví dụ: 'call 123456789' hoặc 'spam.call @User 5 2' (spam 5 lần, cách nhau 2 giây).",
        "✅ Nhận thông báo kết quả cuộc gọi hoặc báo cáo sau khi spam hoàn tất."
    ]
}

def extract_uid(args, message_object):
    """
    Trích xuất UID từ đối số hoặc mentions.
    """
    uid_candidate = args[1] if len(args) >= 2 else ""
    if uid_candidate.isdigit():
        return uid_candidate
    if hasattr(message_object, "mentions") and message_object.mentions:
        return message_object.mentions[0].get("uid") if isinstance(message_object.mentions[0], dict) else message_object.mentions[0]
    return uid_candidate

def get_zalo_name(client, user_id):
    """
    Lấy tên Zalo từ UID.
    """
    try:
        info_response = client.fetchUserInfo(user_id)
        profiles = info_response.unchanged_profiles or info_response.changed_profiles
        info = profiles[str(user_id)]
        return getattr(info, "zaloName", str(user_id))
    except Exception:
        return str(user_id)

def handle_call_command(message, message_object, thread_id, thread_type, author_id, client):
    """
    Lệnh gọi 1 lần đến UID hoặc người được tag.
    """
    if author_id not in ADMIN:
        client.sendMessage(Message(text="🚫 Quyền truy cập bị từ chối!\nChỉ admin mới có thể sử dụng lệnh này."), thread_id, thread_type, ttl=60000)
        return

    args = message.split()
    if len(args) < 2 and not (hasattr(message_object, "mentions") and message_object.mentions):
        client.sendMessage(Message(text="⚠️ Vui lòng cung cấp UID hoặc tag người dùng để gọi!"), thread_id, thread_type, ttl=60000)
        return

    uid = extract_uid(args, message_object)
    if not uid:
        client.sendMessage(Message(text="❌ Không thể xác định UID từ thông tin tag!"), thread_id, thread_type, ttl=60000)
        return

    target_name = get_zalo_name(client, uid)

    try:
        call_result = client.sendCall(uid)
        print(call_result)
        client.sendMessage(Message(text=f"📞 Cuộc gọi đến {target_name} đã được thực hiện!"), thread_id, thread_type, ttl=60000)
    except Exception as e:
        client.sendMessage(Message(text=f"❌ Lỗi khi gọi {target_name}:\n{str(e)}"), thread_id, thread_type, ttl=60000)

def handle_spamcall_command(message, message_object, thread_id, thread_type, author_id, client):
    if author_id not in ADMIN:
        client.sendMessage(Message(text="🚫 Quyền truy cập bị từ chối!\nChỉ admin mới có thể sử dụng lệnh này."), thread_id, thread_type, ttl=60000)
        return

    args = message.split()
    if (len(args) < 3 and not (hasattr(message_object, "mentions") and message_object.mentions)):
        client.sendMessage(Message(text="⚠️ Cú pháp không hợp lệ!\nVui lòng nhập: spam.call <UID/tag> <số lần spam> [<delay_time>]"), thread_id, thread_type, ttl=60000)
        return

    uid = extract_uid(args, message_object)
    if not uid:
        client.sendMessage(Message(text="❌ Không thể xác định UID từ thông tin tag!"), thread_id, thread_type, ttl=60000)
        return

    try:
        # Nếu có tag, spam_count nằm ở vị trí args[-2]
        spam_count = int(args[-2])
    except ValueError:
        client.sendMessage(Message(text="⚠️ Số lần spam không hợp lệ! Vui lòng nhập số nguyên."), thread_id, thread_type, ttl=60000)
        return

    delay_time = 1
    if len(args) >= 4:
        try:
            delay_time = float(args[-1])
        except ValueError:
            client.sendMessage(Message(text="⚠️ Giá trị delay không hợp lệ!\nĐã sử dụng mặc định 1 giây."), thread_id, thread_type, ttl=60000)

    target_name = get_zalo_name(client, uid)

    start_message = f"""📞 ĐÃ NHẬN LỆNH SPAM CALL 📞
👤 Đối tượng: {target_name}
🔢 Bón hành: {spam_count}
⏳ Delay: {delay_time} giây
🚀 Bắt đầu tấn công..."""
    client.sendMessage(Message(text=start_message), thread_id, thread_type, ttl=180000)

    success_count = 0
    fail_count = 0

    for i in range(spam_count):
        try:
            call_result = client.sendCall(uid)
            print(f"Lần gọi thứ {i+1}: {call_result}")
            success_count += 1
        except Exception as e:
            print(f"Lỗi ở lần gọi thứ {i+1}: {str(e)}")
            fail_count += 1
        time.sleep(delay_time)

    result_message = f"""✅ SPAM CALL HOÀN TẤT ✅
👤 Đối tượng: {target_name}
✅ Thành công: {success_count}
❌ Thất bại: {fail_count}
🎯 Tổng số lần: {spam_count}"""
    client.sendMessage(Message(text=result_message), thread_id, thread_type, ttl=180000)


def get_mitaizl():
    return {
        'call': handle_call_command,
        'spam.call': handle_spamcall_command
    }