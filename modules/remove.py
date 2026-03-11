from zlapi.models import Message, ThreadType
import requests
import urllib.parse
from io import BytesIO
import os
import tempfile
import json
from PIL import Image

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Xóa phông ảnh khi reply vào tin nhắn chứa ảnh và upload lên Uguu.se.",
    'tính năng': [
        "🖼️ Xóa phông ảnh bằng API remove.bg khi reply vào tin nhắn ảnh.",
        "📨 Gửi ảnh đã xóa phông với nền trong suốt kèm liên kết Uguu.se.",
        "🔗 Upload ảnh lên Uguu.se để chia sẻ liên kết công khai.",
        "🔄 Xử lý lệnh xóa phông và gửi phản hồi trạng thái.",
        "🔔 Thông báo lỗi cụ thể nếu có vấn đề xảy ra khi xử lý ảnh."
    ],
    'hướng dẫn sử dụng': [
        "📩 Reply vào tin nhắn chứa ảnh và gửi lệnh remove để xóa phông.",
        "📌 Ví dụ: Reply vào ảnh và gõ remove để nhận ảnh và liên kết Uguu.se.",
        "✅ Nhận ảnh với nền trong suốt và liên kết Uguu.se ngay lập tức."
    ]
}

UGUU_API_URL = "https://uguu.se/upload.php"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def get_content_type(url):
    """Kiểm tra Content-Type của URL"""
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        return response.headers.get('Content-Type', '')
    except Exception as e:
        print(f"Debug: Lỗi khi lấy Content-Type: {e}")
        return ''

def upload_to_uguu(file_path):
    """Upload tệp cục bộ lên Uguu.se"""
    print(f"Debug: Uploading to Uguu.se: {file_path}")
    try:
        # Kiểm tra kích thước tệp
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
        if file_size > 100:
            print(f"Debug: Tệp vượt quá 100MB ({file_size:.2f}MB), Uguu.se không hỗ trợ.")
            return None

        with open(file_path, 'rb') as f:
            files = {'files[]': (os.path.basename(file_path), f, 'image/png')}
            data = {'randomname': 'true'}  # Yêu cầu tên ngẫu nhiên
            response = requests.post(UGUU_API_URL, headers=headers, files=files, data=data, timeout=30)
            if response.status_code == 200:
                result = response.json()
                print(f"Debug: Uguu.se API response: {result}")
                if result.get('success'):
                    file_url = result['files'][0]['url']
                    print(f"Debug: Uploaded to Uguu.se: {file_url}")
                    return file_url
                else:
                    print(f"Debug: Uguu.se API error: {result.get('description', 'No error details')}")
                    return None
            else:
                print(f"Debug: Uguu.se API error: {response.status_code} - {response.text}")
                return None
    except Exception as e:
        print(f"Debug: Lỗi khi gọi API Uguu.se: {str(e)}")
        return None

def send_error_message(message, thread_id, thread_type, client):
    """Gửi thông báo lỗi"""
    error_message = Message(text=message)
    try:
        client.sendMessage(error_message, thread_id, thread_type, ttl=60000)
    except Exception as e:
        print(f"Debug: Lỗi khi gửi tin nhắn lỗi: {str(e)}")

def handle_remove_background_command(message, message_object, thread_id, thread_type, author_id, client):
    if "remove" in message.lower():
        action = "✅"  # Biểu tượng phản ứng
        try:
            client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
        except Exception as e:
            print(f"Debug: Error sending reaction: {e}")
    
    # Kiểm tra nếu tin nhắn có quote
    print(f"Debug: Checking quote - quote: {getattr(message_object, 'quote', None)}")
    if not message_object.quote:
        error_message = Message(
            text="⭕ Vui lòng reply vào một tin nhắn chứa ảnh để xóa phông!"
        )
        client.sendMessage(error_message, thread_id, thread_type, ttl=60000)
        return
    
    # Lấy thông tin ảnh từ quote.attach
    attach = message_object.quote.attach
    print(f"Debug: Quote attach: {attach}")
    if not attach:
        error_message = Message(
            text="⭕ Tin nhắn reply không chứa ảnh hoặc nội dung hợp lệ!"
        )
        client.sendMessage(error_message, thread_id, thread_type, ttl=60000)
        return
    
    try:
        attach_data = json.loads(attach) if isinstance(attach, str) else attach
        print(f"Debug: Parsed attach_data: {attach_data}")
        image_url = attach_data.get('hdUrl') or attach_data.get('normalUrl') or attach_data.get('oriUrl') or attach_data.get('href')
        if not image_url:
            raise KeyError("Không tìm thấy URL ảnh trong quote.attach")
        image_url = urllib.parse.unquote(image_url.replace("\\/", "/"))  # Chuẩn hóa URL
        print(f"Debug: Image URL: {image_url}")
    except json.JSONDecodeError as e:
        send_error_message(f"⭕ Lỗi phân tích dữ liệu ảnh: {str(e)}", thread_id, thread_type, client)
        return
    except KeyError as e:
        send_error_message(f"⭕ Lỗi: Không thể lấy URL ảnh từ tin nhắn reply: {str(e)}", thread_id, thread_type, client)
        return
    
    # Kiểm tra Content-Type của URL
    content_type = get_content_type(image_url)
    print(f"Debug: Content-Type: {content_type}")
    if not content_type.startswith('image/'):
        send_error_message(f"⭕ URL không phải ảnh hợp lệ: Content-Type {content_type}", thread_id, thread_type, client)
        return
    
    try:
        # Gọi API remove.bg để xóa phông
        remove_bg_url = "https://api.remove.bg/v1.0/removebg"
        headers_api = {
            "X-Api-Key": "jb6bFsDrZFQb2shDFE9UrVLp",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124",
            "Accept": "image/png,image/jpeg,*/*;q=0.8"
        }
        response = requests.post(
            remove_bg_url,
            headers=headers_api,
            data={"image_url": image_url, "size": "auto"}
        )
        response.raise_for_status()
        
        # Tối ưu ảnh với PIL để giữ nền trong suốt
        image = Image.open(BytesIO(response.content))
        if image.mode != 'RGBA':
            image = image.convert('RGBA')  # Đảm bảo có alpha channel
        # Cắt viền dư thừa (nếu có)
        bbox = image.getbbox()
        if bbox:
            image = image.crop(bbox)
        width, height = image.size
        print(f"Debug: Image size after crop: {width}x{height}")
        
        # Lưu ảnh vào tệp tạm dưới dạng PNG
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
            image.save(temp_file.name, format="PNG", optimize=True)
            temp_file_path = temp_file.name
            print(f"Debug: Temp file saved at: {temp_file_path}")
        
        # Upload ảnh lên Uguu.se
        uguu_link = upload_to_uguu(temp_file_path)
        if not uguu_link:
            send_error_message("⭕ Lỗi khi upload ảnh lên Uguu.se.", thread_id, thread_type, client)
            os.unlink(temp_file_path)
            return
        
        # Gửi ảnh bằng sendLocalImage với liên kết Uguu.se
        client.sendLocalImage(
            imagePath=temp_file_path,
            thread_id=thread_id,
            thread_type=thread_type,
            width=width,
            height=height,
            message=Message(text=f"Để tải ảnh không có nền trắng vui lòng bấm vào link: {uguu_link}"),
            ttl=60000
        )
        
        # Xóa tệp tạm
        os.unlink(temp_file_path)
        
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        if status_code == 403:
            send_error_message(
                "⭕ Lỗi API remove.bg: Key không hợp lệ hoặc hết quota. Tạo key mới tại https://www.remove.bg/api.",
                thread_id, thread_type, client
            )
        elif status_code == 429:
            send_error_message(
                "⭕ Lỗi API remove.bg: Vượt giới hạn lượt gọi. Vui lòng đợi hoặc nâng cấp tài khoản.",
                thread_id, thread_type, client
            )
        else:
            send_error_message(f"⭕ Lỗi API remove.bg: {str(e)}", thread_id, thread_type, client)
        print(f"Debug: HTTPError: {e}")
    except requests.exceptions.RequestException as e:
        send_error_message(f"⭕ Lỗi khi gọi API remove.bg: {str(e)}", thread_id, thread_type, client)
        print(f"Debug: RequestException: {e}")
    except Exception as e:
        send_error_message(f"⭕ Lỗi không xác định: {str(e)}", thread_id, thread_type, client)
        print(f"Debug: Exception: {e}")
        if 'temp_file_path' in locals():
            os.unlink(temp_file_path)  # Xóa tệp tạm nếu có lỗi

# Đăng ký các lệnh
def get_mitaizl():
    return {
        'remove': handle_remove_background_command
    }