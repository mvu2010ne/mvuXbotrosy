import os
import re
import time
import random
import requests
import urllib.parse
import io
import math
from zlapi import *
from zlapi.models import *
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed
import yt_dlp

# ---------------------------
# Biến toàn cục
# ---------------------------
song_search_results = {}  # Lưu danh sách bài hát theo thread_id
search_status = {}        # Lưu trạng thái tìm kiếm của mỗi thread_id: (time_search_sent, has_selected, image_path_or_msgId, thread_type)
PLATFORM = "nhaccuatui"
TIME_TO_SELECT = 60000

# ---------------------------
# Các hàm hỗ trợ chung (giữ nguyên từ mã gốc)
# ---------------------------
def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Referer": "https://www.nhaccuatui.com/",
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

def draw_gradient_text(draw, text, position, font, gradient_colors, shadow_offset=(0,0)):
    x, y = position
    if shadow_offset != (0, 0):
        shadow_color = (0, 0, 0)
        draw.text((x + shadow_offset[0], y + shadow_offset[1]), text, font=font, fill=shadow_color)
    gradient = interpolate_colors(gradient_colors, text_length=len(text), change_every=4)
    for i, char in enumerate(text):
        draw.text((x, y), char, font=font, fill=gradient[i])
        char_bbox = draw.textbbox((x, y), char, font=font)
        char_width = char_bbox[2] - char_bbox[0]
        x += char_width

def add_multicolor_rectangle_border(image, colors, border_thickness=3):
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

# Các hàm xử lý ảnh nâng cao (giữ nguyên từ mã gốc)
def add_circular_multicolor_border(image, colors, border_thickness):
    scale = 4
    scaled_thickness = border_thickness * scale
    size = image.size
    new_size = (size[0] + 2 * border_thickness, size[1] + 2 * border_thickness)
    scaled_new_size = (new_size[0] * scale, new_size[1] * scale)
    border_img_scaled = Image.new("RGBA", scaled_new_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(border_img_scaled)
    for offset in range(scaled_thickness):
        bbox = (offset, offset, scaled_new_size[0] - offset - 1, scaled_new_size[1] - offset - 1)
        for angle in range(360):
            color = get_gradient_color(colors, angle / 360)
            draw.arc(bbox, angle, angle + 1, fill=color, width=1)
    image_scaled = image.resize((size[0] * scale, size[1] * scale), resample=Image.LANCZOS)
    border_img_scaled.paste(image_scaled, (scaled_thickness, scaled_thickness), image_scaled)
    border_img = border_img_scaled.resize(new_size, resample=Image.LANCZOS)
    return border_img

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

def draw_rounded_rectangle(draw, xy, radius, fill, outline=None, width=1):
    x1, y1, x2, y2 = xy
    draw.pieslice([x1, y1, x1 + 2*radius, y1 + 2*radius], 180, 270, fill=fill, outline=outline)
    draw.pieslice([x2 - 2*radius, y1, x2, y1 + 2*radius], 270, 360, fill=fill, outline=outline)
    draw.pieslice([x1, y2 - 2*radius, x1 + 2*radius, y2], 90, 180, fill=fill, outline=outline)
    draw.pieslice([x2 - 2*radius, y2 - 2*radius, x2, y2], 0, 90, fill=fill, outline=outline)
    draw.rectangle([x1+radius, y1, x2-radius, y1+radius], fill=fill, outline=outline)
    draw.rectangle([x1, y1+radius, x2, y2-radius], fill=fill, outline=outline)
    draw.rectangle([x1+radius, y2-radius, x2-radius, y2], fill=fill, outline=outline)

def add_solid_border(thumb, border_thickness=3, border_color=(255, 255, 255, 255)):
    try:
        original_size = thumb.size[0]
        new_size = original_size + 2 * border_thickness
        border_img = Image.new("RGBA", (new_size, new_size), (0, 0, 0, 0))
        draw_border = ImageDraw.Draw(border_img, "RGBA")
        draw_border.ellipse((0, 0, new_size-1, new_size-1), fill=border_color)
        border_img.paste(thumb, (border_thickness, border_thickness), mask=thumb)
        return border_img
    except Exception as e:
        print("[ERROR] Lỗi trong add_solid_border:", e)
        return thumb

# Các hàm xử lý text hỗ trợ emoji và gradient (giữ nguyên từ mã gốc)
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

def draw_mixed_gradient_text(draw_obj, text, position, normal_font, emoji_font, gradient_colors, shadow_offset=(2,2)):
    if not text:  # Kiểm tra nếu text rỗng thì thoát
        return
    total_chars = len(text)
    color_list = []
    num_segments = len(gradient_colors) - 1
    steps_per_segment = (total_chars // 4) + 1
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
    segments = split_text_by_emoji(text)  # Sửa lỗi gọi hàm
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
    segments = split_text_by_emoji(text)  # Sửa lỗi gọi hàm
    for seg, is_emoji in segments:
        f = emoji_font if is_emoji else normal_font
        bbox = base_draw.textbbox((0, 0), seg, font=f)
        total_width += (bbox[2] - bbox[0])
    region_w = region_x1 - region_x0
    x = region_x0 + (region_w - total_width) // 2
    draw_mixed_gradient_text(base_draw, text, (x, y), normal_font, emoji_font, gradient_colors, shadow_offset=(2,2))

# ---------------------------
# Hàm xử lý download, upload và file
# ---------------------------
def search_song_list(query):
    """
    Tìm kiếm bài hát trên NhacCuaTui và trả về danh sách tối đa 10 bài:
    (url, title, cover_url, artist, duration, is_official, is_hd, song_id)
    """
    try:
        encoded_query = urllib.parse.quote(query)
        search_url = f"https://www.nhaccuatui.com/tim-kiem/bai-hat?q={encoded_query}&b=keyword&l=tat-ca&s=default"
        response = requests.get(search_url, headers=get_headers(), timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        for element in soup.select(".sn_search_returns_list_song .sn_search_single_song"):
            song_link = element.select_one("a")
            if song_link and song_link.has_attr("href"):
                url = song_link['href']
                title = song_link.get('title', 'Không rõ').strip()
                key = song_link.get('key', '')
                artist = element.select_one(".name_singer").text.strip() if element.select_one(".name_singer") else "Không rõ"
                thumbnail = element.select_one(".thumb").get('data-src') or element.select_one(".thumb").get('src') or ""
                if thumbnail and "avatar_default" in thumbnail:
                    thumbnail = ""  # Thay thế ảnh bìa mặc định bằng rỗng
                elif thumbnail:
                    thumbnail = thumbnail.replace(".jpg", "_600.jpg")
                is_official = bool(element.select_one(".icon_tag_official"))
                is_hd = bool(element.select_one(".icon_tag_hd"))
                
                # Lấy duration từ API XML
                duration = "N/A"
                try:
                    stream_url, duration_sec = get_stream_url_with_duration(key, url)
                    if duration_sec:
                        minutes = duration_sec // 60
                        seconds = duration_sec % 60
                        duration = f"{minutes}:{seconds:02d}"
                except Exception as e:
                    print(f"[DEBUG] Không thể lấy duration cho bài hát {title}: {e}")
                
                results.append((url, title, thumbnail, artist, duration, is_official, is_hd, key))
                if len(results) == 10:
                    break
        print("[API RESULT] Kết quả tìm kiếm bài hát từ NhacCuaTui:")
        for idx, song in enumerate(results):
            print(f"  {idx + 1}. Title: {song[1]}, Artist: {song[3]}, URL: {song[0]}, Thumbnail: {song[2]}, Duration: {song[4]}, Official: {song[5]}, HD: {song[6]}, Song ID: {song[7]}")
        return results
    except Exception as e:
        print(f"[ERROR] Lỗi khi tìm kiếm bài hát: {e}")
        return []

def get_stream_url_with_duration(song_id, song_link, retry_count=3):
    """
    Lấy URL stream và duration của bài hát từ NhacCuaTui
    """
    try:
        response = requests.get(song_link, headers=get_headers(), timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        key = None
        for script in soup.select("script"):
            content = script.string or ""
            key_match = re.search(r'key1=([a-f0-9]{32})', content, re.I)
            if key_match:
                key = key_match.group(1)
                break
        if not key:
            print("[API RESULT] Không tìm thấy key trong HTML cho bài hát:", song_link)
            return None, None
        xml_url = f"https://www.nhaccuatui.com/flash/xml?html5=true&key1={key}"
        for attempt in range(3):
            try:
                xml_response = requests.get(xml_url, headers=get_headers(), timeout=15)
                xml_response.raise_for_status()
                xml_soup = BeautifulSoup(xml_response.text, 'xml')
                stream_url = xml_soup.find("location").text or xml_soup.find("locationHQ").text
                stream_url = stream_url.replace("<![CDATA[", "").replace("]]>", "").strip()
                duration_tag = xml_soup.find("duration")
                duration_sec = int(duration_tag.text) if duration_tag and duration_tag.text.isdigit() else None
                try:
                    urllib.parse.urlparse(stream_url)
                    print("[API RESULT] Stream URL từ NhacCuaTui:", stream_url)
                    if duration_sec:
                        print("[API RESULT] Duration từ NhacCuaTui:", duration_sec, "giây")
                    return stream_url, duration_sec
                except:
                    print("[API RESULT] Stream URL không hợp lệ:", stream_url)
                    return None, None
            except Exception as e:
                if attempt < 2:
                    print(f"[INFO] Thử lại XML request lần {attempt + 1}...")
                    time.sleep(2 * (attempt + 1))
                else:
                    raise e
    except Exception as e:
        print(f"[ERROR] Lỗi khi lấy stream URL và duration: {e}")
        if retry_count > 0:
            print(f"[INFO] Thử lại toàn bộ quá trình lần {4 - retry_count}...")
            time.sleep(2)
            return get_stream_url_with_duration(song_id, song_link, retry_count - 1)
    return None, None
    
def get_stream_url(song_id, song_link, retry_count=3):
    """
    Lấy URL stream của bài hát từ NhacCuaTui
    """
    stream_url, _ = get_stream_url_with_duration(song_id, song_link, retry_count)
    return stream_url
    
def download(link):
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'cache/downloaded_file.%(ext)s',
            'noplaylist': True,
            'quiet': True
        }
        os.makedirs('cache', exist_ok=True)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(link, download=True)
            return ydl.prepare_filename(info_dict)
    except Exception as e:
        print(f"Lỗi khi tải âm thanh: {e}")
        return None

def upload_to_uguu(file_path):
    url = "https://uguu.se/upload"
    try:
        with open(file_path, 'rb') as file:
            files = {'files[]': (os.path.basename(file_path), file)}
            response = requests.post(url, files=files, headers=get_headers())
            response.raise_for_status()
            return response.json().get('files', [{}])[0].get('url')
    except Exception as e:
        print(f"Lỗi khi tải lên: {e}")
        return None

def delete_file(file_path):
    try:
        os.remove(file_path)
        print(f"Đã xóa tệp: {file_path}")
    except Exception as e:
        print(f"Lỗi khi xóa tệp: {e}")

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

# Các hằng số cấu hình (giữ nguyên từ mã gốc)
MULTICOLOR_GRADIENT = [
    (255, 0, 0), (255, 165, 0), (255, 255, 0),
    (0, 255, 0), (0, 0, 255), (75, 0, 130), (148, 0, 211)
]
OVERLAY_COLORS = [
    (255,255,255,200),
    (255,250,250,200),
    (240,255,255,200),
    (255,228,196,200),
    (255,218,185,200),
    (255,239,213,200),
    (255,222,173,200),
    (255,250,205,200),
    (250,250,210,200),
    (255,245,238,200)
]
MULTICOLOR_GRADIENTS = [
    [(255,0,255), (0,255,255), (255,255,0), (0,255,0)],
    [(255,0,0), (255,165,0), (255,255,0), (0,128,0), (0,0,255), (75,0,130), (148,0,211)]
]

def create_background_from_folder(width, height):
    BACKGROUND_FOLDER = 'gai'
    if os.path.isdir(BACKGROUND_FOLDER):
        imgs = [os.path.join(BACKGROUND_FOLDER, f) for f in os.listdir(BACKGROUND_FOLDER)
                if f.lower().endswith(('.jpg','.jpeg','.png'))]
        if imgs:
            bg_path = random.choice(imgs)
            bg = Image.open(bg_path).convert("RGB")
            return bg.resize((width, height), Image.LANCZOS)
    return Image.new("RGB", (width, height), (130,190,255))

# Hàm tạo ảnh danh sách bài hát (style i4, chỉnh sửa để phù hợp NhacCuaTui)
def process_cover_image(song, cover_size=80):
    """Xử lý ảnh bìa cho một bài hát: tải, resize, bo tròn, thêm viền."""
    cover_url = song[2]
    cover_img = None
    try:
        if cover_url:
            resp = requests.get(cover_url, timeout=10)
            resp.raise_for_status()
            cover_img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
            cover_img = cover_img.resize((cover_size, cover_size), Image.LANCZOS)
            mask = Image.new("L", (cover_size, cover_size), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, cover_size, cover_size), fill=255)
            cover_img.putalpha(mask)
            cover_img = add_multicolor_circle_border(cover_img, MULTICOLOR_GRADIENT, border_thickness=3)
    except Exception as e:
        print(f"[ERROR] Lỗi xử lý cover cho {song[1]}: {e}")
    
    # Nếu không có ảnh bìa, tạo placeholder
    if not cover_img:
        cover_img = Image.new("RGBA", (cover_size, cover_size), (150, 150, 150, 255))
        mask = Image.new("L", (cover_size, cover_size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, cover_size, cover_size), fill=255)
        cover_img.putalpha(mask)
        cover_img = add_multicolor_circle_border(cover_img, MULTICOLOR_GRADIENT, border_thickness=3)
    
    return cover_img

def create_song_list_image(songs, max_show=10):
    songs_to_show = songs[:min(max_show, len(songs))]
    WIDTH = 800
    TOP_HEIGHT = 150
    V_SPACING = 15
    ITEM_HEIGHT = 100
    total_height = TOP_HEIGHT + V_SPACING + len(songs_to_show) * (ITEM_HEIGHT + V_SPACING) + 20

    # Tạo nền
    bg = create_background_from_folder(WIDTH, total_height)
    background_img = bg.convert("RGBA")
    base_draw = ImageDraw.Draw(background_img)

    # Vẽ tiêu đề
    top_overlay = Image.new("RGBA", (WIDTH, TOP_HEIGHT), (0, 0, 0, 0))
    top_draw = ImageDraw.Draw(top_overlay)
    overlay_color = random.choice(OVERLAY_COLORS)
    top_draw.rounded_rectangle((0, 0, WIDTH, TOP_HEIGHT), radius=20, fill=overlay_color)

    title = "🔍 Kết quả tìm kiếm"
    font_title = get_font("font/Tapestry-Regular.ttf", 50)
    emoji_font_title = get_font("font/NotoEmoji-Bold.ttf", 50)
    gradient_title = random.choice(MULTICOLOR_GRADIENTS)
    draw_centered_text_mixed_line(title, (TOP_HEIGHT - font_title.size) // 2, font_title, emoji_font_title,
                                  gradient_title, top_draw, 0, WIDTH)
    background_img.alpha_composite(top_overlay, (0, 0))

    # Song song hóa xử lý ảnh bìa
    cover_images = []
    with ThreadPoolExecutor(max_workers=min(len(songs_to_show), 10)) as executor:
        future_to_song = {executor.submit(process_cover_image, song): song for song in songs_to_show}
        for future in as_completed(future_to_song):
            try:
                cover_img = future.result()
                cover_images.append(cover_img)
            except Exception as e:
                print(f"[ERROR] Lỗi khi xử lý ảnh bìa: {e}")
                # Thêm placeholder nếu lỗi
                cover_size = 80
                cover_img = Image.new("RGBA", (cover_size, cover_size), (150, 150, 150, 255))
                mask = Image.new("L", (cover_size, cover_size), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, cover_size, cover_size), fill=255)
                cover_img.putalpha(mask)
                cover_img = add_multicolor_circle_border(cover_img, MULTICOLOR_GRADIENT, border_thickness=3)
                cover_images.append(cover_img)

    # Vẽ danh sách bài hát
    current_y = TOP_HEIGHT + V_SPACING
    for idx, (song, cover_img) in enumerate(zip(songs_to_show, cover_images)):
        item_overlay = Image.new("RGBA", (WIDTH - 40, ITEM_HEIGHT), (0, 0, 0, 0))
        item_draw = ImageDraw.Draw(item_overlay)
        item_color = random.choice(OVERLAY_COLORS)
        item_draw.rounded_rectangle((0, 0, WIDTH - 40, ITEM_HEIGHT), radius=10, fill=item_color)

        # Vẽ số thứ tự
        circle_radius = 18
        circle_center_x = 20 + circle_radius
        circle_center_y = ITEM_HEIGHT // 2
        item_draw.ellipse([(circle_center_x - circle_radius, circle_center_y - circle_radius),
                           (circle_center_x + circle_radius, circle_center_y + circle_radius)],
                          fill=(255, 87, 34))
        font_number = get_font("font/ChivoMono-VariableFont_wght.ttf", 18)
        num_text = str(idx + 1)
        bbox_num = item_draw.textbbox((0, 0), num_text, font=font_number)
        num_w = bbox_num[2] - bbox_num[0]
        num_h = bbox_num[3] - bbox_num[1]
        item_draw.text((circle_center_x - num_w // 2, circle_center_y - num_h // 2),
                       num_text, font=font_number, fill=(255, 255, 255))

        # Dán ảnh bìa
        cover_offset_x = circle_center_x + circle_radius + 10
        item_overlay.paste(cover_img, (cover_offset_x, (ITEM_HEIGHT - cover_img.size[1]) // 2), cover_img)

        # Thông tin bài hát
        text_start_x = cover_offset_x + cover_img.size[0] + 10
        text_area_width = (WIDTH - 40) - text_start_x - 10
        title_text = song[1] or "Không rõ"
        artist_text = song[3] or "Không rõ"
        tags = []
        if song[5]:
            tags.append("Official")
        if song[6]:
            tags.append("HD")
        tags_text = " | ".join(tags) if tags else ""

        # Vẽ tiêu đề bài hát
        font_title = get_font("font/ChivoMono-VariableFont_wght.ttf", 22)
        emoji_font = get_font("font/NotoEmoji-Bold.ttf", 22)
        title_lines = wrap_text(title_text, font_title, text_area_width, item_draw)
        current_text_y = 15
        for line in title_lines[:1]:
            draw_mixed_gradient_text(item_draw, line, (text_start_x, current_text_y),
                                     font_title, emoji_font, random.choice(MULTICOLOR_GRADIENTS),
                                     shadow_offset=(1, 1))
            bbox = item_draw.textbbox((text_start_x, current_text_y), line, font=font_title)
            current_text_y += (bbox[3] - bbox[1]) + 5

        # Vẽ nghệ sĩ và tags
        font_info = get_font("font/ChivoMono-VariableFont_wght.ttf", 18)
        info_text = f"@{artist_text} {tags_text}".strip()
        info_lines = wrap_text(info_text, font_info, text_area_width, item_draw)
        for line in info_lines[:1]:
            draw_mixed_gradient_text(item_draw, line, (text_start_x, current_text_y),
                                     font_info, emoji_font, random.choice(MULTICOLOR_GRADIENTS),
                                     shadow_offset=(1, 1))
            bbox = item_draw.textbbox((text_start_x, current_text_y), line, font=font_info)
            current_text_y += (bbox[3] - bbox[1]) + 5

        background_img.alpha_composite(item_overlay, (20, current_y))
        current_y += ITEM_HEIGHT + V_SPACING

    # Thêm viền gradient
    final_image = add_multicolor_rectangle_border(background_img, MULTICOLOR_GRADIENT, border_thickness=8)
    final_image = final_image.convert("RGB")
    output_path = "song_list_nct.jpg"
    final_image.save(output_path, quality=95)
    return output_path

def convert_gif_to_webp(gif_path, output_path="cache/rotating_disc.webp"):
    try:
        gif = Image.open(gif_path)
        frames = []
        durations = []
        try:
            while True:
                frame = gif.copy().convert("RGBA")
                frames.append(frame)
                durations.append(gif.info.get('duration', 80))
                gif.seek(gif.tell() + 1)
        except EOFError:
            pass
        frames[0].save(
            output_path,
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0,
            quality=90,
            method=6
        )
        print(f"[DEBUG] Đã chuyển GIF sang WebP: {output_path}")
        return output_path
    except Exception as e:
        print(f"[ERROR] Lỗi khi chuyển GIF sang WebP: {e}")
        return None

def upload_to_uguu(file_path):
    url = "https://uguu.se/upload"
    try:
        with open(file_path, 'rb') as file:
            files = {'files[]': (os.path.basename(file_path), file, 'image/webp')}
            response = requests.post(url, files=files, headers=get_headers())
            response.raise_for_status()
            result = response.json()
            if response.status_code == 200 and 'files' in result and result['files']:
                uploaded_url = result['files'][0].get('url')
                if uploaded_url and uploaded_url.startswith('https://'):
                    print(f"[DEBUG] Đã upload lên Uguu: {uploaded_url}")
                    return uploaded_url
                else:
                    print(f"[ERROR] Phản hồi từ Uguu không hợp lệ: {result}")
                    return None
    except Exception as e:
        print(f"[ERROR] Lỗi khi upload lên Uguu: {e}")
        return None

def create_rotating_gif_from_cover(cover_url, output_path="cache/rotating_disc.gif", num_frames=200, rotation_speed=1):
    try:
        response = requests.get(cover_url, timeout=10)
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content)).convert('RGBA')
        print(f"[DEBUG] Đã tải ảnh bìa từ: {cover_url}")

        # Tạo mặt nạ hình elip để bo tròn
        mask = Image.new("L", image.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, image.size[0], image.size[1]), fill=255)
        image.putalpha(mask)

        frames = []
        for i in range(num_frames):
            angle = -(i * 360) / (num_frames / rotation_speed)
            rotated_image = image.rotate(angle, resample=Image.BICUBIC)
            frames.append(rotated_image)
        print(f"[DEBUG] Đã tạo {num_frames} khung hình với góc bo tròn")

        frames[0].save(
            output_path,
            save_all=True,
            append_images=frames[1:],
            duration=40,
            loop=0,
            disposal=2
        )
        print(f"[DEBUG] Đã tạo GIF tại: {output_path}")

        gif_url = upload_to_uguu(output_path)
        if not gif_url:
            print("[ERROR] Không thể upload GIF lên Uguu")
            return None
        print(f"[DEBUG] Đã upload GIF: {gif_url}")

        delete_file(output_path)
        return gif_url
    except Exception as e:
        print(f"[ERROR] Tạo GIF thất bại: {e}")
        return None
# Handler cho lệnh "nct" - Tìm kiếm bài hát và tạo ảnh danh sách
def handle_nct_command(message, message_object, thread_id, thread_type, author_id, client):
    content = message.strip().split()
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
    if len(content) < 2:
        error_message = Message(text="🚫 Lỗi: Thiếu tên bài hát\n\nCú pháp: ms.nct <tên bài hát>")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return
    query = ' '.join(content[1:])
    song_list = search_song_list(query)
    if not song_list:
        error_message = Message(text="❌ Không tìm thấy bài hát nào phù hợp.")
        client.replyMessage(error_message, message_object, thread_id, thread_type)
        return

    song_search_results[thread_id] = song_list
    list_image_path = create_song_list_image(song_list, max_show=10)
    guide_msg = ("Nhập số (1, 2, 3,...) để chọn bài hát")
    search_status[thread_id] = (time.time(), False, list_image_path, thread_type)

    try:
        list_image_height = 100 * len(song_list) + 20
        response = client.sendLocalImage(
            list_image_path,
            message=Message(text=guide_msg),
            thread_id=thread_id,
            thread_type=thread_type,
            width=700,
            height=list_image_height,
            ttl=60000
        )
        msg_id = response.get('msgId')
        search_status[thread_id] = (*search_status[thread_id][:2], msg_id, thread_type)
        print("[DEBUG] Đã lưu msgId của tin nhắn danh sách bài hát.")
    except Exception as e_img:
        print("[ERROR] Lỗi khi gửi ảnh danh sách:", e_img)

    time.sleep(TIME_TO_SELECT / 1000)
    if thread_id in search_status and not search_status[thread_id][1]:
        try:
            client.deleteGroupMsg(message_object['msgId'], author_id, message_object['cliMsgId'], thread_id)
            print("[DEBUG] Đã xóa ảnh danh sách bài hát sau 60 giây hết hạn.")
        except Exception as e:
            print("[ERROR] Lỗi khi xóa ảnh danh sách:", e)
        del search_status[thread_id]

# Handler cho lệnh "chon" - Chọn bài hát để tải về, xử lý cover, upload và gửi kết quả
def handle_chon_command(message, message_object, thread_id, thread_type, author_id, client):
    content = message.strip().split()
    if thread_id not in search_status or search_status[thread_id][1]:
        error_message = Message(text="🚫 Bạn không thể chọn vì danh sách đã hết hạn hoặc không phải người tìm kiếm.")
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
        error_message = Message(text="🚫 Lỗi: Số bài hát không hợp lệ.\nCú pháp: s <số từ 1-10>")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return

    song_list = song_search_results.get(thread_id)
    if index < 0 or index >= len(song_list):
        error_message = Message(text="🚫 Số bài hát không hợp lệ. Vui lòng chọn lại.")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return

    selected_song = song_list[index]
    url, title, cover, artist, duration, is_official, is_hd, song_id = selected_song
    search_status[thread_id] = (search_status[thread_id][0], True, search_status[thread_id][2], thread_type)

    try:
        client.deleteGroupMsg(search_status[thread_id][2], author_id, message_object['cliMsgId'], thread_id)
        print("[DEBUG] Đã xóa ảnh danh sách bài hát sau khi người dùng chọn.")
    except Exception as e:
        print("[ERROR] Lỗi khi xóa ảnh danh sách:", e)

    # Xóa trạng thái search_status ngay sau khi chọn bài hát
    del search_status[thread_id]

    # Tạo thông báo tải xuống với tên bài hát và thời lượng
    title = selected_song[1]
    duration = selected_song[4] if selected_song[4] != "N/A" else "Không xác định"
    download_message = Message(
        text=f"🔽 Đang tải bài hát: {title}\nThời lượng: {duration}\nNguồn: NhacCuaTui"
    )
    client.replyMessage(download_message, message_object, thread_id, thread_type, ttl=60000)
    
    stream_url = get_stream_url(song_id, url)
    if not stream_url:
        error_message = Message(text="🚫 Lỗi: Không thể lấy URL stream của bài hát.")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return

    mp3_file = download(stream_url)
    if not mp3_file:
        error_message = Message(text="🚫 Lỗi: Không thể tải file âm thanh.")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return
    try:
        size = os.path.getsize(mp3_file)
        print(f"[DEBUG] File tải về: {mp3_file} (kích thước: {size} bytes)")
    except Exception as e:
        print("[ERROR] Không thể lấy kích thước file:", e)

    upload_response = upload_to_uguu(mp3_file)
    if not upload_response:
        error_message = Message(text="🚫 Lỗi: Không thể tải lên Uguu.se.")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        delete_file(mp3_file)
        return
    print(f"[DEBUG] URL file âm thanh sau khi upload: {upload_response}")

    info_text = (
        f"🎵 Bài Hát   : {title}\n"
        f"🎤 Nghệ sĩ   : {artist}\n"
        f"⏳ Thời lượng: {duration}\n"
        f"🔖 Tags     : {' | '.join([t for t in ['Official' if is_official else '', 'HD' if is_hd else ''] if t])}"
    )
    messagesend = Message(text=info_text)
    webp_url = create_rotating_gif_from_cover(cover if cover else "https://stc-id.nixcdn.com/v11/images/avatar_default_600.jpg")

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

    if cover:
        try:
            cover_response = requests.get(cover, headers=get_headers(), timeout=10)
            cover_response.raise_for_status()
            cover_filename = cover.rsplit("/", 1)[-1]
            with open(cover_filename, "wb") as file:
                file.write(cover_response.content)
            cover_image = Image.open(io.BytesIO(cover_response.content)).convert("RGB")
            print(f"[DEBUG] Đã tải ảnh bìa từ URL: {cover}")
        except Exception as e:
            print(f"[ERROR] Lỗi khi xử lý ảnh bìa từ URL: {e}")
            cover_image = None
    else:
        # Thử lấy ảnh bìa mặc định từ thư mục gai
        try:
            gai_path = "gai"
            if not os.path.exists(gai_path):
                raise FileNotFoundError("Thư mục gai không tồn tại")
            image_files = [f for f in os.listdir(gai_path) if f.lower().endswith(('.jpg', '.jpeg', '.png')) and f != 'nct.png']
            if not image_files:
                raise FileNotFoundError("Không tìm thấy ảnh hợp lệ trong gai")
            default_cover_path = os.path.join(gai_path, random.choice(image_files))
            cover_image = Image.open(default_cover_path).convert("RGB")
            cover_filename = "default_cover.jpg"
            print(f"[DEBUG] Đã lấy ảnh bìa mặc định từ: {default_cover_path}")
        except Exception as e:
            print(f"[ERROR] Lỗi khi lấy ảnh bìa từ gai: {e}")
            cover_image = Image.new("RGB", (200, 200), (150, 150, 150))  # Placeholder xám
            cover_filename = "default_cover.jpg"
            print("[DEBUG] Sử dụng ảnh placeholder xám")

    if cover_image:
        # Kích thước tổng thể
        combined_width = 600
        combined_height = 300
        cover_size = (200, 200)
        overlay_margin = 20
        overlay_width = combined_width - 2 * overlay_margin
        overlay_height = combined_height - 2 * overlay_margin
        text_area_width = overlay_width - cover_size[0] - 30

        # Tạo nền từ ảnh bìa
        cover_image = ImageEnhance.Brightness(cover_image).enhance(0.8)
        cover_image = cover_image.filter(ImageFilter.GaussianBlur(radius=10))
        bg_image = cover_image.resize((combined_width, combined_height), Image.LANCZOS)
        combined_image = Image.new("RGBA", (combined_width, combined_height), (0, 0, 0, 0))
        combined_image.paste(bg_image.convert("RGBA"), (0, 0))
        print("[DEBUG] Đã tạo nền từ ảnh bìa với blur")

        # Tạo overlay bán trong suốt màu trắng với 4 góc bo tròn
        overlay = Image.new("RGBA", (overlay_width, overlay_height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rounded_rectangle((0, 0, overlay_width, overlay_height), radius=20, fill=(255, 255, 255, 180))

        # Xử lý ảnh bìa trong overlay
        cover_image = Image.open(cover_filename).convert("RGB").resize(cover_size, Image.LANCZOS)
        mask = Image.new("L", cover_size, 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, cover_size[0], cover_size[1]), fill=255)
        cover_image = cover_image.convert("RGBA")
        cover_image.putalpha(mask)
        gradient_colors = MULTICOLOR_GRADIENT
        cover_border_thickness = 3
        cover_image = add_multicolor_circle_border(cover_image, gradient_colors, cover_border_thickness)
        final_cover_size = (cover_size[0] + 2 * cover_border_thickness, cover_size[1] + 2 * cover_border_thickness)
        overlay.paste(cover_image, (10, (overlay_height - final_cover_size[1]) // 2), cover_image)
        print("[DEBUG] Đã tạo ảnh bìa với viền gradient trong overlay")

        # Tải và xử lý logo nct.png
        logo_size = (50, 50)
        logo_image = None
        try:
            logo_path = os.path.join("logo", "logonct.png")
            if not os.path.exists(logo_path):
                raise FileNotFoundError("Tệp logonct.png không tồn tại")
            logo_image = Image.open(logo_path).convert("RGBA").resize(logo_size, Image.LANCZOS)
            logo_mask = Image.new("L", logo_size, 0)
            logo_mask_draw = ImageDraw.Draw(logo_mask)
            logo_mask_draw.ellipse((0, 0, logo_size[0], logo_size[1]), fill=255)
            logo_image.putalpha(logo_mask)
            logo_image = add_multicolor_circle_border(logo_image, gradient_colors, border_thickness=2)
            print(f"[DEBUG] Đã tải và bo tròn logo từ: {logo_path}")
        except Exception as e:
            print(f"[ERROR] Lỗi khi tải hoặc xử lý logo nct.png: {e}")

        # Dán logo vào góc phải dưới của ảnh bìa
        if logo_image:
            logo_position = (
                10 + final_cover_size[0] - logo_size[0] - 5,
                (overlay_height - final_cover_size[1]) // 2 + final_cover_size[1] - logo_size[1] - 5
            )
            overlay.paste(logo_image, logo_position, logo_image)
            print(f"[DEBUG] Đã dán logo tròn tại vị trí: {logo_position}")

        # Tải font
        try:
            font_title = get_font("font/ChivoMono-VariableFont_wght.ttf", 24)
            font_normal = get_font("font/ChivoMono-VariableFont_wght.ttf", 18)
            emoji_font = get_font("font/NotoEmoji-Bold.ttf", 18)
            print("[DEBUG] Đã tải font thành công")
        except Exception as e:
            print(f"[ERROR] Lỗi khi tải font: {e}")
            font_title = ImageFont.load_default()
            font_normal = ImageFont.load_default()
            emoji_font = ImageFont.load_default()

        # Vẽ văn bản trong overlay
        text_x = 10 + final_cover_size[0] + 10
        text_y = 20
        max_line_width = text_area_width - 20
        for idx, raw_line in enumerate(info_text.split("\n")):
            if raw_line.strip() == "":
                text_y += 10
                continue
            current_font = font_title if idx == 0 else font_normal
            wrapped_lines = wrap_text(raw_line, current_font, max_line_width, overlay_draw)
            for line in wrapped_lines:
                draw_mixed_gradient_text(
                    overlay_draw, line, (text_x, text_y), current_font, emoji_font,
                    random.choice(MULTICOLOR_GRADIENTS), shadow_offset=(1, 1)
                )
                bbox = overlay_draw.textbbox((text_x, text_y), line, font=current_font)
                text_y += (bbox[3] - bbox[1]) + 5
        print("[DEBUG] Đã vẽ văn bản trong overlay")

        # Dán overlay lên nền
        combined_image.alpha_composite(overlay, (overlay_margin, overlay_margin))

        # Thêm viền gradient cho toàn bộ ảnh
        combined_image = add_multicolor_rectangle_border(combined_image, gradient_colors, border_thickness=4)

        # Lưu và gửi ảnh
        combined_image = combined_image.convert("RGB")
        combined_filename = "combined_cover.jpg"
        combined_image.save(combined_filename, quality=90)
        try:
            client.sendLocalImage(
                combined_filename, thread_id, thread_type,
                width=combined_width, height=combined_height, ttl=120000000
            )
            print("[DEBUG] Đã gửi ảnh thành công")
        except Exception as e:
            print(f"[ERROR] Lỗi khi gửi ảnh: {e}")
        delete_file(combined_filename)
        delete_file(cover_filename)
    else:
        client.replyMessage(messagesend, message_object, thread_id, thread_type)
        print("[DEBUG] Gửi tin nhắn văn bản do không có ảnh bìa")

    try:
        client.sendRemoteVoice(voiceUrl=upload_response, thread_id=thread_id, thread_type=thread_type, ttl=120000000)
        print("[DEBUG] Gửi voice thành công!")
    except Exception as e:
        print("[ERROR] Lỗi khi gửi voice:", e)
    delete_file(mp3_file)
# Mapping lệnh tới hàm xử lý
def get_mitaizl():
    return {
        'ms.nct': handle_nct_command,
        '//nct': handle_chon_command
    }