import requests
import time
import os
import json
import threading
from collections import deque
from zlapi.models import Message, ThreadType, MultiMsgStyle, MessageStyle
import random
from config import PREFIX, ADMIN

# Danh sách màu
COLORS = [
    "#db342e",  # Đỏ đậm
    "#15a85f",  # Xanh lá đậm
    "#f27806",  # Cam đậm
    "#f7b503"   # Vàng đậm
]

class UndoHandler:
    def __init__(self, file_name='undo.json', config_file='undo_config.json', max_messages=400, save_interval=60):
        self.file_name = file_name
        self.config_file = config_file
        self.max_messages = max_messages
        self.save_interval = save_interval
        self.messages = deque(maxlen=max_messages)
        self.lock = threading.Lock()
        self.undo_enabled_groups = {}  # Lưu trạng thái Undo: { thread_id: { "group_name": str, "enabled": bool } }
        self.init_undo_file()
        self.load_undo_config()
        self.start_auto_save_thread()

    def init_undo_file(self):
        if os.path.exists(self.file_name):
            try:
                # Đọc file với UTF-8 để tránh lỗi 'charmap' trên Windows
                with open(self.file_name, 'r', encoding='utf-8', errors='replace') as f:
                    data = json.load(f)
                    self.messages.extend(data[-self.max_messages:])
            except (json.JSONDecodeError, IOError, UnicodeDecodeError):
                # Nếu file hỏng hoặc mã hóa lỗi → khởi tạo lại file rỗng
                with open(self.file_name, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False)  # Khởi tạo file rỗng

    def load_undo_config(self):
        """Khôi phục trạng thái bật/tắt từ file config."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.undo_enabled_groups = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Lỗi khi tải {self.config_file}: {e}")
                self.undo_enabled_groups = {}
        else:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)  # Khởi tạo file rỗng

    def save_undo_config(self):
        """Lưu trạng thái bật/tắt vào file config."""
        with self.lock:
            try:
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(self.undo_enabled_groups, f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f"Lỗi khi lưu {self.config_file}: {e}")

    def save_message(self, message_object):
        with self.lock:
            self.messages.append(self.format_message_object(message_object))

    def format_message_object(self, message_object):
        content = message_object.content if isinstance(message_object.content, dict) else message_object.content
        return {
            'msgId': message_object.msgId,
            'uidFrom': message_object.uidFrom,
            'cliMsgId': message_object.cliMsgId,
            'msgType': message_object.msgType,
            'content': content,
            'params': message_object.params,
            'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        }

    def get_message(self, cliMsgId):
        with self.lock:
            for message in self.messages:
                if message['cliMsgId'] == cliMsgId:
                    return message
        return None

    def download_file(self, url, file_extension):
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                file_name = f"temp_{int(time.time())}.{file_extension}"  # Định dạng tên file
                with open(file_name, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                return file_name
            else:
                raise Exception(f"Không thể tải file, mã lỗi: {response.status_code}")
        except Exception as e:
            print(f"Lỗi khi tải file: {e}")
            return None

    def download_image(self, url):
        return self.download_file(url, "jpg")

    def download_video(self, url):
        return self.download_file(url, "mp4")

    def download_voice(self, url):
        return self.download_file(url, "mp3")  # Hoặc là .ogg tùy vào định dạng

    def auto_save(self):
        while True:
            time.sleep(self.save_interval)
            with self.lock:
                # Ghi file với UTF-8 để đồng bộ với init_undo_file
                with open(self.file_name, 'w', encoding='utf-8') as f:
                    json.dump(list(self.messages), f, indent=4, ensure_ascii=False)

    def start_auto_save_thread(self):
        save_thread = threading.Thread(target=self.auto_save, daemon=True)
        save_thread.start()

    def toggle_undo(self, thread_id, group_name, enable=True):
        """Bật/Tắt Undo cho nhóm theo thread_id, lưu kèm tên nhóm."""
        self.undo_enabled_groups[thread_id] = {
            "group_name": group_name,
            "enabled": enable
        }
        self.save_undo_config()  # Lưu trạng thái ngay sau khi thay đổi

    def is_undo_enabled(self, thread_id):
        """Kiểm tra xem Undo có được bật cho nhóm không."""
        group_info = self.undo_enabled_groups.get(thread_id, {"enabled": False})
        return group_info.get("enabled", False)

def handle_undo_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh bật/tắt và danh sách Undo."""
    # Gửi phản ứng ngay khi người dùng soạn đúng lệnh
    action = "✅"
    try:
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    except Exception as e:
        print(f"Lỗi khi gửi phản ứng đến nhóm {thread_id}: {e}")

    # Kiểm tra quyền admin
    if author_id not in ADMIN:
        noquyen = "Bạn không có quyền thực hiện hành động này. Vui lòng liên hệ với quản trị viên!"
        style_noquyen = MultiMsgStyle([
            MessageStyle(offset=0, length=len(noquyen), style="color", color=random.choice(COLORS), auto_format=False),
            MessageStyle(offset=0, length=len(noquyen), style="bold", size="16", auto_format=False),
        ])
        try:
            client.replyMessage(Message(text=noquyen, style=style_noquyen),
                                message_object, thread_id, thread_type, ttl=20000)
        except Exception as e:
            print(f"Lỗi khi gửi thông báo không có quyền đến nhóm {thread_id}: {e}")
        return

    # Xử lý lệnh
    msg_lower = message.strip().lower()

    if msg_lower == f"{PREFIX}undo on" or msg_lower == f"{PREFIX}undo off":
        # Lấy tên nhóm từ API Zalo
        try:
            group = client.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
            group_name = group.name
        except Exception as e:
            group_name = f"Nhóm {thread_id}"
            print(f"Lỗi khi lấy thông tin nhóm {thread_id}: {e}")

        # Kiểm tra trạng thái hiện tại
        current_state = client.undo_handler.is_undo_enabled(thread_id)
        if msg_lower == f"{PREFIX}undo on":
            if current_state:
                response = "ℹ️ Tính năng Undo đã được bật trước đó!"
            else:
                client.undo_handler.toggle_undo(thread_id, group_name, enable=True)
                response = "✅ Đã bật tính năng thu hồi tin nhắn cho nhóm này."
        elif msg_lower == f"{PREFIX}undo off":
            if not current_state:
                response = "ℹ️ Tính năng Undo đã được tắt trước đó!"
            else:
                client.undo_handler.toggle_undo(thread_id, group_name, enable=False)
                response = "❌ Đã tắt tính năng thu hồi tin nhắn cho nhóm này."

    elif msg_lower == f"{PREFIX}undo list":
        # Hiển thị danh sách các nhóm có Undo được bật
        enabled_groups = [
            (tid, info) for tid, info in client.undo_handler.undo_enabled_groups.items()
            if info.get("enabled", False)
        ]
        if not enabled_groups:
            response = "📋 Chưa có nhóm nào bật tính năng Undo."
        else:
            response_lines = ["📋 Danh sách nhóm bật Undo:"]
            for index, (tid, info) in enumerate(enabled_groups, start=1):
                group_name = info.get("group_name", "Nhóm không xác định")
                response_lines.append(f"{index}. {group_name} (ID: {tid})")
            response = "\n".join(response_lines)

    else:
        response = f"⚠️ Cú pháp không hợp lệ. Sử dụng: {PREFIX}undo on, {PREFIX}undo off, hoặc {PREFIX}undo list"

    # Gửi phản hồi với định dạng
    style_response = MultiMsgStyle([
        MessageStyle(offset=0, length=len(response), style="color", color=random.choice(COLORS), auto_format=False),
        MessageStyle(offset=0, length=len(response), style="bold", size="16", auto_format=False),
    ])

    # Gửi phản hồi đến nhóm nơi nhận lệnh
    try:
        print(f"Gửi phản hồi đến nhóm {thread_id}: {response}")
        client.replyMessage(Message(text=response, style=style_response),
                            message_object, thread_id, thread_type, ttl=10000)
    except Exception as e:
        print(f"Lỗi khi gửi phản hồi đến nhóm {thread_id}: {e}")
        response = "⚠️ Đã xảy ra lỗi khi xử lý lệnh."
        client.replyMessage(Message(text=response),
                            message_object, thread_id, thread_type, ttl=10000)

def get_mitaizl():
    return {
        'undo': handle_undo_command
    }