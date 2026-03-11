import json
import os
from zlapi.models import Message
from config import ADMIN

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Quản lý danh sách link API trong file JSON.",
    'tính năng': [
        "➕ Thêm link mới vào file JSON với lệnh api add.",
        "🔍 Kiểm tra số lượng link trong file với lệnh api check.",
        "🔒 Chỉ admin được phép sử dụng lệnh này.",
        "🔔 Gửi thông báo trạng thái với tag người dùng, tự xóa sau 30 giây.",
        "⚠️ Thông báo lỗi nếu file không tồn tại hoặc định dạng sai."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh api add <tên_file> <link> để thêm link.",
        "📩 Gửi lệnh api check <tên_file> để kiểm tra số lượng link.",
        "📌 Ví dụ: api add myapi https://example.com.",
        "✅ Nhận thông báo trạng thái ngay lập tức."
    ]
}

api = "Api/"

if not os.path.exists(api):
    os.makedirs(api)

def handle_api_command(args, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản ứng ngay khi người dùng soạn đúng lệnh
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    
    # Kiểm tra quyền người dùng
    if author_id not in ADMIN:
        response_message = f"@{author_id} Bạn không có quyền thực hiện hành động này!"
        client.sendMessage(Message(text=response_message), thread_id, thread_type, ttl=20000)
        return

    args = args.split()
    if args[0] == '?api':
        args = args[1:]

    # Kiểm tra số lượng tham số
    if len(args) < 2:
        response_message = f"@{author_id} Lệnh không hợp lệ. Vui lòng sử dụng: api add <tên_file> <link> hoặc api check <tên_file>"
    else:
        command = args[0]
        file_name = args[1]
        file_path = os.path.join(api, f"{file_name}.json")

        print(f"DEBUG: command = {command}, file_name = {file_name}, file_path = {file_path}")

        # Thêm link vào file
        if command == "add" and len(args) == 3:
            link = args[2]
            data = []

            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r') as file:
                        data = json.load(file)
                except json.JSONDecodeError:
                    # Đổi thông báo lỗi theo yêu cầu
                    response_message = f"@{author_id} Lỗi: Không thể đọc tệp {file_name}.json."
                    client.sendMessage(Message(text=response_message), thread_id, thread_type, ttl=20000)  # Tin nhắn sẽ tự xóa sau 20 giây
                    return

            data.append(link)
            try:
                with open(file_path, 'w') as file:
                    json.dump(data, file, indent=4)
                response_message = f"@{author_id} Đã thêm link vào {file_name}.json. Tổng cộng: {len(data)} link."
            except IOError:
                response_message = f"@{author_id} Lỗi: Không thể ghi vào tệp {file_name}.json."

        # Kiểm tra số lượng link trong file
        elif command == "check" and len(args) == 2:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r') as file:
                        data = json.load(file)
                    response_message = f"@{author_id} {file_name}.json hiện có {len(data)} link."
                except json.JSONDecodeError:
                    response_message = f"@{author_id} Lỗi: Không thể đọc tệp {file_name}.json."
                    client.sendMessage(Message(text=response_message), thread_id, thread_type, ttl=20000)  # Tin nhắn sẽ tự xóa sau 20 giây
            else:
                response_message = f"@{author_id} Tệp {file_name}.json không tồn tại."

        else:
            response_message = f"@{author_id} Lệnh không hợp lệ hoặc thiếu tham số."

    # Gửi tất cả các tin nhắn với tag vào người dùng và tự xóa sau 30 giây
    client.sendMessage(Message(text=response_message), thread_id, thread_type, ttl=30000)

def get_mitaizl():
    return {
        'api': handle_api_command
    }
