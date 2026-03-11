import os
import time
import random
import math
import re
import requests
import json
from io import BytesIO
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
from zlapi.models import Message
import colorsys
import glob
import base64

# ----------------- HẰNG SỐ & DẢI MÀU -----------------
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

# Đường dẫn thư mục chứa ảnh nền
BACKGROUND_FOLDER = 'Resource/background/'

def BackgroundGetting():
    files = glob.glob(BACKGROUND_FOLDER + "*.jpg") + glob.glob(BACKGROUND_FOLDER + "*.png") + glob.glob(BACKGROUND_FOLDER + "*.jpeg")
    if not files:
        return None
    chosen = random.choice(files)
    try:
        return Image.open(chosen).convert("RGB")
    except:
        return None

# ----------------- HÀM HỖ TRỢ ẢNH -----------------
_FONT_CACHE = {}
def get_font(font_path, size):
    """Load font (cache lại) để không load nhiều lần."""
    key = (font_path, size)
    if key not in _FONT_CACHE:
        try:
            _FONT_CACHE[key] = ImageFont.truetype(font_path, size)
        except:
            _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]

def FetchImage(url):
    """Tải ảnh từ URL hoặc base64."""
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

def Dominant(image):
    """Tính màu chủ đạo của ảnh."""
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
    except:
        return (0, 0, 0)

def RandomContrast(Base):
    """Tạo màu tương phản ngẫu nhiên dựa trên màu nền."""
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

def get_random_gradient():
    """Chọn ngẫu nhiên một dải màu từ GRADIENT_SETS."""
    return random.choice(GRADIENT_SETS)

# --------------------- HÀM HIỆU ỨNG CHỮ VỚI GRADIENT ---------------------
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
    """Tách văn bản thành danh sách các tuple (segment, is_emoji)."""
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
    """Vẽ văn bản hỗn hợp với gradient cho chữ thường và emoji."""
    if not text:
        return
    try:
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
    except:
        pass

def DrawPillowBase1(draw, position, text, font, fill, shadow_offset=(4, 4), shadow_fill=(0, 0, 0, 150)):
    """Vẽ văn bản với bóng đổ."""
    try:
        x, y = position
        draw.text((x + shadow_offset[0], y + shadow_offset[1]), text, font=font, fill=shadow_fill)
        draw.text((x, y), text, font=font, fill=fill)
    except:
        pass

# ----------------- HÀM TẢI DỮ LIỆU MENU TỪ JSON -----------------
def load_menu_data():
    """Đọc dữ liệu menu từ tệp JSON."""
    try:
        with open("menu_data.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {
            "shinhelp": {
                "commands": ["Lỗi: Không đọc được shinhelp!"],
                "total": 0
            }
        }

# ----------------- HÀM TẠO ẢNH MENU CHÀO MỪNG -----------------
def create_menu_welcome_image(user_name, user_avatar_url, user_cover_url, bot_avatar_url, menu_text, menu_name, total_commands):
    """
    Tạo ảnh menu chào mừng với thông số đồ họa giống hoàn toàn menu.py.
    """
    SIZE = (3000, 880)
    FINAL_SIZE = (1500, 460)

    # 1) Tạo nền ảnh
    try:
        if user_cover_url and user_cover_url != "https://cover-talk.zadn.vn/default":
            bg_image = FetchImage(user_cover_url)
            if bg_image:
                bg_image = bg_image.resize(SIZE, Image.Resampling.LANCZOS)
                bg_image = bg_image.filter(ImageFilter.GaussianBlur(radius=20))
            else:
                bg_image = BackgroundGetting()
        else:
            bg_image = BackgroundGetting()
        if not bg_image:
            bg_image = Image.new("RGB", SIZE, (130, 190, 255))
        bg_image = bg_image.convert("RGBA")
    except:
        bg_image = Image.new("RGB", SIZE, (130, 190, 255)).convert("RGBA")

    # 2) Tạo lớp phủ với hình chữ nhật bo góc
    try:
        overlay = Image.new("RGBA", SIZE, (0, 0, 0, 0))
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
        box_x2, box_y2 = SIZE[0] - 60, SIZE[1] - 80
        draw.rounded_rectangle([(box_x1, box_y1), (box_x2, box_y2)], radius=100, fill=box_color)
    except:
        overlay = Image.new("RGBA", SIZE, (0, 0, 0, 0))

    # 3) Load font
    font_top_path = "font/5.otf"
    font_emoji_path = "font/NotoEmoji-Bold.ttf"
    try:
        font_text_large = ImageFont.truetype(font_top_path, 120)
        font_text_big = ImageFont.truetype(font_top_path, 110)
        font_text_small = ImageFont.truetype(font_top_path, 105)
        font_time = ImageFont.truetype(font_top_path, 65)
        font_icon = ImageFont.truetype(font_emoji_path, 65)
    except:
        font_text_large = font_text_big = font_text_small = font_time = font_icon = ImageFont.load_default()

    # 4) Chuẩn bị văn bản
    try:
        time_line = datetime.now(timezone(timedelta(hours=7))).strftime("%H:%M:%S %Y-%m-%d")
        dt = datetime.strptime(time_line, "%H:%M:%S %Y-%m-%d")
        gio_phut = dt.strftime("%H:%M")
        ngay_thang = dt.strftime("%d-%m")
        text_lines = [
            f"Chào {user_name.upper()}!",
            "Welcome to bot Shinn",
            f"Menu {menu_name.title()}",  # Dùng menu_name động
            "Xin mời chọn lệnh",
            f"TỔNG SỐ LỆNH: {total_commands}"  # Dùng total_commands động
        ]
        text_fonts = [font_text_large, font_text_big, font_text_small, font_text_small, font_time]
        emoji_fonts = [font_icon, font_icon, font_icon, font_icon, font_icon]
        random_gradients = random.sample(GRADIENT_SETS, 3)
        text_colors = [
            MULTICOLOR_GRADIENT,  # dòng 1
            random_gradients[0],  # dòng 2
            MULTICOLOR_GRADIENT,  # dòng 3
            random_gradients[1],  # dòng 4
            random_gradients[2]   # dòng 5
        ]
    except:
        text_lines = ["Chào!", "Welcome to bot Shinn", f"Menu {menu_name.title()}", "Xin mời chọn lệnh", f"TỔNG SỐ LỆNH: {total_commands}"]
        text_fonts = [font_text_large, font_text_big, font_text_small, font_text_small, font_time]
        emoji_fonts = [font_icon, font_icon, font_icon, font_icon, font_icon]
        text_colors = [MULTICOLOR_GRADIENT, MULTICOLOR_GRADIENT, MULTICOLOR_GRADIENT, MULTICOLOR_GRADIENT, MULTICOLOR_GRADIENT]

    # 5) Vẽ văn bản với gradient và hỗ trợ emoji
    try:
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
                draw_mixed_gradient_text(draw, truncated_line, (text_x, text_y), normal_font=font, emoji_font=emoji_font, gradient_colors=colors, shadow_offset=(2, 2))
    except:
        pass

    # 6) Xử lý avatar
    try:
        avatar_size = 430
        center_y = (box_y1 + box_y2) // 2 + 60
        left_avatar_x = box_x1 + 50
        right_avatar_x = box_x2 - 460

        def load_avatar(url):
            if not url:
                return Image.new("RGBA", (avatar_size, avatar_size), (200, 200, 200, 255))
            try:
                img = FetchImage(url)
                if img:
                    img = img.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS).convert("RGBA")
                    return img
                return Image.new("RGBA", (avatar_size, avatar_size), (200, 200, 200, 255))
            except:
                return Image.new("RGBA", (avatar_size, avatar_size), (200, 200, 200, 255))

        user_avatar = load_avatar(user_avatar_url)
        bot_avatar = load_avatar(bot_avatar_url)

        for avatar, x in [(user_avatar, left_avatar_x), (bot_avatar, right_avatar_x)]:
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
    except:
        pass

    # 7) Vẽ logo và chữ "design by Minh Vũ Shinn Cte"
    try:
        logo_path = "zalo.png"
        if os.path.exists(logo_path):
            logo = Image.open(logo_path).convert("RGBA")
            logo_size = 80
            logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
            mask = Image.new("L", (logo_size, logo_size), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, logo_size, logo_size), fill=255)
            round_logo = Image.new("RGBA", (logo_size, logo_size), (0, 0, 0, 0))
            round_logo.paste(logo, (0, 0), mask)
            logo_x = box_x1 + 50
            logo_y = SIZE[1] - logo_size - 5
            overlay.paste(round_logo, (logo_x, logo_y), round_logo)

        designer_text = "design by Minh Vũ Shinn Cte"
        designer_font = ImageFont.truetype(font_top_path, 65)
        text_bbox = draw.textbbox((0, 0), designer_text, font=designer_font)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]
        designer_x = box_x2 - text_w - 20
        designer_y = SIZE[1] - text_h - 25
        draw_mixed_gradient_text(
            draw,
            text=designer_text,
            position=(designer_x, designer_y),
            normal_font=designer_font,
            emoji_font=font_icon,
            gradient_colors=get_random_gradient(),
            shadow_offset=(2, 2)
        )
    except:
        pass

    # 8) Vẽ thời gian
    try:
        left_info = f"⏰ {gio_phut}   📆 {ngay_thang}"
        left_font = ImageFont.truetype(font_top_path, 65)
        text_bbox = draw.textbbox((0, 0), left_info, font=left_font)
        text_h = text_bbox[3] - text_bbox[1]
        left_x = box_x1 + 150
        left_y = SIZE[1] - text_h - 5
        draw_mixed_gradient_text(
            draw,
            text=left_info,
            position=(left_x, left_y),
            normal_font=left_font,
            emoji_font=font_icon,
            gradient_colors=MULTICOLOR_GRADIENT,
            shadow_offset=(2, 2)
        )
    except:
        pass

    # 9) Gộp và lưu ảnh
    try:
        final_image = Image.alpha_composite(bg_image, overlay).resize(FINAL_SIZE, Image.Resampling.LANCZOS).convert("RGB")
        image_path = "menu_welcome.jpg"
        final_image.save(image_path, quality=95)
        return image_path
    except:
        return None

def delete_file(file_path):
    """Xóa file nếu tồn tại."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except:
        pass

def get_all_module_commands():
    """Lấy tất cả command từ thư mục modules"""
    commands = []

    try:
        files = glob.glob("modules/*.py")

        for file in files:

            name = os.path.basename(file)[:-3]

            if name == "shinhelp":
                continue

            try:
                module = __import__(f"modules.{name}", fromlist=["*"])

                if hasattr(module, "get_mitaizl"):

                    data = module.get_mitaizl()

                    if isinstance(data, dict):

                        for cmd in data.keys():
                            commands.append(cmd)

            except:
                continue

    except:
        pass

    return sorted(list(set(commands)))
    


# ----------------- HÀM XỬ LÝ LỆNH MENU -----------------
def handle_menu_command(message, message_object, thread_id, thread_type, author_id, client):

    action = message.lower().strip().split()

    page = 1
    if len(action) >= 2 and action[1].isdigit():
        page = int(action[1])

    menu_data = load_menu_data()

    # =========================
    # TRANG 1 (MENU JSON)
    # =========================
    if page == 1:

        menu_key = "shinhelp"
        menu_name = "tổng hợp"
        total_commands = menu_data.get("shinhelp", {}).get("total", 0)
        menu_commands = menu_data.get("shinhelp", {}).get("commands", ["Không có lệnh!"])

        menu_commands_lines = "\n".join([f"➜ {cmd}" for cmd in menu_commands])

        menu_message = (
            f"═════════════════════\n"
            f"📜 MENU CHÍNH\n"
            f"{menu_commands_lines}\n"
            f"═════════════════════\n"
            f"📄 Trang 1\n"
            f"👉 dùng: shinhelp 2 để xem all lệnh"
        )

    # =========================
    # TRANG 2+ (ALL MODULES)
    # =========================
    else:

        all_commands = get_all_module_commands()

        pages = paginate_list(all_commands, 20)

        max_page = len(pages)

        if page - 2 >= max_page:
            page = 2

        commands_page = pages[page - 2]

        cmd_lines = "\n".join([f"➜ {cmd}" for cmd in commands_page])

        menu_message = (
            f"═════════════════════\n"
            f"📜 MENU ALL COMMAND\n"
            f"{cmd_lines}\n"
            f"═════════════════════\n"
            f"📄 Trang {page}/{max_page+1}\n"
            f"👉 dùng: shinhelp {page+1}"
        )

        menu_name = "all"
        total_commands = len(all_commands)

    # =========================
    # REACTION
    # =========================
    try:
        client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
    except:
        pass

    # =========================
    # USER INFO
    # =========================
    try:
        user_info = client.fetchUserInfo(author_id)
        user_name = user_info.changed_profiles[author_id].zaloName
        user_avatar_url = user_info.changed_profiles[author_id].avatar
        user_cover_url = user_info.changed_profiles[author_id].cover
    except:
        user_name = "Người dùng"
        user_avatar_url = ""
        user_cover_url = ""

    # =========================
    # BOT INFO
    # =========================
    try:
        bot_uid = "715870970611339054"
        bot_info = client.fetchUserInfo(bot_uid)
        bot_avatar_url = bot_info.changed_profiles[bot_uid].avatar
    except:
        bot_avatar_url = ""

    # =========================
    # TẠO ẢNH MENU
    # =========================
    try:
        image_path = create_menu_welcome_image(
            user_name,
            user_avatar_url,
            user_cover_url,
            bot_avatar_url,
            menu_message,
            menu_name,
            total_commands
        )
    except:
        image_path = None

    # =========================
    # SEND IMAGE
    # =========================
    try:
        if image_path:

            client.sendLocalImage(
                image_path,
                thread_id=thread_id,
                thread_type=thread_type,
                message=Message(text=menu_message),
                ttl=120000,
                width=1500,
                height=460
            )

    except:
        pass

    delete_file(image_path)

# ----------------- TRẢ VỀ DANH SÁCH LỆNH MODULE -----------------
def get_mitaizl():
    """
    Trả về dictionary chứa các lệnh của module.
    """
    return {
        'shinhelp': handle_menu_command
    }