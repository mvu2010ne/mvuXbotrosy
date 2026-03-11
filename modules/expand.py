import os
import requests
import json
import uuid
import time
import base64
from PIL import Image
import io
from zlapi.models import Message

# === CẤU HÌNH ===
CACHE_DIR = 'modules/cache'
os.makedirs(CACHE_DIR, exist_ok=True)
API_KEY = "sk-Pn6IAdtnVmu28a6X2Ut7LSe3D1AtXnwX-rNP3c-9khM"
EXPAND_API = "https://gemini.aiautotool.com/v1/images/expand"

print(f"[DEBUG] Khởi động expand module - API: {EXPAND_API}")

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Mở rộng ảnh ra ngoài khung (AI Outpainting / Image Expansion).",
    'tính năng': [
        "Reply ảnh + expand → mở rộng 1.5x cả 2 chiều",
        "Reply ảnh + expand 2 1.5 → ngang x2, dọc x1.5",
        "Gửi URL: expand <link> 2 1",
        "Tự động xử lý lỗi, cache ảnh"
    ],
    'hướng dẫn sử dụng': [
        "Reply ảnh → `expand`",
        "Reply ảnh → `expand 2 1.5`",
        "Hoặc: `expand https://...jpg 1.5 2`"
    ]
}

# === TẢI ẢNH TỪ URL ===
def download_image_from_url(url):
    print(f"[DEBUG] Tải ảnh: {url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        print(f"[DEBUG] HTTP: {response.status_code} | Type: {response.headers.get('Content-Type')}")
        if response.status_code == 200 and 'image' in response.headers.get('Content-Type', ''):
            size = len(response.content)
            print(f"[DEBUG] Tải thành công: {size} bytes")
            return response.content
        return None
    except Exception as e:
        print(f"[ERROR] Lỗi tải ảnh: {e}")
        return None


# === GỌI API MỞ RỘNG ẢNH ===
def expand_image(image_bytes, h_ratio=1.5, v_ratio=1.5, max_retries=2):
    h_ratio = max(1.0, float(h_ratio))
    v_ratio = max(1.0, float(v_ratio))
    for attempt in range(max_retries + 1):
        print(f"[DEBUG] Thử mở rộng (lần {attempt + 1}) | H: {h_ratio}x | V: {v_ratio}x")
        try:
            files = {'image': ('input.jpg', image_bytes, 'image/jpeg')}
            data = {
                'horizontal_expansion_ratio': str(h_ratio),
                'vertical_expansion_ratio': str(v_ratio),
                'response_format': 'b64_json'
            }
            headers = {'Authorization': f'Bearer {API_KEY}'}
            response = requests.post(EXPAND_API, headers=headers, data=data, files=files, timeout=90)
            print(f"[DEBUG] → Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                data_list = result.get('data', [])
                if data_list and 'b64_json' in data_list[0]:
                    b64_json = data_list[0]['b64_json']
                    image_data = base64.b64decode(b64_json)
                    output_path = os.path.join(CACHE_DIR, f"expand_{uuid.uuid4().hex}.jpg")
                    with open(output_path, "wb") as f:
                        f.write(image_data)
                    info = {
                        'model': result.get('model', 'picwish-image-expander'),
                        'provider': result.get('provider', 'picwish'),
                        'execution_time': result.get('execution_time', 0),
                        'original_size': result.get('original_size_bytes', len(image_bytes)),
                        'output_size': data_list[0].get('b64_json_length', 0),
                        'h_ratio': h_ratio,
                        'v_ratio': v_ratio
                    }
                    print(f"[SUCCESS] Mở rộng thành công")
                    return output_path, info
            else:
                print(f"[DEBUG] Lỗi {response.status_code}: {response.text[:200]}")
            time.sleep(3)
        except Exception as e:
            print(f"[ERROR] Lỗi mở rộng: {e}")
            time.sleep(3)
    print("[ERROR] Mở rộng thất bại sau các lần thử")
    return None, None


# === XỬ LÝ LỆNH `expand` (HOÀN CHỈNH) ===
def handle_expand_command(message, message_object, thread_id, thread_type, author_id, client):
    print(f"[DEBUG] Lệnh: {message}")
    image_bytes = None
    h_ratio = 1.5
    v_ratio = 1.5

    # === 1. REPLY ẢNH ===
    if hasattr(message_object, 'quote') and message_object.quote:
        attach = getattr(message_object.quote, 'attach', None)
        if attach:
            try:
                data = json.loads(attach)
                url = data.get('hdUrl') or data.get('href')
                if url:
                    image_bytes = download_image_from_url(url)
            except Exception as e:
                print(f"[ERROR] Parse attach: {e}")

        parts = message.strip().split()
        if len(parts) >= 3:
            try:
                h_ratio = float(parts[1])
                v_ratio = float(parts[2])
            except:
                client.replyMessage(Message(text="Tỷ lệ phải là số!\nVí dụ: expand 2 1.5"), message_object, thread_id, thread_type, ttl=10000)
                return
        elif len(parts) == 2:
            try:
                h_ratio = v_ratio = float(parts[1])
            except:
                client.replyMessage(Message(text="Tỷ lệ phải là số!"), message_object, thread_id, thread_type, ttl=10000)
                return

    # === 2. URL + TỶ LỆ ===
    else:
        parts = message.strip().split()
        if len(parts) < 4:
            client.replyMessage(Message(text="Dùng:\nexpand <URL> <ngang> <dọc>\nVí dụ: expand https://...jpg 2 1.5"), message_object, thread_id, thread_type, ttl=10000)
            return
        url_part = parts[1]
        if not url_part.startswith(("http://", "https://")):
            client.replyMessage(Message(text="URL không hợp lệ."), message_object, thread_id, thread_type)
            return
        try:
            h_ratio = float(parts[2])
            v_ratio = float(parts[3])
        except:
            client.replyMessage(Message(text="Tỷ lệ phải là số!"), message_object, thread_id, thread_type)
            return
        image_bytes = download_image_from_url(url_part)

    # === KIỂM TRA ẢNH ===
    if not image_bytes:
        client.replyMessage(Message(text="Không tải được ảnh."), message_object, thread_id, thread_type)
        return

    # === GỌI AI ===
    client.replyMessage(Message(text=f"Đang mở rộng ảnh...\nTỷ lệ: {h_ratio}x ngang, {v_ratio}x dọc"), message_object, thread_id, thread_type, ttl=20000)
    result_path, info = expand_image(image_bytes, h_ratio, v_ratio)

    if result_path and os.path.exists(result_path):
        try:
            # === LẤY KÍCH THƯỚC GỐC ===
            orig_img = Image.open(io.BytesIO(image_bytes))
            orig_width, orig_height = orig_img.size
            print(f"[INFO] Kích thước gốc: {orig_width}x{orig_height}")

            # === TÍNH KÍCH THƯỚC MỤC TIÊU ===
            target_width = int(orig_width * h_ratio)
            target_height = int(orig_height * v_ratio)
            print(f"[INFO] Kích thước mục tiêu: {target_width}x{target_height}")

            # === MỞ ẢNH KẾT QUẢ & RESIZE ===
            expanded_img = Image.open(result_path)
            if expanded_img.size != (target_width, target_height):
                print(f"[INFO] Resize từ {expanded_img.size} → {target_width}x{target_height}")
                expanded_img = expanded_img.resize((target_width, target_height), Image.LANCZOS)

            # === LƯU ẢNH CUỐI ===
            final_path = result_path.replace(".jpg", "_final.jpg")
            expanded_img.save(final_path, "JPEG", quality=95)
            real_width, real_height = target_width, target_height

            # === TẠO THÔNG TIN ===
            ratio_text = f"{h_ratio}x × {v_ratio}x" if h_ratio != v_ratio else f"{h_ratio}x"
            info_text = (
                f"Ảnh đã được mở rộng!\n"
                f"Tỷ lệ: {ratio_text}\n"
                f"Kích thước: {real_width}×{real_height} px\n"
                f"Model: {info['model']}\n"
                f"Thời gian: {info['execution_time']:.1f}s\n"
                f"Dung lượng: {info['original_size']//1024} KB → {info['output_size']//1024} KB"
            )

            msg = Message(text=info_text)

            # === GỬI ẢNH VỚI WIDTH & HEIGHT CHÍNH XÁC ===
            client.sendLocalImage(
                imagePath=final_path,
                message=msg,
                thread_id=thread_id,
                thread_type=thread_type,
                width=real_width,
                height=real_height,
                ttl=600000
            )

            # === DỌN DẸP ===
            time.sleep(2)
            for p in [result_path, final_path]:
                if os.path.exists(p):
                    os.remove(p)
                    print(f"[INFO] Đã xóa: {p}")

        except Exception as e:
            print(f"[ERROR] Xử lý ảnh cuối: {e}")
            client.replyMessage(Message(text="Lỗi xử lý ảnh."), message_object, thread_id, thread_type)
    else:
        client.replyMessage(Message(text="Mở rộng thất bại. Vui lòng thử lại sau."), message_object, thread_id, thread_type)


# === ĐĂNG KÝ LỆNH ===
def get_mitaizl():
    return {'expand': handle_expand_command}