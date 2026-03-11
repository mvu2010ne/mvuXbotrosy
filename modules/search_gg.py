import random
import requests
from zlapi.models import *
from config import ADMIN, IMEI
from bs4 import BeautifulSoup
import os
import time
import urllib.parse
import re
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from PIL import Image, ImageSequence
import tempfile

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "📸 Tìm kiếm và gửi ảnh từ Google Images dựa trên từ khóa người dùng cung cấp.",
    'tính năng': [
        "🔍 Tìm kiếm ảnh trên Google Images bằng từ khóa với tối đa 10 ảnh mỗi lần.",
        "📩 Gửi nhiều ảnh PNG cùng lúc bằng sendMultiLocalImage hoặc GIF bằng sendLocalGif.",
        "🔒 Hạn chế quyền truy cập: chỉ admin có thể sử dụng lệnh để đảm bảo kiểm soát.",
        "🚫 Chặn từ khóa nhạy cảm để ngăn nội dung không phù hợp.",
        "⚠️ Xử lý lỗi chi tiết khi gọi API, tải ảnh hoặc gửi kết quả, với thông báo thân thiện.",
        "🔄 Tự động retry tối đa 5 lần nếu gửi GIF thất bại.",
        "🗑️ Tự động xóa file tạm sau khi gửi, ảnh tự xóa sau 60 giây."
    ],
    'hướng dẫn sử dụng': [
        "📩 Sử dụng lệnh '/gg <từ khóa>' để tìm kiếm ảnh từ Google Images.",
        "📌 Ví dụ: /gg anime girl để nhận tối đa 10 ảnh.",
        "✅ Nhận kết quả ảnh kèm thông báo trạng thái ngay lập tức.",
        "⚠️ Lưu ý: Chỉ admin được phép sử dụng lệnh này, từ khóa nhạy cảm sẽ bị chặn."
    ]
}

CONFIG = {
    'paths': {
        'save_dir': 'temp',
    },
    'download': {
        'max_attempts': 10,
        'timeout': 5000,
        'min_size': 1024,
    },
    'messages': {
        'no_query': lambda name: f"{name} Vui lòng nhập từ khóa tìm kiếm từ google\n Ví dụ: gg anime girl \ngg anime girl gif để tìm ảnh gif ",
        'search_result': lambda name, query: f"[{name}] [{query}]",
        'download_failed': lambda name, attempts: f"{name} Không thể tải ảnh sau {attempts} lần thử. Vui lòng thử lại sau.",
        'no_results': lambda name: f"{name} Không tìm thấy ảnh. Vui lòng thử lại sau.",
        'api_error': lambda name: f"{name} Lỗi khi tìm kiếm ảnh :(((.",
        'banned_keyword': lambda name: f"{name} Từ khóa tìm kiếm này bị cấm!",
    },
    'headers': {
        'user_agents': [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:90.0) Gecko/20100101 Firefox/90.0',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59 Safari/537.36',
            'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Mobile Safari/537.36',
            'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:88.0) Gecko/20100101 Firefox/88.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36'
        ],
        'accept': 'image/jpeg,image/png,image/gif,*/*;q=0.8',
        'referer': 'https://www.google.com/'
    },
    'banned_keywords': [
        # Add banned keywords here
    ]
}

# Tạo session HTTP để tối ưu kết nối
session = requests.Session()

def get_random_user_agent():
    """Return a random User-Agent from the configured list."""
    return random.choice(CONFIG['headers']['user_agents'])

def ensure_temp_dir():
    """Ensure the temporary directory exists."""
    if not os.path.exists(CONFIG['paths']['save_dir']):
        os.makedirs(CONFIG['paths']['save_dir'])

def delete_file(file_path):
    """Delete a file if it exists."""
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

def check_url(url):
    """Validate if the URL is properly formatted and accessible."""
    try:
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': CONFIG['headers']['accept'],
            'Referer': CONFIG['headers']['referer']
        }
        response = session.head(url, headers=headers, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def search_google_images(query):
    api_key = "AIzaSyAiNMkDVOKxcAPfmW1yYV5zTL4OWFqLAzg"  # API key của bạn
    cx = "c44d5da1abf7144d9"  # Search Engine ID từ mã nhúng
    encoded_query = urllib.parse.quote(query)
    url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={cx}&q={encoded_query}&searchType=image"
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept': CONFIG['headers']['accept'],
        'Referer': CONFIG['headers']['referer']
    }
    try:
        response = session.get(url, headers=headers, timeout=CONFIG['download']['timeout'] / 1000)
        response.raise_for_status()
        data = response.json()
        images = [item['link'] for item in data.get('items', [])]
        return images[:20]
    except requests.RequestException as e:
        print(f"ERROR: API request failed: {e}")
        return []

def download_image(image_url, query, index):
    """
    Download an image from a URL and save it as PNG or GIF.
    """
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept': CONFIG['headers']['accept'],
        'Referer': CONFIG['headers']['referer']
    }

    try:
        if not check_url(image_url):
            print(f"ERROR: Invalid URL: {image_url}")
            return None

        image_response = session.get(image_url, headers=headers, stream=True, timeout=CONFIG['download']['timeout'] / 1000)
        image_response.raise_for_status()

        content_type = image_response.headers.get('Content-Type', '').lower()
        print(f"INFO: Downloading image {index+1} - Content-Type: {content_type}")

        if 'image/gif' in content_type:
            suffix = '.gif'
            max_size = 500  # Max dimension for GIF
            is_gif = True
            image_data = BytesIO(image_response.content)
            with Image.open(image_data) as img:
                frames = [frame.copy() for frame in ImageSequence.Iterator(img)]
                orig_width, orig_height = img.size
                if max(orig_width, orig_height) > max_size:
                    scale = max_size / max(orig_width, orig_height)
                    new_width = int(orig_width * scale)
                    new_height = int(orig_height * scale)
                    frames = [
                        frame.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        for frame in frames
                    ]
                else:
                    new_width, new_height = orig_width, orig_height
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False, dir=CONFIG['paths']['save_dir']) as tmp:
                    image_path = tmp.name
                    frames[0].save(
                        image_path,
                        save_all=True,
                        append_images=frames[1:],
                        duration=img.info.get('duration', 100),
                        loop=0,
                        optimize=True
                    )
        else:
            suffix = '.png'
            is_gif = False
            max_size = 1920  # Max dimension for static images
            image_data = BytesIO(image_response.content)
            image = Image.open(image_data)

            # Handle transparency and convert to RGB
            if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[3] if image.mode == 'RGBA' else image.getchannel('A'))
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')

            # Resize if necessary
            orig_width, orig_height = image.size
            if max(orig_width, orig_height) > max_size:
                scale = max_size / max(orig_width, orig_height)
                new_width = int(orig_width * scale)
                new_height = int(orig_height * scale)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            else:
                new_width, new_height = orig_width, orig_height

            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False, dir=CONFIG['paths']['save_dir']) as tmp:
                image_path = tmp.name
                image.save(image_path, format='PNG', optimize=True, quality=85)

        file_size = os.path.getsize(image_path)
        if file_size < CONFIG['download']['min_size']:
            delete_file(image_path)
            print(f"Image too small: {file_size} bytes")
            return None

        format = 'GIF' if is_gif else 'PNG'
        print(f"Image {index+1} from URL: {image_url}")
        print(f"- Original format: {content_type}")
        print(f"- Saved format: {format}")
        print(f"- Resolution: {new_width}x{new_height} pixels")
        print(f"- File size: {file_size} bytes ({file_size / 1024:.2f} KB)")
        print("-" * 50)

        return {
            'path': image_path,
            'width': new_width,
            'height': new_height,
            'is_gif': is_gif,
            'thumbnail_url': image_url if is_gif else None,
            'content_type': content_type
        }
    except (requests.RequestException, OSError, Image.UnidentifiedImageError) as e:
        print(f"ERROR: Failed to download image {index+1}: {str(e)}")
        return None

def handle_search_command(message, message_object, thread_id, thread_type, author_id, client):
    """Handle the /gg command to search and send multiple images or GIFs."""
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
    print(f"INFO: Starting /gg command from {author_id} in {thread_type}-{thread_id}")

    ensure_temp_dir()
    # Lấy tên người dùng
    sender_name = "Người dùng"  # Giá trị mặc định
    try:
        if hasattr(message_object, 'mentions') and message_object.mentions:
            for mention in message_object.mentions:
                if mention.uid == author_id:
                    sender_name = mention.dname or "Người dùng"
                    break
        else:
            user_info_response = client.fetchUserInfo(author_id)
            user_info = user_info_response.changed_profiles.get(str(author_id))
            if user_info and hasattr(user_info, 'displayName'):
                sender_name = user_info.displayName
    except Exception as e:
        print(f"ERROR: Failed to fetch sender name for {author_id}: {str(e)}")

    try:
        # Tách lệnh
        text = message.split()
        print(f"DEBUG: text = {text}")  # Debug đầu vào

        if len(text) < 2 or not text[1].strip():
            msg = CONFIG['messages']['no_query'](sender_name)
            styles = MultiMsgStyle([MessageStyle(offset=0, length=10000, style="font", size="10", auto_format=False)])
            client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=30000)
            return

        # Tách từ khóa và số lượng (theo cách của search_pin.py)
        try:
            num_images = int(text[-1])
            query = " ".join(text[1:-1]).strip().lower()
            if not query:  # Nếu không có từ khóa sau khi tách
                raise ValueError
        except ValueError:
            num_images = 10  # Mặc định 10 ảnh
            query = " ".join(text[1:]).strip().lower()

        # Giới hạn số lượng ảnh
        max_images = 30
        if num_images > max_images:
            msg = f"{sender_name} Số lượng ảnh tối đa là {max_images}!"
            styles = MultiMsgStyle([MessageStyle(offset=0, length=10000, style="font", size="10", auto_format=False)])
            client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=30000)
            return
        if num_images <= 0:
            msg = f"{sender_name} Số lượng ảnh phải lớn hơn 0!"
            styles = MultiMsgStyle([MessageStyle(offset=0, length=10000, style="font", size="10", auto_format=False)])
            client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=30000)
            return

        # Kiểm tra từ khóa cấm
        if any(keyword in query or keyword in query.replace(" ", "") for keyword in CONFIG['banned_keywords']):
            msg = CONFIG['messages']['banned_keyword'](sender_name)
            styles = MultiMsgStyle([MessageStyle(offset=0, length=10000, style="font", size="10", auto_format=False)])
            client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=30000)
            return

        # Tìm kiếm ảnh
        image_urls = search_google_images(query)
        if not image_urls:
            msg = CONFIG['messages']['no_results'](sender_name)
            styles = MultiMsgStyle([MessageStyle(offset=0, length=10000, style="font", size="10", auto_format=False)])
            client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=30000)
            return

        # Giới hạn số lượng ảnh tải
        image_urls = random.sample(image_urls, min(num_images, len(image_urls)))

        # Tải ảnh đồng thời
        downloaded_images = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_index = {executor.submit(download_image, url, query, i): i for i, url in enumerate(image_urls)}
            for future in as_completed(future_to_index):
                result = future.result()
                if result:
                    downloaded_images.append(result)

        if not downloaded_images:
            msg = CONFIG['messages']['download_failed'](sender_name, len(image_urls))
            styles = MultiMsgStyle([MessageStyle(offset=0, length=10000, style="font", size="10", auto_format=False)])
            client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=30000)
            return

        # Tách ảnh tĩnh và GIF
        static_images = [info for info in downloaded_images if not info['is_gif']]
        gif_images = [info for info in downloaded_images if info['is_gif']]

        static_paths = [info['path'] for info in static_images]
        gif_paths = [info['path'] for info in gif_images]
        gif_widths = [info['width'] for info in gif_images]
        gif_heights = [info['height'] for info in gif_images]
        gif_thumbnail_urls = [info['thumbnail_url'] for info in gif_images]

        if not static_paths and not gif_paths:
            msg = CONFIG['messages']['download_failed'](sender_name, len(image_urls))
            styles = MultiMsgStyle([MessageStyle(offset=0, length=10000, style="font", size="10", auto_format=False)])
            client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=30000)
            return

        # Gửi ảnh tĩnh
        if static_paths:
            try:
                valid_paths = []
                for path in static_paths:
                    if os.path.exists(path) and os.path.getsize(path) > 0:
                        try:
                            with Image.open(path) as img:
                                img.verify()
                            valid_paths.append(path)
                        except Exception as e:
                            print(f"ERROR: Invalid image {path}: {str(e)}")
                            continue
                    else:
                        print(f"ERROR: Image file {path} does not exist or is empty")
                        continue

                if valid_paths:
                    print(f"INFO: Sending {len(valid_paths)} static images with original size")
                    result = client.sendMultiLocalImage(
                        imagePathList=valid_paths,
                        thread_id=thread_id,
                        thread_type=thread_type,
                        width=None,
                        height=None,
                        message=Message(text=f"📷 Ảnh từ '{query}' ({len(valid_paths)} ảnh)"),
                        ttl=60000
                    )
                    if hasattr(result, 'error_code') and result.error_code == 0:
                        print(f"INFO: Successfully sent {len(valid_paths)} static images")
                    else:
                        print(f"ERROR: Failed to send static images: {getattr(result, 'error_message', 'Unknown error')}")
                else:
                    print("ERROR: No valid static images to send")
                    client.replyMessage(
                        Message(text="❌ Không có ảnh tĩnh hợp lệ để gửi!"),
                        message_object,
                        thread_id,
                        thread_type,
                        ttl=60000
                    )
            except Exception as e:
                print(f"ERROR: Error sending static images: {str(e)}")
            finally:
                for path in static_paths:
                    delete_file(path)

        # Gửi GIF
        if gif_paths:
            max_attempts = 5
            for i, (gif_path, thumbnail_url, width, height) in enumerate(zip(gif_paths, gif_thumbnail_urls, gif_widths, gif_heights)):
                attempt = 0
                while attempt < max_attempts:
                    try:
                        file_size = os.path.getsize(gif_path) / (1024 * 1024)
                        if file_size > 15:
                            print(f"WARNING: GIF {i+1} too large ({file_size:.2f}MB), attempting compression...")
                            with Image.open(gif_path) as img:
                                frames = [frame.copy() for frame in ImageSequence.Iterator(img)]
                                frames = frames[:10]
                                frames[0].save(
                                    gif_path,
                                    save_all=True,
                                    append_images=frames[1:],
                                    duration=img.info.get('duration', 100),
                                    loop=0,
                                    optimize=True
                                )
                            file_size = os.path.getsize(gif_path) / (1024 * 1024)
                            print(f"INFO: Compressed GIF {i+1} to {file_size:.2f}MB")

                        with Image.open(gif_path) as img:
                            frames = [frame.copy() for frame in ImageSequence.Iterator(img)]
                            frame_count = len(frames)
                            orig_width, orig_height = frames[0].size
                            print(f"INFO: GIF {i+1} - Frames: {frame_count}, Size: {file_size:.2f}MB, Resolution: {orig_width}x{orig_height}")

                        try:
                            thumbnail_response = session.head(thumbnail_url, headers={
                                'User-Agent': get_random_user_agent(),
                                'Accept': CONFIG['headers']['accept'],
                                'Referer': CONFIG['headers']['referer']
                            }, timeout=5)
                            if thumbnail_response.status_code != 200:
                                print(f"WARNING: Invalid thumbnail URL for GIF {i+1}: {thumbnail_url}")
                                thumbnail_url = ""
                        except requests.RequestException:
                            print(f"WARNING: Unable to check thumbnail URL for GIF {i+1}: {thumbnail_url}")
                            thumbnail_url = ""

                        result = client.sendLocalGif(
                            gifPath=gif_path,
                            thumbnailUrl=thumbnail_url,
                            thread_id=thread_id,
                            thread_type=thread_type,
                            width=width,
                            height=height,
                            ttl=60000
                        )

                        if hasattr(result, 'error_code') and result.error_code == 0 and result.data and "msgId" in result.data:
                            print(f"INFO: Successfully sent GIF {i+1} after {attempt + 1} attempts")
                            break
                        else:
                            error_msg = getattr(result, 'error_message', 'Invalid response')
                            error_code = getattr(result, 'error_code', 'N/A')
                            print(f"ERROR: Failed to send GIF {i+1} - Error #{error_code}: {error_msg}")
                            raise Exception("Failed to send GIF")

                    except Exception as e:
                        attempt += 1
                        print(f"ERROR: Attempt {attempt} failed for GIF {i+1}: {str(e)}")
                        if attempt == max_attempts:
                            print(f"ERROR: Could not send GIF {i+1} after {max_attempts} attempts")
                    finally:
                        if gif_path and os.path.exists(gif_path):
                            delete_file(gif_path)

        print(f"INFO: Sent {len(static_paths)} static images and {len(gif_paths)} GIFs for query '{query}'")

    except Exception as e:
        print(f"ERROR: General error: {str(e)}")
        msg = CONFIG['messages']['api_error'](sender_name)
        styles = MultiMsgStyle([MessageStyle(offset=0, length=10000, style="font", size="10", auto_format=False)])
        client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=30000)

def get_mitaizl():
    return {
        'gg': handle_search_command
    }