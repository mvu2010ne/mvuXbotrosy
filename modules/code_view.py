import os
import requests
import asyncio
import time
from zlapi.models import Message, MultiMsgStyle, MessageStyle
from PIL import Image, ImageDraw, ImageFont
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter
from bs4 import BeautifulSoup
import aiohttp

des = {
    'tác giả': "Minh Vũ Shinn Cte ",
    'mô tả': "🔍 Hiển thị mã nguồn lệnh dưới dạng ảnh đẹp mắt.",
    'tính năng': [
        "📋 Hiển thị nội dung nhiều lệnh, chia nhỏ nếu quá dài.",
        "🎨 Tạo ảnh với nền gradient, highlight code, và giao diện hiện đại.",
        "🔎 Tìm kiếm và đánh dấu từ khóa trong mã nguồn (tùy chọn).",
        "📏 Hỗ trợ kích thước ảnh: nhỏ, vừa, lớn.",
        "🔐 Yêu cầu quyền admin để sử dụng."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh code.view [size:small|medium|large] <tên lệnh> [từ khóa].",
        "📌 Ví dụ: code.view large unban hoặc code.view medium ban def.",
        "✅ Nhận ảnh chứa mã nguồn với định dạng đẹp nếu là admin."
    ]
}

ADMIN_ID = "3299675674241805615"
MAX_LINES_PER_IMAGE = 500  # Số dòng tối đa mỗi ảnh
MAX_HEIGHT = 10000  # Chiều cao tối đa của ảnh (pixel)

def is_admin(author_id):
    return author_id == ADMIN_ID

def read_command_content(command_name):
    try:
        file_path = f"modules/{command_name}.py"
        if not os.path.exists(file_path):
            return None
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        return str(e)

async def fetch_python_logo():
    logo_path = "modules/cache/python-logo.png"
    if not os.path.exists(logo_path):
        url = "https://www.python.org/static/community_logos/python-logo.png"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    with open(logo_path, 'wb') as f:
                        f.write(await resp.read())
    return logo_path

def create_image_from_code(code_lines, command_name, size="medium", search_term=None, part_number=1, total_parts=1):
    fontcre = "modules/cache/Roboto_Condensed-Regular.ttf"
    fontlenh = "modules/cache/Roboto_SemiCondensed-Light.ttf"

    line_height = 30 if size == "small" else 35 if size == "medium" else 40
    font_size = 20 if size == "small" else 25 if size == "medium" else 30
    line_offset = 80

    # Tính kích thước ảnh
    temp_img = Image.new('RGBA', (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)
    code_font = ImageFont.truetype(fontcre, font_size)
    max_width = max(temp_draw.textlength(line, font=code_font) for line in code_lines) + 170
    img_width = max(800, min(3000, int(max_width)))
    img_height = min(MAX_HEIGHT, int(line_offset + len(code_lines) * line_height + 60))

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

    # Tiêu đề "Minh Vũ Shinn Cte PROJECT"
    header_font = ImageFont.truetype(fontcre, 38)
    mitai_text = f"Minh Vũ Shinn Cte PROJECT - Part {part_number}/{total_parts}"
    mitai_text_width = temp_draw.textlength(mitai_text, font=header_font)
    mitai_text_x = (img_width - mitai_text_width) // 2
    draw.text((mitai_text_x, 15), mitai_text, font=header_font, fill=(200, 200, 200))

    # Nút tròn
    dot_radius = 12
    dots_x_start = 20
    dot_positions = [(dots_x_start + i * 40, 30) for i in range(3)]
    dot_colors = [(255, 59, 48), (40, 205, 65), (255, 190, 0)]
    for pos, color in zip(dot_positions, dot_colors):
        draw.ellipse([pos[0] - dot_radius, pos[1] - dot_radius, pos[0] + dot_radius, pos[1] + dot_radius], fill=color)

    # Tab lệnh
    command_font = ImageFont.truetype(fontlenh, font_size)
    command_text = f"{command_name}.py"
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

    # Vẽ code
    y_offset = header_height + 20
    for i, line in enumerate(code_lines):
        line_number = f"{i + 1 + (part_number - 1) * MAX_LINES_PER_IMAGE:2}"
        draw.text((10, y_offset), line_number, font=code_font, fill=(150, 150, 150))

        x_offset = 60
        if search_term and search_term.lower() in line.lower():
            draw.rectangle([(x_offset - 5, y_offset - 5), (img_width - 10, y_offset + line_height - 5)], fill=(255, 255, 0, 50))

        highlighted_line = highlight(line, PythonLexer(), HtmlFormatter())
        soup_line = BeautifulSoup(highlighted_line, 'html.parser')
        spans = soup_line.find_all('span')
        last_end_index = 0

        for span in spans:
            token_text = span.get_text()
            token_color = get_color_for_token_type(span)
            start_index = line.find(token_text, last_end_index)
            if start_index > last_end_index:
                space_text = line[last_end_index:start_index]
                draw.text((x_offset, y_offset), space_text, font=code_font, fill=(220, 220, 220))
                x_offset += temp_draw.textlength(space_text, font=code_font)
            draw.text((x_offset, y_offset), token_text, font=code_font, fill=token_color)
            x_offset += temp_draw.textlength(token_text, font=code_font)
            last_end_index = start_index + len(token_text)

        if last_end_index < len(line):
            remaining_space = line[last_end_index:]
            draw.text((x_offset, y_offset), remaining_space, font=code_font, fill=(220, 220, 220))

        y_offset += line_height

    # Lưu ảnh
    image_path = f"modules/cache/anh_part_{part_number}.png"
    background.save(image_path, quality=95)
    return image_path, img_width, img_height

def get_color_for_token_type(span):
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

async def handle_viewcode_command(message, message_object, thread_id, thread_type, author_id, client):
    parts = message.split()
    if len(parts) < 2:
        client.replyMessage(Message(text="Vui lòng nhập: code.view [size] <tên lệnh> [từ khóa]"), message_object, thread_id, thread_type)
        return

    if not is_admin(author_id):
        client.replyMessage(Message(text="• Bạn không có quyền sử dụng lệnh này."), message_object, thread_id, thread_type)
        return

    size = "medium"
    command_start = 1
    if parts[1] in ("small", "medium", "large"):
        size = parts[1]
        command_start = 2

    command_names = parts[command_start:-1] if len(parts) > command_start + 1 else [parts[command_start]]
    search_term = parts[-1] if len(parts) > command_start + 1 else None

    # Thông báo đang xử lý
    client.sendMessage(Message(text="⏳ Đang tạo ảnh code..."), thread_id, thread_type)

    combined_content = ""
    for command_name in command_names:
        content = read_command_content(command_name)
        if content is None:
            client.replyMessage(Message(text=f"❌ Không tìm thấy '{command_name}'."), message_object, thread_id, thread_type)
            return
        combined_content += f"# --- {command_name}.py ---\n{content}\n\n"

    try:
        # Tải logo Python nếu cần
        await fetch_python_logo()

        # Chia nhỏ nội dung nếu quá lớn
        code_lines = combined_content.splitlines()
        total_lines = len(code_lines)
        total_parts = (total_lines + MAX_LINES_PER_IMAGE - 1) // MAX_LINES_PER_IMAGE  # Tính số phần

        image_paths = []
        start_time = time.time()

        for part in range(total_parts):
            start_idx = part * MAX_LINES_PER_IMAGE
            end_idx = min((part + 1) * MAX_LINES_PER_IMAGE, total_lines)
            part_lines = code_lines[start_idx:end_idx]

            image_path, img_width, img_height = create_image_from_code(
                part_lines, "_".join(command_names), size, search_term, part + 1, total_parts
            )
            image_paths.append((image_path, img_width, img_height))

        elapsed_time = time.time() - start_time

        # Gửi từng ảnh
        for part, (image_path, img_width, img_height) in enumerate(image_paths, 1):
            if os.path.exists(image_path):
                msg = f"✅ Đã tạo ảnh cho {', '.join(command_names)} (Phần {part}/{total_parts}, {total_lines} dòng, {elapsed_time:.2f}s)"
                client.sendLocalImage(
                    image_path,
                    message=Message(text=msg),
                    thread_id=thread_id,
                    thread_type=thread_type,
                    width=img_width,
                    height=img_height,
                    ttl=60000
                )
                os.remove(image_path)
            await asyncio.sleep(1)  # Delay nhẹ để tránh gửi quá nhanh

    except Exception as e:
        client.replyMessage(Message(text=f"⚠ Lỗi: {str(e)}"), message_object, thread_id, thread_type)

def get_mitaizl():
    return {
        'code.view': lambda *args: asyncio.run(handle_viewcode_command(*args))
    }