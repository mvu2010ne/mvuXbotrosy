import os
import random
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import re
import math
from zlapi.models import Message, Mention

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Tạo ảnh nền độc đáo với thông tin người dùng và nội dung tùy chỉnh.",
    'tính năng': [
        "🖼️ Tự động lấy ảnh nền hoặc tạo nền màu mặc định.",
        "📷 Lấy tên và avatar người dùng, cắt avatar tròn với viền đa sắc.",
        "🌈 Áp dụng hiệu ứng gradient cho chữ và overlay.",
        "📝 Điều chỉnh font tự động để nội dung vừa khung, hỗ trợ emoji.",
        "✅ Gửi ảnh với TTL 60 giây, tự xóa sau khi hiển thị."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh canva <nội dung> để tạo ảnh.",
        "📌 Ví dụ: canva Chào mừng bạn đến với nhóm!",
        "✅ Nhận ảnh tùy chỉnh ngay lập tức."
    ]
}

# --------------------- HÀM HỖ TRỢ ---------------------
_FONT_CACHE = {}
def get_font(font_path, size):
    """Load font với cache để không load nhiều lần."""
    key = (font_path, size)
    if key not in _FONT_CACHE:
        try:
            _FONT_CACHE[key] = ImageFont.truetype(font_path, size)
        except Exception:
            _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]

def make_round_avatar(avatar):
    """Tăng sáng nhẹ và cắt avatar thành hình tròn."""
    avatar = ImageEnhance.Brightness(avatar).enhance(1.2)
    w, h = avatar.size
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, w, h), fill=255)
    round_img = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    round_img.paste(avatar, (0, 0), mask)
    return round_img

def get_gradient_color(colors, ratio):
    """Nội suy màu theo tỉ lệ 0..1 từ danh sách các màu."""
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
    """Thêm viền tròn đa sắc cho ảnh tròn."""
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
    """Thêm viền đa sắc cho hình chữ nhật."""
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

# --------------------- HIỆU ỨNG CHỮ VỚI GRADIENT & EMOJI ---------------------
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

def draw_mixed_gradient_text(draw_obj, text, position, normal_font, emoji_font, gradient_colors, shadow_offset=(2,2)):
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
                c1, c2 = gradient_colors[i], gradient_colors[i+1]
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
            draw_obj.text((x + shadow_offset[0], y + shadow_offset[1]), ch, font=current_font, fill=shadow_color)
            draw_obj.text((x, y), ch, font=current_font, fill=color_list[char_index])
            bbox = draw_obj.textbbox((0, 0), ch, font=current_font)
            char_width = bbox[2] - bbox[0]
            x += char_width
            char_index += 1

# --------------------- HÀM TẠO NỀN ẢNH ---------------------
MULTICOLOR_GRADIENT = [
    (255, 0, 0), (255, 165, 0), (255, 255, 0),
    (0, 255, 0), (0, 0, 255), (75, 0, 130), (148, 0, 211)
]

OVERLAY_COLORS = [
    (255, 255, 255, 100),  (255, 250, 250, 100),  (240, 255, 255, 100),
    (255, 228, 196, 100),  (255, 218, 185, 100),  (255, 239, 213, 100),
    (255, 222, 173, 100),  (255, 250, 205, 100),  (250, 250, 210, 100),
    (255, 245, 238, 100),  (240, 230, 140, 100),  (230, 230, 250, 100),
    (216, 191, 216, 100),  (221, 160, 221, 100),  (255, 182, 193, 100),
    (255, 105, 180, 100),  (255, 160, 122, 100),  (255, 165, 0, 100),
    (255, 215, 0, 100),    (173, 255, 47, 100),   (144, 238, 144, 100),
    (152, 251, 152, 100),  (127, 255, 212, 100),  (0, 255, 255, 100),
    (135, 206, 250, 100),  (176, 224, 230, 100),  (30, 144, 255, 100),
    (100, 149, 237, 100),  (238, 130, 238, 100),  (255, 20, 147, 100)
]

TITLE_COLORS = [
    (255, 105, 180, 100),  # Hot Pink
    (255, 20, 147, 100),   # Deep Pink
    (255, 165, 0, 100),    # Orange
    (255, 215, 0, 100),    # Gold
    (0, 255, 255, 100),    # Cyan
    (30, 144, 255, 100),   # Dodger Blue
    (100, 149, 237, 100),  # Cornflower Blue
    (238, 130, 238, 100),  # Violet
]


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

def create_background(width, height):
    background_folder = "modules/Background"
    if os.path.isdir(background_folder):
        imgs = [os.path.join(background_folder, f) for f in os.listdir(background_folder)
                if f.lower().endswith(('.jpg','.png','.jpeg'))]
        if imgs:
            try:
                bg = Image.open(random.choice(imgs)).resize((width, height), Image.LANCZOS)
                return bg
            except Exception:
                pass
    return Image.new("RGB", (width, height), (130,190,255))

# --------------------- XỬ LÝ NỘI DUNG: Wrap & Adjust Font ---------------------
def wrap_text(text, font, emoji_font, draw, max_width):
    """
    Chia text thành các dòng sao cho mỗi dòng không vượt quá max_width.
    Hỗ trợ xử lý xuống dòng tự nhiên (nếu có "\n" trong text).
    """
    lines = []
    paragraphs = text.splitlines()  # tách theo newline nếu có
    for para in paragraphs:
        words = para.split(" ")
        current_line = ""
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            if get_mixed_text_width(draw, test_line, font, emoji_font) <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
    return lines

def adjust_font_size(text, initial_font_size, min_font_size, max_width, max_height, font_path, emoji_font_path):
    """
    Điều chỉnh kích thước font cho đến khi nội dung vừa với khung max_width x max_height.
    Sử dụng một ảnh tạm để đo kích thước và thêm một khoảng cách giữa các dòng.
    Trả về kích thước font tối ưu và danh sách các dòng text.
    """
    # Tạo ảnh tạm để đo kích thước
    temp_img = Image.new("RGB", (max_width, max_height))
    temp_draw = ImageDraw.Draw(temp_img)
    font_size = initial_font_size
    line_spacing = 4  # khoảng cách giữa các dòng
    while font_size >= min_font_size:
        font = get_font(font_path, font_size)
        emoji_font = get_font(emoji_font_path, font_size)
        lines = wrap_text(text, font, emoji_font, temp_draw, max_width)
        total_height = 0
        for line in lines:
            bbox = temp_draw.textbbox((0, 0), line, font=font)
            line_height = bbox[3] - bbox[1]
            total_height += line_height + line_spacing
        if total_height <= max_height:
            return font_size, lines
        font_size -= 1
    # Nếu không vừa, trả về kích thước nhỏ nhất
    font = get_font(font_path, min_font_size)
    emoji_font = get_font(emoji_font_path, min_font_size)
    lines = wrap_text(text, font, emoji_font, temp_draw, max_width)
    return min_font_size, lines

# --------------------- HÀM CHÍNH ---------------------
def handle_create_image_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản hồi emoji "✅" xác nhận đã nhận lệnh
    action = "✅ "
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    try:
        # Phân tích tin nhắn người dùng
        splitted = message.strip().split(" ", 1)
        if len(splitted) < 2 or not splitted[1].strip():
            client.replyMessage(
                Message(
                    text="@Member, vui lòng cung cấp nội dung cần tạo ảnh!",
                    mention=Mention(author_id, length=len("@Member"), offset=0)
                ),
                message_object, thread_id, thread_type, ttl=20000
            )
            return

        content = splitted[1].strip()
        if not content:
            content = "Nội dung trống"

        # Cấu hình kích thước ảnh
        image_width, image_height = 800, 500
        top_height = 150  # tăng chiều cao header
        output_path = "modules/cache/temp_image_with_text.jpg"

        # Tạo ảnh nền
        bg = create_background(image_width, image_height).convert("RGBA")
        draw = ImageDraw.Draw(bg)

        # ------------------ Xử lý header (avatar & tên) ------------------
        user_info = client.fetchUserInfo(author_id)
        user_name = user_info.changed_profiles[author_id].displayName
        font_title = get_font("font/Tapestry-Regular.ttf", 60)
        emoji_font_title = get_font("font/NotoEmoji-Bold.ttf", 60)
        gradient_for_name = random.choice(GRADIENT_SETS)

        # Tạo overlay header với padding
        padding = 15  # khoảng cách từ các mép
        top_overlay = Image.new("RGBA", (image_width, top_height), (0, 0, 0, 0))
        top_draw = ImageDraw.Draw(top_overlay)
        radius_top = 30
        overlay_color = 255, 255, 255, 150
        top_draw.rounded_rectangle(
            (padding, padding, image_width - padding, top_height - padding),
            radius=radius_top,
            fill=overlay_color
        )

        # Xử lý avatar
        try:
            resp = requests.get(user_info.changed_profiles[author_id].avatar, timeout=5)
            resp.raise_for_status()
            user_avatar = Image.open(BytesIO(resp.content)).convert("RGBA")
        except Exception:
            user_avatar = Image.new("RGBA", (100, 100), (200, 200, 200, 255))
        user_avatar = user_avatar.resize((100, 100), Image.LANCZOS)
        user_avatar = make_round_avatar(user_avatar)
        gradient_for_avatar = MULTICOLOR_GRADIENT
        user_avatar = add_multicolor_circle_border(user_avatar, gradient_for_avatar, 4)
        top_overlay.paste(user_avatar, (80, 20), user_avatar)
        # Vẽ tên người dùng (căn giữa từ avatar đến mép phải overlay)
        avatar_x = 20
        avatar_size = user_avatar.width
        name_area_start = avatar_x + avatar_size + padding
        name_area_width = image_width - name_area_start - padding

        bbox = top_draw.textbbox((0, 0), user_name, font=font_title)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        x_name = name_area_start + (name_area_width - tw) // 2

        draw_mixed_gradient_text(top_draw, user_name, (x_name, (top_height - th) // 2),
                                 font_title, emoji_font_title, gradient_for_name)

        bg.alpha_composite(top_overlay, (0, 0))

        # ------------------ Xử lý overlay nội dung ------------------
        content_overlay_width = image_width - 40
        content_overlay_height = image_height - top_height - 20
        content_overlay = Image.new("RGBA", (content_overlay_width, content_overlay_height), (0, 0, 0, 0))
        content_draw = ImageDraw.Draw(content_overlay)
        radius_content = 15
        content_overlay_color = 255, 255, 255, 180
        content_draw.rounded_rectangle((0, 0, content_overlay_width, content_overlay_height),
                                       radius=radius_content, fill=content_overlay_color)

        # Điều chỉnh font cho nội dung tự động:
        initial_font_size = 90  # kích thước ban đầu nếu nội dung ngắn
        min_font_size = 10      # kích thước nhỏ nhất nếu nội dung quá nhiều
        gradient_for_content = random.choice(GRADIENT_SETS)
        optimal_font_size, lines = adjust_font_size(content, initial_font_size, min_font_size,
                                                    content_overlay_width, content_overlay_height,
                                                    "font/ChivoMono-VariableFont_wght.ttf", "font/NotoEmoji-Bold.ttf")
        font_content = get_font("font/ChivoMono-VariableFont_wght.ttf", optimal_font_size)
        emoji_font_content = get_font("font/NotoEmoji-Bold.ttf", optimal_font_size)

        # Tính tổng chiều cao của các dòng để căn giữa nội dung theo chiều dọc
        total_text_height = 0
        line_heights = []
        for line in lines:
            bbox_line = content_draw.textbbox((0, 0), line, font=font_content)
            line_height = bbox_line[3] - bbox_line[1]
            line_heights.append(line_height)
            total_text_height += line_height
        y_start = (content_overlay_height - total_text_height) // 2

        # Vẽ từng dòng đã wrap (nếu người dùng nhập xuống dòng, sẽ được giữ nguyên)
        current_y = y_start
        for line, line_height in zip(lines, line_heights):
            line_width = get_mixed_text_width(content_draw, line, font_content, emoji_font_content)
            x_line = (content_overlay_width - line_width) // 2
            draw_mixed_gradient_text(content_draw, line, (x_line, current_y),
                                     font_content, emoji_font_content, gradient_for_content)
            current_y += line_height

        bg.alpha_composite(content_overlay, (20, top_height + 10))

        # ------------------ Thêm viền đa sắc cho toàn bộ ảnh ------------------
        gradient_for_border = random.choice(GRADIENT_SETS)
        final_image = add_multicolor_rectangle_border(bg, gradient_for_border, border_thickness=5)
        final_image = final_image.convert("RGB")

        # Lưu và gửi ảnh
        final_image.save(output_path)
        if os.path.exists(output_path):
            client.sendLocalImage(
                output_path,
                message="",
                thread_id=thread_id,
                thread_type=thread_type,
                width=image_width,
                height=image_height,
                ttl=60000
            )
            os.remove(output_path)
        else:
            raise Exception("Không thể lưu ảnh.")

    except Exception as e:
        client.sendMessage(Message(text=f"Đã xảy ra lỗi: {str(e)}"), thread_id, thread_type)

def get_mitaizl():
    return {
        'canva': handle_create_image_command
    }
