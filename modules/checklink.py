from zlapi import ZaloAPI
from zlapi.models import *
import requests


des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Kiểm tra tính khả dụng của các đường link.",
    'tính năng': [
        "🔗 Kiểm tra từng đường link có khả dụng hay không.",
        "📊 Gửi phản ứng xác nhận khi nhận lệnh kiểm tra.",
        "🛠 Hỗ trợ cả phương thức HEAD và GET để kiểm tra link.",
        "📃 Gửi kết quả kiểm tra về tính khả dụng của từng link đến người sử dụng."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh check theo sau là các đường link bạn muốn kiểm tra.",
        "📌 Ví dụ: check https://example.com https://anotherlink.com để kiểm tra hai link.",
        "✅ Nhận thông báo trạng thái của từng link ngay lập tức."
    ]
}

def check_links(message, message_object, thread_id, thread_type, author_id, self):
    """
    Lệnh: check <link1> <link2> <link3> ...
    Chức năng: Kiểm tra từng đường link có khả dụng không.
    """
    # Gửi phản ứng xác nhận khi nhận lệnh
    action = "✅"
    self.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    # Tách tin nhắn để lấy các link (bỏ qua từ "check")
    parts = message.split()
    if len(parts) < 2:
        self.sendMessage(Message("Vui lòng cung cấp ít nhất 1 link để kiểm tra."), thread_id, thread_type)
        return

    links = parts[1:]
    result_lines = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }

    for idx, link in enumerate(links):
        try:
            # Sử dụng HEAD để tiết kiệm băng thông và thời gian
            response = requests.head(link, headers=headers, timeout=10)
            # Nếu server không hỗ trợ HEAD, hãy thử GET
            if response.status_code == 405:
                response = requests.get(link, headers=headers, timeout=10)
            if response.status_code == 200:
                result_lines.append(f"🟢 Link {idx+1}:  {link}  - ✅ Sử dụng được")
            else:
                result_lines.append(f"🔴 Link {idx+1}:  {link}  - ❌ Không sử dụng được ({response.status_code})")
        except Exception as e:
            result_lines.append(f"🔴 Link {idx+1}:  {link}  - ❌ Không sử dụng được ( {e})")

    result_text = "\n".join(result_lines)
    # Gửi kết quả sau khi kiểm tra
    self.sendMessage(Message(result_text), thread_id, thread_type)

def get_mitaizl():
    return {
        'checklink': check_links
    }
