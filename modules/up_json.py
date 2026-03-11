import os
import json
import urllib.parse
from zlapi.models import Message
from config import ADMIN


def is_admin(author_id):
    return author_id in ADMIN

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "💾 Lưu link ảnh/video vào tệp JSON.",
    'tính năng': [
        "🔒 Chỉ quản trị viên bot được sử dụng lệnh này.",
        "📥 Lấy link ảnh/video từ tin nhắn reply và lưu vào tệp JSON.",
        "📝 Tạo mới hoặc cập nhật tệp JSON với tên do người dùng chỉ định.",
        "⚠️ Thông báo lỗi nếu không có quyền hoặc dữ liệu không hợp lệ."
    ],
    'hướng dẫn sử dụng': [
        "📩 Reply vào ảnh/video và gửi lệnh upjson <tên file>.",
        "📌 Ví dụ: reply ảnh rồi gửi upjson myfile",
        "✅ Nhận thông báo xác nhận và số lượng URL trong tệp."
    ]
}


def handle_data_command(message, message_object, thread_id, thread_type, author_id, client):
    if not is_admin(author_id):
        client.replyMessage(
            Message(text="• Bạn không đủ quyền hạn để sử dụng lệnh này."),
            message_object, thread_id, thread_type
        )
        return

    command_parts = message.split()
    if len(command_parts) < 2:
        client.sendMessage(
            Message(text="• Vui lòng cung cấp tên file."),
            thread_id=thread_id, thread_type=thread_type, ttl=1000
        )
        return

    file_name = command_parts[1]
    json_file_path = os.path.join("modules", "cache", "data", f"{file_name}.json")

    if os.path.exists(json_file_path):
        client.sendMessage(
            Message(text=f"• Tệp {file_name}.json đã tồn tại. Đang thêm link vào tệp."),
            thread_id=thread_id, thread_type=thread_type, ttl=10000
        )
    else:
        client.sendMessage(
            Message(text=f"• Tệp {file_name}.json không tồn tại. Đang tạo mới."),
            thread_id=thread_id, thread_type=thread_type, ttl=20000
        )
        with open(json_file_path, "w") as json_file:
            json.dump([], json_file)

    if message_object.quote and message_object.quote.attach:
        attach = message_object.quote.attach
        try:
            attach_data = json.loads(attach)
            media_url = attach_data.get('hdUrl') or attach_data.get('href')
            if not media_url:
                raise ValueError("Không tìm thấy URL.")

            media_url = urllib.parse.unquote(media_url.replace("\\/", "/"))
            save_to_json(file_name, media_url)
            url_count = count_urls_in_json(json_file_path)
            client.sendMessage(
                Message(text=f"• Đã thêm link: {media_url} vào {file_name}.json\n• Số lượng URL hiện tại: {url_count}"),
                thread_id=thread_id, thread_type=thread_type, ttl=30000
            )


        except (json.JSONDecodeError, ValueError) as e:
            client.sendMessage(
                Message(text=str(e)),
                thread_id=thread_id, thread_type=thread_type
            )
    else:
        client.sendMessage(
            Message(text="• Reply một ảnh hoặc video để thêm link vào file json."),
            thread_id=thread_id, thread_type=thread_type
        )


def save_to_json(filename, url):
    file_path = f"modules/cache/data/{filename}.json"

    with open(file_path, "r+") as json_file:
        try:
            data = json.load(json_file)
        except json.JSONDecodeError:
            data = []

        data.append(url)

        json_file.seek(0)
        json.dump(data, json_file, indent=4)
        json_file.truncate()

def count_urls_in_json(file_path):
    try:
        with open(file_path, "r") as json_file:
            data = json.load(json_file)
            return len(data)

    except (FileNotFoundError, json.JSONDecodeError):
        return 0


def get_mitaizl():
    return {
        'up.json': handle_data_command
    }