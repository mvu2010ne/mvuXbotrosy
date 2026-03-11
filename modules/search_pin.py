import time
from zlapi.models import *
import requests
import urllib.parse
import os

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "📸 Tìm kiếm và gửi ảnh từ Pinterest dựa trên từ khóa người dùng cung cấp.",
    'tính năng': [
        "🔍 Tìm kiếm ảnh trên Pinterest bằng từ khóa và số lượng ảnh yêu cầu.",
        "📩 Gửi ảnh kèm thông báo số lượng ảnh đã gửi với định dạng màu sắc.",
        "⏳ Áp dụng thời gian chờ cho người dùng không phải admin để tránh spam.",
        "🔒 Giới hạn số lượng ảnh tối đa (10 cho người dùng thường, 50 cho admin).",
        "⚠️ Xử lý lỗi chi tiết khi gọi API, lưu ảnh hoặc gửi kết quả."
    ],
    'hướng dẫn sử dụng': [
        "📩 Sử dụng lệnh 'pin <từ khóa> <số lượng>' để tìm kiếm ảnh từ Pinterest.",
        "📌 Ví dụ: pin hoa hồng 5 để nhận 5 ảnh về hoa hồng.",
        "✅ Nhận kết quả ảnh kèm thông báo trạng thái ngay lập tức.",
        "⚠️ Lưu ý: Người dùng thường phải đợi giữa các lần sử dụng lệnh."
    ]
}


admin_ids = ['3299675674241805615']  
user_cooldowns = {}

def send_message_with_style(client, text, thread_id, thread_type, color="#db342e"):
    """
    Gửi tin nhắn với định dạng màu sắc.
    """
    base_length = len(text)
    adjusted_length = base_length + 355
    style = MultiMsgStyle([  # Áp dụng cả màu sắc và cỡ chữ
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
    client.send(Message(text=text, style=style), thread_id=thread_id, thread_type=thread_type, ttl=60000)

def handle_pin_command(message, message_object, thread_id, thread_type, author_id, client):
    current_time = time.time()
    cooldown_time = 0  

    if author_id not in admin_ids:
        if author_id in user_cooldowns:
            time_since_last_use = current_time - user_cooldowns[author_id]
            if time_since_last_use < cooldown_time:
                remaining_time = cooldown_time - time_since_last_use
                send_message_with_style(client, 
                    f"Bạn phải đợi {int(remaining_time // 60)} phút {int(remaining_time % 60)} giây nữa mới có thể dùng lại lệnh.", 
                    thread_id, thread_type)
                return

    if author_id not in admin_ids:
        user_cooldowns[author_id] = current_time

    text = message.split()

    if len(text) < 2 or not text[1].strip():
        send_message_with_style(client, 
            "❌ Vui lòng nhập nội dung cần tìm ảnh.\n pin <từ khóa> <số lượng>", 
            thread_id, thread_type)
        return

    # Gửi phản ứng ngay khi người dùng soạn đúng lệnh
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    # Phản hồi cho tin nhắn người dùng đã soạn lệnh (đã áp dụng style)
    search_terms = " ".join(text[1:])  # Lấy tất cả từ sau "pin"
    reply_message = f"Đang tìm kiếm [{search_terms}]...!"
    send_message_with_style(client, reply_message, thread_id, thread_type)

    try:
        try:
            num_images = int(text[-1])
            search_terms = " ".join(text[1:-1])
        except ValueError:
            num_images = 1
            search_terms = " ".join(text[1:])

        max_images = 10 if author_id not in admin_ids else 50
        if num_images > max_images:
            send_message_with_style(client, 
                f"❗ Bạn chỉ có thể yêu cầu tối đa {max_images} ảnh.", 
                thread_id, thread_type)
            num_images = max_images

        encoded_text = urllib.parse.quote(search_terms, safe='')
        apianh = f'https://subhatde.id.vn/pinterest?search={encoded_text}'

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }

        response = requests.get(apianh, headers=headers)
        response.raise_for_status()

        data = response.json()
        links = data.get('data', [])

        if not links:
            send_message_with_style(client, "❌ Không tìm thấy ảnh nào.", thread_id, thread_type)
            return

        selected_links = links[:num_images]
        image_paths = []
        for idx, link in enumerate(selected_links):
            if link:
                image_response = requests.get(link, headers=headers)
                image_path = f'modules/cache/temp_image_{idx}.jpeg'
                with open(image_path, 'wb') as f:
                    f.write(image_response.content)
                image_paths.append(image_path)

        # Khối gửi ảnh qua sendMultiLocalImage giữ nguyên không áp dụng style
        if all(os.path.exists(path) for path in image_paths):
            total_images = len(image_paths)
            gui = Message(text=f"✅ Đã gửi {total_images} ảnh tìm kiếm từ Pinterest.")
            client.sendMultiLocalImage(
                imagePathList=image_paths, 
                message=gui,
                thread_id=thread_id,
                thread_type=thread_type,
                width=1600,
                height=1600,
                ttl=200000
            )
            for path in image_paths:
                os.remove(path)
                
    except requests.exceptions.RequestException as e:
        send_message_with_style(client, 
            f"❌ Đã xảy ra lỗi khi gọi API: {str(e)}", 
            thread_id, thread_type)
    except KeyError as e:
        send_message_with_style(client, 
            f"❌ Dữ liệu từ API không đúng cấu trúc: {str(e)}", 
            thread_id, thread_type)
    except Exception as e:
        send_message_with_style(client, 
            f"❌ Đã xảy ra lỗi không xác định: {str(e)}", 
            thread_id, thread_type)
            
def get_mitaizl():
    return {
        'pin': handle_pin_command
    }