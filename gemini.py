import requests
import json
import logging
from zlapi.models import *
from collections import deque

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

GEMINI_API_KEY = "AIzaSyCkG7NfjnfBQ4ovfLW7uAFl6V8WDmgt7dg"
api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={GEMINI_API_KEY}"

# Lưu trữ lịch sử trò chuyện để duy trì ngữ cảnh
conversation_history = deque(maxlen=20)  # Giới hạn 20 tin nhắn để tự động xóa

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🔍 Trò chuyện với Gemini AI để trả lời các câu hỏi.",
    'tính năng': [
        "🤖 Gửi câu hỏi đến API Gemini AI và nhận phản hồi thông minh.",
        "📩 Trả lời trực tiếp trong tin nhắn với định dạng rõ ràng.",
        "✅ Phản ứng bằng biểu tượng cảm xúc để xác nhận trạng thái xử lý.",
        "⚠️ Thông báo lỗi chi tiết nếu API gặp sự cố.",
        "🔄 Duy trì ngữ cảnh trò chuyện liên tục.",
        "🗑️ Tự động xóa luồng trò chuyện sau 20 câu.",
        "🧹 Xóa luồng trò chuyện chủ động với lệnh 'gemini clear'."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh gemini <câu hỏi> để trò chuyện với Gemini AI.",
        "📌 Ví dụ: gemini Thời tiết hôm nay thế nào?",
        "🗑️ Gõ 'gemini clear' để xóa luồng trò chuyện.",
        "✅ Nhận câu trả lời từ Gemini AI trong tin nhắn."
    ]
}

def ask_gemini(content, message_object, thread_id, thread_type, client):
    try:
        # Tạo danh sách contents với lịch sử và tin nhắn hiện tại
        contents = []
        for msg in conversation_history:
            role = "user" if msg.startswith("User:") else "model"
            text = msg.replace("User: ", "").replace("Bot: ", "")
            contents.append({
                "role": role,
                "parts": [{"text": text}]
            })
        contents.append({
            "role": "user",
            "parts": [{"text": content}]
        })

        request_data = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 2048,
                "responseMimeType": "text/plain"
            }
        }

        response = requests.post(api_url, json=request_data, headers={'Content-Type': 'application/json'}, timeout=10)
        response.raise_for_status()

        response_data = response.json()

        if 'candidates' not in response_data or not response_data['candidates']:
            logging.error(response_data)
            gemini_response = "API không trả về dữ liệu mong đợi."
        else:
            gemini_response = response_data['candidates'][0]['content']['parts'][0]['text']

        if not gemini_response.strip():
            gemini_response = "Gemini không có gì để nói."

        # Thêm phản hồi vào lịch sử
        conversation_history.append(f"Bot: {gemini_response}")

        message_to_send = Message(text=f"> Gemini AI: {gemini_response}")
        client.replyMessage(message_to_send, message_object, thread_id, thread_type)
        client.sendReaction(message_object, 'YES', thread_id, thread_type)
    except requests.exceptions.Timeout:
        logging.error("Gemini API timeout")
        client.sendReaction(message_object, '🚫', thread_id, thread_type)
        message_to_send = Message(text="API phản hồi quá chậm, vui lòng thử lại sau!")
        client.sendMessage(message_to_send, thread_id, thread_type)
    except requests.exceptions.RequestException as e:
        logging.error(f"Lỗi khi gọi API: {str(e)}")
        client.sendReaction(message_object, '🚫', thread_id, thread_type)
        message_to_send = Message(text=f"Lỗi khi gọi API: {str(e)}")
        client.sendMessage(message_to_send, thread_id, thread_type)
    except Exception as e:
        logging.error(f"Lỗi không xác định: {str(e)}")
        client.sendReaction(message_object, '🚫', thread_id, thread_type)
        message_to_send = Message(text=f"Đã xảy ra lỗi: {str(e)}")
        client.sendMessage(message_to_send, thread_id, thread_type)

def handle_genz_command(message, message_object, thread_id, thread_type, author_id, client):
    text = message.split()

    # Kiểm tra lệnh xóa lịch sử
    if message.lower().strip() == "gemini clear":
        conversation_history.clear()
        client.sendReaction(message_object, 'OK', thread_id, thread_type)
        message_to_send = Message(text="🗑️ Luồng trò chuyện đã được xóa. Bắt đầu trò chuyện mới!")
        client.sendMessage(message_to_send, thread_id, thread_type)
        return

    if len(text) < 2 or "gemini" not in text[0].lower():
        client.sendReaction(message_object, 'OK', thread_id, thread_type)
        error_message = Message(text="Vui lòng nhập câu hỏi với định dạng: gemini <câu hỏi>")
        client.sendMessage(error_message, thread_id, thread_type)
        return

    content = " ".join(text[1:])

    # Thêm tin nhắn người dùng vào lịch sử
    conversation_history.append(f"User: {content}")

    # Kiểm tra nếu lịch sử đạt 20 câu, xóa và thông báo
    if len(conversation_history) >= 20:
        conversation_history.clear()
        client.sendReaction(message_object, 'OK', thread_id, thread_type)
        message_to_send = Message(text="🗑️ Luồng trò chuyện đã đạt 20 câu và được xóa tự động. Bắt đầu trò chuyện mới!")
        client.sendMessage(message_to_send, thread_id, thread_type)
        # Thêm lại tin nhắn hiện tại để tiếp tục xử lý
        conversation_history.append(f"User: {content}")

    ask_gemini(content, message_object, thread_id, thread_type, client)

def get_mitaizl():
    return {
        'gemini': handle_genz_command
    }