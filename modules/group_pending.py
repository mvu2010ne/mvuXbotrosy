from zlapi.models import Message, MultiMsgStyle, MessageStyle
from config import ADMIN, PREFIX
from datetime import datetime
from zlapi import ZaloAPIException

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Hiển thị danh sách ID và ngày tạo tài khoản của các thành viên đang chờ duyệt trong nhóm Zalo bằng tin nhắn văn bản, chia thành nhiều phần nếu quá dài.",
    'tính năng': [
        "📋 Liệt kê tên, ID và ngày tạo tài khoản của các thành viên đang chờ duyệt.",
        "📩 Gửi tin nhắn văn bản với định dạng đơn giản, chia thành nhiều phần nếu vượt giới hạn.",
        "🔒 Chỉ quản trị viên hoặc chủ nhóm mới có quyền sử dụng.",
        "⚠️ Thông báo nếu không có thành viên chờ duyệt hoặc xảy ra lỗi."
    ],
    'hướng dẫn sử dụng': [
        f"📩 Gửi lệnh `{PREFIX}group.pending` để xem danh sách.",
        "📢 Nhận tin nhắn chứa tên, ID và ngày tạo tài khoản của các thành viên."
    ]
}

# Giới hạn độ dài tin nhắn (ký tự)
MAX_MESSAGE_LENGTH = 1000

def handle_pending_members_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        # Gửi phản ứng
        client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)

        # Lấy thông tin nhóm
        group_info = client.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
        creator_id = group_info.get('creatorId')
        admin_ids = group_info.get('adminIds', []) or []

        # Xác định quản trị viên
        all_admin_ids = set(admin_ids)
        all_admin_ids.add(creator_id)
        all_admin_ids.update(ADMIN)
        all_admin_ids.add("3299675674241805615")

        # Kiểm tra quyền
        if author_id not in all_admin_ids:
            error_message = "Bạn không có quyền sử dụng lệnh này."
            style_error = MultiMsgStyle([
                MessageStyle(offset=0, length=len(error_message), style="color", color="#db342e", auto_format=False),
                MessageStyle(offset=0, length=len(error_message), style="bold", size="16", auto_format=False),
            ])
            client.replyMessage(Message(text=error_message, style=style_error), message_object, thread_id, thread_type, ttl=30000)
            return

        # Lấy danh sách thành viên chờ duyệt
        pending_members = group_info.pendingApprove.get('uids', [])

        # Nếu không có thành viên chờ duyệt
        if not pending_members:
            no_pending = "Bot không có quyền trong nhóm hoặc không có thành viên đang chờ duyệt"
            style_no_pending = MultiMsgStyle([
                MessageStyle(offset=0, length=len(no_pending), style="color", color="#db342e", auto_format=False),
                MessageStyle(offset=0, length=len(no_pending), style="font", size="16", auto_format=False),
            ])
            client.replyMessage(Message(text=no_pending, style=style_no_pending), message_object, thread_id, thread_type, ttl=30000)
            return

        # Chuẩn bị danh sách thông tin
        member_info_list = []
        for idx, member_id in enumerate(pending_members, 1):
            try:
                # Lấy thông tin thành viên
                info_response = client.fetchUserInfo(member_id)
                profiles = info_response.unchanged_profiles or info_response.changed_profiles
                info = profiles[str(member_id)]

                # Xử lý ngày tạo tài khoản
                create_time = info.createdTs
                if isinstance(create_time, int):
                    create_time = datetime.fromtimestamp(create_time).strftime("%d/%m/%Y")
                else:
                    create_time = "Không xác định"

                # Tạo chuỗi thông tin
                member_info = (
                    f"{idx} - {info.zaloName}:\n"
                    f"🔣 ID: {info.userId}\n"
                    f"📅 Ngày tạo tài khoản: {create_time}\n"
                    "──────────"
                )
                member_info_list.append(member_info)
            except Exception:
                member_info_list.append(
                    f"{idx} - Không xác định:\n"
                    f"🔣 ID: {member_id}\n"
                    f"⚠️ Lỗi: Không thể lấy thông tin\n"
                    "──────────"
                )

        # Chia tin nhắn thành nhiều phần
        header = f"📋 Danh sách thành viên chờ duyệt ({len(pending_members)}):\n\n"
        messages_to_send = []
        current_message = header
        current_length = len(header)

        for member_info in member_info_list:
            member_length = len(member_info) + 1  # +1 cho ký tự xuống dòng
            # Nếu thêm member_info vượt quá giới hạn
            if current_length + member_length > MAX_MESSAGE_LENGTH:
                messages_to_send.append(current_message)
                current_message = ""  # Bắt đầu tin nhắn mới (không lặp lại header)
                current_length = 0
            current_message += member_info + "\n"
            current_length += member_length

        # Thêm tin nhắn cuối nếu còn nội dung
        if current_message and current_message != header:
            messages_to_send.append(current_message)

        # Gửi từng phần tin nhắn
        for i, msg in enumerate(messages_to_send, 1):
            style_message = MultiMsgStyle([
                MessageStyle(offset=0, length=len(msg), style="color", color="#000000", auto_format=False),
                MessageStyle(offset=0, length=len(msg), style="font", size="3", auto_format=False),
            ])
            client.replyMessage(Message(text=msg.strip(), style=style_message), message_object, thread_id, thread_type, ttl=60000)

    except ZaloAPIException as e:
        error_message = f"🔴 Lỗi API: {str(e)}"
        style_error = MultiMsgStyle([
            MessageStyle(offset=0, length=len(error_message), style="color", color="#db342e", auto_format=False),
            MessageStyle(offset=0, length=len(error_message), style="font", size="3", auto_format=False),
        ])
        client.replyMessage(Message(text=error_message, style=style_error), message_object, thread_id, thread_type, ttl=30000)
    except Exception as e:
        error_message = f"🔴 Lỗi: {str(e)}"
        style_error = MultiMsgStyle([
            MessageStyle(offset=0, length=len(error_message), style="color", color="#db342e", auto_format=False),
            MessageStyle(offset=0, length=len(error_message), style="font", size="3", auto_format=False),
        ])
        client.replyMessage(Message(text=error_message, style=style_error), message_object, thread_id, thread_type, ttl=30000)

def get_mitaizl():
    return {
        'group.pending': handle_pending_members_command
    }