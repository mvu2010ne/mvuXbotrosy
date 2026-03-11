import requests
import time
import urllib.parse
import os
import json
from zlapi.models import Message
from datetime import datetime

# Mô tả tập lệnh
des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🔍 Kiểm tra toàn diện trạng thái API với các phương thức HTTP GET, POST, PUT, DELETE, cùng khả năng upload, download, độ trễ và định dạng phản hồi.",
    'tính năng': [
        "🔗 Tự động kiểm tra kết nối với các phương thức HTTP (GET, POST, PUT, DELETE).",
        "📤 Kiểm tra khả năng upload file lên API (nếu hỗ trợ).",
        "📥 Kiểm tra khả năng download file từ API (nếu cung cấp nội dung hợp lệ).",
        "🟢 Xác định API có tồn tại và sử dụng được hay không.",
        "⏱ Đo độ trễ phản hồi của API cho từng phương thức.",
        "📋 Kiểm tra định dạng phản hồi JSON (nếu có).",
        "🚨 Kiểm tra giới hạn tốc độ (rate limit) nếu API cung cấp trong header.",
        "⚠️ Cung cấp gợi ý khắc phục lỗi chi tiết.",
        "📢 Gửi kết quả kiểm tra qua tin nhắn với định dạng dễ đọc."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh checkapi {api_url} [api_key] để kiểm tra API.",
        "📌 Ví dụ: checkapi https://api.example.com abc123xyz",
        "✅ Nhận kết quả kiểm tra toàn diện cho tất cả phương thức HTTP."
    ]
}

# Hàm kiểm tra định dạng JSON
def is_valid_json(response_text):
    try:
        json.loads(response_text)
        return True
    except json.JSONDecodeError:
        return False

# Hàm kiểm tra kết nối tới API với một phương thức HTTP
def check_api_connection(api_url, method, headers=None):
    methods = {
        "GET": requests.get,
        "POST": requests.post,
        "PUT": requests.put,
        "DELETE": requests.delete
    }
    if method.upper() not in methods:
        return {
            'status': False,
            'status_code': None,
            'latency': None,
            'headers': {},
            'json_valid': False,
            'rate_limit': {},
            'message': f'Phương thức {method} không được hỗ trợ.'
        }

    try:
        start_time = time.time()
        response = methods[method.upper()](api_url, headers=headers, timeout=10, allow_redirects=True)
        latency = (time.time() - start_time) * 1000  # Độ trễ tính bằng ms
        json_valid = is_valid_json(response.text) if response.text else False
        headers = dict(response.headers)

        # Kiểm tra rate limit trong header
        rate_limit_info = {
            'limit': headers.get('X-RateLimit-Limit', 'N/A'),
            'remaining': headers.get('X-RateLimit-Remaining', 'N/A'),
            'reset': headers.get('X-RateLimit-Reset', 'N/A')
        }

        return {
            'status': response.status_code == 200,
            'status_code': response.status_code,
            'latency': round(latency, 2),
            'headers': headers,
            'json_valid': json_valid,
            'rate_limit': rate_limit_info,
            'message': 'Kết nối thành công' if response.status_code == 200 else f'Mã lỗi: {response.status_code}'
        }
    except requests.exceptions.RequestException as e:
        return {
            'status': False,
            'status_code': None,
            'latency': None,
            'headers': {},
            'json_valid': False,
            'rate_limit': {},
            'message': f'Lỗi kết nối: {str(e)}'
        }

# Hàm kiểm tra khả năng upload
def check_upload_capability(api_url, headers=None):
    try:
        # Tạo file tạm để kiểm tra upload
        temp_file_path = "temp_test.txt"
        with open(temp_file_path, "w") as f:
            f.write("Kiểm tra upload API - " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        files = {'file': (os.path.basename(temp_file_path), open(temp_file_path, 'rb'), 'text/plain')}
        start_time = time.time()
        response = requests.post(api_url, files=files, headers=headers, timeout=10)
        latency = (time.time() - start_time) * 1000  # Độ trễ tính bằng ms
        os.remove(temp_file_path)  # Xóa file tạm

        return {
            'status': response.status_code == 200,
            'latency': round(latency, 2),
            'message': 'Upload thành công' if response.status_code == 200 else f'Upload thất bại, mã lỗi: {response.status_code}'
        }
    except Exception as e:
        return {
            'status': False,
            'latency': None,
            'message': f'Lỗi khi upload: {str(e)}'
        }

# Hàm kiểm tra khả năng download
def check_download_capability(api_url, headers=None):
    try:
        start_time = time.time()
        response = requests.get(api_url, headers=headers, timeout=10)
        latency = (time.time() - start_time) * 1000  # Độ trễ tính bằng ms
        content_type = response.headers.get('Content-Type', '')
        is_downloadable = response.status_code == 200 and ('application' in content_type or 'video' in content_type or 'image' in content_type)

        return {
            'status': is_downloadable,
            'latency': round(latency, 2),
            'message': 'Download thành công' if is_downloadable else f'Download thất bại, mã lỗi: {response.status_code} hoặc nội dung không phải file tải xuống.'
        }
    except Exception as e:
        return {
            'status': False,
            'latency': None,
            'message': f'Lỗi khi download: {str(e)}'
        }

# Hàm xử lý lệnh checkapi
def handle_checkapi_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản ứng "🔍" để xác nhận
    action = "🔍"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    # Lấy URL và API key (nếu có) từ tin nhắn
    parts = message.replace("checkapi ", "").strip().split()
    if not parts:
        client.sendMessage(Message(text="Vui lòng cung cấp URL API. Ví dụ: checkapi https://api.example.com [api_key]"),
                           thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    api_url = parts[0]
    api_key = parts[1] if len(parts) > 1 else None

    # Kiểm tra định dạng URL
    if not api_url.startswith(('http://', 'https://')):
        api_url = f"https://{api_url}"

    # Thiết lập header nếu có API key
    headers = {'Authorization': f'Bearer {api_key}'} if api_key else None

    # Danh sách các phương thức HTTP để kiểm tra tự động
    http_methods = ['GET', 'POST', 'PUT', 'DELETE']
    results = {}

    # Kiểm tra từng phương thức HTTP
    for method in http_methods:
        results[method] = check_api_connection(api_url, method, headers)

    # Kiểm tra upload
    upload_result = check_upload_capability(api_url, headers)

    # Kiểm tra download
    download_result = check_download_capability(api_url, headers)

    # Kiểm tra sự tồn tại và khả dụng của API
    api_exists = any(result['status'] for result in results.values()) or upload_result['status'] or download_result['status']

    # Gợi ý khắc phục nếu có lỗi
    suggestions = []
    if not any(result['status'] for result in results.values()):
        suggestions.append("🔎 Kiểm tra lại URL API hoặc thử với các endpoint cụ thể (ví dụ: /upload, /file).")
        if api_key:
            suggestions.append("🔑 Kiểm tra tính hợp lệ của API key.")
        else:
            suggestions.append("🔑 Thử cung cấp API key nếu API yêu cầu xác thực.")
    if not upload_result['status']:
        suggestions.append("📤 Đảm bảo API hỗ trợ upload file qua POST và kiểm tra quyền truy cập (API key nếu cần).")
    if not download_result['status']:
        suggestions.append("📥 Xác minh API cung cấp nội dung tải xuống hợp lệ (file, video, hình ảnh).")
    if not any(result['json_valid'] for result in results.values()):
        suggestions.append("📋 Nếu API trả về JSON, kiểm tra tài liệu API để đảm bảo endpoint đúng.")

    # Tạo thông điệp kết quả
    result_message = (
        f"📊 Kết quả kiểm tra API: {api_url}\n"
        f"🔑 API Key: {'Đã sử dụng' if api_key else 'Không cung cấp'}\n"
        f"🕒 Thời gian kiểm tra: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    )

    # Thêm kết quả cho từng phương thức HTTP
    for method in http_methods:
        result = results[method]
        result_message += (
            f"🔗 {method}:\n"
            f"   - Trạng thái: {'Thành công' if result['status'] else 'Thất bại'}\n"
            f"   - Mã trạng thái: {result['status_code'] or 'N/A'}\n"
            f"   - Độ trễ: {result['latency'] or 'N/A'} ms\n"
            f"   - Phản hồi JSON hợp lệ: {'Có' if result['json_valid'] else 'Không'}\n"
            f"   - Giới hạn tốc độ:\n"
            f"       + Giới hạn: {result['rate_limit']['limit']}\n"
            f"       + Còn lại: {result['rate_limit']['remaining']}\n"
            f"       + Đặt lại: {result['rate_limit']['reset']}\n"
            f"   - Thông điệp: {result['message']}\n\n"
        )

    # Thêm kết quả upload và download
    result_message += (
        f"📤 Upload:\n"
        f"   - Trạng thái: {'Thành công' if upload_result['status'] else 'Thất bại'}\n"
        f"   - Độ trễ: {upload_result['latency'] or 'N/A'} ms\n"
        f"   - Thông điệp: {upload_result['message']}\n\n"
        f"📥 Download:\n"
        f"   - Trạng thái: {'Thành công' if download_result['status'] else 'Thất bại'}\n"
        f"   - Độ trễ: {download_result['latency'] or 'N/A'} ms\n"
        f"   - Thông điệp: {download_result['message']}\n\n"
        f"🟢 API tồn tại và sử dụng được: {'Có' if api_exists else 'Không'}\n"
    )

    # Thêm gợi ý nếu có lỗi
    if suggestions:
        result_message += "\n📝 Gợi ý khắc phục:\n" + "\n".join(suggestions)

    # Gửi kết quả
    client.sendMessage(Message(text=result_message),
                       thread_id=thread_id, thread_type=thread_type, ttl=60000)

# Định nghĩa lệnh
def get_mitaizl():
    return {
        'checkapi': handle_checkapi_command
    }