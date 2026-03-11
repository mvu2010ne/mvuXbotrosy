import re
import os
import requests
import json
from zlapi.models import Message
from bs4 import BeautifulSoup
import yt_dlp
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time

def handle_down_command(message, message_object, thread_id, thread_type, author_id, client):
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    content = message.strip()

    def extract_url(text):
        urls = re.findall(r'(https?://[^\s]+)', text)
        return urls[0] if urls else None

    if hasattr(message_object, 'quote') and message_object.quote:
        if message_object.quote.msg:
            video_link = extract_url(message_object.quote.msg)
            if not video_link:
                error_message = Message(text="Không tìm thấy URL hợp lệ trong tin nhắn reply.")
                client.replyMessage(error_message, message_object, thread_id, thread_type)
                return
        elif message_object.quote.attach:
            try:
                attach_data = json.loads(message_object.quote.attach)
                link_candidate = attach_data.get('href', '') or attach_data.get('title', '')
                video_link = extract_url(link_candidate)
                if not video_link:
                    raise ValueError("Không tìm thấy URL trong attach")
            except (json.JSONDecodeError, ValueError) as e:
                error_message = Message(text=f"Lỗi khi phân tích attach: {str(e)}")
                client.replyMessage(error_message, message_object, thread_id, thread_type)
                return
        else:
            error_message = Message(text="Tin nhắn reply không chứa link hợp lệ.")
            client.replyMessage(error_message, message_object, thread_id, thread_type)
            return
    else:
        def extract_links(content):
            urls = re.findall(r'(https?://[^\s]+)', content)
            soup = BeautifulSoup(content, "html.parser")
            href_links = [a['href'] for a in soup.find_all('a', href=True)]
            return urls + href_links

        links = extract_links(content)
        
        if not links:
            error_message = Message(text="Vui lòng nhập một đường link cần down hợp lệ hoặc reply một tin nhắn chứa link.")
            client.replyMessage(error_message, message_object, thread_id, thread_type)
            return
        
        video_link = links[0].strip()

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    # Cấu hình retry cho requests
    session = requests.Session()
    retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Hàm tải lên Catbox.moe với retry
    def upload_to_catbox(file_path):
        url = "https://catbox.moe/user/api.php"
        data = {'reqtype': 'fileupload', 'userhash': ''}
        for attempt in range(3):
            try:
                files = {'fileToUpload': open(file_path, 'rb')}
                response = session.post(url, data=data, files=files, timeout=30)
                response.raise_for_status()
                return response.text.strip()
            except (requests.RequestException, ConnectionError) as e:
                if attempt == 2:
                    raise Exception(f"Lỗi khi tải lên Catbox sau 3 lần thử: {str(e)}")
                time.sleep(2 ** attempt)  # Backoff theo cấp số nhân

    def download_youtube(link):
        ydl_opts = {
            'format': 'bestvideo[height<=360]+bestaudio/best[height<=360]/best',
            'outtmpl': 'modules/cache/temp_video.%(ext)s',
            'merge_output_format': 'mp4',
            'quiet': True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=True)
                title = info.get('title', 'Không có tiêu đề')
                ext = info.get('ext', 'mp4')
                file_path = f'modules/cache/temp_video.{ext}'
                thumbnail_url = info.get('thumbnail', 'https://files.catbox.moe/xjq5tm.jpeg')
                duration = int(info.get('duration', 0) * 1000)
                return file_path, title, 'YouTube', 'video', thumbnail_url, duration
        except Exception as e:
            raise Exception(f"Lỗi khi tải từ YouTube: {str(e)}")

    def download_tiktok(link):
        ydl_opts = {
            'format': 'best',
            'outtmpl': 'modules/cache/temp_video.%(ext)s',
            'quiet': True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=True)
                title = info.get('title', 'Không có tiêu đề')
                ext = info.get('ext', 'mp4')
                file_path = f'modules/cache/temp_video.{ext}'
                thumbnail_url = info.get('thumbnail', 'https://files.catbox.moe/xjq5tm.jpeg')
                duration = int(info.get('duration', 0) * 1000)
                return file_path, title, 'TikTok', 'video', thumbnail_url, duration
        except Exception as e:
            raise Exception(f"Lỗi khi tải từ TikTok: {str(e)}")

    def download_image(link):
        try:
            response = session.get(link, headers=headers, timeout=30)
            response.raise_for_status()
            content_type = response.headers.get('content-type', '')
            if 'image' in content_type:
                ext = content_type.split('/')[-1]
                file_path = f'modules/cache/temp_image.{ext}'
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                return file_path, 'Ảnh', 'Imgur', 'image', None, None
            else:
                raise Exception("Link không phải là ảnh")
        except Exception as e:
            raise Exception(f"Lỗi khi tải ảnh: {str(e)}")

    def download_direct_video(link):
        try:
            response = session.get(link, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            content_type = response.headers.get('content-type', '')
            if 'video' in content_type:
                ext = content_type.split('/')[-1] if '/' in content_type else 'mp4'
                file_path = f'modules/cache/temp_video.{ext}'
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                title = link.split('/')[-1]
                thumbnail_url = 'https://files.catbox.moe/xjq5tm.jpeg'
                duration = None
                return file_path, title, 'Direct Link', 'video', thumbnail_url, duration
            else:
                raise Exception("Link không phải là video")
        except Exception as e:
            raise Exception(f"Lỗi khi tải video trực tiếp: {str(e)}")

    try:
        if 'youtube.com' in video_link or 'youtu.be' in video_link:
            file_path, title, source, media_type, thumbnail_url, duration = download_youtube(video_link)
        elif 'tiktok.com' in video_link:
            file_path, title, source, media_type, thumbnail_url, duration = download_tiktok(video_link)
        elif 'catbox.moe' in video_link or video_link.endswith(('.mp4', '.mkv', '.avi', '.mov')):
            file_path, title, source, media_type, thumbnail_url, duration = download_direct_video(video_link)
        else:
            file_path, title, source, media_type, thumbnail_url, duration = download_image(video_link)

        sendtitle = f"Thể loại: {source}\nTiêu đề: {title}\nLoại: {media_type}"

        if media_type == 'image' and os.path.exists(file_path):
            message_to_send = Message(text=sendtitle)
            client.sendLocalImage(
                file_path,
                message=message_to_send,
                thread_id=thread_id,
                thread_type=thread_type,
                width=1200,
                height=1600
            )
            os.remove(file_path)

        elif media_type == 'video' and os.path.exists(file_path):
            video_url = upload_to_catbox(file_path)
            messagesend = Message(text=sendtitle)
            client.sendRemoteVideo(
                video_url,
                message=messagesend,
                thread_id=thread_id,
                thread_type=thread_type,
                thumbnailUrl=thumbnail_url,
                duration=duration
            )
            os.remove(file_path)

        else:
            raise Exception("Không thể tải tệp hoặc tệp không tồn tại")

    except Exception as e:
        error_message = Message(text=str(e))
        client.sendMessage(error_message, thread_id, thread_type)

def get_mitaizl():
    return {
        'dl': handle_down_command
    }