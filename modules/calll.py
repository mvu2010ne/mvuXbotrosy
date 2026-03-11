import time
import logging
from zlapi.models import Message, ThreadType
from config import ADMIN

logging.basicConfig(level=logging.DEBUG)

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
        logging.error(f"Error fetching zaloName for UID {user_id}")
        return str(user_id)

def handle_spamcall_command(message, message_object, thread_id, thread_type, author_id, client):
    """
    Xử lý lệnh spam.call để gửi nhiều cuộc gọi liên tiếp.
    """
    logging.debug(f"Processing command: {message}, author_id: {author_id}, client type: {type(client)}")
    
    if not hasattr(client, 'sendMessage'):
        logging.error("Client does not have sendMessage method")
        return

    if str(author_id) not in ADMIN:
        client.sendMessage(Message(text="🚫 Quyền truy cập bị từ chối!\nChỉ admin mới có thể sử dụng lệnh này."), 
                          thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    args = message.split()
    if len(args) < 3 and not (hasattr(message_object, "mentions") and message_object.mentions):
        client.sendMessage(Message(text="⚠️ Cú pháp không hợp lệ!\nVui lòng nhập: spam.call <UID/tag> <số lần> [<delay_time>]"), 
                          thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    uid = extract_uid(args, message_object)
    if not uid:
        client.sendMessage(Message(text="❌ Không thể xác định UID từ thông tin tag!"), 
                          thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    try:
        # Nếu có tag, spam_count nằm ở vị trí args[-2]
        spam_count = int(args[-2])
        if spam_count <= 0 or spam_count > 100:
            raise ValueError("Số lần phải là số nguyên dương từ 1-100")
    except ValueError as e:
        client.sendMessage(Message(text=f"⚠️ Số lần spam không hợp lệ: {str(e)}"), 
                          thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    delay_time = 1
    if len(args) >= 4:
        try:
            delay_time = float(args[-1])
        except ValueError:
            client.sendMessage(Message(text="⚠️ Giá trị delay không hợp lệ!\nĐã sử dụng mặc định 1 giây."), 
                              thread_id=thread_id, thread_type=thread_type, ttl=60000)

    target_name = get_zalo_name(client, uid)

    start_message = f"""📞 ĐÃ NHẬN LỆNH SPAM CALL 📞
👤 Đối tượng: {target_name}
🔢 Số lần: {spam_count}
⏳ Delay: {delay_time} giây
🚀 Bắt đầu thực hiện..."""
    client.sendMessage(Message(text=start_message), thread_id=thread_id, thread_type=thread_type, ttl=180000)

    success_count = 0
    fail_count = 0

    for i in range(spam_count):
        try:
            call_result = client.sendCall(uid)
            logging.debug(f"Lần gọi thứ {i+1}: {call_result}")
            success_count += 1
        except Exception as e:
            logging.error(f"Lỗi ở lần gọi thứ {i+1}: {str(e)}")
            fail_count += 1
        time.sleep(delay_time)

    result_message = f"""✅ SPAM CALL HOÀN TẤT ✅
👤 Đối tượng: {target_name}
✅ Thành công: {success_count}
❌ Thất bại: {fail_count}
🎯 Tổng số lần: {spam_count}"""
    client.sendMessage(Message(text=result_message), thread_id=thread_id, thread_type=thread_type, ttl=180000)

def get_mitaizl():
    return {
        'calll': handle_spamcall_command,  # Giữ tên lệnh 'calll' như code gốc
    }