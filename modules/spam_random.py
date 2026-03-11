from zlapi.models import Message, Mention, MultiMsgStyle, MessageStyle, MultiMention
from config import ADMIN
import time
import random
import threading
import json
from zlapi import ZaloAPIException

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Spam hỗn loạn với tag nhiều người dùng ngẫu nhiên, tag tất cả, câu chửi, và sticker.",
    'tính năng': [
        "📢 Tag nhiều người dùng ngẫu nhiên trong một tin nhắn (@user1 @user2 ...) với câu chửi từ file 5c.txt.",
        "🔗 Tag tất cả thành viên trong nhóm với câu chửi ngẫu nhiên.",  # Tính năng mới
        "🎯 Tag một người dùng ngẫu nhiên trong nhóm với câu chửi.",
        "📨 Gửi sticker ngẫu nhiên từ danh sách định sẵn.",
        "🤬 Kết hợp chửi và gửi sticker trong một lần gửi.",
        "📝 Gửi 2-3 câu chửi ngẫu nhiên liên tiếp.",
        "🛑 Hỗ trợ lệnh stop để dừng spam.",
        "⏳ Tùy chỉnh thời gian delay (ví dụ: spamsos -3 để delay 3 giây).",
        "🔒 Chỉ admin được phép sử dụng lệnh."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh: spamsos -<số giây> để bắt đầu spam hỗn loạn (ví dụ: spamsos -3).",
        "📩 Gửi lệnh: spamsos stop để dừng spam.",
        "🔐 Yêu cầu: Người dùng phải là admin (có ID trong ADMIN).",
        "✅ Nhận thông báo trạng thái khi bắt đầu/dừng spam."
    ]
}

# Danh sách sticker
stickers = [
    {"sticker_type": 3, "sticker_id": "23339", "category_id": "10425"},
    {"sticker_type": 3, "sticker_id": "23340", "category_id": "10425"},
    {"sticker_type": 3, "sticker_id": "23341", "category_id": "10425"},
    {"sticker_type": 3, "sticker_id": "23342", "category_id": "10425"},
    {"sticker_type": 3, "sticker_id": "23343", "category_id": "10425"},
    {"sticker_type": 3, "sticker_id": "23344", "category_id": "10425"},
    {"sticker_type": 3, "sticker_id": "23345", "category_id": "10425"},
    {"sticker_type": 3, "sticker_id": "23346", "category_id": "10425"},
    {"sticker_type": 3, "sticker_id": "23347", "category_id": "10425"},
    {"sticker_type": 3, "sticker_id": "23348", "category_id": "10425"},
    {"sticker_type": 3, "sticker_id": "23349", "category_id": "10425"},
    {"sticker_type": 3, "sticker_id": "23350", "category_id": "10425"},
    {"sticker_type": 3, "sticker_id": "23311", "category_id": "10425"},
]

# Biến toàn cục để kiểm soát trạng thái spam
is_spamming = False
MAX_RUNTIME = 300  # Thời gian tối đa 5 phút

def send_message_with_style(client, text, thread_id, thread_type, color="#db342e"):
    """Gửi tin nhắn có định dạng màu sắc."""
    base_length = len(text)
    adjusted_length = base_length + 355
    style = MultiMsgStyle([
        MessageStyle(offset=0, length=adjusted_length, style="color", color=color, auto_format=False),
        MessageStyle(offset=0, length=adjusted_length, style="bold", size="8", auto_format=False)
    ])
    client.send(Message(text=text, style=style), thread_id=thread_id, thread_type=thread_type, ttl=10000)

def handle_spamsos_command(message, message_object, thread_id, thread_type, author_id, client):
    global is_spamming

    # Kiểm tra quyền admin
    if author_id not in ADMIN:
        send_message_with_style(client, "⭕ Bạn không có quyền thực hiện lệnh này!", thread_id, thread_type)
        return

    # Xử lý lệnh stop
    command_parts = message.split()
    if len(command_parts) > 1 and command_parts[1].lower() == "stop":
        if not is_spamming:
            send_message_with_style(client, "⚠️ Không có quá trình spam nào đang chạy!", thread_id, thread_type)
        else:
            is_spamming = False
            send_message_with_style(client, "🛑 Đã dừng spam hỗn loạn!", thread_id, thread_type)
        return

    # Lấy giá trị delay từ lệnh
    delay = 3  # Mặc định 3 giây
    if len(command_parts) > 1 and command_parts[1].startswith('-'):
        try:
            delay = float(command_parts[1][1:])
            if delay < 0:
                send_message_with_style(client, "⏳ Delay phải là số không âm!", thread_id, thread_type)
                return
        except ValueError:
            send_message_with_style(client, "⛔ Sai định dạng delay! Ví dụ: spamsos -3", thread_id, thread_type)
            return

    # Đọc file 5c.txt
    try:
        with open("5c.txt", "r", encoding="utf-8") as file:
            insults = [line.strip() for line in file.readlines() if line.strip()]
    except FileNotFoundError:
        send_message_with_style(client, "⛔ Không tìm thấy file 5c.txt!", thread_id, thread_type)
        return
    if not insults:
        send_message_with_style(client, "⛔ File 5c.txt rỗng!", thread_id, thread_type)
        return

    # Lấy danh sách thành viên nhóm
    try:
        data = client.fetchGroupInfo(groupId=thread_id)
        members = data['gridInfoMap'][str(thread_id)]['memVerList']
        member_ids = []
        for mem in members:
            try:
                user_id, user_name = mem.split('_')
                member_ids.append((user_id, user_name))
            except ValueError:
                continue
    except Exception as e:
        send_message_with_style(client, f"⛔ Lỗi khi lấy danh sách thành viên: {e}", thread_id, thread_type)
        return

    if not member_ids:
        send_message_with_style(client, "⛔ Không tìm thấy thành viên nào trong nhóm!", thread_id, thread_type)
        return

    # Bắt đầu spam
    is_spamming = True
    start_time = time.time()
    send_message_with_style(client, f"🚀 Bắt đầu spam hỗn loạn với delay {delay} giây!", thread_id, thread_type)

    def spam_loop():
        global is_spamming
        while is_spamming and (time.time() - start_time) < MAX_RUNTIME:
            action = random.choice([
                "tag_multiple",  # Tag nhiều người + chửi
                "tag_all",       # Tag tất cả thành viên + chửi (tính năng mới)
                "tag_single",    # Tag một người + chửi
                "send_sticker",  # Gửi sticker
                "insult_sticker",# Chửi + sticker
                "multiple_insults"# 2-3 câu chửi
            ])

            try:
                if action == "tag_multiple" and member_ids:
                    # Chọn ngẫu nhiên số lượng thành viên để tag (2-5)
                    num_tags = random.randint(2, min(5, len(member_ids)))
                    tagged = random.sample(member_ids, num_tags)
                    insult = random.choice(insults)
                    # Tạo tin nhắn với các tag
                    tag_text = " ".join([f"@{user_name}" for _, user_name in tagged])
                    message_text = f"{tag_text} {insult}"
                    # Gửi tin nhắn văn bản chính
                    send_message_with_style(client, message_text, thread_id, thread_type)
                    # Gửi mention cho từng người dùng
                    for user_id, user_name in tagged:
                        mention = Mention(uid=user_id, offset=0, length=len(user_name))
                        message = Message(text=f"@{user_name}", mention=mention)
                        client.sendMentionMessage(message, thread_id, ttl=10000)
                        time.sleep(0.1)  # Delay nhỏ giữa các mention
                    time.sleep(delay)

                elif action == "tag_all" and member_ids:
                    # Tạo danh sách mentions cho tất cả thành viên
                    text = ""
                    mentions = []
                    offset = 0
                    for user_id, user_name in member_ids:
                        text += f"{user_name} "
                        mentions.append(Mention(uid=user_id, offset=offset, length=len(user_name), auto_format=False))
                        offset += len(user_name) + 1
                    multi_mention = MultiMention(mentions)
                    insult = random.choice(insults)
                    # Gửi tin nhắn với tất cả mentions và câu chửi
                    client.send(
                        Message(text=f"{text}{insult}", mention=multi_mention),
                        thread_id,
                        thread_type,
                        ttl=10000
                    )
                    time.sleep(delay)

                elif action == "tag_single" and member_ids:
                    user_id, user_name = random.choice(member_ids)
                    insult = random.choice(insults)
                    mention = Mention(uid=user_id, offset=0, length=len(f"@{user_name}"))
                    message_text = f"@{user_name} {insult}"
                    message = Message(text=message_text, mention=mention)
                    client.sendMentionMessage(message, thread_id, ttl=10000)
                    time.sleep(delay)

                elif action == "send_sticker":
                    sticker = random.choice(stickers)
                    client.sendSticker(
                        sticker['sticker_type'],
                        sticker['sticker_id'],
                        sticker['category_id'],
                        thread_id,
                        thread_type,
                        ttl=60000
                    )
                    time.sleep(delay)

                elif action == "insult_sticker":
                    insult = random.choice(insults)
                    sticker = random.choice(stickers)
                    send_message_with_style(client, f"{insult}", thread_id, thread_type)
                    client.sendSticker(
                        sticker['sticker_type'],
                        sticker['sticker_id'],
                        sticker['category_id'],
                        thread_id,
                        thread_type,
                        ttl=60000
                    )
                    time.sleep(delay)

                elif action == "multiple_insults":
                    num_insults = random.randint(2, 3)
                    for _ in range(num_insults):
                        insult = random.choice(insults)
                        send_message_with_style(client, f"{insult}", thread_id, thread_type)
                        time.sleep(0.5)  # Delay nhỏ giữa các câu chửi
                    time.sleep(delay)

            except ZaloAPIException as e:
                send_message_with_style(client, f"⛔ Lỗi khi spam: {e}", thread_id, thread_type)
                time.sleep(delay)
            except Exception as e:
                send_message_with_style(client, f"⛔ Lỗi không xác định: {e}", thread_id, thread_type)
                time.sleep(delay)

        if is_spamming:  # Dừng do hết thời gian
            send_message_with_style(client, "⏰ Hết thời gian spam hỗn loạn!", thread_id, thread_type)
            is_spamming = False

    spam_thread = threading.Thread(target=spam_loop)
    spam_thread.start()

def get_mitaizl():
    return {
        'spam.random': handle_spamsos_command
    }