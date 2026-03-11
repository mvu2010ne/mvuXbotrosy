import os
import random
import importlib
from zlapi.models import *
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from config import PREFIX

des = {
    'version': "1.0.4",
    'credits': "Nguyễn Đức Tài",
    'description': "Xem toàn bộ lệnh hiện có của bot"
}

# Thư mục ảnh nền & font
BACKGROUND_DIR = "font/"
MODULES_DIR = "modules/"
FONT_PATH = "modules/cache/fonts/ChivoMono-VariableFont_wght.ttf"

COMMANDS_PER_PAGE = 7  # Số lệnh mỗi trang

def get_random_background():
    """Chọn ngẫu nhiên một ảnh nền từ thư mục background."""
    if not os.path.exists(BACKGROUND_DIR):
        return None
    images = [f for f in os.listdir(BACKGROUND_DIR) if f.endswith((".png", ".jpg", ".jpeg"))]
    if not images:
        return None
    return os.path.join(BACKGROUND_DIR, random.choice(images))

def draw_transparent_box(output_path, box_radius=40, blur_radius=12):
    """Tạo ảnh menu với nền gradient, hộp màu trong suốt và chữ căn giữa."""
    image_path = get_random_background()
    if not image_path:
        print("❌ Không tìm thấy ảnh nền!")
        return None

    try:
        size = (1124, 402)
        box_color = (0, 50, 100, 180)  # Màu trong suốt tinh tế

        # Mở ảnh nền, resize và làm mờ
        bg_image = Image.open(image_path).convert("RGBA")
        bg_image = bg_image.resize(size)
        bg_image = bg_image.filter(ImageFilter.GaussianBlur(blur_radius))

        # Tạo overlay hộp trong suốt với màu sắc gradient
        overlay = Image.new("RGBA", size, (100, 200, 230, 130))
        draw = ImageDraw.Draw(overlay)

        # Vẽ hộp màu gradient trong suốt
        box_x1, box_y1 = 50, 30
        box_x2, box_y2 = size[0] - 50, size[1] - 30
        draw.rounded_rectangle([(box_x1, box_y1), (box_x2, box_y2)], radius=box_radius, fill=box_color)
        bg_image = Image.alpha_composite(bg_image, overlay)

        # Load font Arial
        try:
            font = ImageFont.truetype(FONT_PATH, 38)
        except Exception as e:
            print(f"❌ Lỗi tải font: {e}")
            return None

        # Nội dung chữ trên ảnh
        text_lines = [
            "TÊN BOT: DERAIVE",
            "CHÀO MỪNG BẠN ĐẾN VỚI HỆ THỐNG",
            "HỆ THỐNG LUÔN PHỤC VỤ BẠN",
             "",
            "VERISON: 6.4.1 | UPDATE: 17/3/2025",
            "BOT BY LONG"
        ]

        # Màu sắc cho từng dòng chữ
        text_colors = [
            (255, 255, 255),  # Trắng
            (255, 223, 0),    # Vàng
            (0, 255, 0),      # Xanh lá
            (255, 69, 0),     # Đỏ cam
            (0, 0, 255)       # Xanh dương
        ]

        # Tính toán vị trí để căn giữa chữ
        text_height = len(text_lines) * 50  # Tổng chiều cao chữ
        start_y = (size[1] - text_height) // 2  # Căn giữa theo chiều dọc

        # Vẽ text ở giữa với các màu khác nhau
        draw = ImageDraw.Draw(bg_image)
        for i, line in enumerate(text_lines):
            text_width = draw.textlength(line, font=font)  # Chiều rộng chữ
            text_x = (size[0] - text_width) // 2  # Căn giữa theo chiều ngang
            draw.text((text_x, start_y + i * 50), line, font=font, fill=text_colors[i % len(text_colors)])

        # Lưu ảnh
        bg_image = bg_image.convert("RGB")
        bg_image.save(output_path)
        return output_path

    except Exception as e:
        print(f"❌ Lỗi tạo ảnh: {e}")
        return None

def get_all_mitaizl():
    """Lấy tất cả lệnh từ các module trong thư mục modules."""
    mitaizl = {}

    for module_name in os.listdir(MODULES_DIR):
        if module_name.endswith('.py') and module_name != '__init__.py':
            module_path = f'modules.{module_name[:-3]}'
            module = importlib.import_module(module_path)

            if hasattr(module, 'get_mitaizl'):
                module_mitaizl = module.get_mitaizl()
                mitaizl.update(module_mitaizl)

    return list(mitaizl.keys())

def handle_manh_command(message, message_object, thread_id, thread_type, author_id, bot):
    """Xử lý lệnh `manh` để hiển thị menu kèm ảnh"""
    commands = get_all_mitaizl()  # Lấy tất cả lệnh
    total_pages = (len(commands) + COMMANDS_PER_PAGE - 1) // COMMANDS_PER_PAGE  # Tính tổng số trang

    # Lấy số trang từ tin nhắn (vd: "manh 2")
    parts = message.split()
    page = 1  # Mặc định trang 1
    if len(parts) > 1 and parts[1].isdigit():
        page = int(parts[1])
    
    # Kiểm tra trang hợp lệ
    if page < 1 or page > total_pages:
        bot.send(Message(text=f"⚠ Trang không hợp lệ! Chọn từ 1 đến {total_pages}."), thread_id=thread_id, thread_type=thread_type)
        return

    # Lấy lệnh của trang hiện tại
    start_index = (page - 1) * COMMANDS_PER_PAGE
    end_index = start_index + COMMANDS_PER_PAGE
    commands_page = commands[start_index:end_index]

    intro_image_path = "intro_menu.jpg"
    image_path = draw_transparent_box(intro_image_path)

    # Thêm ký tự "➜" vào trước các lệnh và thay đổi màu sắc
    command_list_text = "\n".join([f"➜ {PREFIX}{cmd}" for cmd in commands_page])
    message_text = f"🚦Command của bạn đây🐳 {page}/{total_pages}\n\n{command_list_text}\n\n🚦End command👑"

    if image_path:
        bot.sendLocalImage(
            message=Message(text=message_text),
            imagePath=image_path,
            thread_id=thread_id,
            thread_type=thread_type,
            width=1124,
            height=402,
            ttl=60000
        )
    else:
        bot.send(Message(text="❌ Không thể tạo ảnh menu. Kiểm tra thư mục background hoặc font chữ."), thread_id=thread_id, thread_type=thread_type)

def get_mitaizl():
    """Trả về danh sách lệnh của module này."""
    return {
        'hidden': handle_manh_command  # Gọi lệnh `manh`
    }
