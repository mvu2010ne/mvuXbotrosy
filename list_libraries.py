import os
import logging
import re
from zlapi.models import Message, MultiMsgStyle, MessageStyle
from config import ADMIN

logger = logging.getLogger("LibraryListHandler")

class LibraryListHandler:
    def __init__(self):
        self.max_message_length = 2000
        self.text_extensions = {'.py'}  # Chỉ quét file Python

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

    def is_admin(self, author_id):
        logger.info(f"Kiểm tra admin - author_id: {author_id}, ADMIN_ID: {ADMIN}")
        return author_id == ADMIN

    def list_libraries(self):
        logger.info("Bắt đầu liệt kê các thư viện được sử dụng")
        libraries = set()  # Sử dụng set để tránh trùng lặp
        search_dir = os.path.dirname(os.path.abspath(__file__))

        try:
            for root, dirs, files in os.walk(search_dir):
                if '__pycache__' in dirs:
                    dirs.remove('__pycache__')

                for file_name in files:
                    file_ext = os.path.splitext(file_name)[1].lower()
                    if file_ext not in self.text_extensions:
                        logger.debug(f"Bỏ qua file không phải Python: {file_name}")
                        continue

                    file_path = os.path.join(root, file_name)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                            content = file.read()
                            # Tìm các câu lệnh import
                            import_matches = re.findall(r'^\s*(?:import|from\s+\w+\s+import)\s+([a-zA-Z0-9_]+)', content, re.MULTILINE)
                            for lib in import_matches:
                                # Loại bỏ các từ khóa không phải thư viện
                                if lib not in {'as', 'import', 'from'}:
                                    libraries.add(lib)
                    except Exception as e:
                        rel_path = os.path.relpath(file_path, search_dir)
                        logger.error(f"Lỗi khi đọc file {rel_path}: {str(e)}")

            if not libraries:
                return [{'library': None, 'content': "Không tìm thấy thư viện nào trong dự án."}]
            
            return [{'library': lib, 'content': f"Thư viện: {lib}"} for lib in sorted(libraries)]
        except Exception as e:
            return [{'library': None, 'content': f"Lỗi khi quét thư mục: {str(e)}"}]

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

    def handle_listlibraries(self, client, message, message_object, thread_id, thread_type, author_id):
        logger.info(f"Nhận lệnh: {message}")
        
        if not self.is_admin(author_id):
            style = self._apply_style("• Bạn không có quyền sử dụng lệnh này.")
            client.replyMessage(
                Message(text="• Bạn không có quyền sử dụng lệnh này.", style=style),
                message_object, thread_id, thread_type
            )
            return

        search_dir = os.path.dirname(os.path.abspath(__file__))

        style = self._apply_style(f"⏳ Đang liệt kê các thư viện trong thư mục '{search_dir}' và các thư mục con...")
        client.sendMessage(
            Message(text=f"⏳ Đang liệt kê các thư viện trong thư mục '{search_dir}' và các thư mục con...", style=style),
            thread_id, thread_type
        )

        results = self.list_libraries()

        if not results or (results and results[0]['library'] is None):
            style = self._apply_style(f"❌ Không tìm thấy thư viện nào trong '{search_dir}'.")
            client.replyMessage(
                Message(text=f"❌ Không tìm thấy thư viện nào trong '{search_dir}'.", style=style),
                message_object, thread_id, thread_type
            )
            return

        result_text = f"📚 Danh sách thư viện được sử dụng trong '{search_dir}':\n"
        for res in results:
            result_text += f"📌 {res['content']}\n"

        chunks = self.split_content(result_text)
        total_parts = len(chunks)

        for part, chunk in enumerate(chunks, 1):
            msg = f"📚 Danh sách thư viện (Phần {part}/{total_parts}):\n{chunk}"
            style = self._apply_style(msg)
            client.sendMessage(
                Message(text=msg, style=style),
                thread_id, thread_type,
                ttl=60000
            )
        logger.info(f"Đã gửi {total_parts} phần kết quả")

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "📚 Liệt kê tất cả các thư viện Python được sử dụng trong dự án.",
    'tính năng': [
        "📜 Quét tất cả file .py trong thư mục dự án và các thư mục con.",
        "📍 Liệt kê các thư viện được import trong mã nguồn.",
        "✂️ Chia nhỏ kết quả nếu quá dài để gửi thành nhiều tin nhắn.",
        "🔐 Yêu cầu quyền admin để sử dụng.",
        "⚠️ Thông báo lỗi nếu không tìm thấy thư viện hoặc có vấn đề khi đọc file."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh list.libraries để liệt kê các thư viện trong dự án.",
        "📌 Ví dụ: list.libraries",
        "✅ Nhận danh sách các thư viện được sử dụng, chia nhỏ nếu cần."
    ]
}