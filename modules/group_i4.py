import os
import math
import random
import re
import requests
from io import BytesIO
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
from zlapi import ZaloAPIException
from zlapi.models import Message, ThreadType
import logging
import colorsys

# ----------------- CẤU HÌNH LOG -----------------
logging.basicConfig(
    level=logging.ERROR,
    filename="bot_error.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s"
)

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
BACKGROUND_FOLDER = 'backgrounds'
if os.path.isdir(BACKGROUND_FOLDER):
    BACKGROUND_IMAGES = [
        os.path.join(BACKGROUND_FOLDER, f)
        for f in os.listdir(BACKGROUND_FOLDER)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ]
else:
    BACKGROUND_IMAGES = []
    logging.error(f"Thư mục {BACKGROUND_FOLDER} không tồn tại hoặc không thể truy cập.")

# ----------------- HÀM HỖ TRỢ -----------------
_FONT_CACHE = {}
def get_font(font_path, size):
    """Load font với cache để không load nhiều lần."""
    key = (font_path, size)
    if key not in _FONT_CACHE:
        try:
            _FONT_CACHE[key] = ImageFont.truetype(font_path, size)
        except Exception as e:
            logging.error(f"Lỗi load font {font_path} với size {size}: {e}")
            _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]

def FetchImage(url):
    """Tải ảnh từ URL."""
    if not url:
        return None
    try:
        r = requests.get(url, stream=True, timeout=10)
        r.raise_for_status()
        return Image.open(BytesIO(r.content)).convert("RGB")
    except Exception as e:
        logging.error(f"Lỗi tải ảnh từ {url}: {e}")
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
    except Exception as e:
        logging.error(f"Lỗi tính màu chủ đạo: {e}")
        return (0, 0, 0)

def make_round_avatar(avatar):
    """Tăng sáng nhẹ và cắt avatar thành hình tròn."""
    avatar = ImageEnhance.Brightness(avatar).enhance(1.2)
    w, h = avatar.size
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, w, h), fill=255)
    round_img = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    round_img.paste(avatar, (0, 0), mask)
    return round_img

def add_rainbow_border(image, border_thickness=6):
    """Thêm viền cầu vồng cho ảnh tròn."""
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

def create_toggle_switch(is_on, width=80, height=44, corner_radius=22):
    """Tạo nút bật/tắt."""
    toggle = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(toggle)
    bg_color = (52, 199, 89, 255) if is_on else (255, 0, 0, 255)
    draw.rounded_rectangle(
        (0, 0, width, height),
        radius=corner_radius,
        fill=bg_color
    )
    circle_size = height - 4
    circle_x = width - circle_size - 2 if is_on else 2
    circle_y = 2
    draw.ellipse(
        (circle_x, circle_y, circle_x + circle_size, circle_y + circle_size),
        fill=(255, 255, 255, 255)
    )
    return toggle

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

def wrap_text(text, font, max_width):
    """Ngắt dòng văn bản sao cho vừa với chiều rộng tối đa."""
    lines = []
    current_line = ""
    segments = split_text_by_emoji(text)
    
    for seg, is_emoji in segments:
        current_font = font if not is_emoji else get_font("font/NotoEmoji-Bold.ttf", font.size)
        for ch in seg:
            test_line = current_line + ch
            bbox = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), test_line, font=current_font)
            text_width = bbox[2] - bbox[0]
            if text_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append((current_line, False))
                current_line = ch
        if current_line and seg == segments[-1][0]:
            lines.append((current_line, is_emoji))
    
    return lines

def draw_centered_text_mixed_line(text, y, normal_font, emoji_font, gradient_colors, base_draw, region_x0, region_x1, max_width):
    """Vẽ văn bản hỗn hợp căn giữa với gradient, hỗ trợ ngắt dòng."""
    lines = wrap_text(text, normal_font, max_width)
    line_height = normal_font.size + 5
    total_height = len(lines) * line_height
    start_y = y - total_height // 2
    
    for i, (line, is_emoji) in enumerate(lines):
        line_y = start_y + i * line_height
        total_width = 0
        line_segments = split_text_by_emoji(line)
        for seg, seg_is_emoji in line_segments:
            f = emoji_font if seg_is_emoji else normal_font
            seg_bbox = base_draw.textbbox((0, 0), seg, font=f)
            total_width += seg_bbox[2] - seg_bbox[0]
        region_w = region_x1 - region_x0
        x = region_x0 + (region_w - total_width) // 2
        draw_mixed_gradient_text(base_draw, line, (x, line_y), normal_font, emoji_font, gradient_colors, shadow_offset=(2,2))

def final_image_width(image_path):
    """Lấy chiều rộng ảnh, mặc định 3000 nếu lỗi."""
    try:
        with Image.open(image_path) as im:
            return im.width
    except Exception as e:
        logging.error(f"Lỗi khi lấy chiều rộng ảnh {image_path}: {e}")
        return 3000

def final_image_height(image_path):
    """Lấy chiều cao ảnh, mặc định 1300 nếu lỗi."""
    try:
        with Image.open(image_path) as im:
            return im.height
    except Exception as e:
        logging.error(f"Lỗi khi lấy chiều cao ảnh {image_path}: {e}")
        return 1300

# ----------------- HÀM TẠO ẢNH NỀN -----------------
def create_background_from_folder(width=3000, height=1300):
    """Chọn ảnh nền ngẫu nhiên từ thư mục và áp dụng blur."""
    if BACKGROUND_IMAGES:
        bg_path = random.choice(BACKGROUND_IMAGES)
        try:
            bg = Image.open(bg_path).convert("RGB")
            bg = bg.resize((width, height), Image.Resampling.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(radius=20))
            print(f"[DEBUG] Successfully loaded and processed background: {bg_path}")
            return bg
        except Exception as e:
            logging.error(f"Lỗi khi mở ảnh nền từ {bg_path}: {e}")
            print(f"[DEBUG] Error opening image {bg_path}: {e}")
            return Image.new("RGB", (width, height), (130, 190, 255))
    else:
        print(f"[DEBUG] No background files found in {BACKGROUND_FOLDER}")
        return Image.new("RGB", (width, height), (130, 190, 255))

# ----------------- TẬP LỆNH GROUP -----------------
def handle_group_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
        group = client.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
        
        def get_name(uid):
            try:
                user_info = client.fetchUserInfo(uid)
                return user_info.changed_profiles[uid].zaloName
            except Exception:
                return "Không tìm thấy tên"
        
        # Dịch key cấu hình
        key_translation = {
            'blockName': 'Chặn đổi tên & ảnh đại diện',
            'signAdminMsg': 'Ghi chú từ chủ/phó nhóm',
            'addMemberOnly': 'Chỉ thêm thành viên',
            'setTopicOnly': 'Cho phép members ghi chú',
            'enableMsgHistory': 'Bật lịch sử tin nhắn',
            'lockCreatePost': 'Khóa tạo bài đăng',
            'lockCreatePoll': 'Khóa tạo bình chọn',
            'joinAppr': 'Duyệt vào nhóm',
            'bannFeature': 'Tính năng cấm',
            'dirtyMedia': 'Nội dung nhạy cảm',
            'banDuration': 'Thời gian cấm',
            'lockSendMsg': 'Khóa gửi tin nhắn',
            'lockViewMember': 'Khóa xem thành viên'
        }
        
        # Danh sách thông tin nhóm (loại bỏ Cấu hình)
        info_list = [
            f"📋 Cộng đồng: {group.name}",
            f"🆔 ID: {group.groupId}",
            f"📝 Mô tả: {'Mặc định' if group.desc == '' else group.desc}",
            f"👑 Chủ cộng đồng: {get_name(group.creatorId)}",
            f"🛡️ Phó cộng đồng: {', '.join([get_name(uid) for uid in group.adminIds])}",
            f"⏳ Chờ duyệt: {', '.join([get_name(uid) for uid in group.updateMems]) if group.updateMems else 'None'}",
            f"👥 Tổng thành viên: {group.totalMember}",
            f"🕒 Thời gian tạo: {datetime.fromtimestamp(group.createdTime / 1000, tz=timezone(timedelta(hours=7))).strftime('%H:%M %d/%m/%Y')}"
        ]
        
        # Danh sách cấu hình riêng
        settings_list = [
            {"text": f"⚙️ {key_translation.get(key, key)}", "status": value == 1}
            for key, value in group.setting.items()
        ]

        # Tạo ảnh
        SIZE = (3000, 2400)
        FINAL_SIZE = (3000, 2400)
        
        # Thử lấy ảnh bìa nhóm
        cover_url = group.fullAvt if hasattr(group, 'fullAvt') and group.fullAvt else None
        try:
            if cover_url and cover_url != "https://cover-talk.zadn.vn/default":
                bg_image = FetchImage(cover_url)
                if bg_image:
                    bg_image = bg_image.resize(SIZE, Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(radius=20)).convert("RGBA")
                    print(f"[DEBUG] Using group cover image")
                else:
                    bg_image = create_background_from_folder(width=SIZE[0], height=SIZE[1])
            else:
                bg_image = create_background_from_folder(width=SIZE[0], height=SIZE[1])
        except Exception as e:
            logging.error(f"Lỗi khi xử lý ảnh bìa nhóm: {e}")
            bg_image = create_background_from_folder(width=SIZE[0], height=SIZE[1])
        
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

        font_text_large = get_font("font/5.otf", 120)
        font_text_big = get_font("font/5.otf", 110)
        font_icon = get_font("font/NotoEmoji-Bold.ttf", 65)

        text_lines = ["GROUP INFO", "THÔNG TIN NHÓM"]
        text_fonts = [font_text_large, font_text_big]
        emoji_fonts = [font_icon, font_icon]
        random_gradients = random.sample(GRADIENT_SETS, 2)
        text_colors = [MULTICOLOR_GRADIENT, random_gradients[0]]

        line_spacing = 150
        start_y = box_y1 + 80
        avatar_left_edge = box_x1 + 50 + 430 + 1
        avatar_right_edge = box_x2 - 460 - 25
        safe_text_width = avatar_right_edge - avatar_left_edge - 50

        for i, (line, font, emoji_font, colors) in enumerate(zip(text_lines, text_fonts, emoji_fonts, text_colors)):
            if line:
                text_bbox = draw.textbbox((0, 0), line, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_x = (box_x1 + box_x2 - text_width) // 2
                text_y = start_y + i * line_spacing
                draw_mixed_gradient_text(draw, line, (text_x, text_y), normal_font=font, emoji_font=emoji_font, gradient_colors=colors)

        avatar_size = 430
        center_y = start_y + font_text_large.size // 2 + 30
        left_avatar_x = box_x1 + 50
        right_avatar_x = box_x2 - 460
        group_avatar = FetchImage(group.avt if hasattr(group, 'avt') else "")
        if not group_avatar:
            group_avatar = Image.new("RGBA", (avatar_size, avatar_size), (200, 200, 200, 255))
        group_avatar = group_avatar.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS).convert("RGBA")
        group_avatar = make_round_avatar(group_avatar)
        group_avatar = add_rainbow_border(group_avatar)

        bot_uid = "715870970611339054"
        bot_avatar_url = ""
        try:
            bot_info = client.fetchUserInfo(bot_uid)
            bot_avatar_url = bot_info.changed_profiles[bot_uid].avatar
        except Exception as e:
            logging.error(f"Lỗi khi lấy avatar bot: {e}")
        bot_avatar = FetchImage(bot_avatar_url)
        if not bot_avatar:
            bot_avatar = Image.new("RGBA", (avatar_size, avatar_size), (180, 180, 180, 255))
        bot_avatar = bot_avatar.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS).convert("RGBA")
        bot_avatar = make_round_avatar(bot_avatar)
        bot_avatar = add_rainbow_border(bot_avatar)

        overlay.paste(group_avatar, (left_avatar_x, center_y - avatar_size // 2), group_avatar)
        overlay.paste(bot_avatar, (right_avatar_x, center_y - avatar_size // 2), bot_avatar)

        # Lưới thông tin chính
        num_items = len(info_list)
        num_columns = 2
        num_rows = math.ceil(num_items / num_columns)
        HORIZONTAL_SPACING = 15
        VERTICAL_SPACING = 15
        CELL_WIDTH = (box_x2 - box_x1 - (num_columns + 1) * HORIZONTAL_SPACING) // num_columns
        CELL_HEIGHT = 140
        cell_start_y = start_y + 2 * line_spacing + 40

        cell_font = get_font("font/5.otf", 75)
        cell_emoji_font = get_font("font/NotoEmoji-Bold.ttf", 75)
        for idx, item in enumerate(info_list):
            col = idx % num_columns
            row = idx // num_columns
            x = box_x1 + HORIZONTAL_SPACING + col * (CELL_WIDTH + HORIZONTAL_SPACING)
            y = cell_start_y + row * (CELL_HEIGHT + VERTICAL_SPACING)
            cell_img = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (0, 0, 0, 0))
            draw_cell = ImageDraw.Draw(cell_img)
            draw_cell.rounded_rectangle((0, 0, CELL_WIDTH, CELL_HEIGHT), radius=15, fill=box_color)
            cell_gradient = random.choice(GRADIENT_SETS)
            draw_centered_text_mixed_line(item, CELL_HEIGHT // 2, cell_font, cell_emoji_font, cell_gradient, draw_cell, 0, CELL_WIDTH, CELL_WIDTH - 20)
            overlay.alpha_composite(cell_img, (x, y))

        # Lưới cấu hình (2 cột, dưới lưới thông tin chính)
        settings_start_y = cell_start_y + num_rows * (CELL_HEIGHT + VERTICAL_SPACING) + 20
        num_settings = len(settings_list)
        settings_rows = math.ceil(num_settings / num_columns)
        for idx, item in enumerate(settings_list):
            col = idx % num_columns
            row = idx // num_columns
            x = box_x1 + HORIZONTAL_SPACING + col * (CELL_WIDTH + HORIZONTAL_SPACING)
            y = settings_start_y + row * (CELL_HEIGHT + VERTICAL_SPACING)
            cell_img = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (0, 0, 0, 0))
            draw_cell = ImageDraw.Draw(cell_img)
            draw_cell.rounded_rectangle((0, 0, CELL_WIDTH, CELL_HEIGHT), radius=15, fill=box_color)
            cell_gradient = random.choice(GRADIENT_SETS)
            text_x = 10  # Căn trái văn bản, cách lề trái 10px
            draw_centered_text_mixed_line(item["text"], CELL_HEIGHT // 2, cell_font, cell_emoji_font, cell_gradient, draw_cell, text_x, CELL_WIDTH - 80, CELL_WIDTH - 80)  # max_width trừ 80px cho toggle
            
            # Thêm toggle switch thẳng hàng
            is_on = item["status"]
            toggle_img = create_toggle_switch(is_on)
            toggle_x = CELL_WIDTH - 70 - 10  # Cách lề phải 10px
            toggle_y = (CELL_HEIGHT - 34) // 2  # Căn giữa theo chiều dọc
            cell_img.paste(toggle_img, (int(toggle_x), int(toggle_y)), toggle_img)
            overlay.alpha_composite(cell_img, (x, y))

        logo_path = "zalo.png"
        if os.path.exists(logo_path):
            try:
                logo = Image.open(logo_path).convert("RGBA")
                logo_size = 80
                logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                mask = Image.new("L", (logo_size, logo_size), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, logo_size, logo_size), fill=255)
                round_logo = Image.new("RGBA", (logo_size, logo_size), (0, 0, 0, 0))
                round_logo.paste(logo, (0, 0), mask)
                overlay.paste(round_logo, (box_x1 + 50, SIZE[1] - logo_size - 5), round_logo)
            except Exception as e:
                logging.error(f"Lỗi khi xử lý logo zalo.png: {e}")

        designer_text = "design by Minh Vũ Shinn Cte"
        designer_font = get_font("font/5.otf", 65)
        text_bbox = draw.textbbox((0, 0), designer_text, font=designer_font)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]
        designer_x = box_x2 - text_w - 20
        designer_y = SIZE[1] - text_h - 25
        draw_mixed_gradient_text(draw, designer_text, (designer_x, designer_y), designer_font, font_icon, random.choice(GRADIENT_SETS))

        final_image = Image.alpha_composite(bg_image, overlay).resize(FINAL_SIZE, Image.Resampling.LANCZOS).convert("RGB")
        image_path = "group_info.jpg"
        final_image.save(image_path, quality=95)
        client.sendLocalImage(
            image_path,
            thread_id,
            thread_type,
            width=final_image_width(image_path),
            height=final_image_height(image_path),
            message=Message(text="𝗧𝗵𝗼̂𝗻𝗴 tin 𝗻𝗵𝗼́𝗺:"),
            ttl=60000
        )
        if os.path.exists(image_path):
            os.remove(image_path)
    
    except ZaloAPIException as e:
        error_msg = Message(text="🔴 Có lỗi xảy ra khi lấy thông tin nhóm!")
        client.sendMessage(error_msg, thread_id, thread_type)
        print(f"[ERROR] Lỗi API Zalo: {e}")
    except Exception as e:
        error_msg = Message(text="🔴 Đã xảy ra lỗi!")
        client.sendMessage(error_msg, thread_id, thread_type)
        print(f"[ERROR] Lỗi không xác định: {e}")

# ----------------- MÔ TẢ TẬP LỆNH -----------------
des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Hiển thị thông tin chi tiết của nhóm Zalo dưới dạng ảnh trực quan, theo phong cách bot_sys.py.",
    'tính năng': [
        "📋 Hiển thị thông tin nhóm: tên, ID, mô tả, chủ/phó nhóm, số thành viên, thời gian tạo.",
        "🔍 Hiển thị danh sách thành viên chờ duyệt.",
        "⚙️ Hiển thị cấu hình nhóm (bật/tắt) trong lưới 2 cột với nút toggle switch thẳng hàng.",
        "🖼️ Tạo ảnh 3000x1300 với overlay bo tròn góc, avatar nhóm và bot (có viền cầu vồng), tiêu đề gradient.",
        "📊 Sắp xếp thông tin và cấu hình theo lưới 2 cột với các ô bo tròn góc, hỗ trợ ngắt dòng.",
        "🖼️ Ưu tiên sử dụng ảnh bìa nhóm, nếu không có thì lấy ảnh ngẫu nhiên từ Resource/background/ với hiệu ứng blur.",
        "🌈 Áp dụng viền cầu vồng, logo Zalo, và chữ ký 'design by Minh Vũ Shinn Cte'."
    ],
    'cách sử dụng': [
        "📩 Nhập `group.i4` để xem thông tin nhóm dưới dạng ảnh.",
        "✅ Nhận hình ảnh thông tin nhóm được gửi trực tiếp trong nhóm."
    ]
}

def get_mitaizl():
    return {'group.i4': handle_group_command}