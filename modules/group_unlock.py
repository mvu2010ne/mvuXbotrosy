import os
import json
import random
from zlapi import ZaloAPI
from zlapi.models import Message

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Mở chặn người dùng trong nhóm",
    'tính năng': [
        "📨 Mở chặn người dùng trong nhóm dựa trên UID.",
        "🔍 Kiểm tra danh sách UID người dùng cần mở chặn.",
        "🛠️ Thực hiện mở chặn người dùng trong nhóm.",
        "🔔 Thông báo lỗi cụ thể nếu có vấn đề xảy ra khi xử lý yêu cầu."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh unlock <UID> để mở chặn người dùng khỏi nhóm.",
        "📌 Ví dụ: unlock 123456789 để mở chặn người dùng có UID 123456789 khỏi nhóm.",
        "✅ Nhận thông báo trạng thái và kết quả ngay lập tức."
    ]
}

def unblock_user_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        user_ids = message.split()[1:]
        if not user_ids:
            client.send(
                Message(text="⚠️ Vui lòng cung cấp ID người dùng cần mở chặn."),
                thread_id=thread_id,
                thread_type=thread_type
            )
            return

        group_id = thread_id
        response = client.unblockUsersInGroup(user_ids, group_id)
        print("API Response:", response)  # Debug phản hồi API

        if response and response.get("error_code", 0) == 0:
            success_message = f"✅ Đã mở chặn {len(user_ids)} người dùng trong nhóm."
            client.send(
                Message(text=success_message),
                thread_id=thread_id,
                thread_type=thread_type
            )
        else:
            error_message = response.get("error_message", "Không rõ lỗi")
            client.send(
                Message(text=f"❌ Lỗi mở chặn: {error_message}"),
                thread_id=thread_id,
                thread_type=thread_type
            )
    except Exception as e:
        client.send(
            Message(text=f"⚠️ Lỗi xảy ra: {str(e)}"),
            thread_id=thread_id,
            thread_type=thread_type
        )

def get_mitaizl():
    return {
        'group.unlock': unblock_user_command
    }
