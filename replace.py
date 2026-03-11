import os
import logging
from zlapi.models import Message, MultiMsgStyle, MessageStyle
from config import ADMIN

logger = logging.getLogger("GeminiKeyReplaceHandler")

class GeminiKeyReplaceHandler:
    def __init__(self):
        self.max_message_length = 2000
        self.target_file = "modules/gemini1.py"
        self.target_line_prefix = "GEMINI_API_KEY = os.getenv"

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
        return author_id in ADMIN

    def replace_gemini_key(self, new_api_key):
        logger.info(f"Thay thế GEMINI_API_KEY")
        results = []
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.target_file)

        try:
            if not os.path.exists(file_path):
                logger.error(f"File {self.target_file} không tồn tại")
                return [{'file': self.target_file, 'line': -1, 'original': f"File {self.target_file} không tồn tại", 'new': ""}]

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                lines = file.readlines()

            modified = False
            replaced_lines = []
            for line_num, line in enumerate(lines, 1):
                if self.target_line_prefix in line:
                    modified = True
                    original_line = line.strip()
                    new_line = f"GEMINI_API_KEY = os.getenv(\"GEMINI_API_KEY\", \"{new_api_key}\")\n"
                    replaced_lines.append({
                        'file': self.target_file,
                        'line': line_num,
                        'original': original_line,
                        'new': new_line.strip()
                    })
                    lines[line_num - 1] = new_line
                    break

            if modified:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.writelines(lines)
                results.extend(replaced_lines)
            else:
                results.append({
                    'file': self.target_file,
                    'line': -1,
                    'original': "Không tìm thấy dòng GEMINI_API_KEY trong file.",
                    'new': ""
                })

            return results
        except Exception as e:
            return [{'file': self.target_file, 'line': -1, 'original': f"Lỗi khi xử lý file: {str(e)}", 'new': ""}]

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

    def handle_keyreplace(self, client, message, message_object, thread_id, thread_type, author_id):
        logger.info(f"Nhận lệnh: {message}")
        parts = message.strip().split(" ", 1)

        if len(parts) < 2:
            style = self._apply_style("Vui lòng nhập: replace <giá_trị_mới>")
            client.replyMessage(
                Message(text="Vui lòng nhập: replace <giá_trị_mới>", style=style),
                message_object, thread_id, thread_type, ttl=10000
            )
            return

        new_api_key = parts[1].strip()

        if not new_api_key:
            style = self._apply_style("❌ Vui lòng cung cấp giá trị mới!")
            client.replyMessage(
                Message(text="❌ Vui lòng cung cấp giá trị mới!", style=style),
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

        style = self._apply_style(f"⏳ Đang cập nhật cấu hình trong '{self.target_file}'...")
        client.sendMessage(
            Message(text=f"⏳ Đang cập nhật cấu hình trong '{self.target_file}'...", style=style),
            thread_id, thread_type
        )

        results = self.replace_gemini_key(new_api_key)

        if not results or (results and results[0]['line'] == -1):
            style = self._apply_style(f"❌ Không cập nhật được cấu hình trong '{self.target_file}'.")
            client.replyMessage(
                Message(text=f"❌ Không cập nhật được cấu hình trong '{self.target_file}'.", style=style),
                message_object, thread_id, thread_type
            )
            return

        result_text = f"🔍 Kết quả cập nhật cấu hình trong '{self.target_file}':\n"
        for res in results:
            if res['line'] == -1:
                result_text += f"📄 File: {res['file']}\n⚠ Lỗi: {res['original']}\n\n"
            else:
                result_text += f"📄 File: {res['file']}\n📍 Dòng {res['line']}:\n  Cũ: {res['original']}\n  Mới: Cấu hình đã được cập nhật\n\n"

        chunks = self.split_content(result_text)
        total_parts = len(chunks)

        for part, chunk in enumerate(chunks, 1):
            msg = f"🔍 Kết quả cập nhật (Phần {part}/{total_parts}):\n{chunk}"
            style = self._apply_style(msg)
            client.sendMessage(
                Message(text=msg, style=style),
                thread_id, thread_type,
                ttl=60000
            )
        logger.info(f"Đã gửi {total_parts} phần kết quả")

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🔍 Cập nhật cấu hình trong file gemini1.py.",
    'tính năng': [
        "📜 Cập nhật dòng cấu hình trong file gemini1.py.",
        "📍 Trả về tên file, số dòng, nội dung cũ và thông báo cập nhật sau khi thay thế.",
        "✂️ Chia nhỏ kết quả nếu quá dài để gửi thành nhiều tin nhắn.",
        "🔐 Yêu cầu quyền admin để sử dụng.",
        "⚠️ Thông báo lỗi nếu không tìm thấy dòng hoặc có vấn đề khi đọc/ghi file."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh key.replace <giá_trị_mới> để cập nhật cấu hình.",
        "📌 Ví dụ: key.replace AIzaSyDmdkInK68Omad89LzSpZdsl7nWdoqq4ag",
        "✅ Nhận kết quả cập nhật, chia nhỏ nếu cần."
    ]
}