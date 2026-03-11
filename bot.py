from zlapi.models import Message, MessageStyle, MultiMsgStyle
import requests
import urllib.parse

des = {
    'tác giả': "Quốc Khánh",
    'mô tả': "Trò chuyện với mya bằng lệnh 'bot'",
    'tính năng': [
        "💬 Trả lời tin nhắn có chứa từ 'bot' bằng học máy",
        "⚡ Gửi phản ứng ngay khi nhận lệnh",
        "🌐 Tích hợp api để phản hồi thông minh",
        "🎨 Hỗ trợ tin nhắn có màu sắc và in đậm",
        "⏳ Hỗ trợ TTL (thời gian tồn tại tin nhắn) lên đến 120 giây",
        "🛠️ Xử lý lỗi khi API không phản hồi hoặc gặp sự cố"
    ],
    'hướng dẫn sử dụng': "Gõ bất kỳ tin nhắn nào có chứa từ 'bot' để trò chuyện với Mya"
}

def send_message_with_style(client, text, thread_id, thread_type, ttl=None, color="#db342e"):
    """
    Gửi tin nhắn với định dạng màu sắc và in đậm.
    """
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
            style="bold",
            size="8",
            auto_format=False
        )
    ])
    msg = Message(text=text, style=style)
    if ttl is not None:
        client.sendMessage(msg, thread_id, thread_type, ttl=ttl)
    else:
        client.sendMessage(msg, thread_id, thread_type)

def handle_sim_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản ứng ngay khi người dùng soạn đúng lệnh
    action = "OK"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    # Kiểm tra xem từ "bot" có trong câu lệnh hay không
    if "bot" not in message.lower():
        return  # Nếu không có từ "bot", không làm gì cả

    # Mã hóa toàn bộ câu lệnh và gửi đi
    encoded_text = urllib.parse.quote(message, safe='')

    try:
        # Gửi yêu cầu đến API của Simi với câu lệnh đầy đủ
        sim_url = f'https://api.sumiproject.net/sim?type=ask&ask={encoded_text}'
        print(f"Sending request to API with: {sim_url}")  # In ra URL gửi tới API
        response = requests.get(sim_url)
        response.raise_for_status()  # Kiểm tra nếu API trả về lỗi (4xx, 5xx)

        # In ra phản hồi từ API để kiểm tra
        print("Response from API:", response.text)

        # Lấy câu trả lời từ API
        data = response.json()
        print("API Data:", data)  # In dữ liệu từ API để kiểm tra

        simi = data.get('answer', 'Không có phản hồi từ Simi.')
        text = f"🗨️ Bot nói : {simi}"
        
        # Trả lời lại người dùng với style
        send_message_with_style(client, text, thread_id, thread_type, ttl=120000)

    except requests.exceptions.RequestException as e:
        # In ra lỗi khi gọi API
        print(f"Error when calling API: {str(e)}")
        error_message = Message(text=f"Đã xảy ra lỗi khi gọi API: {str(e)}")
        client.sendMessage(error_message, thread_id, thread_type)
    except KeyError as e:
        # In ra lỗi nếu dữ liệu từ API không đúng
        print(f"Error with API data structure: {str(e)}")
        error_message = Message(text=f"Dữ liệu từ API không đúng cấu trúc: {str(e)}")
        client.sendMessage(error_message, thread_id, thread_type)
    except Exception as e:
        # In ra lỗi không xác định
        print(f"Unknown error: {str(e)}")
        error_message = Message(text=f"Đã xảy ra lỗi không xác định: {str(e)}")
        client.sendMessage(error_message, thread_id, thread_type)

def get_mitaizl():
    return {
        'bot': handle_sim_command
    }
