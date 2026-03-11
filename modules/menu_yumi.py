import os
import time
import random
import math
import logging
import re
import requests
from io import BytesIO
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
from zlapi.models import Message

# ----------------- CẤU HÌNH LOG & ĐƯỜNG DẪN -----------------
logging.basicConfig(
    level=logging.ERROR,
    filename="bot_error.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ----------------- HẰNG SỐ & ẢNH NỀN -----------------
# Dải màu mặc định cho các chức năng khác
MULTICOLOR_GRADIENT = [
    (255, 0, 0), (255, 165, 0), (255, 255, 0),
    (0, 255, 0), (0, 0, 255), (75, 0, 130), (148, 0, 211)
]

# Danh sách các dải màu để dùng ngẫu nhiên cho mỗi dòng text
MULTICOLOR_GRADIENTS = [
    # Dải màu Neon sáng rực – mở rộng thêm các sắc thái sáng
    [(255, 0, 255), (255, 128, 255), (0, 255, 255), (128, 255, 255), (255, 0, 0), (255, 128, 128), (255, 255, 0), (128, 255, 0), (0, 255, 0)],

    # Dải màu cầu vồng rực rỡ – thêm nhiều màu sáng trung gian
    [(255, 0, 0), (255, 85, 0), (255, 165, 0), (255, 210, 0), (255, 255, 0), (200, 255, 0), (0, 128, 0), (0, 200, 100), (255, 105, 180), (255, 50, 200), (0, 0, 255), (50, 50, 255), (75, 0, 130), (110, 0, 200), (148, 0, 211)],

    # Dải màu pastel nhẹ nhàng – thêm nhiều sắc thái sáng
    [(255, 182, 193), (255, 210, 220), (255, 240, 245), (230, 255, 255), (173, 216, 230), (200, 250, 250), (152, 251, 152), (180, 255, 170), (240, 230, 140), (255, 250, 180)],

    # Dải màu nhiệt đới – mang đến sự tươi mát
    [(0, 255, 127), (0, 230, 150), (255, 200, 0), (255, 165, 0), (255, 69, 0), (255, 105, 180)],

    # Dải màu xanh biển sáng – phù hợp với thiết kế mát mẻ
    [(0, 191, 255), (0, 220, 255), (30, 144, 255), (100, 149, 237), (135, 206, 250)],

    # Dải màu Mặt trời lặn – rực rỡ và hoàng hôn ấm áp
    [(255, 94, 77), (255, 160, 122), (255, 99, 71), (255, 215, 0), (255, 255, 0)],

    # Dải màu Xanh lá tươi sáng – thêm sắc độ sáng nhẹ
    [(0, 255, 0), (34, 255, 34), (34, 139, 34), (50, 205, 50), (90, 230, 90), (144, 238, 144), (152, 251, 152), (180, 255, 180)],

    # Dải màu Cam - Đỏ - Hồng ấm áp
    [(255, 140, 0), (255, 99, 71), (255, 69, 0), (220, 20, 60), (255, 20, 147)],

    # Dải màu Xanh nước biển - xanh lam đậm
    [(0, 255, 255), (70, 130, 180), (0, 0, 255), (25, 25, 112)],

    # Dải màu Xanh lá - Xanh dương - Vàng - Hồng
    [(0, 255, 0), (138, 43, 226), (0, 0, 255), (255, 182, 193), (255, 215, 0)],

    # Dải màu Pastel đa sắc
    [(255, 223, 186), (255, 182, 193), (255, 160, 122), (255, 99, 71), (152, 251, 152), (173, 216, 230)],

    # Dải màu ánh sáng thiên đường
    [(176, 196, 222), (135, 206, 250), (70, 130, 180), (25, 25, 112)],

    # Dải màu cầu vồng pastel – tạo cảm giác nhẹ nhàng nhưng vẫn rực rỡ
    [(255, 200, 200), (255, 165, 150), (255, 255, 180), (200, 255, 180), (180, 255, 255), (180, 200, 255), (220, 180, 255)],

    # Dải màu xanh bạc hà & cam sữa – cảm giác tươi mát và nhẹ nhàng
    [(152, 251, 152), (180, 255, 180), (220, 255, 200), (255, 230, 180), (255, 200, 150), (255, 165, 100)],

    # Dải màu hồng & vàng sáng – tạo cảm giác vui tươi, rực rỡ
    [(255, 105, 180), (255, 120, 190), (255, 165, 200), (255, 200, 220), (255, 230, 240), (255, 250, 255)],

    # Dải màu ngọc bích sáng – tinh tế và sáng rõ
    [(0, 255, 127), (100, 255, 150), (150, 255, 180), (200, 255, 210), (220, 255, 230)],

    # Dải màu lễ hội mùa hè – mang đến sự vui vẻ và rực rỡ
    [(255, 0, 0), (255, 69, 0), (255, 140, 0), (255, 215, 0), (0, 255, 127), (0, 255, 255), (30, 144, 255)],

    # Dải màu Ánh sáng Phương Bắc – thêm các sắc độ chuyển tiếp huyền ảo
    [(0, 255, 127), (0, 191, 255), (123, 104, 238), (75, 0, 130)],

    # Dải màu Galaxy – hòa trộn tím, xanh, hồng
    [(75, 0, 130), (138, 43, 226), (148, 0, 211), (255, 20, 147), (255, 105, 180)]
]

# Danh sách màu cho overlay (RGBA)
OVERLAY_COLORS = [
    (255, 255, 255, 200),  # White
    (255, 250, 250, 200),  # Snow
    (240, 255, 255, 200),  # Azure
    (255, 228, 196, 200),  # Bisque
    (255, 218, 185, 200),  # Peach Puff
    (255, 239, 213, 200),  # Papaya Whip
    (255, 222, 173, 200),  # Navajo White
    (255, 250, 205, 200),  # Lemon Chiffon
    (250, 250, 210, 200),  # Light Goldenrod Yellow
    (255, 245, 238, 200),  # Seashell
    (240, 230, 140, 200),  # Khaki
    (230, 230, 250, 200),  # Lavender
    (216, 191, 216, 200),  # Thistle
    (221, 160, 221, 200),  # Plum
    (255, 182, 193, 200),  # Light Pink
    (255, 105, 180, 200),  # Hot Pink
    (255, 160, 122, 200),  # Light Salmon
    (255, 165, 0, 200),    # Orange
    (255, 215, 0, 200),    # Gold
    (173, 255, 47, 200),   # Green Yellow
    (144, 238, 144, 200),  # Light Green
    (152, 251, 152, 200),  # Pale Green
    (127, 255, 212, 200),  # Aquamarine
    (0, 255, 255, 200),    # Cyan
    (135, 206, 250, 200),  # Light Sky Blue
    (176, 224, 230, 200),  # Powder Blue
    (30, 144, 255, 200),   # Dodger Blue
    (100, 149, 237, 200),  # Cornflower Blue
    (238, 130, 238, 200),  # Violet
    (255, 20, 147, 200)    # Deep Pink
]

# Đường dẫn thư mục chứa ảnh nền (nếu có)
BACKGROUND_FOLDER = 'wcmenu_backgrounds'
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
        try:
            bg = Image.open(bg_path).convert("RGB")
            return bg.resize((width, height), Image.LANCZOS)
        except Exception as e:
            logging.error(f"Lỗi khi mở ảnh nền từ {bg_path}: {e}")
    # Nếu không có ảnh hay lỗi, tạo nền màu xanh nhạt.
    return Image.new("RGB", (width, height), (130, 190, 255))

# ----------------- HÀM HỖ TRỢ ẢNH -----------------
_FONT_CACHE = {}
def get_font(font_path, size):
    """Load font (cache lại) để không load nhiều lần."""
    key = (font_path, size)
    if key not in _FONT_CACHE:
        try:
            _FONT_CACHE[key] = ImageFont.truetype(font_path, size)
        except Exception as e:
            logging.error(f"Lỗi load font {font_path} với size {size}: {e}")
            _FONT_CACHE[key] = ImageFont.load_default()
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

# --------------------- HÀM HIỆU ỨNG CHỮ VỚI GRADIENT ---------------------
emoji_pattern = re.compile(
    "("
    "[\U0001F1E6-\U0001F1FF]{2}|"     # Flags
    "[\U0001F600-\U0001F64F]|"        # Emoticons
    "[\U0001F300-\U0001F5FF]|"        # Symbols & pictographs
    "[\U0001F680-\U0001F6FF]|"        # Transport & map symbols
    "[\U0001F700-\U0001F77F]|"
    "[\U0001F780-\U0001F7FF]|"
    "[\U0001F800-\U0001F8FF]|"
    "[\U0001F900-\U0001F9FF]|"
    "[\U0001FA00-\U0001FA6F]|"
    "[\U0001FA70-\U0001FAFF]|"
    "[\u2600-\u26FF]|"
    "[\u2700-\u27BF]|"
    "[\u2300-\u23FF]|"
    "[\u2B00-\u2BFF]|"
    "\d\uFE0F?\u20E3|"              
    "[#*]\uFE0F?\u20E3|"            
    "[\U00013000-\U0001342F]"
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

def get_mixed_text_width(draw, text, normal_font, emoji_font):
    """
    Tính toán tổng chiều rộng của text hỗn hợp (chữ thường và emoji).
    """
    segments = split_text_by_emoji(text)
    total_width = 0
    for seg, is_emoji in segments:
        font = emoji_font if is_emoji else normal_font
        seg_bbox = draw.textbbox((0, 0), seg, font=font)
        seg_width = seg_bbox[2] - seg_bbox[0]
        total_width += seg_width
    return total_width

def draw_mixed_gradient_text(draw, text, position, normal_font, emoji_font, gradient_colors, shadow_offset=(4, 4)):
    """
    Vẽ text hỗn hợp với hiệu ứng gradient:
      - Dùng normal_font cho ký tự thường.
      - Dùng emoji_font cho emoji.
    """
    if not text:
        return
    segments = split_text_by_emoji(text)
    total_chars = sum(len(seg) for seg, _ in segments)
    color_list = []
    num_segments = len(gradient_colors) - 1
    steps_per_segment = (total_chars // 4) + 1 if total_chars > 0 else 1
    for i in range(num_segments):
        for j in range(steps_per_segment):
            if len(color_list) < total_chars:
                ratio = j / steps_per_segment
                c1, c2 = gradient_colors[i], gradient_colors[i + 1]
                interpolated = (
                    int(c1[0] * (1 - ratio) + c2[0] * ratio),
                    int(c1[1] * (1 - ratio) + c2[1] * ratio),
                    int(c1[2] * (1 - ratio) + c2[2] * ratio)
                )
                color_list.append(interpolated)
    while len(color_list) < total_chars:
        color_list.append(gradient_colors[-1])

    x, y = position
    shadow_color = (0, 0, 0)
    char_index = 0
    for seg, is_emoji in segments:
        current_font = emoji_font if is_emoji else normal_font
        for ch in seg:
            ch_color = color_list[char_index]
            draw.text((x + shadow_offset[0], y + shadow_offset[1]), ch, font=current_font, fill=shadow_color)
            draw.text((x, y), ch, font=current_font, fill=ch_color)
            bbox = draw.textbbox((0, 0), ch, font=current_font)
            char_width = bbox[2] - bbox[0]
            x += char_width
            char_index += 1

# ----------------- HÀM TẠO ẢNH MENU CHÀO MỪNG -----------------
def create_menu_welcome_image(user_name, user_avatar_url, user_cover_url, bot_avatar_url, menu_text):
    """
    Tạo ảnh chào mừng động cho lệnh menu với thông tin người dùng và nội dung menu.
    Sử dụng ảnh zalouser.png làm nền thay vì ảnh bìa người dùng.
    """
    WIDTH, HEIGHT = 1472, 800

    # 1) Tạo nền: Sử dụng ảnh zalouser.png
    try:
        background = Image.open("zaloadmin.png").convert("RGB")
        background = background.resize((WIDTH, HEIGHT), Image.LANCZOS)
    except Exception as e:
        logging.error(f"Lỗi khi mở ảnh zaloadmin.jpg: {e}")
        # Nếu không mở được zalouser.png, dùng nền từ folder hoặc nền mặc định
        background = create_background_from_folder(WIDTH, HEIGHT)
    base_img = background.convert("RGBA")

    # 2) Vẽ overlay với màu được chọn ngẫu nhiên từ OVERLAY_COLORS
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    overlay_height = 460
    rect_y0 = (HEIGHT - overlay_height) // 2
    rect_y1 = rect_y0 + overlay_height
    rect_x0, rect_x1 = 30, WIDTH - 30
    overlay_color = random.choice(OVERLAY_COLORS)
    draw_overlay.rounded_rectangle(
        (rect_x0, rect_y0, rect_x1, rect_y1),
        radius=50,
        fill=overlay_color
    )
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=2))
    base_img.alpha_composite(overlay)

    # 3) Xử lý avatar người dùng: tải, resize, cắt tròn và thêm viền đa sắc.
    def load_avatar(url):
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            av = Image.open(BytesIO(resp.content)).convert("RGBA")
            return av
        except Exception as e:
            logging.error(f"Lỗi tải avatar: {e}")
            return Image.new("RGBA", (150, 150), (200, 200, 200, 255))

    AVATAR_SIZE = 250
    user_avatar = load_avatar(user_avatar_url)
    user_avatar = user_avatar.resize((AVATAR_SIZE, AVATAR_SIZE), Image.LANCZOS)
    user_avatar = make_round_avatar(user_avatar)
    user_avatar = add_multicolor_circle_border(user_avatar, MULTICOLOR_GRADIENT, 4)

    # 4) Paste avatar người dùng lên ảnh (vị trí bên trái overlay)
    ax = rect_x0 + 70
    ay = (HEIGHT - user_avatar.height) // 2
    base_img.alpha_composite(user_avatar, (ax, ay))

    # 5) Xử lý và paste avatar của bot (vị trí bên phải overlay)
    if bot_avatar_url:
        bot_avatar = load_avatar(bot_avatar_url)
        bot_avatar = bot_avatar.resize((AVATAR_SIZE, AVATAR_SIZE), Image.LANCZOS)
        bot_avatar = make_round_avatar(bot_avatar)
        bot_avatar = add_multicolor_circle_border(bot_avatar, MULTICOLOR_GRADIENT, 4)
        bx = rect_x1 - AVATAR_SIZE - 70
        by = (HEIGHT - bot_avatar.height) // 2
        base_img.alpha_composite(bot_avatar, (bx, by))

    # 6) Vẽ tên người dùng bên trong overlay với hiệu ứng bóng chữ (shadow_offset=(4,4))
    base_draw = ImageDraw.Draw(base_img)
    emoji_font_title = get_font("font/NotoEmoji-Bold.ttf", 100)
    emoji_font_60 = get_font("font/NotoEmoji-Bold.ttf", 60)
    emoji_font_50 = get_font("font/NotoEmoji-Bold.ttf", 50)
    emoji_font_45 = get_font("font/NotoEmoji-Bold.ttf", 45)

    padding_top = 20  # khoảng cách từ mép trên overlay
    font_title = get_font("font/Tapestry-Regular.ttf", 100)
    name_text = f"Chào {user_name}!"
    name_width = get_mixed_text_width(base_draw, name_text, font_title, emoji_font_title)
    x_name = rect_x0 + (rect_x1 - rect_x0 - name_width) // 2
    y_name = rect_y0 + padding_top
    gradient_for_name = MULTICOLOR_GRADIENT
    draw_mixed_gradient_text(
        base_draw, name_text, (x_name, y_name), font_title, emoji_font_title,
        gradient_for_name, shadow_offset=(4, 4)
    )
    bbox_name = base_draw.textbbox((0, 0), name_text, font=font_title)  # For height only
    name_h = bbox_name[3] - bbox_name[1]

    # 7) Vẽ các dòng text tùy chỉnh bên trong overlay với bóng chữ giống tên (shadow_offset=(4,4))
    padding_between = 20
    start_y_custom = y_name + name_h + padding_between

    custom_texts = [
        {
            "text": "WELCOME TO MENU",
            "normal_font": get_font("font/Tapestry-Regular.ttf", 60),
            "emoji_font": emoji_font_60
        },
        {
            "text": "NGƯỜI DÙNG",
            "normal_font": get_font("font/ChivoMono-VariableFont_wght.ttf", 50),
            "emoji_font": emoji_font_50
        },
        {
            "text": "Xin mời chọn lệnh",
            "normal_font": get_font("font/ChivoMono-VariableFont_wght.ttf", 45),
            "emoji_font": emoji_font_45
        },
        {
            "text": "Sử dụng help + tên lệnh để xem mô tả lệnh và cách sử dụng ",
            "normal_font": get_font("font/ChivoMono-VariableFont_wght.ttf", 45),
            "emoji_font": emoji_font_45
        }
    ]

    line_heights = []
    for item in custom_texts:
        bbox = base_draw.textbbox((0, 0), item["text"], font=item["normal_font"])
        height_line = bbox[3] - bbox[1]
        line_heights.append(height_line)
    spacing = 40
    total_text_height = sum(line_heights) + spacing * (len(custom_texts) - 1)
    max_available_height = rect_y1 - start_y_custom - 20

    if total_text_height > max_available_height:
        spacing = max(5, (max_available_height - sum(line_heights)) // (len(custom_texts) - 1))

    if len(custom_texts) <= len(MULTICOLOR_GRADIENTS):
        gradients_for_text = random.sample(MULTICOLOR_GRADIENTS, len(custom_texts))
    else:
        gradients_for_text = [random.choice(MULTICOLOR_GRADIENTS) for _ in range(len(custom_texts))]

    current_y = start_y_custom
    for i, item in enumerate(custom_texts):
        text = item["text"]
        normal_font = item["normal_font"]
        emoji_font = item["emoji_font"]
        text_width = get_mixed_text_width(base_draw, text, normal_font, emoji_font)
        x_text = rect_x0 + (rect_x1 - rect_x0 - text_width) // 2
        draw_mixed_gradient_text(
            base_draw, text, (x_text, current_y), normal_font, emoji_font,
            gradients_for_text[i], shadow_offset=(4, 4)
        )
        current_y += line_heights[i] + spacing

    # 8) Thêm viền đa sắc quanh ảnh
    final_image = add_multicolor_rectangle_border(base_img, MULTICOLOR_GRADIENT, 10)
    final_image = final_image.convert("RGB")
    image_path = "menu_welcome.jpg"
    final_image.save(image_path, quality=90)
    return image_path

def delete_file(file_path):
    """Xóa file nếu tồn tại."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
        else:
            logging.error(f"Không tìm thấy file: {file_path}")
    except Exception as e:
        logging.error(f"Lỗi khi xóa file {file_path}: {e}")

def split_message(menu_text, max_length=1600):
    """
    Chia tin nhắn thành nhiều phần nếu vượt quá max_length ký tự.
    Trả về danh sách các phần tin nhắn.
    """
    lines = menu_text.splitlines()
    parts = []
    current_part = ""
    
    for line in lines:
        # Nếu thêm dòng này vào phần hiện tại mà vượt quá max_length
        if len(current_part) + len(line) + 1 > max_length:
            if current_part:  # Nếu đã có nội dung trong current_part, thêm vào parts
                parts.append(current_part.strip())
            current_part = line  # Bắt đầu phần mới với dòng hiện tại
        else:
            # Thêm dòng vào phần hiện tại với ký tự xuống dòng
            current_part += line + "\n"
    
    # Thêm phần cuối cùng nếu còn nội dung
    if current_part:
        parts.append(current_part.strip())
    
    return parts
# ----------------- HÀM XỬ LÝ LỆNH MENU -----------------
def handle_menu_command(message, message_object, thread_id, thread_type, author_id, client):
    """
    Xử lý lệnh menu:
      - Gửi phản hồi bằng emoji "✅" để xác nhận lệnh.
      - Lấy thông tin người dùng (tên, avatar, ảnh bìa) và thông tin của bot.
      - Tạo ảnh menu động với thông tin người dùng, thông tin bot và nội dung menu.
      - Gửi ảnh kèm theo tin nhắn menu.
    """
    menu_message = """
════ 1️⃣ 👥 QUẢN LÝ NHÓM (ADMIN) ════
➜ 👥 manager — Danh sách lệnh admin
➜ 👥 listadmin — Danh sách admin nhóm
➜ 👥 add [@user] — Thêm admin bot
➜ 👥 remove [@user] — Xoá admin bot
➜ 👥 listgroups — Danh sách nhóm bot tham gia
➜ 👥 scangroups — Quét thành viên nhóm
➜ 👥 join — Tham gia nhóm qua link
➜ 👥 leave — Bot rời nhóm
➜ 🔗 changelink — Đổi link nhóm
➜ ⚙️ settinggroup — Sửa cài đặt nhóm
➜ ⚙️ prefix — Xem/đổi prefix
➜ ⚙️ setcmd — Cài đặt lệnh nhóm

════ 2️⃣ 🚫 KIỂM SOÁT VÀ BẢO VỆ NHÓM (ADMIN) ════
➜ 🚫 mute / unmute [@user] — Mute / Gỡ mute
➜ 🚫 listmute — Danh sách bị mute
➜ 🚫 kick [@user] — Kick thành viên
➜ 🚫 block / unblock [@user] — Chặn / Gỡ chặn
➜ 🚫 ban / unban — Khoá / Mở khoá người chơi
➜ 🚫 blockbot / unblockbot — Chặn / Gỡ chặn dùng bot
➜ 🚫 whitelist — Quản lý whitelist
➜ 🚫 antibadword on/off — Lọc từ tục
➜ 🚫 antilink on/off — Chặn link
➜ 🚫 antispam on/off — Chống spam
➜ 🚫 antinude on/off — Chặn ảnh nhạy cảm
➜ 🚫 antiundo on/off — Chống thu hồi
➜ 🚫 onlytext on/off — Chỉ cho nhắn văn bản

════ 3️⃣ 👋 TƯƠNG TÁC NHÓM (ADMIN) ════
➜ 👋 welcome / bye on/off — Bật/tắt chào và tạm biệt
➜ 👋 approve on/off — Tự động duyệt thành viên
➜ 📢 tagall / all [text] — Tag / Nhắn toàn nhóm
➜ 📢 scold — Chửi ngẫu nhiên
➜ 📢 sendp — Gửi tin nhắn riêng
➜ 📢 todo / sendtask — Giao việc tự động

════ 4️⃣ 🗑️ QUẢN LÝ TIN NHẮN (ADMIN) ════
➜ 🗑️ deletemessage — Xoá nhiều tin nhắn
➜ 🗑️ undo — Thu hồi tin nhắn bot
➜ 🤖 reply on/off — Bật/tắt auto-reply
➜ 📚 learn / learnnow — Học trả lời mới
➜ 📚 unlearn — Huỷ học

════ 5️⃣ 🔑 TÀI NGUYÊN & QUYỀN HẠN (ADMIN) ════
➜ 🔑 keygold / keysilver on/off — Gán key đặc biệt
➜ 🔑 unkey — Xoá key
➜ 💰 buff — Tặng tiền người chơi
➜ 📂 downloadresource — Tải file lên resource
➜ 📂 deleteresource — Xoá file resource
➜ ⚙️ alias — Quản lý alias lệnh

════ 6️⃣ 🤖 CẤU HÌNH BOT (ADMIN) ════
➜ 🤖 bot on/off — Bật/tắt bot
➜ 🎮 gameactive — Bật xử lý game
➜ ℹ️ detail — Thông tin bot
➜ ⚙️ prefix — Đổi tiền tố lệnh
➜ 🛠️ settinggroup — Cài đặt nhóm

════ 7️⃣ 🤖 TRÒ CHUYỆN VỚI AI ════
➜ 🤖 chat [nội dung] — Chat với bot
➜ 🤖 simsimi — Chat với Simsimi
➜ 🤖 gemini — Hỏi Gemini AI
➜ 🤖 gpt — Hỏi ChatGPT

════ 8️⃣ 🔍 TÌM KIẾM & MEDIA ════
➜ 🔍 google — Tìm kiếm Google
➜ 🖼️ image / pinterest — Tìm ảnh
➜ 🖼️ girl / boy / cosplay / anime — Gửi ảnh ngẫu nhiên
➜ 🎥 vdgirl / vdsexy / vdcos / vdanime / vdchill — Video ngẫu nhiên
➜ 🎥 tiktok / youtube / capcut — Tìm video
➜ 📥 download — Tải video đa nền tảng
➜ 🎙️ getvoice — Trích xuất giọng
➜ 🎵 zingmp3 / soundcloud / nhaccuatui — Tải nhạc
➜ 🗣️ voice — Chuyển văn bản thành giọng
➜ 🎞️ gif — Gửi ảnh động GIF
➜ 🔗 getlink — Trích link từ reply

════ 9️⃣ 🎮 TRÒ CHƠI & QUẢN LÝ GAME ════
➜ 🎮 game — Danh sách game
➜ 🎮 nongtrai / baucua / taixiu / keobuabao — Minigame
➜ 🎮 vietlott655 / doanso / noitu / doantu — Đố vui
➜ 🎮 login / dangky / logout — Quản lý tài khoản game
➜ 🎮 mycard / mybag / daily / rank — Xem thông tin
➜ 💰 nap / rut / bank — Giao dịch

════ 🔟 ℹ️ THÔNG TIN & TIỆN ÍCH ════
➜ ℹ️ info — Thông tin tài khoản
➜ ℹ️ card — Tạo danh thiếp
➜ 📊 speedtest — Kiểm tra mạng
➜ 🏆 topchat — Xếp hạng tương tác
➜ 🌡️ thoitiet — Xem thời tiết
➜ 📜 phatnguoi — Tra cứu phạt nguội
➜ 😂 truyencuoi / 🔮 tarrot — Giải trí
➜ 📷 poststatus — Ảnh trạng thái
➜ 🔲 createqr / scanqr — Tạo & quét QR
➜ 🌐 dich — Dịch văn bản
➜ 💳 qrbank — Tạo QR chuyển khoản

════ 1️⃣1️⃣ 🎨 STICKER & TUỲ CHỈNH ════
➜ 🎨 sticker — Ảnh thành sticker
➜ 🎨 stickercustom — Gửi sticker custom

════ 1️⃣2️⃣ 🧰 KHÁC ════
➜ ❓ help — Hướng dẫn sử dụng
➜ 📁 alias — Quản lý lệnh bí danh
"""



    # Gửi phản hồi emoji "✅" xác nhận đã nhận lệnh
    action = "✅ "
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    # Lấy thông tin người dùng từ author_id
    try:
        user_info = client.fetchUserInfo(author_id)
        user_name = user_info.changed_profiles[author_id].zaloName
        user_avatar_url = user_info.changed_profiles[author_id].avatar
        user_cover_url = user_info.changed_profiles[author_id].cover
    except Exception as e:
        logging.error(f"Lỗi khi lấy thông tin người dùng: {e}")
        user_name = "Người dùng"
        user_avatar_url = ""
        user_cover_url = ""

    # Lấy thông tin của bot (avatar của bot) với ID đã biết
    try:
        bot_uid = "715870970611339054"
        bot_info = client.fetchUserInfo(bot_uid)
        bot_avatar_url = bot_info.changed_profiles[bot_uid].avatar
    except Exception as e:
        logging.error(f"Lỗi khi lấy thông tin bot: {e}")
        bot_avatar_url = ""

    # Chia tin nhắn thành nhiều phần nếu quá dài (max_length = 2000 ký tự)
    message_parts = split_message(menu_message, max_length=1600)
    
    # Tạo ảnh menu động với thông tin người dùng, thông tin bot và nội dung menu
    image_path = create_menu_welcome_image(user_name, user_avatar_url, user_cover_url, bot_avatar_url, menu_message)

    # Gửi từng phần tin nhắn
    for i, part in enumerate(message_parts):
        if i == 0:
            # Phần đầu tiên: gửi kèm ảnh
            client.sendLocalImage(
                image_path,
                thread_id=thread_id,
                thread_type=thread_type,
                message=Message(text=part),
                ttl=600000,  # thời gian tồn tại của tin nhắn (ms)
                width=1472,
                height=800
            )
        else:
            # Các phần tiếp theo: chỉ gửi văn bản
            client.sendMessage(
                Message(text=part),
                thread_id=thread_id,
                thread_type=thread_type,
                ttl=600000
            )
        # Thêm khoảng dừng nhỏ giữa các tin nhắn để tránh gửi quá nhanh
        time.sleep(0.5)

    # Xóa file ảnh tạm sau khi gửi
    delete_file(image_path)

# ----------------- TRẢ VỀ DANH SÁCH LỆNH MODULE -----------------
def get_mitaizl():
    """
    Trả về dictionary chứa các lệnh của module.
    """
    return {
        'menu.lina': handle_menu_command
    }