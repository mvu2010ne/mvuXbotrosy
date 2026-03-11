from zlapi.models import Message
import json
import urllib.parse
import os
import requests
import time

des = {
    'version': "1.4.1",
    'credits': "Nguyễn Đức Tài x TRBAYK (NGSON)",
    'description': "Làm nét hình ảnh gửi dạng img và link"
}

last_sent_image_url = None

def handle_lamnet_command(message, message_object, thread_id, thread_type, author_id, client):
    print("Bắt đầu xử lý lệnh 'img.enhance'")
    # Gửi phản ứng ngay khi người dùng soạn đúng lệnh
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    global last_sent_image_url

    msg_obj = message_object

    if msg_obj.msgType == "chat.photo":
        print("Đã nhận dạng được ảnh từ tin nhắn chat.photo")
        img_url = msg_obj.content.href.replace("\\/", "/")
        img_url = urllib.parse.unquote(img_url)
        print(f"URL ảnh gốc: {img_url}")
        last_sent_image_url = img_url
        send_image_link(img_url, thread_id, thread_type, client)

    elif msg_obj.quote:
        print("Đang xử lý ảnh được reply từ tin nhắn trích dẫn")
        attach = msg_obj.quote.attach
        if attach:
            try:
                attach_data = json.loads(attach)
                print("Phân tích JSON thành công từ dữ liệu đính kèm")
            except json.JSONDecodeError as e:
                print(f"Lỗi khi phân tích JSON: {str(e)}")
                send_error_message(thread_id, thread_type, client, "Lỗi khi phân tích dữ liệu ảnh.")
                return

            image_url = attach_data.get('hdUrl') or attach_data.get('href')
            if image_url:
                print(f"Tìm thấy URL ảnh từ dữ liệu trích dẫn: {image_url}")
                send_image_link(image_url, thread_id, thread_type, client)
            else:
                print("Không tìm thấy URL ảnh trong dữ liệu trích dẫn")
                send_error_message(thread_id, thread_type, client)
        else:
            print("Không có dữ liệu đính kèm trong tin nhắn trích dẫn")
            send_error_message(thread_id, thread_type, client)

    else:
        print("Tin nhắn không có ảnh hoặc trích dẫn ảnh hợp lệ")
        send_error_message(thread_id, thread_type, client)

def handle_4k_command(image_url, thread_id, thread_type, client):
    if not image_url:
        print("URL ảnh không hợp lệ")
        send_error_message(thread_id, thread_type, client, "URL ảnh không hợp lệ.")
        return

    # Tạo API URL với tham số link được encode
    encoded_url = urllib.parse.quote(image_url)
    api_url = f"https://api.sumiproject.net/lamnet?link={encoded_url}"
    print(f"API URL: {api_url}")

    client.send(Message(text="Đang xử lý ảnh... Vui lòng đợi."), thread_id=thread_id, thread_type=thread_type)

    anhnet = None
    for attempt in range(1, 4):
        print(f"Thử gọi API lần {attempt}...")
        try:
            response = requests.get(api_url)
            response.raise_for_status()
            print("API trả về kết quả thành công")
            
            # In nội dung phản hồi để kiểm tra
            print(f"Nội dung phản hồi: {response.text}")

            # Kiểm tra phản hồi không rỗng trước khi phân tích JSON
            if response.text.strip():
                data = response.json()
                anhnet = data.get('upscaled_image', '')
                if anhnet:
                    print("Nhận được ảnh đã làm nét từ API")
                    break
                else:
                    print("Không nhận được ảnh đã làm nét từ API, tiếp tục thử lại...")
            else:
                print("Phản hồi từ API rỗng, tiếp tục thử lại...")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 500:
                error_text = f"Lỗi server: {e}"
                print(error_text)
                client.send(Message(text=error_text), thread_id=thread_id, thread_type=thread_type)
                send_error_message(thread_id, thread_type, client, "Lỗi từ máy chủ. Vui lòng thử lại sau.")
                return
            else:
                error_text = f"Lỗi khi gọi API: {str(e)}"
                print(error_text)
                send_error_message(thread_id, thread_type, client, "Lỗi không xác định khi gọi API.")
                return
        except requests.exceptions.RequestException as e:
            error_text = f"Lỗi kết nối: {str(e)}"
            print(error_text)
            send_error_message(thread_id, thread_type, client, "Lỗi kết nối đến máy chủ.")
            return
        
        time.sleep(1)

    if anhnet:
        print("Gửi ảnh đã làm nét tới người dùng")
        send_image_with_link(anhnet, "file ảnh đã làm nét của bạn đây", thread_id, thread_type, client)
    else:
        print("Không thể làm nét ảnh sau 3 lần thử")
        send_error_message(thread_id, thread_type, client, "Không thể làm nét ảnh.")

def send_image_with_link(anhnet, fileName, thread_id, thread_type, client):
    if anhnet:
        print(f"Đang gửi file ảnh: {anhnet}")
        client.sendRemoteFile(
            fileUrl=anhnet,
            thread_id=thread_id,
            thread_type=thread_type,
            fileName=fileName,
            fileSize=None,
            extension="JPEG"
        )
    else:
        print("Không có file ảnh để gửi")
        send_error_message(thread_id, thread_type, client, "Không thể gửi file.")

def send_error_message(thread_id, thread_type, client, error_message="Vui lòng reply ảnh hoặc link ảnh cần làm nét."):
    print(f"Gửi thông báo lỗi: {error_message}")
    client.send(Message(text=error_message), thread_id=thread_id, thread_type=thread_type)

def send_image_link(image_url, thread_id, thread_type, client):
    print(f"Bắt đầu xử lý ảnh với URL: {image_url}")
    handle_4k_command(image_url, thread_id, thread_type, client)

def get_mitaizl():
    return {
        'img_enhance': handle_lamnet_command
    }
