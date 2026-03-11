import requests
import time
import os
import json
import threading
from collections import deque

class UndoHandler:
    def __init__(self, file_name='undo.json', max_messages=400, save_interval=60):
        self.file_name = file_name
        self.max_messages = max_messages
        self.save_interval = save_interval
        self.messages = deque(maxlen=max_messages)
        self.lock = threading.Lock()
        self.undo_enabled_groups = {}  # Lưu trạng thái Undo cho từng nhóm
        self.init_undo_file()
        self.start_auto_save_thread()

    def init_undo_file(self):
        if os.path.exists(self.file_name):
            try:
                with open(self.file_name, 'r') as f:
                    data = json.load(f)
                    self.messages.extend(data[-self.max_messages:])
            except (json.JSONDecodeError, IOError):
                with open(self.file_name, 'w') as f:
                    json.dump([], f)  # Khởi tạo file rỗng

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
                with open(self.file_name, 'w') as f:
                    json.dump(list(self.messages), f, indent=4, ensure_ascii=False)

    def start_auto_save_thread(self):
        save_thread = threading.Thread(target=self.auto_save, daemon=True)
        save_thread.start()

    def toggle_undo(self, thread_id, enable=True):
        """Bật/Tắt Undo cho nhóm theo thread_id."""
        self.undo_enabled_groups[thread_id] = enable

    def is_undo_enabled(self, thread_id):
        """Kiểm tra xem Undo có được bật cho nhóm không."""
        return self.undo_enabled_groups.get(thread_id, False)