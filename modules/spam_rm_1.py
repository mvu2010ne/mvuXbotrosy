from zlapi.models import Message, MessageStyle, MultiMsgStyle, ZaloAPIException
import os
import random
import re
from config import ADMIN
import time

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Đổi tên nhóm Zalo một lần bằng nội dung ngẫu nhiên từ file 'noidung.txt'.",
    'tính năng': [
        "🔍 Kiểm tra quyền hạn của người dùng trước khi thực hiện lệnh",
        "📄 Đọc nội dung từ file 'noidung.txt' để sử dụng làm tên nhóm",
        "🔄 Chọn ngẫu nhiên một dòng từ file để đổi tên nhóm",
        "✅ Thực hiện đổi tên nhóm chỉ một lần mỗi khi gọi lệnh",
        "🔗 Hỗ trợ đổi tên nhóm theo ID nhóm hoặc link nhóm",
        "📩 Thông báo kết quả ngay lập tức"
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh 'spam.rename.once' để đổi tên nhóm hiện tại.",
        "📩 Gửi 'spam.rename.once {group_id}' để đổi tên nhóm với ID cụ thể.",
        "📩 Gửi 'spam.rename.once {group_link}' để đổi tên nhóm từ link mời.",
        "📌 Ví dụ: 'spam.rename.once', 'spam.rename.once 123456789', 'spam.rename.once https://zalo.me/g/abc123'.",
        "✅ Nhận thông báo trạng thái và kết quả ngay lập tức."
    ]
}

def send_message_with_style(client, text, thread_id, thread_type, color="#db342e"):
    """
    Gửi tin nhắn với định dạng màu sắc và in đậm.
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
            style="bold",
            size="8",
            auto_format=False
        )
    ])
    client.send(Message(text=text, style=style), thread_id=thread_id, thread_type=thread_type)

def extract_group_id_from_link(client, link):
    """
    Trích xuất group_id từ link nhóm bằng cách gọi API Zalo (getiGroup).
    """
    try:
        print(f"[INFO] Đang lấy thông tin nhóm từ: {link}")
        group_info = client.getiGroup(link)
        time.sleep(1)  # Thêm độ trễ để tránh lỗi API, như trong group_getid.py
        if isinstance(group_info, dict) and 'groupId' in group_info:
            group_id = group_info['groupId']
            print(f"[SUCCESS] Lấy được Group ID {group_id} từ: {link}")
            return group_id
        else:
            print(f"[ERROR] Không lấy được thông tin nhóm từ: {link}")
            return None
    except ZaloAPIException as e:
        print(f"[EXCEPTION] Lỗi API khi trích xuất group_id: {str(e)}")
        return None
    except Exception as e:
        print(f"[EXCEPTION] Lỗi khi trích xuất group_id: {str(e)}")
        return None

def handle_renamegr_command(message, message_object, thread_id, thread_type, author_id, client):
    if author_id not in ADMIN:
        send_message_with_style(
            client,
            "⭕ Lệnh dùng để đổi tên nhóm\n❌ Bạn không có quyền sử dụng",
            thread_id,
            thread_type
        )
        return

    # Phân tích lệnh
    command_parts = message.split(maxsplit=1)
    target_id = thread_id  # Mặc định là nhóm hiện tại

    if len(command_parts) > 1:
        argument = command_parts[1].strip()
        # Kiểm tra xem argument có phải là link nhóm không
        if re.match(r"https?://zalo\.me/g/", argument):
            target_id = extract_group_id_from_link(client, argument)
            if not target_id:
                send_message_with_style(
                    client,
                    "❌ Không thể trích xuất ID nhóm từ link. Vui lòng kiểm tra lại link.",
                    thread_id,
                    thread_type
                )
                return
        else:
            # Giả sử argument là group_id
            target_id = argument

    try:
        with open("noidung.txt", "r", encoding="utf-8") as file:
            names = file.readlines()
    except FileNotFoundError:
        send_message_with_style(
            client,
            "Không tìm thấy file noidung.txt.",
            thread_id,
            thread_type
        )
        return

    if not names:
        send_message_with_style(
            client,
            "File noidung.txt không có nội dung nào để gửi.",
            thread_id,
            thread_type
        )
        return

    # Select a random name from the file
    new_name = random.choice(names).strip()
    try:
        client.changeGroupName(new_name, target_id)
        send_message_with_style(
            client,
            f"✅ Đã đổi tên nhóm (ID: {target_id}) thành: {new_name}",
            thread_id,
            thread_type
        )
    except ZaloAPIException as e:
        send_message_with_style(
            client,
            f"❌ Lỗi API khi đổi tên nhóm: {str(e)}",
            thread_id,
            thread_type
        )
    except Exception as e:
        send_message_with_style(
            client,
            f"❌ Lỗi khi đổi tên nhóm: {str(e)}",
            thread_id,
            thread_type
        )

def get_mitaizl():
    return {
        'spam.rm.1': handle_renamegr_command
    }