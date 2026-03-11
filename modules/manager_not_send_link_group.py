import json
import os
import random
from zlapi.models import Message, MessageStyle, MultiMsgStyle
from config import ADMIN, PREFIX
import time

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Quản lý danh sách nhóm không gửi link trên Zalo",
    'tính năng': [
        "➜👥 Thêm nhóm vào danh sách quản lý với ID và tên nhóm.",
        "➜❌ Xóa nhóm khỏi danh sách quản lý dựa trên ID nhóm.",
        "➜📋 Hiển thị danh sách các nhóm đang được quản lý, bao gồm tên và ID nhóm.",
        "🔐 Lưu trữ thông tin nhóm an toàn trong file JSON với mã hóa UTF-8.",
        "🔔 Thông báo kết quả chi tiết (thành công hoặc lỗi) với định dạng màu sắc và in đậm."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh `addgroup <group_id>` để thêm một nhóm vào danh sách.",
        "📩 Gửi lệnh `addgroup` (không nhập ID) để thêm nhóm hiện tại.",
        "📩 Gửi lệnh `delgroup <group_id>` để xóa một nhóm khỏi danh sách.",
        "📩 Gửi lệnh `delgroup` (không nhập ID) để xóa nhóm hiện tại.",
        "📩 Gửi lệnh `listgroup` để xem toàn bộ danh sách nhóm đang quản lý.",
        "📌 Ví dụ: `addgroup 123456789` hoặc `addgroup`.",
        "✅ Nhận thông báo kết quả ngay lập tức với thông tin nhóm và trạng thái."
    ]
}

# Đường dẫn file lưu trữ danh sách nhóm
GROUP_FILE = "danhsachnhom.json"

def load_groups():
    """
    Tải dữ liệu từ file JSON chứa danh sách nhóm.
    Nếu file không tồn tại hoặc lỗi định dạng, trả về danh sách rỗng.
    """
    if not os.path.exists(GROUP_FILE):
        return []
    try:
        with open(GROUP_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Lỗi tải danh sách nhóm: {str(e)}")
        return []

def save_groups(groups):
    """Lưu danh sách nhóm vào file JSON với định dạng UTF-8."""
    with open(GROUP_FILE, "w", encoding="utf-8") as f:
        json.dump(groups, f, ensure_ascii=False, indent=4)

def add_group(group_id, group_name):
    """
    Thêm nhóm vào danh sách với thông tin tên và id.
    Trả về True nếu thêm thành công, False nếu group id đã tồn tại.
    """
    groups = load_groups()
    for group in groups:
        if group.get("group_id") == group_id:
            return False
    groups.append({"group_id": group_id, "group_name": group_name})
    save_groups(groups)
    return True

def remove_group(group_id):
    """
    Xóa nhóm khỏi danh sách.
    Trả về True nếu xóa thành công, False nếu group id không tồn tại.
    """
    groups = load_groups()
    for group in groups:
        if group.get("group_id") == group_id:
            groups.remove(group)
            save_groups(groups)
            return True
    return False

def list_groups():
    """Trả về danh sách nhóm."""
    return load_groups()

def send_reply_with_style(client, text, message_object, thread_id, thread_type, ttl=None, color="#db342e"):
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
            auto_format=False,
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
    if ttl is not None:
        client.replyMessage(msg, message_object, thread_id, thread_type, ttl=ttl)
    else:
        client.replyMessage(msg, message_object, thread_id, thread_type)

def handle_addgroup_command(message, message_object, thread_id, thread_type, author_id, client):
    """
    Xử lý lệnh thêm nhóm.
    Cú pháp: addgroup <group_id> hoặc addgroup (tự lấy thread_id)
    """
    command_prefix = "addgroup"
    content = message[len(command_prefix):].strip()
    
    if content:
        group_id_input = content.strip()
    else:
        # Không nhập group_id, lấy thread_id của nhóm hiện tại
        group_id_input = thread_id

    # Lấy thông tin nhóm dựa vào group_id_input
    try:
        group_info = client.fetchGroupInfo(group_id_input)
        group = group_info.gridInfoMap[group_id_input]
        group_name = group.name
    except Exception as e:
        reply_text = f"⚠️ Không thể lấy thông tin nhóm: {str(e)}"
        send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=120000, color="#ff0000")
        return

    if add_group(group_id_input, group_name):
        reply_text = f"✅ Đã thêm nhóm:\n👥 {group_name}\n🆔 {group_id_input}\n vào danh sách không gửi link"
    else:
        reply_text = f"⚠️ Nhóm:\n👥 {group_name}\n🆔 {group_id_input}\n đã tồn tại trong danh sách."
    send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=120000)

def handle_delgroup_command(message, message_object, thread_id, thread_type, author_id, client):
    """
    Xử lý lệnh xóa nhóm.
    Cú pháp: delgroup <group_id> hoặc delgroup (tự lấy thread_id)
    """
    command_prefix = "delgroup"
    content = message[len(command_prefix):].strip()
    
    if content:
        group_id_input = content.strip()
    else:
        # Không nhập group_id, lấy thread_id của nhóm hiện tại
        group_id_input = thread_id

    # Tìm tên nhóm từ danh sách đã lưu hoặc lấy thông tin nhóm
    group_name = None
    groups = list_groups()
    for grp in groups:
        if grp.get("group_id") == group_id_input:
            group_name = grp.get("group_name")
            break
    
    # Nếu không tìm thấy tên nhóm trong danh sách, thử lấy từ API
    if not group_name:
        try:
            group_info = client.fetchGroupInfo(group_id_input)
            group = group_info.gridInfoMap[group_id_input]
            group_name = group.name
        except Exception:
            group_name = group_id_input  # Nếu không lấy được, dùng ID làm tên

    if remove_group(group_id_input):
        reply_text = f"❌ Đã xóa nhóm:\n👥 {group_name}\n🆔 {group_id_input}\n khỏi danh sách không gửi link"
    else:
        reply_text = f"⚠️ Nhóm:\n👥 {group_name}\n🆔 {group_id_input}\n không tồn tại trong danh sách."
    send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=120000)

def handle_listgroup_command(message, message_object, thread_id, thread_type, author_id, client):
    """
    Xử lý lệnh xem danh sách nhóm.
    Cú pháp: listgroup
    Phân chia danh sách thành nhiều tin nhắn nếu quá dài, với độ trễ 1 giây giữa các tin nhắn.
    """
    groups = list_groups()
    if not groups:
        reply_text = "📭 Danh sách nhóm không gửi link trống."
        send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=120000)
        return

    # Giới hạn số nhóm mỗi tin nhắn (ví dụ: 10 nhóm mỗi tin nhắn)
    MAX_GROUPS_PER_MESSAGE = 10
    total_groups = len(groups)

    for start in range(0, total_groups, MAX_GROUPS_PER_MESSAGE):
        end = min(start + MAX_GROUPS_PER_MESSAGE, total_groups)
        group_subset = groups[start:end]
        reply_text = f"📋 Danh sách nhóm không gửi link ({start+1}-{end}/{total_groups}):\n" + "\n".join(
            [f"{i+1+start}. 👥 {grp['group_name']}\n    🆔 {grp['group_id']}" for i, grp in enumerate(group_subset)]
        )
        send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=120000)
        if start + MAX_GROUPS_PER_MESSAGE < total_groups:  # Only sleep if more messages follow
            time.sleep(1)  # Delay 1 second between messages

def get_mitaizl():
    """
    Trả về một dictionary ánh xạ lệnh tới các hàm xử lý tương ứng.
    """
    return {
        'addgroup': handle_addgroup_command,
        'delgroup': handle_delgroup_command,
        'listgroup': handle_listgroup_command
    }