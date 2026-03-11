from zlapi.models import Message
import os
import requests
from PIL import Image, ImageFilter

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Chụp cố định 1 trang web (eva.vn) rồi cắt (crop) vùng cố định, có làm nét hậu kỳ.",
    'tính năng': [
        "📸 Chụp màn hình trang eva.vn",
        "🖼️ Cắt (crop) một vùng cố định (80,220,800,1780)",
        "🔧 Xử lý hậu kỳ (làm nét ảnh) bằng PIL",
        "⚡ Gửi ảnh ngay khi xử lý xong",
        "🗑️ Ảnh tự động xóa sau khi gửi để tiết kiệm bộ nhớ"
    ],
    'hướng dẫn sử dụng': (
        "Chỉ cần gõ 'capcrop' (hoặc tuỳ ý) để chụp ảnh từ URL cố định.\n"
        "Không cần tham số."
    )
}

def handle_lich_command(message, message_object, thread_id, thread_type, author_id, client):
    """
    Tập lệnh cố định URL và toạ độ cắt (crop).
    Bỏ qua mọi tham số từ người dùng.
    """
    # Kiểm tra xem có phải lệnh capcrop hay không
    if not message.lower().startswith("lich"):
        return

    # Thả reaction
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    # 1) Cố định URL
    url_to_capture = "https://eva.vn/lich-van-nien-c192.html"

    # 2) Cố định toạ độ crop
    left, upper = 80, 220
    right, lower = 800, 1780

    try:
        # 3) Gọi Thum.io (fullpage) để chụp toàn bộ trang
        capture_url = (
            f"https://image.thum.io/get/width/1920/"
            f"fullpage/noanimate/"
            f"{url_to_capture}"
        )

        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/58.0.3029.110 Safari/537.36'
            )
        }

        # Tăng timeout nếu trang nặng
        image_response = requests.get(capture_url, headers=headers, timeout=60)
        image_response.raise_for_status()

        # 4) Lưu ảnh tạm
        temp_path = 'modules/cache/temp_full_capcrop.jpeg'
        with open(temp_path, 'wb') as f:
            f.write(image_response.content)

        # 5) Mở ảnh, crop vùng cố định, làm nét
        cropped_path = 'modules/cache/temp_crop_capcrop.jpeg'
        with Image.open(temp_path) as img:
            cropped_img = img.crop((left, upper, right, lower))
            if cropped_img.mode == 'RGBA':
                cropped_img = cropped_img.convert('RGB')

            # Áp dụng bộ lọc làm nét (SHARPEN)
            cropped_img = cropped_img.filter(ImageFilter.SHARPEN)
            # Hoặc dùng UnsharpMask (bỏ comment nếu muốn):
            # cropped_img = cropped_img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))

            cropped_img.save(cropped_path, format="JPEG", quality=100)

        # 6) Gửi ảnh đã cắt
        success_text = (
            f"Chụp trang: {url_to_capture}\n"
            f"Crop vùng: (left={left}, upper={upper}, right={right}, lower={lower})"
        )
        success_message = Message(text=success_text)
        client.sendLocalImage(
            cropped_path,
            message="",
            thread_id=thread_id,
            thread_type=thread_type,
            width=720,
            height=1560,
            ttl=120000
        )

        # 7) Xoá file tạm
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(cropped_path):
            os.remove(cropped_path)

    except requests.exceptions.RequestException as e:
        error_message = Message(text=f"Đã xảy ra lỗi khi gọi API Thum.io: {str(e)}")
        client.sendMessage(error_message, thread_id, thread_type)
    except Exception as e:
        error_message = Message(text=f"Đã xảy ra lỗi: {str(e)}")
        client.sendMessage(error_message, thread_id, thread_type)

def get_mitaizl():
    """
    Trả về từ điển { 'capcrop': handle_capcrop_command }
    để Bot biết lệnh nào sẽ gọi hàm nào.
    """
    return {
        'lich': handle_lich_command
    }
