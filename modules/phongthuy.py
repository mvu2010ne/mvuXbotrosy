import requests
import urllib.parse
from zlapi.models import Message, MessageStyle, MultiMsgStyle
from config import ADMIN, PREFIX

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Xem phong thủy 4 số cuối của sdt",
    'tính năng': [
        "🔮 Tra cứu thông tin phong thủy của 4 số cuối điện thoại.",
        "📨 Gửi phản hồi với kết quả phong thủy và thông tin chi tiết.",
        "🔔 Thông báo lỗi cụ thể nếu có vấn đề xảy ra khi gọi API hoặc xử lý dữ liệu.",
        "🎨 Hiển thị tin nhắn với định dạng màu sắc và in đậm."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh phongthuy <số điện thoại> để kiểm tra thông tin phong thủy.",
        "📌 Ví dụ: phongthuy 0987654321 để tra cứu phong thủy của 4 số cuối 4321.",
        "✅ Nhận thông báo trạng thái tra cứu và kết quả chi tiết ngay lập tức."
    ]
}

def send_reply_with_style(client, text, message_object, thread_id, thread_type, ttl=None, color="#db342e"):
    """ Gửi tin nhắn phản hồi với định dạng màu sắc và in đậm. """
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

def handle_phongtuy_command(message, message_object, thread_id, thread_type, author_id, client):
    """ Xử lý lệnh xem phong thủy 4 số cuối của sdt. Định dạng lệnh có thể là: phongtuy: sdt hoặc phongtuy sdt """
    # Gửi phản ứng ngay khi nhận lệnh
    action = "OK"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    # Kiểm tra từ khóa lệnh bắt đầu bằng "phongtuy"
    command_prefix = "phongthuy"
    if not message.lower().startswith(command_prefix):
        error_msg = Message(text="Lệnh không hợp lệ. Vui lòng sử dụng định dạng: phongtuy: sdt hoặc phongtuy sdt")
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    # Loại bỏ tiền tố "phongtuy" và dấu ':' nếu có
    content = message[len(command_prefix):].strip()
    if content.startswith(":"):
        content = content[1:].strip()

    if not content:
        error_msg = Message(text="Không tìm thấy số điện thoại. Vui lòng nhập số điện thoại cần xem phong thủy.")
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    phone_number = content

    # Nếu nhập số điện thoại đầy đủ, lấy 4 số cuối
    if len(phone_number) > 4:
        phone_number = phone_number[-4:]

    if not phone_number.isdigit() or len(phone_number) != 4:
        error_msg = Message(text="Vui lòng nhập đúng 4 số cuối của số điện thoại.")
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    # Mã hóa số điện thoại (4 số cuối)
    encoded_sdt = urllib.parse.quote(phone_number, safe='')

    # Tạo URL API xem phong thủy
    api_url = f'https://api.sumiproject.net/sdtphongtuy?sdt={encoded_sdt}'
    print(f"Sending phong tuy request to API with: {api_url}")

    try:
        response = requests.get(api_url)
        response.raise_for_status()
        print("Response from API:", response.text)
        data = response.json()

        if data.get("success"):
            # Giả sử cấu trúc: { "success": true, "data": { "phongtuy": { "1079": "kết quả phong thủy" } } }
            phongtuy_data = data.get("data", {}).get("phongtuy", {})
            result_text = phongtuy_data.get(phone_number, "Không có kết quả phong thủy.")
        else:
            result_text = data.get("error", "Đã xảy ra lỗi khi xem phong thủy.")

        reply_text = (
            f"🔮 Kết quả phong thủy cho 4 số cuối {phone_number}:\n"
            f"{result_text}"
        )
        send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=120000)

    except requests.exceptions.RequestException as e:
        print(f"Error when calling phong tuy API: {str(e)}")
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
    """ Trả về một dictionary ánh xạ lệnh 'phongtuy' tới hàm xử lý tương ứng. """
    return {
        'phongthuy': handle_phongtuy_command
    }
