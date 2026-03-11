from zlapi import ZaloAPI
from zlapi.models import *
import time
from concurrent.futures import ThreadPoolExecutor
import threading
from deep_translator import GoogleTranslator
from googletrans import Translator
import asyncio

des = {
    'tác giả': "Minh Vũ Shinn Cte FIX",
    'mô tả': "🔍 Dịch văn bản sang nhiều ngôn ngữ khác nhau.",
    'tính năng': [
        "🌐 Hỗ trợ dịch văn bản sang hơn 80 ngôn ngữ từ Google Translate.",
        "📥 Dịch trực tiếp từ tin nhắn nhập hoặc tin nhắn được trích dẫn.",
        "🔎 Tự động phát hiện ngôn ngữ nguồn của văn bản.",
        "⚠️ Cung cấp danh sách ngôn ngữ hỗ trợ và thông báo lỗi chi tiết."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh dich <mã_ngôn_ngữ> <văn_bản> để dịch văn bản.",
        "📩 Hoặc trả lời một tin nhắn và gửi dich <mã_ngôn_ngữ> để dịch nội dung trích dẫn.",
        "📌 Ví dụ: dich en Xin chào hoặc dich en (khi trả lời tin nhắn).",
        "✅ Nhận kết quả dịch và thông tin ngôn ngữ ngay lập tức."
    ]
}

SUPPORTED_LANGUAGES = {
    "af": "Tiếng Afrikaans",
    "ar": "Tiếng Ả Rập",
    "az": "Tiếng Azerbaijan",
    "be": "Tiếng Belarus",
    "bg": "Tiếng Bulgaria",
    "bn": "Tiếng Bengali",
    "bs": "Tiếng Bosnia",
    "ca": "Tiếng Catalan",
    "cs": "Tiếng Séc",
    "cy": "Tiếng Xứ Wales",
    "da": "Tiếng Đan Mạch",
    "de": "Tiếng Đức",
    "el": "Tiếng Hy Lạp",
    "en": "Tiếng Anh",
    "eo": "Tiếng Esperanto",
    "es": "Tiếng Tây Ban Nha",
    "et": "Tiếng Estonia",
    "fa": "Tiếng Ba Tư",
    "fi": "Tiếng Phần Lan",
    "fr": "Tiếng Pháp",
    "ga": "Tiếng Ireland",
    "gl": "Tiếng Galicia",
    "gu": "Tiếng Gujarati",
    "hi": "Tiếng Hindi",
    "hr": "Tiếng Croatia",
    "ht": "Tiếng Haiti Creole",
    "hu": "Tiếng Hungary",
    "hy": "Tiếng Armenia",
    "id": "Tiếng Indonesia",
    "is": "Tiếng Iceland",
    "it": "Tiếng Ý",
    "ja": "Tiếng Nhật",
    "ka": "Tiếng Georgia",
    "kk": "Tiếng Kazakh",
    "km": "Tiếng Khmer",
    "kn": "Tiếng Kannada",
    "ko": "Tiếng Hàn",
    "ky": "Tiếng Kyrgyz",
    "lb": "Tiếng Luxembourg",
    "lo": "Tiếng Lào",
    "lt": "Tiếng Lithuania",
    "lv": "Tiếng Latvia",
    "mg": "Tiếng Malagasy",
    "mk": "Tiếng Macedonia",
    "ml": "Tiếng Malayalam",
    "mn": "Tiếng Mông Cổ",
    "mr": "Tiếng Marathi",
    "ms": "Tiếng Mã Lai",
    "mt": "Tiếng Malta",
    "ne": "Tiếng Nepali",
    "nl": "Tiếng Hà Lan",
    "no": "Tiếng Na Uy",
    "pa": "Tiếng Punjabi",
    "pl": "Tiếng Ba Lan",
    "pt": "Tiếng Bồ Đào Nha",
    "ro": "Tiếng Romania",
    "ru": "Tiếng Nga",
    "sk": "Tiếng Slovak",
    "sl": "Tiếng Slovenia",
    "sq": "Tiếng Albania",
    "sr": "Tiếng Serbia",
    "sv": "Tiếng Thụy Điển",
    "sw": "Tiếng Swahili",
    "ta": "Tiếng Tamil",
    "te": "Tiếng Telugu",
    "th": "Tiếng Thái",
    "tl": "Tiếng Tagalog",
    "tr": "Tiếng Thổ Nhĩ Kỳ",
    "uk": "Tiếng Ukraina",
    "ur": "Tiếng Urdu",
    "uz": "Tiếng Uzbekistan",
    "vi": "Tiếng Việt",
    "zh-cn": "Tiếng Trung (Giản thể)",
    "zh-tw": "Tiếng Trung (Phồn thể)",
    "hk": "Tiếng Hồng Kông"
}

ALIAS_LANGUAGES = {
    "tw": "zh-cn",
    "hk": "zh-tw"
}

def get_supported_languages_message():
    languages_list = [f"{code}: {name}" for code, name in SUPPORTED_LANGUAGES.items()]
    for alias, real in ALIAS_LANGUAGES.items():
        if real in SUPPORTED_LANGUAGES:
            languages_list.append(f"{alias}: {SUPPORTED_LANGUAGES[real]}")
    languages_str = "\n".join(languages_list)
    message = (
        "Cú pháp sử dụng:\n"
        "  dich <ngôn ngữ cuối> <văn bản>\n"
        "Hoặc khi reply vào tin nhắn của người khác:\n"
        "  dich <ngôn ngữ cuối>\n\n"
        "Ví dụ:\n"
        "  dich en Xin chào, bạn khỏe không?\n"
        "  (hoặc reply tin nhắn của người khác và soạn: dich en)\n\n"
        "Danh sách ngôn ngữ được hỗ trợ:\n"
        f"{languages_str}"
    )
    return message

def handle_translate_command(message, message_object, thread_id, thread_type, author_id, client):
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    
    message_text = message_object.get('content', '').strip()
    parts = message_text.split(maxsplit=2)
    
    reply_message = None
    if hasattr(message_object, 'quote'):
        reply_message = message_object.quote
    elif 'quote' in message_object:
        reply_message = message_object.get('quote')
    
    if not reply_message and len(parts) < 3:
        help_message = get_supported_languages_message()
        client.replyMessage(Message(text=help_message), message_object, thread_id, thread_type, ttl=20000)
        return
    if len(parts) < 2:
        help_message = get_supported_languages_message()
        client.replyMessage(Message(text=help_message), message_object, thread_id, thread_type, ttl=20000)
        return

    raw_target = parts[1].strip()
    target_code = ALIAS_LANGUAGES.get(raw_target.lower(), raw_target)
    target_lower = target_code.lower()
    
    if target_lower not in SUPPORTED_LANGUAGES:
        client.replyMessage(
            Message(text=f"Ngôn ngữ '{raw_target}' không được hỗ trợ.\n" + get_supported_languages_message()),
            message_object, thread_id, thread_type
        )
        return

    text_to_translate = ""
    if reply_message:
        try:
            text_to_translate = reply_message.get('msg', '').strip()
        except AttributeError:
            text_to_translate = getattr(reply_message, 'msg', '').strip()
        if not text_to_translate:
            try:
                text_to_translate = reply_message.get('content', '').strip()
            except AttributeError:
                text_to_translate = getattr(reply_message, 'content', '').strip()
        if not text_to_translate:
            if len(parts) < 3:
                help_message = get_supported_languages_message()
                client.replyMessage(Message(text=help_message), message_object, thread_id, thread_type)
                return
            else:
                text_to_translate = parts[2]
    else:
        text_to_translate = parts[2]

    if not text_to_translate:
        client.replyMessage(Message(text="Không tìm thấy nội dung để dịch."), message_object, thread_id, thread_type)
        return

    try:
        # Sửa lỗi: Gọi detect() trực tiếp mà không dùng asyncio.run()
        translator_detect = Translator()
        detected = translator_detect.detect(text_to_translate)  # Gọi đồng bộ
        source_lang = detected.lang
        source_lang_name = SUPPORTED_LANGUAGES.get(source_lang, source_lang)
        
        if target_lower == "zh-cn":
            translator_target = "zh-CN"
        elif target_lower == "zh-tw" or target_lower == "hk":
            translator_target = "zh-TW"
        else:
            translator_target = target_lower

        translated = GoogleTranslator(source='auto', target=translator_target).translate(text_to_translate)
        target_lang_name = SUPPORTED_LANGUAGES.get(target_lower, raw_target)
        
        message1 = f"Đã dịch từ {source_lang_name} sang {target_lang_name}"
        message2 = translated

        client.replyMessage(Message(text=message1), message_object, thread_id, thread_type, ttl=10000)
        client.replyMessage(Message(text=message2), message_object, thread_id, thread_type)
    except Exception as e:
        client.replyMessage(Message(text=f"Lỗi khi dịch: {str(e)}"), message_object, thread_id, thread_type, ttl=180000)

def get_mitaizl():
    return {
        'dich': handle_translate_command
    }