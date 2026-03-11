import json
import random
import os
from PIL import Image, ImageDraw, ImageFont
from zlapi.models import Message

# -------------------------------
# Mô tả module
des = {
    'tác giả': "Inspired by Minh Vũ Shinn Cte & Grok",
    'mô tả': "Xì Tố Nhóm: Mỗi người chơi được chia 2 lá bài riêng, cược tiền ảo qua các vòng với 5 lá bài chung. Người có bài mạnh nhất (đôi, sảnh, v.v.) hoặc cuối cùng còn lại thắng pot.",
    'tính năng': [
        "• Khởi tạo trò chơi với mức cược tối thiểu.",
        "• Hiển thị bài chung qua ảnh, bài riêng qua tin nhắn riêng.",
        "• Cược, tố, theo, hoặc bỏ bài qua lệnh.",
        "• Tính tổ hợp bài cơ bản (đôi, sám, sảnh, v.v.).",
        "• Lưu ví tiền ảo và lịch sử chơi."
    ],
    'hướng dẫn sử dụng': [
        "• 'poker start <tiền cược>': Bắt đầu trò chơi. Ví dụ: poker start 1000",
        "• 'poker join': Tham gia trước khi chia bài. Ví dụ: poker join",
        "• 'poker action <call|raise <số tiền>|fold>': Hành động trong lượt.",
        "   - call: Theo cược hiện tại.",
        "   - raise <số tiền>: Tố thêm. Ví dụ: poker action raise 2000",
        "   - fold: Bỏ bài.",
        "• 'poker status': Xem trạng thái (lượt ai, pot, bài chung)."
    ]
}

# -------------------------------
# Các file dữ liệu
DATA_DIR = 'modules/cache/poker_data'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
MONEY_DATA_FILE = os.path.join(DATA_DIR, 'moneypoker.json')
HISTORY_DATA_FILE = os.path.join(DATA_DIR, 'poker_history.json')

# -------------------------------
# Hàm hỗ trợ đọc/ghi JSON
def load_json(filepath, default):
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def save_json(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

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

def format_money(amount):
    return f"{amount:,} VNĐ"

# -------------------------------
# Nạp font
try:
    FONT_TITLE = ImageFont.truetype("modules/cache/fonts/Tapestry-Regular.ttf", 24)
    FONT_TEXT = ImageFont.truetype("modules/cache/fonts/ChivoMono-VariableFont_wght.ttf", 20)
except Exception:
    FONT_TITLE = ImageFont.load_default()
    FONT_TEXT = ImageFont.load_default()

# -------------------------------
# Hằng số cho trò chơi
BOARD_SIZE = (700, 350)  # Kích thước bàn bài
CARD_SIZE = (50, 70)     # Kích thước lá bài
SUITS = ['♠', '♥', '♦', '♣']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
COLORS = {'♠': 'black', '♥': 'red', '♦': 'red', '♣': 'black'}
RANK_VALUES = {r: i+2 for i, r in enumerate(RANKS)}

# -------------------------------
# Lớp trạng thái trò chơi
class PokerState:
    def __init__(self, min_bet):
        self.players = {}  # {author_id: {'cards': [(rank, suit)], 'chips': int, 'in_game': bool, 'bet': int}}
        self.deck = [(r, s) for r in RANKS for s in SUITS]
        random.shuffle(self.deck)
        self.community_cards = []
        self.pot = 0
        self.min_bet = min_bet
        self.current_bet = min_bet
        self.turn_order = []
        self.current_turn = 0
        self.round = 'pre-flop'  # pre-flop, flop, turn, river, showdown

    def add_player(self, author_id):
        money_data = load_money_data()
        chips = money_data.get(author_id, 10000)  # Mặc định 10,000 VNĐ ảo
        if author_id not in self.players:
            self.players[author_id] = {
                'cards': [],
                'chips': chips,
                'in_game': True,
                'bet': 0
            }
            self.turn_order.append(author_id)
            money_data[author_id] = chips
            save_money_data(money_data)

    def deal_cards(self):
        for player_id in self.players:
            self.players[player_id]['cards'] = [self.deck.pop() for _ in range(2)]

    def deal_community(self, count):
        self.community_cards.extend([self.deck.pop() for _ in range(count)])

    def next_round(self):
        self.round = {'pre-flop': 'flop', 'flop': 'turn', 'turn': 'river', 'river': 'showdown'}.get(self.round, 'showdown')
        if self.round == 'flop':
            self.deal_community(3)
        elif self.round in ['turn', 'river']:
            self.deal_community(1)
        self.current_bet = 0
        for player_id in self.players:
            self.players[player_id]['bet'] = 0
        self.current_turn = 0

    def evaluate_hand(self, player_id):
        cards = self.players[player_id]['cards'] + self.community_cards
        ranks = [RANK_VALUES[card[0]] for card in cards]
        suits = [card[1] for card in cards]
        rank_counts = {r: ranks.count(r) for r in ranks}
        suit_counts = {s: suits.count(s) for s in suits}

        # Kiểm tra Flush (5 lá cùng chất)
        if max(suit_counts.values()) >= 5:
            return (5, max(ranks))  # Flush, trả về rank cao nhất

        # Kiểm tra Straight (Sảnh)
        unique_ranks = sorted(set(ranks))
        for i in range(len(unique_ranks) - 4):
            if unique_ranks[i+4] - unique_ranks[i] == 4:
                return (4, unique_ranks[i+4])  # Straight

        # Kiểm tra Three of a Kind (Sám)
        if 3 in rank_counts.values():
            rank = next(r for r, c in rank_counts.items() if c == 3)
            return (3, rank)

        # Kiểm tra Pair (Đôi)
        if 2 in rank_counts.values():
            rank = next(r for r, c in rank_counts.items() if c == 2)
            return (2, rank)

        # High Card
        return (1, max(ranks))

    def find_winner(self):
        active_players = [pid for pid in self.players if self.players[pid]['in_game']]
        if len(active_players) == 1:
            return active_players[0], "Last player standing"
        scores = [(pid, self.evaluate_hand(pid)) for pid in active_players]
        winner = max(scores, key=lambda x: x[1])
        hand_types = {1: "High Card", 2: "Pair", 3: "Three of a Kind", 4: "Straight", 5: "Flush"}
        return winner[0], hand_types[winner[1][0]]

# -------------------------------
# Vẽ bàn bài
def draw_table(state: PokerState):
    img = Image.new("RGB", BOARD_SIZE, color=(0, 100, 0))  # Bàn xanh
    draw = ImageDraw.Draw(img)

    # Vẽ bài chung
    for i, (rank, suit) in enumerate(state.community_cards):
        x, y = 250 + i * 60, 120
        draw.rectangle([x, y, x + CARD_SIZE[0], y + CARD_SIZE[1]], fill="white", outline="black")
        draw.text((x + 10, y + 10), f"{rank}{suit}", font=FONT_TEXT, fill=COLORS[suit])

    # Vẽ pot
    draw.text((300, 80), f"Pot: {format_money(state.pot)}", font=FONT_TITLE, fill="yellow")

    # Vẽ trạng thái người chơi
    for i, player_id in enumerate(state.players):
        x, y = 50, 50 + i * 40
        player = state.players[player_id]
        status = "Playing" if player['in_game'] else "Folded"
        draw.text((x, y), f"Player {i+1}: {format_money(player['chips'])} ({status})", font=FONT_TEXT, fill="white")

    # Vẽ vòng hiện tại và lượt
    draw.text((50, 300), f"Round: {state.round.upper()}", font=FONT_TEXT, fill="white")
    draw.text((200, 300), f"Turn: Player {state.turn_order[state.current_turn]}", font=FONT_TEXT, fill="white")

    output_path = os.path.join(DATA_DIR, "table.png")
    img.save(output_path)
    return output_path

# -------------------------------
# Biến toàn cục
game_state = None

# -------------------------------
# Xử lý lệnh "poker start"
def handle_poker_start(message, message_object, thread_id, thread_type, author_id, client):
    global game_state
    parts = message.split()
    if len(parts) != 3:
        client.sendMessage(Message(text="❌ Cú pháp: poker start <tiền cược>"), thread_id=thread_id, thread_type=thread_type)
        return
    try:
        min_bet = int(parts[2])
        if min_bet < 100:
            client.sendMessage(Message(text="❌ Tiền cược tối thiểu là 100 VNĐ ảo!"), thread_id=thread_id, thread_type=thread_type)
            return
        game_state = PokerState(min_bet)
        game_state.add_player(author_id)
        client.sendMessage(Message(text="🎴 Trò chơi Xì Tố bắt đầu! Dùng 'poker join' để tham gia trong 30 giây."), thread_id=thread_id, thread_type=thread_type)
    except ValueError:
        client.sendMessage(Message(text="❌ Tiền cược không hợp lệ."), thread_id=thread_id, thread_type=thread_type)

# -------------------------------
# Xử lý lệnh "poker join"
def handle_poker_join(message, message_object, thread_id, thread_type, author_id, client):
    global game_state
    if game_state is None:
        client.sendMessage(Message(text="❌ Trò chơi chưa khởi động. Gõ 'poker start <tiền cược>'!"), thread_id=thread_id, thread_type=thread_type)
        return
    if game_state.round != 'pre-flop':
        client.sendMessage(Message(text="❌ Không thể tham gia khi trò chơi đã bắt đầu."), thread_id=thread_id, thread_type=thread_type)
        return
    if author_id in game_state.players:
        client.sendMessage(Message(text="❌ Bạn đã tham gia rồi!"), thread_id=thread_id, thread_type=thread_type)
        return
    game_state.add_player(author_id)
    client.sendMessage(Message(text=f"✅ Người chơi {author_id} đã tham gia!"), thread_id=thread_id, thread_type=thread_type)

# -------------------------------
# Xử lý lệnh "poker action"
def handle_poker_action(message, message_object, thread_id, thread_type, author_id, client):
    global game_state
    if game_state is None:
        client.sendMessage(Message(text="❌ Trò chơi chưa khởi động."), thread_id=thread_id, thread_type=thread_type)
        return
    if author_id != game_state.turn_order[game_state.current_turn]:
        client.sendMessage(Message(text="❌ Chưa đến lượt bạn!"), thread_id=thread_id, thread_type=thread_type)
        return

    parts = message.split()
    if len(parts) < 3:
        client.sendMessage(Message(text="❌ Cú pháp: poker action <call|raise <số tiền>|fold>"), thread_id=thread_id, thread_type=thread_type)
        return

    action = parts[2].lower()
    player = game_state.players[author_id]

    if action == "call":
        to_call = game_state.current_bet - player['bet']
        if to_call > player['chips']:
            to_call = player['chips']
        player['chips'] -= to_call
        player['bet'] += to_call
        game_state.pot += to_call
        client.sendMessage(Message(text=f"✅ Người chơi {author_id} theo {format_money(to_call)}."),
                           thread_id=thread_id, thread_type=thread_type)
    elif action == "raise":
        if len(parts) != 4:
            client.sendMessage(Message(text="❌ Cú pháp: poker action raise <số tiền>"), thread_id=thread_id, thread_type=thread_type)
            return
        try:
            amount = int(parts[3])
            if amount < game_state.min_bet:
                client.sendMessage(Message(text=f"❌ Tố ít nhất {format_money(game_state.min_bet)}!"), thread_id=thread_id, thread_type=thread_type)
                return
            to_call = game_state.current_bet - player['bet'] + amount
            if to_call > player['chips']:
                client.sendMessage(Message(text="❌ Không đủ tiền để tố!"), thread_id=thread_id, thread_type=thread_type)
                return
            player['chips'] -= to_call
            player['bet'] += to_call
            game_state.pot += to_call
            game_state.current_bet = player['bet']
            client.sendMessage(Message(text=f"🔥 Người chơi {author_id} tố {format_money(amount)}!"),
                               thread_id=thread_id, thread_type=thread_type)
        except ValueError:
            client.sendMessage(Message(text="❌ Số tiền tố không hợp lệ."), thread_id=thread_id, thread_type=thread_type)
            return
    elif action == "fold":
        player['in_game'] = False
        client.sendMessage(Message(text=f"😔 Người chơi {author_id} bỏ bài."), thread_id=thread_id, thread_type=thread_type)
    else:
        client.sendMessage(Message(text="❌ Hành động không hợp lệ."), thread_id=thread_id, thread_type=thread_type)
        return

    # Cập nhật bàn bài
    table_path = draw_table(game_state)
    client.sendLocalImage(table_path, thread_id=thread_id, thread_type=thread_type, width=BOARD_SIZE[0], height=BOARD_SIZE[1],
                          message=Message(text="Bàn bài cập nhật:"))

    # Kiểm tra kết thúc vòng
    game_state.current_turn = (game_state.current_turn + 1) % len(game_state.turn_order)
    active_players = [pid for pid in game_state.players if game_state.players[pid]['in_game']]
    if game_state.current_turn == 0 or len(active_players) <= 1:
        if len(active_players) <= 1:
            if len(active_players) == 1:
                winner_id = active_players[0]
                game_state.players[winner_id]['chips'] += game_state.pot
                client.sendMessage(Message(text=f"🏆 Người chơi {winner_id} thắng {format_money(game_state.pot)} (duy nhất còn lại)!"),
                                   thread_id=thread_id, thread_type=thread_type)
                update_money_data(winner_id, game_state.players[winner_id]['chips'])
                game_state = None
            return
        game_state.next_round()
        if game_state.round == 'showdown':
            winner_id, hand = game_state.find_winner()
            game_state.players[winner_id]['chips'] += game_state.pot
            client.sendMessage(Message(text=f"🎴 Showdown! Người chơi {winner_id} thắng với {hand} ({format_money(game_state.pot)})!"),
                               thread_id=thread_id, thread_type=thread_type)
            update_money_data(winner_id, game_state.players[winner_id]['chips'])
            game_state = None
        else:
            table_path = draw_table(game_state)
            client.sendLocalImage(table_path, thread_id=thread_id, thread_type=thread_type, width=BOARD_SIZE[0], height=BOARD_SIZE[1],
                                  message=Message(text=f"🃏 Vòng mới: {game_state.round.upper()}"))

# -------------------------------
# Xử lý lệnh "poker status"
def handle_poker_status(message, message_object, thread_id, thread_type, author_id, client):
    global game_state
    if game_state is None:
        client.sendMessage(Message(text="❌ Trò chơi chưa khởi động. Gõ 'poker start <tiền cược>'!"),
                           thread_id=thread_id, thread_type=thread_type)
        return
    status_msg = f"📊 Trạng thái Xì Tố Nhóm:\n"
    status_msg += f"• Vòng: {game_state.round.upper()}\n"
    status_msg += f"• Pot: {format_money(game_state.pot)}\n"
    status_msg += f"• Lượt: Người chơi {game_state.turn_order[game_state.current_turn]}\n"
    status_msg += f"• Bài chung: {', '.join(f'{r}{s}' for r, s in game_state.community_cards) or 'Chưa lật'}\n"
    status_msg += "\nNgười chơi:\n"
    for i, pid in enumerate(game_state.players):
        player = game_state.players[pid]
        status = "Playing" if player['in_game'] else "Folded"
        status_msg += f"• Người {i+1} (ID {pid}): {format_money(player['chips'])} ({status})\n"
    client.sendMessage(Message(text=status_msg), thread_id=thread_id, thread_type=thread_type)

# -------------------------------
# Cập nhật ví tiền
def update_money_data(player_id, chips):
    money_data = load_money_data()
    money_data[player_id] = chips
    save_money_data(money_data)

# -------------------------------
# Xử lý lệnh chính
def handle_poker_command(message, message_object, thread_id, thread_type, author_id, client):
    text = message.split()
    if len(text) < 2:
        help_text = "\n".join(des['hướng dẫn sử dụng'])
        client.sendMessage(Message(text=f"🎴 HƯỚNG DẪN XÌ TỐ NHÓM:\n{help_text}"),
                           thread_id=thread_id, thread_type=thread_type)
        return
    if text[1] == "batdau":
        handle_poker_start(message, message_object, thread_id, thread_type, author_id, client)
    elif text[1] == "thamgia":
        handle_poker_join(message, message_object, thread_id, thread_type, author_id, client)
    elif text[1] == "cuoc":
        handle_poker_action(message, message_object, thread_id, thread_type, author_id, client)
    elif text[1] == "xem":
        handle_poker_status(message, message_object, thread_id, thread_type, author_id, client)
    else:
        client.sendMessage(Message(text="❌ Lệnh không hợp lệ. Dùng 'xito batdau', 'xito thamgia', 'xito cuoc', hoặc 'xito xem'."),
                           thread_id=thread_id, thread_type=thread_type)

# -------------------------------
# Mapping lệnh
def get_mitaizl():
    return {
        'xito': handle_poker_command
    }