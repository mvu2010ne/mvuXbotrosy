import os
import random
import math
import requests
import re
import logging
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import speedtest
from datetime import datetime, timezone, timedelta
import colorsys

# Thiết lập logging
logging.basicConfig(
    filename="bot_net_error.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ------------------ MÔ TẢ TẬP LỆNH ------------------
des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Tạo hình ảnh thông tin tốc độ mạng với phong cách giống bot.sys, sử dụng cùng màu sắc, font chữ và overlay",
    'tính năng': [
        "⚡ Kiểm tra tốc độ tải xuống và tải lên của mạng.",
        "🔍 Hiển thị thông tin ping và server tốt nhất.",
        "🎨 Tạo hình ảnh với nền ngẫu nhiên, viền cầu vồng, overlay động, và gradient text.",
        "📊 Sắp xếp thông tin theo lưới 2 cột với các ô bo tròn góc."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh 'bot.net' để tạo và hiển thị hình ảnh thông tin tốc độ mạng.",
        "📌 Ví dụ: bot.net (không cần tham số thêm).",
        "✅ Nhận hình ảnh thông tin tốc độ mạng được gửi trực tiếp trong nhóm ngay lập tức."
    ]
}

# ------------------ HẰNG SỐ & DẢI MÀU -----------------
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
    [(173, 216, 230), (255, 255, 255), (255, 255, 102)]
]

# ------------------ HÀM HỖ TRỢ CHUNG ------------------

_FONT_CACHE = {}
def get_font(font_path, size):
    key = (font_path, size)
    if key not in _FONT_CACHE:
        if not os.path.exists(font_path):
            logging.error(f"Font file not found: {font_path}, using default font")
            _FONT_CACHE[key] = ImageFont.load_default()
        else:
            try:
                _FONT_CACHE[key] = ImageFont.truetype(font_path, size)
            except Exception as e:
                logging.error(f"Failed to load font {font_path}: {str(e)}")
                _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]

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

def get_mixed_text_width(draw, text, normal_font, emoji_font):
    segments = split_text_by_emoji(text)
    total_width = 0
    for seg, is_emoji in segments:
        f = emoji_font if is_emoji else normal_font
        bbox = draw.textbbox((0, 0), seg, font=f)
        total_width += (bbox[2] - bbox[0])
    return total_width

def draw_mixed_gradient_text(draw, text, position, normal_font, emoji_font, gradient_colors, shadow_offset=(2,2)):
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

def wrap_text(text, font, emoji_font, max_width, draw):
    lines = []
    current_line = ""
    segments = split_text_by_emoji(text)
    
    for seg, is_emoji in segments:
        current_font = emoji_font if is_emoji else font
        for ch in seg:
            test_line = current_line + ch
            bbox = draw.textbbox((0, 0), test_line, font=current_font)
            text_width = bbox[2] - bbox[0]
            if text_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = ch
        if current_line and seg == segments[-1][0]:
            lines.append(current_line)
    
    return lines

def draw_centered_text_mixed_line(text, y, normal_font, emoji_font, gradient_colors, base_draw, region_x0, region_x1, max_width):
    lines = wrap_text(text, normal_font, emoji_font, max_width, base_draw)
    line_height = normal_font.size + 10
    total_height = len(lines) * line_height
    start_y = y - total_height // 2
    
    for i, line in enumerate(lines):
        line_y = start_y + i * line_height
        total_width = get_mixed_text_width(base_draw, line, normal_font, emoji_font)
        region_w = region_x1 - region_x0
        x = region_x0 + (region_w - total_width) // 2
        draw_mixed_gradient_text(base_draw, line, (x, line_y), normal_font, emoji_font, gradient_colors, shadow_offset=(2,2))

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
    except Exception as e:
        logging.error(f"Failed to calculate dominant color: {str(e)}")
        return (0, 0, 0)

def make_round_avatar(avatar):
    try:
        avatar = ImageEnhance.Brightness(avatar).enhance(1.2)
        w, h = avatar.size
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, w, h), fill=255)
        round_img = Image.new("RGBA", (w, h), (255, 255, 255, 0))
        round_img.paste(avatar, (0, 0), mask)
        return round_img
    except Exception as e:
        logging.error(f"Failed to make round avatar: {str(e)}")
        return Image.new("RGBA", (200, 200), (200, 200, 200, 255))

def add_rainbow_border(image, border_thickness=6):
    try:
        w, h = image.size
        border_size = w + 2 * border_thickness
        border_img = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
        draw_border = ImageDraw.Draw(border_img)
        for i in range(360):
            h = i / 360
            r, g, b = colorsys.hsv_to_rgb(h, 0.5, 0.8)
            draw_border.arc([(3, 3), (border_size - 4, border_size - 4)], i, i + 1, fill=(int(r * 255), int(g * 255), int(b * 255), 255), width=border_thickness)
        border_img.paste(image, (border_thickness, border_thickness), image)
        return border_img
    except Exception as e:
        logging.error(f"Failed to add rainbow border: {str(e)}")
        return image

# ------------------ HÀM LẤY ẢNH ------------------

def FetchImage(url):
    if not url:
        return None
    try:
        r = requests.get(url, stream=True, timeout=10)
        r.raise_for_status()
        return Image.open(BytesIO(r.content)).convert("RGB")
    except Exception as e:
        logging.error(f"Failed to fetch image from {url}: {str(e)}")
        return None

# ------------------ HÀM LẤY THÔNG TIN TỐC ĐỘ MẠNG ------------------

def network_info():
    vn_timezone = timezone(timedelta(hours=7))
    current_time = datetime.now(vn_timezone).strftime("%d/%m/%Y %H:%M:%S")
    try:
        st = speedtest.Speedtest()
        best_server = st.get_best_server()
        download_speed = st.download() / 1_000_000
        upload_speed = st.upload() / 1_000_000
        ping = st.results.ping
        server_name = best_server['name']
        server_location = best_server['country']
        client_ip = st.results.client['ip']
        info_text = {
            "Thời gian": f"🕒 {current_time}",
            "Ping": f"🏓 {ping:.2f} ms",
            "Tốc độ tải xuống": f"📥 {download_speed:.2f} Mbps",
            "Tốc độ tải lên": f"📤 {upload_speed:.2f} Mbps",
            "Server": f"🖥️ {server_name} ({server_location})",
            "IP": f"🌐 {client_ip}"
        }
    except Exception as e:
        logging.error(f"Failed to get network info: {str(e)}")
        info_text = {
            "Thời gian": f"🕒 {current_time}",
            "Lỗi": f"❌ Không thể kiểm tra: {str(e)}"
        }
    return info_text

# ------------------ HÀM TẠO ẢNH CHO NET ------------------

def create_background(width, height):
    background_folder = "Resource/background/"
    if not os.path.isdir(background_folder):
        logging.warning(f"Background folder not found: {background_folder}, using default background")
        return Image.new("RGB", (width, height), (130, 190, 255))
    imgs = [os.path.join(background_folder, f) for f in os.listdir(background_folder)
            if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    if imgs:
        try:
            bg = Image.open(random.choice(imgs)).resize((width, height), Image.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(radius=20))
            return bg
        except Exception as e:
            logging.error(f"Failed to load background image: {str(e)}")
    return Image.new("RGB", (width, height), (130, 190, 255))

def create_net_image(info_dict, user_avatar_url, bot_avatar_url, author_id, client):
    try:
        SIZE = (1500, 650)  # Kích thước tối ưu
        TOP_HEIGHT = 125
        H_SPACING = 15
        V_SPACING = 15
        NUM_COLUMNS = 2
        WIDTH = SIZE[0]
        
        # Thử lấy ảnh bìa người dùng
        cover_url = None
        try:
            user_info = client.fetchUserInfo(author_id)
            cover_url = user_info.changed_profiles[author_id].cover
        except Exception as e:
            logging.error(f"Failed to fetch user cover: {str(e)}")
        
        # Tạo ảnh nền
        if cover_url and cover_url != "https://cover-talk.zadn.vn/default":
            bg_image = FetchImage(cover_url)
            if bg_image:
                bg_image = bg_image.resize(SIZE, Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(radius=20)).convert("RGBA")
            else:
                bg_image = create_background(WIDTH, SIZE[1])
        else:
            bg_image = create_background(WIDTH, SIZE[1])
        
        overlay = Image.new("RGBA", SIZE, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Tính màu overlay dựa trên độ sáng ảnh nền
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

        # Vẽ overlay chính
        box_x1, box_y1 = 30, 35
        box_x2, box_y2 = SIZE[0] - 30, SIZE[1] - 40
        draw.rounded_rectangle([(box_x1, box_y1), (box_x2, box_y2)], radius=50, fill=box_color)

        # Tiêu đề
        font_text_large = get_font("font/5.otf", 60)
        font_text_big = get_font("font/5.otf", 55)
        font_icon = get_font("font/NotoEmoji-Bold.ttf", 55)
        text_lines = ["NETWORK INFO", "THÔNG TIN TỐC ĐỘ MẠNG"]
        text_fonts = [font_text_large, font_text_big]
        emoji_fonts = [font_icon, font_icon]
        random_gradients = random.sample(GRADIENT_SETS, 2)
        text_colors = [MULTICOLOR_GRADIENT, random_gradients[0]]

        line_spacing = 75
        start_y = box_y1 + 40
        avatar_left_edge = box_x1 + 25 + 215 + 1
        avatar_right_edge = box_x2 - 230 - 12
        safe_text_width = avatar_right_edge - avatar_left_edge - 25

        for i, (line, font, emoji_font, colors) in enumerate(zip(text_lines, text_fonts, emoji_fonts, text_colors)):
            if line:
                draw_centered_text_mixed_line(line, start_y + i * line_spacing, font, emoji_font, colors, draw, avatar_left_edge, avatar_right_edge, safe_text_width)

        # Avatar
        avatar_size = 215
        center_y = start_y + font_text_large.size // 2 + 15
        left_avatar_x = box_x1 + 25
        right_avatar_x = box_x2 - 230
        user_avatar = FetchImage(user_avatar_url)
        if not user_avatar:
            user_avatar = Image.new("RGBA", (avatar_size, avatar_size), (200, 200, 200, 255))
        user_avatar = user_avatar.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS).convert("RGBA")
        user_avatar = make_round_avatar(user_avatar)
        user_avatar = add_rainbow_border(user_avatar)

        bot_avatar = FetchImage(bot_avatar_url)
        if not bot_avatar:
            bot_avatar = Image.new("RGBA", (avatar_size, avatar_size), (180, 180, 180, 255))
        bot_avatar = bot_avatar.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS).convert("RGBA")
        bot_avatar = make_round_avatar(bot_avatar)
        bot_avatar = add_rainbow_border(bot_avatar)

        overlay.paste(user_avatar, (left_avatar_x, center_y - avatar_size // 2), user_avatar)
        overlay.paste(bot_avatar, (right_avatar_x, center_y - avatar_size // 2), bot_avatar)

        # Lưới thông tin
        num_items = len(info_dict)
        num_columns = 2
        num_rows = math.ceil(num_items / num_columns)
        HORIZONTAL_SPACING = 8
        VERTICAL_SPACING = 8
        CELL_WIDTH = (box_x2 - box_x1 - (num_columns + 1) * HORIZONTAL_SPACING) // num_columns
        CELL_HEIGHT = 75
        cell_start_y = start_y + 2 * line_spacing + 35  # Nhích xuống 20 pixel

        cell_font = get_font("font/5.otf", 38)
        cell_emoji_font = get_font("font/NotoEmoji-Bold.ttf", 38)
        cell_infos = []
        temp_img = Image.new("RGBA", (WIDTH, 50), (0, 0, 0, 0))
        temp_draw = ImageDraw.Draw(temp_img)

        for key, text in info_dict.items():
            lines = wrap_text(text, cell_font, cell_emoji_font, CELL_WIDTH - 10, temp_draw)
            line_heights = []
            for line in lines:
                bbox = temp_draw.textbbox((0, 0), line, font=cell_font)
                line_heights.append(bbox[3] - bbox[1])
            text_height = sum(line_heights) + (len(lines) - 1) * 5
            cell_infos.append((lines, text_height, line_heights))

        row_heights = []
        min_cell_height = 75
        for row in range(num_rows):
            heights = []
            for col in range(num_columns):
                idx = row * num_columns + col
                if idx < num_items:
                    heights.append(max(cell_infos[idx][1] + 15, min_cell_height))
            row_heights.append(max(heights) if heights else min_cell_height)

        grid_height = sum(row_heights) + (num_rows + 1) * VERTICAL_SPACING
        total_height = max(SIZE[1], TOP_HEIGHT + grid_height + 40)
        final_bg = bg_image.resize((WIDTH, total_height))

        final_draw = ImageDraw.Draw(final_bg)
        current_y = cell_start_y
        for row in range(num_rows):
            row_height = row_heights[row]
            for col in range(num_columns):
                idx = row * num_columns + col
                if idx >= num_items:
                    break
                x = box_x1 + HORIZONTAL_SPACING + col * (CELL_WIDTH + HORIZONTAL_SPACING)
                y = current_y
                cell_img = Image.new("RGBA", (CELL_WIDTH, row_height), (0, 0, 0, 0))
                draw_cell = ImageDraw.Draw(cell_img)
                draw_cell.rounded_rectangle((0, 0, CELL_WIDTH, row_height), radius=8, fill=box_color)
                lines, text_height, line_heights = cell_infos[idx]
                start_y = (row_height - text_height) // 2 +20 # Căn giữa dọc
                for i, line in enumerate(lines):
                    draw_centered_text_mixed_line(line, start_y + i * (cell_font.size + 5), cell_font, cell_emoji_font, random.choice(GRADIENT_SETS), draw_cell, 0, CELL_WIDTH, CELL_WIDTH - 10)
                    start_y += line_heights[i] + 5
                overlay.alpha_composite(cell_img, (x, y))
            current_y += row_height + VERTICAL_SPACING

        # Thêm logo và chữ ký
        logo_path = "zalo.png"
        if os.path.exists(logo_path):
            try:
                logo = Image.open(logo_path).convert("RGBA")
                logo_size = 40
                logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                mask = Image.new("L", (logo_size, logo_size), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, logo_size, logo_size), fill=255)
                round_logo = Image.new("RGBA", (logo_size, logo_size), (0, 0, 0, 0))
                round_logo.paste(logo, (0, 0), mask)
                overlay.paste(round_logo, (box_x1 + 25, total_height - logo_size - 12), round_logo)
            except Exception as e:
                logging.error(f"Failed to load logo: {str(e)}")

        designer_text = "design by Minh Vũ Shinn Cte"
        designer_font = get_font("font/5.otf", 32)
        text_bbox = draw.textbbox((0, 0), designer_text, font=designer_font)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]
        designer_x = box_x2 - text_w - 10
        designer_y = total_height - text_h - 12
        draw_mixed_gradient_text(draw, designer_text, (designer_x, designer_y), designer_font, font_icon, random.choice(GRADIENT_SETS))

        final_image = Image.alpha_composite(final_bg, overlay).resize((1500, total_height), Image.Resampling.LANCZOS).convert("RGB")
        image_path = f"network_info_{author_id}_{int(datetime.now().timestamp())}.jpg"
        try:
            final_image.save(image_path, quality=95)
        except Exception as e:
            logging.error(f"Failed to save image {image_path}: {str(e)}")
            raise
        return image_path
    except Exception as e:
        logging.error(f"Error in create_net_image: {str(e)}")
        raise

# ------------------ LỆNH CHECK NET ------------------

def handle_speedtest_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
        info = network_info()
        try:
            user_info = client.fetchUserInfo(author_id)
            user_avatar_url = user_info.changed_profiles[author_id].avatar
        except Exception as e:
            logging.error(f"Failed to fetch user avatar: {str(e)}")
            user_avatar_url = ""
        try:
            bot_uid = "715870970611339054"
            bot_info = client.fetchUserInfo(bot_uid)
            bot_avatar_url = bot_info.changed_profiles[bot_uid].avatar
        except Exception as e:
            logging.error(f"Failed to fetch bot avatar: {str(e)}")
            bot_avatar_url = ""
        image_path = create_net_image(info, user_avatar_url, bot_avatar_url, author_id, client)
        try:
            client.sendLocalImage(
                imagePath=image_path,
                thread_id=thread_id,
                thread_type=thread_type,
                width=final_image_width(image_path),
                height=final_image_height(image_path)
            )
        except Exception as e:
            logging.error(f"Failed to send image via Zalo API: {str(e)}")
            raise
        finally:
            if os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except Exception as e:
                    logging.error(f"Failed to remove image {image_path}: {str(e)}")
    except Exception as e:
        logging.error(f"Error in handle_speedtest_command: {str(e)}")
        raise

def final_image_width(image_path):
    try:
        with Image.open(image_path) as im:
            return im.width
    except Exception as e:
        logging.error(f"Failed to get image width {image_path}: {str(e)}")
        return 1500

def final_image_height(image_path):
    try:
        with Image.open(image_path) as im:
            return im.height
    except Exception as e:
        logging.error(f"Failed to get image height {image_path}: {str(e)}")
        return 650

def get_mitaizl():
    return {'bot.net': handle_speedtest_command}