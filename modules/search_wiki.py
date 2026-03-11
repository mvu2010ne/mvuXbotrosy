import re
import time
import wikipedia
import requests
import tempfile
import os
import difflib
import asyncio
from aiohttp import ClientSession
from zlapi.models import Message, MultiMsgStyle, MessageStyle
from config import PREFIX

des = {
    'tác giả': "Minh Vũ Shinn Cte ",
    'mô tả': "🔍 Tìm kiếm thông tin nâng cao từ Wikipedia.",
    'tính năng': [
        "📋 Tìm kiếm với tự động sửa lỗi chính tả và gợi ý chính xác.",
        "🌐 Hỗ trợ nhiều ngôn ngữ (vi, en, fr, es) và tóm tắt thông minh.",
        "📸 Tải ảnh bìa hoặc ảnh liên quan từ trang Wikipedia.",
        "📄 Định dạng đẹp với tóm tắt, infobox, mục chính và liên kết.",
        "⚡ Tối ưu bằng xử lý bất đồng bộ."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh wiki [ngôn ngữ] <từ khóa> để tìm kiếm (mặc định: vi).",
        "📌 Ví dụ: wiki vi Donald Trump hoặc wiki en Elon Musk.",
        "✅ Nhận thông tin chi tiết kèm ảnh (nếu có) trong tin nhắn."
    ]
}

MAX_MESSAGE_LENGTH = 1024
SUPPORTED_LANGS = {"vi": "Tiếng Việt", "en": "Tiếng Anh", "fr": "Tiếng Pháp", "es": "Tiếng Tây Ban Nha"}

def set_wikipedia_language(lang):
    if lang in SUPPORTED_LANGS:
        wikipedia.set_lang(lang)
        return lang
    wikipedia.set_lang("vi")
    return "vi"

async def fetch_cover_image(title, lang):
    async with ClientSession() as session:
        endpoint = f"https://{lang}.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "pageimages",
            "pithumbsize": 1200
        }
        async with session.get(endpoint, params=params) as response:
            data = await response.json()
            pages = data.get("query", {}).get("pages", {})
            for page_id, page_data in pages.items():
                if "thumbnail" in page_data:
                    return page_data["thumbnail"]["source"]
    return None

def extract_main_sections(content):
    return re.findall(r'(?:\n|^)==\s*([^=].*?)\s*==', content)[:5]

def extract_infobox(page):
    try:
        content = page.content
        infobox_match = re.search(r'{{Infobox.*?(?:{{.*}}|\n\s*\|.*?)+?\n}}', content, re.DOTALL)
        if infobox_match:
            fields = {}
            for line in infobox_match.group(0).split("\n"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip("| ").strip()
                    value = re.sub(r'\[\[|\]\]', '', value.strip())
                    if key and value:
                        fields[key] = value
            return fields
    except Exception:
        return {}
    return {}

def split_message_text(text, max_length):
    if len(text) <= max_length:
        return [text]
    lines = text.split("\n")
    chunks = []
    current_chunk = ""
    for line in lines:
        candidate = f"{current_chunk}\n{line}" if current_chunk else line
        if len(candidate) > max_length:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                while len(line) > max_length:
                    chunks.append(line[:max_length])
                    line = line[max_length:]
                current_chunk = line
        else:
            current_chunk = candidate
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

def create_style(text, color="#15a85f", size=16, bold=False):
    styles = [
        MessageStyle(offset=0, length=len(text), style="color", color=color, auto_format=False),
        MessageStyle(offset=0, length=len(text), style="font", size=size, auto_format=False),
    ]
    if bold:
        styles.append(MessageStyle(offset=0, length=len(text), style="bold", auto_format=False))
    return MultiMsgStyle(styles)

async def handle_wikipedia_search_command(message, message_object, thread_id, thread_type, author_id, client):
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
    
    text = message.split()
    if len(text) < 2:
        error_msg = "Cú pháp: wiki [ngôn ngữ] <từ khoá>\nVí dụ: wiki vi Donald Trump"
        client.sendMessage(Message(text=error_msg, style=create_style(error_msg, "#ff4444")), thread_id, thread_type, ttl=60000)
        return

    lang = "vi"
    query_start = 1
    if text[1] in SUPPORTED_LANGS:
        lang = text[1]
        query_start = 2
    query = " ".join(text[query_start:])
    set_wikipedia_language(lang)

    try:
        page = wikipedia.page(query, auto_suggest=False)
    except wikipedia.exceptions.PageError:
        # Tìm gợi ý và sửa lỗi chính tả
        suggestions = wikipedia.search(query, results=10)
        if not suggestions:
            msg = f"❌ Không tìm thấy '{query}'.\nKhông có gợi ý nào phù hợp."
            client.sendMessage(Message(text=msg, style=create_style(msg, "#ff4444")), thread_id, thread_type)
            return
        
        # Tìm từ khóa gần đúng nhất bằng difflib
        closest_match = difflib.get_close_matches(query, suggestions, n=1, cutoff=0.6)
        if closest_match:
            corrected_query = closest_match[0]
            try:
                page = wikipedia.page(corrected_query)
                msg = f"🔍 Không tìm thấy '{query}', đã tự động sửa thành '{corrected_query}':"
                client.sendMessage(Message(text=msg, style=create_style(msg, "#ffaa00")), thread_id, thread_type)
            except Exception:
                msg = f"❌ Không tìm thấy '{query}'.\nGợi ý:\n" + "\n".join([f"• {s}" for s in suggestions[:5]]) + "\nHãy thử lại!"
                client.sendMessage(Message(text=msg, style=create_style(msg, "#ff4444")), thread_id, thread_type)
                return
        else:
            msg = f"❌ Không tìm thấy '{query}'.\nGợi ý:\n" + "\n".join([f"• {s}" for s in suggestions[:5]]) + "\nHãy thử lại!"
            client.sendMessage(Message(text=msg, style=create_style(msg, "#ff4444")), thread_id, thread_type)
            return
    except wikipedia.exceptions.DisambiguationError as e:
        suggestions = e.options[:5]
        msg = f"🔍 '{query}' có nhiều kết quả:\n" + "\n".join([f"• {s}" for s in suggestions]) + "\nHãy thử cụ thể hơn!"
        client.sendMessage(Message(text=msg, style=create_style(msg, "#ffaa00")), thread_id, thread_type)
        return
    except Exception as e:
        client.sendMessage(Message(text=f"⚠ Lỗi: {str(e)}", style=create_style(str(e), "#ff4444")), thread_id, thread_type)
        return

    # Lấy thông tin trang
    summary_sentences = page.summary.split(". ")
    summary = ". ".join(summary_sentences[:3]) + "."
    main_sections = extract_main_sections(page.content)
    infobox = extract_infobox(page)
    page_url = page.url
    cover_image = await fetch_cover_image(page.title, lang)
    representative_images = [cover_image] if cover_image else [img for img in page.images if img.lower().endswith(('.jpg', '.jpeg', '.png')) and "logo" not in img.lower()][:2]

    # Xây dựng nội dung
    message_lines = [f"📖 Thông tin về {page.title} ({SUPPORTED_LANGS[lang]}):"]
    message_lines.append(f"✨ Tóm tắt: {summary}")
    if infobox:
        message_lines.append("\n📊 Thông tin chi tiết:")
        for key, value in list(infobox.items())[:5]:
            message_lines.append(f"• {key}: {value}")
    if main_sections:
        message_lines.append("\n📑 Các mục chính:")
        for section in main_sections:
            message_lines.append(f"➤ {section}")
    message_lines.append(f"\n🔗 Xem thêm: {page_url}")
    full_message = "\n".join(message_lines)
    message_chunks = split_message_text(full_message, MAX_MESSAGE_LENGTH)

    # Gửi tin nhắn kèm ảnh
    for i, chunk in enumerate(message_chunks):
        if i == 0 and representative_images:
            for img_url in representative_images:
                try:
                    async with ClientSession() as session:
                        async with session.get(img_url) as resp:
                            if resp.status == 200:
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                                    tmp_file.write(await resp.read())
                                    tmp_file_path = tmp_file.name
                                client.sendLocalImage(
                                    tmp_file_path,
                                    message=Message(text=chunk, style=create_style(chunk, "#15a85f", 16, bold=True)),
                                    thread_id=thread_id,
                                    thread_type=thread_type,
                                    width=1200,
                                    height=1600,
                                    ttl=60000
                                )
                                os.remove(tmp_file_path)
                                break
                except Exception:
                    client.sendMessage(Message(text=chunk, style=create_style(chunk)), thread_id, thread_type)
        else:
            await asyncio.sleep(2)
            client.sendMessage(Message(text=chunk, style=create_style(chunk)), thread_id, thread_type)

def get_mitaizl():
    return {
        'wiki': lambda *args: asyncio.run(handle_wikipedia_search_command(*args))
    }