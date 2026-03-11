import requests
import urllib.parse
import os
import json
from zlapi.models import Message
import mimetypes
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
from tqdm import tqdm
# Mô tả lệnh
des = {
    'tác giả': "Minh Vũ",
    'mô tả': "📤 Tải toàn bộ ảnh và video từ một thư mục lên Catbox và trả về danh sách link thành công/thất bại (tối ưu tốc độ).",
    'tính năng': [
        "📂 Quét toàn bộ file ảnh và video trong thư mục được chỉ định (hỗ trợ đường dẫn tương đối).",
        "📤 Tải file đồng thời lên Catbox để tăng tốc.",
        "📊 Chia kết quả thành 2 danh sách: thành công và thất bại.",
        "⚠️ Thông báo lỗi chi tiết nếu file không hợp lệ hoặc tải lên thất bại.",
        "📏 Giới hạn file dưới 200MB theo quy định của Catbox."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh upfoldertocatbox <đường_dẫn_thư_mục>.",
        "📌 Ví dụ: upfoldertocatbox vdsex",
        "✅ Nhận danh sách link thành công và thất bại."
    ]
}

# Khóa để đảm bảo thread-safe khi ghi danh sách
success_lock = threading.Lock()
failure_lock = threading.Lock()

# Hàm kiểm tra file có phải ảnh hoặc video và dưới 200MB
def is_valid_media_file(file_path):
    mime_type, _ = mimetypes.guess_type(file_path)
    file_size = os.path.getsize(file_path) / (1024 * 1024)  # Kích thước file tính bằng MB
    return (mime_type and 
            (mime_type.startswith('image/') or mime_type.startswith('video/')) and 
            file_size <= 200)

# Hàm tải file lên Catbox
def upload_to_catbox(file_path):
    file_name = os.path.basename(file_path)
    print(f"[UPLOAD] Trạng thái: Bắt đầu tải lên file {file_name}")
    
    try:
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # Kích thước file tính bằng MB
        if file_size > 200:
            print(f"[UPLOAD] Trạng thái: Thất bại - File {file_name} vượt quá giới hạn 200MB ({file_size:.2f}MB)")
            return file_path, None, "File vượt quá giới hạn 200MB của Catbox."
        
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = 'application/octet-stream'
        
        # Ghi lại thời gian bắt đầu
        start_time = time.time()
        
        # Mở file và chuẩn bị gửi theo từng khối
        with open(file_path, 'rb') as f:
            # Tạo thanh tiến trình với tqdm
            total_size = os.path.getsize(file_path)  # Kích thước file tính bằng byte
            chunk_size = 8192  # Kích thước mỗi khối (8KB)
            progress_bar = tqdm(total=total_size, unit='B', unit_scale=True, desc=file_name)
            
            # Chuẩn bị dữ liệu gửi lên
            files = {'fileToUpload': (file_name, f, mime_type)}
            data = {'reqtype': 'fileupload'}
            
            # Gửi yêu cầu với streaming
            response = requests.post(
                "https://catbox.moe/user/api.php",
                data=data,
                files=files,
                timeout=30
            )
            
            # Cập nhật thanh tiến trình (giả lập hoàn tất)
            progress_bar.n = total_size
            progress_bar.refresh()
            progress_bar.close()
            
            # Tính thời gian và tốc độ
            elapsed_time = time.time() - start_time
            speed = file_size / elapsed_time if elapsed_time > 0 else 0  # MB/s
            
            if response.status_code == 200:
                print(f"[UPLOAD] Trạng thái: Thành công - File {file_name} -> {response.text.strip()} (Tốc độ: {speed:.2f} MB/s)")
                return file_path, response.text.strip(), None
            print(f"[UPLOAD] Trạng thái: Thất bại - File {file_name}, mã lỗi: {response.status_code} (Tốc độ: {speed:.2f} MB/s)")
            return file_path, None, f"Tải lên thất bại, mã lỗi: {response.status_code}"
    except Exception as e:
        # Tính thời gian và tốc độ (nếu có lỗi)
        elapsed_time = time.time() - start_time if 'start_time' in locals() else 0
        speed = file_size / elapsed_time if elapsed_time > 0 else 0  # MB/s
        print(f"[UPLOAD] Trạng thái: Thất bại - File {file_name}, lỗi: {str(e)} (Tốc độ: {speed:.2f} MB/s)")
        return file_path, None, f"Lỗi: {str(e)}"

# Hàm xử lý lệnh tải thư mục lên Catbox
# Hàm xử lý lệnh tải thư mục lên Catbox
def handle_uploadfolder_command(message, message_object, thread_id, thread_type, author_id, client):
    # Lấy đường dẫn thư mục từ tin nhắn
    print(f"[DEBUG] Tin nhắn gốc: {message}")
    
    # Tách lệnh và đường dẫn
    parts = message.strip().split(maxsplit=1)  # Tách thành [lệnh, đường dẫn]
    if len(parts) < 2 or not parts[0].lower().startswith('up.foder'):
        client.sendMessage(Message(text="Cú pháp không hợp lệ. Vui lòng sử dụng: up.foder <đường_dẫn_thư_mục>. Ví dụ: up.foder vdsex"),
                           thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return
    
    folder_path = parts[1].strip()  # Lấy phần đường dẫn
    print(f"[DEBUG] Đường dẫn sau khi tách: {folder_path}")

    if not folder_path:
        client.sendMessage(Message(text="Vui lòng cung cấp đường dẫn thư mục. Ví dụ: up.foder vdsex"),
                           thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    # Gửi thông báo xác nhận
    client.sendMessage(Message(text=f"Đã nhận lệnh upload thư mục: {folder_path}"),
                       thread_id=thread_id, thread_type=thread_type, ttl=60000)

    # Xác định thư mục gốc của dự án
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)  # Lên một cấp từ modules đến ngan
    print(f"[DEBUG] Thư mục chứa tập lệnh: {script_dir}")
    print(f"[DEBUG] Thư mục dự án: {project_dir}")

    # Chuyển đường dẫn tương đối thành đường dẫn tuyệt đối
    try:
        absolute_path = os.path.abspath(os.path.join(project_dir, folder_path))
        print(f"[DEBUG] Đường dẫn tuyệt đối: {absolute_path}")
    except Exception as e:
        print(f"[DEBUG] Lỗi khi xử lý đường dẫn: {str(e)}")
        client.sendMessage(Message(text=f"Lỗi khi xử lý đường dẫn: {str(e)}"),
                           thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    # Kiểm tra thư mục tồn tại
    if not os.path.exists(absolute_path) or not os.path.isdir(absolute_path):
        client.sendMessage(Message(text=f"Thư mục không tồn tại hoặc không hợp lệ: {absolute_path}"),
                           thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    # Quét thư mục để lấy danh sách file
    media_files = [
        os.path.join(root, file)
        for root, _, files in os.walk(absolute_path)
        for file in files
        if is_valid_media_file(os.path.join(root, file))
    ]
    print(f"[DEBUG] Số file media tìm thấy: {len(media_files)}")

    if not media_files:
        client.sendMessage(Message(text="Không tìm thấy ảnh hoặc video hợp lệ (dưới 200MB) trong thư mục."),
                           thread_id=thread_id, thread_type=thread_type, ttl=60000)
        return

    # Tải file đồng thời bằng ThreadPoolExecutor
    success_list = []
    failure_list = []
    max_workers = min(5, len(media_files))  # Giới hạn tối đa 5 luồng

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {executor.submit(upload_to_catbox, file_path): file_path for file_path in media_files}
        for future in as_completed(future_to_file):
            file_path, link, error = future.result()
            file_name = os.path.basename(file_path)
            if link:
                with success_lock:
                    success_list.append(f"{link}")
            else:
                with failure_lock:
                    failure_list.append(f"{file_name}: {error}")

    # Sắp xếp danh sách
    success_list.sort()
    failure_list.sort()

    # Tạo phản hồi
    response_parts = []
    max_message_length = 2000

    # Danh sách 1: Thành công
    success_text = "Danh sách 1\n"
    success_text += f"Media thành công ({len(success_list)} link):\n"
    if success_list:
        success_text += "\n".join(success_list) + "\n"
    else:
        success_text += "Không có file nào tải lên thành công.\n"
    
    # Danh sách 2: Thất bại
    failure_text = "\nDanh sách 2\n"
    failure_text += f"Media thất bại ({len(failure_list)} link):\n"
    if failure_list:
        failure_text += "\n".join(failure_list)
    else:
        failure_text += "Không có file nào thất bại."

    # Kết hợp và chia nhỏ phản hồi
    response_text = success_text + failure_text
    while response_text:
        if len(response_text) <= max_message_length:
            response_parts.append(response_text)
            break
        split_index = response_text.rfind('\n', 0, max_message_length)
        if split_index == -1:
            split_index = max_message_length
        response_parts.append(response_text[:split_index])
        response_text = response_text[split_index:].lstrip()

    # Gửi phản hồi
    for i, part in enumerate(response_parts, 1):
        client.sendMessage(Message(text=f"{part}"),
                           thread_id=thread_id, thread_type=thread_type)
        print(f"[DEBUG] Đã gửi phần {i}/{len(response_parts)} của phản hồi")

# Định nghĩa lệnh
def get_mitaizl():
    return {
        'up.foder': handle_uploadfolder_command
    }