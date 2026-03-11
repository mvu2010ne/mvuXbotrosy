import requests
import urllib.parse
import os
import json
from zlapi.models import Message
from zlapi import ZaloAPIException, ThreadType, User, Group
from zlapi import _util
from PIL import Image
import hashlib
import logging
import time
import mimetypes
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# URL API của tmpfiles.org
TMPFILES_API_URL = 'https://tmpfiles.org/api/v1/upload'

# Hàm kiểm tra loại file
def get_file_type(url):
    print(f"Checking file type for URL: {url}")
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        content_type = response.headers.get('Content-Type', '').lower()
        print(f"Content-Type: {content_type}, Status: {response.status_code}")
        if content_type.startswith('image/'):
            return 'image', content_type.split('/')[-1]
        return None, None
    except Exception as e:
        logger.error(f"Error checking file type for URL {url}: {e}")
        print(f"Error checking file type: {e}")
        return None, None

# Hàm lấy MIME type từ định dạng
def get_mime_type(format):
    mime_type, _ = mimetypes.guess_type(f"file.{format.lower()}")
    return mime_type or f"image/{format.lower()}"

# Hàm chuyển đổi file ảnh
def convert_image(input_path, output_path, target_format):
    print(f"Converting image {input_path} to {output_path} (format: {target_format})")
    try:
        img = Image.open(input_path)
        if target_format.upper() in ['JPEG', 'JPG']:
            img = img.convert('RGB')  # JPEG không hỗ trợ RGBA
        img.save(output_path, target_format.upper())
        # Kiểm tra định dạng thực tế của file đã lưu
        with Image.open(output_path) as saved_img:
            actual_format = saved_img.format.lower()
            print(f"Actual format of saved image: {actual_format}")
            if actual_format != target_format.lower():
                logger.warning(f"Format mismatch: Saved as {actual_format}, expected {target_format}")
                return False
        print(f"Image conversion successful: {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error converting image {input_path} to {target_format}: {e}")
        print(f"Error converting image: {e}")
        return False

# Hàm upload ảnh lên tmpfiles.org
def upload_to_tmpfiles(file_path):
    try:
        with open(file_path, 'rb') as f:
            filename = os.path.basename(file_path)
            mime_type = get_mime_type(file_path.split('.')[-1])
            files = {'file': (filename, f, mime_type)}
            # Thiết lập retry mechanism
            session = requests.Session()
            retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
            session.mount("https://", HTTPAdapter(max_retries=retries))
            upload_response = session.post(TMPFILES_API_URL, files=files, timeout=10)
            print(f"tmpfiles.org API response status: {upload_response.status_code}")
            if upload_response.status_code == 200:
                response_data = upload_response.json()
                tmpfiles_link = response_data.get('data', {}).get('url')
                if tmpfiles_link:
                    logger.info(f"Uploaded to tmpfiles.org: {tmpfiles_link}")
                    print(f"Uploaded to tmpfiles.org: {tmpfiles_link}")
                    return tmpfiles_link
                else:
                    logger.error("No URL found in tmpfiles.org response")
                    print("No URL found in tmpfiles.org response")
                    return None
            else:
                logger.error(f"tmpfiles.org upload error: {upload_response.status_code} - {upload_response.text}")
                print(f"tmpfiles.org upload error: {upload_response.status_code} - {upload_response.text}")
                return None
    except Exception as e:
        logger.error(f"Error uploading to tmpfiles.org: {e}")
        print(f"Error uploading to tmpfiles.org: {e}")
        return None

# Hàm tải file từ URL
def download_file(url, output_path):
    print(f"Downloading file from {url} to {output_path}")
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded file to {output_path}")
            logger.info(f"Downloaded file to {output_path}")
            return True
        else:
            logger.error(f"Failed to download file: Status {response.status_code}")
            print(f"Failed to download file: Status {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        print(f"Error downloading file: {e}")
        return False

# Hàm xử lý lệnh chuyển đổi
def handle_convert_command(message, message_object, thread_id, thread_type, author_id, client):
    print(f"Processing command: {message}")
    # Gửi phản ứng "✅" để xác nhận
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=64)
    print("Sent reaction: {}".format(action))

    # Lấy định dạng đích từ lệnh
    try:
        parts = message.lower().split()
        print(f"Command parts: {parts}")
        if len(parts) < 2 or parts[0] != 'convert':
            raise ValueError("Invalid command format")
        target_format = parts[1].strip()
        if not target_format:
            raise ValueError("No target format provided")
        print(f"Target format: {target_format}")
    except Exception as e:
        logger.error(f"Error parsing command: {e}")
        print(f"Error parsing command: {e}")
        client.sendMessage(Message(text="Vui lòng cung cấp định dạng đích (ví dụ: convert png)."),
                           thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    # Kiểm tra xem có reply không
    if not message_object.quote:
        logger.error("No reply message found")
        print("Error: No reply message found")
        client.sendMessage(Message(text="Vui lòng reply vào một file hình ảnh."),
                           thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    # Lấy dữ liệu đính kèm từ tin nhắn được reply
    attach = message_object.quote.attach
    print(f"Attachment data: {attach}")
    if not attach:
        logger.error("No attachment in reply message")
        print("Error: No attachment in reply message")
        client.sendMessage(Message(text="Tin nhắn được reply không chứa tệp đính kèm."),
                           thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    # Trích xuất URL từ attach
    media_url = None
    try:
        attach_data = json.loads(attach) if isinstance(attach, str) else attach
        print(f"Parsed attachment data: {attach_data}")
        media_url = attach_data.get('hdUrl') or attach_data.get('href')
        if media_url:
            media_url = urllib.parse.unquote(media_url.replace("\\/", "/"))
            print(f"Extracted media URL: {media_url}")
        else:
            logger.error("No URL found in attachment data")
            print("Error: No URL found in attachment data")
            client.sendMessage(Message(text="Không tìm thấy URL trong dữ liệu đính kèm."),
                               thread_id=thread_id, thread_type=thread_type, ttl=60000)
            return
    except json.JSONDecodeError:
        logger.error("Attachment data is not valid JSON")
        print("Error: Attachment data is not valid JSON")
        client.sendMessage(Message(text="Dữ liệu đính kèm không phải định dạng JSON hợp lệ."),
                           thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return
    except Exception as e:
        logger.error(f"Error processing attachment data: {e}")
        print(f"Error processing attachment data: {e}")
        client.sendMessage(Message(text=f"Lỗi khi xử lý dữ liệu đính kèm: {e}"),
                           thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    # Kiểm tra loại file
    file_type, original_format = get_file_type(media_url)
    print(f"File type: {file_type}, Original format: {original_format}")
    if file_type != 'image':
        logger.error("Invalid file type (not image)")
        print("Error: Invalid file type")
        client.sendMessage(Message(text="URL không phải file hình ảnh hợp lệ."),
                           thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    # Danh sách định dạng ảnh hỗ trợ
    supported_formats = ['png', 'jpeg', 'jpg', 'bmp', 'gif', 'tiff', 'webp', 'ico', 'heic']
    if target_format.lower() not in supported_formats:
        logger.error(f"Unsupported format {target_format} for image")
        print(f"Error: Unsupported format {target_format} for image")
        client.sendMessage(Message(text=f"Định dạng {target_format} không được hỗ trợ. Các định dạng hỗ trợ: {', '.join(supported_formats)}."),
                           thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    try:
        # Tải file gốc
        print(f"Downloading file from {media_url}")
        file_response = requests.get(media_url, timeout=15)
        print(f"Download status: {file_response.status_code}")
        if file_response.status_code != 200:
            raise Exception(f"Không tải được file, mã lỗi: {file_response.status_code}")

        # Lưu file tạm
        input_path = f"temp_input.{original_format}"
        with open(input_path, "wb") as f:
            f.write(file_response.content)
        print(f"Saved input file: {input_path}")
        logger.info(f"Saved input file: {input_path}")

        # Chuyển đổi file ảnh
        output_path = f"converted_image.{target_format.lower()}"
        if not convert_image(input_path, output_path, target_format):
            raise Exception("Chuyển đổi file ảnh thất bại.")

        # Kiểm tra định dạng thực tế
        with Image.open(output_path) as img:
            actual_format = img.format.lower()
            width, height = img.size
        print(f"Converted image: {output_path}, Format: {actual_format}, Dimensions: {width}x{height}")
        logger.info(f"Converted image: {output_path}, Format: {actual_format}, Dimensions: {width}x{height}")
        if actual_format != target_format.lower():
            raise Exception(f"Định dạng sau chuyển đổi không đúng: Mong muốn {target_format}, nhận được {actual_format}")

        # Upload file đã chuyển đổi lên tmpfiles.org
        print(f"Uploading {output_path} to tmpfiles.org")
        tmpfiles_link = upload_to_tmpfiles(output_path)
        if not tmpfiles_link:
            raise Exception("Không thể upload ảnh lên tmpfiles.org.")

        # Tải file từ tmpfiles.org về để gửi qua sendRemoteFile
        downloaded_path = f"downloaded_image.{target_format.lower()}"
        if not download_file(tmpfiles_link, downloaded_path):
            raise Exception("Không thể tải file từ tmpfiles.org.")

        # Gửi file qua sendRemoteFile
        file_name = f"converted_image.{target_format.lower()}"
        print(f"Sending file via sendRemoteFile: {file_name}, URL: {tmpfiles_link}")
        client.sendRemoteFile(
            fileUrl=tmpfiles_link,
            thread_id=thread_id,
            thread_type=thread_type,
            fileName=file_name,
            extension=target_format.lower()
        )
        logger.info(f"Sent file via sendRemoteFile: {file_name} from {tmpfiles_link}")
        print(f"File sent successfully as {target_format}")
        client.sendMessage(Message(text=f"File ảnh đã được chuyển đổi sang {target_format.upper()} và upload lên tmpfiles.org: {tmpfiles_link}"),
                           thread_id=thread_id, thread_type=thread_type, ttl=60000)

    except Exception as e:
        logger.error(f"Error in convert command: {e}")
        print(f"Error in convert command: {e}")
        client.sendMessage(Message(text=f"Đã xảy ra lỗi: {e}"),
                           thread_id=thread_id, thread_type=thread_type, ttl=60000)
    finally:
        # Dọn dẹp file tạm
        for path in [f"temp_input.{original_format}", f"converted_image.{target_format.lower()}", f"downloaded_image.{target_format.lower()}"]:
            if os.path.exists(path):
                os.remove(path)
                logger.info(f"Deleted temporary file: {path}")
                print(f"Deleted temporary file: {path}")

# Định nghĩa lệnh
def get_mitaizl():
    return {
        'convert': handle_convert_command
    }