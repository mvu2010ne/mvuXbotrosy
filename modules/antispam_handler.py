import logging
import time
from zlapi.models import Message, MultiMsgStyle, MessageStyle

logger = logging.getLogger("AntiSpamHandler")

class AntiSpamHandler:
    def __init__(self):
        self.antispam_settings = {}  # Trạng thái bật/tắt theo nhóm
        self.message_counters = {}  # Đếm tin nhắn theo nhóm/người dùng
        self.last_message_times = {}  # Thời gian gửi tin cuối cùng
        self.reset_time = 5  # Thời gian reset (giây)
        self.max_message_limit = 6  # Số tin nhắn tối đa

    def _apply_style(self, message):
        # Create MultiMsgStyle with color red and font size 16
        return MultiMsgStyle(
            [
                MessageStyle(
                    offset=0,
                    length=len(message),
                    style="color",
                    color="#db342e",  # Red color
                    auto_format=False,
                ),
                MessageStyle(
                    offset=0,
                    length=len(message),
                    style="font",
                    size="16",  # Font size 16
                    auto_format=False,
                ),
            ]
        )

    def toggle_antispam(self, client, message, message_object, thread_id, thread_type):
        ADMIN_ID = "3299675674241805615"  # Admin duy nhất

        # Kiểm tra quyền admin
        if str(message_object.uidFrom) != ADMIN_ID:
            style = self._apply_style("❌ Bạn không có quyền sử dụng lệnh này.")
            client.replyMessage(
                Message(text="❌ Bạn không có quyền sử dụng lệnh này.", style=style),
                message_object, thread_id, thread_type
            )
            return

        # Tách và chuẩn hóa lệnh
        content = message.strip().split()
        if len(content) < 2 or content[0].lower() != "antispam":
            style = self._apply_style("❌ Lệnh không hợp lệ. Sử dụng 'antispam on', 'off' hoặc 'set [số]'.")
            client.replyMessage(
                Message(text="❌ Lệnh không hợp lệ. Sử dụng 'antispam on', 'off' hoặc 'set [số]'.", style=style),
                message_object, thread_id, thread_type
            )
            return

        command = content[1].lower()

        if command == "on":
            self.antispam_settings[thread_id] = True
            self.message_counters[thread_id] = {}
            self.last_message_times[thread_id] = {}
            style = self._apply_style("✅ Tính năng chống spam đã được bật!")
            client.replyMessage(
                Message(text="✅ Tính năng chống spam đã được bật!", style=style),
                message_object, thread_id, thread_type
            )
        elif command == "off":
            self.antispam_settings[thread_id] = False
            style = self._apply_style("🚫 Tính năng chống spam đã được tắt!")
            client.replyMessage(
                Message(text="🚫 Tính năng chống spam đã được tắt!", style=style),
                message_object, thread_id, thread_type
            )
        elif command == "set" and len(content) == 3:
            try:
                limit = int(content[2])
                self.max_message_limit = limit
                style = self._apply_style(f"📊 Giới hạn tin nhắn đặt thành {limit}.")
                client.replyMessage(
                    Message(text=f"📊 Giới hạn tin nhắn đặt thành {limit}.", style=style),
                    message_object, thread_id, thread_type
                )
            except ValueError:
                style = self._apply_style("❌ Vui lòng nhập số hợp lệ.")
                client.replyMessage(
                    Message(text="❌ Vui lòng nhập số hợp lệ.", style=style),
                    message_object, thread_id, thread_type
                )
        else:
            style = self._apply_style("❌ Lệnh không hợp lệ. Dùng 'antispam on', 'off' hoặc 'set [số]'.")
            client.replyMessage(
                Message(text="❌ Lệnh không hợp lệ. Dùng 'antispam on', 'off' hoặc 'set [số]'.", style=style),
                message_object, thread_id, thread_type
            )


    def is_antispam_enabled(self, thread_id):
        return self.antispam_settings.get(thread_id, False)

    def check_and_handle_spam(self, client, author_id, thread_id, message_object, thread_type):
        current_time = time.time()
        last_time = self.last_message_times.get(thread_id, {}).get(author_id, 0)
        time_diff = current_time - last_time

        if time_diff > self.reset_time:
            self.message_counters[thread_id][author_id] = 0

        self.last_message_times.setdefault(thread_id, {})[author_id] = current_time
        self.message_counters.setdefault(thread_id, {})[author_id] = self.message_counters[thread_id].get(author_id, 0) + 1

        if self.message_counters[thread_id][author_id] >= self.max_message_limit - 2:
            style = self._apply_style("⚠️ Bạn đang spam! Nếu tiếp tục, bạn sẽ bị sút.")
            client.replyMessage(
                Message(text="⚠️ Bạn đang spam! Nếu tiếp tục, bạn sẽ bị sút.", style=style),
                message_object, thread_id, thread_type, ttl= 15000
            )

        if self.message_counters[thread_id][author_id] > self.max_message_limit:
            logger.info(f"Kick {author_id} do spam.")
            client.kick_member_from_group(author_id, thread_id)
            self.message_counters[thread_id][author_id] = 0
            return True

        return False

def get_mitaizl():
        return {
            'antispam': None
        }    
