import requests
import urllib.parse
from zlapi.models import Message, MessageStyle, MultiMsgStyle
from config import ADMIN, PREFIX

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Định giá số điện thoại dựa trên dữ liệu API",
    'tính năng': [
        "📞 Định giá số điện thoại theo dữ liệu có sẵn",
        "🌐 Tích hợp API tự động xử lý thông tin",
        "⏳ Phản hồi nhanh chóng với kết quả chi tiết",
        "🔍 Kiểm tra và xác minh số điện thoại hợp lệ",
        "📂 Hỗ trợ nhiều định dạng nhập liệu"
    ],
    'hướng dẫn sử dụng': [
        "▶️ Dùng lệnh 'dinhgiasdt <số điện thoại>' để tra cứu.",
        "📌 Ví dụ: 'dinhgiasdt 0868084438' để kiểm tra giá trị.",
        "💡 Hệ thống tự động xử lý và hiển thị kết quả.",
        "🚀 Phản hồi nhanh chóng với định dạng tin nhắn đặc biệt."
    ]
}

def send_reply_with_style(client, text, message_object, thread_id, thread_type, ttl=None, color="#db342e"):
    """
    Gửi tin nhắn phản hồi với định dạng màu sắc và in đậm.
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
        client.replyMessage(msg, message_object, thread_id, thread_type, ttl=ttl)
    else:
        client.replyMessage(msg, message_object, thread_id, thread_type)

def handle_valuation_command(message, message_object, thread_id, thread_type, author_id, client):
    """
    Xử lý lệnh định giá số điện thoại.
    Định dạng lệnh có thể là:
        valuation: sdt
    hoặc
        valuation sdt
    Ví dụ:
        valuation: 0868084438
    """
    # Gửi phản ứng ngay khi nhận lệnh
    action = "OK"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    
    # Kiểm tra từ khóa lệnh bắt đầu bằng "valuation"
    command_prefix = "dinhgiasdt"
    if not message.lower().startswith(command_prefix):
        error_msg = Message(text="Lệnh không hợp lệ. Vui lòng sử dụng định dạng: valuation: sdt hoặc valuation sdt")
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    # Loại bỏ tiền tố "valuation" và dấu ':' nếu có
    content = message[len(command_prefix):].strip()
    if content.startswith(":"):
        content = content[1:].strip()
    
    if not content:
        error_msg = Message(text="Không tìm thấy số điện thoại. Vui lòng nhập số điện thoại cần định giá.")
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    phone_number = content
    # Có thể bổ sung kiểm tra định dạng số điện thoại nếu cần

    # Mã hóa URL cho số điện thoại
    encoded_sdt = urllib.parse.quote(phone_number, safe='')

    # Tạo URL API định giá sdt
    valuation_url = f'https://api.sumiproject.net/valuation?sdt={encoded_sdt}'
    print(f"Sending valuation request to API with: {valuation_url}")

    try:
        response = requests.get(valuation_url)
        response.raise_for_status()
        print("Response from API:", response.text)
        data = response.json()
        
        # Kiểm tra cấu trúc phản hồi từ API
        if data.get("success"):
            valuation_data = data.get("data", {}).get("valuation", {})
            result_text = valuation_data.get(phone_number, "Không có kết quả định giá.")
        else:
            result_text = data.get("error", "Đã xảy ra lỗi khi định giá.")

        reply_text = (
            f"📞 Kết quả định giá số điện thoại {phone_number}:\n"
            f"{result_text}"
        )
        send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=120000)

    except requests.exceptions.RequestException as e:
        print(f"Error when calling valuation API: {str(e)}")
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
    """
    Trả về một dictionary ánh xạ lệnh 'valuation' tới hàm xử lý tương ứng.
    """
    return {
        'dinhgiasdt': handle_valuation_command
    }
