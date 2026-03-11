from zlapi import ZaloAPIException, ThreadType
from zlapi.models import Message, MessageStyle, MultiMsgStyle
from config import PREFIX
import time
import threading
from datetime import datetime

# Admin ID (UID Zalo của admin)
ADMIN_ID = "3299675674241805615"

# ID mặc định luôn được thêm vào nhóm
DEFAULT_MEMBER_ID = "3299675674241805615"

# Module-level global state để theo dõi trạng thái giải tán nhóm
global_state = {}

# Mô tả tập lệnh
des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🔧 Quản lý nhóm Zalo: tạo nhóm mới hoặc giải tán nhóm hiện có (chỉ admin).",
    'tính năng': [
        "📌 Tạo nhóm với tên tùy chỉnh và thêm thành viên bằng danh sách UID hoặc mention.",
        "📌 Tự động thêm UID 3299675674241805615 vào mọi nhóm mới.",
        "📋 Hiển thị thông tin chi tiết nhóm vừa tạo (tên, ID, link, số thành viên, thời gian tạo).",
        "🗑️ Giải tán nhóm sau 60 giây với thông báo (chủ nhóm và admin).",
        "🔄 Hủy giải tán nhóm bằng lệnh group.cancel trong 60 giây.",
        "🔄 Giải tán nhóm hiện tại nếu không cung cấp ID (trong nhóm).",
        "🎨 Gửi thông báo với định dạng màu sắc và in đậm.",
        "🔒 Chỉ admin được sử dụng lệnh.",
        "⚠️ Thông báo lỗi nếu cú pháp sai hoặc không thực hiện được hành động."
    ],
    'hướng dẫn sử dụng': [
        "📩 Tạo nhóm: group.creat <tên nhóm> [<UID hoặc @tag>] hoặc danh sách UID trên các dòng.",
        "📩 UID 3299675674241805615 luôn được thêm tự động.",
        "📩 Ví dụ: group.creat MyGroup @user1 @user2 hoặc:",
        "   group.creat MyGroup",
        "   123456789",
        "   987654321",
        "📩 Giải tán nhóm: group.del <groupID> hoặc group.del (trong nhóm).",
        "📩 Hủy giải tán: group.cancel trong 60 giây sau khi nhập group.del.",
        "📌 Ví dụ: group.del 987654321 hoặc group.del",
        "✅ Nhận thông báo kết quả trong tin nhắn."
    ]
}

def send_message_with_style(client, text, thread_id, thread_type, ttl=600000, color="#db342e"):
    """Gửi tin nhắn với định dạng màu sắc và in đậm."""
    base_length = len(text)
    adjusted_length = base_length + 355
    style = MultiMsgStyle([
        MessageStyle(offset=0, length=adjusted_length, style="color", color=color, auto_format=False),
        MessageStyle(offset=0, length=adjusted_length, style="bold", size="8", auto_format=False)
    ])
    msg = Message(text=text, style=style)
    client.send(msg, thread_id=thread_id, thread_type=thread_type, ttl=ttl)

def schedule_disperse(client, thread_id, thread_type, group_id):
    """Lên lịch giải tán nhóm sau 60 giây."""
    global global_state
    msg = f"⚠️ Nhóm với ID: {group_id} sẽ được giải tán sau 60 giây. Nhập '{PREFIX}group.cancel' để hủy."
    send_message_with_style(client, msg, thread_id, thread_type, color="#ffcc00", ttl=60000)
    
    global_state.update({
        "state": "pending_disperse",
        "group_id": group_id,
        "thread_id": thread_id,
        "thread_type": thread_type,
        "timestamp": time.time()
    })
    timer = threading.Timer(60.0, execute_disperse, args=(client, group_id, thread_id, thread_type))
    timer.start()

def execute_disperse(client, group_id, thread_id, thread_type):
    """Thực thi giải tán nhóm sau khi hết thời gian chờ."""
    global global_state
    try:
        if global_state.get('state') == 'pending_disperse' and global_state.get('group_id') == group_id:
            result = client.disperseGroup(group_id)
            print(f"disperseGroup response: {result}")
            if isinstance(result, dict) and "error_code" in result:
                send_message_with_style(client, f"🔴 Lỗi: {result.get('error_message', 'Không giải tán được nhóm')}", thread_id, thread_type)
            else:
                msg = f"🗑️ Đã giải tán nhóm với ID: {group_id}"
                send_message_with_style(client, msg, thread_id, thread_type)
            global_state.clear()
    except ZaloAPIException as e:
        print(f"ZaloAPIException trong disperseGroup: {str(e)}")
        send_message_with_style(client, f"🔴 Lỗi: {str(e)}", thread_id, thread_type)
        global_state.clear()
    except Exception as e:
        print(f"Lỗi bất ngờ trong disperseGroup: {str(e)}")
        send_message_with_style(client, "🔴 Đã xảy ra lỗi khi giải tán nhóm", thread_id, thread_type)
        global_state.clear()

def handle_grouplink_command(client, thread_id):
    """Lấy link nhóm từ Zalo API."""
    try:
        group_link = client.getGroupLink(chatID=thread_id)
        print("Dữ liệu từ Zalo API:", group_link)
        if group_link.get("error_code") == 0:
            data = group_link.get("data")
            if isinstance(data, dict):
                if data.get('link'):
                    return data['link']
                elif data.get('url'):
                    return data['url']
                else:
                    return None
            elif isinstance(data, str):
                return data
            else:
                return None
        else:
            print(f"Lỗi từ Zalo API: {group_link.get('error_message', 'Lỗi không xác định')}")
            return None
    except ValueError as e:
        print(f"Lỗi: Cần có Group ID: {str(e)}")
        return None
    except Exception as e:
        print(f"Đã xảy ra lỗi khi lấy link nhóm: {str(e)}")
        return None

def handle_group_manager_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý các lệnh quản lý nhóm: group.creat, group.del, group.cancel."""
    global global_state
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    
    msg_error = "🔴 Cú pháp đúng: group.creat <tên nhóm> [<UID hoặc @tag>] hoặc danh sách UID; group.del [groupID]; group.cancel để hủy giải tán"
    msg_not_admin = "🔴 Chỉ admin mới có quyền sử dụng lệnh này!"
    msg_not_group = "🔴 Lệnh group.del không có groupID phải được sử dụng trong một nhóm!"
    msg_cancel = "❎ Đã hủy giải tán nhóm."
    
    # Kiểm tra quyền admin
    if str(author_id) != ADMIN_ID:
        send_message_with_style(client, msg_not_admin, thread_id, thread_type)
        return

    try:
        command_parts = message.strip().split()
        if not command_parts or command_parts[0] not in [f"{PREFIX}group.creat", f"{PREFIX}group.del", f"{PREFIX}group.cancel"]:
            send_message_with_style(client, msg_error, thread_id, thread_type)
            return

        if command_parts[0] == f"{PREFIX}group.creat":
            if len(command_parts) < 2:
                send_message_with_style(client, msg_error, thread_id, thread_type)
                return
            
            # Lấy tên nhóm
            group_name_parts = []
            i = 1
            while i < len(command_parts) and not command_parts[i].isnumeric() and not command_parts[i].startswith('@'):
                group_name_parts.append(command_parts[i])
                i += 1
            group_name = ' '.join(group_name_parts) if group_name_parts else command_parts[1]
            
            # Lấy danh sách thành viên
            members = []
            if message_object.mentions:
                members = [mention['uid'] for mention in message_object.mentions]
            if i < len(command_parts) and command_parts[i].isnumeric():
                members.append(command_parts[i])
            lines = message.strip().split('\n')
            if len(lines) > 1:
                for line in lines[1:]:
                    if line.strip().isnumeric():
                        members.append(line.strip())

            # Thêm thành viên mặc định
            if DEFAULT_MEMBER_ID not in members:
                members.append(DEFAULT_MEMBER_ID)

            if not members:
                send_message_with_style(client, "🔴 Vui lòng cung cấp ít nhất một UID hoặc @tag (ngoài UID mặc định)!", thread_id, thread_type)
                return

            try:
                result = client.createGroup(name=group_name, members=members, createLink=1)
                print(f"createGroup response: {result}")
                if isinstance(result, dict) and "groupId" in result and result["groupId"]:
                    group_id = str(result["groupId"])
                    
                    # Lấy thông tin chi tiết nhóm vừa tạo
                    try:
                        group_info = client.fetchGroupInfo(group_id).gridInfoMap.get(group_id)
                        group_link = handle_grouplink_command(client, group_id)
                        
                        if group_info:
                            created_time = datetime.fromtimestamp(group_info.createdTime / 1000).strftime('%H:%M %d/%m/%Y')
                            total_members = str(group_info.totalMember)
                            creator_name = client.fetchUserInfo(group_info.creatorId).changed_profiles.get(group_info.creatorId).zaloName
                            
                            # Tạo thông báo chi tiết
                            msg = (
                                f"🎉 Đã tạo nhóm '{group_name}' với thông tin chi tiết:\n"
                                f"🆔 ID: {group_id}\n"
                            )
                            if group_link:
                                msg += f"🔗 Link nhóm: {group_link}\n"
                            else:
                                msg += f"🔗 Link nhóm: Không lấy được link\n"
                            msg += (
                                f"👥 Số thành viên: {total_members}\n"
                                f"👑 Chủ nhóm: {creator_name}\n"
                                f"⏰ Thời gian tạo: {created_time}"
                            )
                            send_message_with_style(client, msg, thread_id, thread_type, color="#00ff00")
                        else:
                            # Fallback nếu không lấy được thông tin nhóm
                            msg = f"🎉 Đã tạo nhóm '{group_name}' với ID: {group_id}"
                            if group_link:
                                msg += f"\n🔗 Link nhóm: {group_link}"
                            send_message_with_style(client, msg, thread_id, thread_type, color="#00ff00")
                    except Exception as e:
                        print(f"Lỗi khi lấy thông tin nhóm hoặc link: {str(e)}")
                        # Fallback thông báo cơ bản
                        msg = f"🎉 Đã tạo nhóm '{group_name}' với ID: {group_id}"
                        if group_link:
                            msg += f"\n🔗 Link nhóm: {group_link}"
                        send_message_with_style(client, msg, thread_id, thread_type, color="#00ff00")
                elif isinstance(result, dict) and "error_code" in result:
                    send_message_with_style(client, f"🔴 Lỗi: {result.get('error_message', 'Không tạo được nhóm')}", thread_id, thread_type)
                else:
                    print(f"Phản hồi createGroup không hợp lệ: {result}")
                    send_message_with_style(client, "🔴 Lỗi: Không thể lấy ID nhóm, vui lòng thử lại!", thread_id, thread_type)
            except ZaloAPIException as e:
                print(f"ZaloAPIException trong createGroup: {str(e)}")
                send_message_with_style(client, f"🔴 Lỗi: {str(e)}", thread_id, thread_type)
            except Exception as e:
                print(f"Lỗi bất ngờ trong createGroup: {str(e)}")
                send_message_with_style(client, "🔴 Đã xảy ra lỗi khi tạo nhóm", thread_id, thread_type)

        elif command_parts[0] == f"{PREFIX}group.del":
            group_id = None
            if len(command_parts) == 2 and command_parts[1].isnumeric():
                group_id = command_parts[1]
            elif len(command_parts) == 1 and thread_type == ThreadType.GROUP:
                group_id = thread_id
            else:
                print(f"Failed group.del: thread_type={thread_type} is not ThreadType.GROUP or no groupID provided")
                send_message_with_style(client, msg_not_group, thread_id, thread_type)
                return
            
            if not group_id or not str(group_id).isnumeric():
                send_message_with_style(client, "🔴 ID nhóm không hợp lệ!", thread_id, thread_type)
                return

            if global_state.get('state') == 'pending_disperse':
                send_message_with_style(client, "🔴 Vui lòng hủy hoặc chờ hành động giải tán trước đó hoàn tất!", thread_id, thread_type)
                return

            schedule_disperse(client, thread_id, thread_type, group_id)

        elif command_parts[0] == f"{PREFIX}group.cancel":
            if global_state.get('state') == 'pending_disperse':
                global_state.clear()
                send_message_with_style(client, msg_cancel, thread_id, thread_type)
            else:
                send_message_with_style(client, "🔴 Không có yêu cầu giải tán nhóm nào đang chờ!", thread_id, thread_type)

    except Exception as e:
        print(f"Lỗi bất ngờ trong handle_group_manager_command: {str(e)}")
        send_message_with_style(client, "🔴 Đã xảy ra lỗi", thread_id, thread_type)

def get_mitaizl():
    """Trả về danh sách các lệnh được hỗ trợ."""
    return {
        'group.creat': handle_group_manager_command,
        'group.del': handle_group_manager_command,
        'group.cancel': handle_group_manager_command
    }