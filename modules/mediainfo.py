from zlapi.models import Message
import requests
import json
import urllib.parse
import io
import os
from PIL import Image
from moviepy.editor import VideoFileClip
import math

# Thông tin mô tả
des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Đo các thông số của ảnh, video, hoặc GIF từ tin nhắn reply",
    'tính năng': [
        "📷 Đo thông số ảnh: kích thước, định dạng, dung lượng, chế độ màu, độ sâu màu, DPI, metadata (nếu có).",
        "🎥 Đo thông số video: kích thước, định dạng, dung lượng, thời lượng, FPS, tỷ lệ khung hình, trạng thái âm thanh.",
        "🔍 Đo thông số GIF: kích thước, định dạng, dung lượng, số khung hình, thời lượng mỗi khung, bảng màu, transparency, vòng lặp.",
        "🔗 Kiểm tra và xử lý URL ảnh/video/GIF hợp lệ.",
        "🔔 Gửi thông báo chi tiết về thông số qua tin nhắn.",
        "✅ Xác nhận lệnh bằng emoji phản hồi."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh `mediainfo` và reply vào tin nhắn chứa ảnh, video hoặc GIF.",
        "✅ Nhận thông báo trạng thái và kết quả đo thông số ngay lập tức."
    ]
}

# Hàm lấy Content-Type từ URL
def get_content_type(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        return response.headers.get('Content-Type', '')
    except Exception as e:
        print(f"Lỗi khi lấy Content-Type: {e}")
        return ''

# Hàm kiểm tra loại media
def is_valid_image_url(url):
    content_type = get_content_type(url)
    return content_type.startswith('image/') and content_type != 'image/gif'

def is_valid_video_url(url):
    content_type = get_content_type(url)
    return content_type.startswith('video/')

def is_valid_gif_url(url):
    content_type = get_content_type(url)
    return content_type == 'image/gif'

# Hàm lấy dung lượng file từ response
def get_file_size(response):
    try:
        size_bytes = len(response.content)
        if size_bytes < 1024:
            return f"{size_bytes} bytes"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
    except Exception:
        return "Không xác định"

# Hàm xử lý thông tin ảnh
def get_image_info(image_url):
    try:
        response = requests.get(image_url, timeout=10)
        if response.status_code != 200:
            return f"Lỗi: Không tải được ảnh (HTTP {response.status_code})."

        image = Image.open(io.BytesIO(response.content))
        width, height = image.size
        format_type = image.format or "Không xác định"
        file_size = get_file_size(response)
        color_mode = image.mode
        bit_depth = image.info.get('bits', 'Không xác định')
        dpi = image.info.get('dpi', 'Không xác định')
        if isinstance(dpi, tuple):
            dpi = f"{dpi[0]} x {dpi[1]}"
        metadata = "Có" if image.info.get('exif') else "Không"

        info = (
            f"📷 Thông số ảnh:\n"
            f"- Kích thước: {width} x {height} pixels\n"
            f"- Định dạng: {format_type}\n"
            f"- Dung lượng: {file_size}\n"
            f"- Chế độ màu: {color_mode}\n"
            f"- Độ sâu màu: {bit_depth} bit\n"
            f"- DPI: {dpi}\n"
            f"- Metadata (EXIF): {metadata}"
        )
        return info
    except Exception as e:
        return f"Lỗi khi xử lý ảnh: {str(e)}"

# Hàm xử lý thông tin GIF
def get_gif_info(gif_url):
    try:
        response = requests.get(gif_url, timeout=10)
        if response.status_code != 200:
            return f"Lỗi: Không tải được GIF (HTTP {response.status_code})."

        gif = Image.open(io.BytesIO(response.content))
        width, height = gif.size
        format_type = gif.format or GIF
        file_size = get_file_size(response)
        
        # Đếm số khung hình
        frame_count = 0
        try:
            while True:
                gif.seek(gif.tell() + 1)
                frame_count += 1
        except EOFError:
            pass
        
        # Lấy thời lượng mỗi khung
        duration = gif.info.get('duration', 100) / 1000  # Chuyển từ ms sang giây
        total_duration = frame_count * duration if frame_count > 0 else 0
        palette = "Có" if gif.info.get('palette') else "Không"
        transparency = "Có" if gif.info.get('transparency') else "Không"
        loop_count = gif.info.get('loop', 'Không xác định')
        if loop_count == 0:
            loop_count = "Vô hạn"
        elif isinstance(loop_count, int):
            loop_count = str(loop_count)

        info = (
            f"🎞️ Thông số GIF:\n"
            f"- Kích thước: {width} x {height} pixels\n"
            f"- Định dạng: {format_type}\n"
            f"- Dung lượng: {file_size}\n"
            f"- Số khung hình: {frame_count}\n"
            f"- Thời lượng mỗi khung: {duration:.3f} giây\n"
            f"- Tổng thời lượng: {total_duration:.3f} giây\n"
            f"- Bảng màu: {palette}\n"
            f"- Transparency: {transparency}\n"
            f"- Vòng lặp: {loop_count}"
        )
        return info
    except Exception as e:
        return f"Lỗi khi xử lý GIF: {str(e)}"

# Hàm xử lý thông tin video
def get_video_info(video_url):
    try:
        # Tải video tạm thời
        response = requests.get(video_url, timeout=30)
        if response.status_code != 200:
            return f"Lỗi: Không tải được video (HTTP {response.status_code})."

        temp_video_path = "temp_video.mp4"
        with open(temp_video_path, "wb") as f:
            f.write(response.content)

        # Lấy thông tin video
        clip = VideoFileClip(temp_video_path)
        width, height = clip.size
        duration = clip.duration
        fps = clip.fps
        format_type = response.headers.get('Content-Type', 'video/mp4').split('/')[-1]
        file_size = get_file_size(response)
        aspect_ratio = f"{width / height:.2f}:1" if height != 0 else "Không xác định"
        has_audio = "Có" if clip.audio is not None else "Không"
        # Ước lượng bitrate dựa trên dung lượng và thời lượng
        bitrate = "Không xác định"
        if duration > 0 and file_size != "Không xác định":
            size_bytes = len(response.content)
            bitrate = (size_bytes * 8 / duration / 1000)  # kbps
            bitrate = f"{bitrate:.2f} kbps"

        info = (
            f"🎥 Thông số video:\n"
            f"- Kích thước: {width} x {height} pixels\n"
            f"- Định dạng: {format_type}\n"
            f"- Dung lượng: {file_size}\n"
            f"- Thời lượng: {duration:.2f} giây\n"
            f"- FPS: {fps:.2f}\n"
            f"- Tỷ lệ khung hình: {aspect_ratio}\n"
            f"- Âm thanh: {has_audio}\n"
            f"- Bitrate (ước lượng): {bitrate}"
        )

        # Xóa file tạm
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)

        return info
    except Exception as e:
        # Đảm bảo xóa file tạm nếu có lỗi
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        return f"Lỗi khi xử lý video: {str(e)}"

# Hàm xử lý lệnh đo thông số media
def handle_mediainfo_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản hồi emoji "✅" xác nhận đã nhận lệnh
    action = "✅ "
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    print("==> Vào lệnh handle_mediainfo_command")

    media_url = None
    is_gif = False

    # Kiểm tra nếu tin nhắn là reply
    if message_object.quote:
        attach = message_object.quote.attach
        if attach:
            try:
                attach_data = json.loads(attach) if isinstance(attach, str) else attach
                media_url = attach_data.get('hdUrl') or attach_data.get('normalUrl') or attach_data.get('oriUrl') or attach_data.get('href')
                if media_url:
                    media_url = urllib.parse.unquote(media_url.replace("\\/", "/"))
                    print(f"==> Media URL từ reply: {media_url}")
                
                # Kiểm tra nếu là GIF dựa trên action
                if attach_data.get('action') == 'recommend.gif':
                    is_gif = True
            except Exception as e:
                print("==> Lỗi đọc attach:", e)
                client.sendMessage(Message(text="Dữ liệu không hợp lệ."), thread_id, thread_type, ttl=60000)
                return

    # Kiểm tra nếu người dùng nhập URL trực tiếp
    if not media_url:
        parts = message.split()
        if len(parts) >= 2:
            media_url = parts[1]
            print(f"==> Media URL từ lệnh: {media_url}")
        else:
            client.sendMessage(Message(text="Hãy reply vào ảnh/video/GIF hoặc nhập link."), thread_id, thread_type, ttl=60000)
            return

    if not media_url:
        client.sendMessage(Message(text="Không tìm thấy URL media."), thread_id, thread_type, ttl=60000)
        return

    # Xử lý theo loại media
    if is_gif or is_valid_gif_url(media_url):
        print("==> Đang xử lý GIF...")
        info = get_gif_info(media_url)
        client.sendMessage(Message(text=info), thread_id, thread_type, ttl=60000)
    
    elif is_valid_image_url(media_url):
        print("==> Đang xử lý ảnh...")
        info = get_image_info(media_url)
        client.sendMessage(Message(text=info), thread_id, thread_type, ttl=60000)
    
    elif is_valid_video_url(media_url):
        print("==> Đang xử lý video...")
        info = get_video_info(video_url)
        client.sendMessage(Message(text=info), thread_id, thread_type, ttl=60000)
    
    else:
        print("==> URL không phải ảnh, GIF hoặc video hợp lệ.")
        client.sendMessage(Message(text="URL không phải ảnh, GIF hoặc video hợp lệ."), thread_id, thread_type, ttl=60000)

# Cập nhật danh sách lệnh
def get_mitaizl():
    return {
        'mediainfo': handle_mediainfo_command
    }