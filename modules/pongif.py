import random
import os
import requests
from zlapi.models import Message, ThreadType
from moviepy.editor import VideoFileClip
from PIL import Image
import io
import imageio.v3 as imageio
import magic

def get_gif_links_from_file(filepath):
    """Đọc danh sách liên kết GIF từ tệp."""
    print(f"🔍 Đang đọc file: {filepath}")
    if not os.path.exists(filepath):
        return None, "Tệp pgif.txt không tồn tại."
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
            return lines, None
    except Exception as e:
        return None, str(e)

def is_webp_file(filepath):
    """Kiểm tra file có phải WebP không dựa trên MIME type."""
    if not os.path.exists(filepath):
        return False
    try:
        mime = magic.Magic(mime=True)
        file_type = mime.from_file(filepath)
        return file_type == 'image/webp'
    except Exception as e:
        print(f"⚠️ Lỗi khi kiểm tra MIME type: {str(e)}")
        return False

def convert_webp_to_gif(input_path, output_path):
    """Chuyển đổi file WebP động sang GIF bằng PIL."""
    print(f"🔄 Chuyển đổi WebP {input_path} sang GIF")
    try:
        img = Image.open(input_path)
        frames = []
        durations = []
        
        # Thu thập các khung hình
        try:
            while True:
                frame = img.copy().convert('P', palette=Image.ADAPTIVE, colors=128)
                frames.append(frame)
                durations.append(img.info.get('duration', 100))  # Thời gian mặc định 100ms
                img.seek(img.tell() + 1)
        except EOFError:
            pass

        # Lưu thành GIF
        frames[0].save(
            output_path,
            format='GIF',
            save_all=True,
            append_images=frames[1:],
            loop=0,
            duration=durations,
            optimize=True
        )
        return True, None
    except Exception as e:
        return False, str(e)
        
def is_gif_file(filepath):
    """Kiểm tra file có phải GIF không dựa trên phần mở rộng."""
    if not os.path.exists(filepath):
        return False
    return filepath.lower().endswith('.gif')

def convert_to_gif(input_path, output_path):
    """Chuyển đổi file video sang GIF bằng moviepy."""
    print(f"🔄 Chuyển đổi {input_path} sang GIF")
    try:
        clip = VideoFileClip(input_path)
        clip.write_videofile(output_path, codec='gif', fps=10)  # FPS thấp để giảm kích thước
        clip.close()
        return True, None
    except Exception as e:
        return False, str(e)

def compress_gif(input_path, output_path, max_size_bytes=2097152):
    """Nén GIF để kích thước dưới max_size_bytes (mặc định 2MB)."""
    print(f"🗜 Nén GIF: {input_path}")
    try:
        # Mở file GIF
        img = Image.open(input_path)
        frames = []
        durations = []
        
        # Thu thập các frame và thời gian hiển thị
        try:
            while True:
                frame = img.copy().convert('P', palette=Image.ADAPTIVE, colors=128)  # Giảm số màu
                frames.append(frame)
                durations.append(img.info.get('duration', 100))  # Thời gian mặc định 100ms
                img.seek(img.tell() + 1)
        except EOFError:
            pass

        # Nếu file đã nhỏ hơn 2MB, không cần nén thêm
        temp_buffer = io.BytesIO()
        frames[0].save(temp_buffer, format='GIF', save_all=True, append_images=frames[1:], loop=0, duration=durations)
        if temp_buffer.tell() <= max_size_bytes:
            with open(output_path, 'wb') as f:
                f.write(temp_buffer.getvalue())
            return True, None

        # Thử nén bằng cách giảm kích thước và tối ưu hóa
        scale_factor = 0.8  # Giảm kích thước khung hình
        while True:
            temp_buffer = io.BytesIO()
            resized_frames = [frame.resize((int(frame.width * scale_factor), int(frame.height * scale_factor)), Image.LANCZOS) for frame in frames]
            resized_frames[0].save(
                temp_buffer,
                format='GIF',
                save_all=True,
                append_images=resized_frames[1:],
                loop=0,
                duration=durations,
                optimize=True,
                quality=85
            )
            if temp_buffer.tell() <= max_size_bytes or scale_factor < 0.3:  # Ngừng nếu nhỏ hơn 2MB hoặc quá nhỏ
                with open(output_path, 'wb') as f:
                    f.write(temp_buffer.getvalue())
                return True, None
            scale_factor *= 0.8  # Giảm tiếp kích thước
        return True, None
    except Exception as e:
        return False, str(e)

def download_file(url, output_path):
    """Tải file từ URL về máy, thêm phần mở rộng dựa trên MIME type hoặc URL."""
    print(f"⬇️ Tải file từ: {url}")
    try:
        with requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, stream=True, timeout=30) as r:
            r.raise_for_status()
            # Lấy phần mở rộng từ URL hoặc MIME type
            content_type = r.headers.get('Content-Type', '')
            extension = '.bin'  # Mặc định nếu không xác định được
            if 'image/webp' in content_type:
                extension = '.webp'
            elif 'image/gif' in content_type:
                extension = '.gif'
            elif 'video' in content_type:
                extension = '.mp4'
            else:
                # Lấy phần mở rộng từ URL
                from urllib.parse import urlparse
                path = urlparse(url).path
                ext = os.path.splitext(path)[1].lower()
                if ext in ['.webp', '.gif', '.mp4']:
                    extension = ext

            # Đặt tên file với phần mở rộng
            temp_output_path = output_path + extension
            with open(temp_output_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"✅ File đã được tải về: {temp_output_path}")
            return True, temp_output_path
    except Exception as e:
        return False, str(e)

def handle_pgif_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh pgif: đọc liên kết, tải file, chuyển đổi/nén sang GIF nếu cần và gửi."""
    print(f"📂 Thư mục hiện tại: {os.getcwd()}")
    print("🚀 Đã nhận lệnh pgif")
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
    client.sendMessage(Message(text="File đang được xử lý, vui lòng chờ..."), thread_id, thread_type, ttl=60000)

    # Đọc danh sách liên kết từ pgif.txt
    gif_links, error_msg = get_gif_links_from_file("pgif.txt")
    if not gif_links:
        client.sendMessage(Message(text=f"Lỗi: {error_msg}"), thread_id, thread_type)
        return

    # Chọn ngẫu nhiên một liên kết
    file_url = random.choice(gif_links)
    print(f"🎞 Chọn file: {file_url}")

    # Tải file về file tạm
    temp_path = "temp_file"
    success, result = download_file(file_url, temp_path)
    if not success:
        client.sendMessage(Message(text=f"Không tải được file: {result}"), thread_id, thread_type)
        return
    temp_file_path = result  # Đường dẫn file thực tế (bao gồm phần mở rộng)

    # Kiểm tra xem file có tồn tại không
    if not os.path.exists(temp_file_path):
        client.sendMessage(Message(text=f"Lỗi: File {temp_file_path} không tồn tại sau khi tải."), thread_id, thread_type)
        print(f"⚠️ Lỗi: File {temp_file_path} không tồn tại.")
        return

    # Debug: In loại file
    try:
        mime = magic.Magic(mime=True)
        file_type = mime.from_file(temp_file_path)
        print(f"📄 Loại file: {file_type}")
    except:
        print("⚠️ Không thể xác định loại file.")

    # Kiểm tra và chuyển đổi sang GIF nếu cần
    final_gif_path = "temp_gif.gif"
    try:
        if is_webp_file(temp_file_path):
            # Nếu là WebP, chuyển đổi sang GIF bằng PIL
            print(f"🔍 File là WebP: {temp_file_path}")
            success, err = convert_webp_to_gif(temp_file_path, final_gif_path)
            if not success:
                client.sendMessage(Message(text=f"Lỗi khi chuyển đổi WebP sang GIF: {err}"), thread_id, thread_type)
                return
        elif is_gif_file(temp_file_path):
            # Nếu đã là GIF, copy sang final_gif_path
            print(f"🔍 File là GIF: {temp_file_path}")
            with open(temp_file_path, 'rb') as f_in:
                with open(final_gif_path, 'wb') as f_out:
                    f_out.write(f_in.read())
        else:
            # Nếu không phải GIF hoặc WebP, thử chuyển đổi video sang GIF
            print(f"🔍 File là video: {temp_file_path}")
            success, err = convert_to_gif(temp_file_path, final_gif_path)
            if not success:
                client.sendMessage(Message(text=f"Lỗi khi chuyển đổi sang GIF: {err}"), thread_id, thread_type)
                return

        # Kiểm tra kích thước file và nén nếu cần
        if os.path.getsize(final_gif_path) > 2097152:  # 2MB
            compressed_gif_path = "compressed_gif.gif"
            success, err = compress_gif(final_gif_path, compressed_gif_path)
            if not success:
                client.sendMessage(Message(text=f"Lỗi khi nén GIF: {err}"), thread_id, thread_type)
                return
            final_gif_path = compressed_gif_path

        # Gửi GIF bằng sendLocalGif
        client.sendLocalGif(
            final_gif_path,
            thread_id=thread_id,
            thread_type=thread_type,
            width=480,
            height=480,
            thumbnailUrl=file_url,
            ttl=180000
        )
        print(f"✅ Đã gửi GIF từ file: {final_gif_path}")
    except Exception as e:
        client.sendMessage(Message(text=f"Lỗi khi gửi GIF: {str(e)}"), thread_id, thread_type)
        print(f"⚠️ Lỗi khi gửi GIF: {str(e)}")
    finally:
        # Xóa các file tạm
        for path in [temp_file_path, final_gif_path, "compressed_gif.gif"]:
            if os.path.exists(path):
                os.remove(path)
                print(f"🗑️ Đã xóa file tạm: {path}")

def get_mitaizl():
    """Trả về ánh xạ lệnh pgif."""
    return {
        'pongif': handle_pgif_command
    }