import os
import math
import random
import pytz
import lunarcalendar
import textwrap
import re
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
from zlapi.models import Message, Mention
import requests  # Added
import logging   # Added

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Tạo và gửi ảnh lịch âm Việt Nam với giao diện đẹp, hiệu ứng gradient và thông tin phong thủy.",
    'tính năng': [
        "📅 Hiển thị ngày âm/dương lịch, Can–Chi, thứ, giờ hoàng đạo/hắc đạo và ngày tốt/xấu.",
        "🌟 Thiết kế ảnh với gradient đa sắc, overlay mờ, viền bo tròn và hỗ trợ emoji/icon.",
        "📜 Cung cấp sự kiện lịch sử hoặc bài thơ ngắn liên quan đến ngày âm lịch qua API Gemini.",
        "🌸 Tự động căn chỉnh văn bản, bọc dòng, và chọn ảnh nền ngẫu nhiên.",
        "🗑️ Tự xóa ảnh tạm sau khi gửi để tiết kiệm bộ nhớ."
    ],
    'hướng dẫn sử dụng': [
        "💬 Gõ lệnh `amlich` để bot tạo và gửi ảnh lịch âm.",
        "📷 Nhận ảnh với thông tin ngày, phong thủy và sự kiện, kèm mention người gọi.",
        "⚠️ Đảm bảo bot có quyền gửi ảnh và truy cập thư mục font/ảnh nền."
    ]
}

GEMINI_API_KEY = "AIzaSyC5VvVGBk3T0TzfF_JCaDTDPAW97oRhdrc"
# ---------------------------
# HÀM HỖ TRỢ (THEO STYLE i4.py)
# ---------------------------
_FONT_CACHE = {}
def get_font(font_path, size):
    """
    Load font với cache để không load nhiều lần.
    """
    key = (font_path, size)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = ImageFont.truetype(font_path, size)
    return _FONT_CACHE[key]

# ---------------------------
# DANH SÁCH MÀU
# ---------------------------
OVERLAY_COLORS = [
    (255, 255, 255, 150),  # White
    (255, 250, 250, 150),  # Snow
    (240, 255, 255, 150),  # Azure
    (255, 228, 196, 150),  # Bisque
    (255, 218, 185, 150),  # Peach Puff
    (255, 239, 213, 150),  # Papaya Whip
    (255, 222, 173, 150),  # Navajo White
    (255, 250, 205, 150),  # Lemon Chiffon
    (250, 250, 210, 150),  # Light Goldenrod Yellow
    (255, 245, 238, 150),  # Seashell
    (240, 230, 140, 150),  # Khaki
    (230, 230, 250, 150),  # Lavender
    (216, 191, 216, 150),  # Thistle
    (221, 160, 221, 150),  # Plum
    (255, 182, 193, 150),  # Light Pink
    (255, 105, 180, 150),  # Hot Pink
    (255, 160, 122, 150),  # Light Salmon
    (255, 165, 0, 150),    # Orange
    (255, 215, 0, 150),    # Gold
    (173, 255, 47, 150),   # Green Yellow
    (144, 238, 144, 150),  # Light Green
    (152, 251, 152, 150),  # Pale Green
    (127, 255, 212, 150),  # Aquamarine
    (0, 255, 255, 150),    # Cyan
    (135, 206, 250, 150),  # Light Sky Blue
    (176, 224, 230, 150),  # Powder Blue
    (30, 144, 255, 150),   # Dodger Blue
    (100, 149, 237, 150),  # Cornflower Blue
    (238, 130, 238, 150),  # Violet
    (255, 20, 147, 150)    # Deep Pink
]


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

# ---------------------------
# HÀM HỖ TRỢ GRADIENT
# ---------------------------
def get_gradient_color(colors, ratio):
    """
    Nội suy màu dựa trên danh sách màu 'colors' và giá trị ratio trong [0, 1].
    """
    if ratio <= 0:
        return colors[0]
    if ratio >= 1:
        return colors[-1]
    total_segments = len(colors) - 1
    segment = int(ratio * total_segments)
    segment_ratio = (ratio * total_segments) - segment
    c1 = colors[segment]
    c2 = colors[segment + 1]
    r = int(c1[0] * (1 - segment_ratio) + c2[0] * segment_ratio)
    g = int(c1[1] * (1 - segment_ratio) + c2[1] * segment_ratio)
    b = int(c1[2] * (1 - segment_ratio) + c2[2] * segment_ratio)
    return (r, g, b)

def interpolate_colors(colors, text_length, change_every):
    """
    Tạo danh sách các màu gradient theo số lượng ký tự 'text_length'.
    """
    gradient = []
    num_segments = len(colors) - 1
    steps_per_segment = (text_length // change_every) + 1
    for i in range(num_segments):
        for j in range(steps_per_segment):
            if len(gradient) < text_length:
                ratio = j / steps_per_segment
                interpolated_color = (
                    int(colors[i][0] * (1 - ratio) + colors[i + 1][0] * ratio),
                    int(colors[i][1] * (1 - ratio) + colors[i + 1][1] * ratio),
                    int(colors[i][2] * (1 - ratio) + colors[i + 1][2] * ratio)
                )
                gradient.append(interpolated_color)
    while len(gradient) < text_length:
        gradient.append(colors[-1])
    return gradient[:text_length]

# ---------------------------
# HÀM TẠO VIỀN ĐA SẮC
# ---------------------------
def add_multicolor_rectangle_border(image, colors, border_thickness):
    """
    Thêm viền đa sắc cho ảnh theo dạng hình chữ nhật.
    """
    new_w = image.width + 2 * border_thickness
    new_h = image.height + 2 * border_thickness
    border_img = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(border_img)
    for x in range(new_w):
        color = get_gradient_color(colors, x / new_w)
        draw.line([(x, 0), (x, border_thickness - 1)], fill=color)
        draw.line([(x, new_h - border_thickness), (x, new_h - 1)], fill=color)
    for y in range(new_w):
        color = get_gradient_color(colors, y / new_w)
        draw.line([(0, y), (border_thickness - 1, y)], fill=color)
        draw.line([(new_w - border_thickness, y), (new_w - 1, y)], fill=color)
    border_img.paste(image, (border_thickness, border_thickness), image)
    return border_img

def add_multicolor_clock_border(clock_face, center, radius, border_width, colors):
    """
    Vẽ viền gradient cho mặt đồng hồ với các vòng tròn dần dần.
    """
    draw = ImageDraw.Draw(clock_face)
    for offset in range(border_width):
        ratio = offset / (border_width - 1) if border_width > 1 else 0
        color = get_gradient_color(colors, ratio)
        draw.ellipse([
            center[0] - radius - offset,
            center[1] - radius - offset,
            center[0] + radius + offset,
            center[1] + radius + offset
        ], outline=color)
    return clock_face

# ---------------------------
# HÀM VẼ VĂN BẢN VỚI HIỆU ỨNG GRADIENT VÀ ICON
# ---------------------------
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
    Nếu is_emoji=True thì segment chứa emoji, ngược lại là text thường.
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

def draw_mixed_gradient_text(draw_obj, text, position, normal_font, emoji_font, gradient_colors, shadow_offset=(2,2)):
    """
    Vẽ text hỗn hợp (có emoji/icon) với hiệu ứng gradient.
    Dùng normal_font cho văn bản thường, emoji_font cho icon.
    """
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
    shadow_color = (0, 0, 0)
    segments = split_text_by_emoji(text)
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

def draw_gradient_text_with_icon(draw_obj, text, position, normal_font, emoji_font, gradient_colors, shadow_offset=(2,2)):
    """
    Hàm vẽ văn bản với hiệu ứng gradient, áp dụng font cho icon.
    """
    draw_mixed_gradient_text(draw_obj, text, position, normal_font, emoji_font, gradient_colors, shadow_offset)

def draw_wrapped_gradient_text_with_icon(draw_obj, text, position,
                                         normal_font, emoji_font,
                                         gradient_colors, max_width):
    """
    Vẽ văn bản bọc dòng với gradient và hỗ trợ icon, căn giữa theo chiều ngang.
    Nếu text đã có newline, giữ nguyên xuống dòng.
    """
    # Nếu text chứa \n, tách theo dòng đó
    if "\n" in text:
        lines = text.splitlines()
    else:
        # wrap theo độ rộng
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = current_line + " " + word if current_line else word
            bbox = draw_obj.textbbox((0, 0), test_line, font=normal_font)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

    # vẽ từng dòng
    y_offset = 0
    bbox = draw_obj.textbbox((0, 0), "A", font=normal_font)
    line_height = bbox[3] - bbox[1] + 5
    for line in lines:
        # căn giữa
        line_bbox = draw_obj.textbbox((0, 0), line, font=normal_font)
        line_width = line_bbox[2] - line_bbox[0]
        x = position[0] + (max_width - line_width) // 2
        draw_gradient_text_with_icon(
            draw_obj, line, (x, position[1] + y_offset),
            normal_font, emoji_font, gradient_colors
        )
        y_offset += line_height


# ---------------------------
# HÀM TẠO ẢNH LỊCH ÂM VỚI HIỆU ỨNG GRADIENT & ICON RANDOM
# ---------------------------
def create_lunar_calendar_image():
    """
    Tạo ảnh lịch âm với nền ngẫu nhiên, chữ gradient kết hợp icon (emoji) và overlay mờ bao bọc vùng chữ.
    Trả về đường dẫn đến ảnh được lưu.
    """
    # Lấy thời gian hiện tại theo múi giờ TP.HCM và chuyển sang âm lịch
    hcm_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    current_time = datetime.now(hcm_tz)
    lunar_date = lunarcalendar.Converter.Solar2Lunar(current_time)
    
    # Lấy thông tin ngày dương và âm
    day_solar, month_solar, year_solar = current_time.day, current_time.month, current_time.year
    day_lunar, month_lunar, year_lunar = lunar_date.day, lunar_date.month, lunar_date.year
    weekdays = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
    weekday_solar = weekdays[current_time.weekday()]
    
    # Các thông tin bổ sung
    zodiac_hours = get_zodiac_hours()
    good_bad_day = get_good_bad_day()
    historical_event = get_historical_event()
    seasonal_event = get_seasonal_event(month_solar, day_solar)
    
    # Thiết lập kích thước ảnh và đường dẫn lưu
    width, height = 600, 900
    output_path = "modules/cache/temp_lunar_calendar.jpg"
    
    # Lấy ảnh nền ngẫu nhiên từ thư mục (nếu có)
    background_dir = "modules/hinhnenamlich"
    image_files = [os.path.join(background_dir, file) for file in os.listdir(background_dir)
                   if file.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if image_files:
        background_path = random.choice(image_files)
        background = Image.open(background_path).convert("RGB").resize((width, height))
    else:
        background = Image.new("RGB", (width, height), (255, 250, 240))
    
    # Chuyển nền sang RGBA để hỗ trợ alpha
    background = background.convert("RGBA")
    
    # Sử dụng font chữ theo đường dẫn giống i4.py:
    # - Font tiêu đề: "font/Tapestry-Regular.ttf"
    # - Font cho các mục nhỏ: "font/ChivoMono-VariableFont_wght.ttf"
    # - Font emoji: "font/NotoEmoji-Bold.ttf"
    title_font = get_font("font/Tapestry-Regular.ttf", 70)
    date_font = get_font("font/Tapestry-Regular.ttf", 120)
    small_font = get_font("font/ChivoMono-VariableFont_wght.ttf", 24)
    emoji_title = get_font("font/NotoEmoji-Bold.ttf", 70)
    emoji_date = get_font("font/NotoEmoji-Bold.ttf", 120)
    emoji_small = get_font("font/NotoEmoji-Bold.ttf", 24)
    
    # Tạo overlay cho vùng chữ: chọn overlay color ngẫu nhiên từ OVERLAY_COLORS
    overlay_color = (255, 255, 255, 150)
    temp_draw = ImageDraw.Draw(background)
    # Chuẩn bị danh sách các khối văn bản: (văn bản, font, wrapped)
    blocks = []
    blocks.append(("Lịch Âm", title_font, False))
    blocks.append((str(day_lunar), date_font, False))
    blocks.append((f"Tháng {month_lunar} - {year_lunar}", small_font, False))
    solar_text = f"{weekday_solar}, {day_solar:02d}/{month_solar:02d}/{year_solar}"
    blocks.append((solar_text, small_font, False))
    blocks.append((zodiac_hours, small_font, True))
    blocks.append((good_bad_day, small_font, True))
    blocks.append((historical_event, small_font, True))
    if seasonal_event:
        blocks.append((f"Tiết khí: {seasonal_event}", small_font, True))
    
    # Tính toán tổng chiều cao của các khối văn bản và khoảng cách giữa chúng
    text_heights = []
    for text, font, wrapped in blocks:
        if not wrapped:
            bbox = temp_draw.textbbox((0, 0), text, font=font)
            block_height = bbox[3] - bbox[1]
        else:
            lines = textwrap.wrap(text, width=40)
            bbox = temp_draw.textbbox((0, 0), "A", font=font)
            line_height = bbox[3] - bbox[1]
            block_height = len(lines) * line_height + (len(lines) - 1) * 5
        text_heights.append(block_height)
    
    total_text_height = sum(text_heights)
    n = len(blocks)
    gap = (height - total_text_height) // (n + 1)
    
    starting_offset = 20
    starting_y = max(gap - starting_offset, 0)
    
    # Xác định vùng chữ nhật bao bọc với margin đều
    # Tính chiều cao phần overlay
    current_y = starting_y
    for block_height in text_heights:
        current_y += block_height + gap
    final_y = current_y - gap

    # Căn đều overlay và thêm padding
    margin_x = 40
    overlay_height = final_y - starting_y
    equal_margin_y = (height - overlay_height) // 2
    padding_y = -20  # Điều chỉnh khoảng cách với mép trên/dưới

    # Đảm bảo overlay không vượt ra ngoài hình
    top = max(equal_margin_y + padding_y, 0)
    bottom = min(equal_margin_y + overlay_height - padding_y, height)

    # Vùng overlay chính xác
    rect_box = (
        margin_x,
        top,
        width - margin_x,
        bottom
    )

    
    # Tạo overlay: hình chữ nhật bán trong suốt, bo góc và hiệu ứng mờ
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle(rect_box, radius=50, fill=overlay_color)
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=5))
    
    # Hợp layer overlay vào nền
    combined = Image.alpha_composite(background, overlay)
    draw = ImageDraw.Draw(combined)
    
    # Vẽ các khối văn bản: mỗi block được vẽ với dải màu gradient ngẫu nhiên
    current_y = starting_y
    for i, ((text, font, wrapped), block_height) in enumerate(zip(blocks, text_heights)):
        draw_y = current_y - 40 if i == 1 else current_y
        # Chọn font emoji tương ứng theo font đang dùng
        if font == title_font:
            normal_font, emoji_font = title_font, emoji_title
        elif font == date_font:
            normal_font, emoji_font = date_font, emoji_date
        else:
            normal_font, emoji_font = small_font, emoji_small
        # Chọn dải màu gradient ngẫu nhiên cho block này
        block_gradient = random.choice(MULTICOLOR_GRADIENTS)
        if not wrapped:
            bbox = draw.textbbox((0, 0), text, font=normal_font)
            text_width = bbox[2] - bbox[0]
            x_position = (width - text_width) // 2
            draw_gradient_text_with_icon(draw, text, (x_position, draw_y), normal_font, emoji_font, block_gradient)
        else:
            draw_wrapped_gradient_text_with_icon(draw, text, (30, draw_y), normal_font, emoji_font, block_gradient, max_width=width - 60)
        current_y += block_height + gap

    combined = combined.convert("RGB")
    combined.save(output_path)
    return output_path
    
def call_gemini_api(prompt):
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        if 'candidates' in result and result['candidates']:
            for candidate in result['candidates']:
                if 'content' in candidate and 'parts' in candidate['content']:
                    for part in candidate['content']['parts']:
                        if 'text' in part:
                            return part['text'].strip()
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Request Exception: {e}, Response: {response.text if 'response' in locals() else 'N/A'}")
        return None
    except Exception as e:
        logging.error(f"General Exception: {e}")
        return None
# ---------------------------
# HÀM TRỢ GIÚP (Nội dung cố định)
# ---------------------------
# ---------------------------
# DANH SÁCH CAN CHI
# ---------------------------
STEMS = ['Giáp','Ất','Bính','Đinh','Mậu','Kỷ','Canh','Tân','Nhâm','Quý']
BRANCHES = ['Tý','Sửu','Dần','Mão','Thìn','Tỵ','Ngọ','Mùi','Thân','Dậu','Tuất','Hợi']

def get_can_chi(dt):
    """
    Tính Can–Chi của một ngày dương lịch theo JDN:
      - stem_index = (JDN + 9) % 10
      - branch_index = (JDN + 1) % 12
    """
    day, month, year = dt.day, dt.month, dt.year
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12*a - 3
    JDN = day + (153*m + 2)//5 + 365*y + y//4 - y//100 + y//400 - 32045
    stem = STEMS[(JDN + 9) % 10]
    branch = BRANCHES[(JDN + 1) % 12]
    return f"{stem} {branch}"

# ---------------------------
# CẬP NHẬT HÀM VỚI CAN–CHI
# ---------------------------
def get_zodiac_hours():
    now = datetime.now(pytz.timezone('Asia/Ho_Chi_Minh'))
    lunar_date = lunarcalendar.Converter.Solar2Lunar(now)

    # Ngày dương và âm
    day_solar, month_solar, year_solar = now.day, now.month, now.year
    day_lunar, month_lunar, year_lunar = lunar_date.day, lunar_date.month, lunar_date.year

    # Thứ và Can–Chi
    weekdays = ["Thứ Hai","Thứ Ba","Thứ Tư","Thứ Năm","Thứ Sáu","Thứ Bảy","Chủ Nhật"]
    weekday_solar = weekdays[now.weekday()]
    can_chi = get_can_chi(now)

    prompt = (
        f"Hôm nay là {day_lunar} tháng {month_lunar} âm lịch, Can–Chi: {can_chi}, năm Ất Tỵ 2025. "
        "Dựa trên lịch âm Việt Nam tiêu chuẩn, không cần vị trí địa lý, chỉ liệt kê giờ hoàng đạo và hắc đạo trong ngày, không giải thích.Viết theo cấu trúc 1 dòng "
    )
    result = call_gemini_api(prompt)
    if result:
        return result
    return ("Giờ hoàng đạo: Tý, Sửu, Mão, Ngọ, Thân, Dậu\n"
            "Giờ hắc đạo: Dần, Thìn, Tỵ, Mùi, Tuất, Hợi")


def get_good_bad_day():
    now = datetime.now(pytz.timezone('Asia/Ho_Chi_Minh'))
    lunar_date = lunarcalendar.Converter.Solar2Lunar(now)

    day_solar, month_solar, year_solar = now.day, now.month, now.year
    day_lunar, month_lunar, year_lunar = lunar_date.day, lunar_date.month, lunar_date.year

    weekdays = ["Thứ Hai","Thứ Ba","Thứ Tư","Thứ Năm","Thứ Sáu","Thứ Bảy","Chủ Nhật"]
    weekday_solar = weekdays[now.weekday()]
    can_chi = get_can_chi(now)

    prompt = (
        f"Hôm nay là {day_lunar} tháng {month_lunar} âm lịch, Can–Chi: {can_chi}. "
        "Theo lịch âm và phong thủy Việt Nam, xác định ngày này tốt hay xấu "
        "cho xuất hành, cưới hỏi, xây dựng; không giải thích, chỉ cần kết quả."
    )
    result = call_gemini_api(prompt)
    if result:
        return result
    return "Ngày tốt để xuất hành, cưới hỏi. Không tốt cho xây dựng."


def get_historical_event():
    now = datetime.now(pytz.timezone('Asia/Ho_Chi_Minh'))
    lunar_date = lunarcalendar.Converter.Solar2Lunar(now)

    # Ngày dương và âm
    day_solar, month_solar, year_solar = now.day, now.month, now.year
    day_lunar, month_lunar, year_lunar = lunar_date.day, lunar_date.month, lunar_date.year

    # Thứ và Can–Chi
    weekdays = ["Thứ Hai","Thứ Ba","Thứ Tư","Thứ Năm","Thứ Sáu","Thứ Bảy","Chủ Nhật"]
    weekday_solar = weekdays[now.weekday()]
    can_chi = get_can_chi(now)

    # Prompt tìm sự kiện lịch sử
    prompt = (
        f"Hôm nay là {weekday_solar}, ngày {day_solar:02d}/{month_solar:02d}/{year_solar} "
        f"Hôm nay là {day_lunar} tháng {month_lunar} âm lịch, Can–Chi: {can_chi}. "
        "Tra cứu lịch sử Việt Nam và thế giới, không giải thích, "
        "tìm một sự kiện nổi bật xảy ra vào ngày này; nếu không có thì chỉ trả về 'Không có'."
    )
    result = call_gemini_api(prompt)
    if result and result.strip().lower() != "không có":
        return result

    # Nếu không có sự kiện, thử lấy bài thơ từ API
    poem_prompt = (
        f"Viết một bài thơ ngắn 4 câu thể hiện không khí của ngày "
        f"{day_lunar} tháng {month_lunar} âm lịch."
    )
    poem = call_gemini_api(poem_prompt)
    if poem:
        return poem

    # Fallback tĩnh nếu API cũng không trả về thơ
    return (
        "Trăng vàng soi khắp lối,\n"
        "Gió thu thoảng mây trôi,\n"
        "Tâm tư ngẩn ngơ nhớ,\n"
        "Đêm thanh mộng khẽ vơi."
    )



def get_seasonal_event(month, day):
    seasonal_events = {
        (3, 21): "Xuân phân",
        (6, 21): "Hạ chí",
        (9, 23): "Thu phân",
        (12, 22): "Đông chí"
    }
    return seasonal_events.get((month, day), "")

# ---------------------------
# XỬ LÝ LỆNH "amlich" (Gửi ảnh Lịch Âm)
# ---------------------------
def handle_create_lunar_calendar_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản hồi emoji "✅" xác nhận đã nhận lệnh
    action = "✅ "
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    try:
        image_path = create_lunar_calendar_image()
        if os.path.exists(image_path):
            client.sendLocalImage(
                image_path,
                message=Message(
                    text="@Member", 
                    mention=Mention(author_id, length=len("@Member"), offset=0)
                ),
                thread_id=thread_id,
                thread_type=thread_type,
                width=600,
                height=900,
                ttl=30000
            )
            os.remove(image_path)
        else:
            raise Exception("Không thể lưu ảnh.")
    except Exception as e:
        client.sendMessage(Message(text=f"Đã xảy ra lỗi: {str(e)}"), thread_id, thread_type)

def get_mitaizl():
    return {
        'amlich': handle_create_lunar_calendar_command
    }
