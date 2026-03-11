import random
import os
import requests
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import time

des = {
    'tác giả': "Minh Vũ Shinn Cte (modified)",
    'mô tả': "Tải số lượng ảnh ngẫu nhiên tùy chỉnh từ file text chứa các link ảnh và lưu vào thư mục chỉ định dưới dạng PNG với kích thước gốc.",
    'tính năng': [
        "✅ Xác nhận khi lệnh được thực thi, cho phép tùy chỉnh số lượng ảnh (mặc định 10).",
        "🚀 Đọc file text chứa các link ảnh.",
        "🔗 Chọn ngẫu nhiên số lượng link ảnh từ file text theo yêu cầu.",
        "📷 Tải và lưu ảnh tĩnh dưới dạng PNG với kích thước gốc.",
        "🔄 Sử dụng ThreadPoolExecutor để tải ảnh đồng thời.",
        "📁 Lưu ảnh vào thư mục chỉ định, tự động tạo thư mục nếu chưa có.",
        "⚠️ Thông báo lỗi nếu tải ảnh thất bại hoặc định dạng không hỗ trợ."
    ],
    'hướng dẫn sử dụng': [
        "📌 Gọi hàm 'down1 [số lượng]' để tải số lượng ảnh ngẫu nhiên (ví dụ: 'down1 50').",
        "📌 Nếu không nhập số lượng, mặc định tải 10 ảnh.",
        "📎 Đường dẫn file text và thư mục lưu ảnh được cấu hình trong mã.",
        "📢 Kết quả và lỗi được ghi vào console."
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

def download_image(image_url, index, output_dir):
    """
    Tải ảnh từ URL và lưu vào thư mục chỉ định dưới dạng PNG, giữ nguyên kích thước gốc.
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
            print(f"WARNING: GIF không được hỗ trợ trong lệnh down1: {image_url}")
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

        # Tạo tên file duy nhất
        timestamp = int(time.time() * 1000)
        output_path = os.path.join(output_dir, f"image_{index+1}_{timestamp}.png")
        image.save(output_path, format='PNG', optimize=True, quality=85)

        file_size = os.path.getsize(output_path)
        print(f"Ảnh {index+1} từ URL: {image_url}")
        print(f"- Định dạng gốc: {content_type}")
        print(f"- Định dạng lưu: PNG")
        print(f"- Độ phân giải: {new_width}x{new_height} pixels")
        print(f"- Kích thước tệp: {file_size} bytes ({file_size / 1024:.2f} KB)")
        print(f"- Lưu tại: {output_path}")
        print("-" * 50)

        return {
            'path': output_path,
            'width': new_width,
            'height': new_height
        }
    except Exception as e:
        print(f"ERROR: Lỗi khi tải ảnh {index+1}: {str(e)}")
        return None

def down1(message=None, message_object=None, thread_id=None, thread_type=None, author_id=None, self=None):
    """
    Xử lý lệnh 'down1 [num]', tải số lượng ảnh ngẫu nhiên từ file girl1.txt và lưu vào thư mục images.
    Mặc định tải 10 ảnh nếu không chỉ định số lượng.
    """
    # Xử lý tham số số lượng ảnh từ message
    num_images = 10  # Mặc định tải 10 ảnh
    if message and message.strip():
        parts = message.split()
        if len(parts) > 1 and parts[1].isdigit():
            num_images = int(parts[1])
            if num_images <= 0:
                print("ERROR: Số lượng ảnh phải lớn hơn 0!")
                return
        elif len(parts) > 1:
            print("ERROR: Tham số số lượng phải là số nguyên dương!")
            return

    # Ghi log xác nhận lệnh
    print(f"INFO: Bắt đầu xử lý lệnh 'down1' với {num_images} ảnh")

    # Cấu hình file text và thư mục lưu ảnh
    txt_file = 'girl1.txt'
    output_dir = 'images'

    # Tạo thư mục lưu ảnh nếu chưa tồn tại
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"INFO: Đã tạo thư mục {output_dir}")

    # Đọc file text chứa các link ảnh
    if not os.path.exists(txt_file):
        print(f"ERROR: File {txt_file} không tồn tại!")
        return

    with open(txt_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Xử lý từng dòng, loại bỏ khoảng trắng và dòng trống
    image_links = [line.strip() for line in lines if line.strip()]
    if not image_links:
        print("ERROR: Không có link ảnh nào trong file girl1.txt!")
        return

    # Chọn ngẫu nhiên số lượng link ảnh theo yêu cầu
    num_images = min(num_images, len(image_links))
    selected_urls = random.sample(image_links, num_images)
    print(f"INFO: Đã chọn {num_images} link ảnh ngẫu nhiên")

    try:
        image_info_list = []
        with ThreadPoolExecutor(max_workers=min(num_images, 10)) as executor:
            futures = [executor.submit(download_image, url, i, output_dir) for i, url in enumerate(selected_urls)]
            results = [f.result() for f in futures]
            valid_results = [r for r in results if r]
            image_info_list.extend(valid_results)

        if not image_info_list:
            print("ERROR: Không tải được ảnh hợp lệ nào!")
            return

        if len(image_info_list) < num_images:
            print(f"WARNING: Chỉ tải được {len(image_info_list)} ảnh hợp lệ thay vì {num_images}")

        # Ghi log kết quả
        print(f"INFO: Hoàn tất xử lý lệnh down1, đã lưu {len(image_info_list)} ảnh vào {output_dir}")

    except Exception as e:
        print(f"ERROR: Đã xảy ra lỗi: {str(e)}")

def get_mitaizl():
    """
    Trả về dictionary chứa các lệnh được hỗ trợ.
    """
    return {
        'down1': down1
    }
