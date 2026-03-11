from datetime import datetime
import time
from zlapi.models import *

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Bot hỗ trợ lấy danh sách tất cả các link nhóm Zalo mà bot đang tham gia và gửi về cho người dùng.",
    'tính năng': [
        "🔗 Lấy danh sách tất cả các link nhóm Zalo mà bot đang tham gia.",
        "🔔 Thông báo kết quả lấy danh sách với thời gian sống (TTL) khác nhau.",
        "🔒 Chỉ quản trị viên mới có quyền sử dụng lệnh này."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh để bot lấy danh sách các link nhóm Zalo mà bot đang tham gia.",
        "📌 Bot sẽ gửi danh sách các link nhóm.",
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

def handle_list_group_links(message, message_object, thread_id, thread_type, author_id, bot):
    """
    Lấy danh sách tất cả các link nhóm mà bot đang tham gia và gửi về cho người dùng.
    
    DANH SÁCH LINK NHÓM BOT ĐANG Ở
    1. Link nhóm: .....
    """
    print(f"[{datetime.now()}] [handle_list_group_links] Yêu cầu từ người dùng với author_id: {author_id}")
    # Kiểm tra quyền admin: chỉ ADMIN ID mới được sử dụng lệnh
    if author_id not in ADMIN_IDS:
        error_msg = "Bạn không có quyền sử dụng lệnh này."
        send_message_with_style(bot, error_msg, thread_id, thread_type)
        print(f"[{datetime.now()}] [handle_list_group_links] Unauthorized access attempt từ {author_id}")
        return

    # Gửi phản ứng khi nhận lệnh
    bot.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
    # Gửi phản hồi vào tin nhắn người đã soạn
    reply_message = "Đang tải danh sách link nhóm ..."
    send_message_with_style(bot, reply_message, thread_id, thread_type)
    print(f"[{datetime.now()}] [handle_list_group_links] Đã gửi phản hồi ban đầu")

    try:
        # Lấy tất cả các nhóm thông qua client.fetchAllGroups()
        all_group = bot.fetchAllGroups()
        allowed_thread_ids = {gid for gid in all_group.gridVerMap.keys()}
        groups = []
        for gid in allowed_thread_ids:
            # Lấy thông tin chi tiết của từng nhóm
            group_info = bot.fetchGroupInfo(gid).gridInfoMap[gid]
            groups.append(group_info)
            print(f"[{datetime.now()}] [handle_list_group_links] Loaded group info cho nhóm ID: {gid}")
    except Exception as e:
        error_msg = f"Đã xảy ra lỗi khi lấy thông tin nhóm: {e}"
        send_message_with_style(bot, error_msg, thread_id, thread_type)
        print(f"[{datetime.now()}] [handle_list_group_links] Lỗi: {error_msg}")
        return

    seen = set()
    msg = "DANH SÁCH LINK NHÓM BOT ĐANG Ở\n"
    count = 1
    for group in groups:
        if group.groupId in seen:
            continue
        seen.add(group.groupId)
        
        # Lấy link nhóm bằng phương thức getGroupLink
        try:
            group_link = bot.getGroupLink(chatID=group.groupId)
            print(f"[{datetime.now()}] [handle_list_group_links] Dữ liệu từ getGroupLink cho nhóm {group.groupId}: {group_link}")
            if group_link.get("error_code") == 0:
                data = group_link.get("data")
                if isinstance(data, dict):
                    if data.get('link'):
                        group_link_url = data['link']
                    elif data.get('url'):
                        group_link_url = data['url']
                    else:
                        group_link_url = "Không tìm thấy link nhóm"
                        print(f"[{datetime.now()}] [handle_list_group_links] Không tìm thấy link hoặc url trong dữ liệu: {data}")
                elif isinstance(data, str):
                    group_link_url = data
                else:
                    group_link_url = "Không tìm thấy link nhóm"
                    print(f"[{datetime.now()}] [handle_list_group_links] Dữ liệu không hợp lệ: {data}")
            else:
                group_link_url = "Không lấy được link"
                print(f"[{datetime.now()}] [handle_list_group_links] Lỗi từ Zalo API: {group_link.get('error_message', 'Lỗi không xác định')}")
        except ValueError as e:
            group_link_url = "Lỗi: Cần có Group ID"
            print(f"[{datetime.now()}] [handle_list_group_links] Lỗi ValueError khi gọi getGroupLink cho nhóm {group.groupId}: {e}")
        except Exception as e:
            group_link_url = "Không lấy được link"
            print(f"[{datetime.now()}] [handle_list_group_links] Lỗi ngoại lệ khi gọi getGroupLink cho nhóm {group.groupId}: {e}")
        
        msg += (
            f"{count}. 🔗 Link nhóm: {group_link_url}\n"
            f"_________________________________\n"
        )
        print(f"[{datetime.now()}] [handle_list_group_links] Đã xử lý nhóm ID: {group.groupId}")
        count += 1

    # Gửi tin nhắn đã được chia thành các phần nếu nội dung quá dài,
    # với thời gian trễ 1 giây giữa các phần.
    send_long_message(bot, msg, thread_id, thread_type, color="#000000", max_length=1500, delay=3)
    print(f"[{datetime.now()}] [handle_list_group_links] Hoàn thành gửi tin nhắn danh sách link nhóm.")

def get_mitaizl():
    return {
        'bot.grouplinks': handle_list_group_links
    }