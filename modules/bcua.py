import json
import random
import os
import time
import math
import threading
from PIL import Image
from zlapi.models import *
from config import PREFIX

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Module trò chơi Bầu Cua, cho phép người dùng đặt cược và theo dõi lịch sử chiến tích của mình.",
    'tính năng': [
        "🎲 Đặt cược vào các con vật: Bầu, Cua, Tôm, Cá, Nai, Gà",
        "💰 Hỗ trợ cược theo số tiền cụ thể, toàn bộ số dư hoặc phần trăm số dư",
        "🎯 Kết quả được quay ngẫu nhiên, hiển thị bằng GIF và ảnh",
        "📊 Quản lý số dư người chơi và lưu trữ dữ liệu vào JSON",
        "🎁 Nhận tiền miễn phí mỗi ngày để tiếp tục chơi",
        "🏆 Xem bảng xếp hạng người chơi giàu nhất",
        "🔧 Admin có thể chỉnh sửa số dư của người chơi",
        "📜 Xem lịch sử chiến tích tổng hợp (tổng trận, thắng, thua, tỉ lệ thắng, tiền thắng, tiền thua). Bạn có thể tag người dùng để xem lịch sử của họ."
    ],
    'hướng dẫn sử dụng': (
        "• Đặt cược: Dùng lệnh 'bcua' kèm theo tên con vật và số tiền cược. Ví dụ: 'bcua gà 10000' hoặc 'bcua cua 50%'.\n"
        "• Lấy tiền free: Soạn 'bc daily'.\n"
        "• Xem hướng dẫn: Soạn 'bc'.\n"
        "• Xem lịch sử chiến tích: Soạn 'bclichsu' hoặc 'bclichsu @userID' để xem lịch sử của người được tag."
    )
}

# --- Hằng số ---
GIF_FILE_PATH = "modules/cache/gif/gifbcmoi2.gif"  # GIF hiệu ứng
TTL = 60000
MONEY_DATA_FILE = "modules/cache/bc.json"
HISTORY_DATA_FILE = "modules/cache/bc_history.json"
ERROR_IMAGE_PATH = "modules/cache/images/cach-choi-bau-cua-luon-thang-khong-nam-vung-4-quy-luat-nay-ban-dung-mong-thang-cuoc_1716253305.jpg"

# Ảnh nền và thư mục ảnh xúc xắc
BACKGROUND_IMAGE_PATH = "modules/cache/images/bau_cua_bg.png"
DICE_IMAGES_DIR = "modules/cache/databcvip2"
MERGED_IMAGE_PATH = os.path.join(DICE_IMAGES_DIR, "merged_dice.png")

# Danh sách con vật
ANIMALS = ['bầu', 'cua', 'gà', 'cá', 'nai', 'tôm']

# --- Biến toàn cục cho chế độ round ---
ROUND_ACTIVE = False      
ROUND_BETS = {}           # { user_id: [(animal, bet_amount), ...], ... }
ROUND_THREAD_ID = None
ROUND_START_TIME = None

# Lock để đồng bộ khi truy cập các biến toàn cục
round_lock = threading.Lock()

# --- XỬ LÝ DỮ LIỆU ---
def load_money_data():
    try:
        with open(MONEY_DATA_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_money_data(data):
    with open(MONEY_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def load_history_data():
    try:
        with open(HISTORY_DATA_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_history_data(data):
    with open(HISTORY_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def format_money(amount):
    return f"{amount:,} VNĐ"

def get_user_name(client, user_id):
    try:
        user_info = client.fetchUserInfo(user_id)
        profile = user_info.changed_profiles.get(user_id, {})
        return profile.get('zaloName', 'Không xác định')
    except Exception:
        return 'Không xác định'

# --- GHÉP 3 ẢNH XÚC XẮC VÀO ẢNH NỀN ---
def place_3_dice_in_circle(bg_path, dice_paths, output_path,
                           circle_center=None, circle_radius=None,
                           dice_size=(150,150)):
    """
    Ghép 3 ảnh xúc xắc vào giữa ảnh nền (bg_path).
    Mỗi ảnh xúc xắc được đặt theo góc 0°, 120°, 240° để tạo hình tam giác.
    """
    if not os.path.exists(bg_path):
        print(f"Không tìm thấy ảnh nền: {bg_path}")
        return
    bg = Image.open(bg_path).convert("RGBA")
    bg_w, bg_h = bg.size

    if circle_center is None:
        cx, cy = bg_w // 2, bg_h // 2
    else:
        cx, cy = circle_center

    if circle_radius is None:
        circle_radius = min(bg_w, bg_h) // 4

    dice_imgs = []
    for path in dice_paths:
        if not os.path.exists(path):
            print(f"Không tìm thấy file ảnh xúc xắc: {path}")
            return
        dice = Image.open(path).convert("RGBA")
        dice = dice.resize(dice_size, Image.LANCZOS)
        dice_imgs.append(dice)

    angles_deg = [0, 120, 240]
    bg_editable = bg.copy()

    for i, angle_deg in enumerate(angles_deg):
        angle_rad = math.radians(angle_deg)
        r = circle_radius * 0.6
        dx = r * math.cos(angle_rad)
        dy = r * math.sin(angle_rad)

        dice_cx = cx + dx
        dice_cy = cy + dy

        w, h = dice_imgs[i].size
        paste_x = int(dice_cx - w/2)
        paste_y = int(dice_cy - h/2)

        bg_editable.paste(dice_imgs[i], (paste_x, paste_y), dice_imgs[i])

    bg_editable.save(output_path, format="PNG")

# --- BẮT ĐẦU VÒNG (30 GIÂY) ---
def handle_round_start(message, message_object, thread_id, thread_type, author_id, client):
    global ROUND_ACTIVE, ROUND_BETS, ROUND_THREAD_ID, ROUND_START_TIME
    with round_lock:
        if ROUND_ACTIVE:
            client.replyMessage(
                Message(text="❌ Đang có vòng chơi diễn ra. Vui lòng đợi kết thúc!"),
                message_object,
                thread_id,
                thread_type,
                ttl=TTL
            )
            return
        ROUND_ACTIVE = True
        ROUND_THREAD_ID = thread_id
        ROUND_BETS = {}
        ROUND_START_TIME = time.time()

    start_msg = (
        "✅ ĐÃ BẮT ĐẦU CHẾ ĐỘ CHƠI THEO VÒNG!\n"
        "Bạn có 30 giây để đặt cược (dùng lệnh bcua...).\n"
        "Sau 30 giây, hệ thống sẽ đóng cược và xử lý kết quả!"
    )
    client.sendLocalImage(
        imagePath=ERROR_IMAGE_PATH,
        message=Message(text=start_msg),
        thread_id=thread_id,
        thread_type=thread_type,
        width=921,
        height=600,
        ttl=TTL
    )

    # Sử dụng threading.Timer để không chặn luồng chính
    timer = threading.Timer(30, finalize_round, args=(message_object, thread_id, thread_type, client))
    timer.start()

# --- KẾT THÚC VÒNG, TÍNH TIỀN THEO LOGIC GIỐNG IMMEDIATE ---
def finalize_round(message_object, thread_id, thread_type, client):
    global ROUND_ACTIVE, ROUND_BETS, ROUND_THREAD_ID
    with round_lock:
        if not ROUND_ACTIVE:
            return
        # Quay xúc xắc 1 lần
        dice_values = [random.choice(ANIMALS) for _ in range(3)]
        # Đánh thông báo hết giờ
        client.sendMessage(Message(text=f"❗❗❗ Hết giờ .... ❗❗❗ Thả tay ra ...."), thread_id=thread_id, thread_type=thread_type, ttl=8000)
    
    # Tạm dừng 3 giây để tạo hiệu ứng
    time.sleep(3)

    money_data = load_money_data()
    history_data = load_history_data()

    summary_lines = []
    summary_lines.append("🎲 KẾT QUẢ VÒNG CHƠI BẦU Cua:")
    summary_lines.append(f"3 MẶT RA: {dice_values[0]} - {dice_values[1]} - {dice_values[2]}")
    summary_lines.append("─────────────────────")

    # Gửi GIF hiệu ứng
    client.sendLocalGif(
        GIF_FILE_PATH,
        message_object,
        thread_id,
        thread_type,
        width=624,
        height=208,
        ttl=5000
    )
    time.sleep(6)

    # Xử lý cho từng người chơi
    for user_id, bets_list in ROUND_BETS.items():
        old_balance = money_data.get(str(user_id), 0)
        total_bet = sum(bet_amount for (_, bet_amount) in bets_list)

        if total_bet > old_balance:
            summary_lines.append(f"👤 {get_user_name(client, user_id)}: ❌ Tổng cược {format_money(total_bet)} vượt số dư {format_money(old_balance)}. (Bỏ qua)")
            summary_lines.append("─────────────────────")
            continue

        net_change = 0
        user_outcome = []
        for (animal, bet_amount) in bets_list:
            count = dice_values.count(animal)
            if count > 0:
                win_amount = bet_amount * count
                net_change += win_amount
                user_outcome.append(f"+ {format_money(win_amount)} ✅ trúng {animal} x{count}")
            else:
                net_change -= bet_amount
                user_outcome.append(f"- {format_money(bet_amount)} ❌ trượt {animal}")

        new_balance = old_balance + net_change
        money_data[str(user_id)] = new_balance

        if new_balance >= 100_000_000_000:
            rank_title = "👑 Hoàng đế Bầu Cua"
        elif new_balance >= 50_000_000_000:
            rank_title = "💎 Tỷ phú Bầu Cua"
        elif new_balance >= 10_000_000_000:
            rank_title = "🤑 Triệu phú Bầu Cua"
        elif new_balance >= 5_000_000_000:
            rank_title = "🔥 Cao thủ Bầu cua"
        elif new_balance >= 1_000_000_000:
            rank_title = "🎲 Trùm Bầu Cua"
        elif new_balance >= 500_000_000:
            rank_title = "🤞 Chuyên gia Bầu Cua"
        elif new_balance >= 100_000_000:
            rank_title = "💵 Dân chơi Bầu Cua"
        elif new_balance >= 50_000_000:
            rank_title = "😎 Gà may mắn"
        elif new_balance >= 10_000_000:
            rank_title = "🥲 Học viên Bầu Cua"
        elif new_balance >= 1_000_000:
            rank_title = "🍂 Con Nợ Bầu Cua"
        else:
            rank_title = "🆕 Con nợ Bầu Cua"

        username = get_user_name(client, user_id)
        record = {
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())),
            'bets': bets_list,
            'dice': dice_values,
            'net_change': net_change,
            'new_balance': new_balance,
            'rank_title': rank_title
        }
        history_data.setdefault(username, []).append(record)

        net_change_str = f"+{format_money(net_change)}" if net_change >= 0 else f"{format_money(net_change)}"
        summary_lines.append(f"👤 {username} \n🏆 Danh hiệu: {rank_title}")
        summary_lines.append("  " + "\n  ".join(user_outcome))
        summary_lines.append(f"▶ Biến động: {net_change_str}\n💰 Số dư cuối : {format_money(new_balance)}")
        summary_lines.append("─────────────────────")

    save_money_data(money_data)
    save_history_data(history_data)

    final_text = "\n".join(summary_lines)
    msg = Message(text=final_text)

    image_paths = [os.path.join(DICE_IMAGES_DIR, f"{value}.png") for value in dice_values]
    if all(os.path.exists(path) for path in image_paths):
        place_3_dice_in_circle(
            bg_path=BACKGROUND_IMAGE_PATH,
            dice_paths=image_paths,
            output_path=MERGED_IMAGE_PATH,
            dice_size=(150,150)
        )
        if os.path.exists(MERGED_IMAGE_PATH):
            client.sendLocalImage(
                imagePath=MERGED_IMAGE_PATH,
                message=msg,
                thread_id=thread_id,
                thread_type=thread_type,
                width=1000,
                height=600,
                ttl=TTL
            )
            os.remove(MERGED_IMAGE_PATH)
        else:
            client.replyMessage(
                msg,
                message_object,
                thread_id,
                thread_type,
                ttl=TTL
            )
    else:
        client.replyMessage(
            msg,
            message_object,
            thread_id,
            thread_type,
            ttl=TTL
        )

    with round_lock:
        ROUND_ACTIVE = False
        ROUND_BETS = {}
        ROUND_THREAD_ID = None

# --- LỆNH bcua ---
def handle_baocua_command(message, message_object, thread_id, thread_type, author_id, client):
    global ROUND_ACTIVE, ROUND_BETS, ROUND_THREAD_ID, ROUND_START_TIME

    parts = message.split()
    if not parts:
        return
    command = parts[0].lower()
    if command == "bcbatdau":
        handle_round_start(message, message_object, thread_id, thread_type, author_id, client)
        return

    if command == "bcua":
        with round_lock:
            if ROUND_ACTIVE and (thread_id == ROUND_THREAD_ID):
                if len(parts) < 3 or (len(parts) - 1) % 2 != 0:
                    instructions = (
                        "🎲 Cú pháp: bcua [con vật] [tiền/all/%], ...\n"
                        "Ví dụ: bcua gà 10000"
                    )
                    client.replyMessage(
                        Message(text=instructions),
                        message_object,
                        thread_id,
                        thread_type,
                        ttl=TTL
                    )
                    return
                # Trước khi xử lý các cược, tải số dư của người chơi
                money_data = load_money_data()
                old_balance = money_data.get(str(author_id), 0)

                bets = []
                for i in range(1, len(parts), 2):
                    animal = parts[i].lower()
                    if animal not in ANIMALS:
                        client.replyMessage(
                            Message(text=f"❌ '{animal}' không hợp lệ!"),
                            message_object,
                            thread_id,
                            thread_type,
                            ttl=TTL
                        )
                        return

                    bet_str = parts[i+1].lower()
                    bet_amount = 0
                    if bet_str == "all":
                        bet_amount = old_balance
                    elif bet_str.endswith('%'):
                        try:
                            percent = float(bet_str[:-1])
                            if not (1 <= percent <= 100):
                                client.replyMessage(
                                    Message(text="❌ Phần trăm phải từ 1% đến 100%."),
                                    message_object,
                                    thread_id,
                                    thread_type,
                                    ttl=TTL
                                )
                                return
                            bet_amount = int(old_balance * (percent / 100))
                        except ValueError:
                            client.replyMessage(
                                Message(text="❌ Phần trăm không hợp lệ."),
                                message_object,
                                thread_id,
                                thread_type,
                                ttl=TTL
                            )
                            return
                    else:
                        try:
                            bet_amount = int(bet_str)
                        except ValueError:
                            client.replyMessage(
                                Message(text="❌ Số tiền không hợp lệ!"),
                                message_object,
                                thread_id,
                                thread_type,
                                ttl=TTL
                            )
                            return

                    bets.append((animal, bet_amount))

                if author_id not in ROUND_BETS:
                    ROUND_BETS[author_id] = []
                ROUND_BETS[author_id].extend(bets)
                total_bet = sum(bet for (_, bet) in ROUND_BETS.get(author_id, []))
                
                username = get_user_name(client, author_id)
                bet_str_formatted = format_money(total_bet)
                time_passed = time.time() - ROUND_START_TIME
                time_left = 30 - int(time_passed)
                if time_left < 0:
                    time_left = 0

                client.replyMessage(
                    Message(text=f"✅ {username} đã đặt cược thành công \n Tổng cược :{bet_str_formatted}\n  Còn {time_left} giây nữa nhà cái sẽ chốt cược  ..."),
                    message_object,
                    thread_id,
                    thread_type,
                    ttl=TTL
                )
                return
            else:
                handle_baocua_immediate(message, message_object, thread_id, thread_type, author_id, client)
                return

    return

# --- LỆNH chơi ngay ---
def handle_baocua_immediate(message, message_object, thread_id, thread_type, author_id, client):
    parts = message.split()
    if len(parts) < 3 or (len(parts) - 1) % 2 != 0:
        instructions = (
            "🎲 HƯỚNG DẪN CHƠI BẦU Cua\n"
            "────────────────────────\n"
            "💰 bc daily: Nhận tiền miễn phí để chơi.\n"
            "────────────────────────\n"
            "🎯 Đặt cược theo mẫu:\n"
            "   bcua [con vật] [số tiền/all/% số tiền]  {có thể lặp nhiều lần}\n"
            "    Ví dụ:\n"
            "      • bcua gà 10000\n"
            "      • bcua cua 10%\n"
            "      • bcua tôm 5000\n"
            "────────────────────────\n"
            "📜 bclichsu: Xem lịch sử chiến tích của bạn hoặc tag người dùng khác\n"
            "📌 bc: Xem các tiện ích đi kèm.\n"
        )
        if os.path.exists(ERROR_IMAGE_PATH):
            client.sendLocalImage(
                imagePath=ERROR_IMAGE_PATH,
                message=Message(text=instructions),
                thread_id=thread_id,
                thread_type=thread_type,
                width=921,
                height=600,
                ttl=TTL
            )
        else:
            instructions += "\n❌ Không thể hiển thị hình ảnh hướng dẫn do thiếu file."
            client.replyMessage(
                Message(text=instructions),
                message_object,
                thread_id,
                thread_type,
                ttl=TTL
            )
        return

    money_data = load_money_data()
    old_balance = money_data.get(str(author_id), 0)

    bets = []
    total_bet = 0
    all_used = False
    for i in range(1, len(parts), 2):
        animal = parts[i].lower()
        if animal not in ANIMALS:
            response_message = f"❌ '{animal}' không phải là con vật hợp lệ."
            client.replyMessage(
                Message(text=response_message),
                message_object,
                thread_id,
                thread_type,
                ttl=TTL
            )
            return

        bet_str = parts[i+1].lower()
        bet_amount = 0
        if bet_str == "all":
            if all_used or (len(parts) > 3):
                response_message = "❌ Lệnh cược all chỉ được sử dụng cho một con vật duy nhất."
                client.replyMessage(
                    Message(text=response_message),
                    message_object,
                    thread_id,
                    thread_type,
                    ttl=TTL
                )
                return
            else:
                bet_amount = old_balance
                all_used = True
        elif bet_str.endswith('%'):
            try:
                percent = float(bet_str[:-1])
                if not (1 <= percent <= 100):
                    response_message = "❌ Phần trăm phải từ 1% đến 100%."
                    client.replyMessage(
                        Message(text=response_message),
                        message_object,
                        thread_id,
                        thread_type,
                        ttl=TTL
                    )
                    return
                bet_amount = int(old_balance * (percent / 100))
            except ValueError:
                response_message = "❌ Phần trăm không hợp lệ."
                client.replyMessage(
                    Message(text=response_message),
                    message_object,
                    thread_id,
                    thread_type,
                    ttl=TTL
                )
                return
        else:
            try:
                bet_amount = int(bet_str)
            except ValueError:
                response_message = "❌ Số tiền không hợp lệ."
                client.replyMessage(
                    Message(text=response_message),
                    message_object,
                    thread_id,
                    thread_type,
                    ttl=TTL
                )
                return

        bets.append((animal, bet_amount))
        total_bet += bet_amount

    if total_bet > old_balance:
        response_message = f"❌ Bạn không đủ tiền (cần {format_money(total_bet)})!"
        client.replyMessage(
            Message(text=response_message),
            message_object,
            thread_id,
            thread_type,
            ttl=TTL
        )
        return

    if total_bet <= 0:
        response_message = (
            "❌ Số tiền cược phải lớn hơn 0.\n"
            "────────────────────────\n"
            "⚠ Không nhập dấu phẩy trong số tiền.\n"
            "⚠ Nếu hết tiền, hãy nhập 'bc daily' để nhận tiền free."
        )
        client.replyMessage(
            Message(text=response_message),
            message_object,
            thread_id,
            thread_type,
            ttl=TTL
        )
        return

    dice_values = [random.choice(ANIMALS) for _ in range(3)]
    net_change = 0
    outcome_messages = []
    for animal, bet_amount in bets:
        count = dice_values.count(animal)
        if count > 0:
            win_amount = bet_amount * count
            net_change += win_amount
            outcome_messages.append(f"✅ Có {count} con {animal.capitalize()} + {format_money(win_amount)}.")
        else:
            net_change -= bet_amount
            outcome_messages.append(f"⛔ Không có {animal.capitalize()} - {format_money(bet_amount)}.")

    new_balance = old_balance + net_change
    money_data[str(author_id)] = new_balance
    save_money_data(money_data)

    client.sendLocalGif(
        GIF_FILE_PATH,
        message_object,
        thread_id,
        thread_type,
        width=624,
        height=208,
        ttl=5000
    )
    time.sleep(6)

    if new_balance >= 100_000_000_000:
        rank_title = "👑 Hoàng đế Bầu Cua"
    elif new_balance >= 50_000_000_000:
        rank_title = "💎 Tỷ phú Bầu Cua"
    elif new_balance >= 10_000_000_000:
        rank_title = "🤑 Triệu phú Bầu Cua"
    elif new_balance >= 5_000_000_000:
        rank_title = "🔥 Cao thủ Bầu cua"
    elif new_balance >= 1_000_000_000:
        rank_title = "🎲 Trùm Bầu Cua"
    elif new_balance >= 500_000_000:
        rank_title = "🤞 Chuyên gia Bầu Cua"
    elif new_balance >= 100_000_000:
        rank_title = "💵 Dân chơi Bầu Cua"
    elif new_balance >= 50_000_000:
        rank_title = "😎 Gà may mắn"
    elif new_balance >= 10_000_000:
        rank_title = "🥲 Học viên Bầu Cua"
    elif new_balance >= 1_000_000:
        rank_title = "🍂 Con Nợ Bầu Cua"
    else:
        rank_title = "🆕 Con nợ Bầu Cua"

    net_change_str = f"+{format_money(net_change)}" if net_change >= 0 else f"{format_money(net_change)}"
    author_name = get_user_name(client, author_id)

    outcome_text = "\n".join(outcome_messages)
    final_message = (
        f"👤 Người chơi: {author_name}\n"
        f"🏆 Danh hiệu: {rank_title}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💸 Tổng cược: {format_money(total_bet)}\n"
        f"🎲 Khui : {dice_values[0]} - {dice_values[1]} - {dice_values[2]}\n"
        f"{outcome_text}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔄 Biến động số dư: {net_change_str}\n"
        f"💰 Số dư ví hiện tại:\n"
        f"💵 {format_money(new_balance)}\n"
        f"━━━━━━━━━━━━━━━━━━"
    )
    gui = Message(text=final_message)

    history_data = load_history_data()
    username = get_user_name(client, author_id)
    record = {
        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())),
        'bets': bets,
        'dice': dice_values,
        'net_change': net_change,
        'new_balance': new_balance,
        'rank_title': rank_title
    }
    history_data.setdefault(username, []).append(record)
    save_history_data(history_data)

    image_paths = [os.path.join(DICE_IMAGES_DIR, f"{value}.png") for value in dice_values]
    if all(os.path.exists(path) for path in image_paths):
        place_3_dice_in_circle(
            bg_path=BACKGROUND_IMAGE_PATH,
            dice_paths=image_paths,
            output_path=MERGED_IMAGE_PATH,
            dice_size=(150,150)
        )
        if os.path.exists(MERGED_IMAGE_PATH):
            client.sendLocalImage(
                imagePath=MERGED_IMAGE_PATH,
                message=gui,
                thread_id=thread_id,
                thread_type=thread_type,
                width=1000,
                height=600,
                ttl=TTL
            )
            os.remove(MERGED_IMAGE_PATH)
        else:
            error_msg = final_message + "\n❌ Không tìm thấy file ảnh kết quả sau khi ghép."
            client.replyMessage(
                Message(text=error_msg),
                message_object,
                thread_id,
                thread_type,
                ttl=60000
            )
    else:
        error_msg = final_message + "\n❌ Không thể hiển thị hình ảnh kết quả do thiếu hình ảnh con vật."
        client.replyMessage(
            Message(text=error_msg),
            message_object,
            thread_id,
            thread_type,
            ttl=60000
        )

# --- LỊCH SỬ CHIẾN TÍCH ---
def handle_history_command(message, message_object, thread_id, thread_type, author_id, client):
    parts = message.split()
    if len(parts) >= 2:
        potential_username = ' '.join(parts[1:]).strip()
        if potential_username.startswith('@'):
            potential_username = potential_username[1:]
        target_username = potential_username
    else:
        target_username = get_user_name(client, author_id)
    
    history_data = load_history_data()
    user_history = history_data.get(target_username, [])
    
    if not user_history:
        response_message = f"❌ Người dùng '{target_username}' chưa có lịch sử chiến tích nào."
        client.replyMessage(
            Message(text=response_message),
            message_object,
            thread_id,
            thread_type,
            ttl=TTL
        )
        return

    total_games = len(user_history)
    wins = sum(1 for record in user_history if record.get('net_change', 0) > 0)
    losses = sum(1 for record in user_history if record.get('net_change', 0) < 0)
    win_rate = (wins / total_games) * 100 if total_games > 0 else 0
    money_won = sum(record.get('net_change', 0) for record in user_history if record.get('net_change', 0) > 0)
    money_lost = sum(-record.get('net_change', 0) for record in user_history if record.get('net_change', 0) < 0)
    
    final_history = (
        f"📜 LỊCH SỬ CHIẾN TÍCH :\n"
        f" - {target_username}:\n"
        f" - GAME BẦU Cua \n"
        f"────────────────────────\n"
        f"🔸 Tổng trận: {total_games}\n"
        f"🔸 Trận thắng: {wins}\n"
        f"🔸 Trận thua: {losses}\n"
        f"🔸 Tỉ lệ thắng: {win_rate:.2f}%\n"
        f"🔸 Tổng tiền thắng: {format_money(money_won)}\n"
        f"🔸 Tổng tiền thua: {format_money(money_lost)}\n"
        f"────────────────────────"
    )
    
    client.replyMessage(
        Message(text=final_history),
        message_object,
        thread_id,
        thread_type,
        ttl=TTL
    )

# --- TRẢ VỀ DICT LỆNH ---
def get_mitaizl():
    """
    Lệnh:
      - bcbatdau: Bắt đầu vòng 30 giây
      - bcua: nếu đang vòng => lưu, nếu không => chơi ngay
      - bclichsu: xem lịch sử
    """
    return {
        'bcua': handle_baocua_command,
        'bclichsu': handle_history_command,
        'bcbatdau': handle_round_start
    }
