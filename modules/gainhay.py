from zlapi.models import Message
import requests
import json
import random
import tempfile
import os
from moviepy.editor import VideoFileClip
import time

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Gửi thông tin admin và video ngẫu nhiên từ tệp gainhay.json với thumbnail là khung hình đầu tiên của video.",
    'tính năng': [
        "✅ Gửi phản ứng xác nhận khi lệnh được nhập đúng.",
        "🚀 Lấy video ngẫu nhiên từ tệp gainhay.json và gửi phản hồi.",
        "🔗 Tải video về cục bộ và tải lên Uguu.se trước khi gửi.",
        "🖼️ Sử dụng khung hình đầu tiên của video làm thumbnail.",
        "📊 Gửi phản hồi khi lấy thông tin thành công hoặc thất bại.",
        "⚡ Gửi video với thông báo thông tin admin."
    ],
    'hướng dẫn sử dụng': [
        "📌 Gửi lệnh `gainhay` để nhận thông tin admin và video ngẫu nhiên.",
        "📎 Bot sẽ tự động lấy video từ tệp gainhay.json và gửi.",
        "📢 Hệ thống sẽ gửi phản hồi khi hoàn thành."
    ]
}

UGUU_API_URL = "https://uguu.se/upload.php"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def upload_to_uguu(file_path, is_video=True):
    """Tải file lên Uguu.se và trả về URL."""
    print(f"⬆️ Đang tải {'video' if is_video else 'thumbnail'} lên Uguu.se: {file_path}")
    try:
        # Kiểm tra kích thước và thời lượng video trước khi upload (nếu là video)
        if is_video:
            with VideoFileClip(file_path) as clip:
                duration = clip.duration
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                print(f"📏 Kích thước file: {file_size:.2f}MB, Thời lượng: {duration:.2f}s")
                if duration > 120:
                    print("❌ Video vượt quá 120 giây, Uguu.se không hỗ trợ.")
                    return None
                if file_size > 100:
                    print("❌ Video vượt quá 100MB, Uguu.se không hỗ trợ.")
                    return None
        else:
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
            if file_size > 100:
                print("❌ Thumbnail vượt quá 100MB, Uguu.se không hỗ trợ.")
                return None

        with open(file_path, 'rb') as f:
            files = {
                'files[]': (os.path.basename(file_path), f, 'video/mp4' if is_video else 'image/jpeg')
            }
            data = {'randomname': 'true'}  # Yêu cầu Uguu.se tạo tên ngẫu nhiên
            response = requests.post(UGUU_API_URL, headers=headers, files=files, data=data, timeout=30)
            response.raise_for_status()
            uguu_data = response.json()
            if uguu_data.get('success'):
                file_url = uguu_data['files'][0]['url']
                print(f"✅ Đã tải {'video' if is_video else 'thumbnail'} lên Uguu.se: {file_url}")
                return file_url
            else:
                print(f"❌ Uguu.se trả về lỗi: {uguu_data.get('description', 'No error details')}")
                return None
    except requests.RequestException as e:
        print(f"❌ Lỗi khi tải lên Uguu.se: {e}")
        if hasattr(e, 'response') and e.response is not None and hasattr(e.response, 'text'):
            print(f"📜 Chi tiết lỗi từ Uguu.se: {e.response.text}")
        return None
    except Exception as e:
        print(f"❌ Lỗi khi kiểm tra file: {e}")
        return None

def download_video(video_url, temp_file_path):
    """Tải video từ URL về file tạm."""
    print(f"⬇️ Đang tải video từ: {video_url}")
    try:
        with requests.get(video_url, headers=headers, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(temp_file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        print(f"✅ Đã tải video về: {temp_file_path}")
        return True
    except requests.RequestException as e:
        print(f"❌ Lỗi khi tải video: {e}")
        return False

def get_video_thumbnail(video_path):
    """Trích xuất khung hình đầu tiên của video và tải lên Uguu.se."""
    try:
        with VideoFileClip(video_path) as clip:
            thumbnail_path = tempfile.mktemp(suffix=".jpg")
            clip.save_frame(thumbnail_path, t=0)
        thumbnail_url = upload_to_uguu(thumbnail_path, is_video=False)
        os.remove(thumbnail_path)
        if thumbnail_url:
            print(f"✅ Đã tạo và tải thumbnail lên Uguu.se: {thumbnail_url}")
        return thumbnail_url
    except Exception as e:
        print(f"❌ Lỗi khi tạo thumbnail: {e}")
        return None

def handle_ad_command(message, message_object, thread_id, thread_type, author_id, client):
    action = "✅ "
    try:
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    except Exception as e:
        print(f"❌ Lỗi khi gửi phản ứng: {e}")

    try:
        print("🔍 Đang đọc tệp gainhay.json")
        with open('gainhay.json', 'r', encoding='utf-8') as f:
            imgur_links = json.load(f)

        if not imgur_links:
            error_message = Message(text="❌ Tệp gainhay.json rỗng hoặc không có link video.")
            client.sendMessage(error_message, thread_id, thread_type)
            return

        max_attempts = 3
        attempts = 0
        while attempts < max_attempts:
            video_data = random.choice(imgur_links)
            original_video_url = video_data['link']
            video_index = video_data.get('index', 'N/A')
            video_title = video_data.get('title', '')
            print(f"🎞 Đã chọn video ngẫu nhiên (lần {attempts + 1}): {original_video_url}")
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
                temp_file_path = temp_file.name

            time.sleep(1)  # Avoid rate-limiting
            if download_video(original_video_url, temp_file_path):
                if os.path.getsize(temp_file_path) > 0:
                    break
                else:
                    print("❌ Tệp tải về rỗng.")
                    os.remove(temp_file_path)
            else:
                os.remove(temp_file_path)
            attempts += 1
        else:
            error_message = Message(text="❌ Không thể tải video sau nhiều lần thử.")
            client.sendMessage(error_message, thread_id, thread_type)
            return

        uploaded_video_url = upload_to_uguu(temp_file_path, is_video=True)
        if not uploaded_video_url:
            os.remove(temp_file_path)
            error_message = Message(text="❌ Lỗi khi tải video lên Uguu.se.")
            client.sendMessage(error_message, thread_id, thread_type)
            return

        thumbnail_url = get_video_thumbnail(temp_file_path)

        # Lấy duration trước khi xóa file
        try:
            with VideoFileClip(temp_file_path) as clip:
                duration = str(int(clip.duration))
            print(f"⏱ Thời lượng video: {duration}s")
        except Exception:
            duration = '60'
            print("⚠️ Không thể lấy duration, sử dụng mặc định 60s")

        os.remove(temp_file_path)

        if not thumbnail_url:
            error_message = Message(text="❌ Lỗi khi tạo hoặc tải thumbnail lên Uguu.se.")
            client.sendMessage(error_message, thread_id, thread_type)
            return

        # Tạo đối tượng Message để gửi kèm tiêu đề và số thứ tự
        message_to_send = Message(text=f"Video {video_index}: {video_title}" if video_title else f"Video {video_index}")
        print(f"📤 Đang gửi video với URL: {uploaded_video_url}, Thumbnail: {thumbnail_url}, Duration: {duration}, Message: {message_to_send.text}")
        try:
            client.sendRemoteVideo(
                uploaded_video_url,
                thumbnail_url,
                duration=duration,
                message=message_to_send,
                thread_id=thread_id,
                thread_type=thread_type,
                width=1080,
                height=1920
            )
            print("✅ Video đã được gửi thành công!")
        except Exception as e:
            print(f"❌ Lỗi khi gửi video: {e} (Type: {type(e).__name__})")
            error_message = Message(text=f"❌ Lỗi khi gửi video: {str(e)}")
            client.sendMessage(error_message, thread_id, thread_type)

    except FileNotFoundError:
        error_message = Message(text="❌ Không tìm thấy tệp gainhay.json.")
        client.sendMessage(error_message, thread_id, thread_type)
    except json.JSONDecodeError:
        error_message = Message(text="❌ Lỗi định dạng tệp gainhay.json.")
        client.sendMessage(error_message, thread_id, thread_type)
    except Exception as e:
        print(f"❌ Lỗi tổng quát: {e} (Type: {type(e).__name__})")
        error_message = Message(text=f"❌ Đã xảy ra lỗi: {str(e)}")
        client.sendMessage(error_message, thread_id, thread_type)

def get_mitaizl():
    return {
        'gaitt': handle_ad_command
    }