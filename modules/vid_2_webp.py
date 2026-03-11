import requests
import urllib.parse
import os
import json
from PIL import Image
from moviepy.editor import VideoFileClip
from zlapi.models import Message

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🎞️ Chuyển đổi video thành sticker động và gửi link.",
    'tính năng': [
        "📹 Nhận video từ tin nhắn reply và chuyển thành định dạng WEBP.",
        "✂️ Cắt video tối đa 30 giây và điều chỉnh kích thước phù hợp.",
        "📤 Tải sticker và thumbnail lên Catbox, gửi kèm link sticker.",
        "⚠️ Thông báo lỗi nếu video không hợp lệ hoặc xử lý thất bại."
    ],
    'hướng dẫn sử dụng': [
        "📩 Reply vào một video và gửi lệnh vid2webp.",
        "📌 Ví dụ: reply video rồi gửi vid2webp",
        "✅ Nhận sticker động và link WEBP trong tin nhắn."
    ]
}
# Hàm kiểm tra URL có phải video không
def is_valid_video_url(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        content_type = response.headers.get('Content-Type', '')
        print(f"==> Content-Type của URL: {content_type}")
        return content_type.startswith('video/')
    except Exception as e:
        print(f"==> Lỗi khi kiểm tra URL video: {e}")
        return False

# Hàm tải file lên Catbox
def upload_to_catbox(file_path, content_type='image/webp'):
    print(f"==> Đang tải lên Catbox: {file_path}")
    try:
        with open(file_path, 'rb') as f:
            files = {'fileToUpload': (os.path.basename(file_path), f, content_type)}
            data = {'reqtype': 'fileupload'}
            response = requests.post("https://catbox.moe/user/api.php", data=data, files=files)
            if response.status_code == 200:
                return response.text.strip()
        print(f"==> Lỗi: Tải lên Catbox trả về mã {response.status_code}")
        return None
    except Exception as e:
        print(f"==> Lỗi khi tải lên Catbox: {e}")
        return None

# Hàm xử lý video thành sticker và gửi kèm link
def handle_stkvideo_command(message, message_object, thread_id, thread_type, author_id, client):
    print("==> Bắt đầu xử lý lệnh stkvideo")
    
    # Kiểm tra xem có reply không
    if not message_object.quote:
        client.sendMessage(Message(text="Vui lòng reply vào một video."), 
                           thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    # Lấy dữ liệu đính kèm từ tin nhắn được reply
    attach = message_object.quote.attach
    if not attach:
        client.sendMessage(Message(text="Tin nhắn được reply không chứa tệp đính kèm."), 
                           thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    # Trích xuất URL từ attach
    media_url = None
    try:
        print(f"==> Dữ liệu attach: {attach}")
        attach_data = json.loads(attach) if isinstance(attach, str) else attach
        media_url = attach_data.get('hdUrl') or attach_data.get('href')
        if media_url:
            media_url = urllib.parse.unquote(media_url.replace("\\/", "/"))
            print(f"==> URL video từ reply: {media_url}")
        else:
            client.sendMessage(Message(text="Không tìm thấy URL trong dữ liệu đính kèm."), 
                               thread_id=thread_id, thread_type=thread_type, ttl=60000)
            return
    except json.JSONDecodeError:
        client.sendMessage(Message(text="Dữ liệu đính kèm không phải định dạng JSON hợp lệ."), 
                           thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return
    except Exception as e:
        print(f"==> Lỗi khi đọc dữ liệu đính kèm: {e}")
        client.sendMessage(Message(text=f"Lỗi khi xử lý dữ liệu đính kèm: {e}"), 
                           thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    # Kiểm tra URL có phải video không
    if not is_valid_video_url(media_url):
        client.sendMessage(Message(text="URL không phải video hợp lệ."), 
                           thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    print("==> Đang xử lý video...")
    try:
        # Tải video
        video_response = requests.get(media_url)
        if video_response.status_code != 200:
            raise Exception(f"Không tải được video, mã lỗi: {video_response.status_code}")

        video_path = "temp_video.mp4"
        with open(video_path, "wb") as f:
            f.write(video_response.content)

        # Xử lý video
        print("==> Lấy thông tin video và cắt clip...")
        with VideoFileClip(video_path) as clip:
            duration = min(clip.duration, 30)  # Giới hạn 30 giây
            clip = clip.subclip(0, duration).resize((300, 512))
            new_width, new_height = clip.size

        # Chuyển thành WEBP
        webp_path = "sticker.webp"
        os.system(f"ffmpeg -y -i {video_path} -vf \"scale={new_width}:{new_height},fps=15\" -loop 0 -an {webp_path}")
        if not os.path.exists(webp_path):
            raise Exception("Chuyển đổi sang WEBP thất bại.")

        # Tạo thumbnail
        thumbnail_path = "thumbnail.png"
        with VideoFileClip(video_path) as clip:
            clip.save_frame(thumbnail_path, t=0.5)

        # Tải lên Catbox
        print("==> Đang tải WEBP lên Catbox...")
        webp_url = upload_to_catbox(webp_path, content_type='image/webp')
        print("==> Đang tải thumbnail lên Catbox...")
        static_url = upload_to_catbox(thumbnail_path, content_type='image/png')

        if webp_url and static_url:
            # Gửi sticker
            print("==> Gửi sticker video...")
            client.sendCustomSticker(
                staticImgUrl=static_url,
                animationImgUrl=webp_url,
                thread_id=thread_id,
                thread_type=thread_type,
                width=new_width,
                height=new_height,
            )
            # Gửi link
            client.sendMessage(Message(text=f"Sticker video: {webp_url}"),
                               thread_id=thread_id, thread_type=thread_type, ttl=60000)
        else:
            raise Exception("Không thể tải video hoặc thumbnail lên Catbox.")

    except Exception as e:
        print(f"==> Lỗi khi xử lý video: {e}")
        client.sendMessage(Message(text=f"Đã xảy ra lỗi: {e}"),
                           thread_id=thread_id, thread_type=thread_type, ttl=60000)
    finally:
        # Dọn dẹp file tạm
        for f in ["temp_video.mp4", "sticker.webp", "thumbnail.png"]:
            if os.path.exists(f):
                os.remove(f)

# Định nghĩa lệnh
def get_mitaizl():
    return {
        'vid2webp': handle_stkvideo_command
    }