import requests
from zlapi.models import Message
import json

CATBOX_PHPSESSID = 'ce9f3eddc250f6a5008ccadcd'

def handle_upload_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        if hasattr(message_object, 'msgType') and message_object.msgType in ["chat.photo", "chat.video"]:
            media_url = message_object.content.get('href', '').replace("\\/", "/")
            if not media_url:
                send_error_message("Không tìm thấy liên kết ảnh/video.", thread_id, thread_type, client)
                return

            catbox_link = upload_to_catbox(media_url)
            if catbox_link:
                send_success_message(f"Thành Công: {catbox_link}", thread_id, thread_type, client)
            else:
                send_error_message("Lỗi khi upload ảnh/video lên Catbox.", thread_id, thread_type, client)

        elif getattr(message_object, 'quote', None):
            attach = getattr(message_object.quote, 'attach', None)
            if attach:
                try:
                    attach_data = json.loads(attach)
                except json.JSONDecodeError:
                    send_error_message("Phân tích JSON thất bại.", thread_id, thread_type, client)
                    return

                media_url = attach_data.get('hdUrl') or attach_data.get('href')
                if media_url:
                    catbox_link = upload_to_catbox(media_url)
                    if catbox_link:
                        send_success_message(f"Ảnh/video đã được upload: {catbox_link}", thread_id, thread_type, client)
                    else:
                        send_error_message("Lỗi khi upload ảnh/video lên Catbox.", thread_id, thread_type, client)
                else:
                    send_error_message("Không tìm thấy liên kết trong file đính kèm.", thread_id, thread_type, client)
            else:
                send_error_message("Không tìm thấy file đính kèm.", thread_id, thread_type, client)
        else:
            send_error_message("Vui lòng gửi ảnh/video hoặc phản hồi file đính kèm.", thread_id, thread_type, client)
    except Exception as e:
        print(f"Lỗi khi xử lý lệnh upload: {str(e)}")
        send_error_message("Đã xảy ra lỗi khi xử lý lệnh.", thread_id, thread_type, client)


def upload_to_catbox(media_url):
    cookies = {'PHPSESSID': CATBOX_PHPSESSID}
    headers = {
        'authority': 'catbox.moe',
        'accept': '*/*',
        'accept-language': 'vi-VN,vi;q=0.9,zh-CN;q=0.8,zh;q=0.7,en-AU;q=0.6,en;q=0.5,fr-FR;q=0.4,fr;q=0.3,en-US;q=0.2',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://catbox.moe',
        'referer': 'https://catbox.moe/',
        'sec-ch-ua': '"Not:A-Brand";v="99", "Chromium";v="112"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Linux; Android 12; SM-A037F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }
    data = {'reqtype': 'urlupload', 'userhash': '', 'url': media_url}
    try:
        response = requests.post('https://catbox.moe/user/api.php', cookies=cookies, headers=headers, data=data)
        if response.status_code == 200:
             return response.text.strip()
        else:
            print(f"Lỗi API Catbox: {response.status_code} - {response.text}")
            return None
    except requests.RequestException as e:
        print(f"Lỗi khi gọi API Catbox: {str(e)}")
        return None



def send_success_message(message, thread_id, thread_type, client):
    success_message = Message(text=message)
    try:
        client.send(success_message, thread_id, thread_type)
    except Exception as e:
        print(f"Lỗi khi gửi tin nhắn thành công: {str(e)}")

def send_error_message(message, thread_id, thread_type, client):
    error_message = Message(text=message)
    try:
        client.send(error_message, thread_id, thread_type)
    except Exception as e:
        print(f"Lỗi khi gửi tin nhắn lỗi: {str(e)}")

def get_mitaizl():
    return {
        'up.catbox2': handle_upload_command
    }