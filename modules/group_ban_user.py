from zlapi.models import Message, MultiMsgStyle, MessageStyle
from config import ADMIN
import time 

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Lệnh để cấm thành viên khỏi nhóm bằng cách tag, reply hoặc nhập user_id với thông báo lịch sự.",
    'tính năng': [
        "🔍 Kiểm tra quyền admin trước khi thực hiện lệnh.",
        "🛠️ Hỗ trợ cấm người dùng bằng cách tag, reply hoặc nhập user_id.",
        "📨 Gửi tin nhắn phản hồi với định dạng màu sắc và ngôn ngữ lịch sự.",
        "📋 Tự động lấy tên người dùng trước khi cấm (nếu có thể).",
        "🔔 Xử lý lỗi và thông báo chi tiết nếu gặp vấn đề khi cấm người dùng."
    ],
    'hướng dẫn sử dụng': [
        "📩 Nhập lệnh 'group.banuser @username' hoặc reply tin nhắn của người cần cấm để loại bỏ thành viên khỏi nhóm.",
        "📌 Ví dụ: group.banuser @username để cấm một thành viên.",
        "✅ Nhận thông báo trạng thái và kết quả với ngôn ngữ lịch sự ngay lập tức."
    ]
}

def handle_ban_user_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản ứng ngay khi người dùng soạn đúng lệnh
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    text = message.split()

    group_info = client.fetchGroupInfo(thread_id)

    if not group_info:
        error_message = "Không thể lấy thông tin nhóm. Vui lòng thử lại sau."
        style_error = MultiMsgStyle(
            [
                MessageStyle(
                    offset=0,
                    length=len(error_message),
                    style="color",
                    color="#db342e",
                    auto_format=False,
                ),
                MessageStyle(
                    offset=0,
                    length=len(error_message),
                    style="bold",
                    size="16",
                    auto_format=False,
                ),
            ]
        )
        client.sendMessage(Message(text=error_message, style=style_error), thread_id, thread_type)
        return

    group_data = group_info.gridInfoMap.get(thread_id)

    if not group_data:
        error_message = "Không tìm thấy thông tin nhóm. Vui lòng kiểm tra lại."
        style_error = MultiMsgStyle(
            [
                MessageStyle(
                    offset=0,
                    length=len(error_message),
                    style="color",
                    color="#db342e",
                    auto_format=False,
                ),
                MessageStyle(
                    offset=0,
                    length=len(error_message),
                    style="bold",
                    size="16",
                    auto_format=False,
                ),
            ]
        )
        client.sendMessage(Message(text=error_message, style=style_error), thread_id, thread_type)
        return

    creator_id = group_data.get('creatorId')
    admin_ids = group_data.get('adminIds', [])

    if admin_ids is None:
        admin_ids = []

    all_admin_ids = set(admin_ids)
    all_admin_ids.add(creator_id)
    all_admin_ids.update(ADMIN)

    user_id = None

    if message_object.mentions:
        user_id = message_object.mentions[0]['uid']
    elif message_object.quote:
        user_id = str(message_object.quote.ownerId)
    else:
        if len(text) < 2:
            error_message = "Vui lòng chỉ định người dùng cần cấm bằng cách tag, reply hoặc nhập user_id."
            style_error = MultiMsgStyle(
                [
                    MessageStyle(
                        offset=0,
                        length=len(error_message),
                        style="color",
                        color="#db342e",
                        auto_format=False,
                    ),
                    MessageStyle(
                        offset=0,
                        length=len(error_message),
                        style="bold",
                        size="16",
                        auto_format=False,
                    ),
                ]
            )
            client.sendMessage(Message(text=error_message, style=style_error), thread_id, thread_type, ttl=60000)
            return
        user_id = text[1]

    if author_id not in all_admin_ids and author_id not in ADMIN:
        error_message = "Xin lỗi, chỉ admin hoặc người tạo nhóm mới có thể sử dụng lệnh này."
        style_error = MultiMsgStyle(
            [
                MessageStyle(
                    offset=0,
                    length=len(error_message),
                    style="color",
                    color="#db342e",
                    auto_format=False,
                ),
                MessageStyle(
                    offset=0,
                    length=len(error_message),
                    style="bold",
                    size="16",
                    auto_format=False,
                ),
            ]
        )
        client.sendMessage(Message(text=error_message, style=style_error), thread_id, thread_type, ttl=10000)
        return

    try:
        author_info = client.fetchUserInfo(user_id)
        if isinstance(author_info, dict) and 'changed_profiles' in author_info:
            user_data = author_info['changed_profiles'].get(user_id, {})
            user_name = user_data.get('zaloName', 'không xác định')
        else:
            user_name = "Người dùng không xác định"

    except Exception as e:
        user_name = "Người dùng không xác định"
    
    try:
        if hasattr(client, 'blockUsersInGroup'):
            response = client.blockUsersInGroup(user_id, thread_id)
            send_message = f"Đã loại bỏ thành viên {user_name} khỏi nhóm thành công."
        else:
            send_message = "Không thể thực hiện lệnh do lỗi hệ thống. Vui lòng thử lại sau."

    except Exception as e:
        send_message = f"Đã xảy ra lỗi khi loại bỏ thành viên: {str(e)}"

    style_message = MultiMsgStyle(
        [
            MessageStyle(
                offset=0,
                length=len(send_message),
                style="color",
                color="#db342e",
                auto_format=False,
            ),
            MessageStyle(
                offset=0,
                length=len(send_message),
                style="bold",
                size="16",
                auto_format=False,
            ),
        ]
    )

    gui = Message(text=send_message, style=style_message)
    client.sendMessage(gui, thread_id, thread_type, ttl=20000)

def get_mitaizl():
    return {
        'group.banuser': handle_ban_user_command
    }