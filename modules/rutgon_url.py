import requests
import urllib.parse
import json
import re
from zlapi.models import Message

# Thông tin mô tả lệnh
des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🔗 Rút gọn liên kết bằng API subhatde.id.vn/tinyurl.",
    'tính năng': [
        "🔗 Rút gọn URL từ tin nhắn trực tiếp hoặc tin nhắn trích dẫn.",
        "✅ Trả về liên kết đã rút gọn từ subhatde.id.vn.",
        "⚠️ Thông báo lỗi chi tiết nếu rút gọn thất bại."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh short.url kèm URL hoặc trích dẫn tin nhắn chứa URL.",
        "📌 Ví dụ: short.url https://example.com hoặc trích dẫn tin nhắn chứa URL.",
        "✅ Nhận liên kết đã rút gọn nếu thành công."
    ]
}

TINYURL_API_URL = 'https://subhatde.id.vn/tinyurl?url='

# Regex để tìm URL trong chuỗi
URL_REGEX = r'(https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*(?:/[^?\s]*(?:\?[^?\s]*)*)?)'

def extract_url(text):
    """Trích xuất URL từ chuỗi văn bản."""
    matches = re.findall(URL_REGEX, text)
    return matches[0] if matches else None

def is_valid_url(url):
    """Kiểm tra xem chuỗi có phải là URL hợp lệ không."""
    return bool(re.match(URL_REGEX, url.strip()))

def handle_short_url_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        # Trích xuất URL từ tin nhắn
        url = None
        if hasattr(message_object, 'content'):
            if isinstance(message_object.content, str):
                # Tách URL từ chuỗi lệnh (bỏ phần "short.url")
                content = message_object.content.strip()
                print(f"Content của message_object: {content}")
                if content.startswith('short.url'):
                    content = content.replace('short.url', '', 1).strip()
                    url = extract_url(content)
                else:
                    url = extract_url(content)
            elif isinstance(message_object.content, dict):
                url = message_object.content.get('text', '').strip()

        # Kiểm tra tin nhắn trích dẫn nếu không có URL trực tiếp
        if not url and getattr(message_object, 'quote', None):
            quote = message_object.quote
            if hasattr(quote, 'content'):
                if isinstance(quote.content, str):
                    url = extract_url(quote.content.strip())
                elif isinstance(quote.content, dict):
                    url = quote.content.get('text', '').strip()

        # Kiểm tra URL hợp lệ
        if not url or not is_valid_url(url):
            send_error_message("Vui lòng cung cấp URL hợp lệ hoặc trích dẫn tin nhắn chứa URL.", thread_id, thread_type, client)
            return

        # Đảm bảo URL có giao thức
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        # Rút gọn URL
        print(f"Đang xử lý URL: {url}")
        shortened_url = shorten_url(url)
        if shortened_url:
            send_success_message(f"Liên kết đã rút gọn: {shortened_url}", thread_id, thread_type, client)
        else:
            send_error_message("Lỗi khi rút gọn URL. Vui lòng thử lại sau.", thread_id, thread_type, client)

    except Exception as e:
        print(f"Lỗi khi xử lý lệnh rút gọn URL: {str(e)}")
        send_error_message(f"Đã xảy ra lỗi: {str(e)}", thread_id, thread_type, client)

def shorten_url(url):
    """Rút gọn URL bằng API subhatde.id.vn."""
    print(f"Bắt đầu rút gọn URL: {url}")
    try:
        # Mã hóa URL và tạo yêu cầu API
        api_url = f"{TINYURL_API_URL}{urllib.parse.quote(url)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
            'Content-Type': 'application/json'
        }
        print(f"Gửi yêu cầu GET đến: {api_url}")
        
        # Gửi yêu cầu với timeout và tiêu đề
        response = requests.get(api_url, headers=headers, timeout=10)
        print(f"Mã trạng thái: {response.status_code}")
        print(f"Nội dung phản hồi từ API: {response.text}")

        # Kiểm tra phản hồi
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"Phản hồi JSON: {json.dumps(result, indent=2)}")
                shortened_url = result.get('url')
                if shortened_url:
                    print(f"Rút gọn thành công: {shortened_url}")
                    return shortened_url
                else:
                    print("Không tìm thấy trường 'url' trong phản hồi JSON.")
                    return None
            except json.JSONDecodeError as e:
                print(f"Lỗi phân tích JSON: {str(e)}")
                print(f"Phản hồi gốc: {response.text}")
                return None
        else:
            print(f"Yêu cầu API thất bại, mã trạng thái: {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"Lỗi khi gọi API: {str(e)}")
        return None
    except Exception as e:
        print(f"Lỗi không xác định trong quá trình rút gọn: {str(e)}")
        return None

def send_success_message(message, thread_id, thread_type, client):
    """Gửi tin nhắn thành công."""
    print(f"Gửi tin nhắn thành công: {message}")
    success_message = Message(text=message)
    try:
        client.send(success_message, thread_id, thread_type)
    except Exception as e:
        print(f"Lỗi khi gửi tin nhắn thành công: {str(e)}")

def send_error_message(message, thread_id, thread_type, client):
    """Gửi tin nhắn lỗi."""
    print(f"Gửi tin nhắn lỗi: {message}")
    error_message = Message(text=message)
    try:
        client.send(error_message, thread_id, thread_type)
    except Exception as e:
        print(f"Lỗi khi gửi tin nhắn lỗi: {str(e)}")

def get_mitaizl():
    """Trả về danh sách lệnh."""
    return {
        'rutgon.url': handle_short_url_command
    }