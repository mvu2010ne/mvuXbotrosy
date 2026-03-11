from zlapi.models import Message
import json
import urllib.parse
import requests
import os
import re

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Scan QRCODE",
    'tính năng': [
        "📷 Quét mã QR từ ảnh do người dùng cung cấp.",
        "🔍 Kiểm tra và xử lý ảnh được gửi kèm tin nhắn hoặc được quote lại.",
        "📨 Gửi phản hồi với nội dung đã quét từ mã QR.",
        "🔔 Thông báo lỗi cụ thể nếu có vấn đề xảy ra khi quét mã QR."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh scanqr kèm ảnh QR code để quét mã QR.",
        "📌 Ví dụ: scanqr và gửi kèm ảnh QR code hoặc reply lại ảnh QR code.",
        "✅ Nhận thông báo trạng thái và kết quả quét mã QR ngay lập tức."
    ]
}

last_sent_image_url = None

def handle_scanqr_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản ứng ngay khi người dùng soạn đúng lệnh
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    global last_sent_image_url
    msg_obj = message_object

    if msg_obj.msgType == "chat.photo":
        img_url = urllib.parse.unquote(msg_obj.content.href.replace("\\/", "/"))
        last_sent_image_url = img_url
        handle_scan_command(img_url, thread_id, thread_type, client, message_object)
    elif msg_obj.quote:
        attach = msg_obj.quote.attach
        if attach:
            try:
                attach_data = json.loads(attach)
                image_url = attach_data.get('hdUrl') or attach_data.get('href')
                if image_url:
                    handle_scan_command(image_url, thread_id, thread_type, client, message_object)
                else:
                    send_error_message(thread_id, thread_type, client)
            except json.JSONDecodeError as e:
                print(f"Lỗi JSON: {str(e)}")
                send_error_message(thread_id, thread_type, client)
        else:
            send_error_message(thread_id, thread_type, client)
    else:
        send_error_message(thread_id, thread_type, client)

def handle_scan_command(image_url, thread_id, thread_type, client, message_object):
    if image_url:
        try:
            # Tải ảnh về local
            print(f"Downloading image from: {image_url}")
            image_response = requests.get(image_url, timeout=10)
            image_response.raise_for_status()
            image_path = "modules/cache/temp_qr.jpg"
            with open(image_path, 'wb') as f:
                f.write(image_response.content)

            # Gửi file ảnh lên API
            api_url = "http://api.qrserver.com/v1/read-qr-code/"
            client.replyMessage(Message(text="Đang tiến hành scan qrcode... vui lòng đợi"), message_object, thread_id=thread_id, thread_type=thread_type)
            with open(image_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(api_url, files=files, timeout=10)
                response.raise_for_status()
                print(f"API response: {response.text}")
                data = response.json()

            if os.path.exists(image_path):
                os.remove(image_path)

            if data and 'symbol' in data[0] and data[0]['symbol'][0].get('data'):
                datascan = data[0]['symbol'][0]['data']
                # Chuyển đổi URL nếu là link zaloapp.com
                if datascan.startswith("https://zaloapp.com/qr/g/"):
                    match = re.match(r"https://zaloapp\.com/qr/g/([^?]+)", datascan)
                    if match:
                        group_id = match.group(1)
                        datascan = f"https://zalo.me/g/{group_id}"
            else:
                datascan = 'Không thấy dữ liệu trong mã QR.'
            client.replyMessage(Message(text=f"Nội dung đã scan QRCODE:\n {datascan}"), message_object, thread_id=thread_id, thread_type=thread_type, ttl=30000)

        except requests.RequestException as e:
            print(f"Lỗi khi xử lý ảnh hoặc API: {str(e)}")
            client.replyMessage(Message(text=f"Lỗi: {str(e)}"), message_object, thread_id=thread_id, thread_type=thread_type, ttl=30000)
        except Exception as e:
            print(f"Lỗi không xác định: {str(e)}")
            client.replyMessage(Message(text=f"Lỗi không xác định: {str(e)}"), message_object, thread_id=thread_id, thread_type=thread_type, ttl=30000)
    else:
        send_error_message(thread_id, thread_type, client, "Không tìm thấy URL ảnh để quét.")

def send_error_message(thread_id, thread_type, client, error_message="Vui lòng reply ảnh QRCODE cần scan"):
    client.send(Message(text=error_message), thread_id=thread_id, thread_type=thread_type, ttl=30000)

def get_mitaizl():
    return {
        'scanqr': handle_scanqr_command
    }