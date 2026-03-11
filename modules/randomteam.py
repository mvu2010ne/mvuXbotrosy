import random
import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import requests
import logging
import re
import colorsys
import glob
import base64
from zlapi.models import Message, ThreadType

# ----------------- LOG & MÀU -----------------
logging.basicConfig(level=logging.ERROR, filename="bot_error.log", filemode="a",
                    format="%(asctime)s - %(levelname)s - %(message)s")

MULTICOLOR_GRADIENT = [(255,0,0),(255,165,0),(255,255,0),(0,255,0),(0,0,255),(75,0,130),(148,0,211)]
GRADIENT_SETS = [
    [(255,0,255),(0,255,255),(255,255,0),(0,255,0)], [(255,182,193),(173,216,230),(152,251,152),(240,230,140)],
    [(0,255,127),(0,255,255),(30,144,255)], [(255,223,186),(255,182,193),(255,160,122),(255,99,71)],
    [(176,196,222),(135,206,250),(70,130,180)], [(255,105,180),(0,191,255),(30,144,255)],
    [(0,255,255),(30,144,255),(135,206,235)], [(0,255,0),(50,205,50),(154,205,50)],
    [(255,165,0),(255,223,0),(255,140,0),(255,69,0)], [(173,216,230),(216,191,216),(255,182,193)],
    [(152,251,152),(255,255,224),(245,245,245)], [(255,192,203),(255,218,185),(255,250,205)],
    [(224,255,255),(175,238,238),(255,255,255)], [(255,204,204),(255,255,204),(204,255,204),(204,255,255),(204,204,255),(255,204,255)],
    [(255,239,184),(255,250,250),(255,192,203)], [(173,255,47),(255,255,102),(255,204,153)],
    [(189,252,201),(173,216,230)], [(255,182,193),(250,250,250),(216,191,216)], [(173,216,230),(255,255,255),(255,255,102)],
]

BACKGROUND_FOLDER = 'backgroundrandomteam'

# ----------------- HÀM HỖ TRỢ -----------------
_FONT_CACHE = {}
def get_font(path, size):
    key = (path, size)
    if key not in _FONT_CACHE:
        try: _FONT_CACHE[key] = ImageFont.truetype(path, size)
        except: _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]

def BackgroundGetting():
    files = glob.glob(f"{BACKGROUND_FOLDER}/*.*")
    if not files: return None
    return Image.open(random.choice(files)).convert("RGB")

def FetchImage(url):
    if not url: return None
    try:
        if url.startswith('data:image'):
            return Image.open(BytesIO(base64.b64decode(url.split(',',1)[1]))).convert("RGB")
        r = requests.get(url, timeout=10, stream=True); r.raise_for_status()
        return Image.open(BytesIO(r.content)).convert("RGB")
    except: return None

def make_round_avatar(avatar, size):
    avatar = ImageEnhance.Brightness(avatar).enhance(1.2)
    mask = Image.new("L", avatar.size, 0)
    ImageDraw.Draw(mask).ellipse((0,0)+avatar.size, fill=255)
    result = Image.new("RGBA", avatar.size, (0,0,0,0))
    result.paste(avatar, (0,0), mask)
    return result.resize((size, size), Image.Resampling.LANCZOS)

def add_rainbow_border(image, border_thickness=12, size=228):
    border_size = size + 2 * border_thickness
    border = Image.new("RGBA", (border_size, border_size), (0,0,0,0))
    draw = ImageDraw.Draw(border)
    for i in range(360):
        h = i / 360.0
        r,g,b = colorsys.hsv_to_rgb(h, 0.7, 1.0)
        draw.arc([4,4,border_size-5,border_size-5], i, i+3,
                 fill=(int(r*255),int(g*255),int(b*255),255), width=border_thickness)
    border.paste(image, (border_thickness, border_thickness), image)
    return border

# ----------------- GRADIENT TEXT -----------------
emoji_pattern = re.compile(r"[\U0001F300-\U0001F5FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\U0001F900-\U0001FAFF]+", re.UNICODE)
def draw_mixed_gradient_text(draw, text, position, normal_font, emoji_font, gradient_colors, shadow_offset=(3,3)):
    if not text: return
    x, y = position
    shadow_color = (0, 0, 0, 160)
    color_list = []
    total = len(text)
    seg = len(gradient_colors) - 1
    per_seg = max(1, total // (seg * 4))
    for i in range(seg):
        c1, c2 = gradient_colors[i], gradient_colors[i+1]
        for j in range(per_seg):
            if len(color_list) >= total: break
            ratio = j / per_seg
            color = (int(c1[0]*(1-ratio)+c2[0]*ratio), int(c1[1]*(1-ratio)+c2[1]*ratio), int(c1[2]*(1-ratio)+c2[2]*ratio))
            color_list.extend([color]*4)
    color_list = (color_list + [gradient_colors[-1]]*total)[:total]
    i = idx = 0
    while i < len(text):
        ch = text[i]
        font = emoji_font if emoji_pattern.match(ch) else normal_font
        draw.text((x+shadow_offset[0], y+shadow_offset[1]), ch, font=font, fill=shadow_color)
        draw.text((x, y), ch, font=font, fill=color_list[idx%total])
        bbox = draw.textbbox((0,0), ch, font=font)
        x += bbox[2] - bbox[0]
        idx += 1
        i += 1

# ================================
# LỆNH CHÍNH – TỰ ĐỘNG CHỌN 2 HOẶC 4 ĐỘI
# ================================
def handle_randomteam_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        mentions = message_object.mentions or []
        if len(mentions) < 8:
            client.replyMessage(Message(text="Tag ít nhất 8 người để chia đội nha!"), message_object, thread_id, thread_type)
            return

        user_ids = [m['uid'] for m in mentions]
        random.shuffle(user_ids)

        total_people = len(user_ids)

        # ========== CHỌN CHẾ ĐỘ ==========
        if total_people <= 12:                      # 8-12 người → 2 đội 5vs5 (1vs1)
            run_mode_2_teams(user_ids[:10], message_object, thread_id, thread_type, client)
        else:                                        # 13-20 người → 4 đội (2 cặp đấu)
            run_mode_4_teams(user_ids[:20], message_object, thread_id, thread_type, client)

    except Exception as e:
        client.sendMessage(Message(text="Lỗi chia đội rồi boss ơi!"), thread_id, thread_type)
        logging.error(f"RandomTeam Error: {e}", exc_info=True)

# ----------------- CHẾ ĐỘ 2 ĐỘI (1vs1) -----------------
def run_mode_2_teams(user_ids, message_object, thread_id, thread_type, client):
    client.sendReaction(message_object, "Đang chia đội...", thread_id, thread_type, reactionType=75)

    teams = [user_ids[i*5:(i+1)*5] for i in range(2)]
    random.shuffle(teams)
    info = client.fetchUserInfo(user_ids)
    profiles = {**info.unchanged_profiles, **(info.changed_profiles or {})}

    def get_members(uids):
        return [{'name': profiles.get(str(u), {}).get('zaloName', 'Ẩn danh'),
                 'avatar': profiles.get(str(u), {}).get('avatar')} for u in uids]
    team_data = [get_members(t) for t in teams]

    SIZE = (3000, 2400)
    FINAL_SIZE = (1500, 1200)
    bg = BackgroundGetting() or Image.new("RGB", SIZE, (20,30,80))
    bg = bg.convert("RGBA").resize(SIZE, Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(20))
    overlay = Image.new("RGBA", SIZE, (0,0,0,0))
    draw = ImageDraw.Draw(overlay)

    draw.rounded_rectangle([(100,100), (SIZE[0]-100, SIZE[1]-100)], radius=150, fill=(0,0,0,90))
    draw_mixed_gradient_text(draw, "GIẢI ĐẤU LIÊN QUÂN - 1VS1", (SIZE[0]//2 - 800, 120),
                             get_font("font/5.otf", 180), get_font("font/NotoEmoji-Bold.ttf", 120), MULTICOLOR_GRADIENT)

    logoA = add_rainbow_border(make_round_avatar(Image.new("RGBA",(380,380),(0,100,255,255)),380),12,380)
    logoB = add_rainbow_border(make_round_avatar(Image.new("RGBA",(380,380),(255,50,50,255)),380),12,380)
    overlay.paste(logoA, (560, 400), logoA)
    overlay.paste(logoB, (2060, 400), logoB)

    draw_mixed_gradient_text(draw, "VS", (1500-180, 550),
                             get_font("font/5.otf", 280), get_font("font/NotoEmoji-Bold.ttf", 120),
                             [(255,0,0),(255,165,0),(255,255,0),(0,255,0),(0,255,255)])

    cell_w, cell_h = 1200, 280
    font_name = get_font("font/5.otf", 90)
    for i in range(5):
        y = 950 + i * 320
        for idx, team in enumerate(teams):
            m = team_data[idx][i]
            cell = Image.new("RGBA", (cell_w, cell_h), (0,0,0,0))
            d = ImageDraw.Draw(cell)
            color = (0,80,180,120) if idx==0 else (180,40,40,120)
            d.rounded_rectangle([(0,0),(cell_w,cell_h)], radius=70, fill=color)
            ava = FetchImage(m['avatar']) or Image.new("RGB",(200,200),(100,150,255))
            ava = add_rainbow_border(make_round_avatar(ava.resize((200,200))),10,200)
            cell.paste(ava, (50,40), ava)
            draw_mixed_gradient_text(d, m['name'], (280,80), font_name,
                                     get_font("font/NotoEmoji-Bold.ttf",90), random.choice(GRADIENT_SETS))
            overlay.alpha_composite(cell, (300 if idx==0 else 1500, y))

    draw_mixed_gradient_text(draw, "design by Minh Vũ Shinn Cte", (SIZE[0]-900, SIZE[1]-150),
                             get_font("font/5.otf",90), get_font("font/NotoEmoji-Bold.ttf",80), random.choice(GRADIENT_SETS))

    final = Image.alpha_composite(bg, overlay).resize(FINAL_SIZE, Image.Resampling.LANCZOS).convert("RGB")
    path = "rt_2team.jpg"
    final.save(path, quality=95)
    client.sendLocalImage(path, thread_id, thread_type, width=1500, height=1200,
                          message=Message(text="ĐÃ CHIA XONG 2 ĐỘI (1VS1)\nMỗi đội 5 thành viên"))
    os.remove(path)

# ----------------- CHẾ ĐỘ 4 ĐỘI (2vs2) -----------------
def run_mode_4_teams(user_ids, message_object, thread_id, thread_type, client):
    is_test = len(user_ids) <= 12
    per_team = 2 if is_test else 5
    total_players = len(user_ids)

    teams = [user_ids[i*per_team:(i+1)*per_team] for i in range(4)]
    random.shuffle(teams)
    match1, match2 = (teams[0], teams[1]), (teams[2], teams[3])

    info = client.fetchUserInfo(user_ids)
    profiles = {**info.unchanged_profiles, **(info.changed_profiles or {})}

    def get_members(uids):
        return [{'name': profiles.get(str(u), {}).get('zaloName', 'Ẩn danh'),
                 'avatar': profiles.get(str(u), {}).get('avatar')} for u in uids]
    team_data = [get_members(t) for t in teams]

    client.sendReaction(message_object, "Đang vẽ ảnh siêu đẹp...", thread_id, thread_type, reactionType=75)

    SIZE = (7400, 3400)
    FINAL_SIZE = (3700, 1700)
    bg = BackgroundGetting() or Image.new("RGB", SIZE, (15,20,80))
    bg = bg.convert("RGBA").resize(SIZE, Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(16))
    overlay = Image.new("RGBA", SIZE, (0,0,0,0))
    draw = ImageDraw.Draw(overlay)

    draw.rounded_rectangle([(130,130),(SIZE[0]-130,SIZE[1]-130)], radius=220, fill=(0,0,0,150))
    draw.line([(SIZE[0]//2,500),(SIZE[0]//2,SIZE[1]-500)], fill=(255,255,255,240), width=20)
    draw_mixed_gradient_text(draw, "VÒNG LOẠI LIÊN QUÂN", (SIZE[0]//2-1350,140),
                             get_font("font/5.otf",260), get_font("font/NotoEmoji-Bold.ttf",200), MULTICOLOR_GRADIENT)

    # Logo thật
    try:
        logoA = add_rainbow_border(make_round_avatar(Image.open("team_blue.png").convert("RGBA").resize((520,520)),440),16,440)
        logoB = add_rainbow_border(make_round_avatar(Image.open("team_red.png").convert("RGBA").resize((520,520)),440),16,440)
    except:
        logoA = add_rainbow_border(make_round_avatar(Image.new("RGBA",(440,440),(0,110,255,255)),440),16,440)
        logoB = add_rainbow_border(make_round_avatar(Image.new("RGBA",(440,440),(255,60,60,255)),440),16,440)

    avatar_size = 228
    cell_w, cell_h = 1360, 310
    name_font = get_font("font/5.otf", 96)
    start_y = 600
    left_x = 180
    right_x = 3800
    logo_shift = 160

    for idx, (teamA, teamB) in enumerate([match1, match2]):
        base_x = left_x if idx == 0 else right_x
        overlay.paste(logoA, (base_x + 80 + logo_shift, start_y - 100), logoA)
        overlay.paste(logoB, (base_x + 2000 + logo_shift + 500, start_y - 100), logoB)
        draw_mixed_gradient_text(draw, "VS", (base_x + 1460 + logo_shift - 200, start_y + 60),
                                 get_font("font/5.otf",400), get_font("font/NotoEmoji-Bold.ttf",240),
                                 [(255,0,0),(255,100,0),(255,215,0),(50,205,50),(0,255,255),(0,191,255)])

        for i in range(per_team):
            y = start_y + 600 + i * (cell_h + 64)
            for team, offset in [(teamA, 0), (teamB, 2000)]:
                m = team_data[teams.index(team)][i]
                cell = Image.new("RGBA", (cell_w, cell_h), (0,0,0,0))
                d = ImageDraw.Draw(cell)
                fill = (0,100,220,150) if team in [teams[0], teams[2]] else (220,60,60,150)
                d.rounded_rectangle([(0,0),(cell_w,cell_h)], radius=84, fill=fill)
                ava = FetchImage(m['avatar']) or Image.new("RGB",(200,200),(80,150,255))
                ava = add_rainbow_border(make_round_avatar(ava.resize((avatar_size,avatar_size)), avatar_size),12,avatar_size)
                cell.paste(ava, (64,42), ava)
                draw_mixed_gradient_text(d, m['name'], (500,104), name_font,
                                         get_font("font/NotoEmoji-Bold.ttf",96), random.choice(GRADIENT_SETS))
                overlay.alpha_composite(cell, (base_x + offset, y))

    draw_mixed_gradient_text(draw, "design by Minh Vũ Shinn Cte", (SIZE[0]-1280,SIZE[1]-200),
                             get_font("font/5.otf",108), get_font("font/NotoEmoji-Bold.ttf",90), random.choice(GRADIENT_SETS))

    final = Image.alpha_composite(bg, overlay).resize(FINAL_SIZE, Image.Resampling.LANCZOS).convert("RGB")
    path = "rt_4team.jpg"
    final.save(path, quality=99)
    mode = "TEST 2VS2" if is_test else "CHÍNH THỨC 5VS5"
    client.sendLocalImage(path, thread_id, thread_type, width=3700, height=1700,
                          message=Message(text=f"ĐÃ CHIA XONG 4 ĐỘI!\n{mode} — Mỗi đội {per_team} người\nChúc các đội thi đấu thật bùng nổ!"))
    os.remove(path)

# ----------------- ĐĂNG KÝ LỆNH -----------------
def get_mitaizl():
    return {'randomteam': handle_randomteam_command}