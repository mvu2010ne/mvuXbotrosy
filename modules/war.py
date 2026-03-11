from zlapi.models import *
import os
import time
import threading
import random
import json
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import requests
import glob
import colorsys
from datetime import datetime
import pytz
from config import ADMIN

WAR_TXT_DIR = "modules/func_war/war_txt/"
os.makedirs(WAR_TXT_DIR, exist_ok=True)

war_config = {
    'reo': {
        'file': os.path.join(WAR_TXT_DIR, "choc.txt"),
        'delay': 0.6
    },
    'spam': {
        'file': os.path.join(WAR_TXT_DIR, "noidung.txt"),
        'delay': 0.6
    },
    'poll': {
        'file': os.path.join(WAR_TXT_DIR, "noidung.txt"),
        'delay': 0.6
    },
    'todo': {
        'file': os.path.join(WAR_TXT_DIR, "noidung.txt"),
        'delay': 0.6
    }
}

sticker_file = os.path.join(WAR_TXT_DIR, "sticker.json")
is_reo_running = False
is_spam_running = False
is_polling = False
is_todo_active = False
BACKGROUND_PATH = "background/"
CACHE_PATH = "modules/cache/"
OUTPUT_IMAGE_PATH = os.path.join(CACHE_PATH, "war.png")
MAX_RUNTIME = 300  # Thời gian chạy tối đa (giây)

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Tự động thực hiện các chế độ war (réo tên, spam, poll, todo) với tin nhắn từ file văn bản.",
    'tính năng': [
        "🔍 Kiểm tra quyền hạn của người dùng trước khi thực hiện lệnh",
        "🔗 Hỗ trợ tag nhiều người để thực hiện war",
        "📝 Đọc nội dung từ file văn bản để gửi tin nhắn",
        "📩 Gửi tin nhắn, sticker, poll hoặc todo liên tục với khoảng thời gian tùy chỉnh",
        "⏰ Giới hạn thời gian chạy tối đa để tránh spam vô hạn",
        "🛑 Hỗ trợ dừng tất cả chế độ war khi có lệnh từ quản trị viên",
        "🖼️ Tạo ảnh menu với giao diện tùy chỉnh"
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh war.[reo/spam/poll/todo/random] [@người cần war] [số lần] để bắt đầu.",
        "📌 Ví dụ: war.reo @username1 @username2 5 để réo tên 5 lần.",
        "📌 Dùng war.stop để dừng tất cả chế độ war.",
        "⚙️ Cài đặt: war.[reo/spam/poll/todo] delay [thời gian] hoặc war.[reo/spam/poll/todo] set [tên file].",
        "📋 Liệt kê file: war.txt list",
        "🆕 Tạo file mới: war.newtxt [tên file] [nội dung]"
    ]
}

def send_message_with_style(client, text, thread_id, thread_type, color="#db342e"):
    """
    Gửi tin nhắn với định dạng màu sắc.
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
    client.send(Message(text=text, style=style), thread_id=thread_id, thread_type=thread_type, ttl=10000)

def get_dominant_color(image_path):
    try:
        if not os.path.exists(image_path):
            return (0, 0, 0)
        img = Image.open(image_path).convert("RGB").resize((150, 150), Image.Resampling.LANCZOS)
        pixels = img.getdata()
        if not pixels:
            return (0, 0, 0)
        r, g, b = 0, 0, 0
        for pixel in pixels:
            r += pixel[0]
            g += pixel[1]
            b += pixel[2]
        total = len(pixels)
        if total == 0:
            return (0, 0, 0)
        return (r // total, g // total, b // total)
    except Exception:
        return (0, 0, 0)

def get_contrasting_color(base_color, alpha=255):
    r, g, b = base_color[:3]
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return (255, 255, 255, alpha) if luminance < 0.5 else (0, 0, 0, alpha)

def random_contrast_color(base_color):
    r, g, b, _ = base_color
    box_luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    if box_luminance > 0.5:
        r = random.randint(0, 50)
        g = random.randint(0, 50)
        b = random.randint(0, 50)
    else:
        r = random.randint(200, 255)
        g = random.randint(200, 255)
        b = random.randint(200, 255)
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    s = min(1.0, s + 0.9)
    v = min(1.0, v + 0.7)
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    text_luminance = (0.299 * r + 0.587 * g + 0.114 * b)
    if abs(text_luminance - box_luminance) < 0.3:
        if box_luminance > 0.5:
            r, g, b = colorsys.hsv_to_rgb(h, s, min(1.0, v * 0.4))
        else:
            r, g, b = colorsys.hsv_to_rgb(h, s, min(1.0, v * 1.7))
    return (int(r * 255), int(g * 255), int(b * 255), 255)

def download_avatar(avatar_url, save_path=os.path.join(CACHE_PATH, "user_avatar.png")):
    if not avatar_url:
        return None
    try:
        resp = requests.get(avatar_url, stream=True, timeout=5)
        if resp.status_code == 200:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "wb") as f:
                for chunk in resp.iter_content(1024):
                    f.write(chunk)
            return save_path
    except Exception:
        return None

def generate_menu_image(client, author_id, thread_id, thread_type):
    images = glob.glob(os.path.join(BACKGROUND_PATH, "*.jpg")) + \
             glob.glob(os.path.join(BACKGROUND_PATH, "*.png")) + \
             glob.glob(os.path.join(BACKGROUND_PATH, "*.jpeg"))
    if not images:
        return None

    image_path = random.choice(images)
    try:
        size = (1920, 600)
        final_size = (1280, 380)
        bg_image = Image.open(image_path).convert("RGBA").resize(size, Image.Resampling.LANCZOS)
        bg_image = bg_image.filter(ImageFilter.GaussianBlur(radius=7))
        overlay = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        dominant_color = get_dominant_color(image_path)
        box_colors = [
            (255, 20, 147, 90), (128, 0, 128, 90), (0, 100, 0, 90),
            (0, 0, 139, 90), (184, 134, 11, 90), (138, 3, 3, 90), (0, 0, 0, 90)
        ]
        box_color = random.choice(box_colors)
        box_x1, box_y1 = 90, 60
        box_x2, box_y2 = size[0] - 90, size[1] - 60
        draw.rounded_rectangle([(box_x1, box_y1), (box_x2, box_y2)], radius=75, fill=box_color)

        font_arial_path = "arial unicode ms.otf"
        font_emoji_path = "emoji.ttf"
        try:
            font_text_large = ImageFont.truetype(font_arial_path, size=76)
            font_text_big = ImageFont.truetype(font_arial_path, size=68)
            font_text_small = ImageFont.truetype(font_arial_path, size=64)
            font_text_bot = ImageFont.truetype(font_arial_path, size=58)
            font_time = ImageFont.truetype(font_arial_path, size=56)
            font_icon = ImageFont.truetype(font_emoji_path, size=60)
            font_icon_large = ImageFont.truetype(font_emoji_path, size=175)
        except Exception:
            font_text_large = ImageFont.load_default(size=76)
            font_text_big = ImageFont.load_default(size=68)
            font_text_small = ImageFont.load_default(size=64)
            font_text_bot = ImageFont.load_default(size=58)
            font_time = ImageFont.load_default(size=56)
            font_icon = ImageFont.load_default(size=60)
            font_icon_large = ImageFont.load_default(size=175)

        def draw_text_with_shadow(draw, position, text, font, fill, shadow_color=(0, 0, 0, 250), shadow_offset=(2, 2)):
            x, y = position
            draw.text((x + shadow_offset[0], y + shadow_offset[1]), text, font=font, fill=shadow_color)
            draw.text((x, y), text, font=font, fill=fill)

        vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        vietnam_now = datetime.now(vietnam_tz)
        hour = vietnam_now.hour
        formatted_time = vietnam_now.strftime("%H:%M")
        time_icon = "🌤️" if 6 <= hour < 18 else "🌙"
        time_x = box_x2 - 250
        time_y = box_y1 + 10
        box_rgb = box_color[:3]
        box_luminance = (0.299 * box_rgb[0] + 0.587 * box_rgb[1] + 0.114 * box_rgb[2]) / 255
        last_lines_color = (255, 255, 255, 220) if box_luminance < 0.5 else (0, 0, 0, 220)
        time_color = last_lines_color

        if time_x >= 0 and time_y >= 0 and time_x < size[0] and time_y < size[1]:
            icon_x = time_x - 75
            icon_color = random_contrast_color(box_color)
            draw_text_with_shadow(draw, (icon_x, time_y - 8), time_icon, font_icon, icon_color)
            draw.text((time_x, time_y), f" {formatted_time}", font=font_time, fill=time_color)

        user_info = client.fetchUserInfo(author_id) if author_id else None
        user_name = "Unknown"
        if user_info and hasattr(user_info, 'changed_profiles') and author_id in user_info.changed_profiles:
            user = user_info.changed_profiles[author_id]
            user_name = getattr(user, 'name', None) or getattr(user, 'displayName', None) or f"ID_{author_id}"

        greeting_name = "Chủ Nhân" if str(author_id) in ADMIN else user_name
        emoji_colors = {
            "🎵": random_contrast_color(box_color),
            "😁": random_contrast_color(box_color),
            "🖤": random_contrast_color(box_color),
            "💞": random_contrast_color(box_color),
            "🤖": random_contrast_color(box_color),
            "💻": random_contrast_color(box_color),
            "📅": random_contrast_color(box_color),
            "🎧": random_contrast_color(box_color),
            "🌙": random_contrast_color(box_color),
            "🌤️": (200, 150, 50, 255)
        }

        text_lines = [
            f"Hi, {greeting_name}",
            f"💞 Chào mừng đến menu 🧨 war",
            f" ",
            "😁 Bot Sẵn Sàng Phục 🖤",
            f"🤖Bot: WarBot 💻Version: 1.0 📅Update 2025-07-04"
        ]

        color1 = random_contrast_color(box_color)
        color2 = random_contrast_color(box_color)
        while color1 == color2:
            color2 = random_contrast_color(box_color)
        text_colors = [color1, color2, last_lines_color, last_lines_color, last_lines_color]
        text_fonts = [font_text_large, font_text_big, font_text_bot, font_text_bot, font_text_small]
        line_spacing = 85
        start_y = box_y1 + 10

        avatar_url = user_info.changed_profiles[author_id].avatar if user_info and hasattr(user_info, 'changed_profiles') and author_id in user_info.changed_profiles else None
        avatar_path = download_avatar(avatar_url)
        if avatar_path and os.path.exists(avatar_path):
            avatar_size = 200
            avatar_img = Image.open(avatar_path).convert("RGBA").resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
            mask = Image.new("L", (avatar_size, avatar_size), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, Bosef, avatar_size, avatar_size), fill=255)
            border_size = avatar_size + 10
            rainbow_border = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
            draw_border = ImageDraw.Draw(rainbow_border)
            steps = 360
            for i in range(steps):
                h = i / steps
                r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
                draw_border.arc([(0, 0), (border_size-1, border_size-1)], start=i, end=i + (360 / steps), fill=(int(r * 255), int(g * 255), int(b * 255), 255), width=5)
            avatar_y = (box_y1 + box_y2 - avatar_size) // 2
            overlay.paste(rainbow_border, (box_x1 + 40, avatar_y), rainbow_border)
            overlay.paste(avatar_img, (box_x1 + 45, avatar_y + 5), mask)
        else:
            draw.text((box_x1 + 60, (box_y1 + box_y2) // 2 - 140), "🐳", font=font_icon, fill=(0, 139, 139, 255))

        current_line_idx = 0
        for i, line in enumerate(text_lines):
            if not line:
                current_line_idx += 1
                continue
            parts = []
            current_part = ""
            for char in line:
                if ord(char) > 0xFFFF:
                    if current_part:
                        parts.append(current_part)
                        current_part = ""
                    parts.append(char)
                else:
                    current_part += char
            if current_part:
                parts.append(current_part)

            total_width = 0
            part_widths = []
            current_font = font_text_bot if i == 4 else text_fonts[i]
            for part in parts:
                font_to_use = font_icon if any(ord(c) > 0xFFFF for c in part) else current_font
                width = draw.textbbox((0, 0), part, font=font_to_use)[2]
                part_widths.append(width)
                total_width += width

            max_width = box_x2 - box_x1 - 300
            if total_width > max_width:
                font_size = int(current_font.getbbox("A")[3] * max_width / total_width * 0.9)
                if font_size < 60:
                    font_size = 60
                current_font = ImageFont.truetype(font_arial_path, size=font_size) if os.path.exists(font_arial_path) else ImageFont.load_default(size=font_size)
                total_width = 0
                part_widths = []
                for part in parts:
                    font_to_use = font_icon if any(ord(c) > 0xFFFF for c in part) else current_font
                    width = draw.textbbox((0, 0), part, font=font_to_use)[2]
                    part_widths.append(width)
                    total_width += width

            text_x = (box_x1 + box_x2 - total_width) // 2
            text_y = start_y + current_line_idx * line_spacing + (current_font.getbbox("A")[3] // 2)

            current_x = text_x
            for part, width in zip(parts, part_widths):
                if any(ord(c) > 0xFFFF for c in part):
                    emoji_color = emoji_colors.get(part, random_contrast_color(box_color))
                    draw_text_with_shadow(draw, (current_x, text_y), part, font_icon, emoji_color)
                else:
                    if i < 2:
                        draw_text_with_shadow(draw, (current_x, text_y), part, current_font, text_colors[i])
                    else:
                        draw.text((current_x, text_y), part, font=current_font, fill=text_colors[i])
                current_x += width
            current_line_idx += 1

        right_icons = ["🧨"]
        right_icon = random.choice(right_icons)
        icon_right_x = box_x2 - 225
        icon_right_y = (box_y1 + box_y2 - 180) // 2
        draw_text_with_shadow(draw, (icon_right_x, icon_right_y), right_icon, font_icon_large, emoji_colors.get(right_icon, (80, 80, 80, 255)))

        final_image = Image.alpha_composite(bg_image, overlay)
        final_image = final_image.resize(final_size, Image.Resampling.LANCZOS)
        os.makedirs(os.path.dirname(OUTPUT_IMAGE_PATH), exist_ok=True)
        final_image.save(OUTPUT_IMAGE_PATH, "PNG", quality=95)
        return OUTPUT_IMAGE_PATH
    except Exception:
        return None

def set_war_delay(war_type, delay_value):
    try:
        delay = float(delay_value)
        if delay >= 0:
            war_config[war_type]['delay'] = delay
            return True
    except (ValueError, KeyError):
        return False

def set_war_file(war_type, filename):
    if not filename.endswith('.txt'):
        filename += '.txt'
    filepath = os.path.join(WAR_TXT_DIR, filename)
    if os.path.exists(filepath):
        war_config[war_type]['file'] = filepath
        return True
    return False

def list_text_files():
    try:
        return [f for f in os.listdir(WAR_TXT_DIR) if f.endswith('.txt')]
    except FileNotFoundError:
        return []

def create_new_txt(filename, content):
    try:
        if not filename.endswith('.txt'):
            filename += '.txt'
        filepath = os.path.join(WAR_TXT_DIR, filename)
        if os.path.exists(filepath):
            return False, "File already exists!"
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(content)
        return True, f"File {filename} created successfully!"
    except Exception as e:
        return False, f"Error creating file: {str(e)}"

def stop_all_wars(client, message_object, thread_id, thread_type):
    global is_reo_running, is_spam_running, is_polling, is_todo_active
    is_reo_running = is_spam_running = is_polling = is_todo_active = False
    send_message_with_style(client, "⚠️ Đã dừng tất cả chế độ war!", thread_id, thread_type)

def handle_war_command(message, message_object, thread_id, thread_type, author_id, client):
    global is_reo_running, is_spam_running, is_polling, is_todo_active

    if author_id not in ADMIN:
        send_message_with_style(client, "⭕ Bạn không có quyền thực hiện lệnh này!", thread_id, thread_type)
        return

    command_parts = message.split()
    if len(command_parts) < 1 or not command_parts[0].lower().startswith("war."):
        send_message_with_style(client, "Sai cú pháp! Dùng: war.[reo/spam/poll/todo/random] [@người cần war] [số lần] hoặc war.stop", thread_id, thread_type)
        return

    action = command_parts[0].lower().split('.')[1] if '.' in command_parts[0] else None

    if action == "stop":
        if not any([is_reo_running, is_spam_running, is_polling, is_todo_active]):
            send_message_with_style(client, "⚠️ Không có chế độ war nào đang chạy!", thread_id, thread_type)
        else:
            stop_all_wars(client, message_object, thread_id, thread_type)
        return

    if action == "txt" and len(command_parts) > 1 and command_parts[1].lower() == "list":
        files = list_text_files()
        response = "📋 Danh sách file txt có sẵn:\n" + "\n".join(f"• {f}" for f in files) if files else f"❌ Không có file txt nào trong thư mục {WAR_TXT_DIR}!"
        send_message_with_style(client, response, thread_id, thread_type)
        return

    if action in ["reo", "spam", "poll", "todo"] and len(command_parts) > 1 and command_parts[1].lower() in ["delay", "set"]:
        if len(command_parts) < 3:
            send_message_with_style(client, "❌ Thiếu tham số! Dùng: war.[reo/spam/poll/todo] [delay/set] [giá trị]", thread_id, thread_type)
            return
        if command_parts[1].lower() == "delay":
            if set_war_delay(action, command_parts[2]):
                send_message_with_style(client, f"✅ Đã đặt delay {action} thành {command_parts[2]} giây", thread_id, thread_type)
            else:
                send_message_with_style(client, "❌ Thời gian delay không hợp lệ!", thread_id, thread_type)
        else:
            if set_war_file(action, command_parts[2]):
                send_message_with_style(client, f"✅ Đã đặt file {action} thành {os.path.basename(war_config[action]['file'])}", thread_id, thread_type)
            else:
                send_message_with_style(client, f"❌ File {command_parts[2]}.txt không tồn tại!", thread_id, thread_type)
        return

    if action == "newtxt":
        if len(command_parts) < 3:
            send_message_with_style(client, "❌ Thiếu tên file hoặc nội dung!\nVí dụ: war.newtxt tênfile nội dung", thread_id, thread_type)
            return
        filename = command_parts[1]
        content = ' '.join(command_parts[2:])
        success, message = create_new_txt(filename, content)
        send_message_with_style(client, f"✅ {message}" if success else f"❌ {message}", thread_id, thread_type)
        return

    if thread_type != ThreadType.GROUP:
        send_message_with_style(client, "❌ Chỉ dùng trong nhóm!", thread_id, thread_type)
        return

    if not message_object.mentions:
        send_message_with_style(client, "❌ Vui lòng tag ít nhất một người để war!", thread_id, thread_type)
        return

    count = -1
    if len(command_parts) > 1 and command_parts[1].isdigit():
        count = int(command_parts[1])
        if count < 0:
            send_message_with_style(client, "❌ Số lần phải ≥ 0!", thread_id, thread_type)
            return

    tagged_users = [mention['uid'] for mention in message_object.mentions]
    tagged_count = len(tagged_users)

    try:
        with open(war_config[action]['file'], "r", encoding="utf-8") as file:
            content = file.readlines()
    except FileNotFoundError:
        send_message_with_style(client, f"❌ Không tìm thấy file {war_config[action]['file']}!", thread_id, thread_type)
        return
    except KeyError:
        send_message_with_style(client, "❌ Loại war không hợp lệ!", thread_id, thread_type)
        return

    if not content:
        send_message_with_style(client, f"❌ File {war_config[action]['file']} trống!", thread_id, thread_type)
        return

    send_message_with_style(
        client,
        f"🚀 Bắt đầu {action} {tagged_count} người với {len(content)} tin nhắn!\n"
        f"Thời gian chạy tối đa: {MAX_RUNTIME} giây.",
        thread_id,
        thread_type
    )

    def war_loop():
        global is_reo_running, is_spam_running, is_polling, is_todo_active
        start_time = time.time()
        executed = 0

        if action == "reo":
            is_reo_running = True
            while is_reo_running and (time.time() - start_time) < MAX_RUNTIME and (count == -1 or executed < count):
                for line in content:
                    if not is_reo_running or (time.time() - start_time) >= MAX_RUNTIME or (count != -1 and executed >= count):
                        break
                    for user_id in tagged_users:
                        mention = Mention(user_id, length=0, offset=0)
                        client.send(Message(text=f" {line.strip()}", mention=mention), thread_id, thread_type, ttl=5000)
                    executed += 1
                    time.sleep(war_config['reo']['delay'])
            is_reo_running = False

        elif action == "spam":
            try:
                with open(sticker_file, 'r', encoding='utf-8') as file:
                    stickers = json.load(file)
            except:
                send_message_with_style(client, "❗️ Không thể đọc file sticker.json!", thread_id, thread_type)
                return
            is_spam_running = True
            while is_spam_running and (time.time() - start_time) < MAX_RUNTIME and (count == -1 or executed < count):
                for line in content:
                    if not is_spam_running or (time.time() - start_time) >= MAX_RUNTIME or (count != -1 and executed >= count):
                        break
                    for user_id in tagged_users:
                        mention = Mention(user_id, length=0, offset=0)
                        client.send(Message(text=f" {line.strip()}", mention=mention), thread_id, thread_type, ttl=5000)
                        sticker = random.choice(stickers)
                        client.sendSticker(
                            stickerType=sticker['stickerType'],
                            stickerId=sticker['stickerId'],
                            cateId=sticker['cateId'],
                            thread_id=thread_id,
                            thread_type=thread_type
                        )
                    executed += 1
                    time.sleep(war_config['spam']['delay'])
            is_spam_running = False

        elif action == "poll":
            is_polling = True
            while is_polling and (time.time() - start_time) < MAX_RUNTIME and (count == -1 or executed < count):
                for line in content:
                    if not is_polling or (time.time() - start_time) >= MAX_RUNTIME or (count != -1 and executed >= count):
                        break
                    for user_id in tagged_users:
                        try:
                            user_info = client.fetchUserInfo(user_id)
                            username = user_info['changed_profiles'][user_id].get('zaloName', 'không xác định')
                            client.createPoll(question=f"{username} {line.strip()}", options=["Trùm war."], groupId=thread_id)
                        except Exception:
                            send_message_with_style(client, "❌ Lỗi khi tạo poll!", thread_id, thread_type)
                            break
                    executed += 1
                    time.sleep(war_config['poll']['delay'])
            is_polling = False

        elif action == "todo":
            is_todo_active = True
            while is_todo_active and (time.time() - start_time) < MAX_RUNTIME and (count == -1 or executed < count):
                for line in content:
                    if not is_todo_active or (time.time() - start_time) >= MAX_RUNTIME or (count != -1 and executed >= count):
                        break
                    for user_id in tagged_users:
                        client.sendToDo(message_object, line.strip(), [user_id], thread_id, thread_type, -1, "Nhiệm vụ tự động")
                    executed += 1
                    time.sleep(war_config['todo']['delay'])
            is_todo_active = False

        elif action == "random":
            war_type = random.choice(['reo', 'spam', 'poll', 'todo'])
            send_message_with_style(
                client,
                f"🎲 Đã chọn ngẫu nhiên: {war_type} - Delay: {war_config[war_type]['delay']}s - File: {os.path.basename(war_config[war_type]['file'])} - Số lần: {count if count >= 0 else '∞'}",
                thread_id,
                thread_type
            )
            if war_type == "reo":
                is_reo_running = True
                while is_reo_running and (time.time() - start_time) < MAX_RUNTIME and (count == -1 or executed < count):
                    for line in content:
                        if not is_reo_running or (time.time() - start_time) >= MAX_RUNTIME or (count != -1 and executed >= count):
                            break
                        for user_id in tagged_users:
                            mention = Mention(user_id, length=0, offset=0)
                            client.send(Message(text=f" {line.strip()}", mention=mention), thread_id, thread_type, ttl=5000)
                        executed += 1
                        time.sleep(war_config['reo']['delay'])
                is_reo_running = False
            elif war_type == "spam":
                try:
                    with open(sticker_file, 'r', encoding='utf-8') as file:
                        stickers = json.load(file)
                except:
                    send_message_with_style(client, "❗️ Không thể đọc file sticker.json!", thread_id, thread_type)
                    return
                is_spam_running = True
                while is_spam_running and (time.time() - start_time) < MAX_RUNTIME and (count == -1 or executed < count):
                    for line in content:
                        if not is_spam_running or (time.time() - start_time) >= MAX_RUNTIME or (count != -1 and executed >= count):
                            break
                        for user_id in tagged_users:
                            mention = Mention(user_id, length=0, offset=0)
                            client.send(Message(text=f" {line.strip()}", mention=mention), thread_id, thread_type, ttl=5000)
                            sticker = random.choice(stickers)
                            client.sendSticker(
                                stickerType=sticker['stickerType'],
                                stickerId=sticker['stickerId'],
                                cateId=sticker['cateId'],
                                thread_id=thread_id,
                                thread_type=thread_type
                            )
                        executed += 1
                        time.sleep(war_config['spam']['delay'])
                is_spam_running = False
            elif war_type == "poll":
                is_polling = True
                while is_polling and (time.time() - start_time) < MAX_RUNTIME and (count == -1 or executed < count):
                    for line in content:
                        if not is_polling or (time.time() - start_time) >= MAX_RUNTIME or (count != -1 and executed >= count):
                            break
                        for user_id in tagged_users:
                            try:
                                user_info = client.fetchUserInfo(user_id)
                                username = user_info['changed_profiles'][user_id].get('zaloName', 'không xác định')
                                client.createPoll(question=f"{username} {line.strip()}", options=["Trùm war."], groupId=thread_id)
                            except Exception:
                                send_message_with_style(client, "❌ Lỗi khi tạo poll!", thread_id, thread_type)
                                break
                        executed += 1
                        time.sleep(war_config['poll']['delay'])
                is_polling = False
            elif war_type == "todo":
                is_todo_active = True
                while is_todo_active and (time.time() - start_time) < MAX_RUNTIME and (count == -1 or executed < count):
                    for line in content:
                        if not is_todo_active or (time.time() - start_time) >= MAX_RUNTIME or (count != -1 and executed >= count):
                            break
                        for user_id in tagged_users:
                            client.sendToDo(message_object, line.strip(), [user_id], thread_id, thread_type, -1, "Nhiệm vụ tự động")
                        executed += 1
                        time.sleep(war_config['todo']['delay'])
                is_todo_active = False

        if (time.time() - start_time) >= MAX_RUNTIME:
            send_message_with_style(client, "⏰ Hết thời gian war!", thread_id, thread_type)

    threading.Thread(target=war_loop).start()

def get_mitaizl():
    return {
        'war.reo': handle_war_command,
        'war.spam': handle_war_command,
        'war.poll': handle_war_command,
        'war.todo': handle_war_command,
        'war.random': handle_war_command,
        'war.stop': handle_war_command,
        'war.txt': handle_war_command,
        'war.newtxt': handle_war_command
    }