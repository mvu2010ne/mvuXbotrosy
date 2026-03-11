import os
import importlib
import asyncio
from config import ADMIN
from zlapi.models import Message, ThreadType
from PIL import Image, ImageDraw, ImageFont
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter
from bs4 import BeautifulSoup
import aiohttp
import logging

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Biến des cho module
des = {
    'tác giả': "Minh Vũ",
    'mô tả': "📜 Hiển thị danh sách các lệnh từ hàm get_mitaizl của các module dưới dạng cây thư mục trong một ảnh, sắp xếp module theo thứ tự chữ cái.",
    'tính năng': [
        "📋 Thu thập và hiển thị lệnh từ tất cả module trong thư mục 'modules' dưới dạng cây thư mục.",
        "🔤 Sắp xếp module theo thứ tự chữ cái từ A đến Z.",
        "🎨 Tạo ảnh với nền gradient, highlight lệnh, và giao diện hiện đại.",
        "📏 Hỗ trợ kích thước ảnh: nhỏ, vừa, lớn.",
        "🔐 Yêu cầu quyền admin để sử dụng.",
        "🖼️ Tạo một ảnh duy nhất chứa toàn bộ cây lệnh."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh code.cmdmap [size:small|medium|large].",
        "📌 Ví dụ: code.cmdmap large hoặc code.cmdmap medium.",
        "✅ Nhận ảnh chứa cây thư mục lệnh nếu là admin."
    ]
}

MAX_HEIGHT = 200000  # Chiều cao tối đa của ảnh (pixel)
COLUMN_GAP = 50  # Khoảng cách giữa hai cột (pixel)

def is_admin(author_id):
    return author_id in ADMIN

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

def get_all_commands():
    """Thu thập tất cả lệnh từ hàm get_mitaizl của các module, sắp xếp module theo thứ tự chữ cái."""
    logger.info("[get_all_commands] Bắt đầu thu thập lệnh...")
    command_groups = {}
    missing_mitaizl_modules = []
    
    if not os.path.exists('modules'):
        logger.warning("[get_all_commands] Thư mục 'modules' không tồn tại.")
        return command_groups, missing_mitaizl_modules

    # Lấy danh sách module và sắp xếp theo thứ tự chữ cái
    module_names = sorted(
        [name for name in os.listdir('modules') if name.endswith('.py') and name != '__init__.py'],
        key=lambda x: x.lower()
    )

    for module_name in module_names:
        module_key = module_name[:-3]  # Bỏ phần .py
        module_path = f'modules.{module_key}'
        logger.info(f"[get_all_commands] Đang xử lý: {module_name}")
        try:
            module = importlib.import_module(module_path)
            if hasattr(module, 'get_mitaizl'):
                mitaizl = module.get_mitaizl()
                if isinstance(mitaizl, dict):
                    module_commands = list(mitaizl.keys())
                    if module_commands:
                        command_groups[module_key] = module_commands
                        logger.info(f"[get_all_commands] Đã lấy {len(module_commands)} lệnh từ {module_name}")
                    else:
                        logger.info(f"[get_all_commands] Module {module_name} không có lệnh")
                else:
                    missing_mitaizl_modules.append(module_key)
                    logger.warning(f"[get_all_commands] Hàm get_mitaizl của {module_name} không trả về dict")
            else:
                missing_mitaizl_modules.append(module_key)
                logger.info(f"[get_all_commands] Module {module_name} không có hàm get_mitaizl")
        except Exception as e:
            logger.error(f"[get_all_commands] Lỗi với {module_name}: {str(e)}")
    
    return command_groups, missing_mitaizl_modules

def format_command_tree(command_groups, missing_mitaizl_modules):
    """Định dạng danh sách lệnh thành cây thư mục, không có khoảng cách giữa các module."""
    lines = []
    total_commands = sum(len(cmds) for cmds in command_groups.values())
    lines.append(f"# Tổng số lệnh: {total_commands}")

    # Tạo cây thư mục cho các module và lệnh, không thêm dòng trống giữa các module
    for i, (module, commands) in enumerate(sorted(command_groups.items(), key=lambda x: x[0].lower())):
        connector = "└── " if i == len(command_groups) - 1 else "├── "
        lines.append(f"{connector}{module}")
        for j, cmd in enumerate(commands):
            sub_connector = "└── " if j == len(commands) - 1 else "├── "
            lines.append(f"│   {sub_connector}{cmd}")

    if missing_mitaizl_modules:
        lines.append("├── # Module thiếu get_mitaizl:")
        for j, module in enumerate(sorted(missing_mitaizl_modules, key=lambda x: x.lower())):
            sub_connector = "└── " if j == len(missing_mitaizl_modules) - 1 else "├── "
            lines.append(f"│   {sub_connector}{module}")
    
    return lines

def create_image_from_commands(lines, size="medium"):
    """Tạo một ảnh duy nhất từ danh sách lệnh với bố cục cây thư mục."""
    fontcre = "modules/cache/JetBrainsMono-VariableFont_wght.ttf"
    fontlenh = "modules/cache/JetBrainsMono-ExtraBold.ttf"

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
    title_text = "Minh Vũ Shinn Cte PROJECT - Commands Tree"
    title_text_width = temp_draw.textlength(title_text, font=header_font)
    title_text_x = (img_width - title_text_width) // 2
    draw.text((title_text_x, 15), title_text, font=header_font, fill=(200, 200, 200))

    # Nút tròn
    dot_radius = 12
    dots_x_start = 20
    dot_positions = [(dots_x_start + i * 40, 30) for i in range(3)]
    dot_colors = [(255, 59, 48), (40, 205, 65), (255, 190, 0)]
    for pos, color in zip(dot_positions, dot_colors):
        draw.ellipse([pos[0] - dot_radius, pos[1] - dot_radius, pos[0] + dot_radius, pos[1] + dot_radius], fill=color)

    # Tab
    command_font = ImageFont.truetype(fontlenh, font_size)
    command_text = "Command Tree"
    command_text_width = temp_draw.textlength(command_text, font=command_font)
    tab_x = dots_x_start + 120
    tab_width = int(command_text_width + 70)
    draw.rounded_rectangle([(tab_x, 10), (tab_x + tab_width, 50)], radius=10, fill=(70, 90, 110))
    
    python_logo = Image.open("modules/cache/python-logo.png").resize((25, 25))
    if python_logo.mode == 'RGBA':
        background.paste(python_logo, (tab_x + 10, 15), python_logo.split()[3])
    else:
        background.paste(python_logo, (tab_x + 10, 15))
    
    draw.text((tab_x + 40, 15), command_text, font=command_font, fill=(255, 255, 255))

    # Vẽ cây lệnh
    y_offset = header_height + 20
    for i, line in enumerate(lines):
        # Màu sắc dựa trên loại dòng
        if line.startswith("#"):
            color = (150, 150, 150)  # Màu cho dòng tiêu đề
        else:
            color = (220, 220, 220)  # Màu mặc định cho lệnh

        draw.text((10, y_offset), line, font=code_font, fill=color)
        y_offset += line_height

    # Lưu ảnh
    image_path = "modules/cache/cmdtree_single.png"
    background.save(image_path, quality=95)
    return image_path, img_width, img_height

def get_color_for_token_type(span):
    """Ánh xạ màu cho các loại token (không sử dụng trong cây thư mục, giữ lại cho tương thích)."""
    color_map = {
        'k': (0, 255, 255),
        'n': (255, 232, 255),
        's': (255, 255, 107),
        'c': (173, 216, 230),
        'o': (225, 225, 225),
        'p': (0, 255, 0),
        'm': (233, 51, 35),
    }
    if 'class' in span.attrs:
        token_type = span['class'][0][0]
        return color_map.get(token_type, (220, 220, 220))
    return (220, 220, 220)

async def handle_cmdmap_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh code.cmdmap."""
    logger.info(f"[handle_cmdmap_command] Nhận lệnh từ author_id: {author_id}, thread_id: {thread_id}")
    
    parts = message.split()
    size = "medium"
    if len(parts) > 1 and parts[1] in ("small", "medium", "large"):
        size = parts[1]
    else:
        logger.info("[handle_cmdmap_command] Không có tham số size, sử dụng mặc định: medium")

    if not is_admin(author_id):
        client.replyMessage(Message(text="• Bạn không có quyền sử dụng lệnh này."), message_object, thread_id, thread_type)
        logger.info("[handle_cmdmap_command] Người dùng không phải admin, từ chối.")
        return

    # Thông báo đang xử lý
    client.sendMessage(Message(text="⏳ Đang tạo bản đồ ánh xạ lệnh..."), thread_id, thread_type, ttl=10000)

    try:
        # Tải logo Python
        await fetch_python_logo()

        # Lấy danh sách lệnh
        command_groups, missing_mitaizl_modules = get_all_commands()
        if not command_groups and not missing_mitaizl_modules:
            client.replyMessage(Message(text="❌ Không tìm thấy lệnh nào."), message_object, thread_id, thread_type)
            logger.info("[handle_cmdmap_command] Không có lệnh, gửi thông báo lỗi.")
            return

        # Định dạng cây lệnh
        lines = format_command_tree(command_groups, missing_mitaizl_modules)

        # Tạo ảnh duy nhất
        image_path, img_width, img_height = create_image_from_commands(lines, size)
        logger.info(f"[handle_cmdmap_command] Đã tạo ảnh: {image_path}")

        # Gửi ảnh
        total_commands = sum(len(cmds) for cmds in command_groups.values())
        msg = f"✅ Bản đồ ánh xạ lệnh ({total_commands} lệnh)"
        client.sendLocalImage(
            image_path,
            thread_id,
            thread_type,
            width=img_width,
            height=img_height,
            message=Message(text=msg),
            ttl=180000
        )
        logger.info(f"[handle_cmdmap_command] Đã gửi ảnh: {image_path}")

        # Xóa file ảnh tạm
        if os.path.exists(image_path):
            os.remove(image_path)
            logger.info(f"[handle_cmdmap_command] Đã xóa file tạm: {image_path}")

    except Exception as e:
        client.replyMessage(Message(text=f"⚠ Lỗi: {str(e)}"), message_object, thread_id, thread_type)
        logger.error(f"[handle_cmdmap_command] Lỗi xử lý: {str(e)}")

def get_mitaizl():
    """Đăng ký lệnh code.cmdmap."""
    logger.info("[get_mitaizl] Đăng ký lệnh 'code.cmdmap'.")
    return {
        'code.cmdmap': lambda *args: asyncio.run(handle_cmdmap_command(*args))
    }