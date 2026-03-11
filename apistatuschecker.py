import os
import re
import requests
import time
from zlapi.models import Message, MultiMsgStyle, MessageStyle
from config import ADMIN

class ApiStatusChecker:
    def __init__(self):
        self.max_message_length = 2000
        self.text_extensions = {'.py'}  # Chỉ xử lý file .py
        self.api_patterns = [
            r'requests\.(get|post|put|delete)\(\s*[\'"](https?://[^\s\'"]+)[\'"][^\)]*\)',  # requests library
            r'http\.client\.HTTPS?Connection\(\s*[\'"]([^\'"]+)[\'"][^\)]*\)',  # http.client
            r'urllib\.request\.urlopen\(\s*[\'"](https?://[^\s\'"]+)[\'"][^\)]*\)'  # urllib
        ]
        self.message_delay = 1.0  # Thời gian trễ 1 giây giữa các tin nhắn

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
        print(f"[CHECK] Kiểm tra quyền admin - author_id: {author_id}, ADMIN_ID: {ADMIN}")
        return author_id == ADMIN

    def check_api_status(self, url):
        print(f"[CHECK] Đang kiểm tra trạng thái API: {url}")
        try:
            response = requests.head(url, timeout=5, allow_redirects=True)
            status = response.status_code
            status_text = "Hoạt động" if 200 <= status < 400 else f"Lỗi: {status}"
            print(f"[RESULT] Trạng thái API {url}: {status_text} (Mã trạng thái: {status})")
            return status, status_text
        except requests.RequestException as e:
            print(f"[ERROR] Lỗi khi kiểm tra API {url}: {str(e)}")
            return None, f"Lỗi: Không thể kết nối ({str(e)})"

    def search_apis_in_files(self):
        print("[START] Bắt đầu quét API trong các file .py")
        results = []
        search_dir = os.path.dirname(os.path.abspath(__file__))
        print(f"[INFO] Thư mục quét: {search_dir}")
        
        try:
            for root, dirs, files in os.walk(search_dir):
                if '__pycache__' in dirs:
                    dirs.remove('__pycache__')
                    print("[DEBUG] Bỏ qua thư mục __pycache__")
                
                for file_name in files:
                    file_ext = os.path.splitext(file_name)[1].lower()
                    if file_ext not in self.text_extensions:
                        print(f"[DEBUG] Bỏ qua file không phải .py: {file_name}")
                        continue

                    file_path = os.path.join(root, file_name)
                    print(f"[CHECK] Đang quét file: {file_path}")
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                            lines = file.readlines()
                            for line_num, line in enumerate(lines, 1):
                                for pattern in self.api_patterns:
                                    matches = re.finditer(pattern, line)
                                    for match in matches:
                                        url = match.group(2) if 'http' in match.group(0) else f"https://{match.group(1)}"
                                        print(f"[FOUND] Tìm thấy API tại file {file_path}, dòng {line_num}: {url}")
                                        print(f"[DEBUG] Nội dung dòng: {line.strip()}")
                                        status_code, status_text = self.check_api_status(url)
                                        rel_path = os.path.relpath(file_path, search_dir)
                                        results.append({
                                            'file': rel_path,
                                            'line': line_num,
                                            'url': url,
                                            'status': status_text,
                                            'content': line.strip()
                                        })
                    except Exception as e:
                        rel_path = os.path.relpath(file_path, search_dir)
                        print(f"[ERROR] Lỗi khi đọc file {file_path}: {str(e)}")
                        results.append({
                            'file': rel_path,
                            'line': -1,
                            'url': None,
                            'status': f"Lỗi khi đọc file: {str(e)}",
                            'content': None
                        })
            if not results:
                print("[INFO] Không tìm thấy API nào trong các file .py")
                return [{'file': None, 'line': -1, 'url': None, 'status': "Không tìm thấy API nào trong các file .py.", 'content': None}]
            print(f"[DONE] Hoàn tất quét: Tìm thấy {len(results)} API")
            return results
        except Exception as e:
            print(f"[ERROR] Lỗi khi quét thư mục {search_dir}: {str(e)}")
            return [{'file': None, 'line': -1, 'url': None, 'status': f"Lỗi khi quét thư mục: {str(e)}", 'content': None}]

    def split_content(self, content):
        print("[DEBUG] Bắt đầu chia nhỏ nội dung kết quả")
        lines = content.splitlines()
        chunks = []
        current_chunk = ""
        current_length = 0

        for line in lines:
            line_length = len(line) + 1
            if current_length + line_length > self.max_message_length:
                if current_chunk:
                    chunks.append(current_chunk)
                    print(f"[DEBUG] Tạo chunk mới, kích thước: {len(current_chunk)} ký tự")
                    current_chunk = ""
                    current_length = 0
            current_chunk += line + "\n"
            current_length += line_length

        if current_chunk:
            chunks.append(current_chunk)
            print(f"[DEBUG] Tạo chunk cuối, kích thước: {len(current_chunk)} ký tự")

        print(f"[INFO] Hoàn tất chia nội dung: {len(chunks)} phần")
        return chunks

    def handle_apicheck(self, client, message, message_object, thread_id, thread_type, author_id):
        print(f"[START] Nhận lệnh: {message} từ user {author_id} trong thread {thread_id} ({thread_type})")
        
        if not self.is_admin(author_id):
            style = self._apply_style("• Bạn không có quyền sử dụng lệnh này.")
            client.replyMessage(
                Message(text="• Bạn không có quyền sử dụng lệnh này.", style=style),
                message_object, thread_id, thread_type
            )
            print(f"[INFO] User {author_id} không có quyền sử dụng lệnh apicheck")
            return

        search_dir = os.path.dirname(os.path.abspath(__file__))
        style = self._apply_style(f"⏳ Đang kiểm tra trạng thái API trong thư mục '{search_dir}' và các thư mục con...")
        client.sendMessage(
            Message(text=f"⏳ Đang kiểm tra trạng thái API trong thư mục '{search_dir}' và các thư mục con...", style=style),
            thread_id, thread_type
        )
        print(f"[INFO] Đã gửi thông báo bắt đầu quét tới thread {thread_id}")

        results = self.search_apis_in_files()
        
        if not results or (results and results[0]['file'] is None):
            style = self._apply_style(f"❌ Không tìm thấy API nào trong các file .py trong '{search_dir}'.")
            client.replyMessage(
                Message(text=f"❌ Không tìm thấy API nào trong các file .py trong '{search_dir}'.", style=style),
                message_object, thread_id, thread_type
            )
            print(f"[INFO] Không tìm thấy API, đã gửi thông báo tới thread {thread_id}")
            return

        result_text = f"🔍 Kết quả kiểm tra API trong '{search_dir}':\n"
        for res in results:
            if res['line'] == -1:
                result_text += f"📄 File: {res['file']}\n⚠ Lỗi: {res['status']}\n\n"
            else:
                result_text += f"📄 File: {res['file']}\n📍 Dòng {res['line']}\n🔗 URL: {res['url']}\n📊 Trạng thái: {res['status']}\n💻 Code: {res['content']}\n\n"
        print(f"[DEBUG] Nội dung kết quả đầy đủ:\n{result_text}")

        chunks = self.split_content(result_text)
        total_parts = len(chunks)

        for part, chunk in enumerate(chunks, 1):
            msg = f"🔍 Kết quả kiểm tra API (Phần {part}/{total_parts}):\n{chunk}"
            style = self._apply_style(msg)
            client.sendMessage(
                Message(text=msg, style=style),
                thread_id, thread_type,
                ttl=600000
            )
            print(f"[INFO] Đã gửi phần {part}/{total_parts} tới thread {thread_id}, kích thước: {len(msg)} ký tự")
            time.sleep(self.message_delay)  # Thêm thời gian trễ 1 giây
        print(f"[DONE] Hoàn tất gửi {total_parts} phần kết quả tới thread {thread_id}")