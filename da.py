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
import re
import json

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
    'credits': "ROSY FIX",
    'description': "WELCOM"
}

# Danh sách thread_id của các nhóm không gửi ảnh chào mừng
EXCLUDED_GROUPS = load_excluded_groups()

logging.basicConfig(
    level=logging.ERROR,
    filename="bot_error.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s"
)

import re

emoji_pattern = re.compile(
    "("
    "[\U0001F1E6-\U0001F1FF]{2}|"     # Flags (cặp ký tự vùng)
    "[\U0001F600-\U0001F64F]|"        # Emoticons
    "[\U0001F300-\U0001F5FF]|"        # Symbols & pictographs
    "[\U0001F680-\U0001F6FF]|"        # Transport & map symbols
    "[\U0001F700-\U0001F77F]|"
    "[\U0001F780-\U0001F7FF]|"
    "[\U0001F800-\U0001F8FF]|"
    "[\U0001F900-\U0001F9FF]|"
    "[\U0001FA00-\U0001FA6F]|"
    "[\U0001FA70-\U0001FAFF]|"
    "[\U0001FB00-\U0001FBFF]|"        # Thêm phạm vi rộng hơn cho emoji mới
    "[\u2600-\u26FF]|"                # Misc symbols (☀️✈️)
    "[\u2700-\u27BF]|"                # Dingbats (✂️✉️)
    "[\u2300-\u23FF]|"                # Technical (⏰)
    "[\u2B00-\u2BFF]|"                # Additional symbols (⭑, etc)
    "\d\uFE0F?\u20E3|"                # Keycap emoji (7️⃣ etc)
    "[#*]\uFE0F?\u20E3|"              # #️⃣ *️⃣
    "[\U00013000-\U000134AF]"         # Mở rộng Egyptian Hieroglyphs
    ")",
    flags=re.UNICODE
)


def split_text_by_emoji(text):
    """
    Tách văn bản thành danh sách các tuple (segment, is_emoji).
    Nếu is_emoji là True thì segment chứa emoji, False là văn bản thường.
    """
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

def draw_mixed_gradient_text(draw, text, position, normal_font, emoji_font, gradient_colors, shadow_offset=(2,2)):
    """
    Vẽ text hỗn hợp với hiệu ứng gradient:
      - Dùng normal_font cho ký tự thường.
      - Dùng emoji_font cho emoji.
    """
    if not text:
        return

    # Tính danh sách màu gradient cho mỗi ký tự
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
    shadow_color = (0, 0, 0)
    segments = split_text_by_emoji(text)
    char_index = 0
    for seg, is_emoji in segments:
        current_font = emoji_font if is_emoji else normal_font
        for ch in seg:
            # Vẽ bóng đổ
            draw.text((x + shadow_offset[0], y + shadow_offset[1]), ch, font=current_font, fill=shadow_color)
            # Vẽ ký tự với màu gradient tương ứng
            draw.text((x, y), ch, font=current_font, fill=color_list[char_index])
            bbox = draw.textbbox((0, 0), ch, font=current_font)
            char_width = bbox[2] - bbox[0]
            x += char_width
            char_index += 1

def draw_centered_text_mixed_line(text, y, normal_font, emoji_font, gradient_colors, base_draw, region_x0, region_x1):
    """
    Tính toán vị trí căn giữa cho text hỗn hợp và gọi hàm vẽ mixed gradient.
    """
    total_width = 0
    segments = split_text_by_emoji(text)
    for seg, is_emoji in segments:
        f = emoji_font if is_emoji else normal_font
        seg_bbox = base_draw.textbbox((0, 0), seg, font=f)
        seg_width = seg_bbox[2] - seg_bbox[0]
        total_width += seg_width
    region_w = region_x1 - region_x0
    x = region_x0 + (region_w - total_width) // 2
    draw_mixed_gradient_text(base_draw, text, (x, y), normal_font, emoji_font, gradient_colors, shadow_offset=(2,2))

# ------------------ HẰNG SỐ CHUNG & ẢNH NỀN ------------------
MULTICOLOR_GRADIENT = [
    (255, 0, 0), (255, 165, 0), (255, 255, 0),
    (0, 255, 0), (0, 0, 255), (75, 0, 130), (148, 0, 211)
]
# Định nghĩa nhiều dải màu gradient
GRADIENT_SETS = [
    # Dải màu Neon sặc sỡ
    [(255, 0, 255), (0, 255, 255), (255, 255, 0), (0, 255, 0)],
    # Dải màu cầu vồng rực rỡ
    [(255, 0, 0), (255, 165, 0), (255, 255, 0)],
    # Dải màu pastel nhẹ nhàng
    [(255, 182, 193), (173, 216, 230), (152, 251, 152), (240, 230, 140)],
    # Dải màu hoàng hôn
    [(255, 94, 77), (255, 160, 122), (255, 99, 71), (255, 215, 0)],
    # Dải màu vàng - cam - đỏ rực cháy
    [(255, 165, 0), (255, 69, 0), (255, 0, 0)],
    # Dải màu hồng ngọt ngào
    [(255, 182, 193), (255, 105, 180), (255, 20, 147), (255, 0, 255)],
    # Dải màu xanh lá - xanh dương đại dương
    [(0, 255, 127), (0, 255, 255), (30, 144, 255)],
    # Dải màu ánh sáng phương Bắc
    [(0, 255, 127), (0, 191, 255), (123, 104, 238)],
    # Dải màu xanh lá - tím - xanh dương
    [(0, 255, 0), (138, 43, 226), (0, 255, 255)],
    # Dải màu bầu trời bình minh
    [(255, 127, 80), (255, 165, 0), (255, 69, 0), (255, 99, 71)],
    # Dải màu pastel đa sắc
    [(255, 223, 186), (255, 182, 193), (255, 160, 122), (255, 99, 71)],
    # Dải màu ánh sáng thiên đường
    [(176, 196, 222), (135, 206, 250), (70, 130, 180)],
    # Dải màu hồng - xanh dương huyền ảo
    [(255, 105, 180), (0, 191, 255), (30, 144, 255)],
    # Dải màu vàng - cam - đỏ sáng rực
    [(255, 140, 0), (255, 99, 71), (255, 69, 0)],
    # Dải màu gradient đỏ - xanh lá - xanh dương
    [(255, 0, 0), (0, 255, 0), (0, 255, 255)],
    # Dải màu xanh biển mát mẻ
    [(0, 255, 255), (70, 130, 180)],
    # Dải màu ngọc bích huyền bí
    [(0, 255, 127), (60, 179, 113)],
    # Dải màu xanh dương sáng rực
    [(0, 255, 255), (30, 144, 255), (135, 206, 235)],
    # Dải màu xanh lá tươi sáng
    [(0, 255, 0), (50, 205, 50), (154, 205, 50)],
    # Dải màu cam - vàng nắng ấm
    [(255, 165, 0), (255, 223, 0), (255, 140, 0), (255, 69, 0)],
    # Dải màu hồng - tím rực rỡ
    [(255, 105, 180), (138, 43, 226), (255, 20, 147)],
    # Dải màu xanh da trời nhẹ - tím nhạt - hồng baby
    [(173, 216, 230), (216, 191, 216), (255, 182, 193)],

    # Dải màu xanh bạc hà - vàng nhạt - trắng sữa
    [(152, 251, 152), (255, 255, 224), (245, 245, 245)],

    # Dải màu hồng pastel - cam đào - vàng pastel
    [(255, 192, 203), (255, 218, 185), (255, 250, 205)],

    # Dải màu xanh băng - xanh nhạt - trắng sáng
    [(224, 255, 255), (175, 238, 238), (255, 255, 255)],

    # Dải màu cầu vồng pastel sáng
    [(255, 204, 204), (255, 255, 204), (204, 255, 204), (204, 255, 255), (204, 204, 255), (255, 204, 255)],

    # Dải màu vàng kem - trắng - hồng sáng
    [(255, 239, 184), (255, 250, 250), (255, 192, 203)],

    # Dải màu xanh nõn chuối - vàng sáng - cam nhẹ
    [(173, 255, 47), (255, 255, 102), (255, 204, 153)],

    # Dải màu xanh mint - xanh dương nhạt - tím phấn
    [(189, 252, 201), (173, 216, 230)],

    # Dải màu hồng baby - trắng ngọc - tím nhẹ
    [(255, 182, 193), (250, 250, 250), (216, 191, 216)],

    # Dải màu xanh nước biển nhạt - trắng - vàng chanh
    [(173, 216, 230), (255, 255, 255), (255, 255, 102)],

]

def get_random_gradient():
    return random.choice(GRADIENT_SETS)
    
BACKGROUND_FOLDER = 'gai'
if os.path.isdir(BACKGROUND_FOLDER):
    BACKGROUND_IMAGES = [
        os.path.join(BACKGROUND_FOLDER, f) 
        for f in os.listdir(BACKGROUND_FOLDER) 
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ]
else:
    BACKGROUND_IMAGES = []

def create_background_from_folder(width, height):
    """Chọn ảnh nền ngẫu nhiên từ thư mục, resize về (width, height)."""
    if BACKGROUND_IMAGES:
        bg_path = random.choice(BACKGROUND_IMAGES)
        bg = Image.open(bg_path).convert("RGB")
        return bg.resize((width, height), Image.LANCZOS)
    else:
        return Image.new("RGB", (width, height), (130, 190, 255))

# ------------------ HÀM PHỤ TRỢ ------------------
_FONT_CACHE = {}
def get_font(font_path, size):
    """Load font (cache lại) để không load nhiều lần."""
    key = (font_path, size)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = ImageFont.truetype(font_path, size)
    return _FONT_CACHE[key]

def make_round_avatar(avatar):
    """Tăng sáng nhẹ, cắt avatar thành hình tròn."""
    avatar = ImageEnhance.Brightness(avatar).enhance(1.2)
    w, h = avatar.size
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, w, h), fill=255)
    round_img = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    round_img.paste(avatar, (0, 0), mask)
    return round_img

def get_gradient_color(colors, ratio):
    """Nội suy màu theo tỉ lệ 0..1 dựa trên danh sách colors."""
    if ratio <= 0:
        return colors[0]
    if ratio >= 1:
        return colors[-1]
    total_segments = len(colors) - 1
    seg = int(ratio * total_segments)
    seg_ratio = (ratio * total_segments) - seg
    c1, c2 = colors[seg], colors[seg + 1]
    return (
        int(c1[0]*(1 - seg_ratio) + c2[0]*seg_ratio),
        int(c1[1]*(1 - seg_ratio) + c2[1]*seg_ratio),
        int(c1[2]*(1 - seg_ratio) + c2[2]*seg_ratio)
    )

def add_multicolor_circle_border(image, colors, border_thickness=5):
    """Thêm viền tròn đa sắc xung quanh ảnh tròn."""
    w, h = image.size
    new_size = (w + 2 * border_thickness, h + 2 * border_thickness)
    border_img = Image.new("RGBA", new_size, (0, 0, 0, 0))
    draw_border = ImageDraw.Draw(border_img)
    cx, cy = new_size[0] / 2, new_size[1] / 2
    r = w / 2
    outer_r = r + border_thickness

    for angle in range(360):
        rad = math.radians(angle)
        inner_point = (cx + r * math.cos(rad), cy + r * math.sin(rad))
        outer_point = (cx + outer_r * math.cos(rad), cy + outer_r * math.sin(rad))
        color = get_gradient_color(colors, angle / 360.0)
        draw_border.line([inner_point, outer_point], fill=color, width=border_thickness)

    border_img.paste(image, (border_thickness, border_thickness), image)
    return border_img

def add_multicolor_rectangle_border(image, colors, border_thickness=10):
    """Thêm viền đa sắc quanh khung ảnh."""
    new_w = image.width + 2 * border_thickness
    new_h = image.height + 2 * border_thickness
    border_img = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
    draw_b = ImageDraw.Draw(border_img)
    for x in range(new_w):
        color = get_gradient_color(colors, x / new_w)
        draw_b.line([(x, 0), (x, border_thickness - 1)], fill=color)
        draw_b.line([(x, new_h - border_thickness), (x, new_h - 1)], fill=color)
    for y in range(new_h):
        color = get_gradient_color(colors, y / new_h)
        draw_b.line([(0, y), (border_thickness - 1, y)], fill=color)
        draw_b.line([(new_w - border_thickness, y), (new_w - 1, y)], fill=color)

    border_img.paste(image, (border_thickness, border_thickness), image)
    return border_img

def draw_circle_with_text(base_img, x, y, radius, text, font, fill=(255,255,255),
                          bg_color=(255,0,0), alpha=255):
    circle_img = Image.new("RGBA", (radius * 2, radius * 2), (0, 0, 0, 0))
    draw_c = ImageDraw.Draw(circle_img)
    draw_c.ellipse((0, 0, radius * 2, radius * 2),
                   fill=(bg_color[0], bg_color[1], bg_color[2], alpha))
    text_bbox = draw_c.textbbox((0, 0), text, font=font)
    center_x = (text_bbox[0] + text_bbox[2]) / 2  # (left + right) / 2
    center_y = (text_bbox[1] + text_bbox[3]) / 2  # (top + bottom) / 2
    tx = radius - center_x
    ty = radius - center_y
    draw_c.text((tx, ty), text, font=font, fill=fill)
    base_img.alpha_composite(circle_img, (x, y))

def draw_gradient_text(draw, text, position, font, gradient_colors, shadow_offset=(2, 2)):
    """
    Vẽ text với hiệu ứng gradient màu kết hợp bóng (shadow).
    """
    if not text:
        return
    text_len = len(text)
    change_every = 4
    color_list = []
    num_segments = len(gradient_colors) - 1
    steps_per_segment = (text_len // change_every) + 1
    for i in range(num_segments):
        for j in range(steps_per_segment):
            if len(color_list) < text_len:
                ratio = j / steps_per_segment
                c1, c2 = gradient_colors[i], gradient_colors[i+1]
                interpolated = (
                    int(c1[0] * (1 - ratio) + c2[0] * ratio),
                    int(c1[1] * (1 - ratio) + c2[1] * ratio),
                    int(c1[2] * (1 - ratio) + c2[2] * ratio)
                )
                color_list.append(interpolated)
    while len(color_list) < text_len:
        color_list.append(gradient_colors[-1])

    x, y = position
    shadow_color = (0, 0, 0)
    for i, ch in enumerate(text):
        ch_color = color_list[i]
        draw.text((x + shadow_offset[0], y + shadow_offset[1]), ch, font=font, fill=shadow_color)
        draw.text((x, y), ch, font=font, fill=ch_color)
        cw = draw.textbbox((0, 0), ch, font=font)[2]
        x += cw

def draw_ribbon_trapezoid_label(base_img, event_text, group_total_member, font_path="font/ChivoMono-VariableFont_wght.ttf", font_size=32, fill_color=(255, 255, 0)):
    """
    Vẽ nhãn hình thang với nội dung động dựa trên event_text.
    - event_text: Chuỗi mô tả sự kiện (ví dụ: "THAM GIA NHÓM", "OUT MEMBER").
    """
    # Ánh xạ event_text thành nội dung nhãn
    label_text_mapping = {
        "✔ ĐƯỢC DUYỆT VÀO NHÓM": "WELCOME",
        "✔ ĐƯỢC DUYỆT VÀO C.ĐỒNG": "WELCOME",
        "THAM GIA NHÓM BẰNG LINK": "WELCOME",
        "THAM GIA C.ĐỒNG BẰNG LINK": "WELCOME",
        "❌ OUT MEMBER": "OUT MEMBER",
        "🚫 BỊ BLOCK KHỎI NHÓM": "BLOCKED",
        "🚫 BỊ BLOCK KHỎI C.ĐỒNG": "BLOCKED",
        "🗝 ĐÃ TRỞ THÀNH ADMIN NHÓM": "NEW ADMIN",
        "🗝 ĐÃ TRỞ THÀNH ADMIN C.ĐỒNG": "NEW ADMIN",
        "🗝 Đã bị cắt chức phó nhóm": "ADMIN REMOVED",
        "🗝 Đã bị cắt chức phó C.ĐỒNG": "ADMIN REMOVED",
        "📑 Đã cập nhật nội quy nhóm": "UPDATED",
        "📑 Đã cập nhật nội quy C.ĐỒNG": "UPDATED"
    }
    
    # Ghi log để kiểm tra event_text
    logging.debug(f"DEBUG: event_text nhận được: '{event_text}'")
    
    # Lấy nội dung nhãn, mặc định "BOT YUMI" nếu không khớp
    label_text = label_text_mapping.get(event_text, "BOT YUMI")
    if label_text == "BOT YUMI":
        logging.warning(f"Cảnh báo: event_text '{event_text}' không được ánh xạ, dùng mặc định 'BOT YUMI'")

    label_top = 180
    label_bottom = 300
    height = 60
    offset = (label_bottom - label_top) // 2

    # Tạo hình thang với gradient
    label_img = Image.new("RGBA", (label_bottom, height), (0, 0, 0, 0))
    draw_label = ImageDraw.Draw(label_img)
    gradient_colors = get_random_gradient()
    num_steps = label_bottom
    step_width = label_bottom / num_steps
    for i in range(num_steps):
        x_left = i * step_width
        x_right = (i + 1) * step_width
        ratio = i / num_steps
        color = get_gradient_color(gradient_colors, ratio)
        points = [(x_left, 0), (x_right, 0), (x_right, height), (x_left, height)]
        draw_label.polygon(points, fill=color)

    # Tạo mask hình thang
    points_trapezoid = [(offset, 0), (offset + label_top, 0), (label_bottom, height), (0, height)]
    mask = Image.new("L", (label_bottom, height), 0)
    ImageDraw.Draw(mask).polygon(points_trapezoid, fill=255)
    label_img = Image.composite(label_img, Image.new("RGBA", (label_bottom, height), (0, 0, 0, 0)), mask)

    # Xoay hình thang
    rotated = label_img.rotate(45, expand=True)
    pos_x, pos_y = -10, 30
    base_img.alpha_composite(rotated, (pos_x, pos_y))

    # Vẽ chữ xoay và căn giữa với viền đen
    font = get_font(font_path, font_size)
    text_img = Image.new("RGBA", (label_bottom, height), (0, 0, 0, 0))
    draw_text = ImageDraw.Draw(text_img)
    text_bbox = draw_text.textbbox((0, 0), label_text, font=font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]
    text_x = (label_bottom - text_w) // 2
    text_y = (height - text_h) // 2

    # Vẽ viền đen
    outline_color = (0, 0, 0)
    outline_thickness = 2
    for dx in [-outline_thickness, 0, outline_thickness]:
        for dy in [-outline_thickness, 0, outline_thickness]:
            if dx != 0 or dy != 0:
                draw_text.text((text_x + dx, text_y + dy), label_text, font=font, fill=outline_color)

    # Vẽ chữ chính
    draw_text.text((text_x, text_y), label_text, font=font, fill=fill_color)
    
    # Xoay text và dán lên base_img
    rotated_text = text_img.rotate(45, expand=True)
    text_pos_x = pos_x + (rotated.width - rotated_text.width) // 2
    text_pos_y = pos_y + (rotated.height - rotated_text.height) // 2
    base_img.alpha_composite(rotated_text, (text_pos_x, text_pos_y))

def draw_ribbon_trapezoid_label_bottom_right(base_img, text="BOT YUMI", font_path="font/ChivoMono-VariableFont_wght.ttf", font_size=32, fill_color=(255, 255, 0)):
    """
    Vẽ nhãn hình thang ở góc dưới phải, đối xứng với nhãn ở góc trên trái.
    """
    label_top = 180
    label_bottom = 300
    height = 60
    offset = (label_bottom - label_top) // 2

    # Tạo hình thang với gradient
    label_img = Image.new("RGBA", (label_bottom, height), (0, 0, 0, 0))
    draw_label = ImageDraw.Draw(label_img)
    gradient_colors = get_random_gradient()
    num_steps = label_bottom
    step_width = label_bottom / num_steps
    for i in range(num_steps):
        x_left = i * step_width
        x_right = (i + 1) * step_width
        ratio = i / num_steps
        color = get_gradient_color(gradient_colors, ratio)
        points = [(x_left, 0), (x_right, 0), (x_right, height), (x_left, height)]
        draw_label.polygon(points, fill=color)

    # Tạo mask hình thang (đối xứng so với nhãn trên trái)
    points_trapezoid = [(0, 0), (label_bottom, 0), (offset + label_top, height), (offset, height)]
    mask = Image.new("L", (label_bottom, height), 0)
    ImageDraw.Draw(mask).polygon(points_trapezoid, fill=255)
    label_img = Image.composite(label_img, Image.new("RGBA", (label_bottom, height), (0, 0, 0, 0)), mask)

    # Xoay hình thang
    rotated = label_img.rotate(45, expand=True)
    base_width, base_height = base_img.size
    # Tính toán vị trí đối xứng với nhãn trên trái
    # Nhãn trên trái cách mép trái 10px và mép trên 30px
    pos_x = base_width - rotated.width + 10  # Cách mép phải 10px
    pos_y = base_height - rotated.height - 30  # Cách mép dưới 30px
    base_img.alpha_composite(rotated, (pos_x, pos_y))

    # Vẽ chữ xoay và căn giữa với viền đen
    font = get_font(font_path, font_size)
    text_img = Image.new("RGBA", (label_bottom, height), (0, 0, 0, 0))
    draw_text = ImageDraw.Draw(text_img)
    text_bbox = draw_text.textbbox((0, 0), text, font=font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]
    text_x = (label_bottom - text_w) // 2
    text_y = (height - text_h) // 2

    # Vẽ viền đen
    outline_color = (0, 0, 0)
    outline_thickness = 2
    for dx in [-outline_thickness, 0, outline_thickness]:
        for dy in [-outline_thickness, 0, outline_thickness]:
            if dx != 0 or dy != 0:
                draw_text.text((text_x + dx, text_y + dy), text, font=font, fill=outline_color)

    # Vẽ chữ chính
    draw_text.text((text_x, text_y), text, font=font, fill=fill_color)
    
    # Xoay text và dán lên base_img
    rotated_text = text_img.rotate(45, expand=True)
    text_pos_x = pos_x + (rotated.width - rotated_text.width) // 2
    text_pos_y = pos_y + (rotated.height - rotated_text.height) // 2
    base_img.alpha_composite(rotated_text, (text_pos_x, text_pos_y))

def shorten_name(name, max_length=20, word_count=2, is_group=False):
    """Rút gọn tên, với nhóm lấy 2 từ đầu + '..' + 2 từ cuối nếu vượt max_length."""
    if len(name) > max_length:
        words = name.strip().split()
        if is_group and len(words) >= 4:  # Đảm bảo đủ từ
            shortened = " ".join(words[:2]) + " .. " + " ".join(words[-2:])
        elif len(words) >= word_count:
            shortened = " ".join(words[-word_count:])
        else:
            shortened = " ".join(words)
        return shortened
    return name

def draw_red_x(image, thickness=9):
    """Vẽ dấu X màu đỏ lên ảnh."""
    draw = ImageDraw.Draw(image)
    w, h = image.size
    draw.line((0, 0, w, h), fill=(255, 0, 0), width=thickness)
    draw.line((0, h, w, 0), fill=(255, 0, 0), width=thickness)
    return image
    
# ------------------ HÀM TẠO ẢNH CHÀO MỪNG / TẠM BIỆT ------------------
def create_welcome_or_farewell_image(member_name, left_avatar_url, right_avatar_url,
                                     right_number, group_name, event_text,
                                     gio_phut, ngay_thang, executed_by, cover_url=None):
    """
    Tạo ảnh chào mừng/tạm biệt với layout:
      - Nền: nếu có ảnh bìa (cover_url) của người dùng thì sử dụng làm nền, 
             nếu không có thì lấy ảnh ngẫu nhiên từ folder hoặc tạo nền màu xanh.
      - Overlay: khung bo góc hồng mờ.
      - Avatar trái: avatar của thành viên.
      - Avatar phải: avatar của nhóm, có vòng tròn hiển thị số thành viên.
      - Các dòng text: được căn giữa theo overlay.
    Trả về đường dẫn file ảnh ("welcome_or_farewell.jpg").
    """
    WIDTH, HEIGHT = 1472, 600
    member_name = shorten_name(member_name, max_length=12, word_count=2)
    group_name = shorten_name(group_name, max_length=15, word_count=4, is_group=True)
    # 1) Tạo nền ảnh
    if cover_url and cover_url != "https://cover-talk.zadn.vn/default":
        try:
            resp = requests.get(cover_url, timeout=5)
            resp.raise_for_status()
            background = Image.open(BytesIO(resp.content)).convert("RGB")
            background = background.resize((WIDTH, HEIGHT), Image.LANCZOS)
        except Exception as e:
            logging.error(f"Lỗi khi tải ảnh bìa: {e}")
            background = create_background_from_folder(WIDTH, HEIGHT)
    else:
        background = create_background_from_folder(WIDTH, HEIGHT)

    base_img = background.convert("RGBA")

    # 2) Vẽ overlay bo góc hồng mờ
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    overlay_height = 460
    rect_y0 = (HEIGHT - overlay_height) // 2
    rect_y1 = rect_y0 + overlay_height
    rect_x0, rect_x1 = 30, WIDTH - 30
    draw_overlay.rounded_rectangle(
        (rect_x0, rect_y0, rect_x1, rect_y1),
        radius=80,
        fill=(128, 128, 128, 150)
    )
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=2))
    base_img.alpha_composite(overlay)
    draw_ribbon_trapezoid_label(base_img, event_text=event_text, group_total_member=right_number)
    draw_ribbon_trapezoid_label_bottom_right(base_img, text="BOT YUMI")


    # 3) Tải avatar, resize, cắt tròn và thêm viền đa sắc.
    def load_avatar(url):
        if not url:
            return Image.new("RGBA", (150, 150), (200, 200, 200, 255))
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            av = Image.open(BytesIO(resp.content)).convert("RGBA")
            return av
        except Exception as e:
            logging.error(f"Lỗi tải avatar: {e}")
            return Image.new("RGBA", (150, 150), (200, 200, 200, 255))

    left_avatar = load_avatar(left_avatar_url)
    right_avatar = load_avatar(right_avatar_url)
    AVATAR_SIZE = 250
    left_avatar = left_avatar.resize((AVATAR_SIZE, AVATAR_SIZE), Image.LANCZOS)
    right_avatar = right_avatar.resize((AVATAR_SIZE, AVATAR_SIZE), Image.LANCZOS)
    left_avatar = make_round_avatar(left_avatar)
    if event_text in ["🚫 BỊ BLOCK KHỎI NHÓM", "🚫 BỊ BLOCK KHỎI C.ĐỒNG"]:
        left_avatar = draw_red_x(left_avatar, thickness=10)
    if event_text in ["🚫 BỊ BLOCK KHỎI NHÓM", "🚫 BỊ BLOCK KHỎI C.ĐỒNG"]:
        banned_path = "banned.png"
        if os.path.exists(banned_path):
            try:
                banned_img = Image.open(banned_path).convert("RGBA")
                banned_img = banned_img.resize((250, 150), Image.LANCZOS)  # Kích thước 150x150 pixel
                banned_pos_x = left_avatar.width - banned_img.width
                banned_pos_y = left_avatar.height - banned_img.height
                left_avatar.alpha_composite(banned_img, (banned_pos_x, banned_pos_y))
            except Exception as e:
                logging.error(f"Lỗi khi dán banned.jpg lên avatar: {e}")    
    left_avatar = add_multicolor_circle_border(left_avatar, MULTICOLOR_GRADIENT, 4)
    right_avatar = make_round_avatar(right_avatar)
    right_avatar = add_multicolor_circle_border(right_avatar, MULTICOLOR_GRADIENT, 4)

    # 4) Paste avatar vào ảnh
    lx = rect_x0 + 70
    ly = (HEIGHT - left_avatar.height) // 2
    base_img.alpha_composite(left_avatar, (lx, ly))
    rx = rect_x1 - right_avatar.width - 70
    ry = (HEIGHT - right_avatar.height) // 2
    base_img.alpha_composite(right_avatar, (rx, ry))

    # 5) Vẽ vòng tròn hiển thị số thành viên trên avatar phải.
    circle_r = 50
    circle_font = get_font("font/ChivoMono-VariableFont_wght.ttf", 40)
    # Tạo vòng tròn với text
    circle_img = Image.new("RGBA", (circle_r * 2, circle_r * 2), (0, 0, 0, 0))
    draw_c = ImageDraw.Draw(circle_img)
    draw_c.ellipse((0, 0, circle_r * 2, circle_r * 2),
                   fill=(85, 0, 255, 250))
    text_bbox = draw_c.textbbox((0, 0), str(right_number), font=circle_font)
    center_x = (text_bbox[0] + text_bbox[2]) / 2
    center_y = (text_bbox[1] + text_bbox[3]) / 2
    tx = circle_r - center_x
    ty = circle_r - center_y
    draw_c.text((tx, ty), str(right_number), font=circle_font, fill=(255, 255, 255))
    # Thêm viền đa sắc với dải màu ngẫu nhiên từ GRADIENT_SETS
    circle_img = add_multicolor_circle_border(circle_img, get_random_gradient(), 4)
    # Dán vòng tròn lên ảnh chính
    base_img.alpha_composite(circle_img, (rx + (AVATAR_SIZE - 2 * circle_r), ry - circle_r - 10))

    # 6) Vẽ các dòng text căn giữa theo overlay.
    if "tham gia" in event_text.lower():
        line1 = f"{member_name}"
    elif "rời" in event_text.lower():
        line1 = f"{member_name}"
    else:
        line1 = f"{member_name}"
    line2 = event_text
    line3 = group_name
    line4 = f"BỞI : {executed_by}"
    line5 = f"⏰ {gio_phut}   📆 {ngay_thang}"

    # Load font chữ và font emoji
    font_title = get_font("font/Tapestry-Regular.ttf", 120)
    font_sub = get_font("font/ChivoMono-VariableFont_wght.ttf", 50)  # Giữ nguyên cho line2
    font_group = get_font("font/Bungee-Regular.ttf", 60)  # Font mới cho line3
    font_small = get_font("font/ChivoMono-VariableFont_wght.ttf", 50)
    emoji_font_title = get_font("font/NotoEmoji-Bold.ttf", 150)
    emoji_font_sub = get_font("font/NotoEmoji-Bold.ttf", 60)
    emoji_font_small = get_font("font/NotoEmoji-Bold.ttf", 50)

    base_draw = ImageDraw.Draw(base_img)
    # In các dòng text với hỗ trợ in emoji
    random_gradients = random.sample(GRADIENT_SETS, 4)
    draw_centered_text_mixed_line(line1, rect_y0 - 0, font_title, emoji_font_title, MULTICOLOR_GRADIENT, base_draw, rect_x0, rect_x1)
    # Tính chiều rộng của tên
    segments = split_text_by_emoji(line1)
    total_width = sum(base_draw.textbbox((0, 0), seg, font=emoji_font_title if is_emoji else font_title)[2] for seg, is_emoji in segments)
    underline_width = total_width + 60  # Dài hơn tên 20px
    underline_y = rect_y0 + 140  # Dưới line1
    underline_thickness = 5
    underline_x0 = (rect_x0 + rect_x1 - underline_width) // 2 + 20
    underline_x1 = underline_x0 + underline_width
    for x in range(int(underline_x0), int(underline_x1)):
        color = get_gradient_color(MULTICOLOR_GRADIENT, (x - underline_x0) / underline_width)
        base_draw.line([(x, underline_y), (x, underline_y + underline_thickness)], fill=color)
    draw_centered_text_mixed_line(line2, rect_y0 + 160, font_sub, emoji_font_sub, random_gradients[0], base_draw, rect_x0, rect_x1)
    draw_centered_text_mixed_line(line3, rect_y0 + 240, font_group, emoji_font_sub, random_gradients[1], base_draw, rect_x0, rect_x1)
    draw_centered_text_mixed_line(line4, rect_y1 - 140, font_small, emoji_font_small, random_gradients[2], base_draw, rect_x0, rect_x1)
    draw_centered_text_mixed_line(line5, rect_y1 - 70, font_small, emoji_font_small, random_gradients[3], base_draw, rect_x0, rect_x1)
    
    # ---- THÊM DÒNG CHỮ NHỎ Ở GÓC DƯỚI PHẢI: "design by Rosy" ----
    red_rect_x0 = 50
    red_rect_y0 = 700
    red_rect_x1 = 1422
    red_rect_y1 = 780
    draw_overlay.rounded_rectangle(
        (red_rect_x0, red_rect_y0, red_rect_x1, red_rect_y1),
        radius=10,
        fill=(255, 0, 0, 100)
    )
    designer_text = "design by Rosy"
    designer_font = get_font("font/ChivoMono-VariableFont_wght.ttf", 30)
    text_bbox = base_draw.textbbox((0, 0), designer_text, font=designer_font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]
    margin = 10
    designer_x = red_rect_x1 - text_w - margin
    designer_y = red_rect_y1 - text_h - margin
    draw_gradient_text(
        base_draw,
        text=designer_text,
        position=(designer_x, designer_y),
        font=designer_font,
        gradient_colors=MULTICOLOR_GRADIENT,
        shadow_offset=(1, 1)
    )
    logo_path = "zalo.png"  # Đường dẫn đến file zalo.png
    if os.path.exists(logo_path):
        try:
            # Tải logo
            logo = Image.open(logo_path).convert("RGBA")
            logo_size = 80  # Kích thước logo (80x80 pixel)
            logo = logo.resize((logo_size, logo_size), Image.LANCZOS)

            # Bo tròn logo
            mask = Image.new("L", (logo_size, logo_size), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, logo_size, logo_size), fill=255)
            round_logo = Image.new("RGBA", (logo_size, logo_size), (0, 0, 0, 0))
            round_logo.paste(logo, (0, 0), mask)

            # Xác định vị trí góc dưới bên trái (đối diện với "design by Rosy")
            logo_x = 50  # Lề trái
            logo_y = 700  # Cách mép dưới (tương ứng với y của khung đỏ)
            base_img.alpha_composite(round_logo, (logo_x, logo_y))
        except Exception as e:
            logging.error(f"Lỗi khi xử lý logo zalo.png: {e}")
    # 7) Thêm viền đa sắc quanh ảnh.
    final_image = add_multicolor_rectangle_border(base_img, MULTICOLOR_GRADIENT, 5)
    final_image = final_image.convert("RGB")
    image_path = "welcome_or_farewell.jpg"
    final_image.save(image_path, quality=90)
    return image_path

def delete_file(file_path):
    """Xóa file nếu tồn tại."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Đã xóa file: {file_path}")
        else:
            print(f"Không tìm thấy file: {file_path}")
    except Exception as e:
        logging.error(f"Lỗi khi xóa file {file_path}: {e}")

# ------------------ HÀM XỬ LÝ SỰ KIỆN NHÓM ------------------
def welcome(self, event_data, event_type, ttl=3600000):
    """
    Hàm xử lý sự kiện nhóm (JOIN, LEAVE, v.v.).
    """
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
                f"💜 Cung cấp Hack Liên quân, Box zalo\n"
                f"📩 Liên hệ: zalo.me/0868084438 \n"
            ),
            "ttl": 3600000
        },
        GroupEventType.LEAVE: {
            "img_type": "LEAVE",
            "msg_func": lambda member: (               
                f"💜 Cung cấp Hack Liên quân, Box zalo\n"
                f"📩 Liên hệ: zalo.me/0868084438 \n"
            ),
            "ttl": 500000
        },
        GroupEventType.REMOVE_MEMBER: {
            "img_type": "REMOVE_MEMBER",
            "msg_func": lambda member: (
                f"💜 Cung cấp Hack Liên quân, Box zalo\n"
                f"📩 Liên hệ: zalo.me/0868084438 \n"
            ),
            "ttl": 500000
        },
        GroupEventType.ADD_ADMIN: {
            "img_type": "ADD_ADMIN",
            "msg_func": lambda member: (
                f"💜 Cung cấp Hack Liên quân, Box zalo\n"
                f"📩 Liên hệ: zalo.me/0868084438 \n"
            ),
            "ttl": 500000
        },
        GroupEventType.REMOVE_ADMIN: {
            "img_type": "REMOVE_ADMIN",
            "msg_func": lambda member: (
                f"💜 Cung cấp Hack Liên quân, Box zalo\n"
                f"📩 Liên hệ: zalo.me/0868084438 \n"
            ),
            "ttl": 500000
        },
        GroupEventType.UPDATE: {
            "img_type": "UPDATE",
            "msg_func": lambda member: (
                f"💜 Cung cấp Hack Liên quân, Box zalo\n"
                f"📩 Liên hệ: zalo.me/0868084438 \n"
            ),
            "ttl": 500000
        }
    }

    if event_type not in event_config:
        return

    config = event_config[event_type]
    event_text_mapping = {
        "JOIN": "✔ ĐƯỢC DUYỆT VÀO NHÓM",
        "LEAVE": "❌ OUT MEMBER",
        "REMOVE_MEMBER": "🚫 BỊ BLOCK KHỎI NHÓM",
        "ADD_ADMIN": "🗝 ĐÃ TRỞ THÀNH ADMIN NHÓM",
        "REMOVE_ADMIN": "🗝 Đã bị cắt chức phó nhóm",
        "UPDATE": "📑 Đã cập nhật nội quy nhóm"
    }
    time_line = datetime.now(timezone(timedelta(hours=7))).strftime("%H:%M:%S %Y-%m-%d")
    dt = datetime.strptime(time_line, "%H:%M:%S %Y-%m-%d")
    gio_phut = dt.strftime("%H:%M")
    ngay_thang = dt.strftime("%d-%m")
    bot_id = "715870970611339054"

    def process_member(member):
        member_name = member['dName']
        member_id = member['id']
        avatar_url = member.get('avatar', '')
        cover_url = None
        if config["img_type"] == "JOIN" and member_id == bot_id:
            print(f"Bỏ qua sự kiện JOIN cho bot với ID: {bot_id}")
            return

        try:
            user_info = self.fetchUserInfo(member['id'])
            cover_url = user_info.changed_profiles[member['id']].cover
            print(f"Link ảnh bìa của {member_name}: {cover_url}")
        except Exception as e:
            logging.error(f"Lỗi khi lấy ảnh bìa của người dùng (id {member['id']}): {e}")

        # Chuẩn hóa event_text và áp dụng thay thế NHÓM/C.ĐỒNG
        event_text = event_text_mapping.get(config["img_type"], "").strip()
        if config["img_type"] == "JOIN" and member_id == event_data['sourceId']:
            event_text = "THAM GIA NHÓM BẰNG LINK".strip()
        # Thay NHÓM thành C.ĐỒNG nếu số thành viên >= 100
        if group_total_member >= 100:
            event_text = event_text.replace("NHÓM", "C.ĐỒNG")

        # Ghi log để kiểm tra
        logging.debug(f"DEBUG: event_text trong welcome: '{event_text}', group_total_member: {group_total_member}")

        image_path = create_welcome_or_farewell_image(
            member_name=member_name,
            left_avatar_url=avatar_url,
            right_avatar_url=group_logo_url,
            right_number=group_total_member,
            group_name=group_name,
            event_text=event_text,
            gio_phut=gio_phut,
            ngay_thang=ngay_thang,
            executed_by=actor_name,
            cover_url=cover_url
        )
        message_text = config["msg_func"](member_name)
        message = Message(text=message_text)
        self.sendLocalImage(
            image_path,
            thread_id,
            ThreadType.GROUP,
            message=message,
            width=1472,
            height=600,
            ttl=config["ttl"]
        )
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
