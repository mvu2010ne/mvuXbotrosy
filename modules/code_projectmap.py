import os
import asyncio
import time
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import logging
from zlapi.models import Message, ThreadType

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
        "🖼️ Tạo một ảnh duy nhất chứa toàn bộ cây thư mục."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh tree.cmdmap [size:small|medium|large] [path].",
        "📌 Ví dụ: tree.cmdmap large /path/to/project hoặc tree.cmdmap medium .",
        "✅ Nhận ảnh chứa cây thư mục nếu đường dẫn hợp lệ."
    ]
}

MAX_HEIGHT = 200000  # Chiều cao tối đa của ảnh (pixel)

def get_directory_tree(start_path='.'):
    """Tạo cây thư mục từ đường dẫn bắt đầu, bao gồm thông tin ngày và kích thước."""
    logger.info(f"[get_directory_tree] Bắt đầu tạo cây thư mục từ {start_path}...")
    lines = []

    def _walk_directory(path, prefix="", is_last=True, depth=0):
        try:
            # Lấy danh sách các mục trong thư mục
            items = sorted(os.listdir(path), key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))
            # Chỉ loại bỏ các thư mục/tệp không mong muốn (tùy chỉnh theo nhu cầu)
            items = [item for item in items if item not in ('.venv', '__pycache__')]  # Không loại bỏ .git, .gitignore
            if not items:
                return

            for i, item in enumerate(items):
                is_last_item = (i == len(items) - 1)
                item_path = os.path.join(path, item)
                connector = "└── " if is_last_item else "├── "
                new_prefix = prefix + ("    " if is_last else "│   ")

                # Bỏ qua file không phải .py
                if os.path.isfile(item_path) and not item.endswith('.py'):
                    continue

                try:
                    stat = os.stat(item_path)
                    mod_time = stat.st_mtime
                    mod_date = time.strftime("%d/%m/%Y %H:%M %p", time.localtime(mod_time))
                    size = os.path.getsize(item_path) if os.path.isfile(item_path) else "-"
                    size_str = f"{size:,} bytes" if os.path.isfile(item_path) else ""

                    if os.path.isdir(item_path):
                        lines.append(f"{prefix}{connector}{item}/")
                        _walk_directory(item_path, new_prefix, is_last_item, depth + 1)
                    else:
                        lines.append(f"{prefix}{connector}{item:<30} {mod_date:<15} {size_str:<10}")
                except Exception as e:
                    logger.error(f"[get_directory_tree] Lỗi khi truy cập {item_path}: {str(e)}")

        except PermissionError:
            logger.warning(f"[get_directory_tree] Không có quyền truy cập {path}")
            lines.append(f"{prefix}{connector}[Permission Denied] {os.path.basename(path)}")
        except Exception as e:
            logger.error(f"[get_directory_tree] Lỗi khi truy cập {path}: {str(e)}")

    # Bắt đầu từ thư mục gốc
    lines.append(os.path.basename(os.path.abspath(start_path)) or start_path)
    _walk_directory(start_path, "", True, 0)
    return lines

def create_image_from_tree(lines, size="medium"):
    """Tạo một ảnh duy nhất từ danh sách cây thư mục."""
    fontcre = "modules/cache/JetBrainsMono-VariableFont_wght.ttf"  # Sử dụng font JetBrains Mono

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
    title_text = "PROJECT DIRECTORY TREE"
    title_text_width = temp_draw.textlength(title_text, font=header_font)
    title_text_x = (img_width - title_text_width) // 2
    draw.text((title_text_x, 15), title_text, font=header_font, fill=(200, 200, 200))

    # Vẽ cây thư mục
    y_offset = header_height + 20
    for i, line in enumerate(lines):
        # Màu sắc dựa trên loại dòng
        if line == lines[0]:  # Dòng tên thư mục gốc
            color = (255, 255, 255)
        elif line.strip().endswith('/'):  # Thư mục
            color = (173, 216, 230)
        else:  # Tệp
            color = (220, 220, 220)

        draw.text((10, y_offset), line, font=code_font, fill=color)
        y_offset += line_height

    # Lưu ảnh
    image_path = "modules/cache/tree_single.png"
    background.save(image_path, quality=95)
    return image_path, img_width, img_height

async def upload_to_uguu(image_path):
    """Tải ảnh lên Uguu và trả về URL."""
    logger.info(f"[upload_to_uguu] Đang tải ảnh: {image_path}")
    url = "https://uguu.se/upload.php"
    max_file_size = 100 * 1024 * 1024  # 100MB, giới hạn của Uguu

    try:
        file_size = os.path.getsize(image_path)
        if file_size > max_file_size:
            logger.error(f"[upload_to_uguu] Tệp {image_path} vượt quá giới hạn kích thước {max_file_size} bytes")
            return None

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            with open(image_path, 'rb') as f:
                data = {'files[]': f}
                async with session.post(url, data=data) as resp:
                    if resp.status == 200:
                        response = await resp.json()
                        file_url = response.get('files', [{}])[0].get('url')
                        if file_url:
                            logger.info(f"[upload_to_uguu] Tải lên thành công, URL: {file_url}")
                            return file_url
                        else:
                            logger.error("[upload_to_uguu] Không nhận được URL từ phản hồi")
                            return None
                    else:
                        logger.error(f"[upload_to_uguu] Lỗi tải lên, mã trạng thái: {resp.status}")
                        return None
    except aiohttp.ClientError as e:
        logger.error(f"[upload_to_uguu] Lỗi mạng khi tải lên: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"[upload_to_uguu] Lỗi không xác định khi tải lên: {str(e)}")
        return None
    finally:
        logger.info(f"[upload_to_uguu] Hoàn tất xử lý tải lên cho {image_path}")

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
    client.sendMessage(Message(text="⏳ Đang tạo bản đồ thư mục dự án..."), thread_id, thread_type, ttl=10000)

    try:
        # Tải logo Python (tùy chọn, giữ lại cho giao diện)
        await fetch_python_logo()

        # Lấy cây thư mục
        lines = get_directory_tree(path)
        if not lines:
            client.replyMessage(Message(text="❌ Không tìm thấy thư mục nào."), message_object, thread_id, thread_type)
            logger.info("[handle_tree_command] Không có thư mục, gửi thông báo lỗi.")
            return

        # Tạo ảnh duy nhất
        image_path, img_width, img_height = create_image_from_tree(lines, size)
        logger.info(f"[handle_tree_command] Đã tạo ảnh: {image_path}")

        # Tải ảnh lên Uguu
        image_url = await upload_to_uguu(image_path)
        if not image_url:
            client.replyMessage(Message(text="⚠ Lỗi: Không thể tải ảnh lên Uguu."), message_object, thread_id, thread_type)
            logger.error("[handle_tree_command] Tải ảnh lên Uguu thất bại.")
            return

        # Gửi ảnh qua URL
        msg = "✅ Bản đồ thư mục dự án"
        client.sendRemoteImage(
            image_url,
            thread_id,
            thread_type,
            width=img_width,
            height=img_height,
            message=Message(text=msg),
            ttl=180000
        )
        logger.info(f"[handle_tree_command] Đã gửi ảnh qua URL: {image_url}")

    except Exception as e:
        client.replyMessage(Message(text=f"⚠ Lỗi: {str(e)}"), message_object, thread_id, thread_type)
        logger.error(f"[handle_tree_command] Lỗi xử lý: {str(e)}")
    finally:
        # Xóa file ảnh tạm
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
                logger.info(f"[handle_tree_command] Đã xóa file tạm: {image_path}")
            except Exception as e:
                logger.error(f"[handle_tree_command] Lỗi khi xóa file tạm: {str(e)}")

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
        'code.projectmap': lambda *args: asyncio.run(handle_tree_command(*args))
    }