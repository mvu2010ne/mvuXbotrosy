import os
import math
import random
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from io import BytesIO
import base64
from zlapi.models import *
# ---------------------------
# Cấu hình
# ---------------------------
BACKGROUND_FOLDER = 'backgrounds'
if os.path.isdir(BACKGROUND_FOLDER):
    BACKGROUND_IMAGES = [
        os.path.join(BACKGROUND_FOLDER, f) 
        for f in os.listdir(BACKGROUND_FOLDER) 
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ]
else:
    BACKGROUND_IMAGES = []

# Các bộ màu gradient cho chữ
TEXT_GRADIENT_SETS = [
    [(255, 0, 255), (0, 255, 255), (255, 255, 0), (0, 255, 0)],  # Cyan-Magenta-Yellow-Green
    [(255, 0, 0), (255, 165, 0), (255, 255, 0)],  # Red-Orange-Yellow
    [(255, 182, 193), (173, 216, 230), (152, 251, 152)],  # Pink-LightBlue-LightGreen
    [(0, 255, 127), (0, 255, 255), (30, 144, 255)],  # SpringGreen-Cyan-Blue
    [(255, 105, 180), (138, 43, 226), (255, 20, 147)],  # HotPink-BlueViolet-DeepPink
]

# ---------------------------
# Hàm hỗ trợ
# ---------------------------
def get_background(width=800, height=600):
    """Lấy ảnh nền ngẫu nhiên hoặc tạo nền mặc định"""
    if BACKGROUND_IMAGES:
        bg_path = random.choice(BACKGROUND_IMAGES)
        try:
            bg = Image.open(bg_path).convert("RGB")
            bg = bg.resize((width, height), Image.Resampling.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(radius=8))
            return bg
        except:
            pass
    
    # Tạo nền gradient mặc định
    bg = Image.new("RGB", (width, height), (20, 30, 50))
    draw = ImageDraw.Draw(bg)
    for i in range(height):
        ratio = i / height
        r = int(20 + (100 * ratio))
        g = int(30 + (80 * ratio))
        b = int(50 + (120 * ratio))
        draw.line([(0, i), (width, i)], fill=(r, g, b))
    return bg

def get_font(size=100):
    """Lấy font chữ, ưu tiên font có sẵn"""
    font_paths = [
        "font/5.otf",
        "font/NotoEmoji-Bold.ttf"
    ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except:
                continue
    
    return ImageFont.load_default()

def get_gradient_color(colors, ratio):
    """Tính màu gradient"""
    if ratio <= 0:
        return colors[0]
    if ratio >= 1:
        return colors[-1]
    total_segments = len(colors) - 1
    segment = int(ratio * total_segments)
    segment_ratio = (ratio * total_segments) - segment
    c1, c2 = colors[segment], colors[segment + 1]
    return (
        int(c1[0] * (1 - segment_ratio) + c2[0] * segment_ratio),
        int(c1[1] * (1 - segment_ratio) + c2[1] * segment_ratio),
        int(c1[2] * (1 - segment_ratio) + c2[2] * segment_ratio)
    )

def create_text_frames(text, width=800, height=600, num_frames=60):
    """Tạo các frame cho GIF với text chạy"""
    # Lấy nền
    background = get_background(width, height)
    
    # Tạo font và tính kích thước text
    font = get_font(100)
    draw_temp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    bbox = draw_temp.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Tính toán vị trí bắt đầu để text chạy từ phải sang trái
    start_x = width + text_width  # Bắt đầu ngoài màn hình bên phải
    end_x = -text_width  # Kết thúc ngoài màn hình bên trái
    
    # Chọn bộ màu gradient cho text
    gradient_colors = random.choice(TEXT_GRADIENT_SETS)
    
    frames = []
    
    for frame_num in range(num_frames):
        # Tính vị trí x của text trong frame này
        progress = frame_num / (num_frames - 1)
        x_pos = start_x + (end_x - start_x) * progress
        y_pos = (height - text_height) // 2 + 20  # Căn giữa theo chiều dọc
        
        # Tạo frame mới
        frame = background.copy()
        draw = ImageDraw.Draw(frame)
        
        # Vẽ shadow cho text
        shadow_x = int(x_pos + 2)
        shadow_y = int(y_pos + 2)
        shadow_color = (0, 0, 0, 128)
        draw.text((shadow_x, shadow_y), text, font=font, fill=shadow_color)
        
        # Vẽ text với gradient màu
        for i, char in enumerate(text):
            char_x = x_pos + sum(draw.textlength(c, font=font) for c in text[:i])
            char_progress = (i / len(text)) * len(gradient_colors)
            char_color = get_gradient_color(gradient_colors, char_progress / len(gradient_colors))
            draw.text((char_x, y_pos), char, font=font, fill=char_color)
        
        frames.append(frame)
    
    return frames

def create_marquee_gif(text, output_path="cache/text_marquee.gif", width=800, height=600, num_frames=60, duration=50):
    """Tạo GIF với text chạy ngang (marquee)"""
    try:
        # Tạo thư mục cache nếu chưa có
        os.makedirs("cache", exist_ok=True)
        
        # Tạo các frame
        print(f"[DEBUG] Đang tạo {num_frames} frame cho text: '{text}'")
        frames = create_text_frames(text, width, height, num_frames)
        
        # Lưu GIF
        frames[0].save(
            output_path,
            save_all=True,
            append_images=frames[1:],
            duration=duration,
            loop=0,
            optimize=True,
            quality=85
        )
        
        print(f"[DEBUG] Đã tạo GIF thành công: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"[ERROR] Lỗi khi tạo GIF: {e}")
        return None

def upload_to_uguu(file_path):
    """Upload file lên Uguu.se"""
    url = "https://uguu.se/upload"
    try:
        import requests
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        with open(file_path, 'rb') as file:
            files = {'files[]': (os.path.basename(file_path), file)}
            response = requests.post(url, files=files, headers=headers, verify=False, timeout=15)
            response.raise_for_status()
            result = response.json()
            upload_url = result.get('files', [{}])[0].get('url')
            if upload_url:
                print(f"[DEBUG] Đã upload GIF lên Uguu: {upload_url}")
                return upload_url
            else:
                print(f"[ERROR] Không nhận được URL từ Uguu")
                return None
    except Exception as e:
        print(f"[ERROR] Lỗi khi upload lên Uguu: {e}")
        return None

def delete_file(file_path):
    """Xóa file tạm"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"[DEBUG] Đã xóa file: {file_path}")
    except Exception as e:
        print(f"[ERROR] Lỗi khi xóa file: {e}")

# ---------------------------
# Handler cho lệnh textgif
# ---------------------------
def handle_textgif_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh textgif"""
    try:
        # Phân tích lệnh
        content = message.strip().split(maxsplit=1)
        if len(content) < 2:
            error_msg = Message(text="🚫 Lỗi: Thiếu nội dung text\n\nCú pháp: textgif <nội dung>")
            client.replyMessage(error_msg, message_object, thread_id, thread_type, ttl=30000)
            return
        
        text_content = content[1].strip()
        if len(text_content) > 50:  # Giới hạn độ dài text
            text_content = text_content[:50] + "..."
            warning_msg = Message(text=f"⚠️ Text quá dài, đã được rút gọn thành:\n\"{text_content}\"")
            client.replyMessage(warning_msg, message_object, thread_id, thread_type, ttl=20000)
        
        client.sendReaction(message_object, "✨", thread_id, thread_type, reactionType=75)
        
        # Thông báo đang tạo
        processing_msg = Message(text=f"🎨 Đang tạo GIF với text:\n\"{text_content}\"")
        client.replyMessage(processing_msg, message_object, thread_id, thread_type, ttl=30000)
        
        # Tạo GIF
        gif_path = create_marquee_gif(text_content)
        if not gif_path:
            error_msg = Message(text="❌ Lỗi: Không thể tạo GIF")
            client.replyMessage(error_msg, message_object, thread_id, thread_type, ttl=30000)
            return
        
        # Upload lên Uguu
        gif_url = upload_to_uguu(gif_path)
        if not gif_url:
            error_msg = Message(text="❌ Lỗi: Không thể upload GIF")
            client.replyMessage(error_msg, message_object, thread_id, thread_type, ttl=30000)
            delete_file(gif_path)
            return
        
        # Gửi GIF thành công
        success_msg = Message(text=f"✅ Đã tạo GIF thành công!\n📝 Nội dung: \"{text_content}\"\n🎭 Hiệu ứng: Text chạy ngang")
        try:
            # Thử gửi như sticker trước
            client.sendCustomSticker(
                staticImgUrl=gif_url,
                animationImgUrl=gif_url,
                thread_id=thread_id,
                thread_type=thread_type,
                width=800,
                height=600,
                ttl=86400000  # 24 giờ
            )
            print(f"[DEBUG] Đã gửi GIF như sticker: {text_content}")
        except Exception as e1:
            print(f"[DEBUG] Không thể gửi như sticker: {e1}")
            try:
                # Fallback: gửi như ảnh
                client.sendRemoteImage(
                    imageUrl=gif_url,
                    thread_id=thread_id,
                    thread_type=thread_type,
                    width=800,
                    height=600,
                    ttl=86400000
                )
                print(f"[DEBUG] Đã gửi GIF như ảnh: {text_content}")
            except Exception as e2:
                print(f"[ERROR] Không thể gửi GIF: {e2}")
                error_msg = Message(text="❌ Lỗi: Không thể gửi GIF")
                client.replyMessage(error_msg, message_object, thread_id, thread_type, ttl=30000)
                delete_file(gif_path)
                return
        
        # Gửi thông báo thành công
        client.replyMessage(success_msg, message_object, thread_id, thread_type, ttl=30000)
        
        # Dọn dẹp file tạm
        delete_file(gif_path)
        
    except Exception as e:
        print(f"[ERROR] Lỗi trong handle_textgif: {e}")
        error_msg = Message(text="❌ Lỗi không xác định khi tạo GIF")
        client.replyMessage(error_msg, message_object, thread_id, thread_type, ttl=30000)

# ---------------------------
# Hàm chính để đăng ký lệnh
# ---------------------------
def get_mitaizl():
    """Trả về mapping các lệnh textgif"""
    return {
        'textgif': handle_textgif_command,
        '//textgif': handle_textgif_command  # Alias cho lệnh cũ
    }