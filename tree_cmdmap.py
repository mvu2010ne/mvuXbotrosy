import os
import asyncio
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import logging

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Biến des cho module
des = {
    'tác giả': "Minh Vũ",
    'mô tả': "📜 Hiển thị cấu trúc thư mục dự án dưới dạng cây thư mục trong ảnh, bao gồm thông tin kích thước và ngày chỉnh sửa.",
    'tính năng': [
        "📋 Hiển thị toàn bộ cấu trúc thư mục dự án dưới dạng cây thư mục.",
        "🔤 Sắp xếp thư mục và tệp theo thứ tự chữ cái từ A đến Z.",
        "🎨 Tạo ảnh với nền gradient và giao diện hiện đại.",
        "📏 Hỗ trợ kích thước ảnh: nhỏ, vừa, lớn.",
        "🔄 Gửi nhiều ảnh cùng lúc nếu danh sách dài."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh tree.cmdmap [size:small|medium|large] [path].",
        "📌 Ví dụ: tree.cmdmap large /path/to/project hoặc tree.cmdmap medium .",
        "✅ Nhận ảnh chứa cây thư mục nếu đường dẫn hợp lệ."
    ]
}

MAX_LINES_PER_IMAGE = 50  # Số dòng tối đa trong ảnh
MAX_HEIGHT = 10000  # Chiều cao tối đa của ảnh (pixel)

def get_directory_tree(start_path='.'):
    """Tạo cây thư mục từ đường dẫn bắt đầu, bao gồm thông tin ngày và kích thước."""
    logger.info(f"[get_directory_tree] Bắt đầu tạo cây thư mục từ {start_path}...")
    lines = []

    def _walk_directory(path, prefix="", is_last=True, depth=0):
        try:
            # Lấy danh sách các mục trong thư mục
            items = sorted(os.listdir(path), key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))
            items = [item for item in items if not item.startswith('.')]  # Loại bỏ tệp ẩn
            if not items:
                return

            for i, item in enumerate(items):
                is_last_item = (i == len(items) - 1)
                item_path = os.path.join(path, item)
                connector = "└── " if is_last_item else "├── "
                new_prefix = prefix + ("    " if is_last else "│   ")

                stat = os.stat(item_path)
                mod_time = stat.st_mtime
                mod_date = time.strftime("%d/%m/%Y %H:%M %p", time.localtime(mod_time))
                size = os.path.getsize(item_path) if os.path.isfile(item_path) else "-"
                size_str = f"{size:,} bytes" if os.path.isfile(item_path) else ""

                if os.path.isdir(item_path):
                    lines.append(f"{prefix}{connector}{item}")
                    _walk_directory(item_path, new_prefix, is_last_item, depth + 1)
                else:
                    lines.append(f"{prefix}{connector}{item:<30} {mod_date:<15} {size_str:<10}")

        except Exception as e:
            logger.error(f"[get_directory_tree] Lỗi khi truy cập {path}: {str(e)}")

    # Bắt đầu từ thư mục gốc
    lines.append(start_path)
    _walk_directory(start_path, "", True, 0)
    return lines

def create_image_from_tree(lines, size="medium", part_number=1, total_parts=1):
    """Tạo ảnh từ danh sách cây thư mục."""
    fontcre = "modules/cache/JetBrainsMono-Regular.ttf"  # Sử dụng font JetBrains Mono

    line_height = 30 if size == "small" else 35 if size == "medium" else 40
    font_size = 20 if size == "small" else 25 if size == "medium" else 30
    line_offset = 80

    # Tính kích thước ảnh
    temp_img = Image.new('RGBA', (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)
    code_font = ImageFont.truetype(fontcre, font_size)
    max_width = max((temp_draw.textlength(line, font=code_font) for line in lines), default=0) + 100
    img_width = int(max_width)
    img_height = min(MAX_HEIGHT, int(line_offset + len(lines) * line_height + 60))

    # Tạo nền gradient
    background = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(background)
    for y in range(img_height):
        r = int(30 + (y / img_height) * 20)
        g = int(30 + (y / img_height) * 40)
        b = int(30 + (y / img_height) * 60)
        draw.line([(0, y), (img_width, y)], fill=(r, g, b))

    # Header
    header_height = 60
    draw.rectangle([(0, 0), (img_width, header_height)], fill=(50, 70, 90))

    # Tiêu đề
    header_font = ImageFont.truetype(fontcre, 38)
    title_text = f"PROJECT DIRECTORY TREE - Part {part_number}/{total_parts}"
    title_text_width = temp_draw.textlength(title_text, font=header_font)
    title_text_x = (img_width - title_text_width) // 2
    draw.text((title_text_x, 15), title_text, font=header_font, fill=(200, 200, 200))

    # Vẽ cây thư mục
    y_offset = header_height + 20
    for i, line in enumerate(lines):
        # Màu sắc dựa trên loại dòng
        if line == lines[0]:  # Dòng tên thư mục gốc
            color = (255, 255, 255)
        elif os.path.isdir(os.path.join(lines[0], line.strip())):  # Thư mục
            color = (173, 216, 230)
        else:  # Tệp
            color = (220, 220, 220)

        draw.text((10, y_offset), line, font=code_font, fill=color)
        y_offset += line_height

    # Lưu ảnh
    image_path = f"modules/cache/tree_part_{part_number}.png"
    background.save(image_path, quality=95)
    return image_path, img_width, img_height

async def handle_tree_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh tree.cmdmap."""
    logger.info(f"[handle_tree_command] Nhận lệnh từ author_id: {author_id}, thread_id: {thread_id}")
    
    parts = message.split()
    size = "medium"
    path = "."
    if len(parts) > 1 and parts[1] in ("small", "medium", "large"):
        size = parts[1]
    if len(parts) > 2:
        path = parts[2]

    if not os.path.exists(path):
        client.replyMessage(Message(text=f"❌ Đường dẫn '{path}' không tồn tại."), message_object, thread_id, thread_type)
        logger.info("[handle_tree_command] Đường dẫn không hợp lệ, từ chối.")
        return

    # Thông báo đang xử lý
    client.sendMessage(Message(text="⏳ Đang tạo cây thư mục..."), thread_id, thread_type, ttl=10000)

    try:
        # Tải logo Python (tùy chọn, giữ lại cho giao diện)
        await fetch_python_logo()

        # Lấy cây thư mục
        lines = get_directory_tree(path)
        if not lines:
            client.replyMessage(Message(text="❌ Không tìm thấy thư mục nào."), message_object, thread_id, thread_type)
            logger.info("[handle_tree_command] Không có thư mục, gửi thông báo lỗi.")
            return

        total_lines = len(lines)
        lines_per_image = MAX_LINES_PER_IMAGE
        total_parts = (total_lines + lines_per_image - 1) // lines_per_image

        image_paths = []
        image_dimensions = []
        for part in range(total_parts):
            start_idx = part * lines_per_image
            end_idx = min((part + 1) * lines_per_image, total_lines)
            part_lines = lines[start_idx:end_idx]

            image_path, img_width, img_height = create_image_from_tree(
                part_lines, size, part + 1, total_parts
            )
            image_paths.append(image_path)
            image_dimensions.append((img_width, img_height))
            logger.info(f"[handle_tree_command] Đã tạo ảnh phần {part + 1}/{total_parts}: {image_path}")

        # Gửi tất cả ảnh cùng lúc
        if image_paths:
            msg = f"✅ Cây thư mục ({total_parts} phần)"
            default_width, default_height = image_dimensions[0] if image_dimensions else (2560, 2560)
            
            client.sendMultiLocalImage(
                imagePathList=image_paths,
                thread_id=thread_id,
                thread_type=thread_type,
                width=default_width,
                height=default_height,
                message=Message(text=msg),
                ttl=180000
            )
            logger.info(f"[handle_tree_command] Đã gửi {len(image_paths)} ảnh cùng lúc.")

            # Xóa các file ảnh tạm
            for image_path in image_paths:
                if os.path.exists(image_path):
                    os.remove(image_path)
                    logger.info(f"[handle_tree_command] Đã xóa file tạm: {image_path}")

    except Exception as e:
        client.replyMessage(Message(text=f"⚠ Lỗi: {str(e)}"), message_object, thread_id, thread_type)
        logger.error(f"[handle_tree_command] Lỗi xử lý: {str(e)}")

async def fetch_python_logo():
    """Tải logo Python nếu chưa có."""
    logo_path = "modules/cache/python-logo.png"
    if not os.path.exists(logo_path):
        url = "https://www.python.org/static/community_logos/python-logo.png"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    with open(logo_path, 'wb') as f:
                        f.write(await resp.read())
    return logo_path

def get_mitaizl():
    """Đăng ký lệnh tree.cmdmap."""
    logger.info("[get_mitaizl] Đăng ký lệnh 'tree.cmdmap'.")
    return {
        'tree.cmdmap': lambda *args: asyncio.run(handle_tree_command(*args))
    }

