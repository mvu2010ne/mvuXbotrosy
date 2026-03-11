# filename: modules/caro.py
import os
import time
import random
import uuid
import json
import re  # Thêm dòng này nếu chưa có
import glob
import colorsys
import requests
import threading  # Thêm để chạy timeout checker
from datetime import datetime, timezone, timedelta
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
from zlapi import *
from zlapi.models import *
from config import ADMIN  # ADMIN = ["uid1", "uid2", ...]

# ---------------------------
# Biến toàn cục - giữ nguyên cấu trúc thư mục gốc
# ---------------------------
caro_players = {}           # Quản lý ván chơi
CACHE_PATH = "cache/"
FONT_PATH = "font/"
BACKGROUND_PATH = "Resource/background/"
os.makedirs(CACHE_PATH, exist_ok=True)
os.makedirs("Database/minigame/caro", exist_ok=True)

BOARD_SIZE = 16
TOTAL_CELLS = BOARD_SIZE * BOARD_SIZE
WIN_LINE = 5

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
]

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
# ---------------------------
# Debug
# ---------------------------
def debug_print(message):
    print(f"[CARO {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

# ---------------------------
# Load / Save dữ liệu - CẬP NHẬT THÊM SỐ TRẬN VÀ TỈ LỆ THẮNG
# ---------------------------
def get_data_path(bot_uid):
    return f"Database/minigame/caro/{bot_uid}_caro.json"

def load_caro_data(bot_uid):
    path = get_data_path(bot_uid)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Đảm bảo cấu trúc dữ liệu mới cho tất cả người chơi
                for uid in data:
                    if "total_games" not in data[uid]:
                        data[uid]["total_games"] = 0
                    if "wins" not in data[uid]:
                        data[uid]["wins"] = 0
                    if "losses" not in data[uid]:
                        data[uid]["losses"] = 0
                    if "draws" not in data[uid]:
                        data[uid]["draws"] = 0
                    if "timeout_losses" not in data[uid]:
                        data[uid]["timeout_losses"] = 0
                return data
        except Exception as e:
            debug_print(f"Load data error: {e}")
            return {}
    return {}

def save_caro_data(bot_uid, data):
    path = get_data_path(bot_uid)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        debug_print(f"Save data error: {e}")

def update_player_stats(bot_uid, uid, username, result="win", stars=0, is_bot=False):
    """
    Cập nhật thống kê người chơi
    result: "win", "loss", "draw", "timeout_loss" (thua do thoát game)
    stars: số sao thay đổi (+ hoặc -)
    is_bot: True nếu là game với bot
    """
    data = load_caro_data(bot_uid)
    
    if uid not in data:
        data[uid] = {
            "username": username, 
            "level": 1, 
            "stars": 0,
            "total_games": 0,
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "timeout_losses": 0
        }
    
    # Cập nhật username
    data[uid]["username"] = username
    
    # Cập nhật số sao (không âm)
    new_stars = data[uid]["stars"] + stars
    data[uid]["stars"] = max(0, new_stars)
    
    # Cập nhật số trận và kết quả
    if result in ["win", "loss", "draw", "timeout_loss"]:
        data[uid]["total_games"] = data[uid].get("total_games", 0) + 1
        
        if result == "win":
            data[uid]["wins"] = data[uid].get("wins", 0) + 1
        elif result == "loss":
            data[uid]["losses"] = data[uid].get("losses", 0) + 1
        elif result == "draw":
            data[uid]["draws"] = data[uid].get("draws", 0) + 1
        elif result == "timeout_loss":
            data[uid]["losses"] = data[uid].get("losses", 0) + 1
            data[uid]["timeout_losses"] = data[uid].get("timeout_losses", 0) + 1
    
    # Tính tỉ lệ thắng
    total = data[uid].get("total_games", 1)
    wins = data[uid].get("wins", 0)
    win_rate = (wins / total * 100) if total > 0 else 0
    data[uid]["win_rate"] = round(win_rate, 2)
    
    # Cập nhật level (1 level mỗi 500 sao)
    data[uid]["level"] = 1 + data[uid]["stars"] // 500
    
    save_caro_data(bot_uid, data)
    return data[uid]

def get_player_stats(bot_uid, uid):
    """Lấy thống kê của người chơi"""
    data = load_caro_data(bot_uid)
    if uid in data:
        stats = data[uid]
        # Tính lại win_rate để đảm bảo chính xác
        total = stats.get("total_games", 0)
        wins = stats.get("wins", 0)
        if total > 0:
            stats["win_rate"] = round(wins / total * 100, 2)
        else:
            stats["win_rate"] = 0.0
        return stats
    return None

# ---------------------------
# Extract mentions
# ---------------------------
def extract_uids_from_mentions(message_object):
    if hasattr(message_object, "mentions") and message_object.mentions:
        return [m.uid for m in message_object.mentions]
    return []

# ---------------------------
# Font cache & tạo bàn cờ - THÊM TÔ MÀU Ô GẦN NHẤT
# ---------------------------
_font_cache = {}
def get_font(name, size):
    key = (name, size)
    if key not in _font_cache:
        try:
            _font_cache[key] = ImageFont.truetype(os.path.join(FONT_PATH, name), size)
        except:
            _font_cache[key] = ImageFont.load_default()
    return _font_cache[key]

def create_caro_board_image(moves, winning_line=None, last_move=None):
    """
    Tạo ảnh bàn cờ caro với ô gần nhất được tô màu vàng
    moves: dict các nước đi {số ô: ký tự}
    winning_line: danh sách các ô tạo thành đường thắng
    last_move: số ô của nước đi gần nhất (để tô màu vàng)
    """
    cell_size = 70  # Kích thước ô lớn hơn, rõ ràng hơn
    margin = 60
    board_width = BOARD_SIZE * cell_size
    board_height = board_width
    extra_top_space = 80  # Thêm khoảng trống trên để tiêu đề không đụng lưới cờ
    total_w = board_width + margin * 2
    total_h = board_height + margin * 2 + extra_top_space

    img = Image.new('RGBA', (total_w, total_h), color='#F5F5F5')  # Nền trắng xám nhạt
    draw = ImageDraw.Draw(img)

    # Font cơ bản (ưu tiên arial nếu có, fallback default)
    font_num = get_font("arial.ttf", 28)   # Số lớn hơn, xám đậm
    font_xo = get_font("arial.ttf", 60)    # X/O lớn
    font_title = get_font("3.otf", 48)     # Tiêu đề giữ đẹp

    positions = {}
    grid_y_offset = margin + extra_top_space  # Dịch lưới xuống để nhường chỗ tiêu đề

    for i in range(BOARD_SIZE):
        for j in range(BOARD_SIZE):
            idx = i * BOARD_SIZE + j + 1
            x0 = margin + j * cell_size
            y0 = grid_y_offset + i * cell_size
            x1 = x0 + cell_size
            y1 = y0 + cell_size

            # Tô màu vàng cho ô gần nhất
            if last_move == idx:
                draw.rectangle([x0, y0, x1, y1], outline="#333333", width=3, fill="#FFFACD")  # Màu vàng nhạt
                draw.rectangle([x0+2, y0+2, x1-2, y1-2], outline="#FFD700", width=2)  # Viền vàng đậm
            else:
                draw.rectangle([x0, y0, x1, y1], outline="#333333", width=3, fill="#FFFFFF")
                draw.rectangle([x0+2, y0+2, x1-2, y1-2], outline="#CCCCCC", width=1)

            cx = x0 + cell_size // 2
            cy = y0 + cell_size // 2
            positions[idx] = (cx, cy)

            if idx in moves:
                sym = moves[idx]
                color = "#FF4136" if sym == "X" else "#0074D9"  # Màu đỏ/xanh cơ bản
                # Vị trí thủ công bằng bbox (có thể hơi lệch tùy font)
                bbox = font_xo.getbbox(sym)
                text_x = x0 + (cell_size - (bbox[2] - bbox[0])) / 2
                text_y = y0 + (cell_size - (bbox[3] - bbox[1])) / 2
                draw.text((text_x, text_y), sym, fill=color, font=font_xo)
            else:
                num_str = str(idx)
                bbox = font_num.getbbox(num_str)
                text_x = x0 + (cell_size - (bbox[2] - bbox[0])) / 2
                text_y = y0 + (cell_size - (bbox[3] - bbox[1])) / 2
                draw.text((text_x, text_y), num_str, fill="#555555", font=font_num)  # Số xám đậm

    # Viền ngoài cổ điển, đen dày
    draw.rectangle([margin-10, grid_y_offset-10, total_w - margin +10, total_h - margin +10],
                   outline="#333333", width=5)

    # Tiêu đề đặt cao, có khoảng trống lớn phía trên
    draw.text((total_w//2, 40), "♛ CỜ CARO ♛", fill="#2C3E50", font=font_title, anchor="mt")
    
    # Hiển thị ô gần nhất được đánh (nếu có)
    if last_move:
        draw.text((total_w//2, total_h - 30), f"Ô gần nhất: {last_move}", 
                 fill="#FF6B00", font=get_font("arial.ttf", 24), anchor="mt")

    # Dòng thắng: chỉ line đỏ dày, không highlight vòng tròn (thô hơn)
    if winning_line:
        points = [positions[p] for p in winning_line[:WIN_LINE]]
        draw.line(points, fill="#FF0000", width=12)

    filename = os.path.join(CACHE_PATH, f"caro_{uuid.uuid4().hex}.png")
    img.save(filename, "PNG")
    return filename, total_w, total_h

# ---------------------------
# Kiểm tra thắng / hòa
# ---------------------------
def check_win(moves, symbol):
    board = [[' '] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    for pos, sym in moves.items():
        r, c = divmod(pos - 1, BOARD_SIZE)
        board[r][c] = sym

    directions = [(0,1), (1,0), (1,1), (1,-1)]
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] != symbol: continue
            for dr, dc in directions:
                count = 1
                line = [(r,c)]
                for k in range(1, WIN_LINE):
                    nr, nc = r + k*dr, c + k*dc
                    if not (0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE and board[nr][nc] == symbol): break
                    count += 1
                    line.append((nr,nc))
                for k in range(1, WIN_LINE):
                    nr, nc = r - k*dr, c - k*dc
                    if not (0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE and board[nr][nc] == symbol): break
                    count += 1
                    line.insert(0, (nr,nc))
                if count >= WIN_LINE:
                    win_line = [(rr*BOARD_SIZE + cc + 1) for rr, cc in line[:WIN_LINE]]
                    return True, win_line
    return False, []

def is_draw(moves):
    return len(moves) == TOTAL_CELLS

# ---------------------------
# AI Bot đơn giản (theo XO.py)
# ---------------------------
def bot_move(moves, bot_sym, player_sym):
    avail = [i for i in range(1, TOTAL_CELLS+1) if i not in moves]
    if not avail:
        return None

    # Thắng ngay
    for m in avail:
        temp = moves.copy()
        temp[m] = bot_sym
        if check_win(temp, bot_sym)[0]:
            return m

    # Chặn người chơi thắng ngay
    for m in avail:
        temp = moves.copy()
        temp[m] = player_sym
        if check_win(temp, player_sym)[0]:
            return m

    # Random
    return random.choice(avail)

# ---------------------------
# Xử lý thoát game với hình phạt - SỬA LỖI XÓA GAME NGAY LẬP TỨC
# ---------------------------
def handle_quit_game(key, author_id, thread_id, thread_type, client, bot_uid):
    """Xử lý khi người chơi thoát game: thua và trừ sao"""
    debug_print(f"BẮT ĐẦU xử lý thoát game: key={key}, author_id={author_id}")
    
    # Kiểm tra key có tồn tại không
    if key not in caro_players:
        debug_print(f"Key {key} không tồn tại, thử tìm key khác...")
        # Thử tìm key khác
        found_key = None
        for k in list(caro_players.keys()):
            if isinstance(k, tuple) and author_id in k:
                found_key = k
                break
            elif k == author_id and caro_players[k].get("mode") == "single":
                found_key = k
                break
        
        if found_key:
            debug_print(f"Tìm thấy key thay thế: {found_key}")
            key = found_key
        else:
            debug_print(f"KHÔNG tìm thấy game để thoát cho {author_id}")
            try:
                client.replyMessage(Message(text="⚠️ Bạn không có ván chơi nào để thoát!"), 
                                   thread_id=thread_id, thread_type=thread_type)
            except:
                pass
            return
    
    # Lấy game và XÓA NGAY LẬP TỨC
    game = caro_players.pop(key, None)
    if not game:
        debug_print(f"Không thể lấy game với key={key} (đã bị xóa trước đó?)")
        return
    
    debug_print(f"ĐÃ XÓA GAME: key={key} khỏi caro_players")
    debug_print(f"Game mode: {game.get('mode')}")
    
    quit_player_id = author_id
    
    # Lấy tên người thoát
    quit_player_name = "Người chơi"
    try:
        user_info = client.fetchUserInfo(quit_player_id)
        profiles = user_info.unchanged_profiles or user_info.changed_profiles
        if str(quit_player_id) in profiles:
            quit_player_name = profiles[str(quit_player_id)].zaloName
            if not quit_player_name or not quit_player_name.strip():
                quit_player_name = "Người chơi"
    except Exception as e:
        debug_print(f"Lỗi fetch tên người thoát: {e}")
        quit_player_name = "Người chơi"
    
    debug_print(f"Tên người thoát: {quit_player_name}")
    
    try:
        if game["mode"] == "single":
            # Game với bot: người chơi thua
            stars_lost = 200
            update_player_stats(bot_uid, quit_player_id, quit_player_name, 
                               result="timeout_loss", stars=-stars_lost)
            
            # Tạo ảnh bàn cờ
            last_move = game.get("last_move")
            path, w, h = create_caro_board_image(game["moves"], last_move=last_move)
            
            # Thông báo
            text = f"@{quit_player_name} đã thoát game!\n🚫 Bị xử thua -{stars_lost}⭐\n🤖 Bot thắng!"
            
            try:
                mention = Mention(quit_player_id, offset=0, length=len(f"@{quit_player_name}"))
                client.sendLocalImage(imagePath=path, thread_id=thread_id, thread_type=thread_type,
                                     width=w, height=h, message=Message(text=text, mention=mention))
            except Exception as e:
                debug_print(f"Lỗi gửi ảnh single game: {e}")
                try:
                    client.sendMessage(Message(text=text), thread_id=thread_id, thread_type=thread_type)
                except:
                    pass
            
            if os.path.exists(path):
                os.remove(path)
            
        elif game["mode"] == "pvp":
            # Game PvP: người thoát thua, đối thủ thắng
            player_ids = list(game["players"].keys())
            opponent_id = [pid for pid in player_ids if pid != quit_player_id][0]
            opponent_name = game["names"].get(opponent_id, "Đối thủ")
            
            debug_print(f"Đối thủ: {opponent_id} - {opponent_name}")
            
            # Cập nhật điểm: người thoát mất 200 sao, đối thủ được 300 sao
            stars_lost = 200
            stars_gained = 300
            
            # Người thoát: thua do timeout
            update_player_stats(bot_uid, quit_player_id, quit_player_name, 
                               result="timeout_loss", stars=-stars_lost)
            
            # Đối thủ: thắng
            update_player_stats(bot_uid, opponent_id, opponent_name, 
                               result="win", stars=stars_gained)
            
            # Tạo ảnh bàn cờ
            last_move = game.get("last_move")
            path, w, h = create_caro_board_image(game["moves"], last_move=last_move)
            
            # Thông báo với mention cả hai người
            text = f"@{quit_player_name} đã thoát game!\n🚫 Bị xử thua -{stars_lost}⭐\n@{opponent_name} thắng +{stars_gained}⭐"
            
            debug_print(f"Thông báo PvP: {text}")
            
            try:
                # Tạo mention cho cả hai
                at_quit = f"@{quit_player_name}"
                at_opp = f"@{opponent_name}"
                
                mention1 = Mention(quit_player_id, offset=text.find(at_quit), length=len(at_quit))
                mention2 = Mention(opponent_id, offset=text.find(at_opp), length=len(at_opp))
                mentions = [mention1, mention2]
                
                client.sendLocalImage(imagePath=path, thread_id=thread_id, thread_type=thread_type,
                                     width=w, height=h, message=Message(text=text, mentions=mentions))
            except Exception as e:
                debug_print(f"Lỗi gửi ảnh PvP: {e}")
                try:
                    # Fallback: gửi text không có mention
                    client.sendMessage(Message(text=text), thread_id=thread_id, thread_type=thread_type)
                except Exception as e2:
                    debug_print(f"Lỗi gửi text fallback: {e2}")
            
            if os.path.exists(path):
                os.remove(path)
        else:
            debug_print(f"Game mode không xác định: {game.get('mode')}")
    
    except Exception as e:
        debug_print(f"LỖI trong handle_quit_game: {e}")
        import traceback
        traceback.print_exc()
        try:
            client.sendMessage(Message(text=f"⚠️ Đã xảy ra lỗi khi xử lý thoát game."), 
                             thread_id=thread_id, thread_type=thread_type)
        except:
            pass
    
    debug_print(f"KẾT THÚC xử lý thoát game cho {author_id}")

# ---------------------------
# Tìm game cho người chơi - HÀM MỚI
# ---------------------------
def find_game_for_player(author_id):
    """Tìm game mà người chơi đang tham gia"""
    debug_print(f"Tìm game cho người chơi {author_id}")
    
    # In tất cả games hiện có để debug
    all_keys = list(caro_players.keys())
    debug_print(f"Tất cả games hiện có: {all_keys}")
    
    # Kiểm tra single player game
    if author_id in caro_players:
        game = caro_players[author_id]
        if game.get("mode") in ["single", "pvp_wait"]:
            debug_print(f"Tìm thấy single/pvp_wait game: key={author_id}, mode={game.get('mode')}")
            return author_id, game
    
    # Kiểm tra PvP game
    for key in all_keys:
        if isinstance(key, tuple):
            if author_id in key:
                game = caro_players[key]
                if game.get("mode") == "pvp":
                    debug_print(f"Tìm thấy PvP game: key={key}, mode=pvp")
                    return key, game
    
    debug_print(f"Không tìm thấy game cho {author_id}")
    return None, None

# ---------------------------
# Menu guide ảnh đẹp (từ XO.py - có fallback text)
# ---------------------------
def generate_menu_image():
    images = glob.glob(BACKGROUND_PATH + "*.jpg") + glob.glob(BACKGROUND_PATH + "*.png") + glob.glob(BACKGROUND_PATH + "*.jpeg")
    if not images:
        return None

    bg_path = random.choice(images)
    try:
        size = (1280, 400)
        bg = Image.open(bg_path).convert("RGBA").resize(size, Image.Resampling.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=15))
        overlay = Image.new("RGBA", size, (0, 0, 0, 100))
        draw = ImageDraw.Draw(overlay)

        font_path = os.path.join(FONT_PATH, "3.otf")
        try:
            font_title = ImageFont.truetype(font_path, 80)
            font_text = ImageFont.truetype(font_path, 50)
        except:
            font_title = ImageFont.load_default()
            font_text = ImageFont.load_default()

        draw.text((size[0]//2, 100), "♛ CỜ CARO ♛", fill=(255,255,255,255), font=font_title, anchor="mt")
        draw.text((size[0]//2, 200), "caro go • caro pvp @tag • caro bxh", fill=(255,255,255,220), font=font_text, anchor="mt")
        draw.text((size[0]//2, 280), "Nhập số 1-256 để đánh • 0 thoát (bị trừ sao)", fill=(255,100,100,220), font=font_text, anchor="mt")

        final = Image.alpha_composite(bg, overlay)
        path = os.path.join(CACHE_PATH, f"menu_{uuid.uuid4().hex}.png")
        final.save(path, "PNG")
        return path
    except:
        return None

# ---------------------------
# Bảng xếp hạng ảnh đẹp - CẬP NHẬT VỚI THỐNG KÊ MỚI
# ---------------------------
def draw_rounded_rectangle(draw, xy, radius, fill, outline=None, width=1):
    x1, y1, x2, y2 = xy
    draw.pieslice([x1, y1, x1 + 2*radius, y1 + 2*radius], 180, 270, fill=fill, outline=outline)
    draw.pieslice([x2 - 2*radius, y1, x2, y1 + 2*radius], 270, 360, fill=fill, outline=outline)
    draw.pieslice([x1, y2 - 2*radius, x1 + 2*radius, y2], 90, 180, fill=fill, outline=outline)
    draw.pieslice([x2 - 2*radius, y2 - 2*radius, x2, y2], 0, 90, fill=fill, outline=outline)
    draw.rectangle([x1+radius, y1, x2-radius, y1+radius], fill=fill, outline=outline)
    draw.rectangle([x1, y1+radius, x2, y2-radius], fill=fill, outline=outline)
    draw.rectangle([x1+radius, y2-radius, x2-radius, y2], fill=fill, outline=outline)

def draw_caro_leaderboard(bot_uid, client=None):
    """Vẽ bảng xếp hạng Caro với thống kê chính xác"""
    print(f"[CARO BXH] Bắt đầu vẽ bảng xếp hạng cho bot_uid: {bot_uid}")
    
    try:
        data = load_caro_data(bot_uid)
        print(f"[CARO BXH] Đã load dữ liệu, số người chơi: {len(data)}")
        
        # Sắp xếp theo stars
        sorted_players = sorted(data.items(), key=lambda x: x[1].get("stars", 0), reverse=True)[:20]
        
        if not sorted_players:
            print("[CARO BXH] Không có dữ liệu người chơi để vẽ")
            return None, None, None

        # ====== TÍNH TOÁN KÍCH THƯỚC TỰ ĐỘNG ======
        header_height = 180
        footer_height = 80
        top_padding = 40
        bottom_padding = 40
        side_padding = 50
        
        # Kích thước hàng
        row_height = 100
        
        # Số lượng người chơi
        num_players = len(sorted_players)
        
        # Tính chiều cao tổng tự động
        content_height = header_height + (num_players * row_height) + footer_height
        total_height = top_padding + content_height + bottom_padding
        
        # Chiều rộng cố định
        width = 1400
        
        print(f"[CARO BXH] Kích thước: {width}x{total_height} | Players: {num_players}")

        # ====== TẠO ẢNH VÀ NỀN ======
        image = Image.new('RGB', (width, total_height), '#0A0E1A')
        draw = ImageDraw.Draw(image)
        
        # Vẽ gradient nền từ trên xuống dưới
        for y in range(total_height):
            ratio = y / total_height
            r = int(10 + ratio * 15)
            g = int(14 + ratio * 10)
            b = int(26 + ratio * 20)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # ====== LOAD FONT ======
        try:
            font_title = ImageFont.truetype(os.path.join(FONT_PATH, "5.otf"), 56)
            font_header = ImageFont.truetype(os.path.join(FONT_PATH, "5.otf"), 28)
            font_name = ImageFont.truetype(os.path.join(FONT_PATH, "5.otf"), 26)
            font_id = ImageFont.truetype(os.path.join(FONT_PATH, "5.otf"), 24)
            font_numbers = ImageFont.truetype(os.path.join(FONT_PATH, "5.otf"), 26)
            font_percent = ImageFont.truetype(os.path.join(FONT_PATH, "5.otf"), 24)
            
            emoji_font_path = os.path.join(FONT_PATH, "NotoEmoji-Bold.ttf")
            if os.path.exists(emoji_font_path):
                font_emoji = ImageFont.truetype(emoji_font_path, 32)
                font_rank_emoji = ImageFont.truetype(emoji_font_path, 70)
            else:
                font_emoji = ImageFont.truetype(os.path.join(FONT_PATH, "5.otf"), 32)
                font_rank_emoji = ImageFont.truetype(os.path.join(FONT_PATH, "5.otf"), 40)
                
        except Exception as font_err:
            print(f"[CARO BXH] Lỗi load font: {font_err}")
            font_title = ImageFont.load_default()
            font_header = ImageFont.load_default()
            font_name = ImageFont.load_default()
            font_id = ImageFont.load_default()
            font_numbers = ImageFont.load_default()
            font_percent = ImageFont.load_default()
            font_emoji = ImageFont.load_default()
            font_rank_emoji = ImageFont.load_default()

        # ====== HEADER ======
        y_current = top_padding
        
        # Nền header với gradient
        header_gradient = Image.new('RGB', (width, header_height), (0, 0, 0))
        for y in range(header_height):
            ratio = y / header_height
            r = int(40 * (1 - ratio) + 10 * ratio)
            g = int(60 * (1 - ratio) + 20 * ratio)
            b = int(100 * (1 - ratio) + 40 * ratio)
            for x in range(width):
                header_gradient.putpixel((x, y), (r, g, b))
        
        header_gradient = header_gradient.filter(ImageFilter.GaussianBlur(radius=2))
        image.paste(header_gradient, (0, y_current))
        
        # Tiêu đề LEADERBOARD lớn
        title_text = "LEADERBOARD"
        title_bbox = draw.textbbox((0, 0), title_text, font=font_title)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (width - title_width) // 2
        
        title_gradient = random.choice(GRADIENT_SETS)
        draw_mixed_gradient_text(draw, title_text, (title_x, y_current + 40), 
                                font_title, font_emoji, title_gradient, shadow_offset=(3, 3))
        
        # Phụ đề
        subtitle_text = "CARO RANKING SYSTEM"
        subtitle_bbox = draw.textbbox((0, 0), subtitle_text, font=font_header)
        subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
        subtitle_x = (width - subtitle_width) // 2
        draw.text((subtitle_x, y_current + 110), subtitle_text, 
                 fill=(180, 190, 220), font=font_header)
        
        y_current += header_height
        
        # ====== TIÊU ĐỀ CỘT ======
        # Vị trí các cột (cập nhật cho thống kê mới)
        col_positions = [
            ("RANK", 70),
            ("", 160),      # Avatar
            ("NAME", 260),
            ("ID", 500),
            ("SCORES", 700),
            ("MATCHES", 880),
            ("WINRATE", 1050),
            ("WINS", 1230)
        ]
        
        # Nền cho tiêu đề cột
        draw.rectangle([(side_padding, y_current), 
                       (width - side_padding, y_current + 50)], 
                      fill=(30, 35, 60, 200))
        
        # Vẽ tiêu đề cột
        for col_text, x_pos in col_positions:
            if col_text:
                draw.text((x_pos, y_current + 15), col_text, 
                         fill=(220, 230, 250), font=font_header)
        
        # Đường kẻ dưới tiêu đề cột
        draw.line([(side_padding, y_current + 50), 
                   (width - side_padding, y_current + 50)], 
                  fill=(80, 90, 150), width=2)
        
        y_current += 60  # Di chuyển xuống dưới tiêu đề cột

        # ====== DANH SÁCH NGƯỜI CHƠI ======
        for idx, (uid, info) in enumerate(sorted_players):
            row_y = y_current + (idx * row_height)
            
            # Màu nền hàng xen kẽ
            if idx % 2 == 0:
                row_bg_color = (25, 30, 50, 180)
            else:
                row_bg_color = (20, 25, 45, 180)
            
            draw.rectangle([(side_padding, row_y), 
                           (width - side_padding, row_y + row_height - 10)], 
                          fill=row_bg_color)
            
            # 1. RANK
            rank = idx + 1
            
            if rank == 1:
                rank_display = "🥇"
                rank_color = (255, 215, 0)
                rank_font = font_rank_emoji
            elif rank == 2:
                rank_display = "🥈"
                rank_color = (200, 200, 220)
                rank_font = font_rank_emoji
            elif rank == 3:
                rank_display = "🥉"
                rank_color = (205, 127, 50)
                rank_font = font_rank_emoji
            else:
                rank_display = f"{rank}"
                rank_color = (180, 190, 220)
                rank_font = font_numbers
            
            rank_bbox = draw.textbbox((0, 0), rank_display, font=rank_font)
            rank_width = rank_bbox[2] - rank_bbox[0]
            rank_x = 40 + (80 - rank_width) // 2
            
            draw.text((rank_x, row_y + 30), rank_display, 
                     fill=rank_color, font=rank_font)

            # 2. AVATAR
            avatar_size = 70
            avatar_x = 160 - avatar_size // 2
            avatar_y = row_y + (row_height - avatar_size) // 2
            
            avatar_img = None
            avatar_url = None
            
            # Lấy avatar từ fetchUserInfo
            if client:
                try:
                    user_info_response = client.fetchUserInfo(str(uid))
                    profiles = user_info_response.unchanged_profiles or user_info_response.changed_profiles
                    if str(uid) in profiles:
                        user_info = profiles[str(uid)]
                        avatar_url = getattr(user_info, 'avatar', None)
                except Exception as e:
                    print(f"[CARO BXH] Lỗi fetch avatar: {e}")
            
            # Tải avatar
            if avatar_url and "default" not in avatar_url:
                try:
                    resp = requests.get(avatar_url, timeout=5)
                    if resp.status_code == 200:
                        avatar_img = Image.open(BytesIO(resp.content)).convert("RGBA")
                except:
                    pass
            
            # Nếu không có avatar, tạo placeholder
            if not avatar_img:
                import hashlib
                hash_val = hashlib.md5(uid.encode() if isinstance(uid, str) else str(uid).encode()).hexdigest()
                color_r = int(hash_val[0:2], 16)
                color_g = int(hash_val[2:4], 16)
                color_b = int(hash_val[4:6], 16)
                
                avatar_img = Image.new("RGBA", (avatar_size, avatar_size), 
                                      (color_r, color_g, color_b, 255))
                
                draw_avatar = ImageDraw.Draw(avatar_img)
                username = info.get("username", "Player")
                initials = username[:2].upper() if len(username) >= 2 else "PL"
                
                try:
                    avatar_font = ImageFont.truetype(os.path.join(FONT_PATH, "5.otf"), 28)
                except:
                    avatar_font = ImageFont.load_default()
                
                bbox = draw_avatar.textbbox((0, 0), initials, font=avatar_font)
                text_x = (avatar_size - (bbox[2] - bbox[0])) // 2
                text_y = (avatar_size - (bbox[3] - bbox[1])) // 2
                draw_avatar.text((text_x, text_y), initials, fill=(255, 255, 255), font=avatar_font)
            
            # Resize và làm tròn avatar
            avatar_img = avatar_img.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
            
            mask = Image.new("L", (avatar_size, avatar_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
            
            avatar_with_mask = Image.new("RGBA", (avatar_size, avatar_size), (0, 0, 0, 0))
            avatar_with_mask.paste(avatar_img, (0, 0), mask)
            
            border_size = avatar_size + 6
            border_img = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
            border_draw = ImageDraw.Draw(border_img)
            
            border_colors = [(255, 100, 100), (100, 255, 100), (100, 100, 255)]
            border_color = border_colors[idx % len(border_colors)]
            border_draw.ellipse((0, 0, border_size, border_size), fill=border_color)
            
            border_img.paste(avatar_with_mask, (3, 3), avatar_with_mask)
            image.paste(border_img, (avatar_x - 3, avatar_y - 3), border_img)

            # 3. NAME
            display_name = info.get("username", "Player")
            
            # Lấy tên thật từ Zalo nếu có
            if client:
                try:
                    user_info_response = client.fetchUserInfo(str(uid))
                    profiles = user_info_response.unchanged_profiles or user_info_response.changed_profiles
                    if str(uid) in profiles:
                        user_info = profiles[str(uid)]
                        zalo_name = getattr(user_info, 'zaloName', None)
                        if zalo_name and zalo_name.strip():
                            display_name = zalo_name.strip()
                except:
                    pass
            
            # Cắt tên nếu quá dài
            max_name_width = 200
            name_bbox = draw.textbbox((0, 0), display_name, font=font_name)
            name_width = name_bbox[2] - name_bbox[0]
            
            if name_width > max_name_width:
                for i in range(len(display_name), 0, -1):
                    short_name = display_name[:i] + "..."
                    short_bbox = draw.textbbox((0, 0), short_name, font=font_name)
                    if (short_bbox[2] - short_bbox[0]) <= max_name_width:
                        display_name = short_name
                        break
            
            # Vẽ tên với gradient
            name_gradient = random.choice(GRADIENT_SETS)
            draw_mixed_gradient_text(draw, display_name, (260, row_y + 35), 
                                    font_name, font_emoji, name_gradient)

            # 4. ID
            if uid.isdigit() and len(uid) >= 11:
                display_id = uid[:11]
            else:
                import hashlib
                hash_val = hashlib.md5(uid.encode() if isinstance(uid, str) else str(uid).encode()).hexdigest()
                display_id = hash_val[:11]
            
            draw.text((500, row_y + 35), display_id, 
                     fill=(180, 200, 255), font=font_id)

            # 5. SCORES (stars)
            stars = info.get("stars", 0)
            scores_text = f"{stars:,}"
            draw.text((700, row_y + 35), scores_text, 
                     fill=(255, 220, 100), font=font_numbers)

            # 6. MATCHES (số trận thực tế)
            total_games = info.get("total_games", 0)
            matches_text = f"{total_games:,}"
            matches_text = matches_text.replace(",", ".")
            
            draw.text((880, row_y + 35), matches_text, 
                     fill=(200, 220, 240), font=font_numbers)

            # 7. WINRATE (tỉ lệ thắng chính xác)
            win_rate = info.get("win_rate", 0.0)
            if win_rate > 0:
                winrate_text = f"{win_rate:05.2f}%"
            else:
                winrate_text = "0,00%"
            winrate_text = winrate_text.replace(".", ",")
            
            # Màu winrate
            if win_rate >= 90:
                winrate_color = (0, 255, 150)  # Xanh sáng
            elif win_rate >= 80:
                winrate_color = (100, 255, 100)  # Xanh lá
            elif win_rate >= 70:
                winrate_color = (255, 255, 100)  # Vàng
            elif win_rate >= 60:
                winrate_color = (255, 200, 100)  # Cam
            else:
                winrate_color = (255, 150, 100)  # Cam đỏ
            
            draw.text((1050, row_y + 35), winrate_text, 
                     fill=winrate_color, font=font_percent)

            # 8. WINS (số trận thắng)
            wins = info.get("wins", 0)
            wins_text = f"{wins:,}"
            wins_text = wins_text.replace(",", ".")
            wins_color = (100, 255, 150) if wins > 0 else (200, 200, 200)
            
            draw.text((1230, row_y + 35), wins_text, 
                     fill=wins_color, font=font_numbers)
            
            # Đường kẻ ngang phân cách
            if idx < len(sorted_players) - 1:
                draw.line([(side_padding, row_y + row_height - 5), 
                          (width - side_padding, row_y + row_height - 5)], 
                         fill=(40, 50, 80), width=1)
        
        y_current += (num_players * row_height)
        
        # ====== FOOTER ======
        footer_y = y_current + 20
        
        # Nền footer
        draw.rectangle([(side_padding, footer_y), 
                       (width - side_padding, total_height - bottom_padding)], 
                      fill=(20, 25, 45, 200))
        
        # Thông tin footer
        total_text = f"TOTAL PLAYERS: {len(data):,}"
        draw.text((side_padding + 20, footer_y + 20), total_text, 
                 fill=(180, 190, 220), font=font_id)
        
        # Timestamp
        timestamp = datetime.now().strftime("%Y-%m-d %H:%M")
        timestamp_bbox = draw.textbbox((0, 0), timestamp, font=font_id)
        timestamp_x = width - side_padding - 20 - (timestamp_bbox[2] - timestamp_bbox[0])
        draw.text((timestamp_x, footer_y + 20), timestamp, 
                 fill=(180, 190, 220), font=font_id)
        
        # ====== VIỀN TRANG TRÍ ======
        draw.rectangle([(side_padding - 5, top_padding - 5), 
                       (width - side_padding + 5, total_height - bottom_padding + 5)], 
                      outline=(60, 70, 120), width=3)
        
        corner_size = 15
        corners = [
            (side_padding - 5, top_padding - 5),
            (width - side_padding + 5, top_padding - 5),
            (side_padding - 5, total_height - bottom_padding + 5),
            (width - side_padding + 5, total_height - bottom_padding + 5)
        ]
        
        for x, y in corners:
            draw.line([(x, y + corner_size), (x, y)], fill=(80, 100, 180), width=2)
            draw.line([(x, y), (x + corner_size, y)], fill=(80, 100, 180), width=2)

        # ====== LƯU ẢNH ======
        path = os.path.join(CACHE_PATH, f"caro_bxh_{uuid.uuid4().hex}.png")
        image.save(path, "PNG", optimize=True, quality=95)
        
        print(f"[CARO BXH] Hoàn thành! Ảnh lưu tại: {path} ({width}x{total_height})")
        print(f"[CARO BXH] Chiều cao tự động: {total_height}px cho {num_players} players")
        
        return path, width, total_height

    except Exception as e:
        print(f"[CARO BXH] LỖI khi vẽ bảng xếp hạng: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

# ---------------------------
# Kiểm tra người chơi có đang trong ván nào không
# ---------------------------
def is_player_in_game(author_id):
    if author_id in caro_players:
        return True
    for k in caro_players:
        if isinstance(k, tuple) and author_id in k:
            return True
    return False

# ---------------------------
# Xử lý lệnh caro (logic từ XO.py - đã sửa theo yêu cầu)
# ---------------------------
def handle_caro_command(msg, message_object, thread_id, thread_type, author_id, client):
    bot_uid = client.uid
    name = getattr(message_object.sender, "name", "User")
    parts = msg.strip().split()

    if len(parts) <= 1:
        menu_path = generate_menu_image()
        if menu_path and os.path.exists(menu_path):
            client.sendLocalImage(imagePath=menu_path, thread_id=thread_id, thread_type=thread_type,
                                  message=Message(text=f"@{name} ♛ Menu Cờ Caro ♛"), width=1280, height=400)
            os.remove(menu_path)
        else:
            help_text = (
                "♛ CỜ CARO ♛\n\n"
                "➜ caro go      → Chơi với Bot\n"
                "➜ caro pvp @tag → Thách đấu người khác\n"
                "➜ caro bxh     → Xem bảng xếp hạng\n"
                "➜ caro reset   → Reset dữ liệu (admin)\n\n"
                "Nhập số 1-256 để đánh • 0 thoát (bị trừ sao)"
            )
            client.sendMessage(Message(text=help_text), thread_id, thread_type)
        return True

    action = parts[1].lower()

    # Kiểm tra chung: nếu đang trong bất kỳ ván nào thì không cho bắt đầu ván mới
    if action in ["go", "pvp"]:
        if is_player_in_game(author_id):
            client.replyMessage(Message(text="🚫 Bạn đang trong ván chơi! Hãy kết thúc ván hiện tại trước (gõ 0)."), message_object, thread_id, thread_type)
            return True

    if action == "go":
        player_sym = random.choice(["X", "O"])
        bot_sym = "O" if player_sym == "X" else "X"
        caro_players[author_id] = {
            "mode": "single",
            "player_sym": player_sym,
            "bot_sym": bot_sym,
            "moves": {},
            "last_move": None,
            "thread_id": thread_id,
            "thread_type": thread_type
        }

        path, w, h = create_caro_board_image({})
        text = f"@{name} bắt đầu chơi Caro!\nQuân: {'❌' if player_sym=='X' else '⭕'}\n{'Bạn đi trước!' if player_sym=='X' else 'Bot đi trước'}\nNhập 1-256 | 0 thoát (bị trừ sao)"
        mention = Mention(author_id, offset=text.find("@"), length=len(name)+1)
        client.sendLocalImage(imagePath=path, thread_id=thread_id, thread_type=thread_type,
                              width=w, height=h, message=Message(text=text, mention=mention))
        os.remove(path)
        return True

    elif action == "pvp":
        mentions = extract_uids_from_mentions(message_object)
        if not mentions:
            client.replyMessage(Message(text="⚠️ Vui lòng tag đối thủ để thách đấu!"), message_object, thread_id, thread_type)
            return True

        rival_id = mentions[0]
        if rival_id == author_id:
            client.replyMessage(Message(text="🚫 Không thể tự thách đấu mình!"), message_object, thread_id, thread_type)
            return True

        # === LẤY TÊN THẬT CỦA RIVAL (người bị thách đấu) ===
        rival_name = "Đối thủ"
        try:
            user_info = client.fetchUserInfo(rival_id)
            profiles = user_info.unchanged_profiles or user_info.changed_profiles
            if str(rival_id) in profiles:
                rival_name = profiles[str(rival_id)].zaloName.strip()
                if not rival_name:
                    rival_name = "Đối thủ"
        except Exception as e:
            debug_print(f"[PVP] Lỗi fetch tên rival: {e}")

        # === LẤY TÊN THẬT CỦA CHALLENGER (người thách đấu) ===
        challenger_name = "Người chơi"
        try:
            user_info = client.fetchUserInfo(author_id)
            profiles = user_info.unchanged_profiles or user_info.changed_profiles
            if str(author_id) in profiles:
                challenger_name = profiles[str(author_id)].zaloName.strip()
                if not challenger_name:
                    challenger_name = "Người chơi"
        except Exception as e:
            debug_print(f"[PVP] Lỗi fetch tên challenger: {e}")
        if challenger_name == "Người chơi":
            challenger_name = getattr(message_object.sender, "name", "Người chơi").strip()

        # === TẠO CHUỖI @ VÀ MENTION CHO RIVAL ===
        at_rival = f"@{rival_name}"
        mention = Mention(
            uid=rival_id,
            offset=0,
            length=len(at_rival)
        )

        text = f"{at_rival} ơi, @{challenger_name} thách đấu Caro với bạn!\nNhập 1 để chấp nhận\nNhập 0 để từ chối\n⏰ Hết hạn sau 60 giây"

        client.replyMessage(
            Message(text=text, mention=mention),
            message_object,
            thread_id,
            thread_type
        )

        # === LƯU TRẠNG THÁI CHỜ + TIMEOUT 60 GIÂY ===
        caro_players[rival_id] = {
            "mode": "pvp_wait",
            "challenger_id": author_id,
            "challenger_name": challenger_name,
            "rival_name": rival_name,
            "thread_id": thread_id,
            "thread_type": thread_type,
            "timeout": time.time() + 60  # 60 giây hết hạn
        }
        return True

    # Tìm phần xử lý bxh
    elif action == "bxh":
        print(f"[DEBUG] Đang gọi draw_caro_leaderboard với client: {client is not None}")
        path, w, h = draw_caro_leaderboard(bot_uid, client)
        if path:
            client.sendLocalImage(imagePath=path, thread_id=thread_id, thread_type=thread_type,
                                  message=Message(text="🏆 Top 20 Cờ Caro 🏆"), width=w, height=h)
            os.remove(path)
        else:
            client.sendMessage(Message(text="📊 Chưa có dữ liệu xếp hạng."), thread_id, thread_type)
        return True

    return False

# ---------------------------
# Xử lý nước đi và chấp nhận PVP - SỬA LỖI THOÁT GAME
# ---------------------------
def handle_caro_move(msg, message_object, thread_id, thread_type, author_id, client):
    bot_uid = client.uid
    text = msg.strip()
    
    debug_print(f"Xử lý di chuyển: author_id={author_id}, text='{text}'")

    # ==================== CHẤP NHẬN / TỪ CHỐI PVP ====================
    if author_id in caro_players and caro_players[author_id].get("mode") == "pvp_wait":
        debug_print(f"Người chơi {author_id} đang trong trạng thái chờ PvP")
        if text == "1":
            chal_id = caro_players[author_id]["challenger_id"]
            chal_name = caro_players[author_id]["challenger_name"]

            rival_real_name = "Người chơi"
            try:
                user_info = client.fetchUserInfo(author_id)
                profiles = user_info.unchanged_profiles or user_info.changed_profiles
                if str(author_id) in profiles:
                    tmp = profiles[str(author_id)].zaloName
                    if tmp and tmp.strip():
                        rival_real_name = tmp.strip()
            except Exception as e:
                debug_print(f"[CARO] Lỗi fetch tên rival khi chấp nhận: {e}")

            # Tạo key với tuple đã sorted để đảm bảo consistency
            key = tuple(sorted([author_id, chal_id]))
            caro_players[key] = {
                "mode": "pvp",
                "players": {chal_id: "X", author_id: "O"},
                "names": {chal_id: chal_name, author_id: rival_real_name},
                "current_turn": chal_id,
                "moves": {},
                "last_move": None,
                "thread_id": thread_id,
                "thread_type": thread_type
            }
            del caro_players[author_id]
            debug_print(f"Đã tạo PvP game mới: key={key}")

            first_player_name = chal_name
            second_player_name = rival_real_name

            text_msg = f"@{first_player_name} đi trước\n{first_player_name} ❌ - {second_player_name} ⭕\nNhập 1-256 | 0 thoát (bị trừ sao)"

            mention = Mention(uid=chal_id, offset=0, length=len(f"@{first_player_name}"))

            path, w, h = create_caro_board_image({})
            client.sendLocalImage(
                imagePath=path,
                thread_id=thread_id,
                thread_type=thread_type,
                width=w, height=h,
                message=Message(text=text_msg, mention=mention)
            )
            os.remove(path)
        elif text == "0":
            del caro_players[author_id]
            client.replyMessage(Message(text="❌ Từ chối thách đấu."), message_object, thread_id, thread_type)
        return True

    # ==================== THOÁT GAME VỚI HÌNH PHẠT ====================
    if text == "0":
        debug_print(f"Người chơi {author_id} muốn thoát game")
        
        # Sử dụng hàm mới để tìm game
        key, game_data = find_game_for_player(author_id)
        
        if key and game_data:
            debug_print(f"Xử lý thoát game cho {author_id} với key={key}")
            handle_quit_game(key, author_id, thread_id, thread_type, client, bot_uid)
        else:
            debug_print(f"Không tìm thấy game để thoát cho {author_id}")
            client.replyMessage(Message(text="⚠️ Bạn không có ván chơi nào để thoát!"), message_object, thread_id, thread_type)
        return True

    # ==================== ĐÁNH NƯỚC ĐI ====================
    try:
        move = int(text)
        if move < 1 or move > 256:
            debug_print(f"Số {move} không hợp lệ (1-256)")
            return False
    except:
        debug_print(f"Không phải số hợp lệ: {text}")
        return False

    # Sử dụng hàm mới để tìm game
    key, game = find_game_for_player(author_id)

    if not game:
        debug_print(f"Không tìm thấy game cho {author_id}")
        return False

    if move in game["moves"]:
        client.replyMessage(Message(text="🚫 Ô đã đánh!"), message_object, thread_id, thread_type)
        return True

    if game["mode"] == "pvp" and game["current_turn"] != author_id:
        client.replyMessage(Message(text="⏳ Chưa tới lượt bạn!"), message_object, thread_id, thread_type)
        return True

    sym = game["player_sym"] if game["mode"] == "single" else game["players"][author_id]
    game["moves"][move] = sym
    
    # Lưu nước đi gần nhất để tô màu vàng
    game["last_move"] = move
    debug_print(f"Người chơi {author_id} đánh ô {move} với ký hiệu {sym}")

    # ==================== LẤY TÊN THẬT + TẠO MENTION CHUẨN ====================
    display_name = "Người chơi"
    try:
        user_info = client.fetchUserInfo(author_id)
        profiles = user_info.unchanged_profiles or user_info.changed_profiles
        if str(author_id) in profiles:
            zalo_name = profiles[str(author_id)].zaloName
            if zalo_name and zalo_name.strip():
                display_name = zalo_name.strip()
    except Exception as e:
        debug_print(f"[CARO] Lỗi fetch tên người đánh: {e}")
        display_name = getattr(message_object.sender, "name", "Người chơi").strip()

    at_name = f"@{display_name}"
    mention = Mention(uid=author_id, offset=0, length=len(at_name))

    # ==================== KIỂM TRA THẮNG ====================
    win, line = check_win(game["moves"], sym)
    if win:
        debug_print(f"Người chơi {author_id} thắng!")
        # Xác định số sao thưởng
        if game["mode"] == "pvp":
            stars = 300
        else:  # single vs bot
            stars = 500
        
        # Cập nhật thống kê
        update_player_stats(bot_uid, author_id, display_name, result="win", stars=stars)

        text_msg = f"{at_name} THẮNG! +{stars}⭐"

        path, w, h = create_caro_board_image(game["moves"], line, last_move=move)
        client.sendLocalImage(
            imagePath=path,
            thread_id=thread_id,
            thread_type=thread_type,
            width=w, height=h,
            message=Message(text=text_msg, mention=mention)
        )
        os.remove(path)
        
        # Cập nhật thống kê cho đối thủ nếu là PvP
        if game["mode"] == "pvp":
            opponent_id = [pid for pid in game["players"] if pid != author_id][0]
            opponent_name = game["names"][opponent_id]
            update_player_stats(bot_uid, opponent_id, opponent_name, result="loss", stars=0)
        
        # Xóa game
        if key in caro_players:
            del caro_players[key]
            debug_print(f"Đã xóa game sau khi thắng: key={key}")
        return True

    # ==================== HÒA ====================
    if is_draw(game["moves"]):
        debug_print("Game hòa!")
        text_msg = "🤝 Hòa! Bàn cờ đầy."
        path, w, h = create_caro_board_image(game["moves"], last_move=move)
        client.sendLocalImage(
            imagePath=path,
            thread_id=thread_id,
            thread_type=thread_type,
            width=w, height=h,
            message=Message(text=text_msg)
        )
        os.remove(path)
        
        # Cập nhật thống kê cho tất cả người chơi
        if game["mode"] == "pvp":
            for pid, pname in game["names"].items():
                update_player_stats(bot_uid, pid, pname, result="draw", stars=0)
        else:  # single
            update_player_stats(bot_uid, author_id, display_name, result="draw", stars=0)
        
        # Xóa game
        if key in caro_players:
            del caro_players[key]
            debug_print(f"Đã xóa game sau khi hòa: key={key}")
        return True

    # ==================== BOT ĐÁNH (SINGLE) ====================
    bot_m = None
    if game["mode"] == "single":
        bot_m = bot_move(game["moves"], game["bot_sym"], game["player_sym"])
        if bot_m:
            game["moves"][bot_m] = game["bot_sym"]
            game["last_move"] = bot_m  # Cập nhật ô gần nhất
            debug_print(f"Bot đánh ô {bot_m}")
            
            bwin, bline = check_win(game["moves"], game["bot_sym"])
            if bwin:
                debug_print("Bot thắng!")
                update_player_stats(bot_uid, author_id, display_name, result="loss", stars=-100)

                lines = [f"🤖 Bot thắng!", f"{at_name} -100⭐"]
                text_msg = "\n".join(lines)

                path, w, h = create_caro_board_image(game["moves"], bline, last_move=bot_m)
                client.sendLocalImage(
                    imagePath=path,
                    thread_id=thread_id,
                    thread_type=thread_type,
                    width=w, height=h,
                    message=Message(text=text_msg, mention=mention)
                )
                os.remove(path)
                # Xóa game
                if key in caro_players:
                    del caro_players[key]
                    debug_print(f"Đã xóa game sau khi bot thắng: key={key}")
                return True

    # ==================== TẠO ẢNH TIẾP THEO VỚI Ô GẦN NHẤT ĐƯỢC TÔ MÀU ====================
    if game["mode"] == "single":
        lines = [
            f"{at_name} đánh ô {move}",
            "👉 Lượt: Bạn" if not bot_m else "🤖 Bot đã đánh"
        ]
        if bot_m:
            lines.insert(1, f"🤖 Bot đánh ô {bot_m}")
        lines.append("Nhập 1-256 | 0 thoát (bị trừ sao)")
        text_msg = "\n".join(lines)
        final_mention = mention
        last_move_to_show = bot_m if bot_m else move
    else:
        next_player_id = [p for p in game["players"] if p != author_id][0]
        next_player_name = game["names"][next_player_id]
        player_plain_name = display_name

        text_msg = f"@{next_player_name} đến lượt bạn\n{player_plain_name} đã đánh ô {move}\nNhập 1-256 | 0 thoát (bị trừ sao)"

        final_mention = Mention(
            uid=next_player_id,
            offset=0,
            length=len(f"@{next_player_name}")
        )

        game["current_turn"] = next_player_id
        last_move_to_show = move

    # Tạo ảnh với ô gần nhất được tô màu vàng
    debug_print(f"Tạo ảnh bàn cờ với ô gần nhất: {last_move_to_show}")
    path, w, h = create_caro_board_image(game["moves"], last_move=last_move_to_show)
    client.sendLocalImage(
        imagePath=path,
        thread_id=thread_id,
        thread_type=thread_type,
        width=w, height=h,
        message=Message(text=text_msg, mention=final_mention)
    )
    os.remove(path)
    return True

# ---------------------------
# Timeout checker cho lời mời PVP (60 giây)
# ---------------------------
def start_timeout_checker(client):
    def checker():
        while True:
            time.sleep(5)  # Kiểm tra mỗi 5 giây
            now = time.time()
            to_remove = []
            for key, game in list(caro_players.items()):
                if game.get("mode") == "pvp_wait":
                    if now > game.get("timeout", 0):
                        to_remove.append((key, game["thread_id"], game["thread_type"]))
            for key, tid, ttype in to_remove:
                try:
                    client.sendMessage(Message(text="⏰ Thách đấu Caro đã hết hạn!"), tid, ttype)
                except:
                    pass
                if key in caro_players:
                    del caro_players[key]
    threading.Thread(target=checker, daemon=True).start()

# ---------------------------
# Mapping cho main.py
# ---------------------------
def get_mitaizl():
    return {
        'caro': lambda msg, obj, tid, ttype, aid, cli: handle_caro_command(msg, obj, tid, ttype, aid, cli),
        '//caro': lambda msg, obj, tid, ttype, aid, cli: handle_caro_move(msg, obj, tid, ttype, aid, cli)
    }

# Lưu ý: Một số terminal Windows không hỗ trợ in tiếng Việt Unicode → tránh lỗi UnicodeEncodeError.
print("[CARO] Module Caro - Da cap nhat: To vang o gan nhat, xu thua khi thoat, thong ke chinh xac!")