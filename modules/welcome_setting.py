import json
import os
from zlapi.models import Message, MessageStyle, MultiMsgStyle
from config import ADMIN, PREFIX

# Mô tả lệnh
des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🚫 Quản lý danh sách nhóm bị loại khỏi sự kiện chào mừng trên Zalo.",
    'tính năng': [
        "➕ Thêm nhóm vào danh sách bị loại bằng ID hoặc tag nhóm.",
        "➖ Xóa nhóm khỏi danh sách bị loại với xác nhận chi tiết.",
        "📋 Liệt kê danh sách các nhóm bị loại với tên và ID.",
        "🔒 Chỉ admin được phép sử dụng các lệnh quản lý.",
        "💾 Lưu trữ danh sách bị loại trong file JSON với mã hóa UTF-8."
    ],
    'hướng dẫn sử dụng': [
        f"📩 Gửi lệnh {PREFIX}welcome off <group_id> hoặc tag nhóm để thêm vào danh sách bị loại.",
        f"📩 Gửi lệnh {PREFIX}welcome on <group_id> hoặc tag nhóm để xóa khỏi danh sách bị loại.",
        f"📩 Gửi lệnh {PREFIX}welcome list để xem danh sách các nhóm bị loại.",
        f"📌 Ví dụ: {PREFIX}welcome off 123456789 hoặc {PREFIX}welcome on @GroupName.",
        "✅ Nhận phản hồi với định dạng đẹp và TTL 30 giây."
    ]
}

# Đường dẫn file lưu trữ danh sách nhóm bị loại khỏi sự kiện chào mừng
EXCLUDED_EVENTS_FILE = "excluded_event.json"

def load_excluded_groups():
    """Tải dữ liệu từ file JSON chứa danh sách nhóm bị loại. Trả về danh sách rỗng nếu file không tồn tại hoặc lỗi."""
    if not os.path.exists(EXCLUDED_EVENTS_FILE):
        return []
    try:
        with open(EXCLUDED_EVENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Lỗi tải danh sách nhóm bị loại: {str(e)}")
        return []

def save_excluded_groups(excluded_groups):
    """Lưu danh sách nhóm bị loại vào file JSON với định dạng UTF-8."""
    with open(EXCLUDED_EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(excluded_groups, f, ensure_ascii=False, indent=4)

def add_excluded_group(group_id, group_name):
    """Thêm nhóm vào danh sách bị loại. Trả về True nếu thành công, False nếu group_id đã tồn tại."""
    excluded_groups = load_excluded_groups()
    for group in excluded_groups:
        if group.get("group_id") == group_id:
            return False
    excluded_groups.append({"group_id": group_id, "group_name": group_name})
    save_excluded_groups(excluded_groups)
    return True

def remove_excluded_group(group_id):
    """Xóa nhóm khỏi danh sách bị loại. Trả về True nếu xóa thành công, False nếu group_id không tồn tại."""
    excluded_groups = load_excluded_groups()
    for group in excluded_groups:
        if group.get("group_id") == group_id:
            excluded_groups.remove(group)
            save_excluded_groups(excluded_groups)
            return True
    return False

def list_excluded_groups():
    """Trả về danh sách nhóm bị loại khỏi sự kiện chào mừng."""
    return load_excluded_groups()

def send_reply_with_style(client, text, message_object, thread_id, thread_type, ttl=30000, color="#000000"):
    """Gửi tin nhắn phản hồi với định dạng màu sắc và in đậm."""
    base_length = len(text)
    adjusted_length = base_length + 355
    style = MultiMsgStyle([
        MessageStyle(offset=0, length=adjusted_length, style="color", color=color, auto_format=False),
        MessageStyle(offset=0, length=adjusted_length, style="bold", size="8", auto_format=False)
    ])
    msg = Message(text=text, style=style)
    client.replyMessage(msg, message_object, thread_id, thread_type, ttl=ttl)

def fetch_group_info(target_input, message_object, client, command_prefix):
    """
    Lấy group_id từ mentions, target_input, hoặc message_object.idTo.
    Trả về tuple (group_id, group_name) hoặc None nếu có lỗi.
    """
    if message_object.mentions and len(message_object.mentions) > 0:
        group_id = message_object.mentions[0]['uid']
    elif target_input:
        group_id = target_input.strip()
    else:
        group_id = message_object.idTo

    if not group_id:
        return None

    try:
        group_info = client.fetchGroupInfo(group_id)
        group = group_info.gridInfoMap[group_id]
        group_name = group.name
        return group_id, group_name
    except Exception as e:
        print(f"Lỗi fetch thông tin cho group {group_id}: {e}")
        return None

def handle_welcome_command(message, message_object, thread_id, thread_type, author_id, client):
    """
    Xử lý lệnh welcome với các hành động: on, off, list.
    
    Hỗ trợ:
      - welcome off <group_id> hoặc tag nhóm: Thêm nhóm vào danh sách bị loại.
      - welcome on <group_id> hoặc tag nhóm: Xóa nhóm khỏi danh sách bị loại.
      - welcome list: Hiển thị danh sách nhóm bị loại.
    
    Cách sử dụng:
      - Ví dụ: {PREFIX}welcome off 123456789
      - Hoặc: {PREFIX}welcome on @GroupName
      - Hoặc: {PREFIX}welcome list
    """
    if author_id not in ADMIN:
        error_msg = Message(text="❌ Chỉ admin mới có quyền sử dụng lệnh này.")
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    command_prefix = "welcome"
    parts = message[len(command_prefix):].strip().split(maxsplit=1)
    action = parts[0].lower() if parts else ""
    param = parts[1] if len(parts) > 1 else ""

    if action not in ["on", "off", "list"]:
        error_msg = Message(text=f"Cú pháp: {PREFIX}welcome [on|off|list] <group_id hoặc tag nhóm>.")
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    if action == "list":
        excluded_groups = list_excluded_groups()
        if not excluded_groups:
            reply_text = "Danh sách nhóm bị loại khỏi sự kiện chào mừng trống."
        else:
            reply_text = "Danh sách nhóm bị loại khỏi sự kiện chào mừng:\n" + "\n".join(
                [f"{i+1}.   {grp['group_name']}\n🆔 {grp['group_id']}" for i, grp in enumerate(excluded_groups)]
            )
        send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=120000)
        return

    group = fetch_group_info(param, message_object, client, command_prefix)
    if group is None:
        error_msg = Message(text=f"Cú pháp: {PREFIX}welcome {action} <group_id> hoặc tag nhóm.\nKhông thể lấy thông tin nhóm.")
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    group_id, group_name = group

    if action == "off":
        if add_excluded_group(group_id, group_name):
            reply_text = f"❌ Đã tắt chế độ Welcome cho nhóm:\n👥 {group_name}\n🆔 {group_id}"
        else:
            reply_text = f"⚠️ Nhóm: {group_name}\n🆔 {group_id}\n đã được tắt trước đó"
    elif action == "on":
        if remove_excluded_group(group_id):
            reply_text = f"✅ Đã bật chế độ Welcome cho nhóm:\n👥 {group_name}\n🆔 {group_id}"
        else:
            reply_text = f"⚠️ Nhóm với ID: {group_id} đã được bật trước đó"

    send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=120000)

def get_mitaizl():
    """
    Trả về dictionary ánh xạ lệnh tới hàm xử lý cho quản lý nhóm bị loại khỏi sự kiện chào mừng.
    
    Lệnh hỗ trợ:
      - welcome: Xử lý các hành động on, off, list.
    """
    return {
        'welcome': handle_welcome_command
    }