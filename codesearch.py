import os
import logging
from zlapi.models import Message, MultiMsgStyle, MessageStyle
from config import ADMIN
import time  # Thêm import time để sử dụng time.sleep

logger = logging.getLogger("LocalCodeHandler")

class LocalCodeHandler:
    def __init__(self):
        self.max_message_length = 2000
        # Danh sách phần mở rộng file text
        self.text_extensions = {'.py', '.json', '.txt', '.md', '.yaml', '.yml', '.ini', '.cfg'}

    def _apply_style(self, message):
        return MultiMsgStyle(
            [
                MessageStyle(
                    offset=0,
                    length=len(message),
                    style="color",
                    color="#db342e",
                    auto_format=False,
                ),
                MessageStyle(
                    offset=0,
                    length=len(message),
                    style="font",
                    size="16",
                    auto_format=False,
                ),
            ]
        )

    @staticmethod
    def is_admin(author_id):
        return author_id in ADMIN 

    def search_in_files(self, search_string):
        logger.info(f"Tìm kiếm chuỗi: {search_string}")
        results = []
        search_dir = os.path.dirname(os.path.abspath(__file__))
        
        try:
            # Quét đệ quy tất cả file trong thư mục gốc và thư mục con
            for root, dirs, files in os.walk(search_dir):
                # Bỏ qua thư mục __pycache__
                if '__pycache__' in dirs:
                    dirs.remove('__pycache__')
                
                for file_name in files:
                    # Kiểm tra phần mở rộng file
                    file_ext = os.path.splitext(file_name)[1].lower()
                    if file_ext not in self.text_extensions:
                        logger.debug(f"Bỏ qua file không phải text: {file_name}")
                        continue

                    file_path = os.path.join(root, file_name)
                    try:
                        # Thử đọc file với encoding utf-8
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                            lines = file.readlines()
                            for line_num, line in enumerate(lines, 1):
                                if search_string.lower() in line.lower():
                                    # Lấy đường dẫn tương đối
                                    rel_path = os.path.relpath(file_path, search_dir)
                                    results.append({
                                        'file': rel_path,
                                        'line': line_num,
                                        'content': line.strip()
                                    })
                    except Exception as e:
                        rel_path = os.path.relpath(file_path, search_dir)
                        results.append({
                            'file': rel_path,
                            'line': -1,
                            'content': f"Lỗi khi đọc file: {str(e)}"
                        })
            if not results:
                return [{'file': None, 'line': -1, 'content': "Không tìm thấy chuỗi trong bất kỳ file nào."}]
            return results
        except Exception as e:
            return [{'file': None, 'line': -1, 'content': f"Lỗi khi quét thư mục: {str(e)}"}]

    def split_content(self, content):
        lines = content.splitlines()
        chunks = []
        current_chunk = ""
        current_length = 0

        for line in lines:
            line_length = len(line) + 1
            if current_length + line_length > self.max_message_length:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                    current_length = 0
            current_chunk += line + "\n"
            current_length += line_length

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def handle_localcode(self, client, message, message_object, thread_id, thread_type, author_id):
        logger.info(f"Nhận lệnh: {message}")
        parts = message.strip().split(" ", 1)
        
        if len(parts) < 2:
            style = self._apply_style("Vui lòng nhập: code.search <chuỗi cần tìm>")
            client.replyMessage(
                Message(text="Vui lòng nhập: code.search <chuỗi cần tìm>", style=style),
                message_object, thread_id, thread_type
            )
            return

        search_string = parts[1].strip()

        if not search_string:
            style = self._apply_style("❌ Vui lòng cung cấp chuỗi cần tìm!")
            client.replyMessage(
                Message(text="❌ Vui lòng cung cấp chuỗi cần tìm!", style=style),
                message_object, thread_id, thread_type
            )
            return

        if not self.is_admin(author_id):
            style = self._apply_style("• Bạn không có quyền sử dụng lệnh này.")
            client.replyMessage(
                Message(text="• Bạn không có quyền sử dụng lệnh này.", style=style),
                message_object, thread_id, thread_type
            )
            return

        search_dir = os.path.dirname(os.path.abspath(__file__))

        style = self._apply_style(f"⏳ Đang tìm kiếm '{search_string}' trong thư mục '{search_dir}' và các thư mục con...")
        client.sendMessage(
            Message(text=f"⏳ Đang tìm kiếm '{search_string}' trong thư mục '{search_dir}' và các thư mục con...", style=style),
            thread_id, thread_type
        )

        results = self.search_in_files(search_string)
        
        if not results or (results and results[0]['file'] is None):
            style = self._apply_style(f"❌ Không tìm thấy '{search_string}' trong bất kỳ file nào trong '{search_dir}'.")
            client.replyMessage(
                Message(text=f"❌ Không tìm thấy '{search_string}' trong bất kỳ file nào trong '{search_dir}'.", style=style),
                message_object, thread_id, thread_type
            )
            return

        result_text = f"🔍 Kết quả tìm kiếm cho '{search_string}' trong '{search_dir}':\n"
        for res in results:
            if res['line'] == -1:
                result_text += f"📄 File: {res['file']}\n⚠ Lỗi: {res['content']}\n\n"
            else:
                result_text += f"📄 File: {res['file']}\n📍 Dòng {res['line']}: {res['content']}\n\n"

        chunks = self.split_content(result_text)
        total_parts = len(chunks)

        for part, chunk in enumerate(chunks, 1):
            msg = f"🔍 Kết quả tìm kiếm (Phần {part}/{total_parts}):\n{chunk}"
            style = self._apply_style(msg)
            client.sendMessage(
                Message(text=msg, style=style),
                thread_id, thread_type,
                ttl=60000
            )
            time.sleep(1)  # Thêm delay 1 giây giữa các tin nhắn
        logger.info(f"Đã gửi {total_parts} phần kết quả")

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🔍 Tìm kiếm một chuỗi nội dung trong các file text trong dự án (thư mục gốc và thư mục con).",
    'tính năng': [
        "📜 Tìm kiếm chuỗi trong các file text (.py, .json, .txt, v.v.) trong thư mục dự án và các thư mục con.",
        "📍 Trả về tên file, số dòng, và nội dung dòng chứa chuỗi khớp.",
        "✂️ Chia nhỏ kết quả nếu quá dài để gửi thành nhiều tin nhắn.",
        "🔐 Yêu cầu quyền admin để sử dụng.",
        "⚠️ Thông báo lỗi nếu không tìm thấy chuỗi hoặc có vấn đề khi đọc file."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh code.search <chuỗi cần tìm> để quét các file text trong dự án.",
        "📌 Ví dụ: code.search api login",
        "✅ Nhận danh sách file và vị trí chứa chuỗi, chia nhỏ nếu cần."
    ]
}