import requests
import urllib.parse
from zlapi.models import Message, MultiMsgStyle, MessageStyle

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🔍 Kiểm tra thông tin người dùng GitHub.",
    'tính năng': [
        "📋 Lấy thông tin như tên, tiểu sử, vị trí, số lượng kho lưu trữ, người theo dõi, ngày tạo tài khoản.",
        "🎨 Định dạng tin nhắn với phông chữ và in đậm để dễ đọc.",
        "✅ Kiểm tra tính hợp lệ của tên người dùng trước khi gọi API.",
        "⚠️ Thông báo lỗi chi tiết nếu API thất bại hoặc không tìm thấy thông tin."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh githubi4 <tên_người_dùng> để kiểm tra thông tin GitHub.",
        "📌 Ví dụ: githubi4 octocat",
        "✅ Nhận thông tin chi tiết của người dùng GitHub trong tin nhắn."
    ]
}

def handle_checkhost_command(message, message_object, thread_id, thread_type, author_id, client):
    content = message.strip().split()
    if len(content) < 2:
        error_message = "Vui lòng nhập tên người dùng GitHub để kiểm tra thông tin."
        client.replyMessage(
            Message(
                text=error_message, 
                style=MultiMsgStyle([
                    MessageStyle(offset=0, length=len(error_message), style="font", size=13, auto_format=False),
                    MessageStyle(offset=0, length=len(error_message), style="bold", auto_format=False)
                ])
            ), message_object, thread_id, thread_type
        )
        return

    username = " ".join(content[1:]).strip()  # Lấy tên người dùng GitHub từ thông điệp
    try:
        api_url = f'https://api.sumiproject.net/github/info?username={urllib.parse.quote(username)}'  # URL chính xác của API
        response = requests.get(api_url)
        response.raise_for_status()

        data = response.json()
        print("Dữ liệu nhận được từ API:", data)

        # Kiểm tra xem có trả về dữ liệu không
        if not data.get("login"):
            raise KeyError("Không có thông tin nào được tìm thấy cho người dùng này.")
        
        # Lấy dữ liệu từ API
        login = data.get("login", "N/A")
        name = data.get("name", "N/A")
        avatar_url = data.get("avatar_url", "N/A")
        html_url = data.get("html_url", "N/A")
        bio = data.get("bio", "N/A")
        location = data.get("location", "N/A")
        public_repos = data.get("public_repos", 0)
        followers = data.get("followers", 0)
        following = data.get("following", 0)
        ngay_tao = data.get("ngay_tao", "N/A")
        gio_tao = data.get("gio_tao", "N/A")

        result = (
            f"Thông tin người dùng GitHub: {name} (@{login})\n\n"
            f"Avatar: {avatar_url}\n"
            f"URL hồ sơ: {html_url}\n"
            f"Tiểu sử: {bio}\n"
            f"Vị trí: {location}\n"
            f"Số lượng repo công khai: {public_repos}\n"
            f"Số người theo dõi: {followers}\n"
            f"Đang theo dõi: {following}\n"
            f"Ngày tạo tài khoản: {ngay_tao} (Lúc {gio_tao})"
        )

        client.replyMessage(
            Message(
                text=result, 
                style=MultiMsgStyle([
                    MessageStyle(offset=0, length=len(result), style="font", size=13, auto_format=False),
                    MessageStyle(offset=0, length=len(result), style="bold", auto_format=False)
                ])
            ), message_object, thread_id, thread_type
        )

    except requests.exceptions.RequestException as e:
        error_message = f"Đã xảy ra lỗi khi gọi API: {str(e)}"
        client.replyMessage(
            Message(
                text=error_message, 
                style=MultiMsgStyle([
                    MessageStyle(offset=0, length=len(error_message), style="font", size=13, auto_format=False),
                    MessageStyle(offset=0, length=len(error_message), style="bold", auto_format=False)
                ])
            ), message_object, thread_id, thread_type
        )
    except KeyError as e:
        error_message = f"Lỗi: {str(e)}"
        client.replyMessage(
            Message(
                text=error_message, 
                style=MultiMsgStyle([
                    MessageStyle(offset=0, length=len(error_message), style="font", size=13, auto_format=False),
                    MessageStyle(offset=0, length=len(error_message), style="bold", auto_format=False)
                ])
            ), message_object, thread_id, thread_type
        )
    except Exception as e:
        error_message = f"Đã xảy ra lỗi không xác định: {str(e)}"
        client.replyMessage(
            Message(
                text=error_message, 
                style=MultiMsgStyle([
                    MessageStyle(offset=0, length=len(error_message), style="font", size=13, auto_format=False),
                    MessageStyle(offset=0, length=len(error_message), style="bold", auto_format=False)
                ])
            ), message_object, thread_id, thread_type
        )

def get_mitaizl():
    return {
        'githubi4': handle_checkhost_command
    }
