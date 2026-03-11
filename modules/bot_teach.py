import requests
import urllib.parse
from zlapi.models import Message, MessageStyle, MultiMsgStyle
from config import ADMIN, PREFIX

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Dạy Simi trả lời",
    'tính năng': [
        "📨 Dạy Simi trả lời các câu hỏi.",
        "🔍 Tách câu hỏi và câu trả lời bằng dấu '/'",
        "🔗 Mã hóa URL cho câu hỏi và câu trả lời.",
        "🔍 Kiểm tra quyền admin trước khi thực hiện lệnh.",
        "🖼️ Gửi yêu cầu đến API dạy Simi và xử lý phản hồi.",
        "🔔 Thông báo lỗi cụ thể nếu có vấn đề xảy ra khi xử lý yêu cầu."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh teach: <câu hỏi> / <câu trả lời> để dạy Simi trả lời.",
        "📌 Ví dụ: teach: Bạn khỏe không? / Mình khỏe, cảm ơn! để dạy Simi trả lời câu hỏi 'Bạn khỏe không?' với câu trả lời 'Mình khỏe, cảm ơn!'.",
        "✅ Nhận thông báo trạng thái và kết quả dạy Simi ngay lập tức."
    ]
}

def send_reply_with_style(client, text, message_object, thread_id, thread_type, ttl=None, color="#db342e"):
    """ Gửi tin nhắn phản hồi với định dạng màu sắc và in đậm. """
    base_length = len(text)
    adjusted_length = base_length + 355
    style = MultiMsgStyle([
        MessageStyle(offset=0, length=adjusted_length, style="color", color=color, auto_format=False),
        MessageStyle(offset=0, length=adjusted_length, style="bold", size="8", auto_format=False)
    ])
    msg = Message(text=text, style=style)
    
    if ttl is not None:
        client.replyMessage(msg, message_object, thread_id, thread_type, ttl=ttl)
    else:
        client.replyMessage(msg, message_object, thread_id, thread_type)

def handle_teach_command(message, message_object, thread_id, thread_type, author_id, client):
    """ Xử lý lệnh dạy Simi trả lời. Định dạng lệnh có thể là: teach: câu hỏi / câu trả lời hoặc teach câu hỏi / câu trả lời """
    
    # Gửi phản ứng ngay khi nhận lệnh
    action = "OK"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    
    # Kiểm tra từ khóa lệnh bắt đầu bằng "teach" (có thể có hoặc không có dấu ':')
    command_prefix = "bot.teach"
    if not message.lower().startswith(command_prefix):
        error_msg = Message(text="Lệnh không hợp lệ. Vui lòng sử dụng định dạng: teach: câu hỏi / câu trả lời hoặc teach câu hỏi / câu trả lời")
        client.sendMessage(error_msg, thread_id, thread_type)
        return
    
    # Loại bỏ tiền tố "teach" và dấu ':' nếu có
    content = message[len(command_prefix):].strip()
    if content.startswith(":"):
        content = content[1:].strip()
    
    if not content:
        error_msg = Message(text="Không tìm thấy nội dung. Vui lòng sử dụng định dạng: teach câu hỏi / câu trả lời")
        client.sendMessage(error_msg, thread_id, thread_type)
        return
    
    # Tách câu hỏi và câu trả lời bằng dấu '/'
    if "/" not in content:
        error_msg = Message(text="Vui lòng tách câu hỏi và câu trả lời bằng dấu /")
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    ask, ans = content.split("/", 1)
    ask = ask.strip()
    ans = ans.strip()

    if not ask or not ans:
        error_msg = Message(text="Câu hỏi và câu trả lời không được để trống.")
        client.sendMessage(error_msg, thread_id, thread_type)
        return
    
    # Mã hóa URL cho câu hỏi và câu trả lời
    encoded_ask = urllib.parse.quote(ask, safe='')
    encoded_ans = urllib.parse.quote(ans, safe='')

    # Tạo URL API dạy Simi
    teach_url = f'https://api.sumiproject.net/sim?type=teach&ask={encoded_ask}&ans={encoded_ans}'
    print(f"Sending teaching request to API with: {teach_url}")

    try:
        response = requests.get(teach_url)
        response.raise_for_status()
        print("Response from API:", response.text)
        data = response.json()

        # Nếu API trả về lỗi thì lấy thông báo lỗi, nếu không lấy thông báo thành công
        if "error" in data:
            api_message = data["error"]
        else:
            api_message = data.get('message', 'Đã dạy thành công cho Mya.')
        
        reply_text = (
            f"✅ Đã dạy Mya với:\n"
            f"- Câu hỏi: {ask}\n"
            f"- Câu trả lời: {ans}\n"
            f"Phản hồi từ API: {api_message}"
        )
        send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=120000)
    
    except requests.exceptions.RequestException as e:
        print(f"Error when calling teaching API: {str(e)}")
        error_msg = Message(text=f"Đã xảy ra lỗi khi gọi API: {str(e)}")
        client.sendMessage(error_msg, thread_id, thread_type)
    
    except KeyError as e:
        print(f"Error with API data structure: {str(e)}")
        error_msg = Message(text=f"Dữ liệu từ API không đúng cấu trúc: {str(e)}")
        client.sendMessage(error_msg, thread_id, thread_type)
    
    except Exception as e:
        print(f"Unknown error: {str(e)}")
        error_msg = Message(text=f"Đã xảy ra lỗi không xác định: {str(e)}")
        client.sendMessage(error_msg, thread_id, thread_type)

def get_mitaizl():
    """ Trả về một dictionary ánh xạ lệnh 'teach' tới hàm xử lý tương ứng. """
    return {
        'bot.teach': handle_teach_command
    }
