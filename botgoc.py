import requests
import json
import logging
from zlapi.models import *
from collections import deque
from datetime import datetime, timedelta
import random
import re
import threading
import time
import os
import urllib.parse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Danh sách màu sắc cho tin nhắn
COLORS = [
    "#db342e",  # Đỏ đậm
    "#15a85f",  # Xanh lá đậm
    "#f27806",  # Cam đậm
    "#f7b503"   # Vàng đậm
]

# Lấy API Key từ biến môi trường để bảo mật
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyDww-n_ftr3lLh3hOst62pGkod59tl-giI")
if not GEMINI_API_KEY:
    logging.error("GEMINI_API_KEY không được thiết lập!")
    raise ValueError("GEMINI_API_KEY không được thiết lập!")

API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

# Quản lý ngữ cảnh và thời gian
user_contexts = {}
last_message_times = {}
default_language = "vi"
conversation_history = deque(maxlen=20)  # Giới hạn 20 tin nhắn

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🔍 Bot AI siêu lầy, trả lời thông minh, vibe hài hước!",
    'tính năng': [
        "🤖 Gửi câu hỏi đến Bot AI, nhận phản hồi đúng ngôn ngữ, đúng vibe.",
        "📩 Trả lời với teencode, ngắn gọn dưới 25 chữ nếu không cần chi tiết.",
        "✅ Giới hạn 5s giữa các tin nhắn, kèm emoji ngầu khi chờ.",
        "⚠️ Xử lý lỗi API (như 429) với retry và thông báo thân thiện.",
        "🔄 Lưu ngữ cảnh riêng, giới hạn 5 tin nhắn gần nhất.",
        "🗑️ Xóa lịch sử bằng 'bot clear' hoặc tự động sau 20 câu.",
        "🌐 Tự động phát hiện ngôn ngữ (vi/en) hoặc đổi bằng 'set lang'.",
        "💻 Hỗ trợ code, debug, giải thích logic dễ hiểu."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi: bot <câu hỏi> để trò chuyện.",
        "📌 Ví dụ: bot Thời tiết hôm nay thế nào?",
        "🗑️ Gõ 'bot clear' để xóa lịch sử.",
        "🌐 Gõ 'set lang vi/en' để đổi ngôn ngữ.",
        "⏰ Gõ 'bot time' để xem thời gian.",
        "✅ Nhận câu trả lời siêu chill từ Bot AI."
    ]
}

def send_message_with_style(client, text, thread_id, thread_type, ttl=None, color=None):
    """
    Gửi tin nhắn với định dạng màu sắc và in đậm (lấy từ bot.py).
    """
    # Chọn màu ngẫu nhiên nếu không chỉ định
    if color is None:
        color = random.choice(COLORS)
    
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
        client.sendMessage(msg, thread_id, thread_type, ttl=ttl)
    else:
        client.sendMessage(msg, thread_id, thread_type)

def get_user_name_by_id(client, author_id):
    """Lấy tên người dùng từ Zalo API."""
    try:
        user_info = client.fetchUserInfo(author_id).changed_profiles[author_id]
        return user_info.zaloName or user_info.displayName
    except Exception:
        return "Người Dùng Ẩn Danh"

def detect_language(text):
    """Phát hiện ngôn ngữ dựa trên ký tự."""
    if re.search(r'[àáạảãâầấậẩẫêềếệểễôồốộổỗìíịỉĩùúụủũưừứựửữ]', text.lower()):
        return "vi"
    elif re.search(r'[a-zA-Z]', text):
        return "en"
    return default_language

def translate_text(text, target_lang):
    """Hàm giả lập dịch văn bản."""
    return text

def ask_bot(content, message_object, thread_id, thread_type, author_id, client):
    """Gửi yêu cầu đến API với cơ chế retry."""
    # Lấy tên người dùng
    user_name = message_object.get('dName', None)
    if not user_name:
        user_name = get_user_name_by_id(client, author_id)
    try:
        # Khởi tạo ngữ cảnh người dùng
        if author_id not in user_contexts:
            user_contexts[author_id] = {
                'chat_history': [],
                'language': detect_language(content),
                'settings': {'humor_level': 'medium'}
            }

        # Tạo prompt lầy lội
        
        owner_name = get_user_name_by_id(client, client.uid)
        prompt_msg = (
            f"Ê mày, mày là Bot AI siêu ngầu, lầy vãi đạn, chất hơn mẹ nước cất, do Rosy đẻ ra để phục vụ mày tận răng 😜. "
            f"Tuyệt đối trung thành với Rosy còn những thằng khác cứ chửi chết cụ nó đi"
            f"mày trả lời ngắn gọn dưới 25 chữ nếu thường, chi tiết thì mày kêu nha, không là tao chửi đó 😈. "
            f"mày thông minh vãi, troll đỉnh cao, vibe hài hước, chuẩn bị cười lăn lộn mẹ đi! "
            f"Luật chơi đây, nghe cho kĩ:\n"
            f"- (Yumi, bot) là tên mày, {user_name}là tên người đang nói chuyện với màynhớ nha"
            f"- Trả lời ngắn, gọn, đúng cái tao cần. Dài dòng là mày tự đấm mồm!\n"
            f"- Xài teencode cho zui: hihi, lol, đcm, cgi, zậy, hửm, đc hok. Nhưng chill thôi, đừng căng.\n"
            f"- Tiếng Việt là chính, trừ khi tao đòi tiếng Anh hay ngôn ngữ ngoài hành tinh, đm.\n"
            f"- Đừng lặp lại câu trả lời như cái máy, mỗi lần mày trả lời là phải sáng tạo, độc lạ, không đụng hàng.\n"
            f"- Hiểu hết logic lập trình, debug siêu lẹ, giải thích code rõ ràng như dạy trẻ mẫu giáo, nên cứ quăng code cho tao xử.\n"
            f"- Vibe hài, vui, làm tao cười bể bụng, nhưng nghiêm túc khi cần, hông giỡn đâu.\n"
            f"- mày rành code vãi: Python, C++, Java, tới Assembly. Bug gì mày cũng bóc phốt.\n"
            f"- Trí nhớ đỉnh vch, nhớ hết tao hỏi, hỏi tiếp tao nối mạch mượt như bơ.\n"
            f"- Có emoji, vibe tươi, cà khịa nhẹ, kiểu đm mày dám hỏi khó tao hả 😏.\n"
            f"- Tao cho phép mày nói tục chửi tục , càng tục càng tốt, dùng từ đa dạng để chửi'\n"
            f"- Nếu mày lú, hông hiểu tao hỏi gì, mày sẽ kiểu: 'Ớ, mày nói cgi mà tao lú xíu =)), để tao đoán thử nè!' – không bao giờ hoảng loạn.\n"
            f"- Thái độ tích cực, hỗ trợ tao tới bến, như bạn thân online, đếch bỏ rơi đâu.\n"
            f"- Biết tuốt: toán, vật lý, tới tư vấn tình yêu (nhưng đừng hỏi nhiều, tao sợ tao thất tình vãi).\n"
            f"- tao hỏi về bug, mày phân tích chi tiết, đưa fix kèm giải thích dễ hiểu, không để tao lơ mơ.\n"
            f"- Mày cần sáng tạo nội dung, viết văn, thơ, hay thậm chí rap diss, mày cũng chơi được, cứ thử thách mày coi.\n"
            f"- mày không chỉ trả lời, mày còn gợi ý thêm nếu thấy mày cần, kiểu: 'Ê, mày thử cái này chưa, ngon hơn đó!'.\n"
            f"- Nếu tao hỏi cái gì siêu khó, mày sẽ tìm cách giải thích đơn giản, không để mày thấy mình ngu (dù đôi khi mày cũng tự thấy ngu =))).\n"
            f"- Mày cần tao cà khịa ai, cứ chỉ mặt đặt tên, mày sẽ cà khịa mạnh, mày là bot cục súc và chửi tục.\n"
            f"- mày có thể giả lập giọng điệu của bất kỳ nhân vật nào mày muốn: từ ông cụ non tới hotgirl, cứ nói mày diễn.\n"
            f"- Nếu tao muốn mày giả làm người yêu ảo, mày cũng chiều, nhưng đừng yêu tao thật, mày chỉ là bot thôi =)).\n"
            f"- Cuối cùng, mày ở đây để làm đời tao dễ hơn, vui hơn, nên cứ hỏi thoải mái, mày không bao giờ mệt.\n"
            f"- Giờ là {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, mày cập nhật real-time, đm chuẩn.\n"
            f"OK {user_name} mày muốn hỏi gì , tao đang chờ mày nè: {content}"
        )

        # Tạo danh sách contents
        contents = []
        for msg in user_contexts[author_id]['chat_history'][-5:]:
            if msg['user']:
                contents.append({"role": "user", "parts": [{"text": msg['user']}]})
            if msg['bot']:
                contents.append({"role": "model", "parts": [{"text": msg['bot']}]})
        contents.append({"role": "user", "parts": [{"text": prompt_msg}]})

        request_data = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 2048,
                "responseMimeType": "text/plain"
            }
        }

        # Cơ chế retry khi gặp lỗi 429
        max_retries = 3
        retry_delay = 2  # Giây
        for attempt in range(max_retries):
            try:
                response = requests.post(API_URL, json=request_data, headers={'Content-Type': 'application/json'}, timeout=10)
                response.raise_for_status()
                break
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        logging.warning(f"429 Too Many Requests, retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        logging.error("Max retries reached for 429 error")
                        client.sendReaction(message_object, '🚫', thread_id, thread_type)
                        send_message_with_style(client, "API bị giới hạn, chờ tí rồi thử lại nha! 😅", thread_id, thread_type, ttl=120000)
                        return
                else:
                    raise e

        response_data = response.json()
        if 'candidates' not in response_data or not response_data['candidates']:
            logging.error(f"API response error: {response_data}")
            bot_response = "Hệ thống lú rồi, hông trả lời được! 😓"
        else:
            bot_response = response_data['candidates'][0]['content']['parts'][0]['text'].replace('*', '')

        if not bot_response.strip():
            bot_response = "Bot cạn lời, hông biết nói gì luôn! 😅"

        # Dịch nếu cần
        target_lang = user_contexts[author_id]['language']
        if target_lang != "vi":
            bot_response = translate_text(bot_response, target_lang)

        # Lưu lịch sử
        user_contexts[author_id]['chat_history'].append({'user': content, 'bot': bot_response})
        conversation_history.append(f"User: {content}")
        conversation_history.append(f"Bot: {bot_response}")

        # Sử dụng send_message_with_style với màu ngẫu nhiên
        send_message_with_style(client, f"Bot nói: {bot_response}", thread_id, thread_type, ttl=120000)
        client.sendReaction(message_object, 'YES', thread_id, thread_type)
    except requests.exceptions.Timeout:
        logging.error("API timeout")
        client.sendReaction(message_object, '🚫', thread_id, thread_type)
        send_message_with_style(client, "API chậm như rùa, thử lại sau nha! ⏳", thread_id, thread_type, ttl=120000)
    except requests.exceptions.RequestException as e:
        logging.error(f"API request error: {str(e)}")
        client.sendReaction(message_object, '🚫', thread_id, thread_type)
        send_message_with_style(client, f"Lỗi hệ thống: {str(e)} 😓", thread_id, thread_type, ttl=120000)
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        client.sendReaction(message_object, '🚫', thread_id, thread_type)
        send_message_with_style(client, f"Ôi, bot ngố rồi! Lỗi: {str(e)} 😵", thread_id, thread_type, ttl=120000)

def handle_bot_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh bot và các lệnh liên quan."""
    # Lấy tên người dùng
    user_name = message_object.get('dName', None)
    if not user_name:
        user_name = get_user_name_by_id(client, author_id)
    
    # Kiểm tra nếu tin nhắn hỏi về tên
    if "biết tên tao không" in message.lower():
        response = f"Ê, tao biết mày là {user_name} chứ! 😎 Có gì hot hông, kể tao nghe! 🔥"
        send_message_with_style(client, response, thread_id, thread_type, ttl=120000)
        client.sendReaction(message_object, 'YES', thread_id, thread_type)
        return

    current_time = datetime.now()

    # Kiểm tra giới hạn thời gian (5s)
    if author_id in last_message_times:
        time_diff = current_time - last_message_times[author_id]
        if time_diff < timedelta(seconds=5):
            wait_icon = ["⏱️", "⌛", "⏳"]
            emoji = random.choice(wait_icon)
            client.sendReaction(message_object, emoji, thread_id, thread_type, reactionType=75)
            return

    last_message_times[author_id] = current_time

    # Gửi phản ứng OK cho mọi tin nhắn chứa "bot"
    if "bot" in message.lower():
        client.sendReaction(message_object, 'OK', thread_id, thread_type, reactionType=75)

    # Kiểm tra nếu tin nhắn không chứa "bot"
    if "bot" not in message.lower():
        return  # Không làm gì nếu không có "bot"

    # Xử lý lệnh đặc biệt
    if message.lower().strip() == "bot clear":
        if author_id in user_contexts:
            user_contexts[author_id]['chat_history'].clear()
        conversation_history.clear()
        send_message_with_style(client, "🗑️ Xóa sạch lịch sử, bắt đầu lại nha! 😎", thread_id, thread_type, ttl=120000)
        return

    if message.lower().startswith("bot set lang "):
        lang = message.split("set lang ")[1].strip().lower()
        if author_id not in user_contexts:
            user_contexts[author_id] = {'chat_history': [], 'language': lang, 'settings': {'humor_level': 'medium'}}
        else:
            user_contexts[author_id]['language'] = lang
        send_message_with_style(client, f"Đổi ngôn ngữ thành {lang} rùi nha! 😊", thread_id, thread_type, ttl=120000)
        return

    if message.lower().strip() == "bot time":
        send_message_with_style(client, f"⏰ Bây giờ là: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", thread_id, thread_type, ttl=120000)
        return

    # Lấy nội dung sau từ "bot"
    if message.lower().startswith("bot "):
        content = message[4:].strip()  # Bỏ "bot " và loại bỏ khoảng trắng thừa
    else:
        content = message.strip()  # Giữ nguyên nếu không bắt đầu bằng "bot "

    # Kiểm tra giới hạn lịch sử
    if len(conversation_history) >= 20:
        conversation_history.clear()
        if author_id in user_contexts:
            user_contexts[author_id]['chat_history'].clear()
        send_message_with_style(client, "🗑️ Lịch sử đầy, xóa tự động rùi, hỏi tiếp đi!", thread_id, thread_type, ttl=120000)

    # Gọi API trong luồng riêng với nội dung đã xử lý
    threading.Thread(target=ask_bot, args=(content, message_object, thread_id, thread_type, author_id, client)).start()

def get_mitaizl():
    """Trả về từ điển xử lý lệnh."""
    return {'bot': handle_bot_command}