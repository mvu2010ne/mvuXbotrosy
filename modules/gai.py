from zlapi import ZaloAPI
from zlapi.models import *
import random
import os
import requests
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import tempfile
import time

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Gửi 10 ảnh ngẫu nhiên từ file text chứa các link ảnh, sử dụng sendMultiLocalImage để gửi ảnh tĩnh dưới dạng PNG với kích thước gốc.",
    'tính năng': [
        "✅ Gửi phản ứng xác nhận khi lệnh được nhập đúng.",
        "🚀 Đọc file text chứa các link ảnh.",
        "🔗 Chọn ngẫu nhiên 10 link ảnh từ file text.",
        "📷 Tải và gửi 10 ảnh tĩnh dưới dạng PNG sử dụng sendMultiLocalImage với kích thước gốc.",
        "🔄 Sử dụng ThreadPoolExecutor để tải ảnh đồng thời.",
        "🗑️ Tự động xóa file tạm sau khi gửi, ảnh tự xóa sau 60 giây.",
        "⚠️ Thông báo lỗi nếu tải ảnh thất bại hoặc định dạng không hỗ trợ."
    ],
    'hướng dẫn sử dụng': [
        "📌 Gửi lệnh `gai1` để nhận 10 ảnh ngẫu nhiên.",
        "📎 Bot sẽ tự động tìm kiếm, tải và gửi ảnh từ link trong file text.",
        "📢 Hệ thống sẽ gửi phản hồi khi hoàn thành hoặc gặp lỗi."
    ]
}

# Tạo session HTTP để tối ưu kết nối
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'image/jpeg,image/png,*/*;q=0.8',
    'Referer': 'https://example.com/'
})

def check_url(url):
    """
    Kiểm tra URL trước khi tải.
    """
    try:
        response = session.head(url, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def download_image(image_url, index):
    """
    Tải ảnh từ URL và lưu vào file tạm dưới dạng PNG, giữ nguyên kích thước gốc.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'image/jpeg,image/png,*/*;q=0.8',
        'Referer': 'https://example.com/'
    }

    try:
        if not check_url(image_url):
            print(f"ERROR: URL không hợp lệ: {image_url}")
            return None

        image_response = session.get(image_url, headers=headers, stream=True, timeout=30)
        image_response.raise_for_status()

        content_type = image_response.headers.get('Content-Type', '').lower()
        print(f"INFO: Đang tải ảnh {index+1} - Content-Type: {content_type}")

        if 'image/gif' in content_type:
            print(f"WARNING: GIF không được hỗ trợ trong lệnh gai1: {image_url}")
            return None

        suffix = '.png'
        image_data = BytesIO(image_response.content)
        image = Image.open(image_data)

        if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3] if image.mode == 'RGBA' else image.getchannel('A'))
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')

        orig_width, orig_height = image.size
        new_width, new_height = orig_width, orig_height  # Giữ nguyên kích thước gốc

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            image_path = tmp.name
            image.save(image_path, format='PNG', optimize=True, quality=85)

        file_size = os.path.getsize(image_path)
        print(f"Ảnh {index+1} từ URL: {image_url}")
        print(f"- Định dạng gốc: {content_type}")
        print(f"- Định dạng lưu: PNG")
        print(f"- Độ phân giải: {new_width}x{new_height} pixels")
        print(f"- Kích thước tệp: {file_size} bytes ({file_size / 1024:.2f} KB)")
        print("-" * 50)

        return {
            'path': image_path,
            'width': new_width,
            'height': new_height
        }
    except Exception as e:
        print(f"ERROR: Lỗi khi tải ảnh {index+1}: {str(e)}")
        return None

def anhgai1(message, message_object, thread_id, thread_type, author_id, self):
    """
    Xử lý lệnh 'gai1', gửi 10 ảnh ngẫu nhiên từ file girl1.txt dưới dạng PNG.
    """
    # Phản ứng ngay khi người dùng gửi lệnh
    self.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
    print(f"INFO: Bắt đầu xử lý lệnh 'gai1' từ {author_id} trong {thread_type}-{thread_id}")

    # Đọc file text chứa các link ảnh
    txt_file = 'girl1.txt'
    if not os.path.exists(txt_file):
        print(f"ERROR: File {txt_file} không tồn tại!")
        self.sendMessage(
            Message(text=f"❌ File {txt_file} không tồn tại!"),
            thread_id,
            thread_type,
            ttl=60000
        )
        return

    with open(txt_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Xử lý từng dòng, loại bỏ khoảng trắng và dòng trống
    image_links = [line.strip() for line in lines if line.strip()]
    if not image_links:
        print("ERROR: Không có link ảnh nào trong file girl1.txt!")
        self.sendMessage(
            Message(text="❌ Không có link ảnh nào trong file girl1.txt!"),
            thread_id,
            thread_type,
            ttl=60000
        )
        return

    # Chọn ngẫu nhiên tối đa 10 link ảnh
    num_images = min(10, len(image_links))
    selected_urls = random.sample(image_links, num_images)
    print(f"INFO: Đã chọn {num_images} link ảnh ngẫu nhiên")

    try:
        image_info_list = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(download_image, url, i) for i, url in enumerate(selected_urls)]
            results = [f.result() for f in futures]
            valid_results = [r for r in results if r]
            image_info_list.extend(valid_results)

        if not image_info_list:
            print("ERROR: Không tải được ảnh hợp lệ nào!")
            self.sendMessage(
                Message(text="❌ Không tải được ảnh hợp lệ nào!"),
                thread_id,
                thread_type,
                ttl=60000
            )
            return

        if len(image_info_list) < num_images:
            print(f"WARNING: Chỉ tải được {len(image_info_list)} ảnh hợp lệ thay vì {num_images}")
            self.sendMessage(
                Message(text=f"⚠️ Chỉ tải được {len(image_info_list)} ảnh hợp lệ thay vì {num_images}!"),
                thread_id,
                thread_type,
                ttl=60000
            )

        # Chuẩn bị danh sách đường dẫn ảnh để gửi
        image_paths = [info['path'] for info in image_info_list]

        # Gửi ảnh tĩnh với kích thước gốc
        try:
            valid_paths = []
            for path in image_paths:
                if os.path.exists(path) and os.path.getsize(path) > 0:
                    try:
                        with Image.open(path) as img:
                            img.verify()
                        valid_paths.append(path)
                    except Exception as e:
                        print(f"ERROR: Ảnh không hợp lệ {path}: {str(e)}")
                        continue
                else:
                    print(f"ERROR: File ảnh {path} không tồn tại hoặc rỗng")
                    continue

            if valid_paths:
                print(f"INFO: Gửi {len(valid_paths)} ảnh tĩnh dưới dạng PNG")
                result = self.sendMultiLocalImage(
                    imagePathList=valid_paths,
                    thread_id=thread_id,
                    thread_type=thread_type,
                    width=None,
                    height=None,
                    message=Message(text=f"📷 {len(valid_paths)} ảnh ngẫu nhiên"),
                    ttl=60000
                )
                print(f"DEBUG: Toàn bộ kết quả API: {result}")  # Dòng print mới chèn vào đây
                if hasattr(result, 'error_code') and result.error_code == 0:
                    print(f"INFO: Đã gửi {len(valid_paths)} ảnh tĩnh thành công")
                else:
                    print(f"ERROR: Không gửi được ảnh tĩnh: {getattr(result, 'error_message', 'Unknown error')}")
            else:
                print("ERROR: Không có ảnh tĩnh hợp lệ để gửi")
                self.sendMessage(
                    Message(text="❌ Không có ảnh tĩnh hợp lệ để gửi!"),
                    thread_id,
                    thread_type,
                    ttl=60000
                )
        except Exception as e:
            print(f"ERROR: Lỗi khi gửi ảnh tĩnh: {str(e)}")
            self.sendMessage(
                Message(text=f"❌ Lỗi khi gửi ảnh: {str(e)}"),
                thread_id,
                thread_type,
                ttl=60000
            )
        finally:
            for path in image_paths:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception as e:
                        print(f"ERROR: Lỗi khi xóa file tạm {path}: {str(e)}")

        print(f"INFO: Hoàn tất xử lý lệnh gai1, đã gửi {len(valid_paths)} ảnh")

    except Exception as e:
        print(f"ERROR: Đã xảy ra lỗi: {str(e)}")
        self.sendMessage(
            Message(text=f"❌ Đã xảy ra lỗi: {str(e)}"),
            thread_id,
            thread_type,
            ttl=60000
        )

def get_mitaizl():
    return {
        'gai': anhgai1
    }