import json
import random
import time
import os
from zlapi.models import Message
from config import ADMIN
from config import PREFIX

# Thông tin mô tả module
des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Module quản lý tiền trong bot, hỗ trợ giao dịch và xếp hạng.",
    'tính năng': [
        "📌 Chuyển tiền giữa người dùng",
        "💰 Kiểm tra số dư cá nhân hoặc người khác",
        "🏆 Xem bảng xếp hạng người giàu nhất",
        "🎁 Nhận tiền miễn phí mỗi ngày",
        "➕ Thêm tiền cho bản thân",
        "🔧 Admin có thể thêm, xóa tiền của người khác",
        "🔄 Admin có thể reset toàn bộ số dư hệ thống"
    ],
    'hướng dẫn sử dụng': [
        "📩 Dùng lệnh 'bc' kèm theo các tùy chọn như 'pay', 'check', 'top', 'daily', 'add', 'set', 'del', 'rs'.",
        "📌 Nhập 'menubc' để xem hướng dẫn chi tiết.",
        "✅ Nhận thông báo trạng thái và kết quả ngay lập tức."
    ]
}

# Biến lưu cooldown của người dùng
user_cooldowns = {}

# Kiểm tra xem người dùng có phải admin hay không
def is_admin(author_id):
    return author_id in ADMIN

# Tải dữ liệu tiền từ file
def load_money_data():
    try:
        with open('modules/cache/bc.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Lưu dữ liệu tiền vào file
def save_money_data(data):
    with open('modules/cache/bc.json', 'w') as f:
        json.dump(data, f, indent=4)

# Định dạng số tiền
def format_money(amount):
    return f"{amount:,} VNĐ"

# Lấy tên người dùng từ client
def get_user_name(client, user_id):
    try:
        user_info = client.fetchUserInfo(user_id)
        profile = user_info.changed_profiles.get(user_id, {})
        return profile.get('zaloName', 'Không xác định')
    except AttributeError:
        return 'Không xác định'

# Hiển thị menu lệnh
def show_money_menu(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản ứng ngay khi người dùng soạn đúng lệnh
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    response_message = (
    "🦀 𝑻𝑰𝑬̣̂𝑵 𝑰́𝑪𝑯 𝑮𝑨𝑴𝑬 𝑩𝑨̂̀𝑼 𝑪𝑼𝑨 🎲\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "💸 𝗯𝗰 𝗽𝗮𝘆    →  Chuyển tiền cho người khác\n"
    "💰 𝗯𝗰 𝗰𝗵𝗲𝗰𝗸  →  Kiểm tra số dư của bạn hoặc người khác\n"
    "🏆 𝗯𝗰 𝘁𝗼𝗽    →  Xem bảng xếp hạng người giàu nhất\n"
    "🎁 𝗯𝗰 𝗱𝗮𝗶𝗹𝘆  →  Nhận tiền miễn phí mỗi ngày\n"
    "➕ 𝗯𝗰 𝗮𝗱𝗱    →  Thêm tiền cho bản thân\n"
    "🔧 𝗯𝗰 𝘀𝗲𝘁    →  Thêm tiền cho người khác (Admin)\n"
    "❌ 𝗯𝗰 𝗱𝗲𝗹    →  Trừ tiền của người khác (Admin)\n"
    "🔄 𝗯𝗰 𝗿𝘀     →  Reset số dư toàn hệ thống (Admin)\n"
    "━━━━━━━━━━━━━━━━━━━━━━"
)

    client.replyMessage(Message(text=response_message), message_object, thread_id, thread_type, ttl=20000)

# Xử lý các lệnh liên quan đến tiền
def handle_money_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản ứng ngay khi người dùng soạn đúng lệnh
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    text = message.split()
    money_data = load_money_data()

    if len(text) < 2:
        show_money_menu(message, message_object, thread_id, thread_type, author_id, client)
        return

    response_message = ""

    if text[1] == "set" and is_admin(author_id):
        if len(text) < 3 or not text[2].isdigit() or len(message_object.mentions) < 1:
            response_message = "❌ Vui lòng nhập số hợp lệ và tag người nhận."
        else:
            amount = int(text[2])
            target_id = message_object.mentions[0]['uid']
            target_name = get_user_name(client, target_id)
            money_data[target_id] = money_data.get(target_id, 0) + amount
            save_money_data(money_data)
            response_message = f"✅ Đã cộng 💵 {format_money(amount)} cho 👨‍💼 {target_name}."

    elif text[1] == "add" and is_admin(author_id):
        if len(text) < 3 or not text[2].isdigit():
            response_message = "❌ Vui lòng nhập số hợp lệ."
        else:
            amount = int(text[2])
            money_data[author_id] = money_data.get(author_id, 0) + amount
            save_money_data(money_data)
            response_message = f"✅ Đã tự động cộng thêm 💵 {format_money(amount)} cho bản thân."

    elif text[1] == "rs" and is_admin(author_id):
        for user_id in money_data:
            money_data[user_id] = 0  # Đặt số tiền của tất cả người dùng về 0
        save_money_data(money_data)
        response_message = "✅ Đã reset toàn bộ số dư hệ thống về 0."

    elif text[1] == "del" and is_admin(author_id):
        if len(text) < 3:
            response_message = "❌ Vui lòng chỉ định số tiền hoặc 'all'."
        else:
            target_id = message_object.mentions[0]['uid'] if len(message_object.mentions) > 0 else author_id
            target_name = get_user_name(client, target_id)

            if text[2] == "all":
                money_data[target_id] = 0
                response_message = f"✅ Đã trừ thành công toàn bộ tiền của {target_name}."
            elif text[2].isdigit():
                amount = int(text[2])
                money_data[target_id] = max(0, money_data.get(target_id, 0) - amount)
                response_message = f"✅ Đã trừ {format_money(amount)} của {target_name}."
            else:
                response_message = "❌ Vui lòng nhập số hợp lệ."

            save_money_data(money_data)

    elif text[1] == "daily":
        current_time = time.time()
        cooldown_time = 180

        if author_id in user_cooldowns:
            time_since_last_use = current_time - user_cooldowns[author_id]
            if time_since_last_use < cooldown_time:
                remaining_time = cooldown_time - time_since_last_use
                error_message = Message(text=f"Bạn phải đợi {int(remaining_time // 60)} phút {int(remaining_time % 60)} giây nữa mới có thể nhận tiền free.")
                client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=10000)
                return

        amount = random.randint(1, 1000000000)
        money_data[author_id] = money_data.get(author_id, 0) + amount
        user_cooldowns[author_id] = current_time
        save_money_data(money_data)
        response_message = f"✅ Bạn vừa ăn cắp của mẹ bạn \n 💵 {format_money(amount)}\n để chơi game Bầu Cua "

    elif text[1] == "pay":
        if len(text) < 3 or not text[2].isdigit() or len(message_object.mentions) < 1:
            response_message = "❌ Vui lòng nhập số hợp lệ và tag người nhận."
        else:
            amount = int(text[2])
            target_id = message_object.mentions[0]['uid']
            target_name = get_user_name(client, target_id)

            if money_data.get(author_id, 0) >= amount:
                money_data[author_id] -= amount
                money_data[target_id] = money_data.get(target_id, 0) + amount
                save_money_data(money_data)
                response_message = f"✅ Chuyển thành công\n💵 {format_money(amount)} đến 👨‍💼 {target_name}."
            else:
                response_message = "❌ Số dư không đủ để thực hiện giao dịch."

    elif text[1] == "top":
        top_users = sorted(money_data.items(), key=lambda x: x[1], reverse=True)[:10]
        response_message = "🌟   𝐁𝐀̉𝐍𝐆 𝐗𝐄̂́𝐏 𝐇𝐀̣𝐍𝐆 𝐁𝐀̂̀𝐔 𝐂𝐔𝐀 \n"
    
        for idx, (uid, amount) in enumerate(top_users, 1):
            name = get_user_name(client, uid)
            
            # Xác định danh hiệu dựa trên số tiền
            if amount >= 100_000_000_000:
                rank_title = "👑 Hoàng đế Bầu Cua"         # Từ 100 tỷ trở lên
            elif amount >= 50_000_000_000:
                rank_title = "💎 Tỷ phú Bầu Cua"           # Từ 50 tỷ đến dưới 100 tỷ
            elif amount >= 10_000_000_000:
                rank_title = "🤑 Triệu phú Bầu Cua"         # Từ 10 tỷ đến dưới 50 tỷ
            elif amount >= 5_000_000_000:
                rank_title = "🔥 Cao thủ Bầu cua"              # Từ 5 tỷ đến dưới 10 tỷ
            elif amount >= 1_000_000_000:
                rank_title = "🎲 Trùm Bầu Cua"           # Từ 1 tỷ đến dưới 5 tỷ
            elif amount >= 500_000_000:
                rank_title = "🤞 Chuyên gia Bầu Cua"               # Từ 500 triệu đến dưới 1 tỷ
            elif amount >= 100_000_000:
                rank_title = "💵 Dân chơi Bầu Cua"       # Từ 100 triệu đến dưới 500 triệu
            elif amount >= 50_000_000:
                rank_title = "😎  Gà may mắn"         # Từ 50 triệu đến dưới 100 triệu
            elif amount >= 10_000_000:
                rank_title = "🆕 Học viên Bầu Cua"         # Từ 10 triệu đến dưới 50 triệu
            elif amount >= 1_000_000:
                rank_title = "🍂 Con Nợ Bầu Cua"           # Từ 1 triệu đến dưới 10 triệu
            else:
                rank_title = "🆕 Con Nợ Bầu Cua"        # Dưới 1 triệu

    
            response_message += (
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🏆 𝗧𝗼𝗽 {idx} : {rank_title}\n"
                f"👤 𝐓𝐞̂𝐧:      {name}\n"
                f"💰 𝐓𝐢𝐞̂̀𝐧:     {format_money(amount)}\n"
                f"━━━━━━━━━━━━━━━━━━━\n\n"
            )
    
        client.replyMessage(Message(text=response_message), message_object, thread_id, thread_type, ttl=20000)
        return

    elif text[1] == "check":
        if message_object.mentions:
            target_id = message_object.mentions[0]['uid']
            target_name = get_user_name(client, target_id)
            balance = money_data.get(target_id, 0)
            response_message = f"✅ {target_name} hiện có:\n💵 {format_money(balance)}."
        else:
            balance = money_data.get(author_id, 0)
            response_message = f"✅ Số tiền của bạn hiện có:\n💵 {format_money(balance)}."

    else:
        response_message = "❌ Lệnh không hợp lệ hoặc bạn không có quyền sử dụng lệnh này."

    client.replyMessage(Message(text=response_message), message_object, thread_id, thread_type, ttl=20000)

# Cấu hình các lệnh của bot
def get_mitaizl():
    return {
        'bc': handle_money_command,
        'menubc': show_money_menu
    }
