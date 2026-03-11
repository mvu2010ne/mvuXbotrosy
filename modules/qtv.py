import json
import os
import logging
import config
import random
import time
from zlapi.models import Message, MessageStyle, MultiMsgStyle
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import colorsys
import numpy as np
import requests
from io import BytesIO

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ID duy nhất được phép sử dụng lệnh
SUPER_ADMIN_ID = "3299675674241805615"
des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🔧 Quản lý danh sách Quản Trị Viên cấp cao trong file config.py.",
    'tính năng': [
        "➕ Thêm người dùng vào danh sách Quản Trị Viên cấp cao bằng ID hoặc tag người dùng.",
        "➖ Xóa người dùng khỏi danh sách Quản Trị Viên cấp cao bằng ID hoặc tag người dùng.",
        "📋 Liệt kê danh sách Quản Trị Viên cấp cao hiện tại với số thứ tự, tên và ID.",
        "🔒 Chỉ super admin (ID: 5183937580782706480) được phép sử dụng.",
        "💾 Cập nhật trực tiếp tập hợp ADMIN trong file config.py."
    ],
    'hướng dẫn sử dụng': [
        f"📩 Gửi lệnh `{config.PREFIX}qtv add <user_id>` hoặc tag người dùng để thêm vào Quản Trị Viên cấp cao.",
        f"📩 Gửi lệnh `{config.PREFIX}qtv del <user_id>` hoặc tag người dùng để xóa khỏi Quản Trị Viên cấp cao.",
        f"📩 Gửi lệnh `{config.PREFIX}qtv list` để xem danh sách Quản Trị Viên cấp cao.",
        f"📌 Ví dụ: `{config.PREFIX}qtv add 123456789` hoặc `{config.PREFIX}qtv del @UserName`.",
        "✅ Nhận phản hồi với định dạng đẹp và tự xóa sau 30 giây."
    ]
}

# Đường dẫn file config.py
CONFIG_FILE = "config.py"

# ====================== CÁC HÀM HỖ TRỢ TẠO ẢNH ======================
def BackgroundGetting():
    """Lấy ảnh nền ngẫu nhiên"""
    try:
        bg_urls = [
            "https://picsum.photos/1500/800",
            "https://source.unsplash.com/random/1500x800",
        ]
        response = requests.get(random.choice(bg_urls), timeout=10)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))
    except:
        return None

def Dominant(image):
    """Lấy màu chủ đạo từ ảnh"""
    try:
        image = image.resize((100, 100))
        image_array = np.array(image)
        pixels = image_array.reshape(-1, 3)
        unique_colors, counts = np.unique(pixels, axis=0, return_counts=True)
        dominant_color = unique_colors[np.argmax(counts)]
        return tuple(dominant_color)
    except:
        return (130, 190, 255)

def make_round_avatar(image):
    """Tạo avatar hình tròn"""
    mask = Image.new('L', image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, image.size[0], image.size[1]), fill=255)
    result = Image.new('RGBA', image.size, (0, 0, 0, 0))
    result.paste(image, (0, 0), mask)
    return result

def get_random_gradient():
    """Tạo gradient ngẫu nhiên"""
    gradients = [
        [(255, 0, 0), (255, 165, 0), (255, 255, 0)],
        [(0, 255, 0), (0, 255, 255), (0, 0, 255)],
        [(255, 0, 255), (128, 0, 128), (75, 0, 130)],
        [(255, 192, 203), (255, 105, 180), (199, 21, 133)],
        [(135, 206, 250), (0, 191, 255), (30, 144, 255)],
    ]
    return random.choice(gradients)

# Gradient sets cho text
GRADIENT_SETS = [
    [(255, 0, 0), (255, 165, 0), (255, 255, 0)],
    [(0, 255, 0), (0, 255, 255), (0, 0, 255)],
    [(255, 0, 255), (128, 0, 128), (75, 0, 130)],
]

MULTICOLOR_GRADIENT = [
    (255, 0, 0), (255, 165, 0), (255, 255, 0),
    (0, 255, 0), (0, 255, 255), (0, 0, 255),
    (255, 0, 255), (128, 0, 128)
]

def draw_mixed_gradient_text(draw, text, position, normal_font, emoji_font, gradient_colors, shadow_offset=(2, 2)):
    """Vẽ text với gradient và shadow"""
    x, y = position
    
    # Vẽ shadow
    shadow_color = (0, 0, 0, 128)
    draw.text((x + shadow_offset[0], y + shadow_offset[1]), text, font=normal_font, fill=shadow_color)
    
    # Vẽ text với gradient
    text_bbox = draw.textbbox((0, 0), text, font=normal_font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    for i, char in enumerate(text):
        char_bbox = draw.textbbox((0, 0), char, font=normal_font)
        char_width = char_bbox[2] - char_bbox[0]
        
        # Chọn màu từ gradient
        color_idx = int((i / len(text)) * len(gradient_colors))
        color = gradient_colors[color_idx % len(gradient_colors)]
        
        # Vẽ ký tự
        draw.text((x, y), char, font=normal_font, fill=color)
        x += char_width

def create_admin_list_image(admin_list, client):
    print("Bắt đầu tạo ảnh danh sách admin...")
    
    WIDTH = 1500
    HEIGHT = 460
    AVATAR_SIZE = 200
    OVERLAY_HEIGHT = 180
    OVERLAY_SPACING = 40
    BORDER_THICKNESS = 15
    TITLE_OVERLAY_HEIGHT = 140

    # Tính chiều cao cần thiết
    total_height = TITLE_OVERLAY_HEIGHT + OVERLAY_SPACING + len(admin_list) * (OVERLAY_HEIGHT + OVERLAY_SPACING) + 2 * BORDER_THICKNESS + 80
    HEIGHT = max(460, total_height)
    print(f"Kích thước ảnh: {WIDTH}x{HEIGHT}, Số admin: {len(admin_list)}")

    # 1) Tạo nền ảnh
    print("Tạo nền ảnh...")
    bg_image = BackgroundGetting()
    if not bg_image:
        print("Không lấy được nền, sử dụng màu mặc định (130, 190, 255)")
        bg_image = Image.new("RGB", (WIDTH, HEIGHT), (130, 190, 255))
    bg_image = bg_image.convert("RGBA").resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    bg_image = bg_image.filter(ImageFilter.GaussianBlur(radius=20))
    print("Đã tạo và xử lý nền ảnh thành công")

    # 2) Tạo lớp phủ với hình chữ nhật bo góc
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    dominant_color = Dominant(bg_image)
    luminance = (0.299 * dominant_color[0] + 0.587 * dominant_color[1] + 0.114 * dominant_color[2]) / 255
    box_color = random.choice([
        (120, 200, 180, 100), (180, 140, 200, 100), (240, 180, 160, 100),
        (160, 200, 140, 100), (200, 160, 120, 100), (140, 180, 220, 100),
        (220, 200, 140, 100), (180, 180, 180, 105)
    ]) if luminance >= 0.5 else random.choice([
        (200, 140, 160, 105), (140, 120, 180, 105), (100, 140, 160, 105),
        (160, 140, 120, 105), (120, 160, 180, 105), (60, 60, 60, 80)
    ])
    print(f"Màu overlay được chọn: {box_color}, luminance: {luminance}")

    box_x1, box_y1 = 50, 50
    box_x2, box_y2 = WIDTH - 50, HEIGHT - 50
    draw.rounded_rectangle([(box_x1, box_y1), (box_x2, box_y2)], radius=50, fill=box_color)
    print("Đã vẽ lớp phủ chính")

    # 3) Load font
    print("Tải font chữ...")
    font_top_path = "font/5.otf"
    font_emoji_path = "font/NotoEmoji-Bold.ttf"
    try:
        font_title = ImageFont.truetype(font_top_path, 120)
        font_text = ImageFont.truetype(font_top_path, 65)
        font_emoji = ImageFont.truetype(font_emoji_path, 65)
        print("Tải font thành công")
    except Exception as e:
        logging.error(f"Lỗi load font: {e}")
        print(f"Lỗi tải font: {e}, sử dụng font mặc định")
        font_title = font_text = font_emoji = ImageFont.load_default()

    # 4) Vẽ tiêu đề "DANH SÁCH ADMIN BOT"
    print("Vẽ tiêu đề...")
    title_text = "DANH SÁCH QTV CẤP CAO"
    random_gradients = random.sample(GRADIENT_SETS, 3)
    title_colors = MULTICOLOR_GRADIENT
    text_bbox = draw.textbbox((0, 0), title_text, font=font_title)
    title_width = text_bbox[2] - text_bbox[0]
    title_x = (WIDTH - title_width) // 2
    title_y = box_y1 + 20
    draw_mixed_gradient_text(
        draw, title_text, (title_x, title_y), normal_font=font_title, emoji_font=font_emoji,
        gradient_colors=title_colors, shadow_offset=(2, 2)
    )
    print("Đã vẽ tiêu đề thành công")

    # 5) Vẽ danh sách admin
    print("Bắt đầu vẽ danh sách admin...")
    y_offset = box_y1 + TITLE_OVERLAY_HEIGHT + OVERLAY_SPACING
    for i, admin in enumerate(admin_list):
        print(f"Xử lý admin {i+1}: {admin['name']} (ID: {admin['id']})")
        # Tạo overlay cho admin
        overlay_admin = Image.new("RGBA", (WIDTH - 100, OVERLAY_HEIGHT), (0, 0, 0, 0))
        draw_admin = ImageDraw.Draw(overlay_admin)
        draw_admin.rounded_rectangle(
            (0, 0, WIDTH - 100, OVERLAY_HEIGHT), radius=20, fill=box_color
        )
        overlay_admin = overlay_admin.filter(ImageFilter.GaussianBlur(radius=1))
        overlay.alpha_composite(overlay_admin, (50, y_offset))
        print(f"Đã tạo overlay cho admin {admin['name']}")

        # Tải và xử lý avatar
        print(f"Tải avatar từ URL: {admin['avatar_url']}")
        try:
            resp = requests.get(admin['avatar_url'], timeout=5)
            resp.raise_for_status()
            avatar = Image.open(BytesIO(resp.content)).convert("RGBA")
            avatar = avatar.resize((AVATAR_SIZE, AVATAR_SIZE), Image.Resampling.LANCZOS)
            avatar = make_round_avatar(avatar)
            border_size = AVATAR_SIZE + 30
            border_offset = (border_size - AVATAR_SIZE) // 2
            rainbow_border = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
            draw_border = ImageDraw.Draw(rainbow_border)
            for j in range(360):
                h = j / 360
                r, g, b = colorsys.hsv_to_rgb(h, 0.5, 0.8)
                draw_border.arc([(3, 3), (border_size - 4, border_size - 4)], j, j + 1, fill=(int(r * 255), int(g * 255), int(b * 255), 255), width=8)
            overlay.alpha_composite(rainbow_border, (70 - border_offset, y_offset + (OVERLAY_HEIGHT - border_size) // 2))
            overlay.alpha_composite(avatar, (70, y_offset + (OVERLAY_HEIGHT - AVATAR_SIZE) // 2))
            print(f"Đã xử lý avatar cho admin {admin['name']}")
        except Exception as e:
            logging.error(f"Lỗi tải avatar {admin['avatar_url']}: {e}")
            print(f"Lỗi tải avatar {admin['avatar_url']}: {e}, sử dụng avatar mặc định")
            avatar = Image.new("RGBA", (AVATAR_SIZE, AVATAR_SIZE), (200, 200, 200, 255))
            avatar = make_round_avatar(avatar)
            overlay.alpha_composite(avatar, (70, y_offset + (OVERLAY_HEIGHT - AVATAR_SIZE) // 2))

        # Vẽ tên và ID admin
        name_text = admin['name']
        id_text = f"ID: {admin['id']}"
        text_x = 70 + AVATAR_SIZE + 100
        name_y = y_offset + 30
        id_y = name_y + 70
        gradient_colors = random_gradients[i % len(random_gradients)]
        for text, y in [(name_text, name_y), (id_text, id_y)]:
            text_bbox = draw.textbbox((0, 0), text, font=font_text)
            text_width = text_bbox[2] - text_bbox[0]
            safe_text_width = box_x2 - text_x - 50
            truncated_text = text if text_width <= safe_text_width else text[:int(safe_text_width / (text_width / len(text)))] + ".."
            draw_mixed_gradient_text(
                draw, truncated_text, (text_x, y), normal_font=font_text, emoji_font=font_emoji,
                gradient_colors=gradient_colors, shadow_offset=(2, 2)
            )
        print(f"Đã vẽ tên và ID cho admin {admin['name']}")

        y_offset += OVERLAY_HEIGHT + OVERLAY_SPACING

    # 6) Vẽ logo và chữ "design by Minh Vũ Shinn Cte"
    print("Vẽ logo và chữ ký...")
    logo_path = "zalo.png"
    if os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo_size = 80
            logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
            mask = Image.new("L", (logo_size, logo_size), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, logo_size, logo_size), fill=255)
            round_logo = Image.new("RGBA", (logo_size, logo_size), (0, 0, 0, 0))
            round_logo.paste(logo, (0, 0), mask)
            overlay.paste(round_logo, (box_x1 + 50, HEIGHT - logo_size - 10), round_logo)
            print("Đã vẽ logo zalo.png")
        except Exception as e:
            logging.error(f"Lỗi xử lý logo zalo.png: {e}")
            print(f"Lỗi xử lý logo zalo.png: {e}")
    else:
        print("Không tìm thấy file logo zalo.png")

    designer_text = "design by Minh Vũ Shinn Cte"
    text_bbox = draw.textbbox((0, 0), designer_text, font=font_text)
    text_w = text_bbox[2] - text_bbox[0]
    designer_x = box_x2 - text_w - 30
    designer_y = HEIGHT - 90
    draw_mixed_gradient_text(
        draw, designer_text, (designer_x, designer_y), normal_font=font_text, emoji_font=font_emoji,
        gradient_colors=get_random_gradient(), shadow_offset=(2, 2)
    )
    print("Đã vẽ chữ ký 'design by Minh Vũ Shinn Cte'")

    # 7) Gộp và lưu ảnh
    print("Gộp và lưu ảnh...")
    final_image = Image.alpha_composite(bg_image, overlay).convert("RGB")
    image_path = f"admin_list_{random.randint(1000, 9999)}.jpg"
    try:
        final_image.save(image_path, quality=95)
        print(f"Đã lưu ảnh thành công tại: {image_path}")
        return image_path
    except Exception as e:
        logging.error(f"Lỗi khi lưu ảnh danh sách admin: {e}")
        print(f"Lỗi khi lưu ảnh: {e}")
        raise

# ====================== CÁC HÀM GỐC GIỮ NGUYÊN ======================
def is_valid_user_id(user_id):
    return user_id.isdigit()

def load_admin_ids():
    try:
        if not os.path.exists(CONFIG_FILE):
            return set()
        return config.ADMIN if isinstance(config.ADMIN, set) else set()
    except Exception as e:
        logging.error(f"Lỗi tải danh sách admin: {str(e)}")
        return set()

def save_admin_ids(admin_ids):
    try:
        if not os.path.exists(CONFIG_FILE):
            return False
        admin_ids = sorted(set(admin_ids))
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        new_admin_block = "ADMIN = {\n"
        for uid in admin_ids:
            new_admin_block += f" '{uid}',\n"
        new_admin_block += "}\n"
        import re
        if re.search(r"ADMIN\s*=\s*\{.*?\}", content, flags=re.S):
            content = re.sub(r"ADMIN\s*=\s*\{.*?\}", new_admin_block, content, flags=re.S)
        else:
            if not content.endswith("\n"):
                content += "\n"
            content += "\n" + new_admin_block
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        logging.info("Đã lưu danh sách ADMIN không trùng lặp vào config.py")
        return True
    except Exception as e:
        logging.error(f"Lỗi lưu danh sách admin: {e}")
        return False

def add_admin(user_id):
    if not is_valid_user_id(user_id):
        return False, f"⚠️ ID {user_id} không hợp lệ. ID phải là một chuỗi số."
    admin_ids = load_admin_ids()
    if user_id in admin_ids:
        return False, f"đã tồn tại trong danh sách Quản Trị Viên cấp cao"
    admin_ids.add(user_id)
    if save_admin_ids(admin_ids):
        return True, f"Đã thêm vào danh sách Quản Trị Viên cấp cao"
    return False, f"❌ Lỗi khi lưu danh sách Quản Trị Viên cấp cao."

def remove_admin(user_id):
    if not is_valid_user_id(user_id):
        return False, f"⚠️ ID {user_id} không hợp lệ. ID phải là một chuỗi số."
    admin_ids = load_admin_ids()
    if user_id not in admin_ids:
        return False, f"không tồn tại trong danh sách Quản Trị Viên cấp cao"
    if user_id == SUPER_ADMIN_ID:
        return False, f"❌ Không thể xóa super admin (ID: {user_id})."
    admin_ids.remove(user_id)
    if save_admin_ids(admin_ids):
        return True, f"Đã xóa khỏi danh sách Quản Trị Viên cấp cao"
    return False, f"❌ Lỗi khi lưu danh sách Quản Trị Viên cấp cao."

def send_reply_with_style(client, text, message_object, thread_id, thread_type, ttl=60000, color="#000000"):
    try:
        base_length = len(text)
        adjusted_length = base_length + 355
        style = MultiMsgStyle([
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
        msg = Message(text=text, style=style)
        logging.info(f"Đang gửi tin nhắn: {text}, TTL: {ttl}, Thread: {thread_id}, Type: {thread_type}")
        response = client.replyMessage(msg, message_object, thread_id, thread_type, ttl=ttl)
        logging.info(f"Phản hồi từ API: {response}")
        return response
    except Exception as e:
        logging.error(f"Lỗi gửi tin nhắn: {str(e)}")
        error_msg = Message(text="❌ Đã xảy ra lỗi khi gửi tin nhắn.")
        client.sendMessage(error_msg, thread_id, thread_type)
        return None

def fetch_target_info(target_input, message_object, client, command_prefix):
    if message_object.mentions and len(message_object.mentions) > 0:
        target_id = message_object.mentions[0]['uid']
    else:
        target_id = target_input.strip()
    if not target_id:
        return None
    try:
        info_response = client.fetchUserInfo(target_id)
        if not info_response:
            logging.error(f"Không nhận được phản hồi từ client.fetchUserInfo cho target {target_id}")
            return None
        profiles = info_response.unchanged_profiles or info_response.changed_profiles or {}
        target_info = profiles.get(str(target_id))
       
        if not target_info:
            logging.error(f"Không tìm thấy thông tin người dùng cho target {target_id}")
            return None
        if isinstance(target_info, dict):
            target_name = target_info.get("zaloName") or target_info.get("username") or target_info.get("name") or "Unknown"
        else:
            target_name = getattr(target_info, 'zaloName', None) or getattr(target_info, 'username', None) or getattr(target_info, 'name', None) or "Unknown"
       
        return target_id, str(target_name)
    except Exception as e:
        logging.error(f"Lỗi fetch thông tin cho target {target_id}: {e}")
        return None

def handle_admin_command(message, message_object, thread_id, thread_type, author_id, client):
    if author_id != SUPER_ADMIN_ID:
        error_msg = Message(text="❌ Chỉ Quản Trị Viên Tối Cao ( ---Minh Vũ Shinn Cte--- ) mới có quyền sử dụng lệnh này.")
        client.sendMessage(error_msg, thread_id, thread_type, ttl=10000)
        return

    command_parts = message.strip().split()
    if len(command_parts) < 2 or command_parts[0].lower() != f"{config.PREFIX}qtv":
        reply_text = f"❌ Cú pháp: {config.PREFIX}qtv <add|del|list> [user_id hoặc tag]."
        send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=60000)
        return

    action = command_parts[1].lower()
    param = " ".join(command_parts[2:]) if len(command_parts) > 2 else ""

    if action == "add":
        target = fetch_target_info(param, message_object, client, "qtv add")
        if target is None:
            reply_text = f"❌ Cú pháp: {config.PREFIX}qtv add <user_id> hoặc tag người dùng.\nKhông thể lấy thông tin người dùng."
            send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=60000)
            return
        target_id, target_name = target
        success, message = add_admin(target_id)
        if success:
            reply_text = f"✅ ✅ ✅ THÀNH CÔNG ✅ ✅ ✅ \nĐã thêm {target_name} vào danh sách Quản Trị Viên cấp cao\n🆔 {target_id}"
        else:
            reply_text = f"❌❌❌THẤT BẠI❌❌❌\n{target_name} {message}\n🆔 {target_id}"
        send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=60000)

    elif action == "del":
        target = fetch_target_info(param, message_object, client, "qtv del")
        if target is None:
            reply_text = f"❌ Cú pháp: {config.PREFIX}qtv del <user_id> hoặc tag người dùng.\nKhông thể lấy thông tin người dùng."
            send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=60000)
            return
        target_id, target_name = target
        success, message = remove_admin(target_id)
        if success:
            reply_text = f"✅ ✅ ✅ THÀNH CÔNG ✅ ✅ ✅ \nĐã xóa {target_name} khỏi danh sách Quản Trị Viên cấp cao\n🆔 {target_id}"
        else:
            reply_text = f"❌❌❌THẤT BẠI❌❌❌\n{target_name} {message}\n🆔 {target_id}"
        send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=60000)

    # PHẦN LIST ĐƯỢC THAY ĐỔI - GỬI ẢNH THAY VÌ TEXT
    elif action == "list":
        admin_ids = load_admin_ids()
        if not admin_ids:
            reply_text = "Danh sách Quản Trị Viên cấp cao trống."
            send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=60000)
            return

        admin_list = []
        for uid in sorted(admin_ids):
            try:
                info_response = client.fetchUserInfo(uid)
                profiles = info_response.changed_profiles or info_response.unchanged_profiles or {}
                user_info = profiles.get(str(uid), {})
                user_name = user_info.get('zaloName', 'Unknown') if isinstance(user_info, dict) else getattr(user_info, 'zaloName', 'Unknown')
                avatar = user_info.get('avatar') or user_info.get('thumbSrc') if isinstance(user_info, dict) else getattr(user_info, 'avatar', None) or getattr(user_info, 'thumbSrc', None)
            except Exception as e:
                logging.error(f"Lỗi fetch thông tin admin {uid}: {e}")
                user_name = "Unknown"
                avatar = None
            admin_list.append({"name": user_name, "id": uid, "avatar_url": avatar})

        try:
            image_path = create_admin_list_image(admin_list, client)
            
            # Đảm bảo file tồn tại
            if not os.path.exists(image_path):
                raise Exception("File ảnh không tồn tại")
                
            # Kiểm tra kích thước file
            file_size = os.path.getsize(image_path)
            print(f"Kích thước file: {file_size} bytes")
            
            if file_size > 10 * 1024 * 1024:  # > 10MB
                img = Image.open(image_path)
                img.save(image_path, "JPEG", quality=70)
                print("Đã nén ảnh để giảm kích thước")
            
            # Gửi bằng sendLocalImage
            client.sendLocalImage(
                imagePath=image_path,
                thread_id=thread_id,
                thread_type=thread_type, 
                message=Message(text="📋 Danh sách Quản Trị Viên Cấp Cao"),
                ttl=300000
            )
            
            print("✅ Đã gửi ảnh thành công")
            
            # Xóa file tạm
            os.remove(image_path)
                
        except Exception as e:
            logging.error(f"Lỗi gửi ảnh: {e}")
            # Fallback: gửi text nếu không gửi được ảnh
            reply_text = "Danh sách Quản Trị Viên cấp cao:\n"
            for idx, uid in enumerate(sorted(admin_ids), 1):
                try:
                    info_response = client.fetchUserInfo(uid)
                    profiles = info_response.changed_profiles or info_response.unchanged_profiles or {}
                    user_info = profiles.get(str(uid), {})
                    user_name = user_info.get('zaloName', 'Unknown') if isinstance(user_info, dict) else getattr(user_info, 'zaloName', 'Unknown')
                    admin_list.append(f"{idx}. 👤 {user_name}\n🆔 {uid}")
                except Exception as e:
                    logging.error(f"Lỗi fetch thông tin admin {uid}: {e}")
                    admin_list.append(f"{idx}. 👤 Unknown\n🆔 {uid}")
            reply_text += "\n".join(admin_list)
            send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=60000)

    else:
        reply_text = f"❌ Lệnh không hợp lệ. Cú pháp: {config.PREFIX}qtv <add|del|list> [user_id hoặc tag]."
        send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=60000)

def get_mitaizl():
    return {
        'qtv': handle_admin_command
    }