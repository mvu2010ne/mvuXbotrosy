from zlapi.models import Message
import requests
import json
import urllib.parse
import io
import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import cv2
from moviepy.editor import VideoFileClip
from concurrent.futures import ThreadPoolExecutor

# Thông tin mô tả
des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Tạo sticker từ ảnh và video",
    'tính năng': [
        "📷 Xóa nền từ ảnh qua URL.",
        "🎥 Tạo sticker từ video.",
        "🔍 Kiểm tra và xử lý URL ảnh/video hợp lệ.",
        "🔗 Chuyển đổi ảnh sang định dạng WEBP và tải lên Uguu.",
        "🖼️ Gửi sticker đã tạo từ ảnh/video.",
        "💾 Lưu sticker đã tạo vào danh sách kèm width và height.",
        "📜 Xem danh sách sticker đã lưu dưới dạng ảnh lớn.",
        "🗑️ Xóa sticker khỏi danh sách (hỗ trợ xóa nhiều và xóa tất cả).",
        "📤 Gửi sticker đã lưu bằng ID (hỗ trợ gửi nhiều) với kích thước đúng.",
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

# Hàm quản lý sticker
def load_stickers():
    if os.path.exists(STICKER_FILE):
        with open(STICKER_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_sticker(static_url, animation_url, loai='image', width=None, height=None):
    stickers = load_stickers()
    sticker_id = 1 if not stickers else max(map(int, stickers.keys())) + 1
    stickers[sticker_id] = {
        'static_url': static_url,
        'animation_url': animation_url,
        'loai': loai,
        'width': width,   # Lưu chiều rộng
        'height': height  # Lưu chiều cao
    }
    with open(STICKER_FILE, 'w') as f:
        json.dump(stickers, f)
    return sticker_id

def renumber_stickers():
    stickers = load_stickers()
    if not stickers:
        return
    # Tạo danh sách sticker mới với ID đánh số lại
    new_stickers = {}
    for index, (old_id, sticker_data) in enumerate(sorted(stickers.items(), key=lambda x: int(x[0])), 1):
        new_stickers[str(index)] = sticker_data
    # Lưu danh sách mới
    with open(STICKER_FILE, 'w') as f:
        json.dump(new_stickers, f)

# Hàm xóa một sticker
def delete_sticker(sticker_id):
    stickers = load_stickers()
    if str(sticker_id) in stickers:
        del stickers[str(sticker_id)]
        with open(STICKER_FILE, 'w') as f:
            json.dump(stickers, f)
        renumber_stickers()  # Đánh số lại sau khi xóa
        return True
    return False

# Hàm xóa nhiều sticker
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
        renumber_stickers()  # Đánh số lại sau khi xóa
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
                width=sticker.get('width'),   # Sử dụng width đã lưu
                height=sticker.get('height'), # Sử dụng height đã lưu
                ttl=600000
            )
            return True
        except Exception as e:
            print(f"Lỗi khi gửi sticker: {e}")
            return False
    return False

def get_content_type(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        return response.headers.get('Content-Type', '')
    except Exception as e:
        print(f"Lỗi khi lấy Content-Type: {e}")
        return ''

def is_valid_image_url(url):
    content_type = get_content_type(url)
    return content_type.startswith('image/')

def is_valid_video_url(url):
    content_type = get_content_type(url)
    return content_type.startswith('video/')

def is_valid_gif_url(url):
    content_type = get_content_type(url)
    return content_type == 'image/gif'

# Hàm chuyển đổi ảnh sang WEBP và upload lên Uguu
def convert_image_to_webp(image_url):
    try:
        response = requests.get(image_url)
        if response.status_code == 200:
            image = Image.open(io.BytesIO(response.content))
            temp_filename = "temp_image.webp"
            image.save(temp_filename, format="WEBP")
            webp_url = upload_to_uguu(temp_filename, content_type='image/webp')
            os.remove(temp_filename)
            return webp_url
    except Exception as e:
        print(f"Lỗi khi chuyển đổi sang WEBP: {e}")
        return None

def convert_gif_to_animated_webp(gif_url):
    try:
        response = requests.get(gif_url)
        if response.status_code == 200:
            gif = Image.open(io.BytesIO(response.content))
            temp_filename = "temp_animated.webp"
            frames = []
            try:
                while True:
                    frame = gif.copy()
                    frames.append(frame.convert('RGBA'))
                    gif.seek(gif.tell() + 1)
            except EOFError:
                pass

            if len(frames) == 1:
                frames[0].save(temp_filename, format="WEBP")
            else:
                frames[0].save(
                    temp_filename,
                    format="WEBP",
                    append_images=frames[1:],
                    save_all=True,
                    duration=gif.info.get('duration', 100),
                    loop=0
                )

            webp_url = upload_to_uguu(temp_filename, content_type='image/webp')
            os.remove(temp_filename)
            return webp_url
    except Exception as e:
        print(f"Lỗi khi chuyển đổi GIF sang WEBP động: {e}")
        return None

def upload_to_uguu(file_path, content_type='image/webp'):
    print("==> Uploading to Uguu:", file_path)
    try:
        with open(file_path, 'rb') as f:
            files = {'files[]': (os.path.basename(file_path), f, content_type)}
            response = requests.post("https://uguu.se/upload.php", files=files, timeout=30)
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('success') and response_data.get('files'):
                    print(f"==> Upload thành công: {response_data['files'][0]['url']}")
                    return response_data['files'][0]['url']
                else:
                    print("==> Lỗi: Phản hồi từ Uguu không chứa URL hợp lệ")
                    return None
            else:
                print(f"==> Lỗi: Mã trạng thái HTTP {response.status_code}")
                return None
    except Exception as e:
        print(f"==> Lỗi upload Uguu: {e}")
        return None

# Hàm tạo sticker từ video
def create_sticker_from_video(media_url, client, thread_id, thread_type):
    print("==> Tải video về...")
    try:
        video_response = requests.get(media_url)
        if video_response.status_code != 200:
            raise Exception("Không tải được video.")

        video_path = "temp_video.mp4"
        with open(video_path, "wb") as f:
            f.write(video_response.content)

        print("==> Lấy thông tin video và cắt clip...")
        with VideoFileClip(video_path) as clip:
            duration = min(clip.duration, 30)
            clip = clip.subclip(0, duration).resize(height=200)
            new_width, new_height = clip.size

        webp_path = "sticker.webp"
        os.system(f"ffmpeg -y -i {video_path} -vf \"scale={new_width}:{new_height},fps=10\" -loop 0 -an {webp_path}")

        thumbnail_path = "thumbnail.png"
        with VideoFileClip(video_path) as clip:
            clip.save_frame(thumbnail_path, t=0.5)

        if not os.path.exists(webp_path):
            raise Exception("Chuyển sang animated WEBP thất bại.")

        print("==> Upload file animated WEBP lên Uguu...")
        webp_url = upload_to_uguu(webp_path, content_type='image/webp')

        print("==> Upload thumbnail lên Uguu...")
        static_url = upload_to_uguu(thumbnail_path, content_type='image/png')

        if webp_url and static_url:
            print("==> Gửi sticker dạng video...")
            client.sendCustomSticker(
                staticImgUrl=static_url,
                animationImgUrl=webp_url,
                thread_id=thread_id,
                thread_type=thread_type,
                width=new_width,
                height=new_height,
                ttl=600000
            )
            sticker_id = save_sticker(static_url, webp_url, loai='video', width=new_width, height=new_height)
            client.sendMessage(Message(text=f"Sticker video đã tạo và lưu với ID {sticker_id}!"),
                               thread_id=thread_id, thread_type=thread_type, ttl=60000)
        else:
            raise Exception("Không thể upload video hoặc thumbnail.")

    except Exception as e:
        print("Lỗi khi xử lý video:", e)
        client.sendMessage(Message(text=f"Đã xảy ra lỗi: {e}"),
                           thread_id=thread_id, thread_type=thread_type, ttl=60000)
    finally:
        for f in ["temp_video.mp4", "sticker.webp", "thumbnail.png"]:
            if os.path.exists(f):
                os.remove(f)

# Hàm xử lý lệnh tạo sticker từ ảnh/video
def handle_stk_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản hồi emoji "✅" xác nhận đã nhận lệnh
    action = "✅ "
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    print("==> Vào lệnh handle_stk_command")
    
    media_url = None
    is_gif = False
    width = None
    height = None
    static_url = None

    # Kiểm tra nếu tin nhắn là reply
    if message_object.quote:
        attach = message_object.quote.attach
        if attach:
            try:
                attach_data = json.loads(attach)
                media_url = attach_data.get('hdUrl') or attach_data.get('href')
                if media_url:
                    media_url = urllib.parse.unquote(media_url.replace("\\/", "/"))
                    # Chuyển đổi link từ .jxl sang .jpg
                    if media_url.endswith('.jxl'):
                        media_url = media_url.replace('/jxl/', '/jpg/').replace('.jxl', '.jpg')
                    print(f"==> Media URL từ reply: {media_url}")
                
                # Lấy static_url từ thumb hoặc thumbUrl nếu có
                static_url = attach_data.get('thumb') or attach_data.get('thumbUrl')
                if static_url and static_url.endswith('.jxl'):
                    static_url = static_url.replace('/jxl/', '/jpg/').replace('.jxl', '.jpg')
                
                # Kiểm tra nếu là GIF dựa trên action
                if attach_data.get('action') == 'recommend.gif':
                    is_gif = True
                
                # Lấy kích thước từ params nếu có
                if attach_data.get('params'):
                    params = json.loads(attach_data['params'])
                    width = params.get('width')
                    height = params.get('height')
            except Exception as e:
                print("==> Lỗi đọc attach:", e)
                client.sendMessage(Message(text="Dữ liệu không hợp lệ."), thread_id, thread_type, ttl=60000)
                return

    # Kiểm tra nếu người dùng nhập URL trực tiếp
    if not media_url:
        parts = message.split()
        if len(parts) >= 2:
            media_url = parts[1]
            # Chuyển đổi link từ .jxl sang .jpg
            if media_url.endswith('.jxl'):
                media_url = media_url.replace('/jxl/', '/jpg/').replace('.jxl', '.jpg')
            print(f"==> Media URL từ lệnh: {media_url}")
        else:
            client.sendMessage(Message(text="Hãy reply vào ảnh/video/GIF hoặc nhập link."), thread_id, thread_type, ttl=60000)
            return

    if not media_url:
        client.sendMessage(Message(text="Không tìm thấy URL media."), thread_id, thread_type, ttl=60000)
        return

    # Xử lý GIF
    if is_gif or is_valid_gif_url(media_url):
        print("==> Đang xử lý GIF...")
        try:
            response = requests.get(media_url)
            if response.status_code == 200:
                gif_image = Image.open(io.BytesIO(response.content))
                # Sử dụng kích thước từ params nếu có, nếu không lấy từ image.size
                width = width or gif_image.size[0]
                height = height or gif_image.size[1]
                webp_url = convert_gif_to_animated_webp(media_url)
                if webp_url:
                    client.sendCustomSticker(
                        staticImgUrl=static_url or media_url,
                        animationImgUrl=webp_url,
                        thread_id=thread_id,
                        thread_type=thread_type,
                        width=width,
                        height=height,
                        ttl=600000
                    )
                    sticker_id = save_sticker(static_url or media_url, webp_url, loai='gif', width=width, height=height)
                    client.sendMessage(Message(text=f"Sticker GIF đã được tạo và lưu với ID {sticker_id}!"),
                                       thread_id=thread_id, thread_type=thread_type, ttl=60000)
                else:
                    client.sendMessage(Message(text="Không thể chuyển đổi GIF."), thread_id, thread_type, ttl=60000)
        except Exception as e:
            print("==> Lỗi xử lý GIF:", e)
            client.sendMessage(Message(text=f"Đã xảy ra lỗi khi xử lý GIF: {e}"), thread_id, thread_type, ttl=60000)

    # Xử lý ảnh tĩnh
    elif is_valid_image_url(media_url):
        print("==> Đang xử lý ảnh...")
        try:
            response = requests.get(media_url)
            if response.status_code == 200:
                image = Image.open(io.BytesIO(response.content))
                width = width or image.size[0]
                height = height or image.size[1]
                webp_image_url = convert_image_to_webp(media_url)
                if webp_image_url:
                    client.sendCustomSticker(
                        staticImgUrl=media_url,
                        animationImgUrl=webp_image_url,
                        thread_id=thread_id,
                        thread_type=thread_type,
                        width=width,
                        height=height,
                        ttl=600000
                    )
                    sticker_id = save_sticker(media_url, webp_image_url, loai='image', width=width, height=height)
                    client.sendMessage(Message(text=f"Sticker đã được tạo và lưu với ID {sticker_id}!"),
                                       thread_id=thread_id, thread_type=thread_type, ttl=60000)
                else:
                    client.sendMessage(Message(text="Không thể chuyển đổi hình ảnh."), thread_id, thread_type, ttl=60000)
        except Exception as e:
            print("==> Lỗi xử lý ảnh:", e)
            client.sendMessage(Message(text=f"Đã xảy ra lỗi khi xử lý ảnh: {e}"), thread_id, thread_type, ttl=60000)

    # Xử lý video
    elif is_valid_video_url(media_url):
        print("==> Đang xử lý video...")
        create_sticker_from_video(media_url, client, thread_id, thread_type)

    else:
        print("==> URL không phải ảnh, GIF hoặc video hợp lệ.")
        client.sendMessage(Message(text="URL không phải ảnh, GIF hoặc video hợp lệ."), thread_id, thread_type, ttl=60000)

def handle_xem_sticker(message, message_object, thread_id, thread_type, author_id, client):
    action = "✅ "
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    stickers = load_stickers()
    if not stickers:
        client.sendMessage(Message(text="Chưa có sticker nào được lưu."), thread_id, thread_type, ttl=60000)
        return

    num_stickers = len(stickers)
    grid_size = math.ceil(math.sqrt(num_stickers))
    sticker_size = 120
    padding = 10
    large_image_size = grid_size * (sticker_size + padding) + padding
    large_image = Image.new('RGB', (large_image_size, large_image_size), color='#F0F2F5')
    draw = ImageDraw.Draw(large_image)
    font = ImageFont.truetype("Archivo_Condensed-Bold.ttf", 12) if os.path.exists("Archivo_Condensed-Bold.ttf") else ImageFont.load_default()

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'image/webp,image/png,image/jpeg,*/*;q=0.8',
        'Referer': 'https://uguu.se/'
    }

    def download_sticker(sticker_id, static_url):
        try:
            print(f"Đang tải static_url cho sticker ID {sticker_id}: {static_url}")
            response = requests.get(static_url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"Lỗi: Mã trạng thái {response.status_code} cho sticker ID {sticker_id}")
                raise Exception(f"HTTP error {response.status_code}")
            content_type = response.headers.get('Content-Type', '')
            if not content_type.startswith('image/'):
                print(f"Lỗi: Content-Type không phải hình ảnh cho sticker ID {sticker_id}: {content_type}")
                raise Exception(f"Invalid Content-Type: {content_type}")
            sticker_image = Image.open(io.BytesIO(response.content)).resize((sticker_size, sticker_size))
            return sticker_id, sticker_image
        except Exception as e:
            print(f"Lỗi khi tải sticker ID {sticker_id}: {e}")
            return sticker_id, None

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(download_sticker, sticker_id, sticker['static_url'])
            for sticker_id, sticker in stickers.items()
        ]
        sticker_images = {sticker_id: img for sticker_id, img in [f.result() for f in futures]}

    for index, (sticker_id, sticker) in enumerate(stickers.items()):
        x = padding + (index % grid_size) * (sticker_size + padding)
        y = padding + (index // grid_size) * (sticker_size + padding)
        
        sticker_image = sticker_images.get(sticker_id)
        if sticker_image:
            shadow = Image.new('RGBA', (sticker_size + 10, sticker_size + 10), (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow)
            shadow_draw.rectangle([5, 5, sticker_size + 5, sticker_size + 5], fill=(0, 0, 0, 80))
            shadow = shadow.filter(ImageFilter.GaussianBlur(3))
            large_image.paste(shadow, (x - 5, y - 5), shadow)
            large_image.paste(sticker_image, (x, y))
            draw.rectangle([x, y, x + sticker_size, y + sticker_size], outline='#D1D5DB', width=2)
        else:
            draw.rectangle((x, y, x + sticker_size, y + sticker_size), fill='#E5E7EB', outline='#D1D5DB', width=2)

        circle_diameter = 24
        circle_x, circle_y = x + 5, y + 5
        draw.ellipse(
            (circle_x - 2, circle_y - 2, circle_x + circle_diameter + 2, circle_y + circle_diameter + 2),
            fill='orange', outline='orange', width=1
        )
        draw.ellipse(
            (circle_x, circle_y, circle_x + circle_diameter, circle_y + circle_diameter),
            fill='white', outline='white', width=1
        )
        id_text = str(sticker_id)
        text_bbox = draw.textbbox((0, 0), id_text, font=font)
        text_x = circle_x + (circle_diameter - (text_bbox[2] - text_bbox[0])) / 2
        text_y = circle_y + (circle_diameter - (text_bbox[3] - text_bbox[1])) / 2
        draw.text((text_x, text_y), id_text, fill='black', font=font)

        # Sửa điều kiện để bao gồm cả 'animated_xp'
        if sticker.get('loai') in ['video', 'animated_xp']:
            triangle_circle_diameter = circle_diameter
            triangle_circle_x = x + sticker_size - triangle_circle_diameter - 5
            triangle_circle_y = y + 5
            draw.ellipse(
                (triangle_circle_x - 2, triangle_circle_y - 2, 
                 triangle_circle_x + triangle_circle_diameter + 2, triangle_circle_y + triangle_circle_diameter + 2),
                fill='orange', outline='orange', width=1
            )
            draw.ellipse(
                (triangle_circle_x, triangle_circle_y, 
                 triangle_circle_x + triangle_circle_diameter, triangle_circle_y + triangle_circle_diameter),
                fill='white', outline='white', width=1
            )
            triangle_size = int(triangle_circle_diameter * 0.5)
            triangle_offset = (triangle_circle_diameter - triangle_size) // 2
            triangle = [
                (triangle_circle_x + triangle_offset, triangle_circle_y + triangle_offset),
                (triangle_circle_x + triangle_offset + triangle_size, triangle_circle_y + triangle_circle_diameter // 2),
                (triangle_circle_x + triangle_offset, triangle_circle_y + triangle_offset + triangle_size)
            ]
            draw.polygon(triangle, fill='red')

    temp_image_path = 'temp_sticker_grid.png'
    large_image.save(temp_image_path)
    client.sendLocalImage(
        imagePath=temp_image_path,
        thread_id=thread_id,
        thread_type=thread_type,
        width=large_image_size,
        height=large_image_size,
        message=Message(text="Danh sách sticker"),
        ttl=180000
    )
    os.remove(temp_image_path)

# Hàm xóa sticker theo ID hoặc xóa tất cả
def handle_xoa_sticker(message, message_object, thread_id, thread_type, author_id, client):
    action = "✅ "
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    parts = message.split()
    if len(parts) >= 2 and parts[1].lower() == 'del':
        if len(parts) >= 3 and parts[2].lower() == 'all':
            delete_all_stickers()
            client.sendMessage(Message(text="Đã xóa tất cả sticker."), thread_id, thread_type, ttl=60000)
        else:
            id_list = parts[2:] if len(parts) >= 3 else parts[1:]
            deleted_count = delete_multiple_stickers(id_list)
            if deleted_count > 0:
                client.sendMessage(Message(text=f"Đã xóa {deleted_count} sticker."), thread_id, thread_type, ttl=60000)
            else:
                client.sendMessage(Message(text="Không có sticker nào được xóa."), thread_id, thread_type, ttl=60000)
    else:
        client.sendMessage(Message(text="Vui lòng cung cấp ID hoặc 'del all'."), thread_id, thread_type, ttl=60000)

# Hàm gửi sticker đã lưu theo ID (hỗ trợ gửi nhiều)
def handle_gui_sticker(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản hồi emoji "✅" xác nhận đã nhận lệnh
    action = "✅ "
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    parts = message.split()
    if len(parts) >= 2:
        id_list = parts[1:]
        sent_count = sum(send_saved_sticker(client, sticker_id, thread_id, thread_type) for sticker_id in id_list)
        if sent_count > 0:
            client.sendMessage(Message(text=""), thread_id, thread_type, ttl=60000)
        else:
            client.sendMessage(Message(text="Số thứ tự stk này đã bị xóa "), thread_id, thread_type, ttl=60000)
    else:
        client.sendMessage(
            Message(
                text="📌 Vui lòng cung cấp ít nhất 1 ID ví dụ stk 1\n"
                     "➜ ➕ getstk: Tạo sticker mới \n"
                     "➜ 🖌️ getstkxp: Reply ảnh để xóa phông.\n"
                     "➜ 🎥 getstkvd: Reply video để tạo sticker động xóa phông.\n"
                     "➜ 🧿 getstkrt: Reply ảnh để tạo sticker xoay tròn\n"
                     "➜ 📋 showstk: Xem danh sách sticker\n"
                     "➜ 🗑️ delstk [ID]: Xóa sticker theo ID\n"
                     "➜ 🗑️ delstk all: Xóa toàn bộ sticker"
            ),
            thread_id,
            thread_type,
            ttl=60000
        )

def handle_stkxp_command(message, message_object, thread_id, thread_type, author_id, client):
    """Tạo sticker xóa phông từ ảnh reply và lưu vào stickers.json"""
    # Gửi phản ứng "✅"
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    print("==> Vào lệnh handle_stkxp_command")

    # Kiểm tra nếu tin nhắn có quote
    if not message_object.quote:
        client.sendMessage(
            Message(text="⭕ Vui lòng reply vào một tin nhắn chứa ảnh để xóa phông!"),
            thread_id, thread_type, ttl=60000
        )
        return

    # Lấy thông tin ảnh từ quote.attach
    attach = message_object.quote.attach
    print(f"Debug: Quote attach: {attach}")
    if not attach:
        client.sendMessage(
            Message(text="⭕ Tin nhắn reply không chứa ảnh hoặc nội dung hợp lệ!"),
            thread_id, thread_type, ttl=60000
        )
        return

    try:
        attach_data = json.loads(attach) if isinstance(attach, str) else attach
        print(f"Debug: Parsed attach_data: {attach_data}")
        image_url = attach_data.get('hdUrl') or attach_data.get('normalUrl') or attach_data.get('oriUrl') or attach_data.get('href')
        if not image_url:
            raise KeyError("Không tìm thấy URL ảnh trong quote.attach")
        image_url = urllib.parse.unquote(image_url.replace("\\/", "/"))
        # Chuyển đổi link từ .jxl sang .jpg
        if image_url.endswith('.jxl'):
            image_url = image_url.replace('/jxl/', '/jpg/').replace('.jxl', '.jpg')
        print(f"Debug: Image URL: {image_url}")
    except json.JSONDecodeError as e:
        client.sendMessage(
            Message(text=f"⭕ Lỗi phân tích dữ liệu ảnh: {str(e)}"),
            thread_id, thread_type, ttl=60000
        )
        return
    except KeyError as e:
        client.sendMessage(
            Message(text=f"⭕ Lỗi: Không thể lấy URL ảnh từ tin nhắn reply: {str(e)}"),
            thread_id, thread_type, ttl=60000
        )
        return

    # Kiểm tra Content-Type
    content_type = get_content_type(image_url)
    print(f"Debug: Content-Type: {content_type}")
    if not content_type.startswith('image/'):
        client.sendMessage(
            Message(text=f"⭕ URL không phải ảnh hợp lệ: Content-Type {content_type}"),
            thread_id, thread_type, ttl=60000
        )
        return

    try:
        # Gọi API remove.bg để xóa phông
        remove_bg_url = "https://api.remove.bg/v1.0/removebg"
        headers = {
            "X-Api-Key": "bBza6TRLbQZJcSid8vBsqgCR",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124",
            "Accept": "image/png,image/jpeg,*/*;q=0.8"
        }
        response = requests.post(
            remove_bg_url,
            headers=headers,
            data={"image_url": image_url, "size": "auto"}
        )
        response.raise_for_status()

        # Tối ưu ảnh với PIL
        image = Image.open(io.BytesIO(response.content))
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        bbox = image.getbbox()
        if bbox:
            image = image.crop(bbox)
        else:
            print(f"Debug: Ảnh toàn trong suốt, dùng kích thước gốc")
        width, height = image.size
        print(f"Debug: Image size after crop: {width}x{height}")

        # Lưu PNG cục bộ
        png_path = "temp_sticker.png"
        image.save(png_path, format="PNG", optimize=True)
        print(f"Debug: PNG saved at: {png_path}")

        # Chuyển sang WEBP
        webp_path = "temp_sticker.webp"
        image.save(webp_path, format="WEBP")
        print(f"Debug: WEBP saved at: {webp_path}")

        # Upload lên Uguu
        static_url = upload_to_uguu(png_path, content_type='image/png')
        animation_url = upload_to_uguu(webp_path, content_type='image/webp')
        print(f"Debug: Static URL: {static_url}, Animation URL: {animation_url}")

        if not static_url or not animation_url:
            raise Exception("Lỗi upload lên Uguu")

        # Gửi sticker
        client.sendCustomSticker(
            staticImgUrl=static_url,
            animationImgUrl=animation_url,
            thread_id=thread_id,
            thread_type=thread_type,
            width=width,
            height=height,
            ttl=600000
        )

        # Lưu sticker
        sticker_id = save_sticker(static_url, animation_url, loai='image_xp', width=width, height=height)

        # Gửi liên kết Uguu và ID
        client.sendMessage(
            Message(text=f"Sticker xóa phông đã được tạo và lưu với ID {sticker_id}! Để tải sticker, bấm: {static_url}"),
            thread_id, thread_type, ttl=60000
        )

    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        error_msg = (
            "⭕ Lỗi API remove.bg: Key không hợp lệ hoặc hết quota. "
            if status_code == 403 else
            "⭕ Lỗi API remove.bg: Vượt giới hạn lượt gọi. Vui lòng đợi hoặc nâng cấp tài khoản."
            if status_code == 429 else
            f"⭕ Lỗi API"
        )
        client.sendMessage(Message(text=error_msg), thread_id, thread_type, ttl=60000)
        print(f"Debug: HTTPError: {e}")
    except Exception as e:
        client.sendMessage(
            Message(text=f"⭕ Lỗi khi tạo sticker xóa phông: {str(e)}"),
            thread_id, thread_type, ttl=60000
        )
        print(f"Debug: Exception: {e}")
    finally:
        # Xóa tệp tạm
        for f in ["temp_sticker.png", "temp_sticker.webp"]:
            if os.path.exists(f):
                os.remove(f)

def create_animated_sticker_from_video(media_url, client, thread_id, thread_type):
    """Tạo sticker động xóa phông từ video, lấy 1 khung hình mỗi giây, xử lý toàn bộ độ dài video với ThreadPoolExecutor"""
    print("==> Đang xử lý video để tạo sticker động xóa phông...")
    video_path = "temp_video.mp4"
    webp_path = "sticker_animated.webp"
    thumbnail_path = "thumbnail.png"
    frames_dir = "temp_frames"
    
    try:
        # Kiểm tra rembg
        try:
            from rembg import remove
            print("rembg imported successfully")
        except ImportError as e:
            raise Exception("Thư viện rembg chưa được cài đặt. Cài bằng: pip install rembg")

        # Tải video
        print("==> Đang tải video...")
        video_response = requests.get(media_url, timeout=30)  # Tăng timeout cho video dài
        if video_response.status_code != 200:
            raise Exception(f"Không tải được video: HTTP {video_response.status_code}")

        with open(video_path, "wb") as f:
            f.write(video_response.content)

        # Kiểm tra file video
        if not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
            raise Exception("File video trống hoặc không tồn tại.")

        # Kiểm tra định dạng video
        content_type = video_response.headers.get('Content-Type', '')
        if not content_type.startswith('video/'):
            raise Exception(f"URL không phải video hợp lệ: Content-Type {content_type}")

        # Lấy thông tin video
        print("==> Lấy thông tin video...")
        clip = VideoFileClip(video_path)
        if clip is None or clip.duration == 0:
            raise Exception("Video không có khung hình hợp lệ hoặc bị hỏng.")

        # Resize video để xử lý nhanh hơn
        clip = clip.resize(height=200)
        new_width, new_height = clip.size

        # Tạo thư mục tạm cho các khung hình
        os.makedirs(frames_dir, exist_ok=True)

        # Trích xuất khung hình với FPS = 1
        print("==> Trích xuất khung hình (1 khung hình mỗi giây)...")
        frame_paths = []
        fps = 2
        for i, frame in enumerate(clip.iter_frames(fps=fps, dtype="uint8")):
            frame_path = os.path.join(frames_dir, f"frame_{i:04d}.png")
            frame_image = Image.fromarray(frame)
            frame_image.save(frame_path)
            frame_paths.append(frame_path)

        # Xóa phông từng khung hình với rembg, sử dụng ThreadPoolExecutor
        print("==> Xóa phông từng khung hình với ThreadPoolExecutor...")
        processed_frame_paths = []

        def remove_background(frame_path):
            try:
                with open(frame_path, "rb") as f:
                    input_image = f.read()
                output_image = remove(input_image)
                if output_image is None:
                    raise Exception(f"rembg trả về None cho khung hình {frame_path}")
                output_path = frame_path.replace(".png", "_nobg.png")
                with open(output_path, "wb") as f:
                    f.write(output_image)
                return output_path
            except Exception as e:
                print(f"Lỗi khi xóa phông khung hình {frame_path}: {e}")
                return None

        with ThreadPoolExecutor(max_workers=5) as executor:  # Giới hạn 4 luồng
            results = list(executor.map(remove_background, frame_paths))
            processed_frame_paths = [r for r in results if r is not None]

        if not processed_frame_paths:
            raise Exception("Không có khung hình nào được xóa phông thành công.")

        # Tạo WEBP động
        print("==> Tạo WEBP động...")
        frames = [Image.open(p).convert("RGBA") for p in processed_frame_paths]
        if not frames:
            raise Exception("Không có khung hình nào để tạo WEBP động.")
        
        frames[0].save(
            webp_path,
            format="WEBP",
            append_images=frames[1:],
            save_all=True,
            duration=200,  # 1000ms = 1 giây cho mỗi khung hình
            loop=0
        )

        # Tạo thumbnail
        thumbnail_path = "thumbnail.png"
        frames[0].save(thumbnail_path, format="PNG")

        # Upload lên Uguu
        print("==> Upload WEBP động lên Uguu...")
        animation_url = upload_to_uguu(webp_path, content_type='image/webp')
        print("==> Upload thumbnail lên Uguu...")
        static_url = upload_to_uguu(thumbnail_path, content_type='image/png')

        if not animation_url or not static_url:
            raise Exception("Không thể upload WEBP động hoặc thumbnail.")

        # Gửi sticker
        print("==> Gửi sticker động xóa phông...")
        client.sendCustomSticker(
            staticImgUrl=static_url,
            animationImgUrl=animation_url,
            thread_id=thread_id,
            thread_type=thread_type,
            width=new_width,
            height=new_height,
            ttl=600000
        )

        # Lưu sticker
        sticker_id = save_sticker(static_url, animation_url, loai='animated_xp', width=new_width, height=new_height)
        client.sendMessage(
            Message(text=f"Sticker động xóa phông đã tạo và lưu với ID {sticker_id}!"),
            thread_id=thread_id,
            thread_type=thread_type,
            ttl=60000
        )

    except Exception as e:
        print(f"Lỗi khi xử lý video xóa phông: {e}")
        client.sendMessage(
            Message(text=f"Đã xảy ra lỗi: {e}"),
            thread_id=thread_id,
            thread_type=thread_type,
            ttl=60000
        )
    finally:
        # Xóa tệp tạm
        for f in [video_path, webp_path, thumbnail_path]:
            if os.path.exists(f):
                os.remove(f)
        if os.path.exists(frames_dir):
            for f in os.listdir(frames_dir):
                os.remove(os.path.join(frames_dir, f))
            os.rmdir(frames_dir)

def handle_stk_animated_command(message, message_object, thread_id, thread_type, author_id, client):
    """Tạo sticker động xóa phông từ video reply"""
    # Gửi phản ứng "✅"
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    print("==> Vào lệnh handle_stk_animated_command")

    # Kiểm tra nếu tin nhắn có quote
    if not message_object.quote:
        client.sendMessage(
            Message(text="⭕ Vui lòng reply vào một tin nhắn chứa video!"),
            thread_id, thread_type, ttl=60000
        )
        return

    # Lấy thông tin video từ quote.attach
    attach = message_object.quote.attach
    print(f"Debug: Quote attach: {attach}")
    if not attach:
        client.sendMessage(
            Message(text="⭕ Tin nhắn reply không chứa video hoặc nội dung hợp lệ!"),
            thread_id, thread_type, ttl=60000
        )
        return

    try:
        attach_data = json.loads(attach) if isinstance(attach, str) else attach
        print(f"Debug: Parsed attach_data: {attach_data}")
        video_url = attach_data.get('hdUrl') or attach_data.get('normalUrl') or attach_data.get('oriUrl') or attach_data.get('href')
        if not video_url:
            raise KeyError("Không tìm thấy URL video trong quote.attach")
        video_url = urllib.parse.unquote(video_url.replace("\\/", "/"))
        print(f"Debug: Video URL: {video_url}")
    except json.JSONDecodeError as e:
        client.sendMessage(
            Message(text=f"⭕ Lỗi phân tích dữ liệu video: {str(e)}"),
            thread_id, thread_type, ttl=60000
        )
        return
    except KeyError as e:
        client.sendMessage(
            Message(text=f"⭕ Lỗi: Không thể lấy URL video từ tin nhắn reply: {str(e)}"),
            thread_id, thread_type, ttl=60000
        )
        return

    # Kiểm tra Content-Type
    content_type = get_content_type(video_url)
    print(f"Debug: Content-Type: {content_type}")
    if not content_type.startswith('video/'):
        client.sendMessage(
            Message(text=f"⭕ URL không phải video hợp lệ: Content-Type {content_type}"),
            thread_id, thread_type, ttl=60000
        )
        return

    # Gọi hàm tạo sticker động xóa phông
    create_animated_sticker_from_video(video_url, client, thread_id, thread_type)

def add_multicolor_circle_border(image, colors, border_thickness=3):
    w, h = image.size
    new_size = (w + 2 * border_thickness, h + 2 * border_thickness)
    border_img = Image.new("RGBA", new_size, (0, 0, 0, 0))
    draw_border = ImageDraw.Draw(border_img)
    cx, cy = new_size[0] / 2, new_size[1] / 2
    r = w / 2
    outer_r = r + border_thickness
    for angle in range(360):
        rad = math.radians(angle)
        inner_point = (cx + r * math.cos(rad), cy + r * math.sin(rad))
        outer_point = (cx + outer_r * math.cos(rad), cy + outer_r * math.sin(rad))
        color = get_gradient_color(colors, angle / 360.0)
        draw_border.line([inner_point, outer_point], fill=color, width=border_thickness)
    border_img.paste(image, (border_thickness, border_thickness), image)
    return border_img

def get_gradient_color(colors, ratio):
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

def create_rotating_sticker(image_url, client, thread_id, thread_type, size=400, frame_count=200, rotation_speed=1):
    try:
        # Tải ảnh
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124'
        }
        resp = requests.get(image_url, headers=headers, timeout=10)
        resp.raise_for_status()
        image = Image.open(io.BytesIO(resp.content))
        
        # Kiểm tra và chuyển đổi sang RGBA nếu cần
        if image.format == 'JXL' or resp.headers.get('Content-Type') == 'image/jpeg':
            image = image.convert('RGBA')
        image = image.resize((size - 60, size - 60), Image.LANCZOS)
        print(f"==> Đã tải ảnh từ: {image_url}")

        # Tạo mặt nạ hình elip
        mask = Image.new("L", image.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, image.size[0], image.size[1]), fill=255)
        image.putalpha(mask)

        # Tạo các khung hình xoay
        frames = []
        for i in range(frame_count):
            angle = -(i * 360) / (frame_count / rotation_speed)
            rotated = image.rotate(angle, resample=Image.BICUBIC)
            frames.append(rotated)
        print(f"==> Đã tạo {frame_count} khung hình")

        # Lưu GIF tạm thời
        gif_path = "temp_rotating_sticker.gif"
        frames[0].save(
            gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=40,
            loop=0,
            disposal=2,
            optimize=True
        )
        print(f"==> Đã tạo GIF tại: {gif_path}")

        # Chuyển sang WEBP với chất lượng tối ưu
        webp_path = "temp_rotating_sticker.webp"
        frames[0].save(
            webp_path,
            format="WEBP",
            save_all=True,
            append_images=frames[1:],
            duration=40,
            loop=0,
            quality=80,  # Giảm chất lượng để tối ưu kích thước
            method=4     # Phương pháp nén nhanh hơn
        )
        print(f"==> Đã chuyển GIF sang WebP: {webp_path}")

        # Upload lên Uguu
        webp_url = upload_to_uguu(webp_path, content_type='image/webp')
        if not webp_url:
            raise Exception("Không thể upload WebP lên Uguu")
        print(f"==> Đã upload WebP: {webp_url}")

        # Gửi sticker
        client.sendCustomSticker(
            staticImgUrl=image_url,
            animationImgUrl=webp_url,
            thread_id=thread_id,
            thread_type=thread_type,
            width=size,
            height=size,
            ttl=600000
        )
        print("==> Đã gửi sticker xoay tròn")

        # Lưu sticker
        sticker_id = save_sticker(image_url, webp_url, loai='rotating', width=size, height=size)
        client.sendMessage(
            Message(text=f"Sticker xoay tròn đã tạo và lưu với ID {sticker_id}!"),
            thread_id=thread_id,
            thread_type=thread_type,
            ttl=60000
        )

    except Exception as e:
        print(f"==> Lỗi khi tạo sticker xoay tròn: {e}")
        client.sendMessage(
            Message(text=f"⭕ Lỗi khi tạo sticker xoay tròn: {str(e)}"),
            thread_id=thread_id,
            thread_type=thread_type,
            ttl=60000
        )
    finally:
        # Xóa tệp tạm
        for f in ["temp_rotating_sticker.gif", "temp_rotating_sticker.webp"]:
            if os.path.exists(f):
                os.remove(f)

def handle_stkrt_command(message, message_object, thread_id, thread_type, author_id, client):
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    print("==> Vào lệnh handle_stkrt_command")

    if not message_object.quote:
        client.sendMessage(
            Message(text="⭕ Vui lòng reply vào một tin nhắn chứa ảnh!"),
            thread_id, thread_type, ttl=60000
        )
        return

    attach = message_object.quote.attach
    print(f"Debug: Quote attach: {attach}")
    if not attach:
        client.sendMessage(
            Message(text="⭕ Tin nhắn reply không chứa ảnh hoặc nội dung hợp lệ!"),
            thread_id, thread_type, ttl=60000
        )
        return

    try:
        attach_data = json.loads(attach) if isinstance(attach, str) else attach
        print(f"Debug: Parsed attach_data: {attach_data}")
        image_url = attach_data.get('hdUrl') or attach_data.get('normalUrl') or attach_data.get('oriUrl') or attach_data.get('href')
        if not image_url:
            raise KeyError("Không tìm thấy URL ảnh trong quote.attach")
        image_url = urllib.parse.unquote(image_url.replace("\\/", "/"))
        # Chuyển đổi link từ .jxl sang .jpg
        if image_url.endswith('.jxl'):
            image_url = image_url.replace('/jxl/', '/jpg/').replace('.jxl', '.jpg')
        print(f"Debug: Image URL: {image_url}")
    except json.JSONDecodeError as e:
        client.sendMessage(
            Message(text=f"⭕ Lỗi phân tích dữ liệu ảnh: {str(e)}"),
            thread_id, thread_type, ttl=60000
        )
        return
    except KeyError as e:
        client.sendMessage(
            Message(text=f"⭕ Lỗi: Không thể lấy URL ảnh từ tin nhắn reply: {str(e)}"),
            thread_id, thread_type, ttl=60000
        )
        return

    content_type = get_content_type(image_url)
    print(f"Debug: Content-Type: {content_type}")
    if not content_type.startswith('image/'):
        client.sendMessage(
            Message(text=f"⭕ URL không phải ảnh hợp lệ: Content-Type {content_type}"),
            thread_id, thread_type, ttl=60000
        )
        return

    create_rotating_sticker(image_url, client, thread_id, thread_type)


# Cập nhật danh sách lệnh
def get_mitaizl():
    return {
        'stk': lambda message, message_object, thread_id, thread_type, author_id, client: (
            handle_stk_command(message, message_object, thread_id, thread_type, author_id, client)
            if message.strip() == 'stk' and message_object.quote
            else handle_gui_sticker(message, message_object, thread_id, thread_type, author_id, client)
            if len(message.split()) > 1 and message.split()[1].isdigit()
            else handle_xem_sticker(message, message_object, thread_id, thread_type, author_id, client)
            if len(message.split()) > 1 and message.split()[1].lower() == 'list'
            else handle_stkxp_command(message, message_object, thread_id, thread_type, author_id, client)
            if len(message.split()) > 1 and message.split()[1].lower() == 'xp'
            else handle_stkrt_command(message, message_object, thread_id, thread_type, author_id, client)
            if len(message.split()) > 1 and message.split()[1].lower() == 'rt'
            else handle_stk_animated_command(message, message_object, thread_id, thread_type, author_id, client)
            if len(message.split()) > 1 and message.split()[1].lower() == 'vd'
            else handle_xoa_sticker(message, message_object, thread_id, thread_type, author_id, client)
            if len(message.split()) > 1 and message.split()[1].lower() == 'del'
            else client.replyMessage(
                Message(
                    text="📌 Vui lòng reply vào ảnh/video/GIF hoặc nhập lệnh hợp lệ:\n"
                         "➜ stk (reply ảnh/video để tạo sticker)\n"
                         "➜ stk <ID> (gửi sticker, ví dụ: stk 1)\n"
                         "➜ stk list (xem danh sách sticker)\n"
                         "➜ stk xp (reply ảnh để xóa phông)\n"
                         "➜ stk rt (reply ảnh để tạo sticker xoay)\n"
                         "➜ stk vd (reply video để tạo sticker động)\n"
                         "➜ stk del <ID> (xóa sticker)\n"
                         "➜ stk del all (xóa tất cả sticker)"
                ),
                message_object, thread_id, thread_type, ttl=20000
            )
        )
    }