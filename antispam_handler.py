# antispam_handler.py
import logging
import time
import json
import os
from zlapi.models import Message, MultiMsgStyle, MessageStyle

logger = logging.getLogger("AntiSpamHandler")

class AntiSpamHandler:
    SETTINGS_FILE = "antispam_settings.json"

    def __init__(self):
        print("[AntiSpamHandler] Khởi tạo AntiSpamHandler ...")
        self.antispam_settings = {}           # thread_id (str) → bool
        self.message_counters = {}            # thread_id → {user_id: count}
        self.last_message_times = {}          # thread_id → {user_id: last_time}
        self.reset_time = 5                   # giây
        self.max_message_limit = 6            # mặc định toàn cục
        self._load_settings()

        # Test nhỏ: in ra trạng thái ngay sau khi load
        print(f"[AntiSpamHandler] Sau khi load: {len(self.antispam_settings)} nhóm đang bật antispam")
        if self.antispam_settings:
            print("[AntiSpamHandler] Trạng thái chi tiết:", self.antispam_settings)

    def _load_settings(self):
        print(f"[AntiSpamHandler] Bắt đầu đọc file: {self.SETTINGS_FILE}")
        full_path = os.path.abspath(self.SETTINGS_FILE)
        print(f"[AntiSpamHandler] Đường dẫn tuyệt đối: {full_path}")

        if not os.path.exists(self.SETTINGS_FILE):
            print("[AntiSpamHandler] File không tồn tại → khởi tạo trạng thái mặc định (tắt hết)")
            logger.info("antispam_settings.json không tồn tại → dùng mặc định tắt")
            return

        try:
            with open(self.SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"[AntiSpamHandler] Đọc thành công, có {len(data)} mục")

            self.antispam_settings.clear()
            for k, v in data.items():
                thread_id = str(k)
                if isinstance(v, dict):
                    enabled = v.get("enabled", False)
                    self.antispam_settings[thread_id] = enabled
                    print(f"  → Nhóm {thread_id}: enabled = {enabled}")
                else:
                    # tương thích format cũ (chỉ bool)
                    enabled = bool(v)
                    self.antispam_settings[thread_id] = enabled
                    print(f"  → Nhóm {thread_id} (format cũ): enabled = {enabled}")

            print("[AntiSpamHandler] Load hoàn tất. Trạng thái hiện tại:", self.antispam_settings)
            logger.info(f"Đã load antispam cho {len(self.antispam_settings)} nhóm")
        except json.JSONDecodeError as e:
            print(f"[AntiSpamHandler] LỖI JSON: file bị hỏng → {e}")
            logger.error(f"JSON decode error: {e}")
        except Exception as e:
            print(f"[AntiSpamHandler] LỖI đọc file: {type(e).__name__} → {e}")
            logger.error(f"Lỗi load antispam_settings.json", exc_info=True)

    def _save_settings(self):
        print(f"[AntiSpamHandler] Bắt đầu lưu file: {self.SETTINGS_FILE}")
        full_path = os.path.abspath(self.SETTINGS_FILE)
        print(f"[AntiSpamHandler] Đường dẫn lưu: {full_path}")

        try:
            data_to_save = {}
            for thread_id, enabled in self.antispam_settings.items():
                data_to_save[thread_id] = {"enabled": enabled}
                print(f"  → Lưu nhóm {thread_id}: enabled = {enabled}")

            with open(self.SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)

            print("[AntiSpamHandler] LƯU FILE THÀNH CÔNG")
            logger.info("Đã lưu antispam_settings.json thành công")
        except PermissionError:
            print("[AntiSpamHandler] LỖI QUYỀN: Không có quyền ghi file!")
            logger.error("Permission denied khi ghi antispam_settings.json")
        except Exception as e:
            print(f"[AntiSpamHandler] LỖI LƯU FILE: {type(e).__name__} → {e}")
            logger.error(f"Lỗi lưu antispam_settings.json", exc_info=True)

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

    def toggle_antispam(self, client, message, message_object, thread_id, thread_type):
        print(f"[AntiSpamHandler] Nhận lệnh toggle: '{message}' | thread={thread_id}")

        content = message.strip().split()
        if len(content) < 2:
            print("[AntiSpamHandler] Thiếu tham số lệnh")
            style = self._apply_style("Vui lòng nhập 'on', 'off' hoặc 'set [số]'.")
            client.replyMessage(
                Message(text="Vui lòng nhập 'on', 'off' hoặc 'set [số giới hạn].", style=style),
                message_object, thread_id, thread_type
            )
            return

        command = content[1].lower()
        thread_id_str = str(thread_id)

        if command == "on":
            print(f"[AntiSpamHandler] Bật antispam cho nhóm {thread_id_str}")
            self.antispam_settings[thread_id_str] = True
            self.message_counters[thread_id_str] = {}
            self.last_message_times[thread_id_str] = {}
            self._save_settings()

            style = self._apply_style("Tính năng chống spam đã được bật!")
            client.replyMessage(
                Message(text="Tính năng chống spam đã được bật!", style=style),
                message_object, thread_id, thread_type
            )

        elif command == "off":
            print(f"[AntiSpamHandler] Tắt antispam cho nhóm {thread_id_str}")
            self.antispam_settings[thread_id_str] = False
            self._save_settings()

            style = self._apply_style("Tính năng chống spam đã được tắt!")
            client.replyMessage(
                Message(text="Tính năng chống spam đã được tắt!", style=style),
                message_object, thread_id, thread_type
            )

        elif command == "set" and len(content) == 3:
            try:
                limit = int(content[2])
                if limit < 3:
                    style = self._apply_style("Giới hạn phải ≥ 3.")
                    client.replyMessage(Message(text="Giới hạn phải ≥ 3.", style=style),
                                        message_object, thread_id, thread_type)
                    return
                self.max_message_limit = limit
                print(f"[AntiSpamHandler] Đổi giới hạn toàn cục → {limit}")
                style = self._apply_style(f"Giới hạn tin nhắn đặt thành {limit}.")
                client.replyMessage(
                    Message(text=f"Giới hạn tin nhắn đặt thành {limit}.", style=style),
                    message_object, thread_id, thread_type
                )
            except ValueError:
                style = self._apply_style("Vui lòng nhập số hợp lệ.")
                client.replyMessage(
                    Message(text="Vui lòng nhập số hợp lệ.", style=style),
                    message_object, thread_id, thread_type
                )
        else:
            style = self._apply_style("Lệnh không hợp lệ. Dùng: on / off / set [số]")
            client.replyMessage(
                Message(text="Lệnh không hợp lệ. Dùng: on / off / set [số]", style=style),
                message_object, thread_id, thread_type
            )

    def is_antispam_enabled(self, thread_id):
        enabled = self.antispam_settings.get(str(thread_id), False)
        # print(f"[AntiSpamHandler] Kiểm tra nhóm {thread_id} → {enabled}")   # comment nếu log nhiều
        return enabled

    def check_and_handle_spam(self, client, author_id, thread_id, message_object, thread_type):
        if not self.is_antispam_enabled(thread_id):
            return False

        current_time = time.time()
        tid = str(thread_id)
        uid = str(author_id)

        self.last_message_times.setdefault(tid, {})
        self.message_counters.setdefault(tid, {})

        last = self.last_message_times[tid].get(uid, 0)
        diff = current_time - last

        if diff > self.reset_time:
            self.message_counters[tid][uid] = 0
            print(f"[AntiSpam] Reset đếm user {uid} trong nhóm {tid}")

        self.last_message_times[tid][uid] = current_time
        count = self.message_counters[tid].get(uid, 0) + 1
        self.message_counters[tid][uid] = count

        print(f"[AntiSpam] {uid} → tin {count}/{self.max_message_limit} (nhóm {tid})")

        if count >= self.max_message_limit - 2:
            style = self._apply_style("⚠️ Bạn đang spam! Tiếp tục sẽ bị sút.")
            client.replyMessage(
                Message(text="⚠️ Bạn đang spam! Tiếp tục sẽ bị sút.", style=style),
                message_object, thread_id, thread_type, ttl=15000
            )

        if count > self.max_message_limit:
            print(f"[AntiSpam] KICK {uid} vì vượt {self.max_message_limit} tin")
            try:
                client.kick_member_from_group(author_id, thread_id)
            except Exception as e:
                print(f"[AntiSpam] Lỗi kick: {e}")
            self.message_counters[tid][uid] = 0
            return True

        return False

    @staticmethod
    def get_mitaizl():
        return {
            'antispam_handler': 'handle_antispam_handler_command'  # nếu bạn dùng dict handler
        }