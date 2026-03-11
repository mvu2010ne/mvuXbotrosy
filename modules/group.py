from zlapi.models import Message, MultiMsgStyle, MessageStyle
from config import ADMIN, SUPER_ADMIN
import requests
import tempfile
import os
import time
import random
import math
import re
from io import BytesIO
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import logging


# Cấu hình logging cơ bản
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

HARD_CODED_ADMIN_IDS = [
    "1635171141414565734",  # ID của bot hoặc admin chính
    "1356230900980076549",  # ID admin 1
    "5303977902723514956",  # ID admin 2
    # Thêm các ID admin khác nếu cần
]

# Thông tin mô tả tập lệnh
des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Quản lý cài đặt nhóm với giao diện chào mừng tùy chỉnh.",
    'tính năng': [
        "⚙️ Bật/tắt các cài đặt nhóm như khóa tên, tin nhắn, khảo sát.",
        "📷 Tạo ảnh chào mừng với tên, avatar và thông tin nhóm.",
        "🔒 Chỉ admin có quyền sử dụng lệnh.",
        "📋 Hiển thị danh sách cài đặt hoặc thông tin nhóm.",
        "✅ Gửi phản ứng xác nhận và ảnh với TTL 30 giây."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh group <cài đặt> <on/off> để bật/tắt.",
        "📩 Gửi group active để xem trạng thái cài đặt.",
        "📩 Gửi group rename <tên> để đổi tên nhóm.",
        "📌 Ví dụ: group name on hoặc group info.",
        "✅ Nhận phản hồi hoặc ảnh chào mừng."
    ]
}

# Hàm tải ảnh từ URL
def download_image(url):
    """Tải ảnh từ URL và lưu vào file tạm."""
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        tmp_file.write(response.content)
        tmp_file.close()
        return tmp_file.name
    except Exception as e:
        logging.error(f"Lỗi tải ảnh từ {url}: {e}")
        raise Exception("Không thể tải ảnh từ URL.")

# Hàm gửi tin nhắn với kiểu dáng
def send_message_with_style(client, text, thread_id, thread_type, color="#db342e"):
    """Gửi tin nhắn với định dạng màu sắc."""
    base_length = len(text)
    adjusted_length = base_length + 1000
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
    try:
        client.sendMessage(Message(text=text, style=style), thread_id=thread_id, thread_type=thread_type, ttl=60000)
    except Exception as e:
        logging.error(f"Lỗi gửi tin nhắn: {e}")
        raise

# Hàm gửi tin nhắn lỗi
def send_error_message(client, thread_id, thread_type, message, color="#db342e"):
    """Gửi tin nhắn lỗi với định dạng màu sắc."""
    send_message_with_style(client, message, thread_id, thread_type, color)

# Kiểm tra quyền admin
def check_admin_permissions(creator_id, admin_ids, bot_id="127225959075940390"):
    """Kiểm tra xem bot có quyền admin trong nhóm hay không."""
    all_admin_ids = set(admin_ids)
    all_admin_ids.add(creator_id)
    all_admin_ids.update(ADMIN)
    all_admin_ids.update(HARD_CODED_ADMIN_IDS)  # Thêm danh sách ID admin phụ
    logging.info(f"Checking bot admin permissions: bot_id={bot_id}, all_admin_ids={all_admin_ids}")
    return bot_id in all_admin_ids

# Xác thực cài đặt
def validate_setting(setting):
    """Xác thực cài đặt hợp lệ và trả về tên cài đặt chuẩn hóa."""
    valid_settings = {
        "blockname": "blockName",
        "signadminmsg": "signAdminMsg",
        "addmemberonly": "addMemberOnly",
        "settopiconly": "setTopicOnly",
        "enablemsghistory": "enableMsgHistory",
        "lockcreatepost": "lockCreatePost",
        "lockcreatepoll": "lockCreatePoll",
        "joinappr": "joinAppr",
        "locksendmsg": "lockSendMsg",
        "lockviewmember": "lockViewMember",
        "lockgroup": "lockGroup",
        "listmembers": "listMembers",
        "groupinfo": "groupInfo"
    }
    return valid_settings.get(setting.lower())

# Hàm liệt kê trạng thái cài đặt
def handle_list_active_settings(thread_id, client):
    """Liệt kê trạng thái các cài đặt hiện tại của nhóm."""
    group_info = client.fetchGroupInfo(thread_id)
    if not group_info or thread_id not in group_info.gridInfoMap:
        return "Không thể lấy thông tin nhóm."
    group = group_info.gridInfoMap[thread_id]
    key_translation = {
        'blockName': '\n🚫 Thay đổi tên và ảnh đại diện của nhóm',
        'signAdminMsg': '\n✍️ Đánh dấu tin nhắn từ trưởng phó nhóm',
        'addMemberOnly': '\n👤 Chế độ duyệt thành viên mới',
        'setTopicOnly': '\n📝 Ghim tin nhắn, ghi chú, bình luận lên đầu hội thoại',
        'enableMsgHistory': '\n📜 Cho phép thành viên mới đọc tin nhắn gần nhất',
        'lockCreatePost': '\n🔒 Tạo mới ghi chú nhắc hẹn',
        'lockCreatePoll': '\n🔒 Tạo mới bình chọn',
        'joinAppr': '\n✅ Chế độ cấm',
        'lockSendMsg': '\n🔒 Gửi tin nhắn',
        'lockViewMember': '\n🔒 Chỉ trưởng phó cộng đồng được xem đầy đủ danh sách thành viên nhóm',
        'lockGroup': '\n🔒 Khóa toàn bộ nhóm'
    }
    settings = group.get("setting", {})
    config_string = ''.join([f"{key_translation.get(key, key)}: {'🟢' if value == 1 else '🔴'}" 
                             for key, value in settings.items()])
    return f"⚙️ Cài đặt nhóm:{config_string}\n"

# Các hàm xử lý cài đặt nhóm
def handle_block_name(action, thread_id, client):
    """Bật/tắt chế độ khóa thay đổi tên nhóm."""
    new_value = 1 if action == "on" else 0 if action == "off" else None
    if new_value is not None:
        try:
            client.changeGroupSetting(groupId=thread_id, blockName=new_value)
            return f"Đã {'bật' if new_value == 1 else 'tắt'} khóa tên nhóm thành công."
        except Exception as e:
            return f"Lỗi khi thay đổi cài đặt: {str(e)}"
    return "Hành động không hợp lệ. Vui lòng sử dụng 'on' hoặc 'off'."

def handle_sign_admin_msg(action, thread_id, client):
    """Bật/tắt ghi chú tin nhắn admin."""
    new_value = 1 if action == "on" else 0 if action == "off" else None
    if new_value is not None:
        try:
            client.changeGroupSetting(groupId=thread_id, signAdminMsg=new_value)
            return f"Đã {'bật' if new_value == 1 else 'tắt'} ghi chú admin thành công."
        except Exception as e:
            return f"Lỗi khi thay đổi cài đặt: {str(e)}"
    return "Hành động không hợp lệ. Vui lòng sử dụng 'on' hoặc 'off'."

def handle_add_member_only(action, thread_id, client):
    """Bật/tắt chế độ chỉ admin thêm thành viên."""
    new_value = 1 if action == "on" else 0 if action == "off" else None
    if new_value is not None:
        try:
            client.changeGroupSetting(groupId=thread_id, addMemberOnly=new_value)
            return f"Đã {'bật' if new_value == 1 else 'tắt'} chế độ chỉ admin thêm thành viên thành công."
        except Exception as e:
            return f"Lỗi khi thay đổi cài đặt: {str(e)}"
    return "Hành động không hợp lệ. Vui lòng sử dụng 'on' hoặc 'off'."

def handle_set_topic_only(action, thread_id, client):
    """Bật/tắt chế độ chỉ admin thay đổi chủ đề."""
    new_value = 1 if action == "on" else 0 if action == "off" else None
    if new_value is not None:
        try:
            client.changeGroupSetting(groupId=thread_id, setTopicOnly=new_value)
            return f"Đã {'bật' if new_value == 1 else 'tắt'} chế độ chỉ admin thay đổi chủ đề thành công."
        except Exception as e:
            return f"Lỗi khi thay đổi cài đặt: {str(e)}"
    return "Hành động không hợp lệ. Vui lòng sử dụng 'on' hoặc 'off'."

def handle_enable_msg_history(action, thread_id, client):
    """Bật/tắt lịch sử tin nhắn cho thành viên mới."""
    new_value = 1 if action == "on" else 0 if action == "off" else None
    if new_value is not None:
        try:
            client.changeGroupSetting(groupId=thread_id, enableMsgHistory=new_value)
            return f"Đã {'bật' if new_value == 1 else 'tắt'} lịch sử tin nhắn thành công."
        except Exception as e:
            return f"Lỗi khi thay đổi cài đặt: {str(e)}"
    return "Hành động không hợp lệ. Vui lòng sử dụng 'on' hoặc 'off'."

def handle_lock_create_post(action, thread_id, client):
    """Khóa/mở khóa tạo bài viết."""
    new_value = 1 if action == "on" else 0 if action == "off" else None
    if new_value is not None:
        try:
            client.changeGroupSetting(groupId=thread_id, lockCreatePost=new_value)
            return f"Đã {'bật' if new_value == 1 else 'tắt'} khóa tạo bài viết thành công."
        except Exception as e:
            return f"Lỗi khi thay đổi cài đặt: {str(e)}"
    return "Hành động không hợp lệ. Vui lòng sử dụng 'on' hoặc 'off'."

def handle_lock_create_poll(action, thread_id, client):
    """Khóa/mở khóa tạo khảo sát."""
    new_value = 1 if action == "on" else 0 if action == "off" else None
    if new_value is not None:
        try:
            client.changeGroupSetting(groupId=thread_id, lockCreatePoll=new_value)
            return f"Đã {'bật' if new_value == 1 else 'tắt'} khóa tạo khảo sát thành công."
        except Exception as e:
            return f"Lỗi khi thay đổi cài đặt: {str(e)}"
    return "Hành động không hợp lệ. Vui lòng sử dụng 'on' hoặc 'off'."

def handle_join_appr(action, thread_id, client):
    """Bật/tắt chế độ duyệt thành viên mới."""
    new_value = 1 if action == "on" else 0 if action == "off" else None
    if new_value is not None:
        try:
            client.changeGroupSetting(groupId=thread_id, joinAppr=new_value)
            return f"Đã {'bật' if new_value == 1 else 'tắt'} chế độ duyệt thành viên mới thành công."
        except Exception as e:
            return f"Lỗi khi thay đổi cài đặt: {str(e)}"
    return "Hành động không hợp lệ. Vui lòng sử dụng 'on' hoặc 'off'."

def handle_lock_send_msg(action, thread_id, client):
    """Khóa/mở khóa gửi tin nhắn."""
    new_value = 1 if action == "on" else 0 if action == "off" else None
    if new_value is not None:
        try:
            client.changeGroupSetting(groupId=thread_id, lockSendMsg=new_value)
            return f"Đã {'bật' if new_value == 1 else 'tắt'} khóa gửi tin nhắn thành công."
        except Exception as e:
            return f"Lỗi khi thay đổi cài đặt: {str(e)}"
    return "Hành động không hợp lệ. Vui lòng sử dụng 'on' hoặc 'off'."

def handle_lock_view_member(action, thread_id, client):
    """Khóa/mở khóa xem danh sách thành viên."""
    new_value = 1 if action == "on" else 0 if action == "off" else None
    if new_value is not None:
        try:
            client.changeGroupSetting(groupId=thread_id, lockViewMember=new_value)
            return f"Đã {'bật' if new_value == 1 else 'tắt'} khóa xem danh sách thành viên thành công."
        except Exception as e:
            return f"Lỗi khi thay đổi cài đặt: {str(e)}"
    return "Hành động không hợp lệ. Vui lòng sử dụng 'on' hoặc 'off'."

def handle_lock_group(action, thread_id, client):
    """Khóa/mở khóa toàn bộ nhóm."""
    new_value = 1 if action == "on" else 0 if action == "off" else None
    if new_value is not None:
        try:
            client.changeGroupSetting(groupId=thread_id, lockGroup=new_value)
            return f"Nhóm đã {'được khóa' if new_value == 1 else 'mở khóa'} thành công."
        except Exception as e:
            return f"Lỗi khi thay đổi cài đặt: {str(e)}"
    return "Hành động không hợp lệ. Vui lòng sử dụng 'on' hoặc 'off'."

def handle_list_members(thread_id, client):
    """Liệt kê danh sách thành viên trong nhóm."""
    group_info = client.fetchGroupInfo(thread_id)
    if not group_info or thread_id not in group_info.gridInfoMap:
        return "Không thể lấy thông tin nhóm."
    group_data = group_info.gridInfoMap[thread_id]
    members = group_data.get('members', [])
    if not members:
        return "Không có thành viên nào trong nhóm."
    member_list = "\n".join([f"{index}. {member.get('name', member.get('id', 'Không rõ'))}" 
                             for index, member in enumerate(members, start=1)])
    return f"Danh sách thành viên:\n{member_list}"

def handle_group_info(thread_id, client):
    """Hiển thị thông tin nhóm."""
    group_info = client.fetchGroupInfo(thread_id)
    if not group_info or thread_id not in group_info.gridInfoMap:
        return "Không thể lấy thông tin nhóm."
    group_data = group_info.gridInfoMap[thread_id]
    members_count = group_data.get('totalMember', 0)
    last_message = group_data.get('lastMessage', 'Không có tin nhắn gần đây.')
    msg = f"Thông tin nhóm:\n"
    msg += f"- Số lượng thành viên: {members_count}\n"
    msg += f"- Tin nhắn gần đây: {last_message}"
    return msg

def handle_change_group_name(new_group_name, thread_id, client):
    """Thay đổi tên nhóm."""
    if not new_group_name.strip():
        return "Tên nhóm không được để trống."
    try:
        client.changeGroupName(groupName=new_group_name, groupId=thread_id)
        return f"Đã thay đổi tên nhóm thành: {new_group_name}"
    except Exception as e:
        return f"Không thể thay đổi tên nhóm: {str(e)}"

def handle_change_group_avatar(new_avatar_path, thread_id, client):
    """Thay đổi ảnh đại diện nhóm."""
    if not new_avatar_path.strip():
        return "Đường dẫn ảnh không được để trống."
    try:
        # Kiểm tra kích thước ảnh
        with Image.open(new_avatar_path) as img:
            if img.width < 50 or img.height < 50:
                return "Ảnh quá nhỏ, cần ít nhất 50x50 pixel."
        client.changeGroupAvatar(filePath=new_avatar_path, groupId=thread_id)
        return "Đã thay đổi ảnh đại diện nhóm thành công."
    except Exception as e:
        return f"Không thể thay đổi ảnh đại diện nhóm: {str(e)}"

def handle_promote_member(member_ids, thread_id, client, author_id):
    """Nâng cấp thành viên thành admin. Chỉ SUPER_ADMIN được phép."""
    # Kiểm tra quyền SUPER_ADMIN
    if author_id not in SUPER_ADMIN:
        return "❌ Chỉ SUPER_ADMIN mới có quyền nâng cấp phó nhóm!"
    
    if not member_ids:
        return "Danh sách member_id không được để trống."
    
    # Lấy thông tin tên của từng thành viên
    member_names = []
    for member_id in member_ids:
        try:
            user_info = client.fetchUserInfo(member_id)
            # Lấy tên từ thông tin user
            if hasattr(user_info, 'changed_profiles') and member_id in user_info.changed_profiles:
                name = user_info.changed_profiles[member_id].zaloName
            elif hasattr(user_info, 'unchanged_profiles') and member_id in user_info.unchanged_profiles:
                name = user_info.unchanged_profiles[member_id].zaloName
            else:
                name = f"ID: {member_id}"
            member_names.append(name)
        except Exception as e:
            logging.error(f"Lỗi khi lấy thông tin user {member_id}: {e}")
            member_names.append(f"ID: {member_id}")
    
    try:
        client.addGroupAdmins(member_ids, thread_id)
        names_str = ", ".join([f"{name} ({id})" for name, id in zip(member_names, member_ids)])
        return f"✅ Đã nâng cấp thành công admin cho: {names_str}"
    except Exception as e:
        return f"❌ Không thể nâng cấp admin: {str(e)}"

def handle_demote_admin(member_ids, thread_id, client, author_id):
    """Hạ cấp admin thành thành viên thường. Chỉ SUPER_ADMIN được phép."""
    # Kiểm tra quyền SUPER_ADMIN
    if author_id not in SUPER_ADMIN:
        return "❌ Chỉ SUPER_ADMIN mới có quyền hạ cấp phó nhóm!"
    
    if not member_ids:
        return "Danh sách member_ids không được để trống."
    
    # Lấy thông tin tên của từng thành viên
    member_names = []
    for member_id in member_ids:
        try:
            user_info = client.fetchUserInfo(member_id)
            # Lấy tên từ thông tin user
            if hasattr(user_info, 'changed_profiles') and member_id in user_info.changed_profiles:
                name = user_info.changed_profiles[member_id].zaloName
            elif hasattr(user_info, 'unchanged_profiles') and member_id in user_info.unchanged_profiles:
                name = user_info.unchanged_profiles[member_id].zaloName
            else:
                name = f"ID: {member_id}"
            member_names.append(name)
        except Exception as e:
            logging.error(f"Lỗi khi lấy thông tin user {member_id}: {e}")
            member_names.append(f"ID: {member_id}")
    
    try:
        client.removeGroupAdmins(member_ids, thread_id)
        names_str = ", ".join([f"{name} ({id})" for name, id in zip(member_names, member_ids)])
        return f"✅ Đã hạ cấp thành công admin: {names_str}"
    except Exception as e:
        return f"❌ Không thể hạ cấp admin: {str(e)}"

def handle_change_group_owner(new_owner_id, thread_id, client, author_id):
    """Chuyển quyền sở hữu nhóm. Chỉ SUPER_ADMIN được phép."""
    # Kiểm tra quyền SUPER_ADMIN
    if author_id not in SUPER_ADMIN:
        return "❌ Chỉ SUPER_ADMIN mới có quyền chuyển quyền sở hữu nhóm!"
    
    if not new_owner_id.strip():
        return "Member ID không được để trống."
    
    # Lấy thông tin tên của thành viên mới
    try:
        user_info = client.fetchUserInfo(new_owner_id)
        # Lấy tên từ thông tin user
        if hasattr(user_info, 'changed_profiles') and new_owner_id in user_info.changed_profiles:
            new_owner_name = user_info.changed_profiles[new_owner_id].zaloName
        elif hasattr(user_info, 'unchanged_profiles') and new_owner_id in user_info.unchanged_profiles:
            new_owner_name = user_info.unchanged_profiles[new_owner_id].zaloName
        else:
            new_owner_name = f"ID: {new_owner_id}"
    except Exception as e:
        logging.error(f"Lỗi khi lấy thông tin user {new_owner_id}: {e}")
        new_owner_name = f"ID: {new_owner_id}"
    
    try:
        client.changeGroupOwner(newAdminId=new_owner_id, groupId=thread_id)
        return f"✅ Đã chuyển quyền sở hữu nhóm cho: {new_owner_name} ({new_owner_id})"
    except Exception as e:
        return f"❌ Không thể chuyển quyền sở hữu nhóm: {str(e)}"

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

def handle_blocked_members_list(message, message_object, thread_id, thread_type, author_id, client):
    """ Lấy danh sách tên và ID thành viên bị chặn trong nhóm. """
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
    
    try:
        result = client.get_blocked_members(thread_id)
        if not result["success"]:
            error_msg = f"Lỗi: {result['error_message']}"
            send_message_with_style(client, error_msg, thread_id, thread_type)
            return

        blocked_members = result["blocked_members"]["data"]["blocked_members"]
        total_blocked = len(blocked_members)
        if total_blocked == 0:
            send_message_with_style(client, "Không có thành viên nào bị chặn.", thread_id, thread_type)
            return

        msg = f"DANH SÁCH THÀNH VIÊN BỊ CHẶN:\nTổng số: {total_blocked}\n\n"
        for count, member in enumerate(blocked_members, 1):
            member_id = member.get("id")
            member_name = member.get("zaloName", "Không xác định")[:30] + "..." if len(member.get("zaloName", "")) > 30 else member.get("zaloName", "Không xác định")
            msg += f"{count}. Tên: {member_name}\n UID: {member_id}\n\n"

        send_long_message(client, msg, thread_id, thread_type, color="#000000")

    except Exception as e:
        error_msg = f"Lỗi: {e}"
        send_message_with_style(client, error_msg, thread_id, thread_type)

def handle_unblock_member(message, message_object, thread_id, thread_type, author_id, client):
    """ Mở chặn thành viên nhóm dựa trên UID. """
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)

    try:
        uids = message.split()[1:]  # Bỏ qua lệnh đầu tiên (group unblock)
        if not uids:
            send_message_with_style(client, "Vui lòng cung cấp UID của thành viên cần mở chặn.", thread_id, thread_type)
            return

        names = []
        for uid in uids:
            try:
                info_response = client.fetchUserInfo(uid)
                profiles = info_response.unchanged_profiles or info_response.changed_profiles
                info = profiles.get(str(uid))
                if info:
                    names.append(info.zaloName)
                else:
                    names.append("Không xác định")
            except Exception:
                names.append("Không xác định")

        result = client.remove_blocked_member(thread_id, uids)
        if result["success"]:
            success_msg = f"Đã mở chặn thành công: {', '.join(names)}"
            send_message_with_style(client, success_msg, thread_id, thread_type, color="#008000")
        else:
            error_msg = f"Lỗi khi mở chặn: {result['error_message']}"
            send_message_with_style(client, error_msg, thread_id, thread_type)
    except Exception as e:
        error_msg = f"Đã xảy ra lỗi khi mở chặn thành viên: {e}"
        send_message_with_style(client, error_msg, thread_id, thread_type)
        
# Hằng số và tài nguyên ảnh
MULTICOLOR_GRADIENT = [
    (255, 0, 0), (255, 165, 0), (255, 255, 0),
    (0, 255, 0), (0, 0, 255), (75, 0, 130), (148, 0, 211)
]

MULTICOLOR_GRADIENTS = [
    [(255, 0, 255), (255, 128, 255), (0, 255, 255), (128, 255, 255), (255, 0, 0), (255, 128, 128), (255, 255, 0), (128, 255, 0), (0, 255, 0)],
    [(255, 0, 0), (255, 85, 0), (255, 165, 0), (255, 210, 0), (255, 255, 0), (200, 255, 0), (0, 128, 0), (0, 200, 100), (255, 105, 180), (255, 50, 200), (0, 0, 255), (50, 50, 255), (75, 0, 130), (110, 0, 200), (148, 0, 211)],
    [(255, 182, 193), (255, 210, 220), (255, 240, 245), (230, 255, 255), (173, 216, 230), (200, 250, 250), (152, 251, 152), (180, 255, 170), (240, 230, 140), (255, 250, 180)],
    [(0, 255, 127), (0, 230, 150), (255, 200, 0), (255, 165, 0), (255, 69, 0), (255, 105, 180)],
    [(0, 191, 255), (0, 220, 255), (30, 144, 255), (100, 149, 237), (135, 206, 250)],
    [(255, 94, 77), (255, 160, 122), (255, 99, 71), (255, 215, 0), (255, 255, 0)],
    [(0, 255, 0), (34, 255, 34), (34, 139, 34), (50, 205, 50), (90, 230, 90), (144, 238, 144), (152, 251, 152), (180, 255, 180)],
    [(255, 140, 0), (255, 99, 71), (255, 69, 0), (220, 20, 60), (255, 20, 147)],
    [(0, 255, 255), (70, 130, 180), (0, 0, 255), (25, 25, 112)],
    [(0, 255, 0), (138, 43, 226), (0, 0, 255), (255, 182, 193), (255, 215, 0)],
    [(255, 223, 186), (255, 182, 193), (255, 160, 122), (255, 99, 71), (152, 251, 152), (173, 216, 230)],
    [(176, 196, 222), (135, 206, 250), (70, 130, 180), (25, 25, 112)],
    [(255, 200, 200), (255, 165, 150), (255, 255, 180), (200, 255, 180), (180, 255, 255), (180, 200, 255), (220, 180, 255)],
    [(152, 251, 152), (180, 255, 180), (220, 255, 200), (255, 230, 180), (255, 200, 150), (255, 165, 100)],
    [(255, 105, 180), (255, 120, 190), (255, 165, 200), (255, 200, 220), (255, 230, 240), (255, 250, 255)],
    [(0, 255, 127), (100, 255, 150), (150, 255, 180), (200, 255, 210), (220, 255, 230)],
    [(255, 0, 0), (255, 69, 0), (255, 140, 0), (255, 215, 0), (0, 255, 127), (0, 255, 255), (30, 144, 255)],
    [(0, 255, 127), (0, 191, 255), (123, 104, 238), (75, 0, 130)],
    [(75, 0, 130), (138, 43, 226), (148, 0, 211), (255, 20, 147), (255, 105, 180)]
]

OVERLAY_COLORS = [
    (255, 255, 255, 200), (255, 250, 250, 200), (240, 255, 255, 200), (255, 228, 196, 200),
    (255, 218, 185, 200), (255, 239, 213, 200), (255, 222, 173, 200), (255, 250, 205, 200),
    (250, 250, 210, 200), (255, 245, 238, 200), (240, 230, 140, 200), (230, 230, 250, 200),
    (216, 191, 216, 200), (221, 160, 221, 200), (255, 182, 193, 200), (255, 105, 180, 200),
    (255, 160, 122, 200), (255, 165, 0, 200), (255, 215, 0, 200), (173, 255, 47, 200),
    (144, 238, 144, 200), (152, 251, 152, 200), (127, 255, 212, 200), (0, 255, 255, 200),
    (135, 206, 250, 200), (176, 224, 230, 200), (30, 144, 255, 200), (100, 149, 237, 200),
    (238, 130, 238, 200), (255, 20, 147, 200)
]

BACKGROUND_FOLDER = 'wcmenu_backgrounds'
if os.path.isdir(BACKGROUND_FOLDER):
    BACKGROUND_IMAGES = [
        os.path.join(BACKGROUND_FOLDER, f)
        for f in os.listdir(BACKGROUND_FOLDER)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ]
else:
    BACKGROUND_IMAGES = []

def create_background_from_folder(width, height):
    """Chọn ảnh nền ngẫu nhiên từ thư mục."""
    if BACKGROUND_IMAGES:
        bg_path = random.choice(BACKGROUND_IMAGES)
        try:
            bg = Image.open(bg_path).convert("RGB")
            return bg.resize((width, height), Image.LANCZOS)
        except Exception as e:
            logging.error(f"Lỗi khi mở ảnh nền từ {bg_path}: {e}")
    return Image.new("RGB", (width, height), (130, 190, 255))

# Hàm hỗ trợ xử lý ảnh
_FONT_CACHE = {}
def get_font(font_path, size):
    """Load font với cache."""
    key = (font_path, size)
    if key not in _FONT_CACHE:
        try:
            _FONT_CACHE[key] = ImageFont.truetype(font_path, size)
        except Exception:
            _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]

def make_round_avatar(avatar):
    """Cắt avatar thành hình tròn."""
    avatar = ImageEnhance.Brightness(avatar).enhance(1.2)
    w, h = avatar.size
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, w, h), fill=255)
    round_img = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    round_img.paste(avatar, (0, 0), mask)
    return round_img

def get_gradient_color(colors, ratio):
    """Nội suy màu theo tỉ lệ."""
    if ratio <= 0:
        return colors[0]
    if ratio >= 1:
        return colors[-1]
    total_segments = len(colors) - 1
    seg = int(ratio * total_segments)
    seg_ratio = (ratio * total_segments) - seg
    c1, c2 = colors[seg], colors[seg + 1]
    return (
        int(c1[0]*(1 - seg_ratio) + c2[0]*seg_ratio),
        int(c1[1]*(1 - seg_ratio) + c2[1]*seg_ratio),
        int(c1[2]*(1 - seg_ratio) + c2[2]*seg_ratio)
    )

def add_multicolor_circle_border(image, colors, border_thickness=5):
    """Thêm viền tròn đa sắc."""
    w, h = image.size
    new_size = (w + 2 * border_thickness, h + 2 * border_thickness)
    border_img = Image.new("RGBA", new_size, (0, 0, 0, 0))
    draw_border = ImageDraw.Draw(border_img)
    cx, cy = new_size[0] / 2, new_size[1] / 2
    r = w / 2
    outer_r = r + border_thickness

    for angle in range(360):
        rad = math.radians(angle)
        inner_point = (cx + r * math.cos(rad), cy + r * math.sin(rad))
        outer_point = (cx + outer_r * math.cos(rad), cy + outer_r * math.sin(rad))
        color = get_gradient_color(colors, angle / 360.0)
        draw_border.line([inner_point, outer_point], fill=color, width=border_thickness)

    border_img.paste(image, (border_thickness, border_thickness), image)
    return border_img

def add_multicolor_rectangle_border(image, colors, border_thickness=10):
    """Thêm viền chữ nhật đa sắc."""
    new_w = image.width + 2 * border_thickness
    new_h = image.height + 2 * border_thickness
    border_img = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
    draw_b = ImageDraw.Draw(border_img)
    for x in range(new_w):
        color = get_gradient_color(colors, x / new_w)
        draw_b.line([(x, 0), (x, border_thickness - 1)], fill=color)
        draw_b.line([(x, new_h - border_thickness), (x, new_h - 1)], fill=color)
    for y in range(new_h):
        color = get_gradient_color(colors, y / new_h)
        draw_b.line([(0, y), (border_thickness - 1, y)], fill=color)
        draw_b.line([(new_w - border_thickness, y), (new_w - 1, y)], fill=color)

    border_img.paste(image, (border_thickness, border_thickness), image)
    return border_img

# Hiệu ứng chữ gradient
emoji_pattern = re.compile(
    "([\U0001F1E6-\U0001F1FF]{2}|[\U0001F600-\U0001F64F]|[\U0001F300-\U0001F5FF]|[\U0001F680-\U0001F6FF]|[\U0001F700-\U0001F77F]|[\U0001F780-\U0001F7FF]|[\U0001F800-\U0001F8FF]|[\U0001F900-\U0001F9FF]|[\U0001FA00-\U0001FA6F]|[\U0001FA70-\U0001FAFF]|[\u2600-\u26FF]|[\u2700-\u27BF]|[\u2300-\u23FF]|[\u2B00-\u2BFF]|\d\uFE0F?\u20E3|[#*]\uFE0F?\u20E3|[\U00013000-\U0001342F])",
    flags=re.UNICODE
)

def split_text_by_emoji(text):
    """Tách văn bản thành các đoạn (emoji và chữ thường)."""
    segments = []
    buffer = ""
    for ch in text:
        if emoji_pattern.match(ch):
            if buffer:
                segments.append((buffer, False))
                buffer = ""
            segments.append((ch, True))
        else:
            buffer += ch
    if buffer:
        segments.append((buffer, False))
    return segments

def get_mixed_text_width(draw, text, normal_font, emoji_font):
    """Tính chiều rộng của text hỗn hợp."""
    segments = split_text_by_emoji(text)
    total_width = 0
    for seg, is_emoji in segments:
        font = emoji_font if is_emoji else normal_font
        seg_bbox = draw.textbbox((0, 0), seg, font=font)
        total_width += seg_bbox[2] - seg_bbox[0]
    return total_width

def draw_mixed_gradient_text(draw, text, position, normal_font, emoji_font, gradient_colors, shadow_offset=(4, 4)):
    """Vẽ text với gradient hỗn hợp."""
    if not text:
        return
    segments = split_text_by_emoji(text)
    total_chars = sum(len(seg) for seg, _ in segments)
    color_list = [get_gradient_color(gradient_colors, i / (total_chars - 1) if total_chars > 1 else 0) for i in range(total_chars)]

    x, y = position
    shadow_color = (0, 0, 0)
    char_index = 0
    for seg, is_emoji in segments:
        current_font = emoji_font if is_emoji else normal_font
        for ch in seg:
            ch_color = color_list[char_index]
            draw.text((x + shadow_offset[0], y + shadow_offset[1]), ch, font=current_font, fill=shadow_color)
            draw.text((x, y), ch, font=current_font, fill=ch_color)
            bbox = draw.textbbox((0, 0), ch, font=current_font)
            x += bbox[2] - bbox[0]
            char_index += 1

# Tạo ảnh menu chào mừng
def create_gr_welcome_image(user_name, user_avatar_url, user_cover_url, bot_avatar_url, gr_text):
    WIDTH, HEIGHT = 1472, 800
    if user_cover_url and user_cover_url != "https://cover-talk.zadn.vn/default":
        try:
            resp = requests.get(user_cover_url, timeout=5)
            resp.raise_for_status()
            background = Image.open(BytesIO(resp.content)).convert("RGB").resize((WIDTH, HEIGHT), Image.LANCZOS)
        except Exception:
            background = create_background_from_folder(WIDTH, HEIGHT)
    else:
        background = create_background_from_folder(WIDTH, HEIGHT)
    base_img = background.convert("RGBA")

    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    overlay_height = 460
    rect_y0 = (HEIGHT - overlay_height) // 2
    rect_y1 = rect_y0 + overlay_height
    rect_x0, rect_x1 = 30, WIDTH - 30
    overlay_color = random.choice(OVERLAY_COLORS)
    draw_overlay.rounded_rectangle((rect_x0, rect_y0, rect_x1, rect_y1), radius=50, fill=overlay_color)
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=2))
    base_img.alpha_composite(overlay)

    def load_avatar(url):
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            av = Image.open(BytesIO(resp.content)).convert("RGBA")
            if av.size[0] < 50 or av.size[1] < 50:
                raise ValueError("Ảnh quá nhỏ")
            return av
        except Exception:
            return Image.new("RGBA", (150, 150), (200, 200, 200, 255))

    AVATAR_SIZE = 250
    user_avatar = load_avatar(user_avatar_url).resize((AVATAR_SIZE, AVATAR_SIZE), Image.LANCZOS)
    user_avatar = make_round_avatar(user_avatar)
    user_avatar = add_multicolor_circle_border(user_avatar, MULTICOLOR_GRADIENT, 4)
    ax = rect_x0 + 70
    ay = (HEIGHT - user_avatar.height) // 2
    base_img.alpha_composite(user_avatar, (ax, ay))

    if bot_avatar_url:
        bot_avatar = load_avatar(bot_avatar_url).resize((AVATAR_SIZE, AVATAR_SIZE), Image.LANCZOS)
        bot_avatar = make_round_avatar(bot_avatar)
        bot_avatar = add_multicolor_circle_border(bot_avatar, MULTICOLOR_GRADIENT, 4)
        bx = rect_x1 - AVATAR_SIZE - 70
        by = (HEIGHT - bot_avatar.height) // 2
        base_img.alpha_composite(bot_avatar, (bx, by))

    base_draw = ImageDraw.Draw(base_img)
    emoji_font_title = get_font("font/NotoEmoji-Bold.ttf", 100)
    emoji_font_60 = get_font("font/NotoEmoji-Bold.ttf", 60)
    emoji_font_50 = get_font("font/NotoEmoji-Bold.ttf", 50)
    font_title = get_font("font/Tapestry-Regular.ttf", 100)
    name_text = f"Chào {user_name}!"
    name_width = get_mixed_text_width(base_draw, name_text, font_title, emoji_font_title)
    x_name = rect_x0 + (rect_x1 - rect_x0 - name_width) // 2
    y_name = rect_y0 + 20
    draw_mixed_gradient_text(base_draw, name_text, (x_name, y_name), font_title, emoji_font_title, MULTICOLOR_GRADIENT)
    bbox_name = base_draw.textbbox((0, 0), name_text, font=font_title)
    name_h = bbox_name[3] - bbox_name[1]

    padding_between = 20
    start_y_custom = y_name + name_h + padding_between
    custom_texts = [
        {"text": "SETTING GROUP", "normal_font": get_font("font/Tapestry-Regular.ttf", 60), "emoji_font": emoji_font_60},
        {"text": "📌 Thay đổi cài đặt nhóm ", "normal_font": get_font("font/ChivoMono-VariableFont_wght.ttf", 50), "emoji_font": emoji_font_50},
        {"text": "Dành cho quản trị viên nhóm ", "normal_font": get_font("font/ChivoMono-VariableFont_wght.ttf", 50), "emoji_font": emoji_font_50}
    ]

    line_heights = [base_draw.textbbox((0, 0), item["text"], font=item["normal_font"])[3] - base_draw.textbbox((0, 0), item["text"], font=item["normal_font"])[1] for item in custom_texts]
    spacing = 40
    total_text_height = sum(line_heights) + spacing * (len(custom_texts) - 1)
    max_available_height = rect_y1 - start_y_custom - 20
    if total_text_height > max_available_height:
        spacing = max(5, (max_available_height - sum(line_heights)) // (len(custom_texts) - 1))

    gradients_for_text = random.sample(MULTICOLOR_GRADIENTS, len(custom_texts))
    current_y = start_y_custom
    for i, item in enumerate(custom_texts):
        text_width = get_mixed_text_width(base_draw, item["text"], item["normal_font"], item["emoji_font"])
        x_text = rect_x0 + (rect_x1 - rect_x0 - text_width) // 2
        draw_mixed_gradient_text(base_draw, item["text"], (x_text, current_y), item["normal_font"], item["emoji_font"], gradients_for_text[i])
        current_y += line_heights[i] + spacing

    final_image = add_multicolor_rectangle_border(base_img, MULTICOLOR_GRADIENT, 10).convert("RGB")
    image_path = "bott_welcome.jpg"
    final_image.save(image_path, quality=90)
    return image_path

def delete_file(file_path):
    """Xóa file tạm."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        logging.error(f"Lỗi khi xóa file {file_path}: {e}")

def split_message(menu_text, max_length=1000):
    """Chia tin nhắn thành nhiều phần."""
    lines = menu_text.splitlines()
    parts = []
    current_part = ""
    for line in lines:
        if len(current_part) + len(line) + 1 > max_length:
            if current_part:
                parts.append(current_part.strip())
            current_part = line
        else:
            current_part += line + "\n"
    if current_part:
        parts.append(current_part.strip())
    return parts

# Xử lý lệnh chính
def handle_group_setting_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh thay đổi cài đặt nhóm."""
    text = message.split()
    action_react = "✅"
    client.sendReaction(message_object, action_react, thread_id, thread_type, reactionType=75)

    if len(text) < 2:
        gr_text = """
══════════════════════════
Vui lòng sử dụng cú pháp: group <setting> <on/off> hoặc group <command> <params>.
══════════════════════════
## ⚙️ 1. Cài Đặt Bật/Tắt
══════════════════════════
   ➜ 𝗴𝗿𝗼𝘂𝗽 𝗱𝘀𝐓𝗵𝗮𝗻𝗵𝐕𝗶𝗲𝗻 𝗼𝗻/𝗼𝗳𝗳 - Xem danh sách thành viên  
   ➜ 𝗴𝗿𝗼𝘂𝗽 𝗱𝘂𝘆𝗲𝘁𝐌𝗲𝗺 𝗼𝗻/𝗼𝗳𝗳 - Phê duyệt thành viên mới  
   ➜ 𝗴𝗿𝗼𝘂𝗽 𝗱𝘂𝘆𝗲𝘁𝐓𝘃 𝗼𝗻/𝗼𝗳𝗳 - Chỉ cho phép thêm thành viên  
   ➜ 𝗴𝗿𝗼𝘂𝗽 𝗹𝗼𝗰𝗸𝐆𝗿𝗼𝘂𝗽 𝗼𝗻/𝗼𝗳𝗳 - Khóa/mở toàn bộ nhóm  
   ➜ 𝗴𝗿𝗼𝘂𝗽 𝗺𝘀𝗴 𝗼𝗻/𝗼𝗳𝗳 - Lịch sử tin nhắn nhóm  
   ➜ 𝗴𝗿𝗼𝘂𝗽 𝗻𝗮𝗺𝗲 𝗼𝗻/𝗼𝗳𝗳 - Thay đổi tên nhóm  
   ➜ 𝗴𝗿𝗼𝘂𝗽 𝗻𝗼𝘁𝗲 𝗼𝗻/𝗼𝗳𝗳 - Ghi chú cho admin  
   ➜ 𝗴𝗿𝗼𝘂𝗽 𝗽𝗼𝗹𝗹 𝗼𝗻/𝗼𝗳𝗳 - Tạo khảo sát  
   ➜ 𝗴𝗿𝗼𝘂𝗽 𝗽𝗼𝘀𝘁 𝗼𝗻/𝗼𝗳𝗳 - Tạo bài viết  
   ➜ 𝗴𝗿𝗼𝘂𝗽 𝘀𝗼𝘀 𝗼𝗻/𝗼𝗳𝗳 - Gửi tin nhắn  
   ➜ 𝗴𝗿𝗼𝘂𝗽 𝘁𝗵𝗲𝗺𝗲 𝗼𝗻/𝗼𝗳𝗳 - Thay đổi chủ đề nhóm  

══════════════════════════
## 🔧 2. Quản Lý Nhóm
══════════════════════════
   ➜ 𝗴𝗿𝗼𝘂𝗽 𝗮𝗰𝐓𝗶𝘃𝗲 - Xem trạng thái cài đặt  
   ➜ 𝗴𝗿𝗼𝘂𝗽 𝗮𝘃𝗮𝘁𝗮𝗿 <đường_dẫn_ảnh> - Đổi ảnh đại diện nhóm  
   ➜ 𝗴𝗿𝗼𝘂𝗽 𝗱𝗲𝐌𝗼𝘁𝗲 <member_id1> [member_id2] ... - Hạ cấp admin
   ➜ 𝗴𝗿𝗼𝘂𝗽 𝗯𝗹𝗼𝗰𝗸𝗲𝗱𝗹𝗶𝘀𝘁 - Xem danh sách thành viên bị chặn
   ➜ 𝗴𝗿𝗼𝘂𝗽 𝘂𝗻𝗯𝗹𝗼𝗰𝗸 <uid1> [uid2] ... - Mở chặn thành viên   
   ➜ 𝗴𝗿𝗼𝘂𝗽 𝗶𝗻𝗳𝗼 - Xem thông tin nhóm  
   ➜ 𝗴𝗿𝗼𝘂𝗽 𝗹𝗶𝘀𝘁𝐌𝗲𝗺𝗯𝗲𝗿𝘀 - Xem danh sách thành viên  
   ➜ 𝗴𝗿𝗼𝘂𝗽 𝗼𝘄𝗻𝗲𝗿 <member_id> - Chuyển quyền sở hữu nhóm  
   ➜ 𝗴𝗿𝗼𝘂𝗽 𝗽𝗿𝗼𝐌𝗼𝘁𝗲 <member_id1> [member_id2] ... - Nâng cấp admin  
   ➜ 𝗴𝗿𝗼𝘂𝗽 𝗿𝗲𝐍𝗮𝗺𝗲 <new_group_name> - Đổi tên nhóm  
══════════════════════════
"""
        try:
            user_info = client.fetchUserInfo(author_id)
            user_name = user_info.changed_profiles[author_id].zaloName
            user_avatar_url = user_info.changed_profiles[author_id].avatar
            user_cover_url = user_info.changed_profiles[author_id].cover
        except Exception:
            user_name = "Người dùng"
            user_avatar_url = ""
            user_cover_url = ""

        try:
            bot_uid = "690096475735933742"
            bot_info = client.fetchUserInfo(bot_uid)
            bot_avatar_url = bot_info.changed_profiles[bot_uid].avatar
        except Exception:
            bot_avatar_url = ""

        message_parts = split_message(gr_text, max_length=1400)
        image_path = create_gr_welcome_image(user_name, user_avatar_url, user_cover_url, bot_avatar_url, gr_text)

        try:
            for i, part in enumerate(message_parts):
                if i == 0:
                    client.sendLocalImage(
                        image_path,
                        thread_id=thread_id,
                        thread_type=thread_type,
                        message=Message(text=part),
                        ttl=30000,
                        width=1472,
                        height=800
                    )
                else:
                    client.sendMessage(
                        Message(text=part),
                        thread_id=thread_id,
                        thread_type=thread_type,
                        ttl=30000
                    )
                time.sleep(0.5)
        except Exception as e:
            logging.error(f"Lỗi khi gửi tin nhắn: {e}")
            send_error_message(client, thread_id, thread_type, "Không thể gửi menu.", color="#ff0000")
        finally:
            delete_file(image_path)
        return

    setting = text[1].lower()
    group_info = client.fetchGroupInfo(thread_id)
    if not group_info or thread_id not in group_info.gridInfoMap:
        send_error_message(client, thread_id, thread_type, "Không thể lấy thông tin nhóm.", color="#ff0000")
        return
    group_data = group_info.gridInfoMap[thread_id]
    creator_id = group_data.get('creatorId')
    admin_ids = group_data.get('adminIds', [])
    # Kiểm tra quyền của bot
    bot_id = "127225959075940390"  # Thay bằng ID bot thực tế nếu khác
    if not check_admin_permissions(creator_id, admin_ids, bot_id):
        send_error_message(client, thread_id, thread_type, "Bot không có quyền admin trong nhóm.", color="#ff0000")
        return

    if setting == "rename" and len(text) >= 3:
        new_group_name = ' '.join(text[2:])
        result_message = handle_change_group_name(new_group_name, thread_id, client)
        send_message_with_style(client, result_message, thread_id, thread_type, color="#00ff00")
        return

    if setting == "owner" and len(text) >= 3:
        new_owner_id = text[2]
        result_message = handle_change_group_owner(new_owner_id, thread_id, client)
        send_message_with_style(client, result_message, thread_id, thread_type, color="#00ff00")
        return

    if setting == "avatar" and len(text) >= 3:
        new_avatar_url = ' '.join(text[2:])
        local_avatar_path = None
        try:
            local_avatar_path = download_image(new_avatar_url)
            result_message = handle_change_group_avatar(local_avatar_path, thread_id, client)
        except Exception as e:
            result_message = f"Không thể sử dụng link ảnh: {str(e)}"
        finally:
            if local_avatar_path:
                delete_file(local_avatar_path)
        send_message_with_style(client, result_message, thread_id, thread_type, color="#00ff00")
        return

    if setting in ["promote", "demote"]:
        # Trích xuất member_ids từ mentions hoặc text
        member_ids = []
        
        # Kiểm tra mentions trong message_object
        if hasattr(message_object, 'mentions') and message_object.mentions:
            member_ids = [mention['uid'] for mention in message_object.mentions]
        
        # Nếu không có mentions, lấy từ text (bỏ qua lệnh "group promote/demote")
        if not member_ids and len(text) >= 3:
            member_ids = text[2:]
        
        # Kiểm tra nếu không có member_ids
        if not member_ids:
            send_error_message(client, thread_id, thread_type, 
                             "Vui lòng tag ít nhất một thành viên hoặc cung cấp member_id.\n" +
                             "Ví dụ: `group promote @user1 @user2` hoặc `group promote 123 456`", 
                             color="#ff0000")
            return
        
        # Thực hiện promote hoặc demote với kiểm tra SUPER_ADMIN
        if setting == "promote":
            result_message = handle_promote_member(member_ids, thread_id, client, author_id)
        else:  # demote
            result_message = handle_demote_admin(member_ids, thread_id, client, author_id)
        
        send_message_with_style(client, result_message, thread_id, thread_type, color="#00ff00" if "✅" in result_message else "#ff0000")
        return

    if setting == "active":
        result_message = handle_list_active_settings(thread_id, client)
        send_message_with_style(client, result_message, thread_id, thread_type, color="#15a85f")
        return
        
    if setting == "blockedlist":
        handle_blocked_members_list(message, message_object, thread_id, thread_type, author_id, client)
        return

    if setting == "unblock":
        handle_unblock_member(message, message_object, thread_id, thread_type, author_id, client)
        return    

    setting_action_map = {
        "name": handle_block_name,
        "note": handle_sign_admin_msg,
        "duyettv": handle_add_member_only,
        "theme": handle_set_topic_only,
        "msg": handle_enable_msg_history,
        "post": handle_lock_create_post,
        "poll": handle_lock_create_poll,
        "duyetmem": handle_join_appr,
        "sos": handle_lock_send_msg,
        "dsthanhvien": handle_lock_view_member,
        "lockgroup": handle_lock_group,
        "listmembers": handle_list_members,
        "info": handle_group_info,
        "blockedlist": handle_blocked_members_list,
        "unblock": handle_unblock_member
    }

    if setting not in setting_action_map:
        send_error_message(client, thread_id, thread_type, "Cài đặt không hợp lệ.", color="#ff0000")
        return

    no_action_commands = ["listmembers", "info", "active","blockedlist", "unblock" ]
    if setting in no_action_commands:
        result_message = setting_action_map[setting](thread_id, client)
    elif len(text) >= 3:
        action = text[2].lower()
        result_message = setting_action_map[setting](action, thread_id, client)
    else:
        send_error_message(client, thread_id, thread_type, "Thiếu tham số 'on' hoặc 'off' cho lệnh.", color="#ff0000")
        return

    send_message_with_style(client, result_message, thread_id, thread_type, color="#00ff00")

def get_mitaizl():
    """Trả về lệnh chính của tập lệnh."""
    return {'group': handle_group_setting_command}