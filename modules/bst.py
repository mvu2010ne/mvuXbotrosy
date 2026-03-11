import time
from zlapi import ZaloAPI
from zlapi.models import *
import random
import requests
from io import BytesIO
import os
import json
from urllib.parse import urlparse
from PIL import Image
import concurrent.futures
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Gửi nhiều ảnh từ bộ sưu tập, tạo hoặc xóa bộ sưu tập.",
    'tính năng': [
        "📷 Gửi tối đa 10 ảnh ngẫu nhiên từ bộ sưu tập được chọn.",
        "📋 Hiển thị danh sách bộ sưu tập khi không chỉ định tên.",
        "🆕 Tạo/cập nhật bộ sưu tập mới với lệnh addbst (chỉ admin).",
        "🗑️ Xóa bộ sưu tập với lệnh delbst (chỉ admin).",
        "⏳ Áp dụng thời gian chờ 3 phút cho người dùng không phải admin.",
        "⚠️ Thông báo lỗi nếu bộ sưu tập không tồn tại hoặc tải ảnh thất bại."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh bst <tên_bộ_sưu_tập> để nhận ảnh.",
        "📌 Ví dụ: bst blackstocking.",
        "📩 Gửi bst để xem danh sách bộ sưu tập.",
        "📩 [Admin] Gửi addbst <tên> | <mô tả> | <link1> <link2>... để tạo/cập nhật.",
        "📩 [Admin] Gửi delbst <tên_bộ_sưu_tập> để xóa bộ sưu tập.",
        "✅ Nhận ảnh hoặc thông báo trạng thái ngay lập tức."
    ]
}

# Danh sách ID admin (thay bằng ID thực tế của admin)
ADMIN_IDS = ["3299675674241805615"]  # Thay bằng ID thật của bạn

# Dictionary lưu thời gian sử dụng lệnh cuối cùng của từng người dùng
COOLDOWN_TRACKER = {}
COOLDOWN_TIME = 180  # 3 phút = 180 giây

# Đọc bộ sưu tập từ tệp JSON
def load_collections():
    try:
        with open('collections.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Tệp collections.json không tồn tại! Tạo tệp mới.")
        with open('collections.json', 'w', encoding='utf-8') as f:
            json.dump({}, f)
        return {}
    except json.JSONDecodeError:
        print("Lỗi khi đọc tệp collections.json!")
        return {}

# Ghi bộ sưu tập vào tệp JSON
def save_collections(collections):
    try:
        with open('collections.json', 'w', encoding='utf-8') as f:
            json.dump(collections, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Lỗi khi ghi tệp collections.json: {str(e)}")
        return False

COLLECTIONS = load_collections()

# Cấu hình retry cho requests
def create_session_with_retries():
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# Hàm kiểm tra URL trước khi tải
def check_url(url, session, headers):
    try:
        response = session.head(url, headers=headers, timeout=5, allow_redirects=True)
        if response.status_code == 200:
            return True
        else:
            print(f"URL không khả dụng: {url} (Status code: {response.status_code})")
            return False
    except Exception as e:
        print(f"Lỗi kiểm tra URL {url}: {str(e)}")
        return False

# Hàm tải ảnh từ URL và lưu dưới dạng PNG
def download_image(url, index, collection_name, session, headers):
    try:
        # Kiểm tra URL trước khi tải
        if not check_url(url, session, headers):
            return None

        response = session.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            image_data = BytesIO(response.content)
            
            # Mở ảnh bằng Pillow
            image = Image.open(image_data)
            
            # Chuyển đổi ảnh sang định dạng RGB nếu cần (tránh lỗi với ảnh có alpha channel)
            if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[3] if image.mode == 'RGBA' else image.getchannel('A'))
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            temp_image_path = f"temp_{collection_name}_{index}.png"
            
            # Lưu ảnh dưới dạng PNG để bảo toàn chất lượng
            image.save(temp_image_path, format='PNG')
            
            # Lấy thông tin chất lượng ảnh
            width, height = image.size
            format = image.format if image.format else 'UNKNOWN'
            file_size = os.path.getsize(temp_image_path)

            # In thông tin chất lượng ảnh
            print(f"Ảnh {index+1} từ URL: {url}")
            print(f"- Định dạng gốc: {format}")
            print(f"- Định dạng lưu: PNG")
            print(f"- Độ phân giải: {width}x{height} pixels")
            print(f"- Kích thước tệp: {file_size} bytes ({file_size / 1024:.2f} KB)")
            print("-" * 50)

            return temp_image_path
        else:
            print(f"Lỗi tải ảnh từ URL {url}: Status code {response.status_code}")
            return None
    except Exception as e:
        print(f"Lỗi tải ảnh từ URL {url}: {str(e)}")
        return None

# Hàm kiểm tra link trùng lặp trong toàn bộ bộ sưu tập
def check_duplicate_links(new_links, exclude_collection=None):
    all_links = []
    for collection_name, data in COLLECTIONS.items():
        if collection_name != exclude_collection:
            all_links.extend(data['links'])
    return [link for link in new_links if link in all_links]

# Hàm xử lý lệnh thêm bộ sưu tập mới
def add_collection(message, message_object, thread_id, thread_type, author_id, self):
    if author_id not in ADMIN_IDS:
        self.sendMessage(Message(text="❌ Chỉ admin mới có thể sử dụng lệnh này!"), thread_id, thread_type)
        return

    action = "✅"
    self.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    try:
        parts = message.split("|", 2)
        if len(parts) < 3:
            self.sendMessage(Message(text="❌ Vui lòng cung cấp đầy đủ: `addbst <tên_bộ_sưu_tập> | <mô_tả> | <link1> <link2> ...`"), thread_id, thread_type)
            return

        collection_name = parts[0].replace("addbst", "").strip().lower()
        description = parts[1].strip()
        links = [link.strip() for link in parts[2].split() if link.strip() and link.startswith('https://')]

        if not collection_name:
            self.sendMessage(Message(text="❌ Tên bộ sưu tập không được để trống!"), thread_id, thread_type)
            return

        if not links:
            self.sendMessage(Message(text="❌ Danh sách link không hợp lệ! Phải có ít nhất một link bắt đầu bằng https://"), thread_id, thread_type)
            return

        # Kiểm tra link trùng lặp với các bộ sưu tập khác
        duplicate_links = check_duplicate_links(links, exclude_collection=collection_name)
        if duplicate_links:
            self.sendMessage(
                Message(text=f"⚠️ Các link sau đã tồn tại trong bộ sưu tập khác: {', '.join(duplicate_links)}"),
                thread_id,
                thread_type
            )
            # Chỉ giữ lại các link không trùng
            links = [link for link in links if link not in duplicate_links]
            if not links:
                self.sendMessage(Message(text="❌ Không còn link hợp lệ để thêm sau khi loại bỏ trùng lặp!"), thread_id, thread_type)
                return

        global COLLECTIONS
        if collection_name in COLLECTIONS:
            # Thêm link mới và loại bỏ trùng lặp trong cùng bộ sưu tập
            COLLECTIONS[collection_name]['description'] = description
            COLLECTIONS[collection_name]['links'].extend(links)
            COLLECTIONS[collection_name]['links'] = list(set(COLLECTIONS[collection_name]['links']))
            action = "cập nhật"
        else:
            # Tạo bộ sưu tập mới
            COLLECTIONS[collection_name] = {
                'description': description,
                'links': links
            }
            action = "tạo mới"

        if save_collections(COLLECTIONS):
            self.sendMessage(
                Message(text=f"✅ Bộ sưu tập '{collection_name}' đã được {action} với {len(links)} link!"),
                thread_id,
                thread_type
            )
        else:
            self.sendMessage(Message(text="❌ Lỗi khi lưu bộ sưu tập vào tệp JSON!"), thread_id, thread_type)

    except Exception as e:
        self.sendMessage(Message(text=f"❌ Lỗi khi xử lý lệnh: {str(e)}"), thread_id, thread_type)

# Hàm xử lý lệnh xóa bộ sưu tập
def delete_collection(message, message_object, thread_id, thread_type, author_id, self):
    if author_id not in ADMIN_IDS:
        self.sendMessage(Message(text="❌ Chỉ admin mới có thể sử dụng lệnh này!"), thread_id, thread_type)
        return

    action = "✅"
    self.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    try:
        parts = message.split(" ", 1)
        collection_name = parts[1].strip().lower() if len(parts) > 1 else None

        if not collection_name:
            self.sendMessage(Message(text="❌ Vui lòng cung cấp tên bộ sưu tập! Ví dụ: delbst blackstocking"), thread_id, thread_type)
            return

        global COLLECTIONS
        if collection_name not in COLLECTIONS:
            self.sendMessage(Message(text=f"❌ Bộ sưu tập '{collection_name}' không tồn tại!"), thread_id, thread_type)
            return

        # Xóa bộ sưu tập
        del COLLECTIONS[collection_name]

        if save_collections(COLLECTIONS):
            self.sendMessage(
                Message(text=f"✅ Bộ sưu tập '{collection_name}' đã được xóa thành công!"),
                thread_id,
                thread_type
            )
        else:
            self.sendMessage(Message(text="❌ Lỗi khi lưu bộ sưu tập vào tệp JSON!"), thread_id, thread_type)

    except Exception as e:
        self.sendMessage(Message(text=f"❌ Lỗi khi xử lý lệnh: {str(e)}"), thread_id, thread_type)

# Hàm xử lý lệnh gửi nhiều ảnh theo bộ sưu tập
# Hàm xử lý lệnh gửi nhiều ảnh theo bộ sưu tập
def send_collection_image(message, message_object, thread_id, thread_type, author_id, self):
    action = "✅"
    self.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    try:
        parts = message.split(" ", 1)
        collection_input = parts[1].strip().lower() if len(parts) > 1 else None

        # Nếu không cung cấp tham số, hiển thị danh sách bộ sưu tập với số thứ tự
        if not collection_input:
            header = "❌ Vui lòng cung cấp tên bộ sưu tập hoặc số thứ tự! Ví dụ: bst blackstocking hoặc bst 1\nDanh sách bộ sưu tập hiện có:\n"
            example_text = "bst blackstocking hoặc bst 1"
            example_offset = header.find(example_text)
            example_length = len(example_text)

            # Sắp xếp các bộ sưu tập theo thứ tự từ A đến Z và đánh số
            sorted_collections = sorted(COLLECTIONS.items(), key=lambda x: x[0])
            collection_lines = [
                f"[ {i+1} ] {key} - {value['description']} ({len(value['links'])} ảnh)"
                for i, (key, value) in enumerate(sorted_collections)
            ]
            MAX_CHARS = 500
            messages_to_send = []
            current_message = header
            current_styles = [
                MessageStyle(
                    offset=example_offset,
                    length=example_length,
                    style="color",
                    color="#15a85f",
                    auto_format=False
                ),
                MessageStyle(
                    offset=example_offset,
                    length=example_length,
                    style="font",
                    size="16",
                    auto_format=False
                )
            ]
            current_offset = len(header)
            is_first_message = True

            for line in collection_lines:
                # Tách số thứ tự, tên và mô tả
                number = line.split("]")[0] + "]"  # e.g., "[ 1 ]"
                name_and_desc = line[len(number) + 1:].split(" - ")  # e.g., ["1122", "Ảnh nude Hàn Quốc (31 ảnh)"]
                name = name_and_desc[0]  # e.g., "1122"
                description = name_and_desc[1] if len(name_and_desc) > 1 else ""  # e.g., "Ảnh nude Hàn Quốc (31 ảnh)"
                
                number_length = len(number)
                name_length = len(name)
                description_length = len(description)

                if len(current_message) + len(line) + 1 > MAX_CHARS:
                    style_text = MultiMsgStyle(current_styles)
                    messages_to_send.append((current_message, style_text))
                    current_message = "" if not is_first_message else ""
                    current_styles = []
                    current_offset = len(current_message)
                    is_first_message = False

                current_message += line + "\n"
                # Định dạng số thứ tự (màu đỏ #db342e, font size 3)
                current_styles.append(MessageStyle(
                    offset=current_offset,
                    length=number_length,
                    style="color",
                    color="#db342e",  # Màu đỏ cho [ 1 ]
                    auto_format=False
                ))
                current_styles.append(MessageStyle(
                    offset=current_offset,
                    length=number_length,
                    style="font",
                    size="3",
                    auto_format=False
                ))
                # Định dạng tên bộ sưu tập (màu xanh #15a85f, font size 3)
                name_offset = current_offset + number_length + 1
                current_styles.append(MessageStyle(
                    offset=name_offset,
                    length=name_length,
                    style="color",
                    color="#15a85f",  # Màu xanh cho 1122
                    auto_format=False
                ))
                current_styles.append(MessageStyle(
                    offset=name_offset,
                    length=name_length,
                    style="font",
                    size="3",
                    auto_format=False
                ))
                # Định dạng mô tả (màu đen #000000, font size 3)
                description_offset = name_offset + name_length + 3  # +3 để bỏ qua " - "
                current_styles.append(MessageStyle(
                    offset=description_offset,
                    length=description_length,
                    style="color",
                    color="#000000",  # Màu đen cho mô tả
                    auto_format=False
                ))
                current_styles.append(MessageStyle(
                    offset=description_offset,
                    length=description_length,
                    style="font",
                    size="3",
                    auto_format=False
                ))
                current_offset += len(line) + 1

            if current_message:
                style_text = MultiMsgStyle(current_styles)
                messages_to_send.append((current_message, style_text))

            # Gửi tin nhắn với thời gian trễ 1 giây giữa các tin nhắn
            for i, (text, style) in enumerate(messages_to_send):
                self.sendMessage(
                    Message(text=text.rstrip(), style=style),
                    thread_id,
                    thread_type,
                    ttl=120000
                )
                # Thêm thời gian trễ 1 giây, trừ tin nhắn cuối cùng
                if i < len(messages_to_send) - 1:
                    time.sleep(1)
            return

        # Kiểm tra xem đầu vào là số thứ tự hay tên bộ sưu tập
        collection_name = None
        sorted_collections = sorted(COLLECTIONS.items(), key=lambda x: x[0])
        if collection_input.isdigit():
            index = int(collection_input) - 1
            if 0 <= index < len(sorted_collections):
                collection_name = sorted_collections[index][0]
            else:
                self.sendMessage(
                    Message(text=f"❌ Số thứ tự '{collection_input}' không hợp lệ! Vui lòng chọn từ 1 đến {len(sorted_collections)}."),
                    thread_id,
                    thread_type,
                    ttl=60000
                )
                return
        else:
            collection_name = collection_input

    except IndexError:
        self.sendMessage(Message(text="❌ Lệnh không hợp lệ! Vui lòng dùng: bst <tên_bộ_sưu_tập> hoặc bst <số_thứ_tự>"), thread_id, thread_type, ttl=60000)
        return

    current_time = time.time()
    if author_id not in ADMIN_IDS:
        last_used = COOLDOWN_TRACKER.get(author_id, 0)
        time_since_last = current_time - last_used
        if time_since_last < COOLDOWN_TIME:
            remaining_time = int(COOLDOWN_TIME - time_since_last)
            self.sendMessage(
                Message(text=f"⏳ Vui lòng đợi {remaining_time} giây nữa để gửi ảnh tiếp theo!"),
                thread_id,
                thread_type,
                ttl=30000
            )
            return

    if collection_name not in COLLECTIONS:
        self.sendMessage(
            Message(text=f"❌ Bộ sưu tập '{collection_name}' không tồn tại! Các bộ sưu tập hiện có: {', '.join(sorted(COLLECTIONS.keys()))}"),
            thread_id,
            thread_type,
            ttl=60000
        )
        return

    image_links = COLLECTIONS[collection_name]['links']
    if not image_links:
        self.sendMessage(Message(text=f"❌ Bộ sưu tập '{collection_name}' không có ảnh nào!"), thread_id, thread_type, ttl=30000)
        return

    max_images = min(10, len(image_links))
    selected_links = random.sample(image_links, max_images)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }

    session = create_session_with_retries()

    image_paths = []
    failed_urls = []
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_url = {
                executor.submit(download_image, url, i, collection_name, session, headers): url
                for i, url in enumerate(selected_links)
            }
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                temp_image_path = future.result()
                if temp_image_path:
                    image_paths.append(temp_image_path)
                else:
                    failed_urls.append(url)

        if not image_paths:
            self.sendMessage(Message(text="❌ Không thể tải bất kỳ ảnh nào từ bộ sưu tập!"), thread_id, thread_type)
            if failed_urls:
                self.sendMessage(Message(text=f"📌 Các URL không tải được: {', '.join(failed_urls)}"), thread_id, thread_type)
            return

        self.sendMultiLocalImage(
            imagePathList=image_paths,
            thread_id=thread_id,
            thread_type=thread_type,
            width=None,
            height=None,
            message=Message(text=f"📷 Bộ sưu tập '{collection_name}' ({len(image_paths)} ảnh)"),
            ttl=60000
        )

        if failed_urls:
            self.sendMessage(Message(text=f"⚠️ Một số ảnh không tải được: {', '.join(failed_urls)}"), thread_id, thread_type)

        COOLDOWN_TRACKER[author_id] = time.time()

    except Exception as e:
        self.sendMessage(Message(text=f"❌ Đã xảy ra lỗi khi gửi ảnh: {str(e)}"), thread_id, thread_type)

    finally:
        for path in image_paths:
            if os.path.exists(path):
                os.remove(path)

# Hàm xử lý lệnh cập nhật tên và mô tả bộ sưu tập
def fix_collection(message, message_object, thread_id, thread_type, author_id, self):
    if author_id not in ADMIN_IDS:
        self.sendMessage(Message(text="❌ Chỉ admin mới có thể sử dụng lệnh này!"), thread_id, thread_type)
        return

    action = "✅"
    self.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    try:
        # Tách phần lệnh và danh sách bộ sưu tập
        parts = message.split("|", 1)
        if len(parts) < 2:
            self.sendMessage(
                Message(text="❌ Vui lòng cung cấp danh sách bộ sưu tập! Ví dụ: `fix | 1122 - Ảnh nude Hàn Quốc\n9940 - XiuRen No.9940 尹菲`"),
                thread_id,
                thread_type,
                ttl=30000
            )
            return

        # Lấy danh sách bộ sưu tập từ phần sau dấu |
        collection_list = parts[1].strip().split("\n")
        if not collection_list:
            self.sendMessage(Message(text="❌ Danh sách bộ sưu tập trống!"), thread_id, thread_type)
            return

        global COLLECTIONS
        updated_collections = []
        not_found_collections = []
        invalid_format = []

        # Xử lý từng dòng trong danh sách
        for line in collection_list:
            line = line.strip()
            if not line:
                continue

            # Tách tên và mô tả
            try:
                collection_name, description = [part.strip() for part in line.split(" - ", 1)]
                collection_name = collection_name.lower()
            except ValueError:
                invalid_format.append(line)
                continue

            # Kiểm tra xem bộ sưu tập có tồn tại không
            if collection_name in COLLECTIONS:
                # Lưu tên cũ để kiểm tra xem có đổi tên không
                old_name = collection_name
                # Cập nhật mô tả
                COLLECTIONS[collection_name]['description'] = description
                updated_collections.append(collection_name)
            else:
                not_found_collections.append(collection_name)

        # Lưu thay đổi vào tệp JSON
        if save_collections(COLLECTIONS):
            response = "✅ Cập nhật thành công các bộ sưu tập:\n" + "\n".join(
                f"- {name}" for name in updated_collections
            )
            if not_found_collections:
                response += "\n\n⚠️ Không tìm thấy các bộ sưu tập:\n" + "\n".join(
                    f"- {name}" for name in not_found_collections
                )
            if invalid_format:
                response += "\n\n❌ Định dạng không hợp lệ:\n" + "\n".join(
                    f"- {line}" for line in invalid_format
                )
            self.sendMessage(Message(text=response), thread_id, thread_type)
        else:
            self.sendMessage(Message(text="❌ Lỗi khi lưu bộ sưu tập vào tệp JSON!"), thread_id, thread_type)

    except Exception as e:
        self.sendMessage(Message(text=f"❌ Lỗi khi xử lý lệnh: {str(e)}"), thread_id, thread_type)

# Hàm trả về lệnh
def get_mitaizl():
    return {
        'bst': send_collection_image,
        'addbst': add_collection,
        'delbst': delete_collection,
        'fix': fix_collection  # Thêm lệnh fix
    }