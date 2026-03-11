import requests
import os
from datetime import datetime
from zlapi.models import Message, ZaloAPIException
from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO

# Thông tin mô tả
des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Lệnh troll 'bàn thờ' khi tag ai đó",
    'tính năng': [
        "🔍 Chỉ admin mới có quyền sử dụng lệnh",
        "🎨 Tạo ảnh bàn thờ có avatar và tên người bị tag",
        "🖼️ Hỗ trợ bo góc avatar để hiển thị đẹp hơn",
        "📩 Gửi tin nhắn nhắc nếu không tag ai",
        "🗑️ Tự động xóa ảnh sau khi gửi"
    ],
    'hướng dẫn sử dụng': [
        "📩 Nhập lệnh 'bantho' kèm tag người cần troll.",
        "📌 Ví dụ: bantho @username để troll người dùng được tag.",
        "✅ Nhận thông báo trạng thái và kết quả ngay lập tức."
    ]
}

# Danh sách ID admin được phép sử dụng lệnh
ADMIN_IDS = ["3299675674241805615", "8476100371735921782"]  # Thay đổi theo ID admin của bạn

# Hàm tạo ảnh
def create_canvas(user_data):
    # Mở ảnh nền
    background_image = Image.open("bantho.png")
    draw = ImageDraw.Draw(background_image)

    # Kích thước ảnh nền
    bg_width, bg_height = background_image.size

    # Lấy avatar từ URL hoặc sử dụng ảnh mặc định
    avatar_url = user_data.get('avatar')
    if avatar_url:
        response = requests.get(avatar_url)
        avatar_image = Image.open(BytesIO(response.content)).convert("RGB")
    else:
        avatar_image = Image.open("default_avatar.jpg").convert("RGB")

    # Điều chỉnh kích thước avatar
    avatar_size = (110, 145)
    avatar_image = ImageOps.fit(avatar_image, avatar_size, centering=(0.5, 0.5))

    # Bo góc avatar
    mask = Image.new("L", avatar_size, 255)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0) + avatar_size, fill=255)
    avatar_image.putalpha(mask)

    # Vị trí đặt avatar
    avatar_x = bg_width - avatar_size[0] - 240
    avatar_y = (bg_height - avatar_size[1]) // 6 - 5
    background_image.paste(avatar_image, (avatar_x, avatar_y), avatar_image)

    # Thêm thông tin (chỉnh font và vị trí chữ theo kích thước ảnh nền)
    fontc = "UTM AvoBold.ttf"
    font_size = int(bg_height * 0.05)
    font_title = ImageFont.truetype(fontc, font_size)
    font_info = ImageFont.truetype(fontc, font_size + 10)

    # Nội dung text
    text_title = "Chia buồn cùng gia đình:"
    text_info = user_data.get('displayName', 'N/A')

    # Vị trí dọc không thay đổi
    title_y = int(bg_height * 0.8)
    info_y = title_y + font_size + 10

    # Tính toán độ rộng của từng dòng chữ sử dụng textbbox
    title_bbox = draw.textbbox((0, 0), text_title, font=font_title)
    title_width = title_bbox[2] - title_bbox[0]

    info_bbox = draw.textbbox((0, 0), text_info, font=font_info)
    info_width = info_bbox[2] - info_bbox[0]

    # Tính vị trí x để căn giữa
    title_x = (bg_width - title_width) // 2
    info_x = (bg_width - info_width) // 2

    # Vẽ text lên ảnh nền
    draw.text((title_x, title_y), text_title, font=font_title, fill=(255, 0, 0))
    draw.text((info_x, info_y), text_info, font=font_info, fill=(255, 0, 0))

    # Lưu ảnh
    canvas_path = "output_canvas.png"
    background_image.save(canvas_path)
    return canvas_path

# Hàm xử lý người dùng được gắn thẻ
def handle_user_info(message, message_object, thread_id, thread_type, author_id, client):
    """
    Xử lý thông tin người dùng được gắn thẻ và tạo ảnh.
    Chỉ cho phép admin sử dụng lệnh này.
    """
    # Kiểm tra quyền admin
    if author_id not in ADMIN_IDS:
        error_message = Message(text="Bạn không có quyền sử dụng lệnh này!")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=10000)
        return

    try:
        # Gửi phản ứng ngay khi nhận lệnh hợp lệ
        action = "✅"
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
        
        # Nếu người dùng chỉ nhập "bàn thờ" (không tag ai) thì chỉ gửi tin nhắn nhắc nhở
        if not message_object.mentions:
            reminder_message = "Chị Minh Vũ Shinn Cte hãy tag con chó để em cúng nó"
            client.sendMessage(Message(text=reminder_message), thread_id, thread_type, ttl=30000)
            return

        # Nếu có tag thì tiến hành tạo ảnh cho từng người được tag
        for mention in message_object.mentions:
            user_id = mention['uid']
            # Bỏ qua nếu user là admin
            if user_id in ADMIN_IDS:
                continue

            user_info = client.fetchUserInfo(user_id)
            user_data = user_info.get('changed_profiles', {}).get(user_id, {})

            # Tạo ảnh
            canvas_path = create_canvas(user_data)

            if os.path.exists(canvas_path):
                # Gửi ảnh
                client.sendLocalImage(
                    canvas_path,
                    message=None,
                    thread_id=thread_id,
                    thread_type=thread_type,
                    width=558,
                    height=663,
                    ttl=120000
                )
                os.remove(canvas_path)

    except (ValueError, ZaloAPIException) as e:
        error_message = Message(text=f"Error: {str(e)}")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=10000)
    except Exception as e:
        error_message = Message(text=f"An unexpected error occurred: {str(e)}")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=10000)

# Hàm trả về danh sách các lệnh
def get_mitaizl():
    return {
        'bantho': handle_user_info
    }
