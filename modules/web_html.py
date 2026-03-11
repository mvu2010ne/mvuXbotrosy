import os
import requests
import logging
from zlapi.models import *
from config import ADMIN
from urllib.parse import urlparse
import requests.exceptions
import json


des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🔍 Lấy mã HTML của trang web và gửi dưới dạng file.",
    'tính năng': [
        "📥 Tải mã HTML từ URL được cung cấp.",
        "📤 Tạo liên kết mock để gửi file HTML qua tin nhắn.",
        "✅ Kiểm tra quyền admin trước khi thực hiện lệnh.",
        "⚠️ Thông báo lỗi nếu URL không hợp lệ hoặc gặp vấn đề khi tải."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh web.html <url> để lấy mã HTML của trang web.",
        "📌 Ví dụ: web.html https://example.com",
        "✅ Nhận file HTML qua tin nhắn nếu là admin."
    ]
}


def get_html_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text, None
    except requests.RequestException as e:
        logging.error(f"Lỗi khi lấy HTML từ {url}: {e}")
        return None, f"Lỗi khi tải trang web: {e}"

def create_mock_link(code_content, file_name):
    try:
        data = {
            "status": 200,
            "content": code_content,
            "content_type": "text/plain",
            "charset": "UTF-8",
            "secret": "Kaito Kid",
            "expiration": "never"
        }
        response = requests.post("https://api.mocky.io/api/mock", json=data)
        response.raise_for_status()
        response_data = response.json()
        return response_data.get("link"), None
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error when creating mock link: {e}")
        return None, f"Lỗi mạng: {e}"
    except json.JSONDecodeError as e:
        logging.error(f"Json decode error when creating mock link: {e}")
        return None, f"Lỗi Json Decode: {e}"
    except Exception as e:
        logging.error(f"Error when creating mock link: {e}")
        return None, f"Lỗi khi tạo mock link: {e}"

def send_message(client, thread_id, thread_type, message_content, ttl=None):
    try:
        client.sendMessage(
            Message(text=message_content),
            thread_id=thread_id,
            thread_type=thread_type,
            ttl=ttl
        )
    except Exception as e:
       logging.error(f"Lỗi khi gửi tin nhắn: {e}")

def handle_gethtml_command(message, message_object, thread_id, thread_type, author_id, client):
    if not is_admin(author_id):
         send_message(client, thread_id, thread_type, "Bạn không có quyền thực hiện lệnh này.")
         return

    parts = message.split(' ', 1)
    if len(parts) != 2:
        send_message(client, thread_id, thread_type, "Lệnh không đúng định dạng. Vui lòng sử dụng: web.html <url>")
        return

    _, url = parts
    url = url.strip()

    if not url:
         send_message(client, thread_id, thread_type, "URL không được để trống.")
         return
    
    try:
        parsed_url = urlparse(url)
        if not all([parsed_url.scheme, parsed_url.netloc]):
             send_message(client, thread_id, thread_type, "URL không hợp lệ.")
             return
    except Exception as e:
        send_message(client, thread_id, thread_type, f"URL không hợp lệ: {e}")
        return
        

    html_content, error = get_html_content(url)
    if error:
       send_message(client, thread_id, thread_type, f"Đã có lỗi xảy ra: {error}")
       return
    
    file_name = f"{parsed_url.netloc}.html"
    
    try:
        send_message(client, thread_id, thread_type, f"Đang xử lý...")
        
        mock_url, error = create_mock_link(html_content, file_name)
        if error:
           send_message(client, thread_id, thread_type, f"Đã có lỗi xảy ra: {error}")
           return
        
        extension = file_name.split(".")[-1].upper() if "." in file_name else "HTML"
        logging.info(f"Sending HTML file: {file_name}, url: {url}, mock_url: {mock_url}, extension: {extension}")


        client.sendRemoteFile(
            fileUrl=mock_url,
            fileName=file_name,
            thread_id=thread_id,
            thread_type=thread_type,
            fileSize=None,
            extension=extension
        )
            
        send_message(client, thread_id, thread_type, f"Đã gửi HTML của trang web: {url}")
        
    except Exception as e:
       send_message(client, thread_id, thread_type, f"Có lỗi khi gửi file HTML: {e}")
       logging.error(f"Error when sending HTML file: {e}")

                
def get_mitaizl():
    return {
        'web.html': handle_gethtml_command
    }