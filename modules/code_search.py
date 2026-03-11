import os
import re
from zlapi.models import Message
from config import ADMIN

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🔍 Tìm kiếm một chuỗi nội dung trong các tập lệnh Python, hỗ trợ quét nhiều thư mục.",
    'tính năng': [
        "📜 Tìm kiếm chuỗi trong tất cả file .py trong thư mục được chỉ định (mặc định: toàn dự án).",
        "📍 Trả về tên file, số dòng, và nội dung dòng chứa chuỗi khớp.",
        "📂 Hỗ trợ tùy chọn quét thư mục cụ thể với --dir.",
        "✂️ Chia nhỏ kết quả nếu quá dài để gửi thành nhiều tin nhắn.",
        "🔐 Yêu cầu quyền admin để sử dụng.",
        "⚠️ Thông báo lỗi nếu không tìm thấy chuỗi hoặc có vấn đề khi đọc file."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh code.search <chuỗi cần tìm> để quét toàn bộ dự án.",
        "📩 Gửi code.search --dir <đường dẫn> <chuỗi cần tìm> để quét thư mục cụ thể.",
        "📌 Ví dụ: code.search api login",
        "📌 Ví dụ: code.search --dir modules api login",
        "✅ Nhận danh sách file và vị trí chứa chuỗi, chia nhỏ nếu cần."
    ]
}

MAX_MESSAGE_LENGTH = 2000  # Giới hạn ký tự mỗi tin nhắn

def is_admin(author_id):
    return author_id in ADMIN

def search_in_files(search_string, search_dir="."):
    """Tìm kiếm chuỗi trong tất cả file .py trong thư mục được chỉ định."""
    results = []
    
    try:
        # Quét đệ quy tất cả thư mục và file
        for root, _, files in os.walk(search_dir):
            for file_name in files:
                if file_name.endswith(".py"):
                    file_path = os.path.join(root, file_name)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as file:
                            lines = file.readlines()
                            for line_num, line in enumerate(lines, 1):
                                # Tìm kiếm không phân biệt hoa thường
                                if search_string.lower() in line.lower():
                                    results.append({
                                        'file': os.path.relpath(file_path, search_dir),
                                        'line': line_num,
                                        'content': line.strip()
                                    })
                    except Exception as e:
                        results.append({
                            'file': os.path.relpath(file_path, search_dir),
                            'line': -1,
                            'content': f"Lỗi khi đọc file: {str(e)}"
                        })
        return results
    except Exception as e:
        return [{'file': None, 'line': -1, 'content': f"Lỗi khi quét thư mục: {str(e)}"}]

def split_content(content):
    """Chia nhỏ nội dung thành các phần nhỏ hơn MAX_MESSAGE_LENGTH."""
    lines = content.splitlines()
    chunks = []
    current_chunk = ""
    current_length = 0

    for line in lines:
        line_length = len(line) + 1  # +1 cho ký tự xuống dòng
        if current_length + line_length > MAX_MESSAGE_LENGTH:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
                current_length = 0
        current_chunk += line + "\n"
        current_length += line_length

    if current_chunk:
        chunks.append(current_chunk)

    return chunks

def handle_searchcode_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh searchcode để tìm chuỗi nội dung trong các tập lệnh."""
    # Tách lệnh thủ công để xử lý chuỗi tìm kiếm có dấu cách
    parts = message.strip().split(" ")
    search_dir = "."  # Mặc định quét từ thư mục gốc
    search_string = ""

    if len(parts) < 2:
        client.replyMessage(
            Message(text="Vui lòng nhập: code.search [--dir <đường dẫn>] <chuỗi cần tìm>"),
            message_object, thread_id, thread_type
        )
        return

    if parts[1] == "--dir":
        if len(parts) < 4:
            client.replyMessage(
                Message(text="Vui lòng cung cấp thư mục và chuỗi cần tìm: code.search --dir <đường dẫn> <chuỗi>"),
                message_object, thread_id, thread_type
            )
            return
        search_dir = parts[2].strip()
        # Lấy toàn bộ chuỗi sau --dir <thư mục> làm chuỗi tìm kiếm
        search_string = " ".join(parts[3:]).strip()
    else:
        # Không có --dir, lấy toàn bộ chuỗi sau parts[1]
        search_string = " ".join(parts[1:]).strip()

    if not search_string:
        client.replyMessage(
            Message(text="❌ Vui lòng cung cấp chuỗi cần tìm!"),
            message_object, thread_id, thread_type
        )
        return

    if not is_admin(author_id):
        client.replyMessage(
            Message(text="• Bạn không có quyền sử dụng lệnh này."),
            message_object, thread_id, thread_type
        )
        return

    # Kiểm tra thư mục tồn tại
    if not os.path.isdir(search_dir):
        client.replyMessage(
            Message(text=f"❌ Thư mục '{search_dir}' không tồn tại!"),
            message_object, thread_id, thread_type
        )
        return

    # Thông báo đang tìm kiếm
    client.sendMessage(
        Message(text=f"⏳ Đang tìm kiếm '{search_string}' trong thư mục '{search_dir}'..."),
        thread_id, thread_type
    )

    # Tìm kiếm
    results = search_in_files(search_string, search_dir)
    
    if not results or (results and results[0]['file'] is None):
        client.replyMessage(
            Message(text=f"❌ Không tìm thấy '{search_string}' trong bất kỳ tập lệnh nào trong '{search_dir}'."),
            message_object, thread_id, thread_type
        )
        return

    # Tạo nội dung kết quả
    result_text = f"🔍 Kết quả tìm kiếm cho '{search_string}' trong '{search_dir}':\n"
    for res in results:
        if res['line'] == -1:
            result_text += f"📄 File: {res['file']}\n⚠ Lỗi: {res['content']}\n\n"
        else:
            result_text += f"📄 File: {res['file']}\n📍 Dòng {res['line']}: {res['content']}\n\n"

    # Chia nhỏ nội dung nếu cần
    chunks = split_content(result_text)
    total_parts = len(chunks)

    # Gửi từng phần
    for part, chunk in enumerate(chunks, 1):
        msg = f"🔍 Kết quả tìm kiếm (Phần {part}/{total_parts}):\n{chunk}"
        client.sendMessage(
            Message(text=msg),
            thread_id, thread_type,
            ttl=60000
        )

def get_mitaizl():
    return {
        'code.search/': handle_searchcode_command
    }