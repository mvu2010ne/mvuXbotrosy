import os
import logging
from zlapi.models import Message, MultiMsgStyle, MessageStyle
from config import ADMIN

logger = logging.getLogger("LocalCodeReplaceHandler")

class LocalCodeReplaceHandler:
    def __init__(self):
        self.max_message_length = 2000
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

    def is_admin(self, author_id):
        logger.info(f"Kiểm tra admin - author_id: {author_id}, ADMIN_ID: {ADMIN}")
        return str(author_id) in ADMIN

    def replace_in_files(self, search_string, replace_string):
        logger.info(f"Thay thế chuỗi: '{search_string}' thành '{replace_string}'")
        results = []
        search_dir = os.path.dirname(os.path.abspath(__file__))

        try:
            for root, dirs, files in os.walk(search_dir):
                if '__pycache__' in dirs:
                    dirs.remove('__pycache__')

                for file_name in files:
                    file_ext = os.path.splitext(file_name)[1].lower()
                    if file_ext not in self.text_extensions:
                        logger.debug(f"Bỏ qua file không phải text: {file_name}")
                        continue

                    file_path = os.path.join(root, file_name)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                            lines = file.readlines()

                        modified = False
                        replaced_lines = []
                        for line_num, line in enumerate(lines, 1):
                            if search_string in line:
                                modified = True
                                new_line = line.replace(search_string, replace_string)
                                replaced_lines.append({
                                    'file': os.path.relpath(file_path, search_dir),
                                    'line': line_num,
                                    'original': line.strip(),
                                    'new': new_line.strip()
                                })
                                lines[line_num - 1] = new_line

                        if modified:
                            with open(file_path, 'w', encoding='utf-8') as file:
                                file.writelines(lines)
                            results.extend(replaced_lines)

                    except Exception as e:
                        rel_path = os.path.relpath(file_path, search_dir)
                        results.append({
                            'file': rel_path,
                            'line': -1,
                            'original': f"Lỗi khi xử lý file: {str(e)}",
                            'new': ""
                        })

            if not results:
                return [{'file': None, 'line': -1, 'original': "Không tìm thấy chuỗi cần thay thế trong bất kỳ file nào.", 'new': ""}]
            return results
        except Exception as e:
            return [{'file': None, 'line': -1, 'original': f"Lỗi khi quét thư mục: {str(e)}", 'new': ""}]

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

    def handle_localreplace(self, client, message, message_object, thread_id, thread_type, author_id):
        logger.info(f"Nhận lệnh: {message}")
        parts = message.strip().split(" ", 2)

        if len(parts) < 3:
            style = self._apply_style("Vui lòng nhập: code.replace <chuỗi cần tìm> <chuỗi thay thế>")
            client.replyMessage(
                Message(text="Vui lòng nhập: code.replace <chuỗi cần tìm> <chuỗi thay thế>", style=style),
                message_object, thread_id, thread_type
            )
            return

        search_string = parts[1].strip()
        replace_string = parts[2].strip()

        if not search_string or not replace_string:
            style = self._apply_style("❌ Vui lòng cung cấp cả chuỗi cần tìm và chuỗi thay thế!")
            client.replyMessage(
                Message(text="❌ Vui lòng cung cấp cả chuỗi cần tìm và chuỗi thay thế!", style=style),
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

        style = self._apply_style(f"⏳ Đang thay thế '{search_string}' bằng '{replace_string}' trong thư mục '{search_dir}' và các thư mục con...")
        client.sendMessage(
            Message(text=f"⏳ Đang thay thế '{search_string}' bằng '{replace_string}' trong thư mục '{search_dir}' và các thư mục con...", style=style),
            thread_id, thread_type
        )

        results = self.replace_in_files(search_string, replace_string)

        if not results or (results and results[0]['file'] is None):
            style = self._apply_style(f"❌ Không tìm thấy '{search_string}' trong bất kỳ file nào trong '{search_dir}'.")
            client.replyMessage(
                Message(text=f"❌ Không tìm thấy '{search_string}' trong bất kỳ file nào trong '{search_dir}'.", style=style),
                message_object, thread_id, thread_type
            )
            return

        result_text = f"🔍 Kết quả thay thế '{search_string}' bằng '{replace_string}' trong '{search_dir}':\n"
        for res in results:
            if res['line'] == -1:
                result_text += f"📄 File: {res['file']}\n⚠ Lỗi: {res['original']}\n\n"
            else:
                result_text += f"📄 File: {res['file']}\n📍 Dòng {res['line']}:\n  Cũ: {res['original']}\n  Mới: {res['new']}\n\n"

        chunks = self.split_content(result_text)
        total_parts = len(chunks)

        for part, chunk in enumerate(chunks, 1):
            msg = f"🔍 Kết quả thay thế (Phần {part}/{total_parts}):\n{chunk}"
            style = self._apply_style(msg)
            client.sendMessage(
                Message(text=msg, style=style),
                thread_id, thread_type,
                ttl=60000
            )
        logger.info(f"Đã gửi {total_parts} phần kết quả")

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🔍 Thay thế một chuỗi nội dung trong các file text trong dự án (thư mục gốc và thư mục con).",
    'tính năng': [
        "📜 Thay thế chuỗi trong các file text (.py, .json, .txt, v.v.) trong thư mục dự án và các thư mục con.",
        "📍 Trả về tên file, số dòng, nội dung cũ và mới sau khi thay thế.",
        "✂️ Chia nhỏ kết quả nếu quá dài để gửi thành nhiều tin nhắn.",
        "🔐 Yêu cầu quyền admin để sử dụng.",
        "⚠️ Thông báo lỗi nếu không tìm thấy chuỗi hoặc có vấn đề khi đọc/ghi file."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh code.replace <chuỗi cần tìm> <chuỗi thay thế> để thay thế chuỗi trong các file text.",
        "📌 Ví dụ: code.replace 3299675674241805615 3299675674241805615",
        "✅ Nhận danh sách file và vị trí đã thay thế, chia nhỏ nếu cần."
    ]
}