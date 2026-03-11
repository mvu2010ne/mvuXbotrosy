import time
import requests
import threading
import tempfile
from zlapi.models import Message
import unidecode
import random

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🎮 Trò chơi Vua Tiếng Việt thách thức nhập từ khóa có dấu.",
    'tính năng': [
        "📋 Lấy từ khóa ngẫu nhiên từ API và xáo trộn để người chơi đoán.",
        "⌨️ Kiểm tra đáp án chính xác (bao gồm dấu tiếng Việt).",
        "🔄 Tự động gửi câu hỏi mới khi trả lời đúng hoặc hết 3 phút.",
        "📊 Theo dõi cấp độ và số câu hỏi trong từng nhóm.",
        "🛑 Dừng chế độ tự động bằng lệnh vtstop."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi vtv để bắt đầu trò chơi và nhận câu hỏi.",
        "📩 Gửi vt <đáp án> để trả lời câu hỏi.",
        "📩 Gửi vtstop để dừng chế độ tự động.",
        "📌 Ví dụ: vtv hoặc vt nhà cửa.",
        "✅ Nhận câu hỏi mới hoặc kết quả trả lời ngay lập tức."
    ]
}

# Dictionary lưu trữ phiên chơi cho mỗi thread.
active_games = {}
# Biến lưu trạng thái tự động gửi (True: bật, False: tắt)
auto_mode = {}
# Lưu trữ đối tượng timer cho mỗi thread
auto_timers = {}

GAME_VALID_SECONDS = 180   # 3 phút
DEFAULT_REPLY_TTL = 60000  # 60 giây

def schedule_timer(thread_id, thread_type, client):
    if thread_id in auto_timers:
        timer = auto_timers[thread_id]
        timer.cancel()
    timer = threading.Timer(GAME_VALID_SECONDS, lambda: auto_timer_callback(thread_id, thread_type, client))
    auto_timers[thread_id] = timer
    timer.start()

def auto_timer_callback(thread_id, thread_type, client):
    now = time.time()
    if thread_id in active_games:
        game_info = active_games[thread_id]
        elapsed = now - game_info["timestamp"]
        if elapsed >= GAME_VALID_SECONDS:
            active_games.pop(thread_id, None)
            if auto_mode.get(thread_id, False):
                client.sendMessage(Message(text="⌛ Hết thời gian, câu hỏi mới đang được gửi tự động..."), thread_id, thread_type)
                send_question_auto(thread_id, thread_type, client, None)

def shuffle_word(word):
    if len(word) <= 1:
        return word
    first_char = word[0].upper()
    remaining_chars = list(word[1:])
    random.shuffle(remaining_chars)
    return "/".join([first_char] + remaining_chars)

def send_question_auto(thread_id, thread_type, client, message_object=None):
    now = time.time()
    try:
        response = requests.get("https://api.sumiproject.net/game/vuatiengviet")
        if response.status_code != 200:
            client.sendMessage(
                Message(text="⚠️ Không thể truy cập API trò chơi. Vui lòng thử lại sau."),
                thread_id,
                thread_type
            )
            return
        
        data = response.json()
        print(f"DEBUG: Dữ liệu API nhận được: {data}")
        keyword = data.get("keyword")
        
        if not keyword:
            client.sendMessage(
                Message(text="⚠️ Dữ liệu trò chơi không hợp lệ từ API."),
                thread_id,
                thread_type
            )
            return

        # Lấy tên người dùng từ message_object nếu có
        author_name = "Người chơi"
        if message_object and hasattr(message_object, 'author'):
            author_id = message_object.author
            user_info = client.fetchUserInfo(author_id)[author_id]
            author_name = user_info.name if user_info else "Người chơi"

        # Lưu hoặc cập nhật phiên chơi
        if thread_id not in active_games:
            active_games[thread_id] = {
                "answer": keyword.lower().strip(),
                "timestamp": now,
                "level": 1,
                "question_count": 1,
                "author_name": author_name
            }
        else:
            active_games[thread_id]["answer"] = keyword.lower().strip()
            active_games[thread_id]["timestamp"] = now
            active_games[thread_id]["author_name"] = author_name

        # Xáo trộn từ khóa
        shuffled_text = shuffle_word(keyword.lower().strip())

        # Lấy cấp độ hiện tại
        current_level = active_games[thread_id]["level"]

        # Tạo thông báo với tên người dùng
        response_text = (
            f"🚦 @{author_name} 🛫🛬🛬\n"
            f"➜ Level {current_level} - Game Vua Từ 👑\n"
            "➜ Thể loại: Tiếng Việt\n"
            f"➜ Câu hỏi: {shuffled_text}\n"
            "➜ Gợi ý hiện tại: \n"
            "💢 Hãy sắp xếp lại thành từ hoặc câu hoàn chỉnh nhé! 🍁\n"
            "💡 Dùng: vt <đáp án> để trả lời"
        )

        client.sendMessage(
            Message(text=response_text),
            thread_id,
            thread_type
        )

        schedule_timer(thread_id, thread_type, client)

    except Exception as e:
        active_games.pop(thread_id, None)
        error_str = "🚨 Đã xảy ra lỗi: " + str(e)
        client.sendMessage(
            Message(text=error_str),
            thread_id,
            thread_type
        )

def handle_vt_command(message, message_object, thread_id, thread_type, author_id, client):
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
    parts = message.split()
    if len(parts) != 1:
        error_message = Message(text="❌ Cú pháp không hợp lệ.\n👉 Vui lòng nhập: vt")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=DEFAULT_REPLY_TTL)
        return
    auto_mode[thread_id] = True
    now = time.time()
    if thread_id in active_games:
        game_info = active_games[thread_id]
        elapsed = now - game_info["timestamp"]
        if elapsed < GAME_VALID_SECONDS:
            remaining = int(GAME_VALID_SECONDS - elapsed)
            error_message = Message(text=f"⌛ Bạn đang có câu hỏi chưa kết thúc.\n💡 Hãy trả lời hoặc chờ {remaining} giây để nhận câu hỏi mới.")
            client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=10000)
            return
        else:
            active_games.pop(thread_id, None)
    send_question_auto(thread_id, thread_type, client, message_object)

def handle_vt_answer_command(message, message_object, thread_id, thread_type, author_id, client):
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
    parts = message.split(maxsplit=1)
    if len(parts) < 2:
        error_message = Message(text="❌ Cú pháp không hợp lệ.\n👉 Vui lòng nhập: vt <đáp án>")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=DEFAULT_REPLY_TTL)
        return
    now = time.time()
    if thread_id not in active_games:
        error_message = Message(text="⚠️ Chưa có trò chơi nào đang hoạt động.\n👉 Hãy nhập vt để bắt đầu trò chơi.")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=DEFAULT_REPLY_TTL)
        return
    game_info = active_games[thread_id]
    elapsed = now - game_info["timestamp"]
    if elapsed >= GAME_VALID_SECONDS:
        active_games.pop(thread_id, None)
        error_message = Message(text="⌛ Câu hỏi đã hết thời gian hiệu lực.\n👉 Hãy nhập vt để bắt đầu trò chơi mới.")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=DEFAULT_REPLY_TTL)
        if auto_mode.get(thread_id, False):
            send_question_auto(thread_id, thread_type, client, message_object)
        return
    user_answer = parts[1].strip().lower()  # Chuyển đáp án người dùng về chữ thường
    correct_answer = game_info["answer"].lower()  # Chuyển đáp án đúng về chữ thường
    if user_answer == correct_answer:
        game_info["level"] += 1
        game_info["question_count"] += 1
        reply_text = f"🎉 Quá đỉnh! Bạn đã trả lời rất chính xác.\n👉 Đã lên Level {game_info['level']}. Câu hỏi tiếp theo:"
        client.replyMessage(Message(text=reply_text), message_object, thread_id, thread_type, ttl=DEFAULT_REPLY_TTL)
        if auto_mode.get(thread_id, False):
            send_question_auto(thread_id, thread_type, client, message_object)
    else:
        remaining = int(GAME_VALID_SECONDS - elapsed)
        reply_text = f"❌ Sai rồi, hãy thử lại. Câu hỏi còn hiệu lực trong {remaining} giây."
        client.replyMessage(Message(text=reply_text), message_object, thread_id, thread_type, ttl=5000)

def handle_stop_command(message, message_object, thread_id, thread_type, author_id, client):
    auto_mode[thread_id] = False
    if thread_id in auto_timers:
        timer = auto_timers.pop(thread_id)
        timer.cancel()
    client.replyMessage(Message(text="🛑 Chế độ tự động gửi câu hỏi đã dừng."), message_object, thread_id, thread_type, ttl=DEFAULT_REPLY_TTL)

def get_mitaizl():
    return {
        'vtv': handle_vt_command,
        'vt': handle_vt_answer_command,
        'vtstop': handle_stop_command
    }