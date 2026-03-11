# noitu.py – PHIÊN BẢN HOÀN CHỈNH THEO YÊU CẦU MỚI NHẤT
import time
import requests
import threading
from zlapi.models import Message, Mention
import logging
import os
import re

logging.basicConfig(level=logging.INFO)

# ==================== DEEPSEEK ====================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-0aeec1b9a58e4d76a5db0dc829ac6e5e")
API_URL = "https://api.deepseek.com/chat/completions"
MODEL_NAME = "deepseek-chat"

# ==================== TRẠNG THÁI ====================
active_games = {}
player_scores = {}
used_phrases = {}
timers = {}

GAME_TIME = 180
WARNING_TIME = 30

# Lấy từ cuối cùng
def get_last_word(phrase):
    clean = re.sub(r'[^a-zàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ\s]', ' ', phrase.lower())
    words = clean.strip().split()
    return words[-1] if words else ""

# PROMPT + VALIDATE SIÊU CHẶT (không banned list)
def call_deepseek_two_words(start_with):
    prompt = f"""Luật sắt nối từ 2 chữ tiếng Việt:
- Chỉ trả về đúng 1 dòng chứa đúng 2 từ có dấu.
- Từ đầu tiên PHẢI là "{start_with}" (viết thường, đúng dấu).
- Hai từ phải tạo thành cụm CÓ NGHĨA THỰC SỰ, phổ biến trong đời sống.
- Tuyệt đối cấm từ nối, từ đệm, từ cảm thán, lặp từ.
- Không thêm ký tự thừa nào.

Ví dụ chuẩn:
mèo → mèo con
con → con trai
trai → trai đẹp
mướp → mướp đắng
đắng → đắng cay
cay → cay xè
hương → hương đồng
phở → phở bò
bò → bò sữa

Bắt đầu bằng "{start_with}":"""

    for _ in range(12):
        try:
            r = requests.post(API_URL, json={
                "model": MODEL_NAME,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.68,
                "max_tokens": 12,
                "top_p": 0.88
            }, headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}, timeout=10)

            if r.status_code == 200:
                result = r.json()["choices"][0]["message"]["content"].strip().lower()
                lines = [l.strip() for l in result.split("\n") if l.strip()]
                for line in lines:
                    words = line.split()
                    if len(words) != 2 or words[0] != start_with.lower():
                        continue
                    if words[0] == words[1]:
                        continue
                    vowels = "aeiouyáàảãạâấầẩẫậăắằẳẵặéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵ"
                    if len(words[0]) < 2 or len(words[1]) < 2 or not (any(v in words[0] for v in vowels) and any(v in words[1] for v in vowels)):
                        continue
                    return " ".join(words)
        except:
            time.sleep(0.3)
    return None

def schedule_timer(tid, ttype, client):
    if tid in timers:
        timers[tid].cancel()
    timers[tid] = threading.Timer(GAME_TIME, lambda: end_game(tid, ttype, client))
    timers[tid].start()
    threading.Timer(GAME_TIME - WARNING_TIME, lambda: client.sendMessage(
        Message(text="Còn 30 giây! Ai nối nhanh tay nào!"), tid, ttype, ttl=3000)
    ).start()

def end_game(tid, ttype, client):
    if tid in active_games:
        active_games.pop(tid, None)
        player_scores.pop(tid, None)
        used_phrases.pop(tid, None)
        client.sendMessage(Message(text="Hết giờ! Gõ 'nt <2 từ>' để chơi lại nhé!"), tid, ttype, ttl=30000)

def get_user_display_name_and_id(client, author_id):
    try:
        uid = str(author_id)
        real_uid = uid.split('_')[0] if '_' in uid else uid
        info = client.fetchUserInfo(real_uid)
        profile = (info.unchanged_profiles or info.changed_profiles or {}).get(real_uid)
        return profile.zaloName.strip() if profile and profile.zaloName else "Bạn", real_uid
    except:
        return "Bạn", str(author_id).split('_')[0] if '_' in str(author_id) else str(author_id)

# ==================== BẮT ĐẦU TRÒ CHƠI ====================
def handle_nt(message, msg_obj, tid, ttype, author_id, client):
    client.sendReaction(msg_obj, "YES", tid, ttype, reactionType=75)
    parts = message.split(maxsplit=1)
    if len(parts) < 2:
        client.replyMessage(Message(text="Cách dùng: nt <2 từ>\nVí dụ: nt con mèo"), msg_obj, tid, ttype, ttl=20000)
        return

    player_phrase = parts[1].strip().lower()
    if len(player_phrase.split()) != 2:
        client.replyMessage(Message(text="Phải đúng 2 từ thôi nha! Ví dụ: con mèo"), msg_obj, tid, ttype, ttl=10000)
        return

    bot_phrase = call_deepseek_two_words(get_last_word(player_phrase))
    if not bot_phrase:
        client.replyMessage(Message(text="Bot đang lag xíu, thử lại sau vài giây nha!"), msg_obj, tid, ttype, ttl=10000)
        return

    display_name, real_uid = get_user_display_name_and_id(client, author_id)
    mention_text = f"@{display_name}"
    mention = Mention(uid=real_uid, offset=0, length=len(mention_text))

    active_games[tid] = {"last_word": get_last_word(bot_phrase), "timestamp": time.time()}
    player_scores[tid] = {real_uid: 0}
    used_phrases[tid] = {player_phrase, bot_phrase}

    text = f"""Nối Từ 2 Chữ Bắt Đầu!

{mention_text} → {player_phrase}
Bot → {bot_phrase}

Tiếp theo bắt đầu bằng "{get_last_word(bot_phrase).upper()}" nào!"""

    client.sendMessage(Message(text=text, mention=mention), tid, ttype, ttl=180000)
    schedule_timer(tid, ttype, client)

# ==================== XỬ LÝ NGƯỜI CHƠI NỐI (CÓ THÔNG BÁO KHI SAI) ====================
def handle_answer(message, msg_obj, tid, ttype, author_id, client):
    if tid not in active_games:
        return

    required = active_games[tid]["last_word"]
    player_phrase = message.strip().lower()
    words = player_phrase.split()

    # === KIỂM TRA NGHIÊM NGẶT ===
    vowels = "aeiouyáàảãạâấầẩẫậăắằẳẵặéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵ"

    if (len(words) != 2 or 
        words[0] != required or 
        player_phrase in used_phrases[tid] or
        words[0] == words[1] or
        len(words[0]) < 2 or len(words[1]) < 2 or
        not (any(v in words[0] for v in vowels) and any(v in words[1] for v in vowels))):
        
        # Gửi thông báo nhắc nhở 1 lần duy nhất mỗi người
        display_name, real_uid = get_user_display_name_and_id(client, author_id)
        mention_text = f"@{display_name}"
        mention = Mention(uid=real_uid, offset=0, length=len(mention_text))
        client.replyMessage(
            Message(text=f"{mention_text} Cụm từ không hợp lệ hoặc đã dùng rồi! Vui lòng gõ cụm 2 từ có nghĩa, bắt đầu bằng \"{required.upper()}\""),
            msg_obj, tid, ttype, ttl=15000, mention=mention
        )
        return

    # === HỢP LỆ 100% ===
    display_name, real_uid = get_user_display_name_and_id(client, author_id)
    player_scores[tid][real_uid] = player_scores[tid].get(real_uid, 0) + 1
    used_phrases[tid].add(player_phrase)

    bot_phrase = call_deepseek_two_words(words[1])
    mention_text = f"@{display_name}"
    mention = Mention(uid=real_uid, offset=0, length=len(mention_text))

    if not bot_phrase:
        text = f"{mention_text} QUÁ MẠNH! Bot bí hoàn toàn, bạn thắng tuyệt đối\nĐiểm cuối: {player_scores[tid][real_uid]}"
        client.replyMessage(Message(text=text, mention=mention), msg_obj, tid, ttype, ttl=90000)
        end_game(tid, ttype, client)
        return

    active_games[tid]["last_word"] = get_last_word(bot_phrase)
    used_phrases[tid].add(bot_phrase)

    text = f"""{mention_text} → {player_phrase}
Bot → {bot_phrase}

Điểm: {player_scores[tid][real_uid]}
Tiếp theo bắt đầu bằng "{get_last_word(bot_phrase).upper()}" nào!"""

    client.replyMessage(Message(text=text, mention=mention), msg_obj, tid, ttype, ttl=180000)
    schedule_timer(tid, ttype, client)

# ==================== DỪNG (giữ nguyên) ====================
def handle_stop(msg_obj, tid, ttype, client):
    print(f"[NTSTOP] Đã nhận lệnh ntstop - tid: {tid}")
    if tid in timers:
        timers[tid].cancel()
        timers.pop(tid, None)

    if tid not in active_games:
        client.replyMessage(Message(text="Không có game đang chạy!"), msg_obj, tid, ttype, ttl=30000)
        return

    scores = player_scores.get(tid, {})
    if not scores:
        client.replyMessage(Message(text="Không có điểm nào để hiển thị!"), msg_obj, tid, ttype, ttl=30000)
    else:
        ranking = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        text = "Trò chơi đã dừng! Bảng xếp hạng:\n\n"
        mentions = []
        current_offset = len(text)
        for i, (uid, sc) in enumerate(ranking[:10], 1):
            display_name, real_uid = get_user_display_name_and_id(client, uid)
            line = f"{i}. @{display_name} → {sc} điểm\n"
            text += line
            mention_start = current_offset + line.find("@")
            mention_length = len(display_name) + 1
            mentions.append(Mention(uid=real_uid, offset=mention_start, length=mention_length))
            current_offset += len(line)
        client.replyMessage(Message(text=text, mentions=mentions), msg_obj, tid, ttype)

    active_games.pop(tid, None)
    player_scores.pop(tid, None)
    used_phrases.pop(tid, None)

# ==================== RETURN ====================
def get_mitaizl():
    return {
        'nt': handle_nt,
        'ntstop': lambda message, msg_obj, tid, ttype, author_id, client: handle_stop(msg_obj, tid, ttype, client),
        'default': handle_answer
    }