import os
import requests
from zlapi.models import *
from config import ADMIN

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Gửi link lệnh đến người được tag",
    'tính năng': [
        "📨 Gửi link lệnh đến người được tag trong tin nhắn.",
        "🔒 Kiểm tra quyền admin trước khi thực hiện lệnh.",
        "📤 Tạo link runmocky chứa nội dung lệnh.",
        "🔗 Gửi link lệnh qua tin nhắn tới người được tag."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh send.code <tên lệnh> tag người nhận để gửi link lệnh.",
        "📌 Ví dụ: send.code my_command @user để gửi link lệnh 'my_command' tới người dùng 'user'.",
        "✅ Nhận thông báo trạng thái và kết quả gửi link lệnh ngay lập tức."
    ]
}
ADMIN_ID = "3299675674241805615"

def is_admin(author_id):
    """Kiểm tra người dùng có phải admin không"""
    return author_id == ADMIN_ID

def read_command_content(command_name):
    file_path = f"modules/{command_name}.py"
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        return None

def create_mock_link(code_content):
    url = "https://api.mocky.io/api/mock"
    data = {
        "status": 200,
        "content": code_content,
        "content_type": "application/json",
        "charset": "UTF-8",
        "secret": "Kaito Kid",
        "expiration": "never"
    }
    try:
        with requests.Session() as session:
            response = session.post(url, json=data)
            response.raise_for_status()
            return response.json().get("link"), None
    except requests.RequestException as e:
        return None, str(e)

def handle_sendmdl_command(message, message_object, thread_id, thread_type, author_id, client):
    if not is_admin(author_id):
        client.replyMessage(Message(text="Bạn không có quyền để thực hiện điều này!"), message_object, thread_id, thread_type)
        return
    mentions = message_object.mentions
    if not mentions:
        client.replyMessage(Message(text="Vui lòng tag người cần gửi lệnh."), message_object, thread_id, thread_type)
        return
    command_parts = message.split()
    if len(command_parts) < 2:
        client.replyMessage(Message(text="Vui lòng nhập tên lệnh cần gửi."), message_object, thread_id, thread_type)
        return
    command_name = command_parts[1].strip()
    command_content = read_command_content(command_name)
    if command_content is None:
        client.replyMessage(Message(text=f"Lệnh '{command_name}' không tồn tại."), message_object, thread_id, thread_type)
        return
    mock_url, error = create_mock_link(command_content)
    if error:
        client.replyMessage(Message(text=f"Có lỗi khi tạo link runmocky: {error}"), message_object, thread_id, thread_type)
        return
    target_user_id = mentions[0]['uid']
    gui = f"Gửi lệnh '{command_name}' thành công đến người dùng: {target_user_id}"
    client.send(Message(text=gui), thread_id, thread_type)
    gui = f"Dưới đây là link lệnh '{command_name}': {mock_url}"
    client.send(Message(text=gui), target_user_id, ThreadType.USER)
    if mock_url:
        client.sendRemoteFile(
            fileUrl=mock_url,
            fileName=f"{command_name}.py",
            thread_id=target_user_id,
            thread_type=ThreadType.USER,
            fileSize=None,
            extension="PY"
        )

def get_mitaizl():
    return {'send.code': handle_sendmdl_command}
