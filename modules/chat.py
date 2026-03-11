from zlapi.models import Message, MessageStyle, MultiMsgStyle
import requests
import urllib.parse
import time
from collections import deque

# Lưu trữ lịch sử trò chuyện để duy trì ngữ cảnh
conversation_history = deque(maxlen=20)  # Giới hạn 20 tin nhắn để tự động xóa

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Trò chuyện với chat AI qua lệnh 'chat' sử dụng API Chat GPT4",
    'tính năng': [
        "💬 Trả lời tin nhắn có chứa từ 'chat' bằng AI",
        "⚡ Gửi phản ứng ngay khi nhận lệnh",
        "🌐 Tích hợp API Chat GPT4 để phản hồi thông minh",
        "🎨 Hỗ trợ tin nhắn có màu sắc và in đậm",
        "⏳ Hỗ trợ TTL (thời gian tồn tại tin nhắn) lên đến 120 giây",
        "🛠️ Xử lý lỗi khi API không phản hồi hoặc gặp sự cố",
        "✂️ Tự động chia tin nhắn dài thành nhiều phần",
        "🔄 Duy trì ngữ cảnh trò chuyện liên tục",
        "🗑️ Tự động xóa luồng trò chuyện sau 20 câu",
        "🧹 Xóa luồng trò chuyện chủ động với lệnh 'chat clear'"
    ],
    'hướng dẫn sử dụng': "Gõ bất kỳ tin nhắn nào có chứa từ 'chat' để trò chuyện với AI. Gõ 'chat clear' để xóa luồng trò chuyện."
}

def send_message_with_style(client, text, thread_id, thread_type, ttl=None, color="#000000", max_length=1500):
    """
    Gửi tin nhắn với định dạng màu sắc và in đậm, tự động chia nhỏ nếu tin nhắn quá dài.
    """
    if len(text) <= max_length:
        base_length = len(text)
        adjusted_length = base_length + 355
        style = MultiMsgStyle([
            MessageStyle(
                offset=0,
                length=adjusted_length,
                style="color",
                color=color,
                auto_format=False,
            ),
            MessageStyle(
                offset=0,
                length=adjusted_length,
                style="font",
                size="8",
                auto_format=False
            )
        ])
        msg = Message(text=text, style=style)
        if ttl is not None:
            client.sendMessage(msg, thread_id, thread_type, ttl=ttl)
        else:
            client.sendMessage(msg, thread_id, thread_type)
        return

    parts = []
    current_part = ""
    words = text.split(" ")

    for word in words:
        if len(current_part) + len(word) + 1 > max_length:
            parts.append(current_part.strip())
            current_part = word + " "
        else:
            current_part += word + " "
    
    if current_part.strip():
        parts.append(current_part.strip())

    for part in parts:
        base_length = len(part)
        adjusted_length = base_length + 355
        style = MultiMsgStyle([
            MessageStyle(
                offset=0,
                length=adjusted_length,
                style="color",
                color=color,
                auto_format=False,
            ),
            MessageStyle(
                offset=0,
                length=adjusted_length,
                style="bold",
                size="8",
                auto_format=False
            )
        ])
        msg = Message(text=part, style=style)
        if ttl is not None:
            client.sendMessage(msg, thread_id, thread_type, ttl=ttl)
        else:
            client.sendMessage(msg, thread_id, thread_type)

def handle_pollinations_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản ứng ngay khi nhận lệnh
    action = "OK"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    # Kiểm tra lệnh xóa lịch sử
    if message.lower().strip() == "chat clear":
        conversation_history.clear()
        reply_text = "🗑️ Luồng trò chuyện đã được xóa. Bắt đầu trò chuyện mới!"
        send_message_with_style(client, reply_text, thread_id, thread_type, ttl=120000)
        return

    # Kiểm tra xem từ "chat" có trong câu lệnh hay không
    if "chat" not in message.lower():
        return

    # Tách nội dung sau từ "chat"
    chat_index = message.lower().find("chat")
    content = message[chat_index + len("chat"):].strip()

    # Kiểm tra nếu không có nội dung sau "chat"
    if not content:
        error_message = Message(text="Vui lòng nhập nội dung sau lệnh 'chat' để trò chuyện với GPT 4")
        client.sendMessage(error_message, thread_id, thread_type)
        return

    # Thêm tin nhắn người dùng vào lịch sử (chỉ nội dung sau "chat")
    conversation_history.append(f"User: {content}")

    # Kiểm tra nếu lịch sử đạt 20 câu, xóa và thông báo
    if len(conversation_history) >= 20:
        conversation_history.clear()
        reply_text = "🗑️ Luồng trò chuyện đã đạt 20 câu và được xóa tự động. Bắt đầu trò chuyện mới!"
        send_message_with_style(client, reply_text, thread_id, thread_type, ttl=120000)
        # Thêm lại tin nhắn hiện tại để tiếp tục xử lý
        conversation_history.append(f"User: {content}")

    # Tạo ngữ cảnh từ lịch sử trò chuyện
    context = "\n".join(conversation_history)
    encoded_context = urllib.parse.quote(context, safe='')

    try:
        # Gọi API Pollinations với ngữ cảnh
        pollinations_url = f'https://text.pollinations.ai/{encoded_context}'
        print(f"Sending request to Pollinations API with: {pollinations_url}")
        
        # Thêm timeout để tránh treo
        response = requests.get(pollinations_url, timeout=10)
        response.raise_for_status()

        # Xử lý phản hồi API
        content_type = response.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            data = response.json()
            ai_reply = data.get('answer', 'Không có phản hồi từ Pollinations.')
        else:
            ai_reply = response.text

        # Thêm phản hồi AI vào lịch sử
        conversation_history.append(f"Bot: {ai_reply}")

        # Gửi phản hồi với định dạng
        reply_text = f"🗨️ Bot nói: {ai_reply}"
        send_message_with_style(client, reply_text, thread_id, thread_type, ttl=120000)

    except requests.exceptions.Timeout:
        print("Pollinations API timeout")
        error_message = Message(text="API phản hồi quá chậm, vui lòng thử lại sau!")
        client.sendMessage(error_message, thread_id, thread_type)
    except requests.exceptions.RequestException as e:
        print(f"Error when calling Pollinations API: {str(e)}")
        error_message = Message(text="Bạn đang chat quá nhanh, vui lòng chờ AI suy nghĩ!")
        client.sendMessage(error_message, thread_id, thread_type)
        time.sleep(2)
    except KeyError as e:
        print(f"Error with API response structure: {str(e)}")
        error_message = Message(text=f"Dữ liệu từ API không đúng cấu trúc: {str(e)}")
        client.sendMessage(error_message, thread_id, thread_type)
    except Exception as e:
        print(f"Unknown error: {str(e)}")
        error_message = Message(text=f"Đã xảy ra lỗi không xác định: {str(e)}")
        client.sendMessage(error_message, thread_id, thread_type)

def get_mitaizl():
    return {
        'chat': handle_pollinations_command
    }