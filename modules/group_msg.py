from zlapi import ZaloAPIException
from zlapi.models import Message, MessageStyle, MultiMsgStyle
from datetime import datetime
from config import PREFIX
import json

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "📬 Xem danh sách 50 tin nhắn gần nhất trong một nhóm Zalo với tên người gửi chính xác.",
    'tính năng': [
        "📋 Lấy danh sách 50 tin nhắn gần nhất từ group ID.",
        "👤 Hiển thị tên người dùng Zalo chính xác cho từng tin nhắn.",
        "🎨 Hiển thị tên nhóm và tin nhắn với định dạng màu sắc, in đậm.",
        "✅ Hỗ trợ lấy thông tin nhóm và tin nhắn từ group ID nhập tay.",
        "📑 Chia tin nhắn dài thành nhiều phần nếu vượt quá giới hạn.",
        "⚠️ Thông báo lỗi nếu cú pháp sai hoặc không lấy được tin nhắn."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh group.msg <group_id> để xem tin nhắn.",
        "📌 Ví dụ: group.msg 123456789.",
        "✅ Nhận danh sách tin nhắn với tên người gửi và nội dung."
    ]
}

def send_message_with_style(client, text, thread_id, thread_type, ttl=60000, color="#db342e"):
    """Gửi tin nhắn với định dạng màu sắc và in đậm."""
    base_length = len(text)
    adjusted_length = base_length + 355
    style = MultiMsgStyle([
        MessageStyle(offset=0, length=adjusted_length, style="color", color=color, auto_format=False),
        MessageStyle(offset=0, length=adjusted_length, style="bold", size="8", auto_format=False)
    ])
    msg = Message(text=text, style=style)
    client.send(msg, thread_id=thread_id, thread_type=thread_type, ttl=ttl)

def split_message(text, max_length=2000):
    """Chia tin nhắn thành nhiều phần, mỗi phần không vượt quá max_length ký tự."""
    lines = text.split('\n')
    parts = []
    current_part = []
    current_length = 0

    for line in lines:
        line_length = len(line) + 1  # +1 cho ký tự xuống dòng
        if current_length + line_length > max_length:
            parts.append('\n'.join(current_part))
            current_part = [line]
            current_length = line_length
        else:
            current_part.append(line)
            current_length += line_length

    if current_part:
        parts.append('\n'.join(current_part))

    return parts

def handle_viewmsggroup_command(message, message_object, thread_id, thread_type, author_id, client):
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    msg_error = "🔴 Cú pháp đúng: group.msg <group_id>"

    try:
        # Kiểm tra cú pháp và lấy group_id
        group_id = message.strip().split()[1] if len(message.strip().split()) > 1 else None
        if not group_id or not group_id.isnumeric():
            send_message_with_style(client, msg_error, thread_id, thread_type)
            return

        try:
            # Lấy thông tin nhóm
            group_info = client.fetchGroupInfo(group_id).gridInfoMap.get(group_id)
            if not group_info:
                send_message_with_style(client, "Không tìm thấy thông tin nhóm.", thread_id, thread_type)
                return
            group_name = group_info.name

            # Lấy danh sách tin nhắn gần đây trong nhóm (tương tự lệnh src)
            recent_messages = client.getRecentGroup(group_id)
            if not recent_messages or not hasattr(recent_messages, 'groupMsgs'):
                send_message_with_style(client, "Không thể lấy lịch sử tin nhắn nhóm.", thread_id, thread_type)
                return

            messages = recent_messages.groupMsgs[:50]  # Lấy tối đa 50 tin nhắn
            if not messages:
                send_message_with_style(client, "Không tìm thấy tin nhắn nào trong nhóm.", thread_id, thread_type)
                return

            # Cache để lưu thông tin người dùng
            user_cache = {}

            # Xây dựng nội dung trả về
            output = f"📢 Tên nhóm: {group_name}\n{'-' * 20}\n"
            for msg in messages:
                # Xử lý tin nhắn tương tự lệnh src
                sender_id = msg.get('uidFrom', msg.get('senderId', None))
                content = msg.get('content', 'Tin nhắn trống') if isinstance(msg.get('content'), str) else msg.get('content', {}).get('title', 'Tin nhắn trống')

                # Lấy tên người gửi
                sender_name = 'Người dùng ẩn danh'
                if sender_id and sender_id != '0':
                    if sender_id in user_cache:
                        sender_name = user_cache[sender_id]
                    else:
                        try:
                            sender_info = client.fetchUserInfo(sender_id)
                            profiles = getattr(sender_info, 'unchanged_profiles', None) or getattr(sender_info, 'changed_profiles', {})
                            sender_data = profiles.get(str(sender_id), {}) if profiles else {}
                            sender_name = sender_data.get('zaloName', f"Người dùng {sender_id} (Không lấy được zaloName)")
                            user_cache[sender_id] = sender_name
                        except ZaloAPIException as e:
                            sender_name = f"Người dùng {sender_id} (Lỗi API: {str(e)})"
                        except Exception as e:
                            sender_name = f"Người dùng {sender_id} (Lỗi: {str(e)})"

                output += f"{sender_name}: {content}\n"

            # Chia tin nhắn thành nhiều phần nếu quá dài
            message_parts = split_message(output.strip(), max_length=2000)

            # Gửi từng phần tin nhắn
            for i, part in enumerate(message_parts, 1):
                header = f"📬 Phần {i}/{len(message_parts)}\n" if len(message_parts) > 1 else ""
                send_message_with_style(client, f"{header}{part}", thread_id, thread_type)

        except ZaloAPIException as e:
            send_message_with_style(client, f"Lỗi API: {str(e)}", thread_id, thread_type)
        except Exception as e:
            send_message_with_style(client, f"Đã xảy ra lỗi: {str(e)}", thread_id, thread_type)

    except Exception as e:
        send_message_with_style(client, f"Đã xảy ra lỗi: {str(e)}", thread_id, thread_type)

def get_mitaizl():
    return {
        'group.msg': handle_viewmsggroup_command
    }