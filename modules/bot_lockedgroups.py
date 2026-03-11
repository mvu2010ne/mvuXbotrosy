from datetime import datetime
import time
from zlapi.models import *

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Bot hỗ trợ lấy thông tin các nhóm Zalo mà bot đang tham gia và bị khóa chat, sau đó gửi danh sách về cho người dùng.",
    'tính năng': [
        "📋 Lấy thông tin các nhóm Zalo mà bot đang tham gia và bị khóa chat.",
        "🔔 Thông báo kết quả lấy danh sách với thời gian sống (TTL) khác nhau.",
        "🔍 Lấy thông tin chi tiết về nhóm bao gồm tên nhóm, ID nhóm, link nhóm, tên trưởng nhóm, phó nhóm và số thành viên.",
        "🔒 Chỉ quản trị viên mới có quyền sử dụng lệnh này."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh để bot lấy thông tin các nhóm Zalo bị khóa chat mà bot đang tham gia.",
        "📌 Bot sẽ gửi thông tin chi tiết về từng nhóm trong danh sách.",
        "✅ Nhận thông báo trạng thái lấy danh sách ngay lập tức."
    ]
}

# Danh sách ADMIN ID được phép sử dụng lệnh
ADMIN_IDS = ["3299675674241805615"]  # Thay thế bằng ID thực tế của Admin

def send_message_with_style(client, text, thread_id, thread_type, color="#000000"):
    """
    Gửi tin nhắn với định dạng màu sắc và font chữ.
    """
    print(f"[{datetime.now()}] [send_message_with_style] Chuẩn bị gửi tin nhắn đến thread {thread_id}. Nội dung (cắt ngắn): {text[:50]}...")
    try:
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
    except Exception as e:
        print(f"[{datetime.now()}] [send_message_with_style] Lỗi khi gửi tin nhắn: {e}")

def send_long_message(client, text, thread_id, thread_type, color="#db342e", max_length=1500, delay=1.0):
    """
    Gửi tin nhắn dài thành nhiều phần nếu vượt quá max_length ký tự,
    kèm thời gian trễ (delay) giữa các phần.
    """
    try:
        chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
        total_chunks = len(chunks)
        for index, chunk in enumerate(chunks, start=1):
            print(f"[{datetime.now()}] [send_long_message] Đang gửi phần {index}/{total_chunks}")
            send_message_with_style(client, chunk, thread_id, thread_type, color)
            time.sleep(delay)
    except Exception as e:
        print(f"[{datetime.now()}] [send_long_message] Lỗi khi gửi tin nhắn dài: {e}")

def handle_locked_groups(message, message_object, thread_id, thread_type, author_id, bot):
    """
    Lấy thông tin tất cả các nhóm mà bot đang tham gia và bị khóa chat, sau đó gửi danh sách về cho người dùng.
    
    DANH SÁCH NHÓM BOT ĐANG Ở VÀ BỊ KHÓA CHAT
    1. Tên nhóm: ......
       ID nhóm: .....
       Link nhóm: .....
       Trưởng nhóm: .....
       Phó nhóm: .....
       Số thành viên: .....
       Tình trạng chat: ⛔Cấm chat
    """
    print(f"[{datetime.now()}] [handle_locked_groups] Yêu cầu từ người dùng với author_id: {author_id}")
    # Kiểm tra quyền admin: chỉ ADMIN ID mới được sử dụng lệnh
    if author_id not in ADMIN_IDS:
        error_msg = "Bạn không có quyền sử dụng lệnh này."
        send_message_with_style(bot, error_msg, thread_id, thread_type)
        print(f"[{datetime.now()}] [handle_locked_groups] Unauthorized access attempt từ {author_id}")
        return

    # Gửi phản ứng khi nhận lệnh
    try:
        bot.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
    except Exception as e:
        print(f"[{datetime.now()}] [handle_locked_groups] Lỗi khi gửi phản ứng: {e}")

    # Gửi phản hồi ban đầu
    reply_message = "Đang tải danh sách nhóm bị khóa chat ..."
    send_message_with_style(bot, reply_message, thread_id, thread_type)
    print(f"[{datetime.now()}] [handle_locked_groups] Đã gửi phản hồi ban đầu")

    try:
        # Lấy tất cả các nhóm thông qua client.fetchAllGroups()
        all_group = bot.fetchAllGroups()
        allowed_thread_ids = {gid for gid in all_group.gridVerMap.keys()}
        groups = []
        for gid in allowed_thread_ids:
            try:
                # Lấy thông tin chi tiết của từng nhóm
                group_info = bot.fetchGroupInfo(gid).gridInfoMap[gid]
                # Chỉ thêm nhóm có lockSendMsg == 1
                setting = getattr(group_info, 'setting', {}) or {}
                if setting.get('lockSendMsg') == 1:
                    groups.append(group_info)
                    print(f"[{datetime.now()}] [handle_locked_groups] Loaded group info cho nhóm bị khóa chat ID: {gid}")
                time.sleep(0.1)  # Thêm độ trễ để tránh vượt giới hạn API
            except Exception as e:
                print(f"[{datetime.now()}] [handle_locked_groups] Lỗi khi lấy thông tin nhóm ID {gid}: {e}")
                continue
    except Exception as e:
        error_msg = f"Đã xảy ra lỗi khi lấy danh sách nhóm: {e}"
        send_message_with_style(bot, error_msg, thread_id, thread_type)
        print(f"[{datetime.now()}] [handle_locked_groups] Lỗi: {error_msg}")
        return

    # Hàm lấy tên người dùng dựa trên creatorId
    def get_name(user_id):
        try:
            user_info = bot.fetchUserInfo(user_id)
            return user_info.changed_profiles[user_id].zaloName
        except Exception as e:
            print(f"[{datetime.now()}] [get_name] Lỗi khi lấy tên người dùng ID {user_id}: {e}")
            return "Không tìm thấy tên"

    seen = set()
    msg = "DANH SÁCH NHÓM BOT ĐANG Ở VÀ BỊ KH “‘A CHAT\n"
    count = 1
    for group in groups:
        if group.groupId in seen:
            continue
        seen.add(group.groupId)
        
        try:
            # Lấy link nhóm bằng phương thức getGroupLink
            try:
                group_link = bot.getGroupLink(chatID=group.groupId)
                print(f"[{datetime.now()}] [handle_locked_groups] Dữ liệu từ getGroupLink cho nhóm {group.groupId}: {group_link}")
                if group_link.get("error_code") == 0:
                    data = group_link.get("data")
                    if isinstance(data, dict):
                        if data.get('link'):
                            group_link_url = data['link']
                        elif data.get('url'):
                            group_link_url = data['url']
                        else:
                            group_link_url = "Không tìm thấy link nhóm"
                            print(f"[{datetime.now()}] [handle_locked_groups] Không tìm thấy link hoặc url trong dữ liệu: {data}")
                    elif isinstance(data, str):
                        group_link_url = data
                    else:
                        group_link_url = "Không tìm thấy link nhóm"
                        print(f"[{datetime.now()}] [handle_locked_groups] Dữ liệu không hợp lệ: {data}")
                else:
                    group_link_url = "Không lấy được link"
                    print(f"[{datetime.now()}] [handle_locked_groups] Lỗi từ Zalo API: {group_link.get('error_message', 'Lỗi không xác định')}")
            except ValueError as e:
                group_link_url = "Lỗi: Cần có Group ID"
                print(f"[{datetime.now()}] [handle_locked_groups] Lỗi ValueError khi gọi getGroupLink cho nhóm {group.groupId}: {e}")
            except Exception as e:
                group_link_url = "Không lấy được link"
                print(f"[{datetime.now()}] [handle_locked_groups] Lỗi ngoại lệ khi gọi getGroupLink cho nhóm {group.groupId}: {e}")

            # Lấy tên nhóm, đảm bảo không rỗng
            group_name = group.name if group.name else "Không có tên nhóm"
            # Lấy danh sách phó nhóm
            admin_names = []
            for member in group.adminIds:
                try:
                    admin_names.append(get_name(member))
                    time.sleep(0.1)  # Thêm độ trễ để tránh vượt giới hạn API
                except Exception as e:
                    print(f"[{datetime.now()}] [handle_locked_groups] Lỗi khi lấy tên phó nhóm ID {member}: {e}")
                    admin_names.append("Không tìm thấy tên")
            
            msg += (
                f"👪 𝗕𝗢𝗫 {count}: {group_name}\n"            
                f"🔑 𝗧𝗿𝘂̛𝗼̛̉𝗻𝗴 𝗻𝗵𝗼́𝗺: {get_name(group.creatorId)}\n"
                f"🗝️ 𝗣𝗵𝗼́ 𝗻𝗵𝗼́𝗺: {', '.join(admin_names) if admin_names else 'Không có'}\n"
                f"🆔 𝗜𝗗 𝗡𝗵𝗼́𝗺: {group.groupId}\n"
                f"🔗 𝗟𝗶𝗻𝗸 𝗡𝗵𝗼́𝗺: {group_link_url}\n"
                f"👥 𝗧𝗵𝗮̀𝗻𝗵 𝘃𝗶𝗲̂𝗻: {group.totalMember}\n"
                f"⚙ 𝗧𝗶̀𝗻𝗵 𝘁𝗿𝗮̣𝗻𝗴 𝗰𝗵𝗮𝘁: ⛔Cấm chat\n"
                f"_________________________________\n"
            )
            print(f"[{datetime.now()}] [handle_locked_groups] Đã xử lý nhóm: {group_name} (ID: {group.groupId})")
            count += 1
            time.sleep(0.1)  # Thêm độ trễ để tránh vượt giới hạn API
        except Exception as e:
            print(f"[{datetime.now()}] [handle_locked_groups] Lỗi khi xử lý nhóm ID {group.groupId}: {e}")
            continue

    # Nếu không có nhóm nào bị khóa chat
    if count == 1:
        msg = "Hiện tại không có nhóm nào bot đang tham gia bị khóa chat."
        send_message_with_style(bot, msg, thread_id, thread_type)
        print(f"[{datetime.now()}] [handle_locked_groups] Không tìm thấy nhóm bị khóa chat.")
        return

    # Gửi tin nhắn đã được chia thành các phần nếu nội dung quá dài
    send_long_message(bot, msg, thread_id, thread_type, color="#000000", max_length=1500, delay=1.0)
    print(f"[{datetime.now()}] [handle_locked_groups] Hoàn thành gửi tin nhắn danh sách nhóm bị khóa chat.")

def get_mitaizl():
    return {
        'bot.lockedgroups': handle_locked_groups
    }