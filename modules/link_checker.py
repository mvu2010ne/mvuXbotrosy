import json
import os
import time
import re
import threading
import logging
import urllib.parse
from zlapi.models import Message, MessageStyle, MultiMsgStyle
from config import ADMIN, PREFIX

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🔍 Quản lý và tự động xóa các tin nhắn chứa liên kết trong các nhóm Zalo.",
    'tính năng': [
        "📋 Quản lý danh sách nhóm để kiểm tra liên kết (thêm, xóa, liệt kê).",
        "🔗 Phát hiện và xóa tin nhắn chứa liên kết trong nhóm (hỗ trợ cả tin nhắn văn bản và tin nhắn được đề xuất).",
        "⏰ Tự động kiểm tra liên kết mỗi 5 phút hoặc kiểm tra thủ công theo yêu cầu.",
        "✅ Chỉ admin được phép sử dụng các lệnh quản lý và kiểm tra liên kết.",
        "⚠️ Ghi log chi tiết các hoạt động và lỗi để dễ dàng theo dõi."
    ],
    'hướng dẫn sử dụng': [
        f"📩 Gửi {PREFIX}addchecklinkgroup <group_id1>\\n<group_id2> hoặc tag nhóm để thêm vào danh sách kiểm tra.",
        f"📩 Gửi {PREFIX}delchecklinkgroup <group_id> hoặc tag nhóm để xóa khỏi danh sách.",
        f"📩 Gửi {PREFIX}listchecklinkgroup để xem danh sách nhóm đang kiểm tra.",
        f"📩 Gửi {PREFIX}startlinkcheck để bắt đầu kiểm tra liên kết tự động (mỗi 5 phút).",
        f"📩 Gửi {PREFIX}stoplinkcheck để nhận thông tin về trạng thái kiểm tra tự động.",
        f"📩 Gửi {PREFIX}checklinknow [group_id] hoặc tag nhóm để kiểm tra và xóa liên kết ngay lập tức.",
        "📌 Ví dụ: addchecklinkgroup 123456789 hoặc checklinknow @groupname."
    ]
}

# Cấu hình logger
logger = logging.getLogger("LinkChecker")

# Đường dẫn file lưu trữ danh sách nhóm
GROUP_LIST_FILE = "group_list.json"
SKIP_USERS_FILE = "skip_userschecklink.json"

def load_skip_users():
    """
    Tải danh sách ID người dùng bỏ qua từ file JSON.
    Trả về danh sách rỗng nếu file không tồn tại hoặc lỗi định dạng.
    """
    if not os.path.exists(SKIP_USERS_FILE):
        return []
    try:
        with open(SKIP_USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Lỗi tải danh sách người dùng bỏ qua: {str(e)}")
        return []

def save_skip_users(user_list):
    """Lưu danh sách người dùng bỏ qua vào file JSON với định dạng UTF-8."""
    try:
        with open(SKIP_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(user_list, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Lỗi lưu danh sách người dùng bỏ qua: {str(e)}")

def add_skip_user(user_id, user_name):
    """
    Thêm người dùng vào danh sách bỏ qua dựa theo user_id và user_name.
    Trả về True nếu thêm thành công, False nếu user_id đã tồn tại.
    """
    user_list = load_skip_users()
    for user in user_list:
        if user.get("user_id") == user_id:
            return False
    user_list.append({"user_id": user_id, "user_name": user_name})
    save_skip_users(user_list)
    return True

def remove_skip_user(user_id):
    """
    Xóa người dùng khỏi danh sách bỏ qua.
    Trả về True nếu xóa thành công, False nếu user_id không tồn tại.
    """
    user_list = load_skip_users()
    for user in user_list:
        if user.get("user_id") == user_id:
            user_list.remove(user)
            save_skip_users(user_list)
            return True
    return False

def list_skip_users():
    """Trả về danh sách người dùng bỏ qua."""
    return load_skip_users()


def load_group_list():
    """
    Tải danh sách ID nhóm từ file JSON.
    Trả về danh sách rỗng nếu file không tồn tại hoặc lỗi định dạng.
    """
    if not os.path.exists(GROUP_LIST_FILE):
        return []
    try:
        with open(GROUP_LIST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Lỗi tải danh sách nhóm: {str(e)}")
        return []

def save_group_list(group_list):
    """Lưu danh sách nhóm vào file JSON với định dạng UTF-8."""
    try:
        with open(GROUP_LIST_FILE, "w", encoding="utf-8") as f:
            json.dump(group_list, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Lỗi lưu danh sách nhóm: {str(e)}")

def add_group(group_id, group_name):
    """
    Thêm nhóm vào danh sách dựa theo group_id và group_name.
    Trả về True nếu thêm thành công, False nếu group_id đã tồn tại.
    """
    group_list = load_group_list()
    for group in group_list:
        if group.get("group_id") == group_id:
            return False
    group_list.append({"group_id": group_id, "group_name": group_name})
    save_group_list(group_list)
    return True

def remove_group(group_id):
    """
    Xóa nhóm khỏi danh sách.
    Trả về True nếu xóa thành công, False nếu group_id không tồn tại.
    """
    group_list = load_group_list()
    for group in group_list:
        if group.get("group_id") == group_id:
            group_list.remove(group)
            save_group_list(group_list)
            return True
    return False

def list_groups():
    """Trả về danh sách nhóm."""
    return load_group_list()

def is_link(text):
    """
    Kiểm tra xem văn bản có phải là link hay không bằng regex.
    """
    if not isinstance(text, str):
        return False
    
    # Làm sạch chuỗi: bỏ ký tự thoát, khoảng trắng, và ký tự xuống dòng
    text = urllib.parse.unquote(text).strip()
    
    # Loại bỏ các chuỗi có đuôi file phổ biến
    file_extensions = r'\.(txt|pdf|doc|docx|xls|xlsx|png|jpg|jpeg|gif|zip|rar)$'
    if re.search(file_extensions, text, re.IGNORECASE):
        return False

    # Biểu thức chính quy để khớp với URL
    url_pattern = r'(?:(?:https?://|www\.)[^\s<>"]+\.[^\s<>"/]+(?:/[^\s<>"]*)*)'
    return bool(re.search(url_pattern, text, re.IGNORECASE))

def scan_qr_and_get_result(image_url, thread_id, client, message_object):
    """
    Hàm phụ để quét mã QR từ ảnh và trả về kết quả.
    """
    import requests
    import os

    try:
        # Tạo thư mục cache nếu chưa tồn tại
        os.makedirs("modules/cache", exist_ok=True)
        
        # Tải ảnh về local
        image_response = requests.get(image_url, timeout=10)
        image_response.raise_for_status()
        image_path = "modules/cache/temp_qr.jpg"
        with open(image_path, 'wb') as f:
            f.write(image_response.content)

        # Gửi file ảnh lên API
        api_url = "http://api.qrserver.com/v1/read-qr-code/"
        with open(image_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(api_url, files=files, timeout=10)
            response.raise_for_status()
            data = response.json()

        if os.path.exists(image_path):
            os.remove(image_path)

        if data and 'symbol' in data[0] and data[0]['symbol'][0].get('data'):
            return data[0]['symbol'][0]['data']
        return None
    except Exception as e:
        print(f"Lỗi khi quét mã QR: {str(e)}")
        return None

def fetch_and_delete_links(client, group_id, group_name):
    """
    Lấy 50 tin nhắn gần nhất từ nhóm và xóa các tin nhắn chứa link, trừ tin nhắn của người dùng trong danh sách bỏ qua.
    Kiểm tra liên kết trong các trường: văn bản, content dictionary, title của chat.video.msg, và mã QR trong ảnh.
    """
    try:
        group_data = client.getRecentGroup(group_id)
        messages = group_data.groupMsgs if hasattr(group_data, 'groupMsgs') else []
        skip_users = load_skip_users()
        skip_user_ids = [user["user_id"] for user in skip_users]

        for msg in messages:
            msg_content = None
            contains_link = False
            owner_id = getattr(msg, 'uidFrom', getattr(msg, 'ownerId', None))

            # Bỏ qua tin nhắn của người dùng trong danh sách skip
            if owner_id in skip_user_ids:
                continue

            # Xử lý tin nhắn ảnh (chat.photo)
            if getattr(msg, 'msgType', '') == 'chat.photo' and isinstance(getattr(msg, 'content', None), dict):
                content_dict = getattr(msg, 'content', {})
                image_url = content_dict.get('href', '')
                if image_url:
                    try:
                        message_object = msg
                        datascan = scan_qr_and_get_result(image_url, group_id, client, message_object)
                        if datascan and is_link(datascan):
                            contains_link = True
                    except Exception as e:
                        print(f"Lỗi khi quét mã QR từ ảnh: {str(e)}")
                        continue
                else:
                    continue

            # Xử lý tin nhắn chat.recommended
            elif getattr(msg, 'msgType', '') == 'chat.recommended' and isinstance(getattr(msg, 'content', None), dict):
                content_dict = getattr(msg, 'content', {})
                for key, value in content_dict.items():
                    if isinstance(value, str) and is_link(value):
                        contains_link = True
                        break

            # Xử lý tin nhắn video (chat.video.msg)
            elif getattr(msg, 'msgType', '') == 'chat.video.msg' and isinstance(getattr(msg, 'content', None), dict):
                content_dict = getattr(msg, 'content', {})
                title = content_dict.get('title', '')
                if isinstance(title, str) and is_link(title):
                    contains_link = True

            # Xử lý tin nhắn văn bản
            else:
                msg_content = getattr(msg, 'content', getattr(msg, 'msg', None))
                if isinstance(msg_content, str) and is_link(msg_content):
                    contains_link = True

            if not contains_link:
                continue

            # Xóa tin nhắn nếu phát hiện link
            try:
                msg_id = getattr(msg, 'msgId', getattr(msg, 'globalMsgId', None))
                owner_id = getattr(msg, 'uidFrom', getattr(msg, 'ownerId', None))
                cli_msg_id = getattr(msg, 'cliMsgId', None)
                client.deleteGroupMsg(
                    msgId=msg_id,
                    ownerId=owner_id,
                    clientMsgId=cli_msg_id,
                    groupId=group_id
                )
                print(f"Đã xóa tin nhắn chứa link trong nhóm {group_name} (ID: {group_id}), MsgID: {msg_id}")
                time.sleep(0.5)
            except Exception as e:
                print(f"Lỗi khi xóa tin nhắn trong nhóm {group_name} (ID: {group_id}), MsgID: {msg_id}: {str(e)}")

    except Exception as e:
        print(f"Lỗi khi lấy tin nhắn từ nhóm {group_name} (ID: {group_id}): {str(e)}")

def check_groups_for_links(client):
    """
    Kiểm tra từng nhóm trong danh sách và xóa các tin nhắn chứa link.
    """
    groups = load_group_list()
    if not groups:
        logger.info("Danh sách nhóm trống.")
        return

    for group in groups:
        group_id = group.get("group_id")
        group_name = group.get("group_name", "Unknown")
        if group_id:
            logger.info(f"Đang kiểm tra nhóm {group_name} (ID: {group_id})...")
            fetch_and_delete_links(client, group_id, group_name)
        time.sleep(1)  # Nghỉ ngắn giữa các nhóm để tránh quá tải API

def schedule_link_check(client):
    """
    Lên lịch kiểm tra và xóa link mỗi 15 phút, dừng khi trạng thái is_running = False.
    """
    while load_status():
        logger.info("Bắt đầu kiểm tra các nhóm...")
        check_groups_for_links(client)
        logger.info("Hoàn tất kiểm tra. Nghỉ 15 phút...")
        time.sleep(900)  # 15 phút = 900 giây
    logger.info("Đã dừng kiểm tra tự động theo trạng thái.")

def send_reply_with_style(client, text, message_object, thread_id, thread_type, ttl=30000, color="#000000"):
    """
    Gửi tin nhắn phản hồi với định dạng màu sắc và in đậm.
    """
    base_length = len(text)
    adjusted_length = base_length + 355
    style = MultiMsgStyle([
        MessageStyle(
            offset=0,
            length=adjusted_length,
            style="color",
            color=color,
            auto_format=False
        ),
        MessageStyle(
            offset=0,
            length=adjusted_length,
            style="bold",
            size="8",
            auto_format=False
        )
    ])
    msg = Message(text=text, style=style)
    try:
        client.replyMessage(msg, message_object, thread_id, thread_type, ttl=ttl)
    except Exception as e:
        logger.error(f"Lỗi khi gửi tin nhắn phản hồi: {str(e)}")

def fetch_group_info(target_input, message_object, client, command_prefix, thread_id):
    """
    Xác định group_id từ tag, tham số nhập, hoặc thread_id nếu không có tham số.
    Trả về tuple (group_id, group_name) hoặc None nếu có lỗi.
    """
    if message_object.mentions and len(message_object.mentions) > 0:
        group_id = message_object.mentions[0]['uid']
    else:
        group_id = target_input.strip() if target_input.strip() else thread_id
    if not group_id:
        return None
    try:
        group_info = client.fetchGroupInfo(group_id)
        group = group_info.gridInfoMap[group_id]
        group_name = group.name
        return group_id, group_name
    except Exception as e:
        logger.error(f"Lỗi fetch thông tin cho group {group_id}: {e}")
        return None

def handle_addgroup_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản hồi emoji "✅" xác nhận đã nhận lệnh
    action = "✅ "
    try:
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    except Exception as e:
        logger.error(f"Lỗi khi gửi reaction: {str(e)}")
    """
    Xử lý lệnh thêm nhiều nhóm vào danh sách kiểm tra link.
    Cú pháp: addchecklinkgroup <group_id1>\n<group_id2>\n... hoặc tag nhóm, hoặc không nhập để lấy nhóm hiện tại
    """
    if author_id != ADMIN:
        error_msg = Message(text="❌ Chỉ admin mới có quyền sử dụng lệnh này.")
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    command_prefix = "checklink.addgroup"
    param = message[len(command_prefix):].strip()

    # Tách danh sách group_id từ param (mỗi ID trên một dòng)
    group_ids = [gid.strip() for gid in param.split("\n") if gid.strip()] if param else []
    if not group_ids and message_object.mentions and len(message_object.mentions) > 0:
        group_ids = [message_object.mentions[0]['uid']]
    elif not group_ids:
        group_ids = [thread_id]  # Dùng thread_id hiện tại nếu không có tham số

    if not group_ids:
        error_msg = Message(text=f"Cú pháp: {PREFIX}checklink.addgroup <group_id1>\\n<group_id2>\\n... hoặc tag nhóm.")
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    added_groups = []
    failed_groups = []

    for group_id in group_ids:
        try:
            group_info = client.fetchGroupInfo(group_id)
            group = group_info.gridInfoMap[group_id]
            group_name = group.name
            if add_group(group_id, group_name):
                added_groups.append(f"👥 {group_name} (🆔 {group_id})")
            else:
                failed_groups.append(f"⚠️ {group_name} (🆔 {group_id}): Đã tồn tại")
            time.sleep(0.5)  # Delay để tránh rate limit
        except Exception as e:
            logger.error(f"Lỗi fetch thông tin cho group {group_id}: {e}")
            failed_groups.append(f"❌ {group_id}: Không thể lấy thông tin nhóm ({str(e)})")
            time.sleep(0.5)  # Delay ngay cả khi lỗi để tránh spam API

    # Tạo phản hồi
    reply_text = "Kết quả thêm nhóm:\n"
    if added_groups:
        reply_text += "✅ Đã thêm:\n" + "\n".join(added_groups) + "\n"
    if failed_groups:
        reply_text += "🚫 Thất bại:\n" + "\n".join(failed_groups)
    if not added_groups and not failed_groups:
        reply_text = "⚠️ Không có nhóm nào được thêm."

    send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=30000)

def handle_delgroup_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản hồi emoji "✅" xác nhận đã nhận lệnh
    action = "✅ "
    try:
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    except Exception as e:
        logger.error(f"Lỗi khi gửi reaction: {str(e)}")
    """
    Xử lý lệnh xóa nhóm khỏi danh sách kiểm tra link.
    Cú pháp: delchecklinkgroup <group_id> hoặc tag nhóm, hoặc không nhập để lấy nhóm hiện tại
    """
    if author_id != ADMIN:
        error_msg = Message(text="❌ Chỉ admin mới có quyền sử dụng lệnh này.")
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    command_prefix = "checklink.delgroup"
    param = message[len(command_prefix):].strip()
    group = fetch_group_info(param, message_object, client, command_prefix, thread_id)
    if group is None:
        error_msg = Message(text=f"Cú pháp: {PREFIX}checklink.delgroup <group_id> hoặc tag nhóm.\nKhông thể lấy thông tin nhóm.")
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    group_id, group_name = group

    if remove_group(group_id):
        reply_text = f"❌ Đã xóa nhóm:\n👥 {group_name}\n🆔 {group_id}\n khỏi danh sách kiểm tra link."
    else:
        reply_text = f"⚠️ Nhóm với ID: {group_id} không tồn tại trong danh sách."
    send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=30000)

def handle_listgroup_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản hồi emoji "✅" xác nhận đã nhận lệnh
    action = "✅ "
    try:
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    except Exception as e:
        logger.error(f"Lỗi khi gửi reaction: {str(e)}")
    """
    Xử lý lệnh xem danh sách nhóm kiểm tra link.
    Cú pháp: listchecklinkgroup
    """
    if author_id != ADMIN:
        error_msg = Message(text="❌ Chỉ admin mới có quyền sử dụng lệnh này.")
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    group_list = list_groups()
    if not group_list:
        reply_text = "Danh sách nhóm kiểm tra link trống."
    else:
        reply_text = "Danh sách nhóm kiểm tra link:\n" + "\n".join(
            [f"{i+1}.   {grp['group_name']}\n🆔 {grp['group_id']}" for i, grp in enumerate(group_list)]
        )
    send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=30000)

def handle_startlinkcheck_command(message, message_object, thread_id, thread_type, author_id, client):
    action = "✅ "
    try:
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    except Exception as e:
        logger.error(f"Lỗi khi gửi reaction: {str(e)}")

    if author_id != ADMIN:
        error_msg = Message(text="❌ Chỉ admin mới có quyền sử dụng lệnh này.")
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    if load_status():
        reply_text = "⚠️ Kiểm tra link tự động đã được kích hoạt. Không cần chạy lại."
        send_reply_with_style(client, reply_text, message_object, thread_id, thread_type)
        return

    save_status(True)
    if not hasattr(client, 'link_check_thread') or not client.link_check_thread.is_alive():
        client.link_check_thread = threading.Thread(target=schedule_link_check, args=(client,), daemon=True)
        client.link_check_thread.start()
    
    reply_text = "✅ Đã bắt đầu kiểm tra và xóa link trong các nhóm. Kiểm tra mỗi 15 phút."
    send_reply_with_style(client, reply_text, message_object, thread_id, thread_type)

def handle_stoplinkcheck_command(message, message_object, thread_id, thread_type, author_id, client):
    action = "✅ "
    try:
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    except Exception as e:
        logger.error(f"Lỗi khi gửi reaction: {str(e)}")

    if author_id != ADMIN:
        error_msg = Message(text="❌ Chỉ admin mới có quyền sử dụng lệnh này.")
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    if not load_status():
        reply_text = "⚠️ Không có quá trình kiểm tra link nào đang chạy."
        send_reply_with_style(client, reply_text, message_object, thread_id, thread_type)
        return

    save_status(False)
    reply_text = "ℹ️ Kiểm tra link tự động sẽ dừng sau tối đa 15 phút (khi vòng lặp hiện tại hoàn tất)."
    send_reply_with_style(client, reply_text, message_object, thread_id, thread_type)

def handle_checklinknow_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản hồi emoji "✅" xác nhận đã nhận lệnh
    action = "✅ "
    try:
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    except Exception as e:
        logger.error(f"Lỗi khi gửi reaction: {str(e)}")

    """
    Xử lý lệnh kiểm tra và xóa link ngay lập tức trong nhóm hiện tại hoặc nhóm được chỉ định.
    Cú pháp: checklinknow [group_id] hoặc tag nhóm, hoặc không nhập để lấy nhóm hiện tại
    """
    if author_id != ADMIN:
        error_msg = Message(text="❌ Chỉ admin mới có quyền sử dụng lệnh này.")
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    command_prefix = "checklink.now"
    param = message[len(command_prefix):].strip()
    group = fetch_group_info(param, message_object, client, command_prefix, thread_id)
    if group is None:
        error_msg = Message(text=f"Cú pháp: {PREFIX}checklinknow [group_id] hoặc tag nhóm.\nKhông thể lấy thông tin nhóm.")
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    group_id, group_name = group

    # Kiểm tra và xóa link, đếm số link đã xóa
    deleted_count = 0
    try:
        group_data = client.getRecentGroup(group_id)
        messages = group_data.groupMsgs if hasattr(group_data, 'groupMsgs') else []
        logger.info(f"Số tin nhắn lấy được từ nhóm {group_name} (ID: {group_id}): {len(messages)}")
        for msg in messages:
            msg_content = None

            # Xử lý content dựa trên msgType
            if getattr(msg, 'msgType', '') in ['chat.recommended', 'chat.photo'] and isinstance(getattr(msg, 'content', None), dict):
                content_dict = getattr(msg, 'content', {})
                for key, value in content_dict.items():
                    if isinstance(value, str) and is_link(value):
                        msg_content = value
                        break
            else:
                msg_content = getattr(msg, 'content', getattr(msg, 'msg', None))

            if not msg_content or not isinstance(msg_content, str):
                continue

            if is_link(msg_content):
                try:
                    client.deleteGroupMsg(
                        msgId=getattr(msg, 'msgId', getattr(msg, 'globalMsgId', None)),
                        ownerId=getattr(msg, 'uidFrom', getattr(msg, 'ownerId', None)),
                        clientMsgId=getattr(msg, 'cliMsgId', None),
                        groupId=group_id
                    )
                    deleted_count += 1
                    logger.info(f"Đã xóa tin nhắn chứa link trong nhóm {group_name} (ID: {group_id}), MsgID: {getattr(msg, 'msgId', getattr(msg, 'globalMsgId', None))}")
                    time.sleep(0.5)
                except Exception as e:
                    print(f"Lỗi khi xóa tin nhắn trong nhóm {group_name} (ID: {group_id}), MsgID: {getattr(msg, 'msgId', getattr(msg, 'globalMsgId', None))}: {str(e)}")
    except Exception as e:
        print(f"Lỗi khi lấy tin nhắn từ nhóm {group_name} (ID: {group_id}): {str(e)}")
        reply_text = f"❌ Lỗi khi kiểm tra nhóm {group_name} (ID: {group_id}): {str(e)}"
        send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=30000)
        return

    # Gửi thông báo hoàn tất
    reply_text = f"✅ Kiểm tra hoàn tất trong nhóm {group_name} (ID: {group_id}).\nSố link đã xóa: {deleted_count}."
    send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=30000)
    
def handle_skip_user_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản hồi emoji "✅" xác nhận đã nhận lệnh
    action = "✅ "
    try:
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    except Exception as e:
        logger.error(f"Lỗi khi gửi reaction: {str(e)}")
    """
    Xử lý lệnh thêm nhiều người dùng vào danh sách bỏ qua.
    Cú pháp: checklink.skip @user1 @user2 ... hoặc checklink.skip id1 id2 ...
    """
    if author_id != ADMIN:
        error_msg = Message(text="❌ Chỉ admin mới có quyền sử dụng lệnh này.")
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    command_prefix = "checklink.skip"
    param = message[len(command_prefix):].strip()
    
    # Lấy danh sách user_id từ mentions hoặc tham số
    user_ids = []
    if message_object.mentions and len(message_object.mentions) > 0:
        user_ids = [mention['uid'] for mention in message_object.mentions]
    elif param:
        user_ids = [uid.strip() for uid in param.split() if uid.strip()]
    
    if not user_ids:
        error_msg = Message(text=f"Cú pháp: {PREFIX}checklink.skip @user1 @user2 ... hoặc {PREFIX}checklink.skip id1 id2 ...")
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    added_users = []
    failed_users = []

    for user_id in user_ids:
        try:
            user_info_response = client.fetchUserInfo(user_id)
            profiles = user_info_response.unchanged_profiles or user_info_response.changed_profiles
            if not profiles or str(user_id) not in profiles:
                logger.error(f"Không thể lấy thông tin người dùng {user_id}: Không có dữ liệu trong profiles")
                failed_users.append(f"❌ ID: {user_id}: Không thể lấy thông tin người dùng")
                continue

            user_info = profiles[str(user_id)]
            user_name = getattr(user_info, 'zaloName', 'Không xác định')
            if not user_name or user_name == 'Không xác định':
                user_name = getattr(user_info, 'displayName', f"User_{user_id}")

            if add_skip_user(user_id, user_name):
                added_users.append(f"👤 {user_name} (🆔 {user_id})")
            else:
                failed_users.append(f"⚠️ {user_name} (🆔 {user_id}): Đã tồn tại trong danh sách bỏ qua")
            time.sleep(0.5)  # Delay để tránh rate limit
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin người dùng {user_id}: {str(e)}")
            failed_users.append(f"❌ ID: {user_id}: Lỗi ({str(e)})")

    # Tạo phản hồi
    reply_text = "Kết quả thêm người dùng vào danh sách bỏ qua:\n"
    if added_users:
        reply_text += "✅ Đã thêm:\n" + "\n".join(added_users) + "\n"
    if failed_users:
        reply_text += "🚫 Thất bại:\n" + "\n".join(failed_users)
    if not added_users and not failed_users:
        reply_text = "⚠️ Không có người dùng nào được thêm."

    send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=30000)

def handle_remove_user_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản hồi emoji "✅" xác nhận đã nhận lệnh
    action = "✅ "
    try:
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    except Exception as e:
        logger.error(f"Lỗi khi gửi reaction: {str(e)}")
    """
    Xử lý lệnh xóa nhiều người dùng khỏi danh sách bỏ qua.
    Cú pháp: checklink.remove @user1 @user2 ... hoặc checklink.remove id1 id2 ...
    """
    if author_id != ADMIN:
        error_msg = Message(text="❌ Chỉ admin mới có quyền sử dụng lệnh này.")
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    command_prefix = "checklink.remove"
    param = message[len(command_prefix):].strip()
    
    # Lấy danh sách user_id từ mentions hoặc tham số
    user_ids = []
    if message_object.mentions and len(message_object.mentions) > 0:
        user_ids = [mention['uid'] for mention in message_object.mentions]
    elif param:
        user_ids = [uid.strip() for uid in param.split() if uid.strip()]
    
    if not user_ids:
        error_msg = Message(text=f"Cú pháp: {PREFIX}checklink.remove @user1 @user2 ... hoặc {PREFIX}checklink.remove id1 id2 ...")
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    removed_users = []
    failed_users = []

    for user_id in user_ids:
        try:
            user_info_response = client.fetchUserInfo(user_id)
            profiles = user_info_response.unchanged_profiles or user_info_response.changed_profiles
            if not profiles or str(user_id) not in profiles:
                logger.error(f"Không thể lấy thông tin người dùng {user_id}: Không có dữ liệu trong profiles")
                failed_users.append(f"❌ ID: {user_id}: Không thể lấy thông tin người dùng")
                continue

            user_info = profiles[str(user_id)]
            user_name = getattr(user_info, 'zaloName', 'Không xác định')
            if not user_name or user_name == 'Không xác định':
                user_name = getattr(user_info, 'displayName', f"User_{user_id}")

            if remove_skip_user(user_id):
                removed_users.append(f"👤 {user_name} (🆔 {user_id})")
            else:
                failed_users.append(f"⚠️ {user_name} (🆔 {user_id}): Không tồn tại trong danh sách bỏ qua")
            time.sleep(0.5)  # Delay để tránh rate limit
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin người dùng {user_id}: {str(e)}")
            failed_users.append(f"❌ ID: {user_id}: Lỗi ({str(e)})")

    # Tạo phản hồi
    reply_text = "Kết quả xóa người dùng khỏi danh sách bỏ qua:\n"
    if removed_users:
        reply_text += "✅ Đã xóa:\n" + "\n".join(removed_users) + "\n"
    if failed_users:
        reply_text += "🚫 Thất bại:\n" + "\n".join(failed_users)
    if not removed_users and not failed_users:
        reply_text = "⚠️ Không có người dùng nào được xóa."

    send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=30000)

def handle_list_users_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản hồi emoji "✅" xác nhận đã nhận lệnh
    action = "✅ "
    try:
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    except Exception as e:
        logger.error(f"Lỗi khi gửi reaction: {str(e)}")
    """
    Xử lý lệnh xem danh sách người dùng bỏ qua.
    Cú pháp: checklink.list
    """
    if author_id != ADMIN:
        error_msg = Message(text="❌ Chỉ admin mới có quyền sử dụng lệnh này.")
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    user_list = list_skip_users()
    if not user_list:
        reply_text = "Danh sách người dùng bỏ qua trống."
    else:
        reply_text = "Danh sách người dùng bỏ qua:\n" + "\n".join(
            [f"{i+1}. 👤 {user['user_name']}\n🆔 {user['user_id']}" for i, user in enumerate(user_list)]
        )
    send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=30000)
    
STATUS_FILE = "data/link_checker_status.json"

def load_status():
    """
    Tải trạng thái từ file JSON.
    Trả về True nếu bot đang chạy, False nếu không.
    """
    if not os.path.exists(STATUS_FILE):
        return False
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("is_running", False)
    except Exception as e:
        logger.error(f"Lỗi tải trạng thái từ {STATUS_FILE}: {str(e)}")
        return False

def save_status(is_running):
    """
    Lưu trạng thái vào file JSON.
    """
    try:
        os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)  # Tạo thư mục 'data' nếu chưa có
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump({"is_running": is_running}, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Lỗi lưu trạng thái vào {STATUS_FILE}: {str(e)}")

def initialize_status_file():
    """
    Khởi tạo tệp trạng thái nếu chưa tồn tại.
    """
    if not os.path.exists(STATUS_FILE):
        save_status(False)
        logger.info(f"Đã tạo tệp {STATUS_FILE} với trạng thái mặc định: is_running = False")

def initialize_link_checker(client):
    """
    Khởi động kiểm tra liên kết dựa trên trạng thái đã lưu.
    """
    initialize_status_file()
    if load_status() and (not hasattr(client, 'link_check_thread') or not client.link_check_thread.is_alive()):
        client.link_check_thread = threading.Thread(target=schedule_link_check, args=(client,), daemon=True)
        client.link_check_thread.start()
        logger.info("Đã khôi phục kiểm tra link tự động từ trạng thái đã lưu.")  

def get_mitaizl():
    """
    Trả về dictionary ánh xạ lệnh tới các hàm xử lý tương ứng.
    """
    return {
        'checklink.addgroup': handle_addgroup_command,
        'checklink.delgroup': handle_delgroup_command,
        'checklink.listgroup': handle_listgroup_command,
        'checklink.start': handle_startlinkcheck_command,
        'checklink.stop': handle_stoplinkcheck_command,
        'checklink.now': handle_checklinknow_command,
        'checklink.skip': handle_skip_user_command,
        'checklink.remove': handle_remove_user_command,
        'checklink.list': handle_list_users_command
    }