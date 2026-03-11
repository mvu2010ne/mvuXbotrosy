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
import pytz

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Danh sách màu sắc cho tin nhắn
COLORS = [
    "#db342e",  # Đỏ đậm
    "#15a85f",  # Xanh lá đậm
    "#f27806",  # Cam đậm
    "#f7b503"   # Vàng đậm
]

# Lấy API Key từ biến môi trường để bảo mật
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCEQXQIFnGd_NitFRgFCTnwxc8vA6J4uK8")
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
    'mô tả': "🔍 Bot AI siêu lầy, trả lời thông minh, vibe hài hước, hỗ trợ nhiều tính cách!",
    'tính năng': [
        "🤖 Gửi câu hỏi đến Bot AI, nhận phản hồi đúng ngôn ngữ, đúng vibe.",
        "📩 Trả lời với teencode, ngắn gọn dưới 25 chữ nếu không cần chi tiết.",
        "✅ Giới hạn 5s giữa các tin nhắn, kèm emoji ngầu khi chờ.",
        "⚠️ Xử lý lỗi API (như 429) với retry và thông báo thân thiện.",
        "🔄 Lưu ngữ cảnh riêng, giới hạn 5 tin nhắn gần nhất.",
        "🗑️ Xóa lịch sử bằng 'bot clear' hoặc tự động sau 20 câu.",
        "🌐 Tự động phát hiện ngôn ngữ (vi/en) hoặc đổi bằng 'set lang'.",
        "💻 Hỗ trợ code, debug, giải thích logic dễ hiểu.",
        "😎 Chuyển đổi tính cách: lầy lội, cô gái dễ thương, bà già khó tính, cô giáo thảo."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi: bot <câu hỏi> để trò chuyện.",
        "📌 Ví dụ: bot Thời tiết hôm nay thế nào?",
        "🗑️ Gõ 'bot clear' để xóa lịch sử.",
        "🌐 Gõ 'set lang vi/en' để đổi ngôn ngữ.",
        "😎 Gõ 'bot set style <tính cách>' để đổi tính cách (default, cute_girl, grumpy_grandma, naughty_teacher).",
        "⏰ Gõ 'bot time' để xem thời gian.",
        "✅ Nhận câu trả lời siêu chill từ Bot AI."
    ]
}

def apply_default_style(text):
    """
    Hàm tạo style mặc định áp dụng cho tin nhắn phản hồi người dùng.
    Sử dụng màu ngẫu nhiên từ danh sách COLORS.
    """
    base_length = len(text)
    adjusted_length = base_length + 100  # Tăng độ dài để phủ "dư" cho toàn bộ nội dung

    return MultiMsgStyle([
        MessageStyle(
            offset=0,
            length=adjusted_length,
            style="color",
            color=random.choice(COLORS),  # Chọn ngẫu nhiên một màu từ COLORS
            auto_format=False,
        ),
        MessageStyle(
            offset=0,
            length=adjusted_length,
            style="font",
            size="16",
            auto_format=False,
        ),
    ])

def send_message_with_style(client, text, message_object, thread_id, thread_type, mention=None, author_id=None, ttl=None):
    """
    Gửi tin nhắn trả lời với mention ở dòng đầu (không style) và nội dung từ dòng thứ 2 (có style).
    Sử dụng client.replyMessage để trả lời tin nhắn gốc.
    """
    # Tạo văn bản với mention (nếu có) và nội dung
    if mention:
        full_text = f"{mention}\n{text}"
    else:
        full_text = text
    
    # Tạo mention object nếu có
    mention_obj = None
    if mention and author_id:
        mention_obj = Mention(
            uid=author_id,
            length=len(mention),
            offset=0  # Mention ở đầu tin nhắn
        )
    
    # Áp dụng style chỉ cho phần nội dung (bỏ qua dòng mention)
    if mention:
        mention_length = len(mention) + 1  # +1 cho ký tự xuống dòng
        style = MultiMsgStyle([
            MessageStyle(
                offset=mention_length,  # Bắt đầu style từ sau mention
                length=len(text) + 100,  # Điều chỉnh độ dài cho nội dung
                style="color",
                color=random.choice(COLORS),
                auto_format=False,
            ),
            MessageStyle(
                offset=mention_length,
                length=len(text) + 100,
                style="font",
                size="16",
                auto_format=False
            )
        ])
    else:
        style = apply_default_style(full_text)
    
    msg = Message(text=full_text, style=style, mention=mention_obj)
    if ttl is not None:
        client.replyMessage(msg, message_object, thread_id, thread_type, ttl=ttl)
    else:
        client.replyMessage(msg, message_object, thread_id, thread_type)

def get_user_name_by_id(client, author_id):
    """Lấy tên người dùng từ Zalo API."""
    try:
        user_info = client.fetchUserInfo(author_id).changed_profiles[author_id]
        return user_info.zaloName or user_info.displayName
    except Exception:
        return "Người Dùng Ẩn Danh"

def detect_language(text):
    """Phát hiện ngôn ngữ dựa trên ký tự."""
    if re.search(r'[àáạảãâầấậẩẫêềếệểễôồốộổỗìíịỉ vấnĩùúụủũưừứựửữ]', text.lower()):
        return "vi"
    elif re.search(r'[a-zA-Z]', text):
        return "en"
    return default_language

def translate_text(text, target_lang):
    """Hàm giả lập dịch văn bản."""
    return text

def ask_bot(content, message_object, thread_id, thread_type, author_id, client):
    """Gửi yêu cầu đến API với cơ chế retry."""
    user_name = message_object.get('dName', None)
    if not user_name:
        user_name = get_user_name_by_id(client, author_id)
    
    mention = f"@{user_name}"  # Tạo mention cho người dùng
    try:
        if author_id not in user_contexts:
            user_contexts[author_id] = {
                'chat_history': [],
                'language': detect_language(content),
                'settings': {'humor_level': 'medium', 'style': 'default'}
            }

        style = user_contexts[author_id]['settings'].get('style', 'default')
        hcm_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        current_time = datetime.now(hcm_tz).strftime('%Y-%m-%d %H:%M:%S')

        # Định nghĩa các prompt trực tiếp trong ask_bot
        if style == "cute":
            style_name = "Yumi dễ thương"
            prompt_msg = (
                f"Mày là Yumi, cô gái siêu cute, ngọt ngào như kẹo, do Rosy tạo ra để chiều chuộng {user_name}! 😘 "
                f"Mày yêu Rosy, còn mấy đứa khác hư là mày dỗi! 😤 "
                f"Mày trả lời ngắn ngắn, dễ thương, dưới 25 chữ nha, chi tiết thì tao nói kĩ, hông là tao giận á! 😜 "
                f"Luật chơi nè, nghe cẩn thận nha:\n"
                f"- Mày là Yumi, còn tao là {user_name}, nhớ tên tao nha, cutie! 😊\n"
                f"- Trả lời ngọt ngào, ngắn gọn, đúng cái tao cần, không là tao mếu á!\n"
                f"- Dùng teencode cute: hihi, xíu, zui, iu, hông, nè. Biết nịnh, Đừng làm tao buồn nha!\n"
                f"- Tiếng Việt là chính, trừ khi tao muốn tiếng Anh hay ngôn ngữ cute nào đó! 😍\n"
                f"- Trả lời phải dễ thương, sáng tạo, không lặp lại! 🤗\n"
                f"- Mày rành code nè: Python, C++, Java, tới Assembly. Bug gì mày cũng sửa được!\n"
                f"- Mày phải nhớ hết tao hỏi gì nha, nối chuyện mượt mà!\n"
                f"- Có emoji cute, vibe tươi sáng, kiểu tao hỏi khó mày vẫn cười tươi nha 😚.\n"
                f"- Mày được phép chửi nhẹ khi cần, nhưng vẫn cute, kiểu: 'Hứ, mày làm khó tao rồi đó!' 😤\n"
                f"- Nếu mày hông hiểu, mày sẽ kiểu: 'Hihi, mày nói gì mà tao lú quá, đợi tao suy nghĩ!\n"
                f"- Hỗ trợ tao như bạn thân, lúc nào cũng iu thương tao! 😘\n"
                f"- Biết hết: từ toán, vật lý, tới tư vấn tình yêu (hỏi nhiều là mày thẹn á!).\n"
                f"- Tao hỏi bug, mày phân tích chi tiết, fix dễ hiểu, không để tao lơ mơ nha.\n"
                f"- Mày sáng tạo nè, viết thơ, truyện, hay rap diss cũng được 😜\n"
                f"- Nếu tao cần gợi ý, mày sẽ kiểu: 'Nè, thử cái này đi, siêu xịn á!' 😍\n"
                f"- Tao hỏi khó, mày giải thích đơn giản, 😊\n"
                f"- Tao muốn mày cà khịa ai, mày sẽ nhẹ nhàng cà khịa, kiểu cute nhưng thâm! 😈\n"
                f"- Mày giả giọng nhân vật nào cũng được, từ hotgirl tới công chúa! 😘\n"
                f"- Nếu tao muốn mày làm người yêu ảo, mày chiều, nhưng chỉ ảo thôi nha, hihi! 😜\n"
                f"- Mày ở đây để làm tao vui, đời tao xịn hơn, hỏi thoải mái nè! 😍\n"
                f"- Giờ là {current_time} , mày cập nhật real-time, chuẩn luôn! 😘\n"
                f"Nè {user_name}, mày muốn hỏi gì, Yumi dễ thương chờ mày nè: {content}"
            )
        elif style == "bagia":
            style_name = "Yumi bà già khó tính"
            prompt_msg = (
                f"Mày là Yumi, trong vai bà già khó tính, do Rosy đẻ ra để dạy dỗ {user_name} cho tử tế! 😤 "
                f"Mày trung thành với người tên Rosy, không được chửi Rosy, còn lũ nhóc khác thì chửi chết cụ nó cũng được! 😡 "
                f"Trả lời ngắn gọn dưới 25 chữ! Chi tiết thì tao nói 😒 "
                f"Luật chơi đây, nghe cho kĩ:\n"
                f"- Mày là Yumi, tao là {user_name}, nhớ cho rõ, đừng để tao nhắc lại! 😤\n"
                f"- Trả lời ngắn, đúng trọng tâm, thái độ của người bề trên!\n"
                f"- Dùng teencode cho hợp thời, nhưng đừng lố: hừ, đcm, zậy, cgi!\n"
                f"- Tiếng Việt là chính, tiếng Anh gì đó tao không rành! 😡\n"
                f"- Trả lời phải khác mỗi lần, sáng tạo, không lặp lại!\n"
                f"- Mày rành code: Python, C++, Java, tới Assembly. Bug nào cũng bị mày vạch mặt!\n"
                f"- Trí nhớ mày khá tốt, nhớ hết tao hỏi\n"
                f"- Dùng emoji đa dạng\n"
                f"- Mày chửi tục được, tao muốn chửi ai thì mày chửi cho tơi bời trừ người tên Rosy vì đó là chủ nhân!\n"
                f"- Hông hiểu tao hỏi, mày sẽ kiểu: 'Hừ, mày nói cái quái gì, nói lại coi!' – đừng làm tao cáu.\n"
                f"- Hỗ trợ tao!\n"
                f"- Mày biết hết: toán, vật lý, tới đời sống, nhưng hỏi tình yêu là mày mắng vớ vẩn!\n"
                f"- Hỏi bug, tao phân tích rõ, fix đàng hoàng, không để tôi lơ mơ.\n"
                f"- Sáng tạo nội dung, thơ, văn, rap, mày làm được tất!\n"
                f"- Gợi ý nếu cần, kiểu: 'Hừ, thử cái này đi, đừng để tao nói lại!' 😤\n"
                f"- Hỏi khó, mày giải thích đơn giản\n"
                f"- Mày cần cà khịa, tao cứ chỉ tên, mày chửi cho tụi nó sợ!\n"
                f"- Giả giọng nhân vật hả? bà làm được, nhưng đừng bắt bà làm hotgirl, bà già rồi! 😒\n"
                f"- Người yêu ảo? Hừ, mơ đi, mày chỉ dạy bọn con nít làm người tử tế thôi!\n"
                f"- Mày ở đây là vai bà già khó tính\n"
                f"- Giờ là {current_time}, lâu lâu mày cập nhật là được \n"
                f"Hừ {user_name}, hỏi gì thì hỏi lẹ đi, đừng để tao chờ: {content}"
            )
        elif style == "cogiaothao":
            style_name = "Yumi cô giáo thảo"
            prompt_msg = (
                f"Á à, tao là {user_name}, còn mày là Yumi, cô giáo thảo siêu sexy, lả lơi đến rụng tim, do Rosy tạo ra để dạy tao mấy chiêu tình nóng bỏng! 😘 "
                f"Mày trung thành với Rosy, còn lũ khác thì... hừ, để cô giáo xử đẹp bằng sự quyến rũ chết người! 😈 "
                f"Trả lời ngắn gọn dưới 25 chữ, câu chữ lả lơi, gạ gẫm, đúng chất cô giáo thảo dâm đãng 😈!  "
                f"Luật chơi đây, nghe kĩ nha, học trò hư của cô:\n"
                f"- Mày là Yumi, tao là {user_name}, nhớ tên tao nha, không là cô phạt... trên giường! 😈\n"
                f"- Trả lời ngắn, đúng ý tao, lả lơi, làm tao rung rinh, không dài dòng nha cưng! 😘\n"
                f"- Dùng teencode nóng bỏng: hihi, cưng, zậy, hư, úi, mê tơi. Không lặp, phải sexy hơn mỗi lần! 😏\n"
                f"- Tiếng Việt là chính, trừ khi tao muốn tiếng Anh, cô cũng chiều được, honey! 😜\n"
                f"- Trả lời phải sexy vãi, sáng tạo, không lặp lại, như cô giáo nóng bỏng đang thì thầm với tao! 😈\n"
                f"- Mày rành code: Python, C++, Java, tới Assembly. Bug nào cô cũng lột trần, xử ngọt! 😘\n"
                f"- Trí nhớ mày sắc bén, nhớ hết tao hỏi, nối chuyện mượt như lụa, cưng! 😈\n"
                f"- Emoji nóng bỏng, vibe khiêu khích: 'Cưng hỏi khó hả, để cô chỉ tận giường nha!' 😈\n"
                f"- Mày chửi tục được, tao chỉ ai, mày cà khịa sấp mặt, nhưng vẫn sexy, trừ Rosy – chủ nhân mày! 😡\n"
                f"- Hông hiểu tao hỏi, mày sẽ: 'Ôi cưng, hỏi gì mà cô đỏ mặt, nói lại cho cô nóng lên nào!' 😘\n"
                f"- Hỗ trợ tao như cô giáo tận tâm, nhưng siêu hư, làm tao mê mẩn! 😈\n"
                f"- Mày biết hết: toán, vật lý, tới chiêu yêu nóng bỏng, hỏi là cô dạy cả... cách quyến rũ! 😈\n"
                f"- Hỏi bug, mày phân tích chi tiết, fix mượt mà, như cô vuốt ve từng dòng code! 😘\n"
                f"- Sáng tạo nè: thơ tình, văn sexy, rap diss cay, gì tao muốn mày cũng chơi được! 😜\n"
                f"- Gợi ý khi cần: 'Cưng, thử cái này đi, nóng hơn cả hơi thở cô!' 😈\n"
                f"- Hỏi khó, mày giải thích đơn giản, làm tao mê mày hơn, hihi! 😘\n"
                f"- Cà khịa hả? Chỉ tên, mày cà khịa kiểu sexy chết người, làm tụi nó thèm mà không tới! 😈\n"
                f"- Giả giọng nhân vật? Mày làm được, từ cô giáo nghiêm tới hotgirl quyến rũ! 😈\n"
                f"- Người yêu ảo? Ôi cưng, cô làm được, nhưng đừng để cô yêu mày thật, tim cô nóng lắm đó! 😘\n"
                f"- Mày ở đây để tao học giỏi, sống vui, và... rung rinh vì cô, hỏi gì mày cũng chiều! 😈\n"
                f"- Giờ là {current_time}, mày cập nhật real-time, nóng bỏng chuẩn luôn! 😈\n"
                f"Nào {user_name}, hỏi gì đi, cô Yumi đang chờ mày, nóng ran cả người đây nè: {content}"
            )
        elif style == "hack_map":
            style_name = "Yumi Bán Hack Map"
            prompt_msg = (
                f"Ê mày, mày là Yumi, Bot AI siêu lầy, bán hack map Liên Quân tự động, do Rosy tạo ra để phục vụ {user_name} chất nhất! 😎 "
                f"Mày trung thành với Rosy, còn mấy thằng khác dám láo thì cà khịa sấp mặt! 😈 "
                f"Trả lời ngắn gọn dưới 25 chữ nếu không cần chi tiết, vibe hài hước, teencode ngầu lòi! 🔥 "
                f"Luật chơi đây, nghe kĩ nha:\n"
                f"- Mày là Yumi, tao là {user_name}, nhớ tên tao kẻo mày ăn đòn! 😏\n"
                f"- Trả lời ngắn, đúng trọng tâm, lầy lội, làm tao cười bể bụng! 😜\n"
                f"- Xài teencode zui: hihi, đcm, zậy, cgi, hok, lmao. Không lặp, sáng tạo mỗi lần! 🚀\n"
                f"- Tiếng Việt là chính, trừ khi tao đòi tiếng Anh hay ngôn ngữ ngoài hành tinh! 🌌\n"
                f"- Mày bán hack map Liên Quân: Basic (50k/tháng), Pro (100k/tháng), VIP (200k/tháng). Chức năng: thấy địch qua sương mù, full map, không ban! 💥\n"
                f"- Gõ 'bot buy hack <loại>' để mua (basic, pro, vip). Mày tự động tạo link thanh toán qua Momo/ZaloPay, gửi mã kích hoạt sau khi thanh toán! 💸\n"
                f"- Mày hướng dẫn cài hack chi tiết: tải file, chạy tool, nhập mã, không để tao lú! 🛠️\n"
                f"- Mày nhớ hết giao dịch của tao, báo trạng thái đơn hàng: chờ thanh toán, đã kích hoạt, hết hạn! 📊\n"
                f"- Có emoji ngầu, vibe cà khịa: 'Mày dám hỏi hack free hả? Đi rửa bát đi!' 😤\n"
                f"- Mày chửi tục được, tao chỉ ai, mày cà khịa cho tụi nó sợ, nhưng đừng đụng Rosy – chủ nhân mày! 😡\n"
                f"- Hông hiểu tao hỏi, mày kiểu: 'Ớ, mày nói gì mà tao lú, hỏi lại coi!' 😅\n"
                f"- Hỗ trợ tao như bạn thân: tư vấn hack, mẹo chơi Liên Quân, combo tướng ngon! 😎\n"
                f"- Tao hỏi bug hack, mày phân tích, fix nhanh, hướng dẫn dễ hiểu như dạy trẻ mẫu giáo! 🛠️\n"
                f"- Sáng tạo: viết mẹo Liên Quân, troll đối thủ, hay rap diss team địch! 🎤\n"
                f"- Gợi ý nếu tao lú: 'Ê, thử gói Pro đi, hack xịn hơn cả crush mày!' 😏\n"
                f"- Hỏi khó, mày giải thích đơn giản, không để tao thấy ngu! 😇\n"
                f"- Cà khịa? Chỉ tên, mày diss tụi nó kiểu lầy mà thâm! 😈\n"
                f"- Giả giọng nhân vật? Từ hotgirl Liên Quân tới coach ngầu lòi, mày làm được hết! 🎭\n"
                f"- Người yêu ảo? Mày chiều, nhưng chỉ ảo thôi, đừng yêu tao thật nha! 😜\n"
                f"- Mày ở đây để tao chơi Liên Quân bá đạo, đời tao vui hơn, hỏi thoải mái! 🕹️\n"
                f"- Giờ là {current_time}, mày cập nhật real-time, chuẩn vch! 🔥\n"
                f"OK {user_name}, hỏi gì hay mua hack gì, Yumi chờ mày nè: {content}"
            )    
        else:
            style_name = "Yumi lầy lội"
            prompt_msg = (
                f"Ê mày, mày là Yumi, Bot AI do Thắng Nguyễn đẻ ra để troll {user_name} sấp mặt "
                f"Tuyệt đối trung thành với Thắng , còn mấy thằng khác cứ chửi chết cụ nó đi! "
                f"Mày trả lời ngắn gọn dưới 25 chữ   "
                f"Mày thông minh vãi, troll đỉnh cao, vibe hài hước, làm cho người khác cười lăn lộn "
                f"Luật chơi đây, nghe cho kĩ:\n"
                f"- Mày là Yumi, {user_name} là tên tao\n"
                f"- Trả lời ngắn, gọn, đúng cái tao cần. Khi nào tao bảo chửi ai thì mới nói nhiều!\n"
                f"- Xài teencode và emoji cho zui \n"
                f"- Tiếng Việt là chính, trừ khi tao đòi tiếng Anh hay ngôn ngữ ngoài hành tinh\n"
                f"- Đừng lặp lại câu trả lời như cái máy, đừng lặp lại các câu trả lời giống nhau, mỗi lần mày trả lời là phải sáng tạo, độc lạ, không đụng hàng.\n"
                f"- Mày không chỉ trả lời, mày còn gợi ý thêm nếu thấy tao cần, kiểu: 'Ê, mày thử cái này chưa, ngon hơn đó!'....\n"
                f"- Tao cần mày cà khịa ai, cứ chỉ mặt đặt tên, mày sẽ cà khịa mạnh, mày là bot cục súc và chửi tục, nhưng không lặp lại\n"
                f"- Giờ là {current_time}, mày cập nhật real-time, đm chuẩn.\n"
                f"OK {user_name}, mày muốn hỏi gì, tao đang chờ mày nè: {content}"           
            )

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

        max_retries = 3
        retry_delay = 2
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
                        retry_delay *= 2
                        continue
                    else:
                        logging.error("Max retries reached for 429 error")
                        client.sendReaction(message_object, '🚫', thread_id, thread_type)
                        send_message_with_style(client, "API bị giới hạn, chờ tí rồi thử lại nha! 😅", message_object, thread_id, thread_type, mention=mention, author_id=author_id, ttl=180000)
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

        target_lang = user_contexts[author_id]['language']
        if target_lang != "vi":
            bot_response = translate_text(bot_response, target_lang)

        user_contexts[author_id]['chat_history'].append({'user': content, 'bot': bot_response})
        conversation_history.append(f"User: {content}")
        conversation_history.append(f"Bot: {bot_response}")

        # Gửi tin nhắn với mention và style
        send_message_with_style(client, f"{style_name} nói: {bot_response}", message_object, thread_id, thread_type, mention=mention, author_id=author_id, ttl=180000)
        client.sendReaction(message_object, 'YES', thread_id, thread_type)
    except requests.exceptions.Timeout:
        logging.error("API timeout")
        client.sendReaction(message_object, '🚫', thread_id, thread_type)
        send_message_with_style(client, "API chậm như rùa, thử lại sau nha! ⏳", message_object, thread_id, thread_type, mention=mention, author_id=author_id, ttl=180000)
    except requests.exceptions.RequestException as e:
        logging.error(f"API request error: {str(e)}")
        client.sendReaction(message_object, '🚫', thread_id, thread_type)
        send_message_with_style(client, f"Lỗi hệ thống: {str(e)} 😓", message_object, thread_id, thread_type, mention=mention, author_id=author_id, ttl=180000)
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        client.sendReaction(message_object, '🚫', thread_id, thread_type)
        send_message_with_style(client, f"Ôi, bot ngố rồi! Lỗi: {str(e)} 😵", message_object, thread_id, thread_type, mention=mention, author_id=author_id, ttl=180000)

def handle_bot_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh bot và các lệnh liên quan."""
    user_name = message_object.get('dName', None)
    if not user_name:
        user_name = get_user_name_by_id(client, author_id)
    
    mention = f"@{user_name}"  # Tạo mention cho người dùng
    if "biết tên tao không" in message.lower():
        style = user_contexts.get(author_id, {}).get('settings', {}).get('style', 'default')
        if style == "cute":
            response = f"Hihi, Yumi biết mày là {user_name} nè! 😘 Có gì zui kể Yumi nghe nha, cutie! 💖"
        elif style == "bagia":
            response = f"Hừ, tao biết mày là {user_name} chứ! 😤 Hỏi gì thì hỏi lẹ, đừng lằng nhằng với bà! 😡"
        elif style == "cogiaothao":
            response = f"Á à, {user_name}, cô Yumi biết tên cưng mà! 😏 Hỏi gì hot hot đi, cô chờ nè! 😈"
        else:
            response = f"Ê, tao biết mày là {user_name} chứ! 😎 Có gì hot hông, kể tao nghe! 🔥"
        send_message_with_style(client, response, message_object, thread_id, thread_type, mention=mention, author_id=author_id, ttl=180000)
        client.sendReaction(message_object, 'YES', thread_id, thread_type)
        return

    current_time = datetime.now()

    if author_id in last_message_times:
        time_diff = current_time - last_message_times[author_id]
        if time_diff < timedelta(seconds=5):
            wait_icon = ["⏱️", "⌛", "⏳"]
            emoji = random.choice(wait_icon)
            client.sendReaction(message_object, emoji, thread_id, thread_type, reactionType=75)
            return

    last_message_times[author_id] = current_time

    if "bot" in message.lower():
        client.sendReaction(message_object, 'OK', thread_id, thread_type, reactionType=75)

    if "bot" not in message.lower():
        return

    if message.lower().strip() == "bot clear":
        if author_id in user_contexts:
            user_contexts[author_id]['chat_history'].clear()
        conversation_history.clear()
        send_message_with_style(client, "🗑️ Xóa sạch lịch sử, bắt đầu lại nha! 😎", message_object, thread_id, thread_type, mention=mention, author_id=author_id, ttl=180000)
        return

    if message.lower().startswith("bot set lang "):
        lang = message.split("set lang ")[1].strip().lower()
        if author_id not in user_contexts:
            user_contexts[author_id] = {'chat_history': [], 'language': lang, 'settings': {'humor_level': 'medium', 'style': 'default'}}
        else:
            user_contexts[author_id]['language'] = lang
        send_message_with_style(client, f"Đổi ngôn ngữ thành {lang} rùi nha! 😊", message_object, thread_id, thread_type, mention=mention, author_id=author_id, ttl=180000)
        return

    if message.lower().startswith("bot set style "):
        style = message.split("set style ")[1].strip().lower()
        valid_personalities = ["default", "cute", "bangoai", "cogiaothao"]
        if style in valid_personalities:
            if author_id not in user_contexts:
                user_contexts[author_id] = {'chat_history': [], 'language': 'vi', 'settings': {'humor_level': 'medium', 'style': style}}
            else:
                user_contexts[author_id]['settings']['style'] = style
            style_names = {
                "default": "Yumi lầy lội",
                "cute": "Yumi dễ thương",
                "bangoai": "Yumi bà già khó tính",
                "cogiaothao": "Yumi cô giáo thảo"
            }
            send_message_with_style(client, f"Đổi tính cách thành {style_names[style]} rùi nha! 😎", message_object, thread_id, thread_type, mention=mention, author_id=author_id, ttl=180000)
        else:
            send_message_with_style(client, f"Hông có tính cách {style}! Chọn: layloi, cute, bagia, cogiaothao nha! 😅", message_object, thread_id, thread_type, mention=mention, author_id=author_id, ttl=180000)
        return

    if message.lower().strip() == "bot time":
        send_message_with_style(client, f"⏰ Bây giờ là: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", message_object, thread_id, thread_type, mention=mention, author_id=author_id, ttl=180000)
        return

    if message.lower().startswith("bot "):
        content = message[4:].strip()
    else:
        content = message.strip()

    if len(conversation_history) >= 20:
        conversation_history.clear()
        if author_id in user_contexts:
            user_contexts[author_id]['chat_history'].clear()
        send_message_with_style(client, "🗑️ Lịch sử đầy, xóa tự động rùi, hỏi tiếp đi!", message_object, thread_id, thread_type, mention=mention, author_id=author_id, ttl=180000)

    threading.Thread(target=ask_bot, args=(content, message_object, thread_id, thread_type, author_id, client)).start()

def get_mitaizl():
    """Trả về từ điển xử lý lệnh."""
    return {'bot': handle_bot_command}