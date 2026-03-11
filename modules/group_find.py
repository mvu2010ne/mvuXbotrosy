from zlapi.models import *

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Tìm thông tin nhóm dựa trên ID nhóm",
    'tính năng': [
        "🔍 Tìm kiếm và hiển thị thông tin chi tiết của nhóm dựa trên ID nhóm.",
        "🔐 Kiểm tra quyền admin trước khi thực hiện lệnh.",
        "📋 Lấy thông tin nhóm bao gồm tên nhóm, trưởng nhóm, số thành viên, ID nhóm và link nhóm.",
        "🔗 Hỗ trợ lấy link mời nhóm thông qua API Zalo.",
        "🔔 Thông báo lỗi cụ thể nếu không tìm thấy nhóm, cú pháp không hợp lệ hoặc gặp sự cố khi truy xuất thông tin."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh group.find kèm theo danh sách ID nhóm để tìm thông tin.",
        "📌 Ví dụ: group.find <ID_nhóm_1> <ID_nhóm_2> để lấy thông tin các nhóm tương ứng.",
        "✅ Nhận kết quả thông tin nhóm ngay lập tức, bao gồm tên, trưởng nhóm, số thành viên và link nhóm."
    ]
}

# Danh sách ADMIN ID được phép sử dụng lệnh
ADMIN_IDS = ["3299675674241805615"]  # Thay bằng ID thực tế của Admin

def send_message_with_style(client, text, thread_id, thread_type, color="#000000"):
    """
    Gửi tin nhắn với định dạng màu sắc và font chữ.
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
            style="font",
            size="1",
            auto_format=False
        )
    ])
    client.send(Message(text=text, style=style), thread_id=thread_id, thread_type=thread_type, ttl=60000)

def handle_find_group_name(message, message_object, thread_id, thread_type, author_id, bot):
    """
    Tìm tên nhóm dựa trên danh sách ID nhóm do người dùng cung cấp, bao gồm link mời nhóm.
    """
    if author_id not in ADMIN_IDS:
        error_msg = "Bạn không có quyền sử dụng lệnh này."
        send_message_with_style(bot, error_msg, thread_id, thread_type)
        return
    
    bot.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
    
    # Định nghĩa hàm get_name để lấy tên người dùng (dựa vào creatorId)
    def get_name(user_id):
        if not user_id:
            return "Không tìm thấy tên"
        try:
            user_info = bot.fetchUserInfo(user_id)
            return user_info.changed_profiles.get(user_id, {}).get('zaloName', "Không tìm thấy tên")
        except Exception as e:
            print(f"[handle_find_group_name] Lỗi khi lấy tên người dùng {user_id}: {e}")
            return "Không tìm thấy tên"
    
    args = message.split()
    if len(args) < 2:
        send_message_with_style(bot, "Vui lòng nhập ít nhất một ID nhóm cần tìm.", thread_id, thread_type)
        return
    
    group_ids = args[1:]
    msg = "🔍 Kết quả tìm kiếm nhóm:\n"
    
    for group_id in group_ids:
        try:
            group_info = bot.fetchGroupInfo(group_id).gridInfoMap.get(group_id, None)
            if not group_info:
                msg += f"❌ Không tìm thấy nhóm với ID: {group_id}\n"
                print(f"[handle_find_group_name] Không tìm thấy thông tin nhóm với ID: {group_id}")
                continue
            
            # Lấy link nhóm bằng phương thức getGroupLink
            try:
                group_link = bot.getGroupLink(chatID=group_id)
                print(f"[handle_find_group_name] Dữ liệu từ getGroupLink cho nhóm {group_id}: {group_link}")
                if group_link.get("error_code") == 0:
                    data = group_link.get("data")
                    if isinstance(data, dict):
                        if data.get('link'):
                            group_link_url = data['link']
                        elif data.get('url'):
                            group_link_url = data['url']
                        else:
                            group_link_url = "Không tìm thấy link nhóm"
                            print(f"[handle_find_group_name] Không tìm thấy link hoặc url trong dữ liệu: {data}")
                    elif isinstance(data, str):
                        group_link_url = data
                    else:
                        group_link_url = "Không tìm thấy link nhóm"
                        print(f"[handle_find_group_name] Dữ liệu không hợp lệ: {data}")
                else:
                    group_link_url = "Không lấy được link"
                    print(f"[handle_find_group_name] Lỗi từ Zalo API: {group_link.get('error_message', 'Lỗi không xác định')}")
            except ValueError as e:
                group_link_url = "Lỗi: Cần có Group ID"
                print(f"[handle_find_group_name] Lỗi ValueError khi gọi getGroupLink cho nhóm {group_id}: {e}")
            except Exception as e:
                group_link_url = "Không lấy được link"
                print(f"[handle_find_group_name] Lỗi ngoại lệ khi gọi getGroupLink cho nhóm {group_id}: {e}")
            
            msg += (
                f"✅ 𝗡𝗵𝗼́𝗺: {group_info.name}\n"
                f"👤 𝗧𝗿𝘂̛𝗼̛̉𝗻𝗴 𝗻𝗵𝗼́𝗺: {group_info.creatorId}\n"
                f"🔑 𝗧𝗿𝘂̛𝗼̛̉𝗻𝗴 𝗻𝗵𝗼́𝗺: {get_name(group_info.creatorId)}\n"
                f"👥 𝗦𝗼̂́ 𝗧𝗵𝗮̀𝗻𝗵 𝗩𝗶𝗲̂𝗻: {group_info.totalMember}\n"
                f"🆔 𝗜𝗗 𝗡𝗵𝗼́𝗺: {group_id}\n"
                f"🔗 L𝗶𝗻𝗸 𝗡𝗵𝗼́𝗺: {group_link_url}\n"
                f"---------------------------------\n"
            )
            print(f"[handle_find_group_name] Đã xử lý nhóm: {group_info.name} (ID: {group_id})")
        except Exception as e:
            msg += f"⚠️ Lỗi khi lấy thông tin nhóm {group_id}: {e}\n"
            print(f"[handle_find_group_name] Lỗi khi lấy thông tin nhóm {group_id}: {e}")
    
    send_message_with_style(bot, msg, thread_id, thread_type, color="#000000")

def get_mitaizl():
    return {
        'group.find': handle_find_group_name
    }