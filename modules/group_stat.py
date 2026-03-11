from datetime import datetime
import time
from zlapi.models import *

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "📊 Thống kê số lượng nhóm Zalo mà bot tham gia theo trưởng nhóm, kèm thông tin chi tiết.",
    'tính năng': [
        "📋 Đếm số lượng nhóm theo từng trưởng nhóm, bao gồm tên trưởng nhóm và số nhóm.",
        "🔗 Lấy danh sách nhóm với tên nhóm và link nhóm tương ứng.",
        "✅ Chỉ admin được phép sử dụng lệnh để đảm bảo bảo mật.",
        "✉️ Hỗ trợ gửi tin nhắn dài bằng cách chia nhỏ nội dung, với định dạng màu sắc và font chữ.",
        "⚠️ Xử lý lỗi API Zalo và cung cấp thông báo chi tiết khi xảy ra sự cố."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh group.stat để xem thống kê nhóm theo trưởng nhóm.",
        "📌 Ví dụ: group.stat",
        "✅ Nhận kết quả với định dạng: Tên trưởng nhóm, số lượng nhóm, danh sách nhóm (tên và link).",
        "⚠️ Lệnh chỉ hoạt động với người dùng có ID trong danh sách admin."
    ]
}

# Danh sách ADMIN ID được phép sử dụng lệnh
ADMIN_IDS = ["3299675674241805615"]  # Thay thế bằng ID thực tế của Admin

def send_message_with_style(client, text, thread_id, thread_type, color="#000000"):
    """
    Gửi tin nhắn với định dạng màu sắc và font chữ.
    """
    print(f"[{datetime.now()}] [send_message_with_style] Chuẩn bị gửi tin nhắn đến thread {thread_id}. Nội dung (cắt ngắn): {text[:50]}...")
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
            size="1",
            auto_format=False
        )
    ])
    client.send(Message(text=text, style=style), thread_id=thread_id, thread_type=thread_type, ttl=600000)

def send_long_message(client, text, thread_id, thread_type, color="#db342e", max_length=1500, delay=0.3):
    """
    Gửi tin nhắn dài thành nhiều phần nếu vượt quá max_length ký tự,
    kèm thời gian trễ (delay) giữa các phần.
    """
    chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
    total_chunks = len(chunks)
    for index, chunk in enumerate(chunks, start=1):
        print(f"[{datetime.now()}] [send_long_message] Đang gửi phần {index}/{total_chunks}")
        send_message_with_style(client, chunk, thread_id, thread_type, color)
        time.sleep(delay)

def get_group_link(client, group_id):
    """
    Lấy link nhóm dựa trên group_id, xử lý các trường hợp lỗi và dữ liệu trả về từ Zalo API.
    """
    try:
        group_link = client.getGroupLink(chatID=group_id)
        print(f"[{datetime.now()}] [get_group_link] Dữ liệu từ Zalo API cho nhóm {group_id}: {group_link}")
        if group_link.get("error_code") == 0:
            data = group_link.get("data")
            if isinstance(data, dict):
                if data.get('link'):
                    return data['link']
                elif data.get('url'):
                    return data['url']
                else:
                    print(f"[{datetime.now()}] [get_group_link] Không tìm thấy link hoặc url trong dữ liệu: {data}")
                    return "Không tìm thấy link nhóm"
            elif isinstance(data, str):
                return data
            else:
                print(f"[{datetime.now()}] [get_group_link] Dữ liệu không hợp lệ: {data}")
                return "Không tìm thấy link nhóm"
        else:
            print(f"[{datetime.now()}] [get_group_link] Lỗi từ Zalo API: {group_link.get('error_message', 'Lỗi không xác định')}")
            return "Không lấy được link"
    except ValueError as e:
        print(f"[{datetime.now()}] [get_group_link] Lỗi ValueError: {e}")
        return "Lỗi: Cần có Group ID"
    except Exception as e:
        print(f"[{datetime.now()}] [get_group_link] Lỗi ngoại lệ: {e}")
        return "Không lấy được link"

def handle_count_groups_by_leader(message, message_object, thread_id, thread_type, author_id, bot):
    """
    Đếm số lượng nhóm mà bot đang tham gia theo từng tên trưởng nhóm, bao gồm tên nhóm và link nhóm.
    
    KẾT QUẢ ĐẾM NHÓM THEO TRƯỞNG NHÓM
    1. Tên trưởng nhóm: ...
       Số lượng nhóm: ...
       Danh sách nhóm:
       - Tên nhóm: ... | Link nhóm: ...
    Tổng số nhóm: ...
    """
    print(f"[{datetime.now()}] [handle_count_groups_by_leader] Yêu cầu từ người dùng với author_id: {author_id}")
    
    # Kiểm tra quyền admin
    if author_id not in ADMIN_IDS:
        error_msg = "Bạn không có quyền sử dụng lệnh này."
        send_message_with_style(bot, error_msg, thread_id, thread_type)
        print(f"[{datetime.now()}] [handle_count_groups_by_leader] Unauthorized access attempt từ {author_id}")
        return

    # Gửi phản ứng khi nhận lệnh
    bot.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
    # Gửi phản hồi ban đầu
    reply_message = "Đang đếm số lượng nhóm theo trưởng nhóm ..."
    send_message_with_style(bot, reply_message, thread_id, thread_type)
    print(f"[{datetime.now()}] [handle_count_groups_by_leader] Đã gửi phản hồi ban đầu")

    try:
        # Lấy tất cả các nhóm mà bot đang tham gia
        all_group = bot.fetchAllGroups()
        allowed_thread_ids = {gid for gid in all_group.gridVerMap.keys()}
        groups = []
        for gid in allowed_thread_ids:
            group_info = bot.fetchGroupInfo(gid).gridInfoMap[gid]
            groups.append(group_info)
            print(f"[{datetime.now()}] [handle_count_groups_by_leader] Loaded group info cho nhóm ID: {gid}")
    except Exception as e:
        error_msg = f"Đã xảy ra lỗi khi lấy thông tin nhóm: {e}"
        send_message_with_style(bot, error_msg, thread_id, thread_type)
        print(f"[{datetime.now()}] [handle_count_groups_by_leader] Lỗi: {error_msg}")
        return

    # Hàm lấy tên người dùng dựa trên creatorId
    def get_name(user_id):
        try:
            user_info = bot.fetchUserInfo(user_id)
            return user_info.changed_profiles[user_id].zaloName
        except KeyError:
            return "Không tìm thấy tên"

    # Đếm số lượng nhóm và lưu thông tin chi tiết theo trưởng nhóm
    leader_groups = {}
    seen = set()
    for group in groups:
        if group.groupId in seen:
            continue
        seen.add(group.groupId)
        leader_name = get_name(group.creatorId)
        group_link = get_group_link(bot, group.groupId)
        if leader_name not in leader_groups:
            leader_groups[leader_name] = []
        leader_groups[leader_name].append((group.name, group_link))
        print(f"[{datetime.now()}] [handle_count_groups_by_leader] Đã xử lý nhóm: {group.name} (Trưởng nhóm: {leader_name})")

    # Tạo tin nhắn kết quả
    msg = "KẾT QUẢ ĐẾM NHÓM THEO TRƯỞNG NHÓM\n"
    count = 1
    for leader_name, group_list in leader_groups.items():
        msg += (
            f"{count}. Tên trưởng nhóm: {leader_name}\n"
            f"   Số lượng nhóm: {len(group_list)}\n"
            f"   Danh sách nhóm:\n"
        )
        for group_name, group_link in group_list:
            msg += f"   - Tên nhóm: {group_name} | Link nhóm: {group_link}\n"
        msg += "_________________________________\n"
        count += 1
    total_groups = len(seen)
    msg += f"Tổng số nhóm: {total_groups}"

    # Gửi tin nhắn kết quả
    send_long_message(bot, msg, thread_id, thread_type, color="#000000", max_length=1500, delay=1)
    print(f"[{datetime.now()}] [handle_count_groups_by_leader] Hoàn thành gửi kết quả đếm nhóm.")

def get_mitaizl():
    return {
        'group.stat': handle_count_groups_by_leader
    }