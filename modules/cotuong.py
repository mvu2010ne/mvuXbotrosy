import json
import os
from PIL import Image, ImageDraw, ImageFont
from zlapi.models import Message
import random
from collections import defaultdict
import uuid
import threading
import logging
import re
import time

# Cấu hình logging
logging.basicConfig(filename='modules/cache/cotuong_data/cotuong_errors.log', level=logging.ERROR)

# Khóa đồng bộ hóa cho file JSON
json_lock = threading.Lock()

# Biến toàn cục để lưu trữ trò chơi và thách đấu
active_games = {}
pending_challenges = {}

# -------------------------------
# Các file dữ liệu
DATA_DIR = 'modules/cache/cotuong_data'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
MONEY_DATA_FILE = os.path.join(DATA_DIR, 'moneycotuong.json')
HISTORY_DATA_FILE = os.path.join(DATA_DIR, 'cotuong_history.json')
TEMP_IMAGE_DIR = os.path.join(DATA_DIR, 'temp')
if not os.path.exists(TEMP_IMAGE_DIR):
    os.makedirs(TEMP_IMAGE_DIR)

# -------------------------------
# Hàm hỗ trợ đọc/ghi JSON
def load_json(filepath, default):
    with json_lock:
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Error loading JSON {filepath}: {e}")
            return default

def save_json(filepath, data):
    with json_lock:
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logging.error(f"Error saving JSON {filepath}: {e}")

# -------------------------------
# Quản lý ví và lịch sử
def load_money_data():
    return load_json(MONEY_DATA_FILE, {})

def save_money_data(data):
    save_json(MONEY_DATA_FILE, data)

def load_history_data():
    return load_json(HISTORY_DATA_FILE, {})

def save_history_data(data):
    save_json(HISTORY_DATA_FILE, data)

# -------------------------------
# Nạp font với dự phòng
def load_fonts():
    try:
        return (
            ImageFont.truetype("modules/cache/fonts/Tapestry-Regular.ttf", 24),
            ImageFont.truetype("modules/cache/fonts/ChivoMono-VariableFont_wght.ttf", 20)
        )
    except Exception as e:
        logging.error(f"Font loading failed: {e}")
        try:
            return ImageFont.truetype("arial.ttf", 24), ImageFont.truetype("arial.ttf", 20)
        except:
            return ImageFont.load_default(), ImageFont.load_default()

FONT_TITLE, FONT_TEXT = load_fonts()

# -------------------------------
# Hằng số
MOVE_TIMEOUT = 300000  # 5 phút
ACCEPT_TIMEOUT = 60000  # 60 giây
PIECE_SYMBOLS = {
    'rK': '帅', 'rA': '仕', 'rB': '相', 'rN': '马', 'rR': '车', 'rC': '炮', 'rP': '兵',
    'bK': '将', 'bA': '士', 'bB': '象', 'bN': '马', 'bR': '车', 'bC': '炮', 'bP': '卒'
}

# -------------------------------
# Lớp trạng thái trò chơi
class CoTuongState:
    def __init__(self, challenger_id, opponent_id, bet_amount, thread_id):
        self.id = f"{thread_id}_{uuid.uuid4().hex[:8]}"
        self.thread_id = thread_id
        self.players = {'red': challenger_id, 'black': opponent_id}
        self.bet_amount = bet_amount
        self.board = self.initialize_board()
        self.current_turn = 'red'
        self.move_history = []
        self.last_move_time = int(time.time() * 1000)
        self.status = {'is_check': False, 'is_checkmate': False}
        self.last_drawn_history = []
        self.pending_surrender = None  # Lưu ID người yêu cầu đầu hàng

    def initialize_board(self):
        """Khởi tạo bàn cờ Cờ Tướng với vị trí ban đầu"""
        board = [[None for _ in range(9)] for _ in range(10)]
        # Quân đỏ (dưới)
        board[9] = ['rR', 'rN', 'rB', 'rA', 'rK', 'rA', 'rB', 'rN', 'rR']
        board[7] = [None, None, 'rC', None, None, None, 'rC', None, None]
        board[6] = ['rP', None, 'rP', None, 'rP', None, 'rP', None, 'rP']
        # Quân đen (trên)
        board[0] = ['bR', 'bN', 'bB', 'bA', 'bK', 'bA', 'bB', 'bN', 'bR']
        board[2] = [None, None, 'bC', None, None, None, 'bC', None, None]
        board[3] = ['bP', None, 'bP', None, 'bP', None, 'bP', None, 'bP']
        return board

    def parse_position(self, pos):
        try:
            col = ord(pos[0].lower()) - ord('a')
            row = 9 - (int(pos[1]) - 1)
            return {'row': row, 'col': col}
        except (ValueError, IndexError):
            return None

    def parse_traditional_move(self, move_str):
        """Phân tích nước đi truyền thống, ví dụ: 'Mã 2 tiến 3'"""
        pattern = r'^(?P<piece>[马车炮兵卒帅将士仕相象])(?P<col>\d)\s*(?P<dir>[进退平])(?P<amount>\d)$'
        match = re.match(pattern, move_str)
        if not match:
            return None
        piece = match.group('piece')
        col = int(match.group('col')) - 1  # Cột từ 1-9 thành 0-8
        dir = match.group('dir')
        amount = int(match.group('amount'))
        piece_type = {'马': 'N', '车': 'R', '炮': 'C', '兵': 'P', '卒': 'P', '帅': 'K', '将': 'K', '士': 'A', '仕': 'A', '相': 'B', '象': 'B'}
        color = 'r' if piece in ['兵', '帅', '仕', '相'] and self.current_turn == 'red' else 'b'
        piece_code = f"{color}{piece_type[piece]}"
        from_pos = None
        for row in range(10):
            if self.board[row][col] == piece_code:
                from_pos = {'row': row, 'col': col}
                break
        if not from_pos:
            return None
        to_pos = {'row': from_pos['row'], 'col': from_pos['col']}
        if piece_type[piece] == 'P':  # Tốt
            if dir == '进':
                to_pos['row'] += -1 if color == 'r' else 1
            elif dir == '平':
                to_pos['col'] += amount if color == 'r' else -amount
        else:  # Các quân khác
            if dir == '进':
                to_pos['row'] += -amount if color == 'r' else amount
            elif dir == '退':
                to_pos['row'] += amount if color == 'r' else -amount
            elif dir == '平':
                to_pos['col'] += amount if color == 'r' else -amount
        return from_pos, to_pos

    def is_valid_position(self, pos):
        return 0 <= pos['row'] < 10 and 0 <= pos['col'] < 9

    def is_valid_move(self, from_pos, to_pos, piece):
        """Kiểm tra nước đi hợp lệ (triển khai cơ bản)"""
        if not (self.is_valid_position(from_pos) and self.is_valid_position(to_pos)):
            return False
        piece_type = piece[1]
        color = piece[0]
        dr = to_pos['row'] - from_pos['row']
        dc = to_pos['col'] - from_pos['col']
        # Quy tắc cơ bản cho từng loại quân
        if piece_type == 'K':  # Tướng
            if not (0 <= to_pos['col'] <= 5 and (to_pos['row'] in (0, 1, 2) if color == 'b' else to_pos['row'] in (7, 8, 9))):
                return False
            return (abs(dr) == 1 and dc == 0) or (abs(dc) == 1 and dr == 0)
        elif piece_type == 'A':  # Sĩ
            if not (0 <= to_pos['col'] <= 5 and (to_pos['row'] in (0, 1, 2) if color == 'b' else to_pos['row'] in (7, 8, 9))):
                return False
            return abs(dr) == 1 and abs(dc) == 1
        elif piece_type == 'B':  # Tượng
            if (color == 'r' and to_pos['row'] < 5) or (color == 'b' and to_pos['row'] > 4):
                return False
            return abs(dr) == 2 and abs(dc) == 2 and not self.board[from_pos['row'] + dr//2][from_pos['col'] + dc//2]
        elif piece_type == 'N':  # Mã
            if (abs(dr) == 2 and abs(dc) == 1) or (abs(dr) == 1 and abs(dc) == 2):
                block_row = from_pos['row'] + (dr // 2 if abs(dr) == 2 else dr)
                block_col = from_pos['col'] + (dc // 2 if abs(dc) == 2 else dc)
                return not self.board[block_row][block_col]
            return False
        elif piece_type == 'R':  # Xe
            if dr != 0 and dc != 0:
                return False
            step = dr if dr != 0 else dc
            step_dir = 1 if step > 0 else -1
            for i in range(1, abs(step)):
                if dr != 0:
                    if self.board[from_pos['row'] + i * step_dir][from_pos['col']]:
                        return False
                else:
                    if self.board[from_pos['row']][from_pos['col'] + i * step_dir]:
                        return False
            return True
        elif piece_type == 'C':  # Pháo
            if dr != 0 and dc != 0:
                return False
            target = self.board[to_pos['row']][to_pos['col']]
            step = dr if dr != 0 else dc
            step_dir = 1 if step > 0 else -1
            pieces_between = 0
            for i in range(1, abs(step)):
                if dr != 0:
                    if self.board[from_pos['row'] + i * step_dir][from_pos['col']]:
                        pieces_between += 1
                else:
                    if self.board[from_pos['row']][from_pos['col'] + i * step_dir]:
                        pieces_between += 1
            return (not target and pieces_between == 0) or (target and pieces_between == 1)
        elif piece_type == 'P':  # Tốt
            if color == 'r':
                if from_pos['row'] > 4:  # Chưa qua sông
                    return dr == -1 and dc == 0
                else:
                    return (dr == -1 and dc == 0) or (abs(dc) == 1 and dr == 0)
            else:
                if from_pos['row'] < 5:  # Chưa qua sông
                    return dr == 1 and dc == 0
                else:
                    return (dr == 1 and dc == 0) or (abs(dc) == 1 and dr == 0)
        return False

    def make_move(self, from_pos, to_pos, player_color):
        if isinstance(from_pos, str):  # Định dạng tọa độ
            from_p = self.parse_position(from_pos)
            to_p = self.parse_position(to_pos)
        else:  # Định dạng dictionary từ parse_traditional_move
            from_p, to_p = from_pos, to_pos

        if not (from_p and to_p and self.is_valid_position(from_p) and self.is_valid_position(to_p)):
            return {'valid': False, 'message': "Tọa độ không hợp lệ"}

        piece = self.board[from_p['row']][from_p['col']]
        if not piece:
            return {'valid': False, 'message': "Không có quân cờ tại vị trí xuất phát"}
        if piece[0] != player_color[0]:
            return {'valid': False, 'message': "Đây không phải quân cờ của bạn"}

        if not self.is_valid_move(from_p, to_p, piece):
            return {'valid': False, 'message': "Nước đi không hợp lệ"}

        captured_piece = self.board[to_p['row']][to_p['col']]
        self.board[to_p['row']][to_p['col']] = piece
        self.board[from_p['row']][from_p['col']] = None

        if self.is_in_check(player_color):
            self.board[from_p['row']][from_p['col']] = piece
            self.board[to_p['row']][to_p['col']] = captured_piece
            return {'valid': False, 'message': "Nước đi này sẽ để tướng bị chiếu"}

        if self.is_repetitive_move():
            self.board[from_p['row']][from_p['col']] = piece
            self.board[to_p['row']][to_p['col']] = captured_piece
            return {'valid': False, 'message': "Nước đi lặp lại vi phạm luật Cờ Tướng"}

        self.move_history.append({'from': f"{chr(from_p['col'] + ord('a'))}{10 - from_p['row']}", 'to': f"{chr(to_p['col'] + ord('a'))}{10 - to_p['row']}", 'player': player_color})
        return {'valid': True}

    def is_repetitive_move(self):
        if len(self.move_history) < 8:
            return False
        recent_moves = self.move_history[-8:]
        return all(recent_moves[i] == recent_moves[i+4] for i in range(4))

    def is_checkmate(self, color):
        if not self.is_in_check(color):
            return False
        for row in range(10):
            for col in range(9):
                piece = self.board[row][col]
                if piece and piece[0] == color[0]:
                    for to_row in range(10):
                        for to_col in range(9):
                            move_result = self.make_move_simulated({'row': row, 'col': col}, {'row': to_row, 'col': to_col}, piece)
                            if move_result['valid']:
                                return False
        return True

    def make_move_simulated(self, from_p, to_p, piece):
        if not self.is_valid_move(from_p, to_p, piece):
            return {'valid': False}
        original_piece = self.board[to_p['row']][to_p['col']]
        self.board[to_p['row']][to_p['col']] = piece
        self.board[from_p['row']][from_p['col']] = None
        is_valid = not self.is_in_check(piece[0])
        self.board[from_p['row']][from_p['col']] = piece
        self.board[to_p['row']][to_p['col']] = original_piece
        return {'valid': is_valid}

    def is_in_check(self, color):
        red_king_pos, black_king_pos = None, None
        for row in range(10):
            for col in range(9):
                piece = self.board[row][col]
                if piece == 'rK':
                    red_king_pos = {'row': row, 'col': col}
                if piece == 'bK':
                    black_king_pos = {'row': row, 'col': col}
        if red_king_pos and black_king_pos and red_king_pos['col'] == black_king_pos['col']:
            has_blocking_piece = False
            min_row = min(red_king_pos['row'], black_king_pos['row']) + 1
            max_row = max(red_king_pos['row'], black_king_pos['row'])
            for row in range(min_row, max_row):
                if self.board[row][red_king_pos['col']]:
                    has_blocking_piece = True
                    break
            if not has_blocking_piece:
                return True if color == 'r' else False
        king_pos = red_king_pos if color == 'r' else black_king_pos
        opponent_color = 'b' if color == 'r' else 'r'
        for row in range(10):
            for col in range(9):
                piece = self.board[row][col]
                if piece and piece[0] == opponent_color:
                    if self.is_valid_move({'row': row, 'col': col}, king_pos, piece):
                        return True
        return False

    def check_game_status(self):
        self.status = {'is_check': False, 'is_checkmate': False}
        if self.is_in_check(self.current_turn):
            self.status['is_check'] = True
            self.status['is_checkmate'] = self.is_checkmate(self.current_turn)
        return self.status

    def check_timeout(self, client, thread_id, thread_type):
        if int(time.time() * 1000) - self.last_move_time > MOVE_TIMEOUT:
            winner = 'black' if self.current_turn == 'red' else 'red'
            end_game(self, winner, client, thread_id, thread_type)
            client.sendMessage(Message(text=f"⏰ Hết thời gian! Người chơi {self.players[winner]} thắng!"), thread_id=thread_id, thread_type=thread_type)
            return True
        return False

# -------------------------------
# Vẽ bàn cờ
def draw_board(state: CoTuongState):
    cache_path = os.path.join(TEMP_IMAGE_DIR, f"board_{state.id}_cache.png")
    if os.path.exists(cache_path) and state.move_history == state.last_drawn_history:
        return cache_path

    img = Image.new("RGB", (800, 900), color=(240, 217, 181))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 800, 900), fill=(240, 217, 181))
    for i in range(10):
        draw.line((100, 100 + i * 80, 700, 100 + i * 80), fill="black", width=2)
        if i < 9:
            draw.line((100 + i * 75, 100, 100 + i * 75, 820), fill="black", width=2)
    for row in range(10):
        for col in range(9):
            piece = state.board[row][col]
            if piece:
                x = 100 + col * 75
                y = 100 + row * 80
                color = "red" if piece[0] == 'r' else "black"
                draw.ellipse((x-20, y-20, x+20, y+20), fill=(255, 255, 255), outline="black")
                draw.text((x-10, y-10), PIECE_SYMBOLS[piece], font=FONT_TEXT, fill=color)
    draw.text((50, 50), f"Game ID: {state.id}", font=FONT_TITLE, fill="black")
    draw.text((50, 850), f"Turn: {state.current_turn.upper()}", font=FONT_TEXT, fill="black")
    draw.text((300, 850), f"Bet: {state.bet_amount:,} VNĐ", font=FONT_TEXT, fill="black")

    output_path = os.path.join(TEMP_IMAGE_DIR, f"board_{state.id}.png")
    img.save(output_path)
    state.last_drawn_history = state.move_history.copy()
    return output_path

# -------------------------------
# Xử lý lệnh
def handle_cotuong_challenge(message, message_object, thread_id, thread_type, author_id, client):
    parts = message.split()
    if len(parts) < 3 or not message_object.mentions:
        client.sendMessage(Message(text="❌ Cú pháp: cotuong thachdau <tiền cược> @nguoichoi"), thread_id=thread_id, thread_type=thread_type)
        return
    opponent_id = list(message_object.mentions.keys())[0]
    if opponent_id == author_id:
        client.sendMessage(Message(text="❌ Không thể thách đấu chính mình!"), thread_id=thread_id, thread_type=thread_type)
        return
    for ch in pending_challenges.values():
        if ch['opponent'] == opponent_id or ch['challenger'] == opponent_id:
            client.sendMessage(Message(text="❌ Đối thủ đang có thách đấu khác!"), thread_id=thread_id, thread_type=thread_type)
            return
    try:
        bet_amount = int(parts[2])
        if bet_amount < 1000:
            client.sendMessage(Message(text="❌ Tiền cược tối thiểu là 1,000 VNĐ!"), thread_id=thread_id, thread_type=thread_type)
            return
    except ValueError:
        client.sendMessage(Message(text="❌ Số tiền cược không hợp lệ!"), thread_id=thread_id, thread_type=thread_type)
        return
    money_data = load_money_data()
    balance = money_data.get(author_id, 10000)
    if balance < bet_amount:
        client.sendMessage(Message(text=f"❌ Số dư không đủ. Bạn chỉ có {balance:,} VNĐ!"), thread_id=thread_id, thread_type=thread_type)
        return
    challenge = {'challenger': author_id, 'opponent': opponent_id, 'bet_amount': bet_amount, 'thread_id': thread_id, 'timestamp': int(time.time() * 1000)}
    challenge_id = f"challenge_{thread_id}_{uuid.uuid4().hex[:8]}"
    pending_challenges[challenge_id] = challenge
    client.sendMessage(Message(text=f"🎮 Thách đấu Cờ Tướng!\n👤 {author_id} thách đấu {opponent_id}\n💰 Tiền cược: {bet_amount:,} VNĐ\n⏳ Chấp nhận trong 60 giây: 'cotuong chapnhan'"), thread_id=thread_id, thread_type=thread_type)

def handle_cotuong_accept(message, message_object, thread_id, thread_type, author_id, client):
    challenges = [(cid, ch) for cid, ch in pending_challenges.items() if ch['opponent'] == author_id and ch['thread_id'] == thread_id]
    if len(challenges) > 1:
        client.sendMessage(Message(text="❌ Có nhiều thách đấu, vui lòng thử lại sau!"), thread_id=thread_id, thread_type=thread_type)
        return
    if not challenges:
        client.sendMessage(Message(text="❌ Không tìm thấy thách đấu nào!"), thread_id=thread_id, thread_type=thread_type)
        return
    challenge_id, challenge = challenges[0]
    if int(time.time() * 1000) - challenge['timestamp'] > ACCEPT_TIMEOUT:
        del pending_challenges[challenge_id]
        client.sendMessage(Message(text="❌ Thách đấu đã hết hạn!"), thread_id=thread_id, thread_type=thread_type)
        return
    money_data = load_money_data()
    balance = money_data.get(author_id, 10000)
    if balance < challenge['bet_amount']:
        client.sendMessage(Message(text="❌ Số dư không đủ!"), thread_id=thread_id, thread_type=thread_type)
        return
    del pending_challenges[challenge_id]
    game_state = CoTuongState(challenge['challenger'], challenge['opponent'], challenge['bet_amount'], thread_id)
    active_games[game_state.id] = game_state
    board_path = draw_board(game_state)
    try:
        client.sendMessage(Message(text=f"🎮 Ván cờ bắt đầu!\n🔴 Quân đỏ: {challenge['challenger']}\n⚫ Quân đen: {challenge['opponent']}\n💰 Tiền cược: {challenge['bet_amount']:,} VNĐ\n⏳ Lượt đi: Quân đỏ"), thread_id=thread_id, thread_type=thread_type)
        client.sendLocalImage(board_path, thread_id=thread_id, thread_type=thread_type, width=800, height=900)
    except Exception as e:
        logging.error(f"Error sending board: {e}")
        client.sendMessage(Message(text="❌ Lỗi hiển thị bàn cờ, nhưng ván cờ đã bắt đầu!"), thread_id=thread_id, thread_type=thread_type)

def handle_cotuong_move(message, message_object, thread_id, thread_type, author_id, client):
    parts = message.split()
    game = None
    for g in active_games.values():
        if (g.players['red'] == author_id or g.players['black'] == author_id) and g.thread_id == thread_id:
            game = g
            break
    if not game:
        client.sendMessage(Message(text="❌ Bạn không trong ván cờ nào!"), thread_id=thread_id, thread_type=thread_type)
        return
    if game.check_timeout(client, thread_id, thread_type):
        return
    player_color = 'red' if game.players['red'] == author_id else 'black'
    if game.current_turn != player_color:
        client.sendMessage(Message(text="❌ Chưa đến lượt của bạn!"), thread_id=thread_id, thread_type=thread_type)
        return
    if len(parts) == 4:
        from_pos, to_pos = parts[2], parts[3]
        if not (len(from_pos) == 2 and len(to_pos) == 2 and from_pos[0].isalpha() and to_pos[0].isalpha() and from_pos[1].isdigit() and to_pos[1].isdigit()):
            client.sendMessage(Message(text="❌ Tọa độ phải có dạng chữ+số, ví dụ: e2 e4"), thread_id=thread_id, thread_type=thread_type)
            return
    elif len(parts) == 3:  # Định dạng truyền thống
        move_str = parts[2]
        parsed = game.parse_traditional_move(move_str)
        if not parsed:
            client.sendMessage(Message(text="❌ Nước đi truyền thống không hợp lệ, ví dụ: 'Mã 2 tiến 3'"), thread_id=thread_id, thread_type=thread_type)
            return
        from_pos, to_pos = parsed
    else:
        client.sendMessage(Message(text="❌ Cú pháp: cotuong datco <tọa độ gốc> <tọa độ đích> hoặc cotuong datco <nước đi truyền thống>"), thread_id=thread_id, thread_type=thread_type)
        return
    move_result = game.make_move(from_pos, to_pos, player_color)
    if not move_result['valid']:
        client.sendMessage(Message(text=f"❌ {move_result['message']}"), thread_id=thread_id, thread_type=thread_type)
        return
    game.current_turn = 'black' if game.current_turn == 'red' else 'red'
    game.last_move_time = int(time.time() * 1000)
    game_status = game.check_game_status()
    board_path = draw_board(game)
    status_msg = f"🎮 Nước đi: {game.move_history[-1]['from']} → {game.move_history[-1]['to']}\n⏳ Lượt đi: {'Quân đỏ' if game.current_turn == 'red' else 'Quân đen'}"
    if game_status['is_check']:
        status_msg += "\n⚠️ CHIẾU TƯỚNG!"
    if game_status['is_checkmate']:
        winner = player_color
        end_game(game, winner, client, thread_id, thread_type)
        status_msg += f"\n🎉 CHIẾU BÍ! Người chơi {game.players[winner]} thắng!"
    try:
        client.sendMessage(Message(text=status_msg), thread_id=thread_id, thread_type=thread_type)
        client.sendLocalImage(board_path, thread_id=thread_id, thread_type=thread_type, width=800, height=900)
    except Exception as e:
        logging.error(f"Error sending move update: {e}")
        client.sendMessage(Message(text=f"{status_msg}\n❌ Lỗi hiển thị bàn cờ!"), thread_id=thread_id, thread_type=thread_type)

def handle_cotuong_surrender(message, message_object, thread_id, thread_type, author_id, client):
    game = None
    for g in active_games.values():
        if (g.players['red'] == author_id or g.players['black'] == author_id) and g.thread_id == thread_id:
            game = g
            break
    if not game:
        client.sendMessage(Message(text="❌ Bạn không trong ván cờ nào!"), thread_id=thread_id, thread_type=thread_type)
        return
    parts = message.split()
    if len(parts) == 3 and parts[2].lower() == 'xacnhan':
        winner = 'black' if game.players['red'] == author_id else 'red'
        end_game(game, winner, client, thread_id, thread_type)
        client.sendMessage(Message(text=f"🏳️ Người chơi {author_id} đã đầu hàng!\n🎉 Người chơi {game.players[winner]} thắng!"), thread_id=thread_id, thread_type=thread_type)
    else:
        game.pending_surrender = author_id
        client.sendMessage(Message(text="⚠️ Bạn có chắc muốn đầu hàng? Gõ 'cotuong dauhang xacnhan' để xác nhận."), thread_id=thread_id, thread_type=thread_type)

def handle_cotuong_draw(message, message_object, thread_id, thread_type, author_id, client):
    game = None
    for g in active_games.values():
        if (g.players['red'] == author_id or g.players['black'] == author_id) and g.thread_id == thread_id:
            game = g
            break
    if not game:
        client.sendMessage(Message(text="❌ Bạn không trong ván cờ nào!"), thread_id=thread_id, thread_type=thread_type)
        return
    parts = message.split()
    if len(parts) == 3 and parts[2].lower() == 'xacnhan':
        money_data = load_money_data()
        for player in [game.players['red'], game.players['black']]:
            money_data[player] = money_data.get(player, 10000)
        save_money_data(money_data)
        history_data = load_history_data()
        history_data[game.id] = {'result': 'draw', 'bet_amount': game.bet_amount, 'moves': game.move_history}
        save_history_data(history_data)
        del active_games[game.id]
        client.sendMessage(Message(text="🤝 Ván cờ kết thúc hòa!"), thread_id=thread_id, thread_type=thread_type)
    else:
        client.sendMessage(Message(text="⚠️ Đề nghị hòa cờ. Đối thủ cần gõ 'cotuong hoa xacnhan' để đồng ý."), thread_id=thread_id, thread_type=thread_type)

def handle_cotuong_status(message, message_object, thread_id, thread_type, author_id, client):
    game = None
    for g in active_games.values():
        if (g.players['red'] == author_id or g.players['black'] == author_id) and g.thread_id == thread_id:
            game = g
            break
    if not game:
        client.sendMessage(Message(text="❌ Bạn không trong ván cờ nào!"), thread_id=thread_id, thread_type=thread_type)
        return
    status_msg = f"📊 Trạng thái Cờ Tướng:\n"
    status_msg += f"• Game ID: {game.id}\n"
    status_msg += f"• Quân đỏ: {game.players['red']}\n"
    status_msg += f"• Quân đen: {game.players['black']}\n"
    status_msg += f"• Tiền cược: {game.bet_amount:,} VNĐ\n"
    status_msg += f"• Lượt đi: {'Quân đỏ' if game.current_turn == 'red' else 'Quân đen'}\n"
    status_msg += f"• Trạng thái: {'CHIẾU TƯỚNG' if game.status['is_check'] else 'Bình thường'}"
    parts = message.split()
    if len(parts) > 2 and parts[2].lower() == 'lichsu':
        status_msg += "\n📜 Lịch sử nước đi:\n" + "\n".join(f"{m['player']}: {m['from']} → {m['to']}" for m in game.move_history[-5:])
    board_path = draw_board(game)
    try:
        client.sendMessage(Message(text=status_msg), thread_id=thread_id, thread_type=thread_type)
        client.sendLocalImage(board_path, thread_id=thread_id, thread_type=thread_type, width=800, height=900)
    except Exception as e:
        logging.error(f"Error sending status: {e}")
        client.sendMessage(Message(text=f"{status_msg}\n❌ Lỗi hiển thị bàn cờ!"), thread_id=thread_id, thread_type=thread_type)

def handle_cotuong_stats(message, message_object, thread_id, thread_type, author_id, client):
    money_data = load_money_data()
    history_data = load_history_data()
    stats = {'wins': 0, 'losses': 0, 'draws': 0, 'balance': money_data.get(author_id, 10000)}
    for game_id, game in history_data.items():
        if game.get('winner') == author_id:
            stats['wins'] += 1
        elif game.get('result') == 'draw':
            stats['draws'] += 1
        elif 'winner' in game and author_id != game['winner']:
            stats['losses'] += 1
    msg = f"📈 Thống kê của {author_id}:\n"
    msg += f"• Số dư: {stats['balance']:,} VNĐ\n"
    msg += f"• Thắng: {stats['wins']}\n"
    msg += f"• Thua: {stats['losses']}\n"
    msg += f"• Hòa: {stats['draws']}"
    client.sendMessage(Message(text=msg), thread_id=thread_id, thread_type=thread_type)

def clean_expired_challenges():
    current_time = int(time.time() * 1000)
    expired = [cid for cid, ch in pending_challenges.items() if current_time - ch['timestamp'] > ACCEPT_TIMEOUT]
    for cid in expired:
        del pending_challenges[cid]

def handle_cotuong_command(message, message_object, thread_id, thread_type, author_id, client):
    clean_expired_challenges()
    text = message.split()
    if len(text) < 2:
        help_text = "\n".join([
            "• 'cotuong thachdau <tiền cược> @nguoichoi': Thách đấu.",
            "• 'cotuong chapnhan': Chấp nhận thách đấu.",
            "• 'cotuong datco <tọa độ gốc> <tọa độ đích>': Di chuyển, ví dụ: cotuong datco e2 e4",
            "• 'cotuong datco <nước đi truyền thống>': Ví dụ: cotuong datco Mã 2 tiến 3",
            "• 'cotuong dauhang': Đầu hàng (yêu cầu xác nhận).",
            "• 'cotuong hoa': Đề nghị hòa cờ.",
            "• 'cotuong xem': Xem trạng thái bàn cờ.",
            "• 'cotuong xem lichsu': Xem lịch sử nước đi.",
            "• 'cotuong thongke': Xem thống kê cá nhân."
        ])
        try:
            client.sendMessage(Message(text=f"🎴 HƯỚNG DẪN CỜ TƯỚNG:\n{help_text}"), thread_id=thread_id, thread_type=thread_type)
        except Exception as e:
            logging.error(f"Error sending help: {e}")
        return

    command = text[1].lower()
    try:
        if command == "thachdau":
            handle_cotuong_challenge(message, message_object, thread_id, thread_type, author_id, client)
        elif command == "chapnhan":
            handle_cotuong_accept(message, message_object, thread_id, thread_type, author_id, client)
        elif command == "datco":
            handle_cotuong_move(message, message_object, thread_id, thread_type, author_id, client)
        elif command == "dauhang":
            handle_cotuong_surrender(message, message_object, thread_id, thread_type, author_id, client)
        elif command == "hoa":
            handle_cotuong_draw(message, message_object, thread_id, thread_type, author_id, client)
        elif command == "xem":
            handle_cotuong_status(message, message_object, thread_id, thread_type, author_id, client)
        elif command == "thongke":
            handle_cotuong_stats(message, message_object, thread_id, thread_type, author_id, client)
        else:
            client.sendMessage(Message(text="❌ Lệnh không hợp lệ!"), thread_id=thread_id, thread_type=thread_type)
    except Exception as e:
        logging.error(f"Error in command {command}: {e}")
        client.sendMessage(Message(text="❌ Lỗi hệ thống, vui lòng thử lại!"), thread_id=thread_id, thread_type=thread_type)

def end_game(game, winner, client, thread_id, thread_type):
    loser = 'black' if winner == 'red' else 'red'
    money_data = load_money_data()
    money_data[game.players[winner]] = money_data.get(game.players[winner], 10000) + game.bet_amount
    money_data[game.players[loser]] = money_data.get(game.players[loser], 10000) - game.bet_amount
    save_money_data(money_data)
    history_data = load_history_data()
    history_data[game.id] = {'winner': game.players[winner], 'bet_amount': game.bet_amount, 'moves': game.move_history}
    save_history_data(history_data)
    del active_games[game.id]

def get_mitaizl():
    return {
        'cotuong': handle_cotuong_command
    }