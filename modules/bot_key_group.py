from zlapi.models import *
import json

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Lấy danh sách link mời của các nhóm Zalo mà bot đang là phó nhóm",
    'tính năng': [
        "🔗 Lấy link mời của các nhóm Zalo mà bot giữ vai trò phó nhóm thông qua API Zalo.",
        "📋 Trả về danh sách link dưới dạng URL hoặc thông báo lỗi nếu không tìm thấy.",
        "🔍 Kiểm tra vai trò phó nhóm của bot dựa trên thông tin quản trị viên nhóm.",
        "🔔 Thông báo lỗi cụ thể nếu không có nhóm nào hoặc gặp sự cố khi truy xuất link.",
        "📩 Gửi kết quả trực tiếp dưới dạng tin nhắn trả lời trong nhóm hoặc người dùng."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh bot.keygroup để lấy danh sách link mời của các nhóm mà bot là phó nhóm.",
        "📌 Ví dụ: bot.keygroup (không cần tham số).",
        "✅ Nhận danh sách link mời nhóm hoặc thông báo nếu không có nhóm phù hợp."
    ]
}

def check_sub_admin_group(bot, thread_id):
    try:
        # Lấy thông tin nhóm
        group = bot.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
        admin_ids = group.adminIds.copy()  # Danh sách ID phó nhóm
        creator_id = group.creatorId  # ID trưởng nhóm

        # Kiểm tra bot có trong danh sách phó nhóm và không phải trưởng nhóm
        is_sub_admin = bot.uid in admin_ids and bot.uid != creator_id
        print(f"Kiểm tra vai trò phó nhóm cho nhóm {thread_id}: bot.uid={bot.uid}, is_sub_admin={is_sub_admin}")
        return is_sub_admin, group.name if hasattr(group, 'name') else "Nhóm không có tên"
    except Exception as e:
        print(f"Lỗi khi kiểm tra vai trò phó nhóm cho nhóm {thread_id}: {str(e)}")
        return False, None

def handle_groupsublink_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        # Lấy danh sách tất cả nhóm mà bot tham gia
        print(f"Gọi fetchAllGroups cho bot.uid={client.uid}")
        group_data = client.fetchAllGroups()
        print(f"Kết quả từ fetchAllGroups: {group_data}")

        # Kiểm tra dữ liệu trả về từ fetchAllGroups
        if not group_data:
            response_message = "Không nhận được dữ liệu nhóm từ API Zalo. Vui lòng kiểm tra kết nối API."
            message_to_send = Message(text=response_message)
            client.replyMessage(message_to_send, message_object, thread_id, thread_type)
            return

        # Lấy danh sách nhóm từ gridVerMap
        grid_ver_map = getattr(group_data, 'gridVerMap', None)
        if not grid_ver_map:
            response_message = "Danh sách nhóm rỗng hoặc không tìm thấy gridVerMap trong dữ liệu."
            print(f"gridVerMap không tồn tại: {group_data}")
            message_to_send = Message(text=response_message)
            client.replyMessage(message_to_send, message_object, thread_id, thread_type)
            return

        # Lấy danh sách chatID từ gridVerMap
        group_ids = list(grid_ver_map.keys())
        print(f"Danh sách nhóm tìm thấy: {group_ids}")

        if not group_ids:
            response_message = "Bot không tham gia nhóm nào hoặc danh sách nhóm rỗng."
            message_to_send = Message(text=response_message)
            client.replyMessage(message_to_send, message_object, thread_id, thread_type)
            return

        # Lưu trữ danh sách nhóm mà bot là phó nhóm
        sub_admin_groups = []
        for group_id in group_ids:
            print(f"Xử lý nhóm {group_id}")
            is_sub_admin, group_name = check_sub_admin_group(client, group_id)
            if is_sub_admin:
                sub_admin_groups.append((group_id, group_name))

        if not sub_admin_groups:
            response_message = "Bot hiện không là phó nhóm của bất kỳ nhóm nào."
            print(f"Không tìm thấy nhóm nào mà bot là phó nhóm: {sub_admin_groups}")
            message_to_send = Message(text=response_message)
            client.replyMessage(message_to_send, message_object, thread_id, thread_type)
            return

        # Lấy link mời cho từng nhóm mà bot là phó nhóm
        results = []
        for group_id, group_name in sub_admin_groups:
            try:
                group_link = client.getGroupLink(chatID=group_id)
                print(f"Dữ liệu từ getGroupLink cho nhóm {group_id}: {group_link}")
                if group_link.get("error_code") == 0:
                    data = group_link.get("data")
                    if isinstance(data, dict):
                        if data.get('link'):
                            results.append(f"{group_name}\n{data['link']}")
                        elif data.get('url'):
                            results.append(f"{group_name}\n{data['url']}")
                        else:
                            results.append(f"{group_name}\n❌ Không tìm thấy link group. Dữ liệu trả về: {data}")
                    elif isinstance(data, str):
                        results.append(f"{group_name}\n{data}")
                    else:
                        results.append(f"{group_name}\n❌ Không tìm thấy link group.")
                else:
                    results.append(f"{group_name}\n❌ Lỗi từ Zalo API: {group_link.get('error_message', 'Lỗi không xác định')}")
            except ValueError:
                results.append(f"{group_name}\n❌ Lỗi: ID nhóm không hợp lệ.")
            except Exception as e:
                results.append(f"{group_name}\n❌ Đã xảy ra lỗi: {str(e)}")

        # Tạo phản hồi với tất cả kết quả
        response_message = "\n\n".join(results) if results else "Không có link nhóm nào được tìm thấy."
        
    except ZaloAPIException as e:
        response_message = f"Lỗi từ Zalo API: {str(e)}"
        print(f"ZaloAPIException: {str(e)}")
    except Exception as e:
        response_message = f"Đã xảy ra lỗi khi xử lý lệnh: {str(e)}"
        print(f"Exception: {str(e)}")

    message_to_send = Message(text=response_message)
    client.replyMessage(message_to_send, message_object, thread_id, thread_type)

def get_mitaizl():
    return {
        'bot.keygroup': handle_groupsublink_command
    }