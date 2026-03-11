import os
import math
import random
import requests
import logging
from io import BytesIO
from datetime import datetime
from zlapi import ZaloAPIException
from zlapi.models import Message, ThreadType
from config import PREFIX
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import re
import unicodedata

# --------------------- CẤU HÌNH NGÂN HÀNG ---------------------
# Danh sách các ngân hàng với thông tin chi tiết
BANKS = [
    {
        "aliases": ["vcb", "vietcombank"],
        "bin": "970436",
        "name": "VIETCOMBANK",
        "full_name": "Ngân hàng Ngoại thương Việt Nam"
    },
    {
        "aliases": ["tcb", "techcombank"],
        "bin": "970407",
        "name": "TECHCOMBANK",
        "full_name": "Ngân hàng Kỹ Thương Việt Nam"
    },
    {
        "aliases": ["mb", "mbbank", "mb bank"],
        "bin": "970422",
        "name": "MB BANK",
        "full_name": "Ngân hàng Quân Đội"
    },
    {
        "aliases": ["acb"],
        "bin": "970416",
        "name": "ACB",
        "full_name": "Ngân hàng Á Châu"
    },
    {
        "aliases": ["vib"],
        "bin": "970441",
        "name": "VIB",
        "full_name": "Ngân hàng Quốc Tế"
    },
    {
        "aliases": ["bidv"],
        "bin": "970418",
        "name": "BIDV",
        "full_name": "Ngân hàng Đầu tư và Phát triển Việt Nam"
    },
    {
        "aliases": ["vietinbank", "vtb"],
        "bin": "970415",
        "name": "VIETINBANK",
        "full_name": "Ngân hàng Công Thương Việt Nam"
    },
    {
        "aliases": ["tpbank"],
        "bin": "970423",
        "name": "TPBANK",
        "full_name": "Ngân hàng Tiên Phong"
    },
    {
        "aliases": ["vpbank"],
        "bin": "970432",
        "name": "VPBANK",
        "full_name": "Ngân hàng Việt Nam Thịnh Vượng"
    },
    {
        "aliases": ["agribank"],
        "bin": "970405",
        "name": "AGRIBANK",
        "full_name": "Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam"
    },
    {
        "aliases": ["sacombank"],
        "bin": "970403",
        "name": "SACOMBANK",
        "full_name": "Ngân hàng Sài Gòn Thương Tín"
    },
    {
        "aliases": ["scb"],
        "bin": "970429",
        "name": "SCB",
        "full_name": "Ngân hàng Sài Gòn"
    },
    {
        "aliases": ["hdbank"],
        "bin": "970437",
        "name": "HDBANK",
        "full_name": "Ngân hàng Phát triển Nhà TP.HCM"
    },
    {
        "aliases": ["ocb"],
        "bin": "970448",
        "name": "OCB",
        "full_name": "Ngân hàng Phương Đông"
    },
    {
        "aliases": ["msb", "maritimebank"],
        "bin": "970426",
        "name": "MSB",
        "full_name": "Ngân hàng Hàng Hải Việt Nam"
    },
    {
        "aliases": ["shb"],
        "bin": "970443",
        "name": "SHB",
        "full_name": "Ngân hàng Sài Gòn - Hà Nội"
    },
    {
        "aliases": ["eximbank", "exim"],
        "bin": "970431",
        "name": "EXIMBANK",
        "full_name": "Ngân hàng Xuất Nhập khẩu Việt Nam"
    },
    {
        "aliases": ["dongabank", "dab"],
        "bin": "970406",
        "name": "DONGABANK",
        "full_name": "Ngân hàng Đông Á"
    },
    {
        "aliases": ["pvcombank"],
        "bin": "970412",
        "name": "PVCOMBANK",
        "full_name": "Ngân hàng Đại chúng Việt Nam"
    },
    {
        "aliases": ["gpbank"],
        "bin": "970408",
        "name": "GPBANK",
        "full_name": "Ngân hàng Dầu khí Toàn cầu"
    },
    {
        "aliases": ["oceanbank"],
        "bin": "970414",
        "name": "OCEANBANK",
        "full_name": "Ngân hàng Đại Dương"
    },
    {
        "aliases": ["namabank"],
        "bin": "970428",
        "name": "NAMABANK",
        "full_name": "Ngân hàng Nam Á"
    },
    {
        "aliases": ["ncb"],
        "bin": "970419",
        "name": "NCB",
        "full_name": "Ngân hàng Quốc Dân"
    },
    {
        "aliases": ["vietabank"],
        "bin": "970427",
        "name": "VIETABANK",
        "full_name": "Ngân hàng Việt Á"
    },
    {
        "aliases": ["vietbank"],
        "bin": "970433",
        "name": "VIETBANK",
        "full_name": "Ngân hàng Việt Nam Thương Tín"
    },
    {
        "aliases": ["vrb"],
        "bin": "970421",
        "name": "VRB",
        "full_name": "Ngân hàng Việt Nga"
    },
    {
        "aliases": ["wooribank"],
        "bin": "970457",
        "name": "WOORIBANK",
        "full_name": "Ngân hàng Woori Việt Nam"
    },
    {
        "aliases": ["uob"],
        "bin": "970458",
        "name": "UOB",
        "full_name": "Ngân hàng United Overseas Bank"
    },
    {
        "aliases": ["standardchartered"],
        "bin": "970410",
        "name": "STANDARD CHARTERED",
        "full_name": "Ngân hàng Standard Chartered Việt Nam"
    },
    {
        "aliases": ["publicbank"],
        "bin": "970439",
        "name": "PUBLIC BANK",
        "full_name": "Ngân hàng Public Bank Việt Nam"
    },
    {
        "aliases": ["shinhanbank"],
        "bin": "970424",
        "name": "SHINHAN BANK",
        "full_name": "Ngân hàng Shinhan Việt Nam"
    },
    {
        "aliases": ["hsbc"],
        "bin": "458761",
        "name": "HSBC",
        "full_name": "Ngân hàng HSBC Việt Nam"
    },
    {
        "aliases": ["coop", "coopbank"],
        "bin": "970446",
        "name": "COOPBANK",
        "full_name": "Ngân hàng Hợp tác xã Việt Nam"
    },
    {
        "aliases": ["lienvietpostbank", "lvb"],
        "bin": "970449",
        "name": "LIENVIETPOSTBANK",
        "full_name": "Ngân hàng Bưu điện Liên Việt"
    },
    {
        "aliases": ["baovietbank", "bvb"],
        "bin": "970438",
        "name": "BAOVIETBANK",
        "full_name": "Ngân hàng Bảo Việt"
    },
    {
        "aliases": ["bvbank", "banviet"],
        "bin": "970454",
        "name": "BVBANK",
        "full_name": "Ngân hàng Bản Việt"
    }
]

# Chuyển danh sách thành từ điển BANK_CODES
BANK_CODES = {
    alias: {
        "bin": bank["bin"],
        "name": bank["name"],
        "full_name": bank["full_name"]
    }
    for bank in BANKS
    for alias in bank["aliases"]
}

# --------------------- MÔ TẢ LỆNH ---------------------
des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Bot hiển thị thông tin tài khoản ngân hàng qua ảnh với QR code VietQR, hiệu ứng gradient, viền đa sắc và overlay bo góc.",
    'tính năng': [
        "📋 Tạo ảnh chứa thông tin ngân hàng (tên ngân hàng, số tài khoản, chủ tài khoản, số tiền, nội dung).",
        "🖼️ Hiển thị QR code VietQR để chuyển khoản nhanh.",
        "🎨 Sử dụng nền ảnh từ avatar người dùng hoặc gradient mặc định, thêm overlay và viền đa sắc.",
        "✅ Hỗ trợ nhập số tài khoản, mã ngân hàng, số tiền, nội dung chuyển khoản và tên chủ tài khoản (tùy chọn).",
        "⚠️ Tự động xóa file ảnh tạm sau khi gửi và thông báo lỗi nếu xử lý thất bại."
    ],
    'hướng dẫn sử dụng': [
        f"📩 creat.bankcard | [Tên ngân hàng] | [Số tài khoản] | [Tên chủ tài khoản] | [Số tiền] | [Nội dung]",
        "📌 Ví dụ: `!creat.bankcard 123456789 vcb 500000 Thanh toán|Nguyen Van A`.",
        "✅ Nhận ảnh chứa thông tin tài khoản ngân hàng và QR code."
    ]
}

# --------------------- HÀM HỖ TRỢ ---------------------
_FONT_CACHE = {}
def get_font(font_path, size):
    """Load font with cache, fallback to default font if resource not found."""
    key = (font_path, size)
    if key not in _FONT_CACHE:
        try:
            # Chuẩn hóa đường dẫn font
            font_path = os.path.join(os.path.dirname(__file__), font_path)
            _FONT_CACHE[key] = ImageFont.truetype(font_path, size)
        except IOError as e:
            logging.error(f"Không thể tải font {font_path}: {e}")
            # Fallback to default font
            try:
                # Thử các font hệ thống phổ biến
                fallback_fonts = [
                    "arial.ttf",  # Windows
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
                    "/Library/Fonts/Arial.ttf"  # macOS
                ]
                for fallback in fallback_fonts:
                    if os.path.exists(fallback):
                        _FONT_CACHE[key] = ImageFont.truetype(fallback, size)
                        logging.info(f"Sử dụng font mặc định: {fallback}")
                        break
                else:
                    # Nếu không tìm thấy font fallback, dùng font mặc định của Pillow
                    _FONT_CACHE[key] = ImageFont.load_default()
                    logging.warning("Không tìm thấy font fallback, sử dụng font mặc định của Pillow")
            except Exception as fallback_error:
                logging.error(f"Lỗi khi tải font fallback: {fallback_error}")
                _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]

def make_round_avatar(avatar):
    avatar = ImageEnhance.Brightness(avatar).enhance(1.2)
    w, h = avatar.size
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, w, h), fill=255)
    round_img = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    round_img.paste(avatar, (0, 0), mask)
    return round_img

def get_gradient_color(colors, ratio):
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

def add_multicolor_rectangle_border(image, colors, border_thickness=10):
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

def add_multicolor_circle_border(image, colors, border_thickness=5):
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

def draw_centered_text_mixed_line(text, y, normal_font, emoji_font, gradient_colors, base_draw, region_x0, region_x1):
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

# --------------------- DẢI MÀU ---------------------
MULTICOLOR_GRADIENT = [
    (255, 0, 0), (255, 165, 0), (255, 255, 0),
    (0, 255, 0), (0, 0, 255), (75, 0, 130), (148, 0, 211)
]
OVERLAY_COLORS = [
    (255, 255, 255, 200), (255, 250, 250, 200), (240, 255, 255, 200),
    (255, 228, 196, 200), (255, 218, 185, 200), (255, 239, 213, 200),
    (255, 222, 173, 200), (255, 250, 205, 200), (250, 250, 210, 200),
    (255, 245, 238, 200), (240, 230, 140, 200), (230, 230, 250, 200),
    (216, 191, 216, 200), (221, 160, 221, 200), (255, 182, 193, 200),
    (255, 105, 180, 200), (255, 160, 122, 200), (255, 165, 0, 200),
    (255, 215, 0, 200), (173, 255, 47, 200), (144, 238, 144, 200),
    (152, 251, 152, 200), (127, 255, 212, 200), (0, 255, 255, 200),
    (135, 206, 250, 200), (176, 224, 230, 200), (30, 144, 255, 200),
    (100, 149, 237, 200), (238, 130, 238, 200), (255, 20, 147, 200)
]
MULTICOLOR_GRADIENTS = [
    [(255, 0, 255), (255, 128, 255), (0, 255, 255), (128, 255, 255), (255, 0, 0), (255, 128, 128), (255, 255, 0), (128, 255, 0), (0, 255, 0)],
    [(255, 0, 0), (255, 85, 0), (255, 165, 0), (255, 210, 0), (255, 255, 0), (200, 255, 0), (0, 128, 0), (0, 200, 100), (255, 105, 180), (255, 50, 200), (0, 0, 255), (50, 50, 255), (75, 0, 130), (110, 0, 200), (148, 0, 211)],
    [(255, 182, 193), (255, 210, 220), (255, 240, 245), (230, 255, 255), (173, 216, 230), (200, 250, 250), (152, 251, 152), (180, 255, 170), (240, 230, 140), (255, 250, 180)],
    [(0, 255, 127), (0, 230, 150), (255, 200, 0), (255, 165, 0), (255, 69, 0), (255, 105, 180)],
    [(0, 191, 255), (0, 220, 255), (30, 144, 255), (100, 149, 237), (135, 206, 250)],
    [(255, 94, 77), (255, 160, 122), (255, 99, 71), (255, 215, 0), (255, 255, 0)],
    [(0, 255, 0), (34, 255, 34), (34, 139, 34), (50, 205, 50), (90, 230, 90), (144, 238, 144), (152, 251, 152), (180, 255, 180)],
    [(255, 140, 0), (255, 99, 71), (255, 69, 0), (220, 20, 60), (255, 20, 147)],
    [(0, 255, 255), (70, 130, 180), (0, 0, 255), (25, 25, 112)],
    [(0, 255, 0), (138, 43, 226), (0, 0, 255), (255, 182, 193), (255, 215, 0)],
    [(255, 223, 186), (255, 182, 193), (255, 160, 122), (255, 99, 71), (152, 251, 152), (173, 216, 230)],
    [(176, 196, 222), (135, 206, 250), (70, 130, 180), (25, 25, 112)],
    [(255, 200, 200), (255, 165, 150), (255, 255, 180), (200, 255, 180), (180, 255, 255), (180, 200, 255), (220, 180, 255)],
    [(152, 251, 152), (180, 255, 180), (220, 255, 200), (255, 230, 180), (255, 200, 150), (255, 165, 100)],
    [(255, 105, 180), (255, 120, 190), (255, 165, 200), (255, 200, 220), (255, 230, 240), (255, 250, 255)],
    [(0, 255, 127), (100, 255, 150), (150, 255, 180), (200, 255, 210), (220, 255, 230)],
    [(255, 0, 0), (255, 69, 0), (255, 140, 0), (255, 215, 0), (0, 255, 127), (0, 255, 255), (30, 144, 255)],
    [(0, 255, 127), (0, 191, 255), (123, 104, 238), (75, 0, 130)],
    [(75, 0, 130), (138, 43, 226), (148, 0, 211), (255, 20, 147), (255, 105, 180)]
]

# --------------------- HÀM XỬ LÝ THÔNG TIN NGÂN HÀNG ---------------------
def find_account_number(text):
    numbers = re.findall(r'\d+', text)
    return numbers[0] if numbers else None

def find_bank_code(text):
    words = text.lower().split()
    for word in words:
        if word in BANK_CODES:
            return {
                'bin': BANK_CODES[word]['bin'],
                'name': BANK_CODES[word]['name'],
                'word': word
            }
    return None

def normalize_account_name(name):
    vietnamese_map = {'Đ': 'D', 'đ': 'd'}
    name = name.strip().upper()
    name = unicodedata.normalize('NFD', name)
    name = re.sub(r'[\u0300-\u036f]', '', name)
    for char, repl in vietnamese_map.items():
        name = name.replace(char, repl)
    return name

def normalize_description(description):
    vietnamese_map = {'Đ': 'D', 'đ': 'd'}
    description = description.strip().upper()
    description = unicodedata.normalize('NFD', description)
    description = re.sub(r'[\u0300-\u036f]', '', description)
    for char, repl in vietnamese_map.items():
        description = description.replace(char, repl)
    description = re.sub(r'[^A-Z0-9\s]', '', description)
    return description

def generate_vietqr_link(bank_info, account_number, account_name, amount=0, add_info=""):
    from urllib.parse import quote
    base_url = "https://img.vietqr.io/image"
    template = "qr_only"
    encoded_account_name = quote(account_name)
    return f"{base_url}/{bank_info['bin']}-{account_number}-{template}.jpg?accountName={encoded_account_name}&amount={amount}&addInfo={add_info}"

def find_amount(text, account_number):
    numbers = re.findall(r'\d+', text) or []
    return next((num for num in numbers if num != account_number and len(num) > 3), '0')

def find_transfer_info(text, bank_code, account_number, amount):
    text = text.replace(bank_code, '').replace(account_number, '').replace(amount, '').strip()
    return text

# --------------------- HÀM TẠO ẢNH ---------------------
def create_bank_card_image(bank_info, account_number, account_name, amount, description, qr_code_url, user_info):
    WIDTH = 1000
    HEIGHT = 400
    image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Tạo nền ảnh
    try:
        resp = requests.get(user_info['avatar'], timeout=5)
        resp.raise_for_status()
        bg = Image.open(BytesIO(resp.content)).convert("RGB")
        bg = bg.resize((WIDTH, HEIGHT), Image.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=8))
    except Exception:
        bg = Image.new("RGB", (WIDTH, HEIGHT), (26, 35, 126))

    image.paste(bg.convert("RGBA"), (0, 0))

    # Thêm overlay gradient
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (26, 35, 126, 77))
    image.alpha_composite(overlay)

    # Tải và vẽ QR code
    QR_SIZE = 300
    QR_PADDING = 50
    try:
        resp = requests.get(qr_code_url, timeout=5)
        resp.raise_for_status()
        qr_image = Image.open(BytesIO(resp.content)).convert("RGBA")
        qr_image = qr_image.resize((QR_SIZE, QR_SIZE), Image.LANCZOS)
    except Exception:
        qr_image = Image.new("RGBA", (QR_SIZE, QR_SIZE), (255, 255, 255, 255))

    # Vẽ khung cho QR code
    qr_frame = Image.new("RGBA", (QR_SIZE + 20, QR_SIZE + 20), (255, 255, 255, 255))
    draw_frame = ImageDraw.Draw(qr_frame)
    draw_frame.rectangle((0, 0, QR_SIZE + 20, QR_SIZE + 20), fill=(255, 255, 255, 255))
    qr_frame.paste(qr_image, (10, 10), qr_image)
    image.alpha_composite(qr_frame, (QR_PADDING - 10, (HEIGHT - QR_SIZE - 20) // 2))

    # Vẽ đường phân cách
    draw.line([(QR_SIZE + QR_PADDING * 2, 50), (QR_SIZE + QR_PADDING * 2, HEIGHT - 50)], fill=(255, 255, 255, 77), width=2)

    # Vẽ thông tin ngân hàng
    INFO_X = QR_SIZE + QR_PADDING * 3
    INFO_Y = 30
    LINE_HEIGHT = 50
    # Sử dụng font từ user_info.py
    font_title = get_font("font/Tapestry-Regular.ttf", 32)
    font_info = get_font("font/Tapestry-Regular.ttf", 28)
    emoji_font = get_font("font/NotoEmoji-Bold.ttf", 28)
    gradient_colors = random.choice(MULTICOLOR_GRADIENTS)

    # Vẽ tiêu đề
    draw_centered_text_mixed_line("THÔNG TIN CHUYỂN KHOẢN", INFO_Y, font_title, emoji_font, gradient_colors, draw, INFO_X, WIDTH - 50)
    INFO_Y += LINE_HEIGHT

    # Vẽ thông tin chi tiết
    fields = [
        f"Ngân hàng: {bank_info['name']}",
        f"STK: {account_number}",
        f"Chủ TK: {account_name}",
        f"Số tiền: {f'{int(amount):,}'.replace(',', '.') + ' VNĐ' if amount != '0' else 'Không có'}",
        f"Nội dung: {description[:20] + '...' if description and len(description) > 20 else description or 'Không có'}"
    ]

    overlay_color = random.choice(OVERLAY_COLORS)
    for field in fields:
        field_img = Image.new("RGBA", (WIDTH - INFO_X - 50, LINE_HEIGHT), (0, 0, 0, 0))
        draw_field = ImageDraw.Draw(field_img)
        draw_field.rounded_rectangle((0, 0, WIDTH - INFO_X - 50, LINE_HEIGHT), radius=10, fill=overlay_color)
        draw_centered_text_mixed_line(field, (LINE_HEIGHT - font_info.size) // 2, font_info, emoji_font, gradient_colors, draw_field, 0, WIDTH - INFO_X - 50)
        image.alpha_composite(field_img, (INFO_X, INFO_Y))
        INFO_Y += LINE_HEIGHT + 10

    # Thêm viền đa sắc
    final_image = add_multicolor_rectangle_border(image, MULTICOLOR_GRADIENT, border_thickness=3)
    final_image = final_image.convert("RGB")
    image_path = f"bank_card_{int(datetime.now().timestamp())}.jpg"
    final_image.save(image_path, quality=100)
    return image_path

# --------------------- XỬ LÝ LỆNH creat.bankcard ---------------------
def handle_bankinfo_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        content = message.replace(f"{PREFIX}creat.bankcard", "").strip()
        if not content:
            # Tạo danh sách ngân hàng hợp lệ
            valid_banks = sorted(set((key, info['name'], info['full_name']) for key, info in BANK_CODES.items()), key=lambda x: x[0])
            valid_banks_text = "\nDanh sách ngân hàng hợp lệ:\n" + "\n".join(
                f"{key} - {name} - {full_name}" for key, name, full_name in valid_banks[:30]
            )  # Giới hạn 10 ngân hàng để tránh quá dài
            error_msg = Message(text=f"Vui lòng nhập thông tin theo định dạng: {PREFIX}creat.bankcard | Tên_ngân_hàng | Số_tài_khoản | Tên_chủ_tài_khoản | Số_tiền | Nội_dung\n{valid_banks_text}")
            client.sendMessage(error_msg, thread_id, thread_type)
            return

        # Phản ứng nhanh
        client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)

        # Tách các trường bằng dấu |
        fields = [field.strip() for field in content.split("|")]
        if len(fields) != 6:  # Đảm bảo có đúng 6 trường (bao gồm lệnh creat.bankcard)
            # Tạo danh sách ngân hàng hợp lệ
            valid_banks = sorted(set((key, info['name'], info['full_name']) for key, info in BANK_CODES.items()), key=lambda x: x[0])
            valid_banks_text = "\nDanh sách ngân hàng hợp lệ:\n" + "\n".join(
                f"{key} - {name} - {full_name}" for key, name, full_name in valid_banks[:10]
            )  # Giới hạn 10 ngân hàng để tránh quá dài
            error_msg = Message(text=f"Định dạng không đúng! Vui lòng sử dụng: {PREFIX}creat.bankcard | [Tên ngân hàng] | [Số tài khoản] | [Tên chủ tài khoản] | [Số tiền] | [Nội dung]\n{valid_banks_text}")
            client.sendMessage(error_msg, thread_id, thread_type)
            return

        # Gán các trường
        bank_code = fields[1].lower()  # Tên ngân hàng
        account_number = fields[2]     # Số tài khoản
        account_name = fields[3]       # Tên chủ tài khoản
        amount = fields[4]             # Số tiền
        description = fields[5]        # Nội dung

        # Kiểm tra tên ngân hàng
        if bank_code not in BANK_CODES:
            # Tạo danh sách ngân hàng hợp lệ
            valid_banks = sorted(
                set((key, info['name'], info['full_name']) for key, info in BANK_CODES.items()),
                key=lambda x: x[0]
            )
            valid_banks_text = "\nDanh sách ngân hàng hợp lệ:\n" + "\n".join(
                f"{key} - {name} - {full_name}" for key, name, full_name in valid_banks[:10]
            )  # Giới hạn 10 ngân hàng
            suggestions = [info['name'] for key, info in BANK_CODES.items() if bank_code in key][:5]
            # Tránh dùng backslash bên trong biểu thức f-string
            if suggestions:
                suggestion_lines = "\n".join(suggestions)
                suggestion_text = "\nCác ngân hàng gần giống:\n" + suggestion_lines
            else:
                suggestion_text = ""
            error_msg = Message(text=f"Không tìm thấy tên ngân hàng hợp lệ!{suggestion_text}\n{valid_banks_text}")
            client.sendMessage(error_msg, thread_id, thread_type)
            return
        bank_info = {
            'bin': BANK_CODES[bank_code]['bin'],
            'name': BANK_CODES[bank_code]['name'],
            'word': bank_code
        }

        # Kiểm tra số tài khoản
        if not account_number.isdigit():
            error_msg = Message(text="Số tài khoản chỉ được chứa các chữ số!")
            client.sendMessage(error_msg, thread_id, thread_type)
            return

        # Chuẩn hóa tên chủ tài khoản và nội dung
        account_name = normalize_account_name(account_name) if account_name.strip() else "---"
        description = normalize_description(description) if description.strip() else ""

        # Kiểm tra số tiền
        if not amount.isdigit():
            amount = "0"  # Nếu số tiền không hợp lệ, đặt mặc định là 0

        # Lấy thông tin người dùng
        info_response = client.fetchUserInfo(author_id)
        profiles = info_response.unchanged_profiles or info_response.changed_profiles
        user_info = profiles[str(author_id)]

        # Tạo link VietQR
        vietqr_link = generate_vietqr_link(bank_info, account_number, account_name, amount, description)

        # Tạo ảnh
        image_path = create_bank_card_image(bank_info, account_number, account_name, amount, description, vietqr_link, user_info)

        # Gửi ảnh
        client.sendLocalImage(
            image_path,
            thread_id,
            thread_type,
            width=1000,
            height=400,
            message=Message(text=f"{user_info['zaloName']} đây là QR chuyển khoản mà bạn cần!"),
            ttl=600000
        )

        # Xóa file tạm
        if os.path.exists(image_path):
            os.remove(image_path)

    except ZaloAPIException as e:
        error_msg = Message(text="🔴 Có lỗi xảy ra khi lấy thông tin!")
        client.sendMessage(error_msg, thread_id, thread_type)
        print(f"Lỗi API: {e}")
    except Exception as e:
        error_msg = Message(text="🔴 Đã xảy ra lỗi!")
        client.sendMessage(error_msg, thread_id, thread_type)
        print(f"Lỗi: {e}")

def get_mitaizl():
    return {
        'creat.bankcard': handle_bankinfo_command
    }