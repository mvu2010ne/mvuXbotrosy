from zlapi import ZaloAPI
from zlapi.models import *
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import requests
from io import BytesIO
import os
import random
from datetime import datetime
import pytz
import re
import time
import base64
import colorsys
import urllib.parse

# === CẤU HÌNH ===
hcm_tz = pytz.timezone('Asia/Ho_Chi_Minh')
utc_tz = pytz.utc
today = datetime.now(hcm_tz)
TODAY_STR = today.strftime("%d/%m")

# === API KEYS ===
GEMINI_API_KEY = "AIzaSyC8dBlEjrrtHoz6_93I4OTxfzGeSVnDYLI"  # Thay bằng key thật
POLLINATIONS_API = "https://image.pollinations.ai/prompt/"

# === FONT CACHE ===
FONT_NAME = None
FONT_WISH = None
FONT_INFO = None
FONT_EMOJI = None

# === DẢI MÀU ĐA SẮC TỪ da.py ===
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
    [(173, 216, 230), (255, 255, 255), (255, 250, 250)],
    [(255, 218, 185), (255, 250, 205), (255, 255, 224)],
    [(135, 206, 250), (176, 196, 222), (70, 130, 180)],
    [(255, 182, 193), (255, 105, 180), (255, 20, 147), (255, 0, 255)],
    [(0, 255, 127), (0, 255, 255), (30, 144, 255), (135, 206, 235)]
]

def get_random_gradient():
    return random.choice(GRADIENT_SETS)

def load_fonts_once():
    global FONT_NAME, FONT_WISH, FONT_INFO, FONT_EMOJI
    if FONT_NAME is not None:
        return
    font_name_path = "font/1.ttf"
    font_text_path = "font/5.otf"
    font_emoji_path = "font/NotoEmoji-Bold.ttf"

    def safe_load(path, size, name):
        if not os.path.exists(path):
            print(f"[FONT] KHÔNG TÌM THẤY: {name}")
            return None
        try:
            return ImageFont.truetype(path, size)
        except Exception as e:
            print(f"[FONT] LỖI TẢI {name}: {e}")
            return None

    FONT_NAME = safe_load(font_name_path, 140, "Tên")
    FONT_WISH = safe_load(font_text_path, 90, "Chúc")
    FONT_INFO = safe_load(font_text_path, 70, "Info")
    FONT_EMOJI = safe_load(font_emoji_path, 90, "Emoji")

    default = ImageFont.load_default()
    FONT_NAME = FONT_NAME or default
    FONT_WISH = FONT_WISH or default
    FONT_INFO = FONT_INFO or default
    FONT_EMOJI = FONT_EMOJI or default
    print("[FONT] TẢI FONT HOÀN TẤT!")

load_fonts_once()

# === HÀM HỖ TRỢ ===
def format_date(ts):
    try:
        return datetime.fromtimestamp(ts, tz=utc_tz).astimezone(hcm_tz).strftime("%d/%m")
    except:
        return "??/??"

def format_join_duration(ts):
    try:
        current_time = datetime.now(hcm_tz)
        join_time = datetime.fromtimestamp(ts, tz=pytz.UTC).astimezone(hcm_tz)
        delta = current_time - join_time
        years = delta.days // 365
        months = delta.days % 365 // 30
        days = delta.days % 30
        if years > 0:
            return f"{years} năm {months} tháng"
        elif months > 0:
            return f"{months} tháng {days} ngày"
        else:
            return f"{days} ngày"
    except:
        return "Không rõ"

def calculate_age(dob_ts):
    try:
        birth_hcm = datetime.fromtimestamp(dob_ts, tz=utc_tz).astimezone(hcm_tz)
        today_hcm = datetime.now(hcm_tz)
        age = today_hcm.year - birth_hcm.year
        if (today_hcm.month, today_hcm.day) < (birth_hcm.month, birth_hcm.day):
            age -= 1
        return age
    except:
        return None

def fetch_image(url):
    if not url or "default" in url:
        return None
    try:
        if url.startswith('data:'):
            _, data = url.split(',', 1)
            return Image.open(BytesIO(base64.b64decode(data))).convert("RGB")
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return Image.open(BytesIO(r.content)).convert("RGB")
    except:
        return None

# === POLLINATIONS: TẠO ẢNH NỀN SINH NHẬT ===
def generate_birthday_background(name, age):
    prompt = f"beautiful birthday card background, {name}, {age} years old, festive, cake, balloons, golden lights, luxury, elegant, cinematic, 4k"
    encoded = urllib.parse.quote(prompt)
    url = f"{POLLINATIONS_API}{encoded}?width=3000&height=1050&nologo=True"
    try:
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            img = Image.open(BytesIO(r.content)).convert("RGB")
            img = img.filter(ImageFilter.GaussianBlur(0))
            return img
    except Exception as e:
        print(f"[LỖI POLLINATIONS] {e}")
    return None

# === GEMINI: TẠO LỜI CHÚC CÁ NHÂN HÓA ===
def generate_birthday_wish_gemini(name, age, join_duration):
    prompt = f"""
    Viết lời chúc sinh nhật bằng tiếng Việt, cảm xúc, ấm áp, vui vẻ, dành cho {name}.
    - Tuổi: {age} (nếu không rõ thì bỏ qua)
    - Đã tham gia nhóm: {join_duration}
    - Giọng điệu: thân thiện, gần gũi, có thể hài hước nhẹ
    - Dưới 2 câu, ngắn gọn, dễ đọc
    - Không dùng emoji
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}]
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            data = r.json()
            text = data['candidates'][0]['content']['parts'][0]['text'].strip()
            return re.sub(r'^["\']|["\']$', '', text)
    except Exception as e:
        print(f"[LỖI GEMINI] {e}")
    return f"Chúc {name} sinh nhật thật vui vẻ và hạnh phúc!"

# === VẼ CHỮ – MƯỢT NHƯ da.py ===
def get_text_width(text, font, emoji_font):
    if not text: return 0
    dummy = ImageDraw.Draw(Image.new("RGB", (1,1)))
    segments = split_text_by_emoji(text)
    width = 0
    for seg, is_emoji in segments:
        f = emoji_font if is_emoji else font
        for ch in seg:
            bbox = dummy.textbbox((0,0), ch, font=f)
            width += bbox[2] - bbox[0]
    return width

emoji_pattern = re.compile(r"([\U0001F300-\U0001F5FF]|[\U0001F600-\U0001F64F]|[\U0001F680-\U0001F6FF]|[\U0001F900-\U0001F9FF]|[\U0001FA00-\U0001FA6F]|\uFE0F)", re.UNICODE)

def split_text_by_emoji(text):
    segments = []
    buffer = ""
    for ch in text:
        if emoji_pattern.match(ch):
            if buffer: segments.append((buffer, False))
            segments.append((ch, True))
            buffer = ""
        else:
            buffer += ch
    if buffer: segments.append((buffer, False))
    return segments

def draw_mixed_gradient_text(draw, text, position, normal_font, emoji_font, gradient_colors, shadow_offset=(4,4)):
    if not text:
        return
    total_chars = len(text)
    change_every = 4  # Mượt như da.py
    color_list = []
    num_segments = len(gradient_colors) - 1
    steps_per_segment = max(1, (total_chars // change_every) // num_segments + 1)

    for i in range(num_segments):
        for j in range(steps_per_segment):
            if len(color_list) >= total_chars:
                break
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
    shadow_color = (0, 0, 0, 150)
    segments = split_text_by_emoji(text)
    char_index = 0
    for seg, is_emoji in segments:
        current_font = emoji_font if is_emoji else normal_font
        for ch in seg:
            if char_index >= len(color_list):
                break
            color = color_list[char_index]
            draw.text((x + shadow_offset[0], y + shadow_offset[1]), ch, font=current_font, fill=shadow_color)
            draw.text((x, y), ch, font=current_font, fill=color)
            bbox = draw.textbbox((0, 0), ch, font=current_font)
            char_width = bbox[2] - bbox[0]
            x += char_width
            char_index += 1

# === TẠO THIỆP SINH NHẬT ===
def create_birthday_card(member):
    name = (member.get('name', '') or "Ẩn danh").strip()
    user_id = member['id']
    age = member.get('age')
    join_duration = format_join_duration(member['created_ts'])

    # === 1. TẠO ẢNH NỀN SINH NHẬT BẰNG AI (Pollinations) ===
    bg = generate_birthday_background(name, age or "?")
    if not bg:
        bg = Image.new("RGB", (3000, 1050), (100, 150, 255))
        bg = bg.filter(ImageFilter.GaussianBlur(20))
    else:
        bg = bg.resize((3000, 1050), Image.Resampling.LANCZOS)

    draw = ImageDraw.Draw(bg)
    fonts = {
        'name': FONT_NAME,
        'wish': FONT_WISH,
        'info': FONT_INFO,
        'emoji': FONT_EMOJI
    }

    # === 2. TẠO LỜI CHÚC CÁ NHÂN HÓA BẰNG GEMINI ===
    wish = generate_birthday_wish_gemini(name, age, join_duration)

    # === 3. AVATAR + VIỀN CẦU VỒNG ===
    avatar = fetch_image(member['avatar'])
    if not avatar:
        avatar = Image.new("RGB", (500, 500), (200, 200, 200))
    avatar = avatar.resize((500, 500), Image.Resampling.LANCZOS)
    mask = Image.new("L", (500, 500), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 500, 500), fill=255)
    bg.paste(avatar, (100, 170), mask)

    # Viền cầu vồng
    border = Image.new("RGBA", (540, 540), (0,0,0,0))
    d = ImageDraw.Draw(border)
    for i in range(360):
        h = i / 360
        r, g, b = colorsys.hsv_to_rgb(h, 0.8, 1.0)
        d.arc([(8,8), (532, 532)], i, i+3, fill=(int(r*255), int(g*255), int(b*255), 255), width=10)
    bg.paste(border, (90, 160), border)

    # === 4. VÙNG CHỮ – DẢI MÀU ĐA SẮC TỪ da.py ===
    text_x = 720
    region_width = 3000 - text_x - 150
    y = 80  # Tên cao hơn

    # --- TÊN NGƯỜI ---
    name_gradient = get_random_gradient()
    name_to_draw = name[:22] + "..." if len(name) > 22 else name
    name_w = get_text_width(name_to_draw, fonts['name'], fonts['emoji'])
    x_c = text_x + (region_width - name_w) // 2
    draw_mixed_gradient_text(draw, name_to_draw, (x_c, y), fonts['name'], fonts['emoji'], name_gradient)
    y += 220

    # --- ĐƯỜNG KẺ NGANG ---
    line_y = y - 20
    draw.line([(text_x + 50, line_y), (3000 - 150, line_y)], fill=(255, 255, 255, 150), width=2)
    y = line_y + 80

    # --- LỜI CHÚC (TỰ ĐỘNG XUỐNG DÒNG) ---
    wish_gradient = get_random_gradient()
    words = wish.split()
    lines = []
    cur = ""
    for w in words:
        test = cur + w + " "
        if get_text_width(test, fonts['wish'], fonts['emoji']) <= region_width:
            cur = test
        else:
            lines.append(cur.strip())
            cur = w + " "
    if cur:
        lines.append(cur.strip())

    for line in lines:
        w = get_text_width(line, fonts['wish'], fonts['emoji'])
        x_c = text_x + (region_width - w) // 2
        draw_mixed_gradient_text(draw, line, (x_c, y), fonts['wish'], fonts['emoji'], wish_gradient)
        y += 125

    # --- THÔNG TIN PHỤ ---
    info_gradient = get_random_gradient()
    info = f"Năm nay {age or '?'} tuổi • Đã tham gia: {join_duration}"
    info_w = get_text_width(info, fonts['info'], fonts['emoji'])
    x_i = text_x + (region_width - info_w) // 2
    draw_mixed_gradient_text(draw, info, (x_i, y + 40), fonts['info'], fonts['emoji'], info_gradient)

    # === 5. LƯU ẢNH – RESIZE CHUẨN 1500x460 ===
    final = bg.resize((1500, 600), Image.Resampling.LANCZOS).convert("RGB")
    path = f"bd_{user_id}.jpg"
    try:
        final.save(path, quality=95, optimize=True)
        print(f"[ẢNH] ĐÃ LƯU: {os.path.abspath(path)}")
    except Exception as e:
        print(f"[LỖI] Lưu ảnh: {e}")
        return None, wish, name

    return path, wish, name
    
def print_birthday_list(client, thread_id, thread_type):
    try:
        group_info = client.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
        members = group_info.get('memVerList', [])
    except Exception as e:
        client.sendMessage(Message(f"Lỗi lấy danh sách: {e}"), thread_id, thread_type)
        return

    birthday_list = []

    for mid in members:
        try:
            info = client.fetchUserInfo(mid)
            profiles = info.unchanged_profiles or info.changed_profiles
            profile = profiles.get(str(mid))
            if not profile: 
                continue
            dob = profile.dob or profile.sdob
            if not dob: 
                continue

            name = (profile.zaloName or "Ẩn danh").strip()
            birth_str = format_date(dob)
            age = calculate_age(dob)
            join = format_join_duration(profile.createdTs or 0)

            birthday_list.append({
                'name': name,
                'birth': birth_str,
                'age': age,
                'join': join
            })

        except Exception as e:
            logging.error(f"Lỗi xử lý user {mid}: {e}")
            continue

    if not birthday_list:
        client.sendMessage(Message("Không có thông tin sinh nhật nào trong nhóm!"), thread_id, thread_type, ttl=60000)
        return

    # Sắp xếp theo ngày sinh (MM/DD)
    birthday_list.sort(key=lambda x: x['birth'])

    # === TẠO TIN NHẮN ===
    msg = "DANH SÁCH SINH NHẬT NHÓM\n"
    msg += f"Tổng: {len(birthday_list)} thành viên\n\n"

    count = 1
    for m in birthday_list:
        age_str = f" ({m['age']} tuổi)" if m['age'] is not None else ""
        today_mark = " HÔM NAY" if m['birth'] == TODAY_STR else ""
        msg += f"{count}. {m['name']}{age_str}\n"
        msg += f" Sinh nhật: {m['birth']}{today_mark}\n"
        msg += f" Tham gia: {m['join']}\n\n"
        count += 1

    # === CHIA NHỎ TIN NHẮN NẾU DÀI ===
    chunks = [msg[i:i+1500] for i in range(0, len(msg), 1500)]
    for i, chunk in enumerate(chunks):
        suffix = f"\n\nTrang {i+1}/{len(chunks)}" if len(chunks) > 1 else ""
        client.sendMessage(Message(chunk + suffix), thread_id, thread_type, ttl=60000)
        if i < len(chunks) - 1:
            time.sleep(1)  # Tránh spam
# === XỬ LÝ LỆNH ===
def get_user_profile(client, user_id):
    try:
        uid = str(user_id)
        if len(uid) < 10 or uid.endswith('_0'):
            uid = uid.rsplit('_', 1)[0]
        info = client.fetchUserInfo(uid)
        profiles = info.unchanged_profiles or info.changed_profiles
        return profiles.get(uid)
    except:
        return None

def handle_cmsn(message, message_object, thread_id, thread_type, author_id, client):
    cmd = message.strip().lower()
    if cmd not in ["cmsn", "cmsn list"]:
        return
    if cmd == "cmsn list":
        client.sendReaction(message_object, "Đang quét...", thread_id, thread_type, reactionType=75)
        print_birthday_list(client, thread_id, thread_type)
        return

    try:
        group_info = client.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
        members = group_info.get('memVerList', [])
    except:
        return

    today_members = []
    for mid in members:
        profile = get_user_profile(client, mid)
        if not profile: continue
        dob = profile.dob or profile.sdob
        if not dob: continue
        if format_date(dob) == TODAY_STR:
            name = (profile.zaloName or "").strip() or "Ẩn danh"
            age = calculate_age(dob)
            today_members.append({
                'id': str(mid),           # memVerList format: "uid_name"
                'name': name,
                'avatar': profile.avatar or '',
                'dob': dob,
                'created_ts': profile.createdTs or 0,
                'age': age
            })

    if not today_members:
        client.sendMessage(Message("Hôm nay chưa có ai sinh nhật!"), thread_id, thread_type)
        return

    for member in today_members:
        img_path, wish, display_name = create_birthday_card(member)
        if not img_path or not os.path.exists(img_path):
            # Nếu không có ảnh → vẫn mention + chúc mừng
            mention_text = f"@{display_name}"
            uid = member['id'].split('_')[0]  # Lấy UID chính xác từ memVerList
            mention = Mention(uid=uid, offset=0, length=len(mention_text))
            msg = Message(text=mention_text, mention=mention)
            client.sendMessage(msg, thread_id, thread_type)
            continue

        # === GỬI ẢNH + MENTION CHUẨN NHƯ tag_all_msg.py ===
        mention_text = f"@{display_name}"
        uid = member['id'].split('_')[0]  # UID chính xác
        mention = Mention(uid=uid, offset=0, length=len(mention_text))

        msg = Message(text=mention_text, mention=mention)

        try:
            client.sendLocalImage(
                imagePath=img_path,
                thread_id=thread_id,
                thread_type=thread_type,
                message=msg,
                ttl=3600000,
                width=1500,
                height=600
            )
            time.sleep(2)
            os.remove(img_path)
        except Exception as e:
            print(f"[LỖI GỬI] {e}")
            try: os.remove(img_path)
            except: pass
            # Fallback: vẫn mention
            fallback_msg = Message(text=mention_text, mention=mention)
            client.sendMessage(fallback_msg, thread_id, thread_type)

def get_mitaizl():
    return {'cmsn': handle_cmsn}