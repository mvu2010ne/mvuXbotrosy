import time
import requests
import tempfile
import threading
from zlapi.models import Message

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Trò chơi Đuổi Hình Bắt Chữ.",
    'tính năng': [
        "🎮 Nhận câu hỏi bằng hình ảnh từ API",
        "⏳ Câu hỏi có hiệu lực trong 3 phút",
        "🤔 Gợi ý số ký tự và trợ giúp trả lời",
        "🚀 Kiểm tra và xử lý câu trả lời của người chơi",
        "📂 Lưu trữ phiên chơi theo từng nhóm/chat",
        "🔄 Tự động gửi câu hỏi mới khi trả lời đúng hoặc hết thời gian",
        "🛑 Lệnh stop để dừng tự động gửi câu hỏi"
    ],
    'hướng dẫn sử dụng': [
        "▶️ Dùng lệnh 'dhbc' để nhận câu hỏi và bật chế độ tự động.",
        "✍️ Trả lời bằng cách nhập 'tl <đáp án>'.",
        "⏳ Mỗi câu hỏi có thời gian giới hạn là 3 phút.",
        "🎉 Trả lời đúng sẽ tự động gửi câu hỏi mới.",
        "⌛ Nếu hết thời gian mà chưa trả lời, câu hỏi cũ sẽ bị bỏ và câu hỏi mới được gửi.",
        "🛑 Dùng lệnh 'stop' để dừng chế độ tự động gửi."
    ]
}

# Dictionary lưu trữ trò chơi đang hoạt động cho mỗi thread.
active_games = {}
# Biến lưu trạng thái tự động gửi cho mỗi thread (True: auto bật, False: auto tắt)
auto_mode = {}
# Lưu trữ đối tượng timer cho mỗi thread để có thể huỷ khi cần
auto_timers = {}

GAME_VALID_SECONDS = 180   # 3 phút
DEFAULT_REPLY_TTL = 60000  # 60 giây

def schedule_timer(thread_id, thread_type, client):
    # Huỷ timer cũ nếu tồn tại
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
            # Hết thời gian, xoá câu hỏi hiện tại
            active_games.pop(thread_id, None)
            if auto_mode.get(thread_id, False):
                client.sendMessage(thread_id, thread_type, text="⌛ Hết thời gian, câu hỏi mới đang được gửi tự động...")
                send_question_auto(thread_id, thread_type, client)

def send_question_auto(thread_id, thread_type, client):
    now = time.time()
    try:
        # Đã thay đổi API endpoint
        response = requests.get("https://api-dowig.onrender.com/game/dhbcv1")
        if response.status_code != 200:
            client.sendMessage(thread_id, thread_type, text="⚠️ Không thể truy cập API game. Vui lòng thử lại sau.")
            return
        data = response.json()
        game_data = data.get("dataGame")
        if not game_data:
            client.sendMessage(thread_id, thread_type, text="⚠️ Dữ liệu trò chơi không hợp lệ.")
            return

        tukhoa  = game_data.get("tukhoa", "N/A")
        sokitu  = game_data.get("sokitu", "N/A")
        goiy    = game_data.get("suggestions", "N/A")
        lienket = game_data.get("link", "N/A")
        
        # Lưu đáp án và thời gian bắt đầu câu hỏi
        active_games[thread_id] = {
            "answer": tukhoa.lower().strip(),
            "timestamp": now
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/90.0.4430.93 Safari/537.36"
        }
        image_response = requests.get(lienket, stream=True, headers=headers)
        if image_response.status_code != 200:
            active_games.pop(thread_id, None)
            client.sendMessage(thread_id, thread_type, text="⚠️ Không thể tải hình ảnh từ API. Vui lòng thử lại sau.")
            return

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            tmp_file.write(image_response.content)
            temp_image_path = tmp_file.name

        response_text = (
            "🤔 Đuổi Hình Bắt Chữ\n"
            f"🔠 Số ký tự: {sokitu}\n"
            f"💡 Gợi ý:    {goiy}\n\n"
            "👉 Hãy trả lời bằng cách nhập: tl <đáp án>\n"
            "⏳ Lưu ý: Câu hỏi có hiệu lực trong 3 phút.\n"
            "🛑 Soạn dhbcstop để dừng việc gửi câu hỏi tự động"
        )
        
        client.sendLocalImage(
            temp_image_path,
            thread_id=thread_id,
            thread_type=thread_type,
            message=Message(text=response_text),
            width=1920,
            height=1080,
            ttl=180000
        )
        # Lên lịch timer để kiểm tra thời gian hiệu lực của câu hỏi
        schedule_timer(thread_id, thread_type, client)
    except Exception as e:
        active_games.pop(thread_id, None)
        client.sendMessage(thread_id, thread_type, text="🚨 Đã xảy ra lỗi: " + str(e))

def handle_dhbc_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản ứng ngay khi nhận lệnh chính xác
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    
    parts = message.split()
    if len(parts) != 1:
        error_message = Message(text="❌ Cú pháp không hợp lệ.\n👉 Vui lòng nhập: dhbc")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=DEFAULT_REPLY_TTL)
        return

    # Bật chế độ tự động cho thread này
    auto_mode[thread_id] = True

    now = time.time()
    # Kiểm tra nếu đã có câu hỏi chưa hết hiệu lực
    if thread_id in active_games:
        game_info = active_games[thread_id]
        elapsed = now - game_info["timestamp"]
        if elapsed < GAME_VALID_SECONDS:
            remaining = int(GAME_VALID_SECONDS - elapsed)
            error_message = Message(
                text=f"⌛ Bạn đang có câu hỏi chưa kết thúc.\n💡 Hãy trả lời hoặc chờ {remaining} giây để nhận câu hỏi mới."
            )
            client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=10000)
            return
        else:
            active_games.pop(thread_id, None)
    
    send_question_auto(thread_id, thread_type, client)

def handle_answer_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản ứng khi người dùng nhập lệnh trả lời đúng cú pháp
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    
    parts = message.split(maxsplit=1)
    if len(parts) < 2:
        error_message = Message(text="❌ Cú pháp không hợp lệ.\n👉 Vui lòng nhập: tl <đáp án>")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=DEFAULT_REPLY_TTL)
        return

    now = time.time()
    if thread_id not in active_games:
        error_message = Message(text="⚠️ Chưa có trò chơi nào đang hoạt động.\n👉 Hãy nhập dhbc để bắt đầu trò chơi.")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=DEFAULT_REPLY_TTL)
        return

    game_info = active_games[thread_id]
    elapsed = now - game_info["timestamp"]
    if elapsed >= GAME_VALID_SECONDS:
        active_games.pop(thread_id, None)
        error_message = Message(text="⌛ Câu hỏi đã hết thời gian hiệu lực.\n👉 Hãy nhập dhbc để bắt đầu trò chơi mới.")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=DEFAULT_REPLY_TTL)
        # Nếu chế độ auto đang bật, tự động gửi câu hỏi mới
        if auto_mode.get(thread_id, False):
            send_question_auto(thread_id, thread_type, client)
        return

    user_answer = parts[1].strip().lower()
    correct_answer = game_info["answer"]

    if user_answer == correct_answer:
        active_games.pop(thread_id, None)
        reply_text = "🎉 Quá đỉnh! Bạn đã trả lời rất chính xác \n👉 Câu hỏi tiếp theo"
        client.replyMessage(Message(text=reply_text), message_object, thread_id, thread_type, ttl=DEFAULT_REPLY_TTL)
        # Tự động gửi câu hỏi mới nếu chế độ auto đang bật
        if auto_mode.get(thread_id, False):
            send_question_auto(thread_id, thread_type, client)
    else:
        remaining = int(GAME_VALID_SECONDS - elapsed)
        reply_text = f"❌ Sai rồi, hãy thử lại. Câu hỏi sẽ còn hiệu lực trong {remaining} giây."
        client.replyMessage(Message(text=reply_text), message_object, thread_id, thread_type, ttl=5000)

def handle_stop_command(message, message_object, thread_id, thread_type, author_id, client):
    # Tắt chế độ tự động gửi câu hỏi
    auto_mode[thread_id] = False
    if thread_id in auto_timers:
        timer = auto_timers.pop(thread_id)
        timer.cancel()
    client.replyMessage(Message(text="🛑 Chế độ tự động gửi câu hỏi đã dừng."), message_object, thread_id, thread_type, ttl=DEFAULT_REPLY_TTL)

def get_mitaizl():
    return {
        'dhbc': handle_dhbc_command,
        'tl': handle_answer_command,
        'dhbcstop': handle_stop_command
    }