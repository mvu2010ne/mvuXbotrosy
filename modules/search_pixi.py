import random
import requests
import os
import urllib.parse
from io import BytesIO
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed
from zlapi.models import *
import tempfile

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🎨 Tìm kiếm và gửi ảnh từ Pixiv dựa trên từ khóa người dùng cung cấp.",
    'tính năng': [
        "🔍 Tìm kiếm ảnh trên Pixiv bằng từ khóa với tối đa 17 ảnh mỗi lần.",
        "📩 Gửi nhiều ảnh PNG cùng lúc bằng sendMultiLocalImage.",
        "🚫 Chặn từ khóa nhạy cảm để ngăn nội dung không phù hợp.",
        "⚠️ Xử lý lỗi chi tiết khi gọi API, tải ảnh hoặc gửi kết quả.",
        "🗑️ Tự động xóa file tạm sau khi gửi, ảnh tự xóa sau 60 giây."
    ],
    'hướng dẫn sử dụng': [
        "📩 Sử dụng lệnh '/pix <từ khóa>' để tìm kiếm ảnh từ Pixiv.",
        "📌 Ví dụ: /pix anime girl để nhận tối đa 17 ảnh.",
        "✅ Nhận kết quả ảnh kèm thông báo trạng thái ngay lập tức.",
        "⚠️ Lưu ý: Từ khóa nhạy cảm sẽ bị chặn."
    ]
}

CONFIG = {
    'paths': {
        'save_dir': 'temp'
    },
    'download': {
        'max_attempts': 10,
        'timeout': 5000,
        'min_size': 1024,
        'max_images': 6
    },
    'messages': {
        'no_query': lambda name: f"{name} Vui lòng nhập từ khóa tìm kiếm từ Pixiv\nVí dụ: /pix anime girl",
        'search_result': lambda name, query: f"[{name}] Kết quả tìm kiếm cho '{query}'",
        'download_failed': lambda name, attempts: f"{name} Không thể tải ảnh sau {attempts} lần thử. Vui lòng thử lại.",
        'no_results': lambda name: f"{name} Không tìm thấy ảnh. Vui lòng thử lại.",
        'api_error': lambda name: f"{name} Lỗi khi tìm kiếm ảnh trên Pixiv :(((.",
        'banned_keyword': lambda name: f"{name} Từ khóa tìm kiếm này bị cấm!"
    },
    'headers': {
        'user_agents': [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:90.0) Gecko/20100101 Firefox/90.0',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1'
        ],
        'accept': 'image/jpeg,image/png,*/*;q=0.8',
        'referer': 'https://www.pixiv.net/'
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

def search_pixiv_images(query):
    """Search for images on Pixiv."""
    encoded_query = urllib.parse.quote(query)
    url = f"https://www.pixiv.net/ajax/search/artworks/{encoded_query}?word={encoded_query}&order=date_d&mode=all&p=1&csw=0&s_mode=s_tag&type=all&lang=en"
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept': CONFIG['headers']['accept'],
        'Referer': CONFIG['headers']['referer']
    }
    try:
        response = session.get(url, headers=headers, timeout=CONFIG['download']['timeout'] / 1000)
        response.raise_for_status()
        data = response.json()
        if data['error']:
            return []
        return [artwork['url'] for artwork in data['body']['illustManga']['data'] if 'url' in artwork]
    except requests.RequestException as e:
        print(f"Error during Pixiv request: {e}")
        return []

def download_image(image_url, query, index):
    """Download an image from a URL and save it as PNG."""
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

        max_size = 1920
        image_data = BytesIO(image_response.content)
        image = Image.open(image_data)
        if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3] if image.mode == 'RGBA' else image.getchannel('A'))
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')

        orig_width, orig_height = image.size
        if max(orig_width, orig_height) > max_size:
            scale = max_size / max(orig_width, orig_height)
            new_width = int(orig_width * scale)
            new_height = int(orig_height * scale)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        else:
            new_width, new_height = orig_width, orig_height

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False, dir=CONFIG['paths']['save_dir']) as tmp:
            image_path = tmp.name
            image.save(image_path, format='PNG', optimize=True, quality=85)

        file_size = os.path.getsize(image_path)
        if file_size < CONFIG['download']['min_size']:
            delete_file(image_path)
            print(f"Image too small: {file_size} bytes")
            return None

        print(f"Image {index+1} from URL: {image_url}")
        print(f"- Original format: {content_type}")
        print(f"- Saved format: PNG")
        print(f"- Resolution: {new_width}x{new_height} pixels")
        print(f"- File size: {file_size} bytes ({file_size / 1024:.2f} KB)")
        print("-" * 50)

        return {
            'path': image_path,
            'width': new_width,
            'height': new_height
        }
    except Exception as e:
        print(f"ERROR: Failed to download image {index+1}: {str(e)}")
        return None

def handle_pixiv_command(message, message_object, thread_id, thread_type, author_id, client):
    """Handle the /pix command to search and send multiple images."""
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
    print(f"INFO: Starting /pix command from {author_id} in {thread_type}-{thread_id}")

    ensure_temp_dir()

    # Lấy tên người dùng
    sender_name = "Người dùng"
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
        if len(text) < 2 or not text[1].strip():
            msg = CONFIG['messages']['no_query'](sender_name)
            styles = MultiMsgStyle([MessageStyle(offset=0, length=10000, style="font", size="10", auto_format=False)])
            client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=30000)
            return

        # Tách từ khóa và số lượng
        try:
            num_images = int(text[-1])
            query = " ".join(text[1:-1]).strip().lower()
            if not query:
                raise ValueError
        except ValueError:
            num_images = CONFIG['download']['max_images']
            query = " ".join(text[1:]).strip().lower()

        # Giới hạn số lượng ảnh
        if num_images > CONFIG['download']['max_images']:
            msg = f"{sender_name} Số lượng ảnh tối đa là {CONFIG['download']['max_images']}!"
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
        image_urls = search_pixiv_images(query)
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

        # Gửi ảnh
        image_paths = [info['path'] for info in downloaded_images]
        try:
            valid_paths = []
            for path in image_paths:
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
                print(f"INFO: Sending {len(valid_paths)} images")
                result = client.sendMultiLocalImage(
                    imagePathList=valid_paths,
                    thread_id=thread_id,
                    thread_type=thread_type,
                    message=Message(text=CONFIG['messages']['search_result'](sender_name, query)),
                    ttl=60000
                )
                if hasattr(result, 'error_code') and result.error_code == 0:
                    print(f"INFO: Successfully sent {len(valid_paths)} images")
                else:
                    print(f"ERROR: Failed to send images: {getattr(result, 'error_message', 'Unknown error')}")
            else:
                print("ERROR: No valid images to send")
                client.replyMessage(
                    Message(text="❌ Không có ảnh hợp lệ để gửi!"),
                    message_object,
                    thread_id,
                    thread_type,
                    ttl=60000
                )
        except Exception as e:
            print(f"ERROR: Error sending images: {str(e)}")
        finally:
            for path in image_paths:
                delete_file(path)

        print(f"INFO: Sent {len(image_paths)} images for query '{query}'")

    except Exception as e:
        print(f"ERROR: General error: {str(e)}")
        msg = CONFIG['messages']['api_error'](sender_name)
        styles = MultiMsgStyle([MessageStyle(offset=0, length=10000, style="font", size="10", auto_format=False)])
        client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=30000)

def get_mitaizl():
    return {
        'pix': handle_pixiv_command
    }