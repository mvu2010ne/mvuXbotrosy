import os
import time
from zlapi.models import Message
from config import ADMIN

# ===========================
# Mô tả lệnh cho menu bot
# ===========================
des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🔍 Tìm kiếm chuỗi trong các tập lệnh Python, hiển thị toàn bộ nội dung file chứa chuỗi, với tiến trình quét in ra console.",
    'tính năng': [
        "📜 Tìm kiếm chuỗi trong tất cả file .py trong thư mục được chỉ định (mặc định: toàn dự án).",
        "📄 Hiển thị toàn bộ nội dung của file chứa chuỗi khớp.",
        "📂 Hỗ trợ tùy chọn quét thư mục cụ thể với --dir.",
        "✂️ Chia nhỏ nội dung file thành nhiều tin nhắn nếu quá dài.",
        "🔍 In tiến trình quét file ra console để theo dõi và phát hiện lỗi.",
        "🔐 Yêu cầu quyền admin để sử dụng.",
        "⚠️ Báo cáo lỗi chi tiết nếu không tìm thấy chuỗi hoặc có vấn đề khi đọc file."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh code.fullsearch <chuỗi cần tìm> để quét toàn bộ dự án.",
        "📩 Gửi code.fullsearch --dir <đường dẫn> <chuỗi cần tìm> để quét thư mục cụ thể.",
        "📌 Ví dụ: code.fullsearch api login",
        "📌 Ví dụ: code.fullsearch --dir modules api login",
        "✅ Nhận toàn bộ nội dung file chứa chuỗi, với tiến trình quét in ra console."
    ]
}

# ===========================
# Cấu hình
# ===========================
MAX_MESSAGE_LENGTH = 500
SEND_DELAY_SECONDS = 1  # Chờ 1 giây giữa các tin nhắn để tránh spam

# ===========================
# Hàm kiểm tra quyền admin
# ===========================
def is_admin(author_id):
    return author_id in ADMIN

# ===========================
# Tìm kiếm chuỗi trong .py và trả về nội dung file
# ===========================
def search_and_get_full_file(search_string, search_dir=".", client=None, thread_id=None, thread_type=None):
    results = []
    file_count = 0
    error_log = []

    try:
        total_files = sum(
            1 for root, _, files in os.walk(search_dir) for file_name in files if file_name.endswith(".py")
        )
        if total_files == 0:
            print(f"[INFO] Không tìm thấy file .py nào trong '{search_dir}'.")
            client.sendMessage(
                Message(text=f"❌ Không tìm thấy file .py nào trong '{search_dir}'."),
                thread_id, thread_type
            )
            return results

        print(f"[INFO] Bắt đầu quét {total_files} file .py trong '{search_dir}'...")

        for root, _, files in os.walk(search_dir):
            for file_name in files:
                if file_name.endswith(".py"):
                    file_count += 1
                    file_path = os.path.join(root, file_name)
                    rel_path = os.path.relpath(file_path, search_dir)
                    print(f"[PROGRESS] Đang quét file {file_count}/{total_files}: {rel_path}")

                    try:
                        with open(file_path, 'r', encoding='utf-8') as file:
                            content = file.read()
                            if search_string.lower() in content.lower():
                                print(f"[DEBUG] Tìm thấy chuỗi '{search_string}' trong file {rel_path}")
                                results.append({
                                    'file': rel_path,
                                    'content': content
                                })
                            else:
                                print(f"[DEBUG] Không tìm thấy chuỗi '{search_string}' trong file {rel_path}")
                    except Exception as e:
                        error_log.append(f"File {rel_path}: Lỗi khi đọc - {str(e)}")
                        results.append({
                            'file': rel_path,
                            'content': f"Lỗi khi đọc file: {str(e)}"
                        })

        print(f"[DEBUG] Tổng số file chứa chuỗi '{search_string}': {len(results)}")
        if error_log:
            print("[ERROR] Các lỗi trong quá trình quét:")
            for error in error_log:
                print(f"  {error}")
            client.sendMessage(
                Message(text="⚠️ Các lỗi trong quá trình quét:\n" + "\n".join(error_log)),
                thread_id, thread_type,
                ttl=60000
            )
        else:
            print("[INFO] Hoàn tất quét tất cả file!")
            client.sendMessage(
                Message(text="✅ Hoàn tất quét tất cả file!"),
                thread_id, thread_type,
                ttl=60000
            )

        if not results:
            print(f"[INFO] Không tìm thấy '{search_string}' trong bất kỳ file nào.")
            client.sendMessage(
                Message(text=f"❌ Không tìm thấy '{search_string}' trong bất kỳ file nào trong '{search_dir}'."),
                thread_id, thread_type,
                ttl=60000
            )

        return results
    except Exception as e:
        print(f"[ERROR] Lỗi khi quét thư mục: {str(e)}")
        client.sendMessage(
            Message(text=f"❌ Lỗi khi quét thư mục: {str(e)}"),
            thread_id, thread_type
        )
        return [{'file': None, 'content': f"Lỗi khi quét thư mục: {str(e)}"}]

# ===========================
# Hàm chia nhỏ nội dung file
# ===========================
def split_content(content, file_name):
    """Chia nội dung file thành các phần nhỏ hơn MAX_MESSAGE_LENGTH, trả về danh sách tin nhắn."""
    lines = content.splitlines()
    chunks = []
    current_chunk = ""
    current_length = 0

    for line in lines:
        line_length = len(line) + 1
        if current_length + line_length > MAX_MESSAGE_LENGTH:
            chunks.append(current_chunk)
            current_chunk = ""
            current_length = 0
        current_chunk += line + "\n"
        current_length += line_length

    if current_chunk.strip():
        chunks.append(current_chunk)

    # Thêm heading chuẩn
    total_parts = len(chunks)
    final_chunks = []
    for idx, chunk in enumerate(chunks, start=1):
        header = f"📄 File: {file_name} (Phần {idx}/{total_parts})\n"
        final_chunks.append(header + chunk)

    return final_chunks

# ===========================
# Xử lý lệnh fullsearch
# ===========================
def handle_fullsearch_command(message, message_object, thread_id, thread_type, author_id, client):
    parts = message.strip().split(" ")
    search_dir = "."
    search_string = ""

    if len(parts) < 2:
        client.replyMessage(
            Message(text="Vui lòng nhập: code.fullsearch [--dir <đường dẫn>] <chuỗi cần tìm>"),
            message_object, thread_id, thread_type
        )
        return

    if parts[1] == "--dir":
        if len(parts) < 4:
            client.replyMessage(
                Message(text="Vui lòng cung cấp thư mục và chuỗi cần tìm: code.fullsearch --dir <đường dẫn> <chuỗi>"),
                message_object, thread_id, thread_type
            )
            return
        search_dir = parts[2].strip()
        search_string = " ".join(parts[3:]).strip()
    else:
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

    if not os.path.isdir(search_dir):
        print(f"[ERROR] Thư mục '{search_dir}' không tồn tại!")
        client.replyMessage(
            Message(text=f"❌ Thư mục '{search_dir}' không tồn tại!"),
            message_object, thread_id, thread_type
        )
        return

    print(f"[INFO] Đang tìm kiếm '{search_string}' trong '{search_dir}'...")
    client.sendMessage(
        Message(text=f"⏳ Đang tìm kiếm '{search_string}' và lấy nội dung file trong '{search_dir}'..."),
        thread_id, thread_type
    )

    results = search_and_get_full_file(search_string, search_dir, client, thread_id, thread_type)
    
    print(f"[DEBUG] Kết quả tìm kiếm: {len(results)} file được tìm thấy")
    if not results or (results and results[0]['file'] is None):
        print(f"[INFO] Không tìm thấy '{search_string}' trong bất kỳ tập lệnh nào trong '{search_dir}'.")
        client.replyMessage(
            Message(text=f"❌ Không tìm thấy '{search_string}' trong bất kỳ tập lệnh nào trong '{search_dir}'."),
            message_object, thread_id, thread_type
        )
        return

    for res in results:
        print(f"[DEBUG] Xử lý file: {res['file']}, độ dài nội dung: {len(res['content'])} ký tự")
        if "Lỗi" in res['content']:
            print(f"[DEBUG] Gửi lỗi cho file {res['file']}")
            client.sendMessage(
                Message(text=f"📄 File: {res['file']}\n⚠ {res['content']}"),
                thread_id, thread_type,
                ttl=60000
            )
            time.sleep(SEND_DELAY_SECONDS)
            continue

        chunks = split_content(res['content'], res['file'])
        print(f"[DEBUG] File {res['file']} được chia thành {len(chunks)} phần")
        for chunk in chunks:
            print(f"[DEBUG] Gửi phần nội dung: {chunk[:100]}...")
            client.sendMessage(
                Message(text=chunk),
                thread_id, thread_type,
                ttl=60000
            )
            time.sleep(SEND_DELAY_SECONDS)

# ===========================
# Đăng ký lệnh cho bot
# ===========================
def get_mitaizl():
    return {
        'code.fullsearch/': handle_fullsearch_command
    }
