import time
import json
import logging
from collections import defaultdict
from zlapi.models import Message, ThreadType
from modules.bot_info import apply_default_style

logger = logging.getLogger("Bot")

# Biến toàn cục
message_counts = defaultdict(lambda: defaultdict(int))

def load_message_counts():
    """Tải dữ liệu thống kê tin nhắn từ file."""
    global message_counts
    try:
        with open("message_counts.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            for thread_id, counts in data.items():
                message_counts[thread_id].update(counts)
    except FileNotFoundError:
        save_message_counts()
    except Exception as e:
        logger.error(f"Lỗi tải message_counts.json: {e}")

def save_message_counts():
    """Lưu dữ liệu thống kê tin nhắn vào file."""
    try:
        with open("message_counts.json", "w", encoding="utf-8") as f:
            # Convert defaultdict to regular dict for JSON serialization
            serializable_data = {}
            for thread_id, counts in message_counts.items():
                serializable_data[thread_id] = dict(counts)
            json.dump(serializable_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Lỗi lưu message_counts.json: {e}")

def handle_topchat(client, thread_id, thread_type, author_id, admin_ids, prefix):
    """
    Xử lý lệnh topchat, chỉ ADMIN mới được sử dụng.
    
    Args:
        client: Instance của Client
        thread_id: ID của thread (nhóm hoặc user)
        thread_type: Loại thread (GROUP hoặc USER)
        author_id: ID của người gửi lệnh
        admin_ids: Danh sách ID admin
        prefix: Prefix của bot
    """
    # Kiểm tra quyền admin
    if author_id not in admin_ids:
        client.sendMessage(
            Message(
                text="🚫 Bạn không có quyền sử dụng lệnh này. Chỉ admin mới có thể sử dụng!",
                style=apply_default_style("🚫 Bạn không có quyền sử dụng lệnh này. Chỉ admin mới có thể sử dụng!")
            ),
            thread_id,
            thread_type,
            ttl=10000
        )
        logger.info(f"User {author_id} không có quyền sử dụng lệnh {prefix}topchat")
        return

    if thread_type != ThreadType.GROUP:
        client.sendMessage(
            Message(text="Lệnh topchat chỉ dùng trong nhóm!", style=apply_default_style("Lệnh topchat chỉ dùng trong nhóm!")),
            thread_id,
            thread_type,
            ttl=60000
        )
        return

    counts = message_counts.get(thread_id, {})
    if not counts:
        client.sendMessage(
            Message(text="Chưa có dữ liệu tin nhắn trong nhóm này!", style=apply_default_style("Chưa có dữ liệu tin nhắn trong nhóm này!")),
            thread_id,
            thread_type,
            ttl=60000
        )
        return

    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:200]
    max_message_length = 2000  # Giới hạn độ dài mỗi tin nhắn
    message_lines = [f"🏆 Top 200 người lắm mồm nhất nhóm:"]
    current_length = len(message_lines[0])

    for i, (user_id, count) in enumerate(sorted_counts, 1):
        try:
            user_info = client.fetchUserInfo(user_id).changed_profiles.get(str(user_id), {})
            user_name = user_info.get("displayName", f"User {user_id}")
        except Exception:
            user_name = f"User {user_id}"
        line = f"{i}. {user_name} - {count} tin nhắn"
        line_length = len(line)

        if current_length + line_length + 1 > max_message_length:
            message_text = "\n".join(message_lines)
            client.sendMessage(
                Message(text=message_text, style=apply_default_style(message_text)),
                thread_id,
                thread_type
            )
            logger.info(f"Đã gửi một phần danh sách topchat cho nhóm {thread_id}")
            message_lines = [f"Phần tiếp theo:"]
            current_length = len(message_lines[0])
            time.sleep(1)  # Chờ 1 giây trước khi gửi tin nhắn tiếp theo

        message_lines.append(line)
        current_length += line_length + 1

    if message_lines:
        message_text = "\n".join(message_lines)
        client.sendMessage(
            Message(text=message_text, style=apply_default_style(message_text)),
            thread_id,
            thread_type
        )
        logger.info(f"Đã gửi phần cuối danh sách topchat cho nhóm {thread_id}")

def increment_message_count(thread_id, author_id):
    """Tăng bộ đếm tin nhắn cho user trong thread."""
    if thread_id and author_id:
        message_counts[thread_id][author_id] += 1
        save_message_counts()

def handle_topchat_command(message, message_object, thread_id, thread_type, author_id, client):
    """Handler cho lệnh topchat được gọi từ command system."""
    from config import ADMIN, PREFIX  # Import tại đây để tránh circular import
    handle_topchat(client, thread_id, thread_type, author_id, ADMIN, PREFIX)

def get_mitaizl():
    """Function trả về các handler lệnh cho topchat."""
    return {
        'topchat': handle_topchat_command
    }

# Tải dữ liệu khi module được import
load_message_counts()