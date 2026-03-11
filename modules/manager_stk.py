from zlapi.models import Message
import requests
import json
import urllib.parse
import io
import os
import math
from PIL import Image, ImageDraw, ImageFont
import cv2

# Thông tin mô tả
des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Tạo sticker từ ảnh và video",
    'tính năng': [
        "📷 Tải ảnh qua URL.",
        "🎥 Tạo sticker từ video.",
        "🔍 Kiểm tra và xử lý URL ảnh/video hợp lệ.",
        "🔗 Chuyển đổi ảnh sang định dạng WEBP (với góc bo tròn) và tải lên Catbox.",
        "🖼️ Gửi sticker đã tạo từ ảnh/video.",
        "💾 Lưu sticker đã tạo vào danh sách.",
        "📜 Xem danh sách sticker đã lưu dưới dạng ảnh lớn.",
        "🗑️ Xóa sticker khỏi danh sách (hỗ trợ xóa nhiều và xóa tất cả).",
        "📤 Gửi sticker đã lưu bằng ID (hỗ trợ gửi nhiều).",
        "🔔 Thông báo lỗi cụ thể nếu có vấn đề xảy ra khi xử lý ảnh/video."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh stktn và reply vào ảnh hoặc video cần tạo sticker.",
        "📌 Ví dụ: stktn và reply vào ảnh/video để tạo sticker.",
        "✅ Nhận thông báo trạng thái và kết quả tạo sticker ngay lập tức.",
        "📜 Xem danh sách sticker: xemstk",
        "🗑️ Xóa sticker: xoastk <ID> hoặc xoastk all để xóa tất cả",
        "📤 Gửi sticker: guistk <ID> hoặc guistk <ID1> <ID2> ... để gửi nhiều"
    ]
}

# Đường dẫn đến file lưu sticker
STICKER_FILE = 'stickers.json'

# --- Các hàm quản lý sticker ---

def load_stickers():
    if os.path.exists(STICKER_FILE):
        with open(STICKER_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_sticker(static_url, animation_url):
    stickers = load_stickers()
    sticker_id = 1 if not stickers else max(map(int, stickers.keys())) + 1
    stickers[sticker_id] = {'static_url': static_url, 'animation_url': animation_url}
    with open(STICKER_FILE, 'w') as f:
        json.dump(stickers, f)
    return sticker_id

def delete_sticker(sticker_id):
    stickers = load_stickers()
    if str(sticker_id) in stickers:
        del stickers[str(sticker_id)]
        with open(STICKER_FILE, 'w') as f:
            json.dump(stickers, f)
        return True
    return False

def delete_multiple_stickers(id_list):
    stickers = load_stickers()
    deleted_count = 0
    for sticker_id in id_list:
        if str(sticker_id) in stickers:
            del stickers[str(sticker_id)]
            deleted_count += 1
    if deleted_count > 0:
        with open(STICKER_FILE, 'w') as f:
            json.dump(stickers, f)
    return deleted_count

def delete_all_stickers():
    with open(STICKER_FILE, 'w') as f:
        json.dump({}, f)
    return True

def send_saved_sticker(client, sticker_id, thread_id, thread_type):
    stickers = load_stickers()
    if str(sticker_id) in stickers:
        sticker = stickers[str(sticker_id)]
        try:
            client.sendCustomSticker(
                staticImgUrl=sticker['static_url'],
                animationImgUrl=sticker['animation_url'],
                thread_id=thread_id,
                thread_type=thread_type,
                ttl=60000
            )
            return True
        except Exception as e:
            print(f"Lỗi khi gửi sticker: {e}")
            return False
    return False

# --- Hàm kiểm tra định dạng URL ---
def is_valid_image_url(url):
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
    return any(url.lower().endswith(ext) for ext in valid_extensions)

def is_valid_video_url(url):
    valid_extensions = ['.mp4', '.avi', '.mov']
    return any(url.lower().endswith(ext) for ext in valid_extensions)

# --- Hàm bo tròn 4 góc của ảnh ---
def round_corners(im, rad):
    """
    Hàm bo tròn 4 góc của ảnh với bán kính rad.
    """
    im = im.convert("RGBA")
    mask = Image.new("L", im.size, 0)
    draw = ImageDraw.Draw(mask)
    width, height = im.size
    draw.rounded_rectangle([(0, 0), (width, height)], radius=rad, fill=255)
    im.putalpha(mask)
    return im

# --- Hàm chuyển đổi ảnh sang WEBP (với góc bo tròn) và upload lên Catbox ---
def convert_image_to_webp(image_path, radius=50):
    """
    Mở ảnh từ image_path, bo tròn 4 góc với bán kính radius,
    chuyển đổi ảnh sang định dạng WEBP và upload lên Catbox.
    """
    try:
        with Image.open(image_path) as image:
            image = round_corners(image, radius)
            buffered = io.BytesIO()
            image.save(buffered, format="WEBP")
            buffered.seek(0)
            return upload_to_catbox(buffered)
    except Exception as e:
        print(f"Lỗi khi chuyển đổi sang WEBP: {e}")
        return None

def upload_to_catbox(buffered_or_path):
    url = "https://catbox.moe/user/api.php"
    if isinstance(buffered_or_path, io.BytesIO):
        files = {'fileToUpload': ('image.webp', buffered_or_path, 'image/webp')}
    else:
        files = {'fileToUpload': open(buffered_or_path, 'rb')}
    data = {'reqtype': 'fileupload'}
    response = requests.post(url, files=files, data=data)
    if response.status_code == 200 and response.text.startswith("http"):
        return response.text
    print(f"Lỗi khi upload lên Catbox: {response.text}")
    return None

# --- Hàm chuyển đổi video sang GIF ---
def convert_video_to_gif(video_path):
    cap = cv2.VideoCapture(video_path)
    frames = []
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames.append(Image.fromarray(frame))
    cap.release()
    
    gif_path = "sticker.gif"
    if frames:
        frames[0].save(gif_path, save_all=True, append_images=frames[1:], loop=0)
        return gif_path
    return None

# --- Hàm tạo sticker từ video ---
def create_sticker_from_video(video_url, client, thread_id, thread_type):
    if not is_valid_video_url(video_url):
        client.sendMessage("Video không hợp lệ!", thread_id, thread_type, ttl=60000)
        return
    
    video_path = "temp_video.mp4"
    with open(video_path, 'wb') as f:
        f.write(requests.get(video_url).content)
    
    gif_path = convert_video_to_gif(video_path)
    if not gif_path:
        client.sendMessage("Không thể tạo GIF!", thread_id, thread_type, ttl=60000)
        return
    
    gif_url = upload_to_catbox(gif_path)
    if gif_url:
        client.sendCustomSticker(
            staticImgUrl=gif_url, animationImgUrl=gif_url,
            thread_id=thread_id,
            thread_type=thread_type,
            ttl=60000
        )
        sticker_id = save_sticker(gif_url, gif_url)
        client.sendMessage(
            Message(text=f"Sticker video đã được tạo và lưu với ID {sticker_id}!"),
            thread_id=thread_id,
            thread_type=thread_type,
            ttl=60000
        )
    else:
        client.sendMessage("Không thể tải GIF lên!", thread_id, thread_type, ttl=60000)
    
    if os.path.exists(gif_path):
        os.remove(gif_path)
    if os.path.exists(video_path):
        os.remove(video_path)

# --- Hàm xử lý lệnh tạo sticker ---
def handle_stk_command(message, message_object, thread_id, thread_type, author_id, client):
    if message_object.quote:
        attach = message_object.quote.attach
        if attach:
            try:
                attach_data = json.loads(attach)
            except json.JSONDecodeError:
                client.sendMessage(Message(text="Dữ liệu không hợp lệ."), thread_id, thread_type, ttl=60000)
                return
            media_url = attach_data.get('hdUrl') or attach_data.get('href')
            if not media_url:
                client.sendMessage(Message(text="Không tìm thấy URL media."), thread_id, thread_type, ttl=60000)
                return
            media_url = media_url.replace("\\/", "/")
            media_url = urllib.parse.unquote(media_url)

            if is_valid_image_url(media_url):
                # Tải ảnh về lưu cục bộ (không xóa nền)
                try:
                    response = requests.get(media_url)
                    if response.status_code == 200:
                        temp_image_path = "temp_img.png"
                        with open(temp_image_path, "wb") as f:
                            f.write(response.content)
                        webp_image_url = convert_image_to_webp(temp_image_path, radius=50)
                        os.remove(temp_image_path)
                        if webp_image_url:
                            # Dùng webp_image_url cho cả static và animation
                            client.sendCustomSticker(
                                staticImgUrl=webp_image_url, animationImgUrl=webp_image_url,
                                thread_id=thread_id,
                                thread_type=thread_type,
                                ttl=60000
                            )
                            sticker_id = save_sticker(webp_image_url, webp_image_url)
                            client.sendMessage(
                                Message(text=f"Sticker đã được tạo và lưu với ID {sticker_id}!"),
                                thread_id=thread_id,
                                thread_type=thread_type,
                                ttl=60000
                            )
                        else:
                            client.sendMessage(Message(text="Không thể chuyển đổi hình ảnh."), thread_id, thread_type, ttl=60000)
                    else:
                        client.sendMessage(Message(text="Lỗi tải ảnh từ URL."), thread_id, thread_type, ttl=60000)
                except Exception as e:
                    client.sendMessage(Message(text=f"Lỗi tải ảnh: {e}"), thread_id, thread_type, ttl=60000)
            elif is_valid_video_url(media_url):
                create_sticker_from_video(media_url, client, thread_id, thread_type)
            else:
                client.sendMessage(Message(text="URL không phải ảnh/video hợp lệ."), thread_id, thread_type, ttl=60000)
        else:
            client.sendMessage(Message(text="Không có media nào được reply."), thread_id, thread_type, ttl=60000)
    else:
        client.sendMessage(Message(text="Hãy reply vào ảnh hoặc video."), thread_id, thread_type, ttl=60000)

# --- Hàm xem danh sách sticker đã lưu ---
def handle_xem_sticker(message, message_object, thread_id, thread_type, author_id, client):
    stickers = load_stickers()
    if not stickers:
        client.sendMessage(Message(text="Chưa có sticker nào được lưu."), thread_id, thread_type, ttl=60000)
        return

    num_stickers = len(stickers)
    grid_size = math.ceil(math.sqrt(num_stickers))
    sticker_size = 100
    large_image_size = grid_size * sticker_size
    large_image = Image.new('RGB', (large_image_size, large_image_size), color='white')
    draw = ImageDraw.Draw(large_image)
    font = ImageFont.load_default()

    for index, (sticker_id, sticker) in enumerate(stickers.items()):
        static_url = sticker['static_url']
        try:
            response = requests.get(static_url)
            if response.status_code == 200:
                sticker_image = Image.open(io.BytesIO(response.content)).resize((sticker_size, sticker_size))
                x = (index % grid_size) * sticker_size
                y = (index // grid_size) * sticker_size
                large_image.paste(sticker_image, (x, y))

                circle_diameter = 20
                circle_x, circle_y = x + 5, y + 5
                draw.ellipse(
                    (circle_x, circle_y, circle_x + circle_diameter, circle_y + circle_diameter),
                    fill='white', outline='black'
                )

                id_text = str(sticker_id)
                text_bbox = draw.textbbox((0, 0), id_text, font=font)
                text_x = circle_x + (circle_diameter - (text_bbox[2] - text_bbox[0])) / 2
                text_y = circle_y + (circle_diameter - (text_bbox[3] - text_bbox[1])) / 2
                draw.text((text_x, text_y), id_text, fill='black', font=font)
        except Exception as e:
            print(f"Lỗi khi tải sticker ID {sticker_id}: {e}")

    temp_image_path = 'temp_sticker_grid.png'
    large_image.save(temp_image_path)
    client.sendLocalImage(
        imagePath=temp_image_path,
        thread_id=thread_id,
        thread_type=thread_type,
        width=large_image_size,
        height=large_image_size,
        message=Message(text="Danh sách sticker"),
        ttl=60000
    )
    os.remove(temp_image_path)

# --- Hàm xóa sticker ---
def handle_xoa_sticker(message, message_object, thread_id, thread_type, author_id, client):
    parts = message.split()
    if len(parts) >= 2:
        if parts[1].lower() == "all":
            delete_all_stickers()
            client.sendMessage(Message(text="Đã xóa tất cả sticker."), thread_id, thread_type, ttl=60000)
        else:
            id_list = parts[1:]
            deleted_count = delete_multiple_stickers(id_list)
            if deleted_count > 0:
                client.sendMessage(Message(text=f"Đã xóa {deleted_count} sticker."), thread_id, thread_type, ttl=60000)
            else:
                client.sendMessage(Message(text="Không có sticker nào được xóa."), thread_id, thread_type, ttl=60000)
    else:
        client.sendMessage(Message(text="Vui lòng cung cấp ID hoặc 'all'."), thread_id, thread_type, ttl=60000)

# --- Hàm gửi sticker đã lưu theo ID ---
def handle_gui_sticker(message, message_object, thread_id, thread_type, author_id, client):
    parts = message.split()
    if len(parts) >= 2:
        id_list = parts[1:]
        sent_count = sum(send_saved_sticker(client, sticker_id, thread_id, thread_type) for sticker_id in id_list)
        if sent_count > 0:
            client.sendMessage(Message(text=f"Đã gửi {sent_count} sticker."), thread_id, thread_type, ttl=60000)
        else:
            client.sendMessage(Message(text="Không có sticker nào được gửi."), thread_id, thread_type, ttl=60000)
    else:
        client.sendMessage(Message(text="Vui lòng cung cấp ít nhất một ID."), thread_id, thread_type, ttl=60000)

# --- Định nghĩa các lệnh ---
def get_mitaizl():
    return {
        'getstk1': handle_stk_command,
        'xemstk1': handle_xem_sticker,
        'xoastk1': handle_xoa_sticker,
        'stk1': handle_gui_sticker
    }
