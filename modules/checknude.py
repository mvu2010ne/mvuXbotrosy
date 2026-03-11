from zlapi.models import Message
import requests
import urllib.parse
import json
import os
from PIL import Image
import io
from nudenet import NudeDetector
import imageio
import cv2
import numpy as np

# Khởi tạo NudeDetector
nude_detector = NudeDetector()

# Hàm kiểm tra độ nhạy cảm của ảnh sử dụng NudeNet
def check_image_sensitivity(image_path_or_url, is_url=True):
    try:
        if is_url:
            response = requests.get(image_path_or_url, timeout=10)
            if response.status_code != 200:
                return {"error": f"Lỗi tải ảnh: HTTP {response.status_code}"}
            image = Image.open(io.BytesIO(response.content))
            temp_image_path = "temp_image.jpg"
            # Chuyển đổi định dạng sang JPEG để đảm bảo tương thích
            if image.format == "WEBP":
                image = image.convert("RGB")  # Chuyển đổi WebP sang RGB để lưu dưới dạng JPEG
            image.save(temp_image_path, format="JPEG")
        else:
            temp_image_path = image_path_or_url
            image = Image.open(temp_image_path)
            if image.format == "WEBP":
                image = image.convert("RGB")
                temp_converted_path = "temp_converted_image.jpg"
                image.save(temp_converted_path, format="JPEG")
                temp_image_path = temp_converted_path

        results = nude_detector.detect(temp_image_path)
        print([detection['class'] for detection in results])

        if is_url and os.path.exists(temp_image_path):
            os.remove(temp_image_path)
        elif not is_url and image.format == "WEBP" and os.path.exists(temp_converted_path):
            os.remove(temp_converted_path)

        # Bản dịch và emoji cho các nhãn
        label_map = {
            'EXPOSED_ANUS': ('Hậu môn lộ rõ', '❌'),
            'EXPOSED_BUTTOCKS': ('Mông lộ rõ', '🍑'),
            'EXPOSED_FEMALE_GENITALIA': ('Bộ phận sinh dục nữ lộ rõ', '❌'),
            'EXPOSED_MALE_GENITALIA': ('Bộ phận sinh dục nam lộ rõ', '❌'),
            'EXPOSED_FEMALE_BREAST': ('Ngực nữ lộ rõ', '❌'),
            'BUTTOCKS': ('Mông', '🍑'),
            'FEMALE_BREAST': ('Ngực nữ', '❌'),
            'FACE_FEMALE': ('Khuôn mặt nữ', '👩'),
            'FACE_MALE': ('Khuôn mặt nam', '👱'),
            'FEET': ('Bàn chân', '👣'),
            'HANDS': ('Bàn tay', '✋'),
            'BELLY': ('Bụng', '🩳'),
            'MALE_CHEST': ('Ngực nam', '💪'),
            'FEMALE_CHEST': ('Ngực nữ (chung)', '❌'),
            'BACK': ('Lưng', '🛌'),
            'ARMPITS': ('Nách', '💪'),
            'BELLY_EXPOSED': ('Bụng lộ rõ', '🩳'),
            'FEMALE_BREAST_COVERED': ('Ngực nữ được che phủ', '👙'),
            'ARMPITS_EXPOSED': ('Nách lộ rõ', '💪'),
            'BUTTOCKS_EXPOSED': ('Mông lộ rõ', '🍑'),
            'FEET_EXPOSED': ('Bàn chân lộ rõ', '👣'),
            'FEMALE_GENITALIA_COVERED': ('Bộ phận sinh dục nữ được che phủ', '❌'),
            'BELLY_COVERED': ('Bụng được che phủ', '🩳'),
            'FEET_COVERED': ('Bàn chân được che phủ', '👣'),
            'FEMALE_BREAST_EXPOSED': ('Ngực nữ lộ rõ', '❌'),
            'BUTTOCKS_COVERED': ('Mông được che phủ', '👗'),
            'FEMALE_GENITALIA_EXPOSED': ('Bộ phận sinh dục nữ lộ rõ', '❌'),
            'ANUS_EXPOSED': ('Hậu môn lộ rõ', '🔞'),
            'MALE_GENITALIA_EXPOSED': ('Bộ phận sinh dục nam lộ rõ', '❌')
        }

        sensitivity_report = []
        is_sensitive = False
        detected_labels = set()

        for detection in results:
            label = detection['class']
            score = detection['score']
            if label not in detected_labels and score > 0.5:
                vietnamese_label, icon = label_map.get(label, (label, '❓'))
                sensitivity_report.append(f"➜ {icon} {vietnamese_label}: Xác suất {score*100:.0f}%")
                detected_labels.add(label)
                if label in [
                    'EXPOSED_ANUS', 'EXPOSED_BUTTOCKS', 'EXPOSED_FEMALE_GENITALIA',
                    'EXPOSED_MALE_GENITALIA', 'EXPOSED_FEMALE_BREAST', 'BUTTOCKS', 'FEMALE_BREAST'
                ]:
                    is_sensitive = True

        if not sensitivity_report:
            sensitivity_report.append("Không phát hiện nội dung nào với xác suất đáng kể.")

        return {
            "is_sensitive": is_sensitive,
            "report": sensitivity_report
        }

    except Exception as e:
        return {"error": f"Lỗi khi kiểm tra ảnh: {str(e)}"}

# Hàm trích xuất khung hình đầu và cuối từ GIF, video hoặc WebP động
def extract_frames(media_url, media_type):
    """
    Trích xuất khung hình đầu và cuối từ GIF, video hoặc WebP động.
    Trả về danh sách đường dẫn file tạm của các khung hình.
    """
    temp_files = []
    try:
        # Tải file từ URL
        response = requests.get(media_url, timeout=10)
        if response.status_code != 200:
            return {"error": f"Lỗi tải {media_type}: HTTP {response.status_code}"}

        temp_media_path = f"temp_media.{media_type if media_type != 'image' else 'webp'}"
        with open(temp_media_path, "wb") as f:
            f.write(response.content)

        if media_type in ["gif", "image"]:  # Xử lý cả GIF và WebP động
            try:
                # Đọc file bằng imageio để kiểm tra xem có phải ảnh động
                reader = imageio.get_reader(temp_media_path)
                frames = [reader.get_data(0), reader.get_data(-1)]  # Lấy khung đầu và cuối
                for i, frame in enumerate(frames):
                    temp_image_path = f"temp_frame_{i}.jpg"
                    imageio.imwrite(temp_image_path, frame, format="JPEG")
                    temp_files.append(temp_image_path)
                reader.close()
            except Exception:
                # Nếu không phải ảnh động, xử lý như ảnh tĩnh
                if media_type == "image":
                    temp_image_path = "temp_frame_0.jpg"
                    image = Image.open(temp_media_path).convert("RGB")
                    image.save(temp_image_path, format="JPEG")
                    temp_files.append(temp_image_path)

        elif media_type == "video":
            # Đọc video bằng OpenCV
            cap = cv2.VideoCapture(temp_media_path)
            if not cap.isOpened():
                return {"error": "Không thể mở video"}

            # Lấy khung đầu
            ret, frame = cap.read()
            if ret:
                temp_image_path = "temp_frame_0.jpg"
                cv2.imwrite(temp_image_path, frame)
                temp_files.append(temp_image_path)

            # Lấy khung cuối
            cap.set(cv2.CAP_PROP_POS_FRAMES, cap.get(cv2.CAP_PROP_FRAME_COUNT) - 1)
            ret, frame = cap.read()
            if ret:
                temp_image_path = "temp_frame_1.jpg"
                cv2.imwrite(temp_image_path, frame)
                temp_files.append(temp_image_path)

            cap.release()

        # Xóa file media tạm
        if os.path.exists(temp_media_path):
            os.remove(temp_media_path)

        return temp_files

    except Exception as e:
        return {"error": f"Lỗi khi trích xuất khung hình: {str(e)}"}

# Hàm xử lý lệnh kiểm tra độ nhạy cảm
def handle_check_sensitivity_command(message, message_object, thread_id, thread_type, author_id, client):
    """
    Xử lý lệnh kiểm tra độ nhạy cảm của ảnh, GIF, video hoặc WebP từ tin nhắn gốc hoặc reply.
    """
    # Gửi phản ứng "✅" xác nhận nhận lệnh
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    print("==> Vào lệnh handle_check_sensitivity_command")

    # Kiểm tra Content-Type
    def get_content_type(url):
        try:
            response = requests.head(url, allow_redirects=True, timeout=10)
            return response.headers.get('Content-Type', '')
        except Exception as e:
            print(f"Lỗi khi lấy Content-Type: {e}")
            return ''

    # Hàm suy ra media_type từ đuôi tệp
    def infer_media_type_from_extension(url, content_type):
        url_lower = url.lower()
        if content_type == 'application/octet-stream':
            if url_lower.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                return 'image'
            elif url_lower.endswith('.gif'):
                return 'gif'
            elif url_lower.endswith(('.mp4', '.avi', '.mov', '.mkv')):
                return 'video'
        return None

    # Hàm lấy URL media
    def get_media_url(data):
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return data  # Nếu là chuỗi URL trực tiếp
        if isinstance(data, dict):
            return data.get('hdUrl') or data.get('normalUrl') or data.get('oriUrl') or data.get('href')
        return None

    # Xác định nguồn media (quote hoặc content)
    media_url = None
    media_type = None

    if message_object.quote and message_object.quote.attach:
        # Xử lý tin nhắn reply
        attach = message_object.quote.attach
        print(f"Debug: Quote attach: {attach}")
        media_url = get_media_url(attach)
        if not media_url:
            client.sendMessage(
                Message(text="⭕ Lỗi: Không thể lấy URL từ tin nhắn reply."),
                thread_id, thread_type, ttl=60000
            )
            return
    elif message_object.msgType in ['chat.gif', 'chat.video.msg', 'chat.photo'] and message_object.content:
        # Xử lý tin nhắn gốc là GIF, video hoặc ảnh
        content = message_object.content
        print(f"Debug: Content: {content}")
        media_url = get_media_url(content)
        media_type = 'gif' if message_object.msgType == 'chat.gif' else 'video' if message_object.msgType == 'chat.video.msg' else 'image'
        if not media_url:
            client.sendMessage(
                Message(text="⭕ Lỗi: Không thể lấy URL từ tin nhắn gốc."),
                thread_id, thread_type, ttl=60000
            )
            return
    else:
        client.sendMessage(
            Message(text="⭕ Vui lòng reply vào một tin nhắn chứa ảnh, GIF, video hoặc WebP, hoặc gửi trực tiếp ảnh/GIF/video!"),
            thread_id, thread_type, ttl=60000
        )
        return

    # Kiểm tra Content-Type
    content_type = get_content_type(media_url)
    print(f"Debug: Content-Type: {content_type}")
    if not media_type:  # Nếu chưa xác định từ msgType
        if content_type.startswith('image/'):
            media_type = 'image' if content_type != 'image/gif' else 'gif'
        elif content_type.startswith('video/'):
            media_type = 'video'
        else:
            # Thử suy ra từ đuôi tệp nếu Content-Type không hợp lệ
            inferred_type = infer_media_type_from_extension(media_url, content_type)
            if inferred_type:
                media_type = inferred_type
            else:
                client.sendMessage(
                    Message(text=f"⭕ URL không phải định dạng hợp lệ: Content-Type {content_type}"),
                    thread_id, thread_type, ttl=60000
                )
                return

    media_url = urllib.parse.unquote(media_url.replace("\\/", "/"))
    print(f"Debug: Media URL: {media_url}")

    # Kiểm tra độ nhạy cảm
    try:
        if media_type == 'image':
            result = check_image_sensitivity(media_url)
            if "error" in result:
                client.sendMessage(
                    Message(text=f"⭕ {result['error']}"),
                    thread_id, thread_type, ttl=60000
                )
                return
        else:
            # Trích xuất khung hình từ GIF, video hoặc WebP động
            frame_paths = extract_frames(media_url, media_type)
            if "error" in frame_paths:
                client.sendMessage(
                    Message(text=f"⭕ {frame_paths['error']}"),
                    thread_id, thread_type, ttl=60000
                )
                return

            # Kiểm tra từng khung hình
            results = []
            is_sensitive = False
            for i, frame_path in enumerate(frame_paths):
                frame_result = check_image_sensitivity(frame_path, is_url=False)
                if "error" in frame_result:
                    client.sendMessage(
                        Message(text=f"⭕ Lỗi khi kiểm tra khung hình {i+1}: {frame_result['error']}"),
                        thread_id, thread_type, ttl=60000
                    )
                    # Xóa file tạm trước khi thoát
                    for path in frame_paths:
                        if os.path.exists(path):
                            os.remove(path)
                    return
                results.append(f"Khung hình {i+1}: " + "\n- ".join(frame_result['report']))
                if frame_result['is_sensitive']:
                    is_sensitive = True
                # Xóa file tạm ngay sau khi xử lý
                if os.path.exists(frame_path):
                    os.remove(frame_path)

            result = {
                "is_sensitive": is_sensitive,
                "report": results
            }

        # Định dạng báo cáo dễ hiểu
        report_text = "\n".join(result['report'])
        media_display = media_type.replace('image', 'ảnh').replace('gif', 'gif').replace('video', 'video')
        if media_type == 'image' and (content_type == 'image/webp' or media_url.lower().endswith('.webp')):
            media_display = 'ảnh WebP'
        message_text = f"📊 Kết quả kiểm tra {media_display}:\n {report_text}"
        client.sendMessage(
            Message(text=message_text),
            thread_id, thread_type, ttl=60000
        )
        # Nếu nội dung nhạy cảm, gửi thêm cảnh báo
        if result['is_sensitive']:
            client.sendMessage(
                Message(text=f"⚠️ ❌❌❌Cảnh báo❌❌❌: {media_display.capitalize()} chứa nội dung nhạy cảm, có thể không phù hợp. Hãy cẩn thận khi sử dụng hoặc chia sẻ!"),
                thread_id, thread_type, ttl=60000
            )

    except Exception as e:
        client.sendMessage(
            Message(text=f"⭕ Lỗi khi kiểm tra độ nhạy cảm: {str(e)}"),
            thread_id, thread_type, ttl=60000
        )
        print(f"Debug: Exception: {e}")

# Cập nhật danh sách lệnh
def get_mitaizl():
    return {
        'checknude': handle_check_sensitivity_command  # Lệnh: checkimg
    }