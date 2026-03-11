from zlapi.models import Message, ZaloAPIException, Mention, MultiMention, ThreadType
from datetime import datetime
import json

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🔍 Quản lý và tìm kiếm thành viên trong nhóm.",
    'tính năng': [
        "📋 Lệnh group.finduser: Tìm và liệt kê thông tin thành viên theo tên hoặc viết tắt.",
        "🏷️ Lệnh group.findtag: Tag trực tiếp các thành viên khớp tên (yêu cầu quyền admin).",
        "✅ Kiểm tra quyền admin tự động cho lệnh group.findtag.",
        "⚠️ Thông báo lỗi chi tiết nếu không tìm thấy thành viên hoặc gặp vấn đề API."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh group.finduser <tên> để tìm thành viên trong nhóm.",
        "📩 Gửi lệnh group.findtag <tên> để tag thành viên khớp tên (chỉ admin).",
        "📌 Ví dụ: group.finduser Tèo hoặc findtag Nam.",
        "✅ Nhận danh sách thành viên hoặc tag trực tiếp trong nhóm."
    ]
}

# Hàm lấy danh sách thành viên từ nhóm
def get_group_members(client, thread_id, thread_type, message_object):
    try:
        # Lấy thông tin nhóm từ fetchGroupInfo
        group_info = client.fetchGroupInfo(thread_id).gridInfoMap.get(thread_id)
        if not group_info:
            return None, "Không thể lấy thông tin nhóm."
        
        # Lấy danh sách ID thành viên từ memVerList
        member_ids = group_info.get('memVerList', [])
        if not member_ids:
            return None, "Nhóm không có thành viên hoặc danh sách trống."

        # Lấy thông tin chi tiết của từng thành viên
        members = []
        for member_id in member_ids:
            # Loại bỏ hậu tố "_0" nếu có
            if isinstance(member_id, str) and member_id.endswith('_0'):
                member_id = member_id.rsplit('_', 1)[0]
            try:
                info = client.fetchUserInfo(member_id)
                info = info.unchanged_profiles or info.changed_profiles
                info = info.get(str(member_id))
                if info:
                    members.append({
                        'id': member_id,
                        'dName': info.zaloName,
                        'zaloName': info.zaloName  # Lưu tên đầy đủ để tìm kiếm chính xác
                    })
            except Exception as e:
                continue  # Bỏ qua nếu không lấy được thông tin của thành viên
        return members, None
    except ZaloAPIException as e:
        return None, f"Lỗi API: {str(e)}"
    except Exception as e:
        return None, f"Lỗi không xác định: {str(e)}"

# Hàm kiểm tra xem người dùng có phải là admin không
def is_admin(client, thread_id, author_id, message_object, thread_type):
    try:
        # Kiểm tra admin bằng ID cứng
        admin_id = "3299675674241805615"
        return str(author_id) == admin_id, None
    except Exception as e:
        return False, f"Lỗi không xác định: {str(e)}"

# Hàm xử lý lệnh 'find'
def handle_find(message, message_object, thread_id, thread_type, author_id, client):
    if thread_type != ThreadType.GROUP:
        client.replyMessage(Message(text="Lệnh này chỉ hoạt động trong nhóm."), message_object, thread_id, thread_type, ttl=60000)
        return

    parts = message.strip().split(" ", 1)
    if len(parts) < 2 or not parts[1].strip():
        client.replyMessage(Message(text="Nhập tên thành viên cần tìm.\nVí dụ: group.finduser Tèo"), message_object, thread_id, thread_type, ttl=60000)
        return

    search_term = parts[1].strip().lower()

    members, error = get_group_members(client, thread_id, thread_type, message_object)
    if error:
        client.replyMessage(Message(text=error), message_object, thread_id, thread_type, ttl=60000)
        return

    # Tìm thành viên khớp với từ khóa (ưu tiên khớp chính xác, sau đó khớp một phần)
    found_members = [
        member for member in members 
        if search_term == member['zaloName'].lower() or  # Khớp chính xác
        search_term in member['zaloName'].lower() or   # Khớp một phần
        search_term in "".join(c[0] for c in member['zaloName'].split()).lower()  # Khớp viết tắt
    ]

    if not found_members:
        client.replyMessage(
            Message(text=f"Không tìm thấy thành viên nào có tên chứa '{search_term}'."),
            message_object, thread_id, thread_type, ttl=86400000
        )
        return

    response_text = f"🔎 Danh sách thành viên '{search_term}' tìm thấy hoặc có tên gần giống:\n\n"
    for i, member in enumerate(found_members[:100], 1):  # Giới hạn 100 thành viên
        response_text += f"{i}.\n- Tên: {member['zaloName']}, ID: {member['id']}\n\n"
    client.replyMessage(Message(text=response_text), message_object, thread_id, thread_type, ttl=86400000)

# Hàm xử lý lệnh 'findtag'
def handle_findtag(message, message_object, thread_id, thread_type, author_id, client):
    if thread_type != ThreadType.GROUP:
        client.replyMessage(Message(text="Lệnh này chỉ hoạt động trong nhóm."), message_object, thread_id, thread_type, ttl=60000)
        return
    
    is_admin_user, error = is_admin(client, thread_id, author_id, message_object, thread_type)
    if error:
        client.replyMessage(Message(text=error), message_object, thread_id, thread_type, ttl=60000)
        return
    if not is_admin_user:
        client.replyMessage(Message(text="Chỉ admin mới có thể sử dụng lệnh này."), message_object, thread_id, thread_type, ttl=60000)
        return
        
    parts = message.strip().split(" ", 1)
    if len(parts) < 2 or not parts[1].strip():
        client.replyMessage(Message(text="Nhập tên thành viên cần tag.\nVí dụ: group.findtag Nam"), message_object, thread_id, thread_type, ttl=60000)
        return

    search_term = parts[1].strip().lower()

    members, error = get_group_members(client, thread_id, thread_type, message_object)
    if error:
        client.replyMessage(Message(text=error), message_object, thread_id, thread_type, ttl=60000)
        return

    found_members = [
        member for member in members 
        if search_term == member['zaloName'].lower() or
        search_term in member['zaloName'].lower() or
        search_term in "".join(c[0] for c in member['zaloName'].split()).lower()
    ]

    if not found_members:
        client.replyMessage(
            Message(text=f"Không tìm thấy thành viên nào có tên chứa '{search_term}'."),
            message_object, thread_id, thread_type, ttl=60000
        )
        return

    text = ""
    mentions = []
    offset = 0
    for member in found_members:
        user_id = str(member['id'])
        user_name = member['zaloName']
        text += f"{user_name} "
        mentions.append(Mention(uid=user_id, offset=offset, length=len(user_name), auto_format=False))
        offset += len(user_name) + 1
    client.replyMessage(
        Message(text=text.strip(), mention=MultiMention(mentions)),
        message_object, thread_id, thread_type, ttl=60000
    )

# Hàm trả về lệnh
def get_mitaizl():
    return {
        'group.finduser': handle_find,
        'group.findtag': handle_findtag
    }