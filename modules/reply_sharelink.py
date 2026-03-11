import re
import json
import threading
import time
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import os
from tempfile import NamedTemporaryFile
import random
import urllib.parse
import math
from datetime import datetime, timezone, timedelta
import colorsys
from zlapi.models import Message, MessageStyle, MultiMsgStyle, ThreadType, ZaloAPIException

# Constants
DEFAULT_IMAGE_URL = "https://f59-zpg-r.zdn.vn/jpg/8605264667460368029/51d6589f0c98bac6e389.jpg"
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
FONT_PATH = "font/5.otf"
EMOJI_FONT_PATH = "font/NotoEmoji-Bold.ttf"
BACKGROUND_FOLDER = 'gai'

# Load background images
print(f"Đang kiểm tra thư mục {BACKGROUND_FOLDER} để tải ảnh nền...")
BACKGROUND_IMAGES = [
    os.path.join(BACKGROUND_FOLDER, f) 
    for f in os.listdir(BACKGROUND_FOLDER) 
    if f.lower().endswith(('.jpg', '.jpeg', '.png'))
] if os.path.isdir(BACKGROUND_FOLDER) else []
print(f"Số lượng ảnh nền tải được: {len(BACKGROUND_IMAGES)}")

# Font cache
_FONT_CACHE = {}
def get_font(font_path, size):
    """Load font with caching."""
    key = (font_path, size)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = ImageFont.truetype(font_path, size)
    return _FONT_CACHE[key]

# Emoji pattern
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
    """Vẽ văn bản hỗn hợp với hiệu ứng gradient."""
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

def draw_centered_text_mixed_line(text, y, normal_font, emoji_font, gradient_colors, base_draw, region_x0, region_x1):
    """Tính toán vị trí căn giữa và vẽ văn bản hỗn hợp."""
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

def make_round_avatar(avatar):
    """Tăng sáng nhẹ và cắt avatar thành hình tròn."""
    print("Đang xử lý avatar thành hình tròn...")
    avatar = ImageEnhance.Brightness(avatar).enhance(1.2)
    w, h = avatar.size
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, w, h), fill=255)
    round_img = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    round_img.paste(avatar, (0, 0), mask)
    return round_img

def load_avatar(url, default_color=(200, 200, 200)):
    """Tải avatar từ URL, trả về ảnh mặc định nếu lỗi."""
    print(f"Đang tải avatar từ URL: {url}")
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        im = Image.open(BytesIO(r.content)).convert("RGBA")
        print("Avatar tải thành công")
        return im
    except Exception as e:
        print(f"Lỗi khi tải avatar: {e}, sử dụng avatar mặc định")
        return Image.new("RGBA", (150, 150), default_color+(255,))

def Dominant(image):
    """Tính màu chủ đạo của ảnh (từ da.py)."""
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

def get_random_gradient():
    """Chọn ngẫu nhiên một dải màu từ GRADIENT_SETS."""
    return random.choice(GRADIENT_SETS)

def create_custom_background(group_name, group_avatar_url, width=1944, height=1024):
    """Tạo nền tùy chỉnh với phong cách đồ họa từ da.py, căn giữa văn bản theo chiều dọc."""
    print(f"Tạo nền cho nhóm: {group_name}, avatar: {group_avatar_url}")
    size = (width, height)
    
    # Tạo nền ảnh
    if BACKGROUND_IMAGES:
        bg_path = random.choice(BACKGROUND_IMAGES)
        print(f"Chọn ảnh nền: {bg_path}")
        bg_image = Image.open(bg_path).convert("RGB").resize(size, Image.Resampling.LANCZOS)
        bg_image = bg_image.filter(ImageFilter.GaussianBlur(radius=20))
    else:
        print("Dùng nền màu xanh (130, 190, 255)")
        bg_image = Image.new("RGB", size, (130, 190, 255))
    bg_image = bg_image.convert("RGBA")
    
    # Tạo overlay
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Tính màu chủ đạo của ảnh nền
    dominant_color = Dominant(bg_image)
    luminance = (0.299 * dominant_color[0] + 0.587 * dominant_color[1] + 0.114 * dominant_color[2]) / 255
    
    # Chọn màu cho hình chữ nhật bo góc
    box_color = random.choice([
        (120, 200, 180, 100), (180, 140, 200, 100), (240, 180, 160, 100),
        (160, 200, 140, 100), (200, 160, 120, 100), (140, 180, 220, 100),
        (220, 200, 140, 100), (180, 180, 180, 105)
    ]) if luminance >= 0.5 else random.choice([
        (200, 140, 160, 105), (140, 120, 180, 105), (100, 140, 160, 105),
        (160, 140, 120, 105), (120, 160, 180, 105), (60, 60, 60, 80)
    ])
    
    # Vẽ hình chữ nhật bo góc
    box_x1, box_y1 = 60, 70
    box_x2, box_y2 = size[0] - 60, size[1] - 80
    draw.rounded_rectangle([(box_x1, box_y1), (box_x2, box_y2)], radius=100, fill=box_color)
    
    # Load font
    try:
        font_title = get_font(FONT_PATH, 120)
        font_group = get_font(FONT_PATH, 100)
        font_time = get_font(FONT_PATH, 65)
        font_icon = get_font(EMOJI_FONT_PATH, 65)
        font_designer = get_font(FONT_PATH, 65)
    except Exception as e:
        print(f"Lỗi khi load font: {e}")
        font_title = font_group = font_time = font_icon = font_designer = ImageFont.load_default()

    # Xử lý avatar
    avatar = load_avatar(group_avatar_url)
    avatar_size = 400
    avatar = avatar.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
    avatar = make_round_avatar(avatar)
    
    # Thêm viền cầu vồng cho avatar
    border_size = avatar_size + 20
    border_offset = (border_size - avatar_size) // 2
    rainbow_border = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
    draw_border = ImageDraw.Draw(rainbow_border)
    for i in range(360):
        h = i / 360
        r, g, b = colorsys.hsv_to_rgb(h, 0.5, 0.8)
        draw_border.arc([(3, 3), (border_size - 4, border_size - 4)], i, i + 1, fill=(int(r * 255), int(g * 255), int(b * 255), 255), width=6)
    overlay.paste(rainbow_border, (80 - border_offset, (height - border_size) // 2), rainbow_border)
    overlay.paste(avatar, (80, (height - avatar_size) // 2), avatar)
    print("Avatar đã xử lý và dán vào overlay")

    # Tính toán để căn giữa văn bản theo chiều dọc
    line_spacing = 50
    region_x0, region_x1 = 500, width - 50
    
    # Đo chiều cao của các dòng văn bản
    text_lines = ["CỘNG ĐỒNG", group_name]
    text_fonts = [font_title, font_group]
    total_text_height = 0
    for text, font in zip(text_lines, text_fonts):
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_height = text_bbox[3] - text_bbox[1]
        total_text_height += text_height
    total_text_height += line_spacing  # Thêm khoảng cách giữa các dòng
    
    # Tính tọa độ Y để căn giữa theo chiều dọc
    region_height = box_y2 - box_y1
    start_y = box_y1 + (region_height - total_text_height) // 2
    
    # Vẽ "CỘNG ĐỒNG"
    gradient_colors_title = get_random_gradient()
    draw_centered_text_mixed_line("CỘNG ĐỒNG", start_y, font_title, font_icon, gradient_colors_title, draw, region_x0, region_x1)
    print("Đã vẽ 'CỘNG ĐỒNG'")

    # Vẽ tên nhóm
    gradient_colors_group = get_random_gradient()
    draw_centered_text_mixed_line(group_name, start_y + line_spacing + (draw.textbbox((0, 0), "CỘNG ĐỒNG", font=font_title)[3] - draw.textbbox((0, 0), "CỘNG ĐỒNG", font=font_title)[1]), font_group, font_icon, gradient_colors_group, draw, region_x0, region_x1)
    print("Đã vẽ tên nhóm")

    # Vẽ thời gian
    time_line = datetime.now(timezone(timedelta(hours=7))).strftime("%H:%M %d-%m")
    left_info = f"⏰ {time_line}"
    text_bbox = draw.textbbox((0, 0), left_info, font=font_time)
    text_h = text_bbox[3] - text_bbox[1]
    left_x = box_x1 + 150
    left_y = height - text_h - 5
    draw_mixed_gradient_text(
        draw,
        text=left_info,
        position=(left_x, left_y),
        normal_font=font_time,
        emoji_font=font_icon,
        gradient_colors=MULTICOLOR_GRADIENT,
        shadow_offset=(2, 2)
    )
    print("Đã vẽ thời gian")

    # Vẽ logo và chữ "design by Minh Vũ Shinn Cte"
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
            logo_x = box_x1 + 50
            logo_y = height - logo_size - 5
            overlay.paste(round_logo, (logo_x, logo_y), round_logo)
            print("Đã dán logo")
        except Exception as e:
            print(f"Lỗi khi xử lý logo zalo.png: {e}")

    designer_text = "design by Minh Vũ Shinn Cte"
    text_bbox = draw.textbbox((0, 0), designer_text, font=font_designer)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]
    designer_x = box_x2 - text_w - 20
    designer_y = height - text_h - 25
    draw_mixed_gradient_text(
        draw,
        text=designer_text,
        position=(designer_x, designer_y),
        normal_font=font_designer,
        emoji_font=font_icon,
        gradient_colors=get_random_gradient(),
        shadow_offset=(2, 2)
    )
    print("Đã vẽ 'design by Minh Vũ Shinn Cte'")

    # Kết hợp nền và overlay
    final_image = Image.alpha_composite(bg_image, overlay).convert("RGB")
    print("Ảnh chuyển sang RGB")
    
    with NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
        final_image.save(tmp_file.name, format='JPEG', quality=95)
        print(f"Ảnh lưu tại: {tmp_file.name}")
        return final_image, tmp_file.name

def upload_to_uguuse(file_path):
    """Tải ảnh lên Uguu.se và trả về URL."""
    print(f"Đang tải ảnh lên Uguu.se từ {file_path}")
    try:
        with open(file_path, 'rb') as f:
            files = {'files[]': (os.path.basename(file_path), f, 'image/jpeg')}
            response = requests.post("https://uguu.se/upload.php", files=files)
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('success') and response_data.get('files'):
                    print(f"Đã tải ảnh lên thành công, URL: {response_data['files'][0]['url']}")
                    return response_data['files'][0]['url']
                print("Tải ảnh lên thất bại, không tìm thấy URL")
                return None
            print(f"Tải ảnh lên thất bại, mã trạng thái: {response.status_code}")
            return None
    except Exception as e:
        print(f"Lỗi khi tải lên Uguu.se: {e}")
        return None

def send_message_with_style(client, text, thread_id, thread_type, ttl=60000, color="#2e86de"):
    """Gửi tin nhắn với định dạng màu và font."""
    print(f"Đang gửi tin nhắn với nội dung: {text}")
    base_length = len(text)
    adjusted_length = base_length + 355
    style = MultiMsgStyle([
        MessageStyle(offset=0, length=adjusted_length, style="color", color=color, auto_format=False),
        MessageStyle(offset=0, length=adjusted_length, style="font", size="8", auto_format=False)
    ])
    msg = Message(text=text, style=style)
    client.send(msg, thread_id=thread_id, thread_type=thread_type, ttl=ttl)
    print("Tin nhắn đã được gửi")

def send_link_to_group(client, link_url, thumbnail_url, title, domain_url, desc, thread_id):
    """Gửi link đến nhóm."""
    print(f"Bắt đầu gửi link đến nhóm {thread_id}")
    print(f"Thông tin link: URL={link_url}, Thumbnail={thumbnail_url}, Title={title}, Domain={domain_url}, Desc={desc}")
    try:
        if not thumbnail_url or not thumbnail_url.startswith(('http://', 'https://')):
            print(f"Thumbnail URL không hợp lệ: {thumbnail_url}")
            raise Exception("Thumbnail URL không hợp lệ")
        
        client.sendLink(
            linkUrl=link_url,
            title=title,
            thread_id=thread_id,
            thread_type=ThreadType.GROUP,
            domainUrl=domain_url,
            desc=desc,
            thumbnailUrl=thumbnail_url,
            ttl=600000
        )
        print(f"Đã gửi link đến nhóm {thread_id} thành công")
    except Exception as e:
        print(f"Lỗi khi gửi link đến nhóm {thread_id}: {e}")

def get_excluded_group_ids(filename="danhsachnhom.json"):
    """Đọc tệp JSON và trả về tập hợp các group_id cần loại trừ."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            groups = json.load(f)
            return {grp.get("group_id") for grp in groups if "group_id" in grp}
    except Exception as e:
        print(f"Lỗi khi đọc file {filename}: {e}")
        return set()

def start_sharelink(client, link_url, thumbnail_url, title, domain_url, desc, thread_id, thread_type, group_avatar_url, group_name):
    """Chia sẻ link đến tất cả nhóm được phép, trừ các nhóm trong danhsachnhom.json."""
    print(f"Bắt đầu chia sẻ link, thread_id hiện tại: {thread_id}")
    try:
        excluded_group_ids = get_excluded_group_ids()
        all_groups = client.fetchAllGroups()
        allowed_thread_ids = [gid for gid in all_groups.gridVerMap.keys() if gid != thread_id and gid not in excluded_group_ids]
        print(f"Số nhóm được phép gửi: {len(allowed_thread_ids)} (đã loại trừ các nhóm trong danhsachnhom.json)")

        for group_id in allowed_thread_ids:
            print(f"Đang gửi đến nhóm {group_id}")
            try:
                send_link_to_group(client, link_url, thumbnail_url, title, domain_url, desc, group_id)
                time.sleep(3)  # Độ trễ 3 giây giữa các lần gửi
            except Exception as e:
                print(f"Lỗi khi gửi link đến nhóm {group_id}: {e}")

        send_message_with_style(client, "✅ Hoàn thành gửi link mời nhóm đến tất cả nhóm!", thread_id, thread_type)
        print("Đã hoàn thành gửi link đến tất cả nhóm.")
    except Exception as e:
        print(f"Lỗi trong quá trình gửi link: {e}")
        send_message_with_style(client, f"🚫 Lỗi khi gửi link: {e}", thread_id, thread_type)

def handle_reply_sharelink_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh reply.sharelink."""
    print(f"[START] Xử lý lệnh reply từ author_id: {author_id} trong thread: {thread_id}")
    # Gửi phản ứng xác nhận
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    # Lấy thông tin từ tin nhắn được reply
    print(f"Đang lấy thông tin từ message_object: {message_object}")
    content = message_object.content
    print(f"Nội dung tin nhắn: {content}")
    if not message_object.quote or not message_object.quote.get('attach'):
        print("Không tìm thấy thông tin tin nhắn được reply!")
        send_message_with_style(client, "🚫 Không tìm thấy thông tin link để chia sẻ!", thread_id, thread_type)
        return

    try:
        # Giải mã dữ liệu từ tin nhắn reply
        attach_data = json.loads(message_object.quote['attach'])
        print(f"Thông tin attach giải mã: {json.dumps(attach_data, indent=2, ensure_ascii=False)}")
        params = json.loads(attach_data.get("params", "{}"))
        link_url = attach_data.get("href") or attach_data.get("title", "")
        title_url = attach_data.get("title", "")  # URL nhóm từ trường title
        print(f"Link URL lấy được: {link_url}")
        print(f"Title URL lấy được: {title_url}")
        title = params.get("mediaTitle", "Không xác định")
        print(f"Tiêu đề lấy được: {title}")
        domain_url = attach_data.get("src", "zalo.me")
        print(f"Tên miền: {domain_url}")
        desc = "Bấm vào ảnh để tham gia nhóm"
        print(f"Mô tả: {desc}")

        # Lấy và giải mã tên nhóm từ mediaTitle
        group_name = params.get("mediaTitle", "Không xác định")
        group_name = group_name.replace("\\/", "/")
        print(f"Tên nhóm lấy từ mediaTitle (sau xử lý): {group_name}")

        # Giải mã URL nếu cần
        link_url = urllib.parse.unquote(link_url)
        title_url = urllib.parse.unquote(title_url)
        print(f"Link URL sau khi giải mã: {link_url}")
        print(f"Title URL sau khi giải mã: {title_url}")

        # Lấy ID nhóm từ title_url
        print(f"[INFO] Đang lấy ID nhóm từ: {title_url}")
        group_info = client.getiGroup(title_url)
        if not isinstance(group_info, dict) or 'groupId' not in group_info:
            print(f"[ERROR] Không lấy được thông tin nhóm từ: {title_url}")
            send_message_with_style(client, f"🚫 Không lấy được ID nhóm từ {title_url}", thread_id, thread_type)
            return
        group_id = group_info['groupId']
        print(f"[SUCCESS] Lấy được Group ID {group_id} từ: {title_url}")

        # Lấy avatar nhóm từ group_id
        group = client.fetchGroupInfo(group_id).gridInfoMap[group_id]
        group_avatar_url = group.avt if group.avt else DEFAULT_IMAGE_URL
        print(f"Avatar URL lấy từ nhóm ID {group_id}: {group_avatar_url}")

        print(f"Tạo thumbnail cho nhóm {group_name}")
        thumbnail, thumbnail_path = create_custom_background(group_name, group_avatar_url)
        print(f"Thumbnail lưu tại: {thumbnail_path}")

        print(f"Tải thumbnail lên Uguu.se từ {thumbnail_path}")
        thumbnail_url = upload_to_uguuse(thumbnail_path)
        if not thumbnail_url:
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
                print(f"Đã xóa file tạm {thumbnail_path}")
            raise Exception("Không thể tải thumbnail lên Uguu.se")
        print(f"Thumbnail URL: {thumbnail_url}")
        # Thông báo bắt đầu gửi với định dạng
        print(f"Đang gửi thông báo bắt đầu cho thread {thread_id}")
        send_message_with_style(client, "⏳ Đang bắt đầu gửi link mời nhóm đến các nhóm...", thread_id, thread_type)

        # Khởi chạy gửi link trong thread riêng
        print(f"Khởi tạo thread để gửi link với tham số: link_url={link_url}, thumbnail_url={thumbnail_url}, title={title}")
        threading.Thread(
            target=start_sharelink,
            args=(client, link_url, thumbnail_url, title, domain_url, desc, thread_id, thread_type, group_avatar_url, group_name),
            daemon=True
        ).start()

        # Dọn dẹp file tạm
        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
            print(f"Đã xóa file tạm {thumbnail_path}")
    except Exception as e:
        print(f"Lỗi khi xử lý: {str(e)}")
        send_message_with_style(client, f"🚫 Lỗi khi xử lý: {str(e)}", thread_id, thread_type)
        if 'thumbnail_path' in locals() and os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
            print(f"Đã xóa file tạm {thumbnail_path} sau lỗi")

def get_mitaizl():
    """Trả về danh sách lệnh hỗ trợ."""
    print("Đang trả về danh sách lệnh hỗ trợ")
    return {
        'reply.sharelink': handle_reply_sharelink_command
    }
