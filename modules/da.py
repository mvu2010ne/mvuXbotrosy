from zlapi import ZaloAPI, ZaloAPIException
from zlapi.models import *
from zlapi.models import Message, Mention
from threading import Thread
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import requests
from io import BytesIO
import os
import random
import logging
import math
from datetime import datetime, timezone, timedelta
import pytz
import re
import json
import colorsys
import glob
import base64


def format_join_duration(created_ts):
    try:
        hcm_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        current_time = datetime.now(hcm_tz)
        join_time = datetime.fromtimestamp(created_ts, tz=pytz.UTC).astimezone(hcm_tz)
        delta = current_time - join_time
        years = delta.days // 365
        months = delta.days % 365 // 30
        days = delta.days % 30
        if years > 0:
            return f"Đã tham gia Zalo {years} năm {months} tháng {days} ngày"
        elif months > 0:
            return f"Đã tham gia Zalo {months} tháng {days} ngày"
        else:
            return f"Đã tham gia Zalo {days} ngày"
    except:
        return "Đã tham gia Zalo: Không rõ"

def load_excluded_groups(filepath="excluded_event.json"):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [entry["group_id"] for entry in data if "group_id" in entry]
    except Exception as e:
        logging.error(f"Lỗi khi đọc excluded_event.json: {e}")
        return []

des = {
    'version': "1.0.1",
    'credits': "Minh Vũ Shinn Cte FIX",
    'description': "WELCOM"
}

EXCLUDED_GROUPS = load_excluded_groups()

logging.basicConfig(
    level=logging.ERROR,
    filename="bot_error.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s"
)

emoji_pattern = re.compile(
    "("
    "[\U0001F1E6-\U0001F1FF]{2}|"
    "[\U0001F600-\U0001F64F]|"
    "[\U0001F300-\U0001F5FF]|"
    "[\U0001F680-\U0001F6FF]|"
    "[\U0001F700-\U0001F77F]|"
    "[\U0001F780-\U0001F7FF]|"
    "[\U0001F800-\U0001F8FF]|"
    "[\U0001F900-\U0001F9FF]|"
    "[\U0001FA00-\U0001FA6F]|"
    "[\U0001FA70-\U0001FAFF]|"
    "[\U0001FB00-\U0001FBFF]|"
    "[\u2600-\u26FF]|"
    "[\u2700-\u27BF]|"
    "[\u2300-\u23FF]|"
    "[\u2B00-\u2BFF]|"
    "\d\uFE0F?\u20E3|"
    "[#*]\uFE0F?\u20E3|"
    "[\U00013000-\U000134AF]"
    ")",
    flags=re.UNICODE
)

def split_text_by_emoji(text):
    segments = []
    buffer = ""
    for ch in text:
        if emoji_pattern.match(ch):
            if buffer:
                segments.append((buffer, False))
                buffer = ""
            segments.append((ch, True))
        else:
            buffer += ch
    if buffer:
        segments.append((buffer, False))
    return segments

def draw_mixed_gradient_text(draw, text, position, normal_font, emoji_font, gradient_colors, shadow_offset=(4,4)):
    if not text:
        return
    total_chars = len(text)
    change_every = 4
    color_list = []
    num_segments = len(gradient_colors) - 1
    steps_per_segment = (total_chars // change_every) + 1
    for i in range(num_segments):
        for j in range(steps_per_segment):
            if len(color_list) < total_chars:
                ratio = j / steps_per_segment
                c1, c2 = gradient_colors[i], gradient_colors[i+1]
                interpolated = (
                    int(c1[0]*(1 - ratio) + c2[0]*ratio),
                    int(c1[1]*(1 - ratio) + c2[1]*ratio),
                    int(c1[2]*(1 - ratio) + c2[2]*ratio)
                )
                color_list.append(interpolated)
    while len(color_list) < total_chars:
        color_list.append(gradient_colors[-1])
    
    x, y = position
    shadow_color = (0, 0, 0, 150)
    segments = split_text_by_emoji(text)
    char_index = 0
    for seg, is_emoji in segments:
        current_font = emoji_font if is_emoji else normal_font
        for ch in seg:
            draw.text((x + shadow_offset[0], y + shadow_offset[1]), ch, font=current_font, fill=shadow_color)
            draw.text((x, y), ch, font=current_font, fill=color_list[char_index])
            bbox = draw.textbbox((0, 0), ch, font=current_font)
            char_width = bbox[2] - bbox[0]
            x += char_width
            char_index += 1

def Dominant(image):
    try:
        img = image.convert("RGB").resize((150, 150), Image.Resampling.LANCZOS)
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
        r, g, b = r // total, g // total, b // total
        return (r, g, b)
    except Exception:
        return (0, 0, 0)

def ConsColor(Base, alpha=255):
    r, g, b = Base[:3]
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return (255, 255, 255, alpha) if luminance < 0.5 else (0, 0, 0, alpha)

def RandomContrast(Base):
    r, g, b, _ = Base
    box_luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    if box_luminance > 0.5:
        r = random.randint(80, 140)
        g = random.randint(80, 140)
        b = random.randint(80, 140)
    else:
        r = random.randint(160, 220)
        g = random.randint(160, 220)
        b = random.randint(160, 220)
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    s = min(0.5, s + 0.3)
    v = min(0.85, v + 0.1)
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    text_luminance = (0.299 * r + 0.587 * g + 0.114 * b)
    if abs(text_luminance - box_luminance) < 0.4:
        if box_luminance > 0.5:
            r, g, b = colorsys.hsv_to_rgb(h, s, min(0.7, v * 0.6))
        else:
            r, g, b = colorsys.hsv_to_rgb(h, s, min(0.9, v * 1.2))
    return (int(r * 255), int(g * 255), int(b * 255), 255)

def FetchImage(url):
    if not url:
        return None
    try:
        if url.startswith('data:image'):
            h, e = url.split(',', 1)
            i = base64.b64decode(e)
            return Image.open(BytesIO(i)).convert("RGB")
        r = requests.get(url, stream=True, timeout=10)
        r.raise_for_status()
        return Image.open(BytesIO(r.content)).convert("RGB")
    except:
        return None

MULTICOLOR_GRADIENT = [
    (255, 0, 0), (255, 165, 0), (255, 255, 0),
    (0, 255, 0), (0, 0, 255), (75, 0, 130), (148, 0, 211)
]

GRADIENT_SETS = [
    [(255, 0, 255), (0, 255, 255), (255, 255, 0), (0, 255, 0)],
    [(255, 0, 0), (255, 165, 0), (255, 255, 0)],
    [(255, 182, 193), (173, 216, 230), (152, 251, 152), (240, 230, 140)],
    [(255, 94, 77), (255, 160, 122), (255, 99, 71), (255, 215, 0)],
    [(255, 165, 0), (255, 69, 0), (255, 0, 0)],
    [(255, 182, 193), (255, 105, 180), (255, 20, 147), (255, 0, 255)],
    [(0, 255, 127), (0, 255, 255), (30, 144, 255)],
    [(0, 255, 127), (0, 191, 255), (123, 104, 238)],
    [(0, 255, 0), (138, 43, 226), (0, 255, 255)],
    [(255, 127, 80), (255, 165, 0), (255, 69, 0), (255, 99, 71)],
    [(255, 223, 186), (255, 182, 193), (255, 160, 122), (255, 99, 71)],
    [(176, 196, 222), (135, 206, 250), (70, 130, 180)],
    [(255, 105, 180), (0, 191, 255), (30, 144, 255)],
    [(255, 140, 0), (255, 99, 71), (255, 69, 0)],
    [(255, 0, 0), (0, 255, 0), (0, 255, 255)],
    [(0, 255, 255), (70, 130, 180)],
    [(0, 255, 127), (60, 179, 113)],
    [(0, 255, 255), (30, 144, 255), (135, 206, 235)],
    [(0, 255, 0), (50, 205, 50), (154, 205, 50)],
    [(255, 165, 0), (255, 223, 0), (255, 140, 0), (255, 69, 0)],
    [(255, 105, 180), (138, 43, 226), (255, 20, 147)],
    [(173, 216, 230), (216, 191, 216), (255, 182, 193)],
    [(152, 251, 152), (255, 255, 224), (245, 245, 245)],
    [(255, 192, 203), (255, 218, 185), (255, 250, 205)],
    [(224, 255, 255), (175, 238, 238), (255, 255, 255)],
    [(255, 204, 204), (255, 255, 204), (204, 255, 204), (204, 255, 255), (204, 204, 255), (255, 204, 255)],
    [(255, 239, 184), (255, 250, 250), (255, 192, 203)],
    [(173, 255, 47), (255, 255, 102), (255, 204, 153)],
    [(189, 252, 201), (173, 216, 230)],
    [(255, 182, 193), (250, 250, 250), (216, 191, 216)],
    [(173, 216, 230), (255, 255, 255), (255, 255, 102)],
]

def get_random_gradient():
    return random.choice(GRADIENT_SETS)

BACKGROUND_FOLDER = 'backgrounds'
if os.path.isdir(BACKGROUND_FOLDER):
    BACKGROUND_IMAGES = [
        os.path.join(BACKGROUND_FOLDER, f) 
        for f in os.listdir(BACKGROUND_FOLDER) 
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ]
else:
    BACKGROUND_IMAGES = []

def BackgroundGetting(width=3000, height=880):
    if BACKGROUND_IMAGES:
        bg_path = random.choice(BACKGROUND_IMAGES)
        bg = Image.open(bg_path).convert("RGB")
        bg = bg.resize((width, height), Image.Resampling.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=20))
        return bg
    else:
        return Image.new("RGB", (width, height), (130, 190, 255))

def DrawPillowBase1(draw, position, text, font, fill, shadow_offset=(4, 4), shadow_fill=(0, 0, 0, 150)):
    x, y = position
    draw.text((x + shadow_offset[0], y + shadow_offset[1]), text, font=font, fill=shadow_fill)
    draw.text((x, y), text, font=font, fill=fill)

def create_welcome_or_farewell_image(member_name, left_avatar_url, right_avatar_url,
                                     right_number, group_name, event_text,
                                     gio_phut, ngay_thang, executed_by, cover_url=None, created_ts=None):
    size = (3000, 880)
    final_size = (1500, 460)
    
    # Tạo nền ảnh
    if cover_url and cover_url != "https://cover-talk.zadn.vn/default":
        bg_image = FetchImage(cover_url)
        if bg_image:
            bg_image = bg_image.resize(size, Image.Resampling.LANCZOS)
            bg_image = bg_image.filter(ImageFilter.GaussianBlur(radius=20))
        else:
            bg_image = BackgroundGetting()
    else:
        bg_image = BackgroundGetting()
    if not bg_image:
        bg_image = Image.new("RGB", size, (130, 190, 255))
    bg_image = bg_image.convert("RGBA")
    
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    dominant_color = Dominant(bg_image)
    luminance = (0.299 * dominant_color[0] + 0.587 * dominant_color[1] + 0.114 * dominant_color[2]) / 255
    box_color = random.choice([
        (120, 200, 180, 100), (180, 140, 200, 100), (240, 180, 160, 100),
        (160, 200, 140, 100), (200, 160, 120, 100), (140, 180, 220, 100),
        (220, 200, 140, 100), (180, 180, 180, 105)
    ]) if luminance >= 0.5 else random.choice([
        (200, 140, 160, 105), (140, 120, 180, 105), (100, 140, 160, 105),
        (160, 140, 120, 105), (120, 160, 180, 105), (60, 60, 60, 80)
    ])

    box_x1, box_y1 = 60, 70
    box_x2, box_y2 = size[0] - 60, size[1] - 80
    draw.rounded_rectangle([(box_x1, box_y1), (box_x2, box_y2)], radius=100, fill=box_color)

    # Load font
    font_top_path = "font/5.otf"  # Font cũ cho các dòng khác
    font_name_path = "font/1.ttf"  # Font mới cho line1
    font_emoji_path = "font/NotoEmoji-Bold.ttf"
    try:
        font_text_large = ImageFont.truetype(font_name_path, 120)  # Font VL-Begin.ttf cho tên người dùng
        font_text_big = ImageFont.truetype(font_top_path, 110)  # Font cũ cho line2
        font_text = ImageFont.truetype(font_top_path, 80)  # Font cũ cho line3
        font_text_small = ImageFont.truetype(font_top_path, 105)  # Font cũ cho line4
        font_time = ImageFont.truetype(font_top_path, 65)  # Font cũ cho line5
        font_icon = ImageFont.truetype(font_emoji_path, 90)  # Font cho emoji
    except:
        font_text_large = font_text = font_text_big = font_text_small = font_time = font_icon = ImageFont.load_default()

    # Chuẩn bị văn bản
    if "tham gia" in event_text.lower():
        line1 = member_name  # Bỏ viết hoa
    elif "rời" in event_text.lower():
        line1 = member_name  # Bỏ viết hoa
    else:
        line1 = member_name  # Bỏ viết hoa
    line2 = event_text
    line3 = group_name
    if event_text == "Tham gia nhóm bằng link" or event_text == "Tham gia c.đồng bằng link":
        line4 = "Welcome"
    elif event_text == "❌ Tạm biệt":
        line4 = "Gặp gỡ là duyên, chia ly là lẽ thường."
    elif event_text in ["✔ Được duyệt vào nhóm", "✔ Được duyệt vào c.đồng"]:
        line4 = f"Duyệt bởi: {executed_by}"
    elif event_text in ["🚫 Bị block khỏi nhóm", "🚫 Bị block khỏi c.đồng"]:
        line4 = f"Chặn bởi: {executed_by}"
    elif event_text in ["🗝 Đã trở thành admin nhóm", "🗝 Đã trở thành admin c.đồng"]:
        line4 = f"Chỉ định bởi: {executed_by}"
    elif event_text in ["🗝 Đã bị cắt chức admin nhóm", "🗝 Đã bị cắt chức admin c.đồng"]:
        line4 = f"Gỡ bởi: {executed_by}"
    elif event_text in ["📑 Đã c.nhật nội quy nhóm", "📑 Đã c.nhật nội quy c.đồng"]:
        line4 = f"Cập nhật bởi: {executed_by}"
    else:
        line4 = f"Duyệt bởi: {executed_by}"
    line5 = f"Clan PricelessAOV"
    
    text_lines = [line1, line2, line3, line4, line5]
    text_fonts = [font_text_large, font_text_big, font_text_small, font_text_small, font_time]
    emoji_fonts = [font_icon, font_icon, font_icon, font_icon, font_icon]
    random_gradients = random.sample(GRADIENT_SETS, 3)

    text_colors = [
        MULTICOLOR_GRADIENT,  # line1
        random_gradients[0],  # line2
        MULTICOLOR_GRADIENT,  # line3
        random_gradients[1],  # line4
        random_gradients[2]   # line5
    ]

    line_spacing = 150
    start_y = box_y1 + 80 - 30
    avatar_left_edge = box_x1 + 50 + 430 + 1
    avatar_right_edge = box_x2 - 460 - 25
    safe_text_width = avatar_right_edge - avatar_left_edge - 50

    def truncate_text(line, font, max_width):
        if not line:
            return line
        truncated = line
        ellipsis = ".."
        ellipsis_width = draw.textbbox((0, 0), ellipsis, font=font)[2]
        while True:
            text_bbox = draw.textbbox((0, 0), truncated + ellipsis, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            if text_width <= max_width or len(truncated) <= 3:
                break
            if ord(truncated[-1]) > 0xFFFF:
                truncated = truncated[:-1]
            else:
                truncated = truncated[:-1]
        return truncated + ellipsis if truncated != line else line

    for i, (line, font, emoji_font, colors) in enumerate(zip(text_lines, text_fonts, emoji_fonts, text_colors)):
        if line:
            truncated_line = truncate_text(line, font, safe_text_width)
            text_bbox = draw.textbbox((0, 0), truncated_line, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_x = (box_x1 + box_x2 - text_width) // 2
            text_y = start_y + i * line_spacing
            if i == 0:  # Nhích line1 lên trên 20 pixel
                text_y -= 60
            draw_mixed_gradient_text(draw, truncated_line, (text_x, text_y), normal_font=font, emoji_font=emoji_font, gradient_colors=colors, shadow_offset=(4, 4))
            # Thêm đường kẻ ngang màu trắng sau line1
            if i == 0:
                line_y = text_y + (text_bbox[3] - text_bbox[1]) + 60  # Đặt đường kẻ cách line1 20 pixel
                draw.line([(box_x1 + 700, line_y), (box_x2 - 700, line_y)], fill=(255, 255, 255, 255), width=4)

    # Xử lý avatar
    avatar_size = 550
    center_y = (box_y1 + box_y2) // 2 + 60
    left_avatar_x = box_x1 + 50
    right_avatar_x = box_x2 - 600

    def load_avatar(url):
        if not url:
            return Image.new("RGBA", (avatar_size, avatar_size), (200, 200, 200, 255))
        try:
            img = FetchImage(url)
            if img:
                img = img.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS).convert("RGBA")
                return img
            return Image.new("RGBA", (avatar_size, avatar_size), (200, 200, 200, 255))
        except Exception as e:
            logging.error(f"Lỗi tải avatar: {e}")
            return Image.new("RGBA", (avatar_size, avatar_size), (200, 200, 200, 255))

    left_avatar = load_avatar(left_avatar_url)
    right_avatar = load_avatar(right_avatar_url)
    
    if event_text in ["🚫 Bị block khỏi nhóm", "🚫 Bị block khỏi c.đồng"]:
        left_avatar = draw_red_x(left_avatar, thickness=10)
        banned_path = "banned.png"
        if os.path.exists(banned_path):
            try:
                banned_img = Image.open(banned_path).convert("RGBA")
                avatar_diameter = 500
                aspect_ratio = banned_img.height / banned_img.width
                new_height = int(avatar_diameter * aspect_ratio)
                banned_img = banned_img.resize((avatar_diameter, new_height), Image.Resampling.LANCZOS)
                banned_pos_x = left_avatar.width - banned_img.width - 20
                banned_pos_y = left_avatar.height - banned_img.height
                left_avatar.alpha_composite(banned_img, (banned_pos_x, banned_pos_y))
            except Exception as e:
                logging.error(f"Lỗi khi dán banned.png lên avatar: {e}")

    for avatar, x in [(left_avatar, left_avatar_x), (right_avatar, right_avatar_x)]:
        mask = Image.new("L", (avatar_size, avatar_size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
        border_size = avatar_size + 20
        border_offset = (border_size - avatar_size) // 2
        rainbow_border = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
        draw_border = ImageDraw.Draw(rainbow_border)
        for i in range(360):
            h = i / 360
            r, g, b = colorsys.hsv_to_rgb(h, 0.5, 0.8)
            draw_border.arc([(3, 3), (border_size - 4, border_size - 4)], i, i + 1, fill=(int(r * 255), int(g * 255), int(b * 255), 255), width=6)
        overlay.paste(rainbow_border, (x - border_offset, center_y - border_size // 2), rainbow_border)
        overlay.paste(avatar, (x, center_y - avatar_size // 2), mask)

    # Vẽ số thành viên
    if right_number is not None:
        circle_radius = 90
        circle_center_x = box_x2 - 120
        circle_center_y = box_y1 + 120
        circle_color = get_random_gradient()[0]
        shadow_offset = (4, 4)
        shadow_color = (0, 0, 0, 150)
        border_width = 15

        draw.ellipse(
            [
                circle_center_x - circle_radius + shadow_offset[0],
                circle_center_y - circle_radius + shadow_offset[1],
                circle_center_x + circle_radius + shadow_offset[0],
                circle_center_y + circle_radius + shadow_offset[1]
            ],
            outline=shadow_color,
            width=border_width
        )
        
        draw.ellipse(
            [
                circle_center_x - circle_radius,
                circle_center_y - circle_radius,
                circle_center_x + circle_radius,
                circle_center_y + circle_radius
            ],
            outline=circle_color,
            width=border_width
        )

        member_count_text = str(right_number)
        member_count_font_size = 80
        try:
            member_count_font = ImageFont.truetype(font_top_path, member_count_font_size)
        except:
            member_count_font = ImageFont.load_default()

        text_bbox = draw.textbbox((0, 0), member_count_text, font=member_count_font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        while (text_width > (circle_radius - border_width) * 1.8 or text_height > (circle_radius - border_width) * 1.8) and member_count_font_size > 30:
            member_count_font_size -= 5
            try:
                member_count_font = ImageFont.truetype(font_top_path, member_count_font_size)
            except:
                member_count_font = ImageFont.load_default()
            text_bbox = draw.textbbox((0, 0), member_count_text, font=member_count_font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]

        text_x = circle_center_x - text_width // 2
        text_y = circle_center_y - text_height // 2 - 10
        text_color = (255, 255, 255, 255)
        DrawPillowBase1(draw, (text_x, text_y), member_count_text, member_count_font, text_color, shadow_offset, shadow_color)

    # Dán logo và chữ "design by Minh Vũ Shinn Cte"
    logo_path = "zalo.png"
    if os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo_size = 100
            logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
            mask = Image.new("L", (logo_size, logo_size), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, logo_size, logo_size), fill=255)
            round_logo = Image.new("RGBA", (logo_size, logo_size), (0, 0, 0, 0))
            round_logo.paste(logo, (0, 0), mask)
            logo_x = box_x1 + 50
            logo_y = size[1] - logo_size - 5
            overlay.paste(round_logo, (logo_x, logo_y), round_logo)
        except Exception as e:
            logging.error(f"Lỗi khi xử lý logo zalo.png: {e}")

    designer_text = "- Minh Vũ Shinn Cte Dzai -"
    designer_font = ImageFont.truetype(font_top_path, 65)
    text_bbox = draw.textbbox((0, 0), designer_text, font=designer_font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]
    designer_x = box_x2 - text_w - 20
    designer_y = size[1] - text_h - 25
    draw_mixed_gradient_text(
        draw,
        text=designer_text,
        position=(designer_x, designer_y),
        normal_font=designer_font,
        emoji_font=font_icon,
        gradient_colors=get_random_gradient(),
        shadow_offset=(4, 4)
    )

    # Dán thời gian
    left_info = format_join_duration(created_ts)
    left_font = ImageFont.truetype(font_top_path, 65)
    text_bbox = draw.textbbox((0, 0), left_info, font=left_font)
    text_h = text_bbox[3] - text_bbox[1]
    left_x = box_x1 + 150
    left_y = size[1] - text_h - 20
    draw_mixed_gradient_text(
        draw,
        text=left_info,
        position=(left_x, left_y),
        normal_font=left_font,
        emoji_font=font_icon,
        gradient_colors=[(255, 255, 255)],
        shadow_offset=(4, 4)
    )         

    final_image = Image.alpha_composite(bg_image, overlay).resize(final_size, Image.Resampling.LANCZOS).convert("RGB")
    image_path = "welcome_or_farewell.jpg"
    final_image.save(image_path, quality=95)
    return image_path

def draw_red_x(image, thickness=9):
    draw = ImageDraw.Draw(image)
    w, h = image.size
    draw.line((0, 0, w, h), fill=(255, 0, 0), width=thickness)
    draw.line((0, h, w, 0), fill=(255, 0, 0), width=thickness)
    return image

def shorten_name(name, max_length=20, word_count=2, is_group=False):
    return name

def delete_file(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Đã xóa file: {file_path}")
        else:
            print(f"Không tìm thấy file: {file_path}")
    except Exception as e:
        logging.error(f"Lỗi khi xóa file {file_path}: {e}")

def welcome(self, event_data, event_type, ttl=3600000):

    if event_type == GroupEventType.UNKNOWN:
        return

    thread_id = event_data['groupId']
    if thread_id in EXCLUDED_GROUPS:
        print(f"Nhóm {thread_id} nằm trong danh sách loại trừ, không gửi ảnh chào mừng.")
        return
    group_info = self.fetchGroupInfo(thread_id)
    if not group_info or 'gridInfoMap' not in group_info or thread_id not in group_info.gridInfoMap:
        print(f"Không thể lấy thông tin nhóm cho thread_id: {thread_id}")
        return

    group_data = group_info.gridInfoMap[thread_id]
    group_name = group_data['name']
    group_logo_url = group_data.get('avt', '')
    group_total_member = group_data['totalMember']

    def get_name(user_id):
        try:
            user_info = self.fetchUserInfo(user_id)
            return user_info.changed_profiles[user_id].zaloName
        except KeyError:
            return "Không tìm thấy tên"

    group_leader = get_name(group_data['creatorId'])
    actor_name = get_name(event_data['sourceId'])

    event_config = {
        GroupEventType.JOIN: {
            "img_type": "JOIN",
            "msg_func": lambda member: (
                "☘ {mention} ơi! Hãy cho chúng tôi biết về bạn\n"
                "Hãy giới thiệu, show acc kèm 1 tấm ảnh cá nhân, và đọc tin nhắn ghim nhé, cảm ơn bạn\n\n🚀 𝐃𝐈̣𝐂𝐇 𝐕𝐔̣ BOT ZALO X TELEBOT X FF🚀\n\n\n👑Nhận Cày Thuê Block Fruit\n\n💸Bán Scr Bot 400🐟\n🇻🇳Thuê Bot Chỉ 75🐟/1tháng\n💵Nhận Code Bot Theo Yêu Cầu\nCho Thuê Bot FF 50🐟/1tuần 150🐟/1tháng full\n\n\n✨ 🔥 DỊCH VỤ THUÊ BOT HD TELEGRAM 🔥\n✨🤖 Bot HD Telegram (Cơ Bản)\n💰 Giá chỉ: 40.000đ / tháng\n📌 Phù hợp: Treo nhóm, hỗ trợ lệnh cơ bản, tiện lợi & tiết kiệm\n🎮 Bot HD Trong Game (Bản Xịn)\n💎 Giá chỉ: 60.000đ / tháng"
            ),
            "ttl": 180000
        },
        GroupEventType.LEAVE: {
            "img_type": "LEAVE",
            "msg_func": lambda member: (
                f"☘ Chúng tôi sẽ nhớ bạn\n\n🚀 𝐃𝐈̣𝐂𝐇 𝐕𝐔̣ BOT ZALO X TELEBOT X FF🚀\n\n\n👑Nhận Cày Thuê Block Fruit\n\n💸Bán Scr Bot 400🐟\n🇻🇳Thuê Bot Chỉ 75🐟/1tháng\n💵Nhận Code Bot Theo Yêu Cầu\nCho Thuê Bot FF 50🐟/1tuần 150🐟/1tháng full\n\n\n✨ 🔥 DỊCH VỤ THUÊ BOT HD TELEGRAM 🔥\n✨🤖 Bot HD Telegram (Cơ Bản)\n💰 Giá chỉ: 40.000đ / tháng\n📌 Phù hợp: Treo nhóm, hỗ trợ lệnh cơ bản, tiện lợi & tiết kiệm\n🎮 Bot HD Trong Game (Bản Xịn)\n💎 Giá chỉ: 60.000đ / tháng"
            ),
            "ttl": 180000
        },
        GroupEventType.REMOVE_MEMBER: {
            "img_type": "REMOVE_MEMBER",
            "msg_func": lambda member: (
                f"☘ Hãy tuân thủ nội quy để tránh vi phạm nhé\n\n🚀 𝐃𝐈̣𝐂𝐇 𝐕𝐔̣ BOT ZALO X TELEBOT X FF🚀\n\n\n👑Nhận Cày Thuê Block Fruit\n\n💸Bán Scr Bot 400🐟\n🇻🇳Thuê Bot Chỉ 75🐟/1tháng\n💵Nhận Code Bot Theo Yêu Cầu\nCho Thuê Bot FF 50🐟/1tuần 150🐟/1tháng full\n\n\n✨ 🔥 DỊCH VỤ THUÊ BOT HD TELEGRAM 🔥\n✨🤖 Bot HD Telegram (Cơ Bản)\n💰 Giá chỉ: 40.000đ / tháng\n📌 Phù hợp: Treo nhóm, hỗ trợ lệnh cơ bản, tiện lợi & tiết kiệm\n🎮 Bot HD Trong Game (Bản Xịn)\n💎 Giá chỉ: 60.000đ / tháng"
            ),
            "ttl": 180000
        },
        GroupEventType.ADD_ADMIN: {
            "img_type": "ADD_ADMIN",
            "msg_func": lambda member: (
                f"☘ Chúc mừng bạn\n\n🚀 𝐃𝐈̣𝐂𝐇 𝐕𝐔̣ BOT ZALO X TELEBOT X FF🚀\n\n\n👑Nhận Cày Thuê Block Fruit\n\n💸Bán Scr Bot 400🐟\n🇻🇳Thuê Bot Chỉ 75🐟/1tháng\n💵Nhận Code Bot Theo Yêu Cầu\nCho Thuê Bot FF 50🐟/1tuần 150🐟/1tháng full\n\n\n✨ 🔥 DỊCH VỤ THUÊ BOT HD TELEGRAM 🔥\n✨🤖 Bot HD Telegram (Cơ Bản)\n💰 Giá chỉ: 40.000đ / tháng\n📌 Phù hợp: Treo nhóm, hỗ trợ lệnh cơ bản, tiện lợi & tiết kiệm\n🎮 Bot HD Trong Game (Bản Xịn)\n💎 Giá chỉ: 60.000đ / tháng"
            ),
            "ttl": 180000
        },
        GroupEventType.REMOVE_ADMIN: {
            "img_type": "REMOVE_ADMIN",
            "msg_func": lambda member: (
                f"☘ Hi vọng bạn sẽ vẫn đồng hành cùng nhóm với vai trò khác\n\n🚀 𝐃𝐈̣𝐂𝐇 𝐕𝐔̣ BOT ZALO X TELEBOT X FF🚀\n\n\n👑Nhận Cày Thuê Block Fruit\n\n💸Bán Scr Bot 400🐟\n🇻🇳Thuê Bot Chỉ 75🐟/1tháng\n💵Nhận Code Bot Theo Yêu Cầu\nCho Thuê Bot FF 50🐟/1tuần 150🐟/1tháng full\n\n\n✨ 🔥 DỊCH VỤ THUÊ BOT HD TELEGRAM 🔥\n✨🤖 Bot HD Telegram (Cơ Bản)\n💰 Giá chỉ: 40.000đ / tháng\n📌 Phù hợp: Treo nhóm, hỗ trợ lệnh cơ bản, tiện lợi & tiết kiệm\n🎮 Bot HD Trong Game (Bản Xịn)\n💎 Giá chỉ: 60.000đ / tháng"
            ),
            "ttl": 180000
        },
        GroupEventType.UPDATE: {
            "img_type": "UPDATE",
            "msg_func": lambda member: (
                f"☘ ADMIN đã cập nhật nội quy nhóm\n\n🚀 𝐃𝐈̣𝐂𝐇 𝐕𝐔̣ BOT ZALO X TELEBOT X FF🚀\n\n\n👑Nhận Cày Thuê Block Fruit\n\n💸Bán Scr Bot 400🐟\n🇻🇳Thuê Bot Chỉ 75🐟/1tháng\n💵Nhận Code Bot Theo Yêu Cầu\nCho Thuê Bot FF 50🐟/1tuần 150🐟/1tháng full\n\n\n✨ 🔥 DỊCH VỤ THUÊ BOT HD TELEGRAM 🔥\n✨🤖 Bot HD Telegram (Cơ Bản)\n💰 Giá chỉ: 40.000đ / tháng\n📌 Phù hợp: Treo nhóm, hỗ trợ lệnh cơ bản, tiện lợi & tiết kiệm\n🎮 Bot HD Trong Game (Bản Xịn)\n💎 Giá chỉ: 60.000đ / tháng"
            ),
            "ttl": 180000
        }
    }

    if event_type not in event_config:
        return

    config = event_config[event_type]
    event_text_mapping = {
        "JOIN": "✔ Được duyệt vào nhóm",
        "LEAVE": "❌ Tạm biệt",
        "REMOVE_MEMBER": "🚫 Bị block khỏi nhóm",
        "ADD_ADMIN": "🗝 Đã trở thành admin nhóm",
        "REMOVE_ADMIN": "🗝 Đã bị cắt chức admin nhóm",
        "UPDATE": "📑 Đã c.nhật nội quy nhóm"
    }

    bot_id = "127225959075940390"

    def process_member(member):
        member_name = member['dName']
        member_id = member['id']
        avatar_url = member.get('avatar', '')
        cover_url = None
        created_ts = None  # Khởi tạo mặc định
        if config["img_type"] == "JOIN" and member_id == bot_id:
            print(f"Bỏ qua sự kiện JOIN cho bot với ID: {bot_id}")
            return
        try:
            user_info = self.fetchUserInfo(member['id'])
            cover_url = user_info.changed_profiles[member['id']].cover
            created_ts = user_info.changed_profiles[member['id']].createdTs
            print(f"[DEBUG] Dữ liệu từ API fetchUserInfo cho {member_name} (id: {member['id']}): {user_info.changed_profiles[member['id']].__dict__}")
            if isinstance(created_ts, int) and created_ts > 0:
                join_time = format_join_duration(created_ts)
                print(f"[DEBUG] Thời gian tham gia của {member_name}: {join_time}")
            else:
                join_time = "Đã tham gia Zalo: Không rõ"
                print(f"[DEBUG] createdTs không hợp lệ cho {member_name}: {created_ts}")
        except Exception as e:
            logging.error(f"Lỗi khi lấy thông tin người dùng (id {member['id']}): {e}")
            print(f"[DEBUG] Lỗi khi lấy thông tin người dùng (id {member['id']}): {e}")
            join_time = "Đã tham gia Zalo: Không rõ"
            cover_url = None

        event_text = event_text_mapping.get(config["img_type"], "").strip()
        if config["img_type"] == "JOIN" and member_id == event_data['sourceId']:
            event_text = "Tham gia nhóm bằng link".strip()
        if group_total_member >= 100:
            event_text = event_text.replace("nhóm", "c.đồng")

        logging.debug(f"DEBUG: event_text trong welcome: '{event_text}', group_total_member: {group_total_member}")

        image_path = create_welcome_or_farewell_image(
            member_name=member_name,
            left_avatar_url=avatar_url,
            right_avatar_url=group_logo_url,
            right_number=group_total_member,
            group_name=group_name,
            event_text=event_text,
            gio_phut="",  # Không dùng
            ngay_thang="",  # Không dùng
            executed_by=actor_name,
            cover_url=cover_url,
            created_ts=created_ts
        )
        if image_path and os.path.exists(image_path):
            print(f"[DEBUG] Ảnh tồn tại tại: {image_path}")
        else:
            print(f"[DEBUG] Ảnh không tồn tại hoặc image_path là: {image_path}")
            return
        try:
            raw_text = config["msg_func"](member_name)
            if "{mention}" in raw_text and config["img_type"] == "JOIN":
                # Lấy UID thật (có thể là "12345_abc" → chỉ lấy "12345")
                uid = member_id.split('_')[0] if '_' in member_id else member_id
                # Tạo chuỗi @Tên
                mention_text = f"@{member_name}"
                # Thay {mention} bằng @Tên
                full_text = raw_text.replace("{mention}", mention_text)
                # Tính vị trí và độ dài của @Tên
                offset = full_text.find(mention_text)
                length = len(mention_text)
                # Tạo mention object
                mention = Mention(uid=uid, offset=offset, length=length)
                # Gửi tin nhắn có mention
                message = Message(text=full_text, mention=mention)
            else:
                # Không có {mention} hoặc không phải JOIN → gửi text thường
                message = Message(text=raw_text)

            self.sendLocalImage(
                image_path,
                thread_id,
                ThreadType.GROUP,
                message=message,
                width=1500,
                height=460,
                ttl=config["ttl"]
            )
            print(f"[DEBUG] Đã gửi ảnh: {image_path}")
        except Exception as e:
            logging.error(f"Lỗi khi gửi ảnh: {e}")
            print(f"[DEBUG] Lỗi khi gửi ảnh: {e}")
        delete_file(image_path)           

    if len(event_data.updateMembers) > 1:
        with ThreadPoolExecutor(max_workers=30) as executor:
            executor.map(process_member, event_data.updateMembers)
    else:
        for member in event_data.updateMembers:
            process_member(member)

def get_mitaizl():
    return {
        'welcome': None
    }