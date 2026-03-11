import json
import os
import urllib.parse
import random
import difflib

from zlapi.models import Message, MessageStyle, MultiMsgStyle
from config import ADMIN, PREFIX

# Đường dẫn file lưu trữ dữ liệu
DATA_FILE = "chat_data.json"

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Dạy và trả lời tin nhắn thông qua học máy",
    'tính năng': [
        "📨 Dạy bot với câu hỏi và câu trả lời mới.",
        "🔍 Tìm kiếm câu trả lời dựa trên chuỗi con, tập từ và so sánh mờ.",
        "📝 Lưu dữ liệu vào file JSON để bot có thể học và nhớ.",
        "🎲 Chọn câu trả lời ngẫu nhiên nếu có nhiều câu trả lời cho cùng một câu hỏi.",
        "🔔 Thông báo lỗi cụ thể nếu cú pháp lệnh không chính xác hoặc giá trị không hợp lệ."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh day <câu hỏi> | <câu trả lời> để dạy bot.",
        "📩 Gửi lệnh mya <tin nhắn> để bot trả lời tin nhắn của bạn.",
        "📌 Ví dụ: day mya | dạ Mya nghe để dạy bot trả lời câu hỏi 'mya' với câu trả lời 'dạ Mya nghe'.",
        "✅ Nhận thông báo trạng thái và kết quả ngay lập tức."
    ]
}

def load_data():
    """
    Tải dữ liệu từ file JSON.
    Nếu file không tồn tại hoặc lỗi định dạng, trả về dictionary rỗng.
    """
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Lỗi tải dữ liệu JSON: {str(e)}")
        return {}

def save_data(data):
    """Lưu dữ liệu vào file JSON với định dạng UTF-8."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Tải dữ liệu ban đầu từ file JSON
chat_data = load_data()

def send_reply_with_style(client, text, message_object, thread_id, thread_type, ttl=None, color="#db342e"):
    """
    Gửi tin nhắn phản hồi với định dạng màu sắc và in đậm.
    """
    base_length = len(text)
    adjusted_length = base_length + 355
    style = MultiMsgStyle([
        MessageStyle(
            offset=0,
            length=adjusted_length,
            style="color",
            color=color,
            auto_format=False,
        ),
        MessageStyle(
            offset=0,
            length=adjusted_length,
            style="bold",
            size="8",
            auto_format=False
        )
    ])
    msg = Message(text=text, style=style)
    if ttl is not None:
        client.replyMessage(msg, message_object, thread_id, thread_type, ttl=ttl)
    else:
        client.replyMessage(msg, message_object, thread_id, thread_type)

def handle_teach_command(message, message_object, thread_id, thread_type, author_id, client):
    """
    Xử lý lệnh dạy bot với định dạng:
    day: câu hỏi | câu trả lời hoặc day câu hỏi | câu trả lời
    Ví dụ: day mya | dạ Mya nghe
    """
    print("DEBUG - Đã vào hàm handle_teach_command")
    # Gửi phản ứng ngay khi nhận lệnh
    action = "OK"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    command_prefix = "day"
    if not message.lower().startswith(command_prefix):
        error_msg = Message(
            text="Lệnh không hợp lệ. Vui lòng sử dụng định dạng: day: câu hỏi | câu trả lời hoặc day câu hỏi | câu trả lời"
        )
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    # Loại bỏ tiền tố "day" và dấu ':' nếu có
    content = message[len(command_prefix):].strip()
    if content.startswith(":"):
        content = content[1:].strip()
    if not content:
        error_msg = Message(text="Không tìm thấy nội dung. Vui lòng sử dụng định dạng: day câu hỏi | câu trả lời")
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    # Tách câu hỏi và câu trả lời bằng dấu '|'
    if "|" not in content:
        error_msg = Message(text="Vui lòng tách câu hỏi và câu trả lời bằng dấu |")
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    ask, ans = content.split("|", 1)
    ask = ask.strip()
    ans = ans.strip()
    if not ask or not ans:
        error_msg = Message(text="Câu hỏi và câu trả lời không được để trống.")
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    # Cập nhật dữ liệu vào chat_data và lưu file JSON
    global chat_data
    # Nếu câu hỏi đã tồn tại, thêm câu trả lời vào danh sách thay vì thay thế
    if ask in chat_data:
        # Nếu dữ liệu hiện tại không phải là danh sách thì chuyển đổi
        if not isinstance(chat_data[ask], list):
            chat_data[ask] = [chat_data[ask]]
        # Thêm câu trả lời mới (có thể kiểm tra trùng lặp nếu cần)
        if ans not in chat_data[ask]:
            chat_data[ask].append(ans)
    else:
        # Lưu dưới dạng danh sách với một phần tử
        chat_data[ask] = [ans]
    save_data(chat_data)

    reply_text = (
        f"✅ Đã dạy Mya với:\n"
        f"- Câu hỏi: {ask}\n"
        f"- Câu trả lời: {ans}"
    )
    send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=120000)

def handle_sim_command(message, message_object, thread_id, thread_type, author_id, client):
    """
    Xử lý lệnh chat với bot.
    Tin nhắn cần bắt đầu bằng từ 'mya' và sau đó là nội dung cần hỏi.
    Nếu bot không hiểu câu hỏi, sẽ yêu cầu người dùng dạy bot.
    """
    print("DEBUG - Đã vào hàm handle_sim_command")
    # Gửi phản ứng ngay khi nhận lệnh
    action = "OK"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    # Kiểm tra xem tin nhắn có bắt đầu bằng "mya" không
    if not message.lower().startswith("mya"):
        print("DEBUG - Tin nhắn không bắt đầu bằng từ 'mya'")
        return

    # Tách các từ trong tin nhắn
    words = message.split()
    # Nếu tin nhắn chỉ có từ "mya"
    if len(words) == 1:
        reply_text = random.choice(["Sủa đi", "Nói", "Kêu cc"])
    else:
        # Loại bỏ từ "mya" đầu tiên và lấy phần còn lại của tin nhắn
        content = " ".join(words[1:]).strip().lower()
        print(f"DEBUG - Nội dung tin nhắn sau khi loại bỏ 'mya': '{content}'")
        print(f"DEBUG - Dữ liệu Mya: {chat_data}")

        # Bước 1: Tìm kiếm trực tiếp theo chuỗi con
        matched_keys = []
        for key in chat_data.keys():
            if key.lower() in content:
                matched_keys.append(key)

        # Bước 2: Nếu không tìm được kết quả, thử tách tin nhắn thành từng từ và so sánh theo tập từ
        if not matched_keys:
            content_words = set(content.split())
            for key in chat_data.keys():
                key_words = set(key.lower().split())
                if content_words.intersection(key_words):
                    matched_keys.append(key)

        # Bước 3: Nếu vẫn chưa có kết quả, dùng so sánh mờ (fuzzy matching) với difflib
        if not matched_keys:
            fuzzy_matches = []
            for key in chat_data.keys():
                ratio = difflib.SequenceMatcher(None, content, key.lower()).ratio()
                if ratio > 0.6:  # Ngưỡng có thể điều chỉnh
                    fuzzy_matches.append((key, ratio))
            if fuzzy_matches:
                fuzzy_matches.sort(key=lambda x: x[1], reverse=True)
                matched_keys = [fuzzy_matches[0][0]]

        # Xử lý kết quả tìm kiếm:
        if not matched_keys:
            reply_text = "em hông hiểu gì hết , dạy em trả lời đi"
        elif len(matched_keys) == 1:
            answer = chat_data[matched_keys[0]]
            chosen_answer = random.choice(answer) if isinstance(answer, list) else answer
            reply_text = f"💬 Mya nói:\n{chosen_answer}"
        else:
            chosen_key = random.choice(matched_keys)
            answer = chat_data[chosen_key]
            chosen_answer = random.choice(answer) if isinstance(answer, list) else answer
            reply_text = f"💬 Mya nói:\n{chosen_answer}"

    print(f"DEBUG - Tin nhắn trả lời: {reply_text}")
    send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=120000)

def get_mitaizl():
    """
    Trả về một dictionary ánh xạ lệnh tới các hàm xử lý tương ứng.
    """
    return {
        'day': handle_teach_command,
        'mya': handle_sim_command
    }
