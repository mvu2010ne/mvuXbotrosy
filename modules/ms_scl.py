import os
import re
import time
import random
import requests
import urllib.parse
import io
import math
import json
import subprocess
from zlapi import *
from zlapi.models import *
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter, ImageOps
from io import BytesIO
from cachetools import LRUCache
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from colorsys import rgb_to_hsv, hsv_to_rgb

# ---------------------------
# Biến toàn cục
# ---------------------------
song_search_results = {}  # Lưu danh sách bài hát theo thread_id
search_status = {}        # Lưu trạng thái tìm kiếm: (time_search_sent, has_selected, msg_id, thread_type)
PLATFORM = "soundcloud"
TIME_TO_SELECT = 60000
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
CLIENT_ID_CACHE = None
MEDIA_CACHE = LRUCache(maxsize=500)  # Bộ nhớ đệm cho URL âm thanh đã tải lên

# Các hằng số cấu hình (giữ nguyên từ mã gốc)
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

BACKGROUND_FOLDER = 'backgrounds'
if os.path.isdir(BACKGROUND_FOLDER):
    BACKGROUND_IMAGES = [
        os.path.join(BACKGROUND_FOLDER, f) 
        for f in os.listdir(BACKGROUND_FOLDER) 
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ]
else:
    BACKGROUND_IMAGES = []

# ---------------------------
# Các hàm hỗ trợ chung (giữ nguyên từ mã gốc)
# ---------------------------
def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Referer": "https://soundcloud.com/",
        "Connection": "keep-alive"
    }

def get_gradient_color(colors, ratio):
    if ratio <= 0:
        return colors[0]
    if ratio >= 1:
        return colors[-1]
    total_segments = len(colors) - 1
    segment = int(ratio * total_segments)
    segment_ratio = (ratio * total_segments) - segment
    c1, c2 = colors[segment], colors[segment + 1]
    return (
        int(c1[0] * (1 - segment_ratio) + c2[0] * segment_ratio),
        int(c1[1] * (1 - segment_ratio) + c2[1] * segment_ratio),
        int(c1[2] * (1 - segment_ratio) + c2[2] * segment_ratio)
    )

def interpolate_colors(colors, text_length, change_every):
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

def split_text_by_emoji(text):
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

def add_multicolor_rectangle_border(image, colors, border_thickness=4):
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

def draw_rounded_rectangle(draw, xy, radius, fill, outline=None, width=1):
    x1, y1, x2, y2 = xy
    draw.pieslice([x1, y1, x1 + 2*radius, y1 + 2*radius], 180, 270, fill=fill, outline=outline)
    draw.pieslice([x2 - 2*radius, y1, x2, y1 + 2*radius], 270, 360, fill=fill, outline=outline)
    draw.pieslice([x1, y2 - 2*radius, x1 + 2*radius, y2], 90, 180, fill=fill, outline=outline)
    draw.pieslice([x2 - 2*radius, y2 - 2*radius, x2, y2], 0, 90, fill=fill, outline=outline)
    draw.rectangle([x1+radius, y1, x2-radius, y1+radius], fill=fill, outline=outline)
    draw.rectangle([x1, y1+radius, x2, y2-radius], fill=fill, outline=outline)
    draw.rectangle([x1+radius, y2-radius, x2-radius, y2], fill=fill, outline=outline)

def add_multicolor_circle_border(image, colors, border_thickness=3):
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

def wrap_text(text, font, max_width, draw):
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines

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

def FetchImage(url):
    if not url:
        return None
    try:
        if url.startswith('data:image'):
            h, e = url.split(',', 1)
            i = base64.b64decode(e)
            return Image.open(BytesIO(i)).convert("RGB")
        r = requests.get(url, stream=True, timeout=10, verify=False)
        r.raise_for_status()
        return Image.open(BytesIO(r.content)).convert("RGB")
    except:
        return None

def BackgroundGetting(width=680, height=880):
    if BACKGROUND_IMAGES:
        bg_path = random.choice(BACKGROUND_IMAGES)
        bg = Image.open(bg_path).convert("RGB")
        bg = bg.resize((width, height), Image.Resampling.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=10))
        return bg
    else:
        return Image.new("RGB", (width, height), (130, 190, 255))

def create_song_list_image(songs, max_show=20):
    songs_to_show = songs[:min(max_show, len(songs))]
    num_songs = len(songs_to_show)
    
    # ==================== THIẾT LẬP KÍCH THƯỚC ====================
    scale = 2
    card_height = 105 * scale
    card_width = 583 * scale
    thumb_size = 90 * scale
    padding = 20 * scale
    spacing_y = 10 * scale
    card_padding = 8 * scale
    column_spacing = 20 * scale
    header_height = 60 * scale
    
    songs_per_column = 10
    num_columns = (num_songs - 1) // songs_per_column + 1
    
    img_width = padding * 2 + num_columns * card_width + (num_columns - 1) * column_spacing
    img_height = padding * 2 + header_height + songs_per_column * card_height + (songs_per_column - 1) * spacing_y
    
    # ==================== TẠO NỀN VÀ CANVAS ====================
    bg_image = BackgroundGetting(img_width, img_height)
    image = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
    image.paste(bg_image.convert("RGBA"), (0, 0))
    draw = ImageDraw.Draw(image)
    
    # ==================== TẢI FONT ====================
    try:
        font_title = ImageFont.truetype("font/5.otf", 28 * scale)
        font_artist = ImageFont.truetype("font/5.otf", 20 * scale)
        font_info = ImageFont.truetype("font/5.otf", 20 * scale)
        # SỬA: Sử dụng indexaSin2.otf cho số thứ tự
        font_index = ImageFont.truetype("font/indexaSin2.otf", 70 * scale)  # CHỈ SỬA DÒNG NÀY
        font_header = ImageFont.truetype("font/5.otf", 50 * scale)
        emoji_font = ImageFont.truetype("font/NotoEmoji-Bold.ttf", 28 * scale)
        emoji_font_small = ImageFont.truetype("font/NotoEmoji-Bold.ttf", 21 * scale)
    except:
        # Fallback nếu không tìm thấy indexaSin2.otf
        try:
            font_index = ImageFont.truetype("font/5.otf", 50 * scale)
        except:
            font_index = ImageFont.load_default()
        font_title = font_artist = font_info = font_header = emoji_font = emoji_font_small = ImageFont.load_default()
    
    # ==================== HÀM HỖ TRỢ ====================
    def get_text_width(text, font):
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0]
    
    # Hàm draw_mixed_gradient_text đơn giản
    def draw_mixed_gradient_text_simple(draw, position, text, font, emoji_font, gradient_colors, shadow_offset=(1, 1)):
        if not text:
            return
        
        x, y = position
        shadow_color = (0, 0, 0, 150)
        
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
        
        char_index = 0
        segments = split_text_by_emoji(text)
        
        for seg, is_emoji in segments:
            current_font = emoji_font if is_emoji else font
            for ch in seg:
                draw.text((x + shadow_offset[0], y + shadow_offset[1]), ch, 
                         font=current_font, fill=shadow_color)
                draw.text((x, y), ch, font=current_font, fill=color_list[char_index])
                
                bbox = draw.textbbox((0, 0), ch, font=current_font)
                char_width = bbox[2] - bbox[0]
                x += char_width
                char_index += 1
    
    def truncate_text_gradient(text, max_width, font_text, font_emoji, gradient_colors):
        if not text:
            return "", []
        
        import emoji
        result = ""
        result_colors = []
        current_width = 0
        
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
        
        char_index = 0
        segments = split_text_by_emoji(text)
        
        for seg, is_emoji in segments:
            current_font = font_emoji if is_emoji else font_text
            for ch in seg:
                char_width = get_text_width(ch, current_font)
                
                if current_width + char_width > max_width - get_text_width('..', font_text):
                    if result:
                        result += ".."
                        result_colors.append(color_list[char_index])
                        result_colors.append(color_list[char_index])
                    return result, result_colors
                
                result += ch
                result_colors.append(color_list[char_index])
                current_width += char_width
                char_index += 1
        
        return result, result_colors
    
    # ==================== HEADER ====================
    header_text = "DANH SÁCH BÀI HÁT"
    header_width = get_text_width(header_text, font_header)
    header_x = (img_width - header_width) // 2
    header_y = padding
    
    draw_mixed_gradient_text(
        draw, header_text, (header_x, header_y), 
        font_header, emoji_font, 
        random.choice(GRADIENT_SETS), 
        shadow_offset=(3, 3)
    )
    
    # ==================== CHUẨN BỊ ẢNH THUMBNAIL TỪ BACKGROUNDS ====================
    # Lấy danh sách ảnh từ thư mục backgrounds (giống BackgroundGetting)
    background_images = []
    if os.path.isdir(BACKGROUND_FOLDER):
        background_images = [
            os.path.join(BACKGROUND_FOLDER, f) 
            for f in os.listdir(BACKGROUND_FOLDER) 
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ]
    
    # Tạo danh sách thumbnail images
    thumbnail_images = []
    for song in songs_to_show:
        img = None
        
        # Thử tải ảnh từ URL
        if song[2]:  # cover_url
            try:
                resp = requests.get(song[2], timeout=10, verify=False)
                resp.raise_for_status()
                img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
            except:
                img = None
        
        # Nếu không tải được từ URL, lấy ảnh ngẫu nhiên từ backgrounds
        if img is None:
            if background_images:
                try:
                    # Chọn ảnh ngẫu nhiên từ thư mục backgrounds
                    random_bg_path = random.choice(background_images)
                    img = Image.open(random_bg_path).convert("RGBA")
                except:
                    img = None
        
        # Xử lý ảnh (giống các ảnh khác)
        if img is not None:
            try:
                # Resize đúng kích thước
                img = img.resize((thumb_size, thumb_size), Image.LANCZOS)
                
                # Tạo mask hình tròn
                mask = Image.new("L", (thumb_size, thumb_size), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, thumb_size, thumb_size), fill=255)
                img.putalpha(mask)
                
                # Thêm viền gradient MULTICOLOR (giống các ảnh khác)
                img = add_multicolor_circle_border(img, MULTICOLOR_GRADIENT, border_thickness=3)
            except:
                img = None
        
        # Nếu vẫn không có ảnh, tạo ảnh mặc định đơn giản
        if img is None:
            img = Image.new("RGBA", (thumb_size, thumb_size), (100, 100, 100, 255))
            draw_img = ImageDraw.Draw(img)
            draw_img.ellipse((0, 0, thumb_size, thumb_size), fill=(100, 100, 100, 255))
            img = add_multicolor_circle_border(img, MULTICOLOR_GRADIENT, border_thickness=3)
        
        thumbnail_images.append(img)
    
    # ==================== VẼ DANH SÁCH BÀI HÁT ====================
    for col in range(num_columns):
        start_idx = col * songs_per_column
        end_idx = min(start_idx + songs_per_column, num_songs)
        column_songs = songs_to_show[start_idx:end_idx]
        
        left = padding + col * (card_width + column_spacing)
        
        for i, song in enumerate(column_songs):
            url, title, cover, artist, duration, is_official, is_hd, song_id, track_auth = song
            thumb = thumbnail_images[start_idx + i]
            
            # Vị trí card
            top = padding + header_height + i * (card_height + spacing_y)
            
            # ========== VẼ CARD BACKGROUND ==========
            card_overlay = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
            card_draw = ImageDraw.Draw(card_overlay)
            
            # Lấy dominant color từ background để chọn màu card
            dominant_color = Dominant(bg_image)
            luminance = (0.299 * dominant_color[0] + 0.587 * dominant_color[1] + 0.114 * dominant_color[2]) / 255
            
            if luminance >= 0.5:
                box_color = random.choice([
                    (120, 200, 180, 100), (180, 140, 200, 100), (240, 180, 160, 100),
                    (160, 200, 140, 100), (200, 160, 120, 100), (140, 180, 220, 100),
                    (220, 200, 140, 100), (180, 180, 180, 105)
                ])
            else:
                box_color = random.choice([
                    (200, 140, 160, 105), (140, 120, 180, 105), (100, 140, 160, 105),
                    (160, 140, 120, 105), (120, 160, 180, 105), (60, 60, 60, 80)
                ])
            
            radius = 20 * scale
            card_draw.rounded_rectangle([0, 0, card_width, card_height], radius=radius, fill=box_color)
            image.paste(card_overlay, (left, top), card_overlay.split()[3])
            
            # ========== VẼ THUMBNAIL ==========
            thumb_y = top + (card_height - thumb_size) // 2
            image.paste(thumb, (left + card_padding, thumb_y), thumb)
            
            # ========== VẼ THÔNG TIN BÀI HÁT ==========
            x_text = left + card_padding + thumb_size + 20 * scale
            y_title = top + card_padding
            
            max_text_width = card_width - thumb_size - 3 * card_padding - 80 * scale
            
            # 1. TIÊU ĐỀ VỚI GRADIENT
            gradient_colors_title = random.choice(GRADIENT_SETS)
            truncated_title, title_colors = truncate_text_gradient(
                title, max_text_width, font_title, emoji_font, gradient_colors_title
            )
            
            if truncated_title:
                x_title = x_text
                y_title_pos = y_title
                shadow_color = (0, 0, 0, 150)
                
                char_index = 0
                segments = split_text_by_emoji(truncated_title)
                
                for seg, is_emoji in segments:
                    current_font = emoji_font if is_emoji else font_title
                    for ch in seg:
                        draw.text((x_title + 1, y_title_pos + 1), ch, 
                                 font=current_font, fill=shadow_color)
                        draw.text((x_title, y_title_pos), ch, 
                                 font=current_font, fill=title_colors[char_index] if char_index < len(title_colors) else gradient_colors_title[-1])
                        
                        bbox = draw.textbbox((0, 0), ch, font=current_font)
                        char_width = bbox[2] - bbox[0]
                        x_title += char_width
                        char_index += 1
            
            # 2. NGHỆ SĨ VỚI GRADIENT
            y_artist = y_title + int(35 * scale)
            gradient_colors_artist = random.choice(GRADIENT_SETS)
            
            max_artist_width = max_text_width
            artist_truncated = artist
            if get_text_width(artist, font_artist) > max_artist_width:
                while get_text_width(artist_truncated + "...", font_artist) > max_artist_width and artist_truncated:
                    artist_truncated = artist_truncated[:-1]
                artist_truncated += "..."
            
            draw_mixed_gradient_text_simple(
                draw, (x_text, y_artist), artist_truncated,
                font_artist, emoji_font_small, gradient_colors_artist,
                shadow_offset=(1, 1)
            )
            
            # 3. THÔNG TIN (Duration, Tags)
            stats = []
            if is_official: stats.append("✅ Official")
            if is_hd: stats.append("🎥 HD")
            if duration: stats.append(f"⏳ {duration}")
            
            info_text = " • ".join(stats) if stats else ""
            info_height = font_info.size
            y_info = top + card_height - card_padding - info_height - 4 * scale
            
            if info_text:
                gradient_colors_info = random.choice(GRADIENT_SETS)
                draw_mixed_gradient_text_simple(
                    draw, (x_text, y_info), info_text,
                    font_info, emoji_font_small, gradient_colors_info,
                    shadow_offset=(1, 1)
                )
            
            # ========== VẼ SỐ THỨ TỰ ==========
            number_text = str(start_idx + i + 1)
            number_width = get_text_width(number_text, font_index)

            # Vị trí số thứ tự (góc phải card)
            number_x = left + card_width - number_width - card_padding
            number_y = top + (card_height - font_index.size) // 2

            # MÀU XANH LÁ SÁNG CỐ ĐỊNH
            bright_green = (100, 255, 100)  # Màu xanh lá sáng

            # Vẽ số với màu xanh lá cố định
            x_num = number_x
            for char in number_text:
                # Vẽ bóng đen
                draw.text((x_num + 2, number_y + 2), char, 
                         font=font_index, fill=(0, 0, 0, 150))
                # Vẽ số với màu xanh lá sáng
                draw.text((x_num, number_y), char, 
                         font=font_index, fill=bright_green)
                
                # Di chuyển vị trí cho chữ số tiếp theo
                char_width = get_text_width(char, font_index)
                x_num += char_width
    
    # ==================== THÊM VIỀN VÀ LƯU ẢNH ====================
    image = add_multicolor_rectangle_border(image, MULTICOLOR_GRADIENT, border_thickness=4)
    image = image.convert("RGB")
    
    output_path = "song_list_scl.jpg"
    os.makedirs("cache", exist_ok=True)
    image.save(output_path, quality=95)
    
    return output_path, image.width, image.height

def convert_mp3_to_m4a(mp3_path, title="song"):
    if not mp3_path or not os.path.exists(mp3_path):
        return None
    safe_title = re.sub(r'[<>:"/\\|?*]', '', title)[:50]
    m4a_path = f"cache/{safe_title}.m4a"
    try:
        cmd = [
            'ffmpeg', '-i', mp3_path,
            '-c:a', 'aac', '-b:a', '128k',
            '-vn', '-y', m4a_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0 and os.path.exists(m4a_path):
            print(f"[CONVERT] MP3 → M4A: {m4a_path}")
            return m4a_path
        else:
            print(f"[ERROR] FFmpeg: {result.stderr}")
            return None
    except Exception as e:
        print(f"[ERROR] Chuyển đổi thất bại: {e}")
        return None
        
def create_song_cover_image(title, artist, duration, is_official, is_hd, cover_url):
    try:
        import os
        import requests
        from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
        from io import BytesIO
        import random
        from datetime import datetime, timezone, timedelta
        import colorsys
        import glob
        import math
        
        # ==================== KÍCH THƯỚC VÀ ĐƯỜNG DẪN ====================
        BACKGROUND_PATH = "backgrounds"
        CACHE_PATH = "cache"
        
        # Font paths - THÊM FONT EMOJI
        font_path_5 = "font/5.otf"
        font_emoji_path = "font/NotoEmoji-Bold.ttf"  # Font emoji từ ms.scl.py
        
        # Kích thước giống soundcloud.py
        size = (2560, 800)
        final_size = (1280, 400)
        
        # ==================== TẠO NỀN ====================
        # ==================== TẠO NỀN ====================
        bg_image = None
        if cover_url:
            try:
                response = requests.get(cover_url, timeout=10, verify=False)
                if response.status_code == 200:
                    bg_image = Image.open(BytesIO(response.content)).convert("RGBA").resize(size, Image.Resampling.LANCZOS)
                    bg_image = bg_image.filter(ImageFilter.GaussianBlur(radius=30))
                    print(f"[DEBUG] Đã tải ảnh nền từ URL: {cover_url}")
                else:
                    print(f"[DEBUG] Không thể tải ảnh nền từ URL (status {response.status_code}): {cover_url}")
                    bg_image = None
            except Exception as e:
                print(f"[DEBUG] Lỗi khi tải ảnh nền từ URL: {e}")
                bg_image = None

        # Nếu không tải được ảnh nền từ URL, sử dụng ảnh từ thư mục backgrounds
        if bg_image is None:
            try:
                if not os.path.exists(BACKGROUND_PATH):
                    print(f"[ERROR] Thư mục {BACKGROUND_PATH} không tồn tại")
                    # Không return, tiếp tục fallback
                else:
                    images = glob.glob(os.path.join(BACKGROUND_PATH, "*.jpg")) + \
                             glob.glob(os.path.join(BACKGROUND_PATH, "*.png")) + \
                             glob.glob(os.path.join(BACKGROUND_PATH, "*.jpeg"))
                    
                    if images:
                        image_path = random.choice(images)
                        print(f"[DEBUG] Sử dụng ảnh nền từ backgrounds: {image_path}")
                        
                        bg_image = Image.open(image_path).convert("RGBA").resize(size, Image.Resampling.LANCZOS)
                        bg_image = bg_image.filter(ImageFilter.GaussianBlur(radius=30))
                    else:
                        print(f"[DEBUG] Không tìm thấy ảnh trong thư mục {BACKGROUND_PATH}")
            except Exception as e:
                print(f"[DEBUG] Lỗi khi mở ảnh nền từ backgrounds: {e}")

        # Fallback cuối cùng: tạo ảnh nền mặc định
        if bg_image is None:
            print("[DEBUG] Sử dụng ảnh nền mặc định")
            bg_image = Image.new("RGBA", size, (130, 190, 255, 255))  # Màu xanh dương nhạt
            bg_image = bg_image.filter(ImageFilter.GaussianBlur(radius=30))
        
        # ==================== TẠO OVERLAY ====================
        overlay = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # ==================== TẢI FONT (THÊM FONT EMOJI) ====================
        try:
            font_title = ImageFont.truetype(font_path_5, 100)
            font_artist = ImageFont.truetype(font_path_5, 80)
            font_info = ImageFont.truetype(font_path_5, 70)
            # THÊM FONT EMOJI
            font_emoji = ImageFont.truetype(font_emoji_path, 70)
        except Exception as e:
            print(f"[WARNING] Lỗi tải font: {e}")
            font_title = font_artist = font_info = font_emoji = ImageFont.load_default()
        
        # ==================== HÀM VIỀN ĐA SẮC ====================
        def get_gradient_color(colors, ratio):
            if ratio <= 0:
                return colors[0]
            if ratio >= 1:
                return colors[-1]
            total_segments = len(colors) - 1
            segment = int(ratio * total_segments)
            segment_ratio = (ratio * total_segments) - segment
            c1, c2 = colors[segment], colors[segment + 1]
            return (
                int(c1[0] * (1 - segment_ratio) + c2[0] * segment_ratio),
                int(c1[1] * (1 - segment_ratio) + c2[1] * segment_ratio),
                int(c1[2] * (1 - segment_ratio) + c2[2] * segment_ratio)
            )
        
        def add_multicolor_circle_border(image, colors, border_thickness=3):
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
        
        def add_multicolor_rectangle_border(image, colors, border_thickness=4):
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
        
        # ==================== VẼ BOX ====================
        box_x1, box_y1 = 80, 60
        box_x2, box_y2 = size[0] - 80, size[1] - 60
        
        # PHONG CÁCH MÀU SẮC NHƯ CŨ (TỪ MS.SCL.PY)
        box_color_choices = [
            (120, 200, 180, 100), (180, 140, 200, 100), (240, 180, 160, 100),
            (160, 200, 140, 100), (200, 160, 120, 100), (140, 180, 220, 100),
            (220, 200, 140, 100), (180, 180, 180, 105)
        ]
        box_color = random.choice(box_color_choices)
        
        draw.rounded_rectangle([(box_x1, box_y1), (box_x2, box_y2)], radius=120, fill=box_color)
        
        # ==================== HÀM VẼ CHỮ CÓ BÓNG ====================
        def draw_text_with_shadow(draw, position, text, font, fill, shadow_offset=(4, 4), shadow_fill=(0, 0, 0, 150)):
            x, y = position
            draw.text((x + shadow_offset[0], y + shadow_offset[1]), text, font=font, fill=shadow_fill)
            draw.text((x, y), text, font=font, fill=fill)
        
        # ==================== HÀM VẼ TEXT CÓ EMOJI ====================
        def draw_mixed_text(draw, position, text, normal_font, emoji_font, fill_color):
            x, y = position
            for char in text:
                # Kiểm tra nếu là emoji (unicode > 0xFFFF)
                if ord(char) > 0xFFFF:
                    font_to_use = emoji_font
                else:
                    font_to_use = normal_font
                
                # Vẽ bóng
                draw.text((x + 2, y + 2), char, font=font_to_use, fill=(0, 0, 0, 150))
                # Vẽ chữ
                draw.text((x, y), char, font=font_to_use, fill=fill_color)
                
                # Di chuyển vị trí
                bbox = draw.textbbox((0, 0), char, font=font_to_use)
                char_width = bbox[2] - bbox[0]
                x += char_width
        
        # ==================== CHUẨN BỊ TEXT ====================
        vietnam_now = datetime.now(timezone(timedelta(hours=7)))
        formatted_time = vietnam_now.strftime("%H:%M %p")
        
        plays = random.randint(1000, 1000000)
        likes = random.randint(100, 100000)
        comments = random.randint(10, 10000)
        
        # DÙNG ICON EMOJI NHƯ SOUNDCLOUD.PY
        text_lines = [
            f"{title[:40]}{'...' if len(title) > 40 else ''}",
            f"{artist[:30]}{'...' if len(artist) > 30 else ''}",
            f"🎧 {plays:,} 💘 {likes:,} 💬 {comments:,}",  # Icon emoji
            f"⏰ {formatted_time}"  # Icon đồng hồ
        ]
        
        # PHONG CÁCH MÀU SẮC NHƯ MS.SCL.PY
        gradient_set = random.choice(GRADIENT_SETS)
        title_color = gradient_set[0]
        artist_color = gradient_set[1] if len(gradient_set) > 1 else (255, 255, 255)
        info_color = (255, 255, 255)  # Màu trắng cho info
        
        text_colors = [title_color, artist_color, info_color, info_color]
        text_fonts = [font_title, font_artist, font_info, font_info]
        
        # ==================== XỬ LÝ ẢNH COVER ====================
        thumb_size = 420

        if cover_url:
            try:
                response = requests.get(cover_url, timeout=10, verify=False)
                if response.status_code == 200:
                    thumb = Image.open(BytesIO(response.content)).convert("RGBA")
                    thumb = ImageOps.fit(thumb, (thumb_size, thumb_size), centering=(0.5, 0.5))
                    print(f"[DEBUG] Đã tải ảnh cover từ URL: {cover_url}")
                else:
                    print(f"[DEBUG] Không thể tải ảnh cover từ URL (status {response.status_code}), sử dụng ảnh từ backgrounds")
                    # SỬA: Trực tiếp dùng ảnh từ backgrounds thay vì raise Exception
                    thumb = None
            except Exception as e:
                print(f"[DEBUG] Lỗi khi tải ảnh cover từ URL: {e}")
                thumb = None
        else:
            print("[DEBUG] Không có cover_url, sử dụng ảnh từ backgrounds")
            thumb = None

        # Nếu thumb vẫn None (không có URL hoặc tải thất bại), dùng ảnh từ backgrounds
        if thumb is None:
            try:
                if os.path.exists(BACKGROUND_PATH):
                    background_images = [
                        f for f in os.listdir(BACKGROUND_PATH) 
                        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
                    ]
                    if background_images:
                        random_bg_path = os.path.join(BACKGROUND_PATH, random.choice(background_images))
                        print(f"[DEBUG] Sử dụng ảnh cover từ backgrounds: {random_bg_path}")
                        
                        # Mở ảnh và cắt thành hình vuông
                        thumb = Image.open(random_bg_path).convert("RGBA")
                        # Lấy phần giữa của ảnh
                        width, height = thumb.size
                        min_dim = min(width, height)
                        left = (width - min_dim) // 2
                        top = (height - min_dim) // 2
                        right = left + min_dim
                        bottom = top + min_dim
                        thumb = thumb.crop((left, top, right, bottom))
                        thumb = thumb.resize((thumb_size, thumb_size), Image.Resampling.LANCZOS)
                    else:
                        raise Exception("Không có ảnh trong thư mục backgrounds")
                else:
                    raise Exception("Thư mục backgrounds không tồn tại")
            except Exception as e:
                print(f"[DEBUG] Lỗi khi lấy ảnh từ backgrounds: {e}")
                # Fallback cuối cùng: tạo ảnh gradient đẹp
                thumb = Image.new("RGBA", (thumb_size, thumb_size), (0, 0, 0, 0))
                draw_thumb = ImageDraw.Draw(thumb)
                # Tạo gradient màu
                for i in range(thumb_size):
                    ratio = i / thumb_size
                    r = int(100 + 155 * ratio)
                    g = int(180 + 75 * (1 - ratio))
                    b = int(220 + 35 * ratio)
                    draw_thumb.line([(0, i), (thumb_size, i)], fill=(r, g, b, 255))
                print("[DEBUG] Tạo ảnh cover gradient mặc định")

        # BO TRÒN ẢNH COVER (luôn thực hiện dù ảnh từ nguồn nào)
        mask = Image.new("L", (thumb_size, thumb_size), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, thumb_size, thumb_size), fill=255)
        thumb.putalpha(mask)

        # THÊM VIỀN ĐA SẮC CHO COVER
        thumb_with_border = add_multicolor_circle_border(thumb, MULTICOLOR_GRADIENT, border_thickness=3)

        center_y = (box_y1 + box_y2) // 2
        thumb_x = box_x1 + 40
        thumb_y = center_y - (thumb_size // 2) - 3
        overlay.paste(thumb_with_border, (thumb_x, thumb_y), thumb_with_border)
        
        # ==================== LOGO SOUNDCLOUD (BO TRÒN) ====================
        scl_icon_size = 130
        logo_found = False
        logo_paths = [
            "Resource/music/soundcloud/sclden.jpg",
            "Resource/music/soundcloud/sclcam.png",
            "logo/scl.png",
            "backgrounds/scl.png"
        ]
        
        for logo_path in logo_paths:
            if os.path.exists(logo_path):
                try:
                    scl_img = Image.open(logo_path).convert("RGBA")
                    scl_img = ImageOps.fit(scl_img, (scl_icon_size, scl_icon_size), centering=(0.5, 0.5))
                    
                    # BO TRÒN LOGO SOUNDCLOUD
                    mask = Image.new("L", (scl_icon_size, scl_icon_size), 0)
                    draw_mask = ImageDraw.Draw(mask)
                    draw_mask.ellipse((0, 0, scl_icon_size, scl_icon_size), fill=255)
                    scl_img.putalpha(mask)
                    
                    # THÊM VIỀN ĐA SẮC CHO LOGO
                    scl_img_with_border = add_multicolor_circle_border(scl_img, MULTICOLOR_GRADIENT, border_thickness=2)
                    
                    # Vị trí logo
                    scl_x = thumb_x + thumb_size - scl_icon_size - 20
                    scl_y = thumb_y + thumb_size - scl_icon_size - 20
                    
                    overlay.paste(scl_img_with_border, (scl_x, scl_y), scl_img_with_border)
                    logo_found = True
                    print(f"[DEBUG] Đã thêm logo SoundCloud (bo tròn): {logo_path}")
                    break
                except Exception as e:
                    print(f"[DEBUG] Lỗi xử lý logo {logo_path}: {e}")
                    continue
        
        if not logo_found:
            print("[DEBUG] Không tìm thấy logo SoundCloud")
        
        # ==================== VẼ TEXT VỚI EMOJI ====================
        line_spacing = 140
        start_y = box_y1 + 30
        
        for i, line in enumerate(text_lines):
            if not line:
                continue
                
            # Tính chiều rộng text
            bbox = draw.textbbox((0, 0), line, font=text_fonts[i])
            text_width = bbox[2] - bbox[0]
            
            # Căn giữa
            text_x = box_x1 + (box_x2 - box_x1 - text_width) // 2
            text_y = start_y + i * line_spacing
            
            # Vẽ text với emoji support
            draw_mixed_text(draw, (text_x, text_y), line, text_fonts[i], font_emoji, text_colors[i])
        
        # ==================== GHÉP ẢNH VÀ LƯU ====================
        final_image = Image.alpha_composite(bg_image, overlay).resize(final_size, Image.Resampling.LANCZOS)
        
        # THÊM VIỀN ĐA SẮC CHO TOÀN BỘ ẢNH
        final_image_with_border = add_multicolor_rectangle_border(final_image, MULTICOLOR_GRADIENT, border_thickness=4)
        
        os.makedirs(CACHE_PATH, exist_ok=True)
        file_path = os.path.join(CACHE_PATH, "selected_song_scl.jpg")
        final_image_with_border.convert("RGB").save(file_path, "JPEG", quality=95)
        
        print(f"[DEBUG] Đã tạo ảnh bìa: {file_path}")
        return file_path
        
    except Exception as e:
        print(f"[ERROR] Lỗi trong create_song_cover_image: {e}")
        import traceback
        traceback.print_exc()
        return None
# ---------------------------
# Hàm xử lý API SoundCloud
# ---------------------------
def get_client_id():
    global CLIENT_ID_CACHE
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            last_update = datetime.fromisoformat(config.get('soundcloud', {}).get('lastUpdate', '1970-01-01'))
            if (datetime.now() - last_update).days < 3 and config.get('soundcloud', {}).get('clientId'):
                CLIENT_ID_CACHE = config['soundcloud']['clientId']
                return CLIENT_ID_CACHE

        response = requests.get("https://soundcloud.com/", headers=get_headers(), verify=False)
        response.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        script_tags = soup.find_all('script', {'crossorigin': True})
        urls = [tag['src'] for tag in script_tags if tag.get('src') and tag['src'].startswith('https')]
        
        if not urls:
            raise ValueError("Không tìm thấy URL script")
        
        script_response = requests.get(urls[-1], headers=get_headers(), verify=False)
        script_response.raise_for_status()
        client_id = script_response.text.split(',client_id:"')[1].split('"')[0]
        
        config = {'soundcloud': {'clientId': client_id, 'lastUpdate': datetime.now().isoformat()}}
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        
        CLIENT_ID_CACHE = client_id
        return client_id
    except Exception as e:
        print(f"[ERROR] Không thể lấy client ID: {e}")
        return CLIENT_ID_CACHE or "W00nmY7TLer3uyoEo1sWK3Hhke5Ahdl9"

def search_song_list(query, limit=20):
    try:
        client_id = get_client_id()
        search_url = "https://api-v2.soundcloud.com/search/tracks"
        params = {
            'q': query,
            'client_id': client_id,
            'limit': limit,
            'offset': 0,
            'linked_partitioning': 1,
            'app_locale': 'en'
        }
        response = requests.get(search_url, params=params, headers=get_headers(), verify=False)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for track in data.get('collection', [])[:limit]:
            duration = f"{track.get('duration', 0) // 60000}:{(track.get('duration', 0) % 60000) // 1000:02d}" if track.get('duration') else "N/A"
            results.append((
                track.get('permalink_url', ''),
                track.get('title', 'Không rõ'),
                track.get('artwork_url', '').replace('-large', '-t500x500') if track.get('artwork_url') else '',
                track.get('user', {}).get('username', 'Không rõ'),
                duration,
                False,  # is_official (SoundCloud không cung cấp)
                False,  # is_hd (SoundCloud không cung cấp)
                str(track.get('id', '')),  # song_id
                track.get('track_authorization', '')  # Thêm track_authorization
            ))
        print("[API RESULT] Kết quả tìm kiếm bài hát từ SoundCloud:")
        for idx, song in enumerate(results):
            print(f"  {idx + 1}. Title: {song[1]}, Artist: {song[3]}, URL: {song[0]}, Thumbnail: {song[2]}, Duration: {song[4]}, Official: {song[5]}, HD: {song[6]}, Song ID: {song[7]}")
        return results
    except Exception as e:
        print(f"[ERROR] Lỗi khi tìm kiếm bài hát: {e}")
        return []

def get_music_stream_url(link, track_authorization):
    try:
        client_id = get_client_id()
        api_url = f"https://api-v2.soundcloud.com/resolve?url={link}&client_id={client_id}"
        response = requests.get(api_url, headers=get_headers(), verify=False)
        response.raise_for_status()
        data = response.json()
        
        progressive_url = next((t['url'] for t in data.get('media', {}).get('transcodings', []) if t['format']['protocol'] == 'progressive'), None)
        if not progressive_url:
            raise ValueError("Không tìm thấy URL âm thanh")
        
        stream_response = requests.get(f"{progressive_url}?client_id={client_id}&track_authorization={track_authorization}", headers=get_headers(), verify=False)
        stream_response.raise_for_status()
        return stream_response.json()['url']
    except Exception as e:
        print(f"[ERROR] Lỗi khi lấy stream URL: {e}")
        return None

def download(link, track_authorization):
    try:
        stream_url = get_music_stream_url(link, track_authorization)
        if not stream_url:
            return None

        os.makedirs('cache', exist_ok=True)
        output_path = 'cache/downloaded_song.mp3'  # Rõ ràng là .mp3

        headers = get_headers()
        headers['Accept'] = 'audio/mpeg,*/*'

        with requests.get(stream_url, headers=headers, stream=True, verify=False, timeout=60) as response:
            response.raise_for_status()

            # Lấy tên file từ header nếu có
            content_disposition = response.headers.get('Content-Disposition')
            if content_disposition:
                import re
                fname = re.findall('filename="?([^"]+)"?', content_disposition)
                if fname:
                    original_name = fname[0]
                    if not original_name.lower().endswith('.mp3'):
                        original_name += '.mp3'
                    output_path = os.path.join('cache', original_name)
                else:
                    output_path = 'cache/downloaded_song.mp3'
            else:
                output_path = 'cache/downloaded_song.mp3'

            # Kiểm tra Content-Type
            content_type = response.headers.get('Content-Type', '')
            if 'audio' not in content_type and 'octet-stream' not in content_type:
                print(f"[WARNING] Content-Type không phải audio: {content_type}")

            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        print(f"[DEBUG] Đã tải file âm thanh: {output_path} (MP3)")
        return output_path
    except Exception as e:
        print(f"[ERROR] Lỗi khi tải âm thanh: {e}")
        return None


def upload_to_zalo(client, file_path: str, thread_id: str, thread_type) -> str | None:
    """
    Upload file (m4a, gif, webp, ...) lên Zalo server bằng _uploadAttachment
    Trả về URL nếu thành công, None nếu thất bại
    """
    try:
        if not os.path.exists(file_path):
            print(f"[ERROR] File không tồn tại: {file_path}")
            return None

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            print(f"[ERROR] File rỗng: {file_path}")
            return None

        print(f"[UPLOAD ZALO] Bắt đầu upload {os.path.basename(file_path)} ({file_size/1024/1024:.1f} MB)")

        # Gọi hàm upload của zlapi
        upload_response = client._uploadAttachment(file_path, thread_id, thread_type)

        file_url = None
        if isinstance(upload_response, dict):
            file_url = upload_response.get("fileUrl") or upload_response.get("url")
        elif hasattr(upload_response, 'fileUrl'):
            file_url = upload_response.fileUrl
        elif hasattr(upload_response, 'url'):
            file_url = upload_response.url
        elif isinstance(upload_response, str):
            file_url = upload_response

        if file_url:
            print(f"[UPLOAD ZALO SUCCESS] URL: {file_url}")
            return file_url
        else:
            print("[UPLOAD ZALO ERROR] Không tìm thấy fileUrl/url trong response")
            if isinstance(upload_response, dict):
                print(f"Response keys: {list(upload_response.keys())}")
            print(f"Response raw: {upload_response}")
            return None

    except Exception as e:
        print(f"[UPLOAD ZALO EXCEPTION] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None
        
def upload_to_uguu(file_path):
    url = "https://uguu.se/upload"
    try:
        if not os.path.exists(file_path):
            print(f"[ERROR] File không tồn tại: {file_path}")
            return None

        upload_filename = os.path.basename(file_path)
        if file_path.endswith('.m4a'):
            mime_type = 'audio/mp4'
        else:
            upload_filename = upload_filename if upload_filename.lower().endswith('.mp3') else upload_filename + '.mp3'
            mime_type = 'audio/mpeg'

        with open(file_path, 'rb') as file:
            files = {'files[]': (upload_filename, file, mime_type)}
            response = requests.post(url, files=files, headers=get_headers(), verify=False, timeout=30)
            response.raise_for_status()
            result = response.json()
            upload_url = result.get('files', [{}])[0].get('url')

            if upload_url:
                print(f"[DEBUG] Đã tải lên Uguu: {upload_url}")
                return upload_url
            else:
                print(f"[ERROR] Không nhận được URL từ Uguu: {result}")
                return None
    except Exception as e:
        print(f"[ERROR] Lỗi khi tải lên Uguu: {e}")
        return None        
        
def convert_mp3_to_m4a(mp3_path, title="song"):
    if not mp3_path or not os.path.exists(mp3_path):
        return None
    safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)[:50]
    m4a_path = f"cache/{safe_title}.m4a"
    try:
        cmd = [
            'ffmpeg', '-i', mp3_path,
            '-c:a', 'aac', '-b:a', '128k',
            '-vn', '-y', m4a_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0 and os.path.exists(m4a_path):
            print(f"[CONVERT] MP3 → M4A: {m4a_path}")
            return m4a_path
        else:
            print(f"[FFMPEG ERROR] {result.stderr}")
            return None
    except Exception as e:
        print(f"[ERROR] Chuyển đổi thất bại: {e}")
        return None        
        
def delete_file(file_path):
    try:
        os.remove(file_path)
        print(f"[DEBUG] Đã xóa tệp: {file_path}")
    except Exception as e:
        print(f"[ERROR] Lỗi khi xóa tệp: {e}")

# Các hàm hỗ trợ font và ảnh avatar (giữ nguyên từ mã gốc)
_FONT_CACHE = {}
def get_font(font_path, size):
    key = (font_path, size)
    if key not in _FONT_CACHE:
        try:
            _FONT_CACHE[key] = ImageFont.truetype(font_path, size)
        except Exception:
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

def create_rotating_gif_from_cover(cover_url, client, thread_id, thread_type, output_path="cache/rotating_disc.gif", num_frames=200, rotation_speed=1):
    try:
        # Thử tải ảnh bìa từ URL
        response = requests.get(cover_url, timeout=10, verify=False)
        if response.status_code == 200:
            image = Image.open(io.BytesIO(response.content)).convert('RGBA')
            print(f"[DEBUG] Đã tải ảnh bìa từ: {cover_url}")
        else:
            raise Exception("Không thể tải ảnh bìa từ URL")
    except Exception as e:
        print(f"[DEBUG] Không thể tải ảnh bìa từ URL: {e}")
        # Nếu không tải được ảnh bìa, chọn ảnh ngẫu nhiên từ thư mục backgrounds
        try:
            if not os.path.exists(BACKGROUND_FOLDER):
                raise FileNotFoundError("Thư mục backgrounds không tồn tại")
            image_files = [f for f in os.listdir(BACKGROUND_FOLDER) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            if not image_files:
                raise FileNotFoundError("Không tìm thấy ảnh hợp lệ trong thư mục backgrounds")
            default_image_path = os.path.join(BACKGROUND_FOLDER, random.choice(image_files))
            image = Image.open(default_image_path).convert('RGBA')
            print(f"[DEBUG] Đã sử dụng ảnh mặc định từ: {default_image_path}")
        except Exception as e:
            print(f"[ERROR] Không thể tải ảnh từ thư mục backgrounds: {e}")
            # Nếu không có ảnh trong thư mục, tạo ảnh mặc định
            image = Image.new("RGBA", (200, 200), (150, 150, 150))
            print("[DEBUG] Đã tạo ảnh mặc định màu xám")

    # Resize ảnh thành hình vuông
    min_side = min(image.size)
    square_size = (min_side, min_side)
    image = image.resize(square_size, Image.Resampling.LANCZOS)

    # Tạo mặt nạ hình elip để bo tròn
    mask = Image.new("L", square_size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, min_side, min_side), fill=255)
    image.putalpha(mask)

    frames = []
    for i in range(num_frames):
        angle = -(i * 360) / (num_frames / rotation_speed)
        rotated_image = image.rotate(angle, resample=Image.BICUBIC)
        frames.append(rotated_image)
    print(f"[DEBUG] Đã tạo {num_frames} khung hình với góc bo tròn")

    # Lưu GIF tạm thời
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=40,
        loop=0,
        disposal=2
    )
    print(f"[DEBUG] Đã tạo GIF tại: {output_path}")

    # Upload lên Zalo
    gif_zalo_url = upload_to_zalo(client, output_path, thread_id, thread_type)

    # Xóa file ngay sau upload
    delete_file(output_path)

    if not gif_zalo_url:
        print("[ERROR] Không upload được GIF lên Zalo")
        return None

    print(f"[DEBUG] Đã upload GIF lên Zalo: {gif_zalo_url}")
    return gif_zalo_url

# Handler cho lệnh "scl"
def handle_scl_command(message, message_object, thread_id, thread_type, author_id, client):
    content = message.strip().split()
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
    if len(content) < 2:
        error_message = Message(text="🚫 Lỗi: Thiếu tên bài hát\n\nCú pháp: ms.scl <tên bài hát>")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return
    query = ' '.join(content[1:])
    song_list = search_song_list(query)
    if not song_list:
        error_message = Message(text="❌ Không tìm thấy bài hát nào phù hợp.")
        client.replyMessage(error_message, message_object, thread_id, thread_type)
        return

    song_search_results[thread_id] = song_list
    list_image_path, list_image_width, list_image_height = create_song_list_image(song_list, max_show=20)
    guide_msg = "Nhập số (1, 2, 3,..., 20) để chọn bài hát"
    search_status[thread_id] = (time.time(), False, list_image_path, thread_type, author_id)


    try:
        response = client.sendLocalImage(
            list_image_path,
            message=Message(text=guide_msg),
            thread_id=thread_id,
            thread_type=thread_type,
            width=list_image_width,
            height=list_image_height,
            ttl=60000
        )
        msg_id = response.get('msgId')
        search_status[thread_id] = (time.time(), False, msg_id, thread_type, author_id)

        print("[DEBUG] Đã lưu msgId của tin nhắn danh sách bài hát.")
    except Exception as e_img:
        print("[ERROR] Lỗi khi gửi ảnh danh sách:", e_img)

    time.sleep(TIME_TO_SELECT / 1000)
    if thread_id in search_status and not search_status[thread_id][1]:
        try:
            client.deleteGroupMsg(search_status[thread_id][2], author_id, message_object['cliMsgId'], thread_id)
            print("[DEBUG] Đã xóa ảnh danh sách bài hát sau 60 giây hết hạn.")
        except Exception as e:
            print("[ERROR] Lỗi khi xóa ảnh danh sách:", e)
        del search_status[thread_id]

# Handler cho lệnh "chon"
def handle_chon_command(message, message_object, thread_id, thread_type, author_id, client):
    content = message.strip().split()
    if thread_id not in search_status or search_status[thread_id][1]:
        error_message = Message(text="🚫 Bạn không thể chọn vì danh sách đã hết hạn hoặc không phải người tìm kiếm.")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return
    stime, selected, msg_id, _, original_author_id = search_status[thread_id]  # Lấy original_author_id từ tuple
    # KIỂM TRA QUYỀN:
    if author_id != original_author_id:
        error_message = Message(text="🚫 Chỉ người tìm kiếm mới được chọn bài hát.")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return        

    if content[1] == '0':
        try:
            client.deleteGroupMsg(search_status[thread_id][2], author_id, message_object['cliMsgId'], thread_id)
            print("[DEBUG] Đã xóa ảnh danh sách bài hát sau khi người dùng hủy.")
        except Exception as e:
            print("[ERROR] Lỗi khi xóa ảnh danh sách:", e)
        del search_status[thread_id]
        success_message = Message(text="🔄 Lệnh tìm kiếm đã được hủy. Bạn có thể thực hiện tìm kiếm mới.")
        client.replyMessage(success_message, message_object, thread_id, thread_type, ttl=60000)
        return

    try:
        index = int(content[1]) - 1
    except ValueError:
        error_message = Message(text="🚫 Lỗi: Số bài hát không hợp lệ.\nCú pháp: //scl <số từ 1-20>")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return

    song_list = song_search_results.get(thread_id)
    if index < 0 or index >= min(20, len(song_list)):
        error_message = Message(text="🚫 Số bài hát không hợp lệ. Vui lòng chọn từ 1 đến 20.")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return

    selected_song = song_list[index]
    url, title, cover, artist, duration, is_official, is_hd, song_id, track_auth = selected_song
    search_status[thread_id] = (search_status[thread_id][0], True, search_status[thread_id][2], thread_type, original_author_id)


    try:
        client.deleteGroupMsg(search_status[thread_id][2], author_id, message_object['cliMsgId'], thread_id)
        print("[DEBUG] Đã xóa ảnh danh sách bài hát sau khi người dùng chọn.")
    except Exception as e:
        print("[ERROR] Lỗi khi xóa ảnh danh sách:", e)

    del search_status[thread_id]

    # Kiểm tra bộ nhớ đệm
    cache_key = f"{PLATFORM}_{song_id}"
    cached_music = MEDIA_CACHE.get(cache_key)
    if cached_music:
        print(f"[DEBUG] Sử dụng URL âm thanh từ bộ nhớ đệm: {cached_music}")
        upload_response = cached_music
    else:
        download_message = Message(
            text=f"🔽 Đang tải bài hát: {title}\nThời lượng: {duration}\nNguồn: Soundcloud"
        )
        client.replyMessage(download_message, message_object, thread_id, thread_type, ttl=40000)
        
        mp3_file = download(url, track_auth)
        if not mp3_file:
            error_message = Message(text="🚫 Lỗi: Không thể tải file âm thanh.")
            client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
            return
        
        try:
            size = os.path.getsize(mp3_file)
            print(f"[DEBUG] File tải về: {mp3_file} (kích thước: {size} bytes)")
        except Exception as e:
            print("[ERROR] Không thể lấy kích thước file:", e)

        m4a_file = convert_mp3_to_m4a(mp3_file, title)
        delete_file(mp3_file)  # Xóa MP3

        if not m4a_file:
            error_message = Message(text="Lỗi: Không thể chuyển đổi sang M4A.")
            client.replyMessage(error_message, message_object, thread_id, thread_type)
            return

        # === UPLOAD M4A lên Uguu ===
        audio_url = upload_to_uguu(m4a_file)  # SỬA DÒNG NÀY
        delete_file(m4a_file)  # Xóa M4A

        if not audio_url:
            error_message = Message(text="Lỗi: Không thể upload file âm thanh lên server.")
            client.replyMessage(error_message, message_object, thread_id, thread_type)
            return

        MEDIA_CACHE[cache_key] = audio_url  # Cập nhật cache với URL mới
        print(f"[SUCCESS] URL âm thanh Uguu: {audio_url}")
        delete_file(mp3_file)  # Giữ nguyên nếu cần xóa mp3

    info_text = (
        f"🎵 Bài Hát   : {title}\n"
        f"🎤 Nghệ sĩ   : {artist}\n"
        f"⏳ Thời lượng: {duration}\n"
        f"🔖 Tags     : {' | '.join([t for t in ['Official' if is_official else '', 'HD' if is_hd else ''] if t])}"
    )
    messagesend = Message(text=info_text)
    webp_url = create_rotating_gif_from_cover(
        cover if cover else "https://a-v2.sndcdn.com/assets/images/sc-icons/android-7e6641b3.png",
        client=client,
        thread_id=thread_id,
        thread_type=thread_type
    )

    if webp_url:
        try:
            client.sendCustomSticker(
                staticImgUrl=webp_url,
                animationImgUrl=webp_url,
                thread_id=thread_id,
                thread_type=thread_type,
                width=250,
                height=250,
                ttl=120000000
            )
            print("[DEBUG] Đã gửi sticker WebP thành công!")
        except Exception as e:
            print(f"[ERROR] Lỗi khi gửi sticker: {e}")
            try:
                client.sendRemoteImage(
                    imageUrl=webp_url,
                    thread_id=thread_id,
                    thread_type=thread_type,
                    width=250,
                    height=250,
                    ttl=120000000
                )
                print("[DEBUG] Đã gửi WebP dưới dạng ảnh!")
            except Exception as e2:
                print(f"[ERROR] Lỗi khi gửi ảnh: {e2}")
        delete_file("cache/rotating_disc.gif")
        delete_file("cache/rotating_disc.webp")
    else:
        print("[ERROR] Không tạo được WebP sticker")

    image_path = create_song_cover_image(title, artist, duration, is_official, is_hd, cover_url=cover if cover else None)

    try:
        client.sendLocalImage(
            image_path, thread_id, thread_type,
            width=1200, height=400, ttl=120000000
        )
        print("[DEBUG] Đã gửi ảnh thành công")
    except Exception as e:
        print(f"[ERROR] Lỗi khi gửi ảnh: {e}")
    delete_file(image_path)

 

    # === GỬI DƯỚI DẠNG VOICE (dùng URL Zalo) ===
    try:
        client.sendRemoteVoice(
            voiceUrl=audio_url,          # <-- thay upload_response bằng zalo_audio_url
            thread_id=thread_id,
            thread_type=thread_type,
            ttl=120000000
        )
        print("[SUCCESS] ĐÃ GỬI VOICE (M4A) THÀNH CÔNG QUA ZALO SERVER!")
    except Exception as e:
        print(f"[ERROR] Gửi voice thất bại: {e}")
        # Fallback: gửi như file đính kèm
        try:
            client.sendRemoteFile(
                fileUrl=audio_url,
                fileName=f"{title}.m4a",
                thread_id=thread_id,
                thread_type=thread_type,
                ttl=120000000
            )
            print("[FALLBACK] Gửi dưới dạng file đính kèm")
        except Exception as e2:
            print(f"[ERROR] Cả voice và file đều lỗi: {e2}")
            client.replyMessage(
                Message(text=f"Nghe tại đây: {audio_url}"),
                message_object,
                thread_id,
                thread_type
            )

# Mapping lệnh tới hàm xử lý
def get_mitaizl():
    return {
        'ms.scl': handle_scl_command,
        '//scl': handle_chon_command
    }