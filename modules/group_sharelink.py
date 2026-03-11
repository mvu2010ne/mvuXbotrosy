import re
import json
import threading
import time
import requests
from io import BytesIO
from zlapi.models import Message, ThreadType
from PIL import Image

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Lấy link mời của nhóm Zalo hiện tại và gửi đến tất cả các nhóm khác, trừ các nhóm trong danh sách loại trừ.",
    'tính năng': [
        "🔗 Tự động lấy link mời của nhóm hiện tại khi nhập lệnh.",
        "📷 Sử dụng ảnh mặc định làm ảnh nền, nếu lỗi thì dùng avatar nhóm.",
        "📋 Tạo tiêu đề từ tên nhóm và mô tả mặc định.",
        "📨 Gửi liên kết đến tất cả nhóm, trừ các nhóm trong danh sách loại trừ (từ file JSON).",
        "🔒 Kiểm tra quyền admin trước khi thực hiện lệnh.",
        "⏳ Gửi tin nhắn với khoảng cách thời gian cố định giữa các lần gửi.",
        "🔍 Kiểm tra định dạng URL và xử lý các lỗi liên quan."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh `group.sharelink` trong nhóm để lấy link mời và gửi đến tất cả các nhóm khác.",
        "📌 Không cần tham số, bot tự động lấy thông tin nhóm (link, avatar, tên).",
        "✅ Nhận thông báo trạng thái và kết quả gửi tin nhắn ngay lập tức."
    ]
}

# Danh sách admin
ADMIN_IDS = {"3299675674241805615", "1632905559702714318"}

# URL ảnh mặc định
DEFAULT_IMAGE_URL = "https://f59-zpg-r.zdn.vn/jpg/8605264667460368029/51d6589f0c98bac6e389.jpg"

# Regex kiểm tra URL
url_pattern = re.compile(
    r'http[s]?://(?:[a-zA-Z0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
)


def get_excluded_group_ids(filename="danhsachnhom.json"):
    """Đọc tệp JSON và trả về tập hợp các group_id cần loại trừ."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            groups = json.load(f)
            # Kiểm tra xem groups có phải là danh sách không
            if not isinstance(groups, list):
                print(f"Lỗi: Nội dung file {filename} không phải là danh sách.")
                return set()
            # Trả về tập hợp các group_id
            return {grp.get("group_id") for grp in groups if isinstance(grp, dict) and "group_id" in grp}
    except FileNotFoundError:
        print(f"Lỗi: File {filename} không tồn tại.")
        return set()
    except json.JSONDecodeError:
        print(f"Lỗi: File {filename} có định dạng JSON không hợp lệ.")
        return set()
    except PermissionError:
        print(f"Lỗi: Không có quyền đọc file {filename}.")
        return set()
    except Exception as e:
        print(f"Lỗi không xác định khi đọc file {filename}: {e}")
        return set()

def send_link_to_group(client, link_url, thumbnail_url, title, domain_url, desc, thread_id):
    """Gửi một liên kết có hình ảnh đến một nhóm cụ thể."""
    try:
        client.sendLink(
            linkUrl=link_url,
            title=title,
            thread_id=thread_id,
            thread_type=ThreadType.GROUP,
            domainUrl=domain_url,
            desc=desc,
            thumbnailUrl=thumbnail_url,
            ttl=600000
        )
        print(f"Đã gửi link đến nhóm {thread_id}")
    except Exception as e:
        print(f"Lỗi khi gửi link đến nhóm {thread_id}: {e}")

def start_sharelink(client, link_url, thumbnail_url, title, domain_url, desc, thread_id, thread_type):
    """Gửi link đến tất cả nhóm không nằm trong danh sách loại trừ, trừ nhóm hiện tại."""
    try:
        excluded_group_ids = get_excluded_group_ids()
        excluded_group_ids.add(thread_id)  # Loại trừ nhóm hiện tại
        all_groups = client.fetchAllGroups()
        allowed_thread_ids = [gid for gid in all_groups.gridVerMap.keys() if gid not in excluded_group_ids]
        print(f"Đang gửi link đến {len(allowed_thread_ids)} nhóm (đã loại trừ các nhóm không cho phép).")

        for group_id in allowed_thread_ids:
            try:
                send_link_to_group(client, link_url, thumbnail_url, title, domain_url, desc, group_id)
                time.sleep(3)  # Độ trễ 3 giây giữa các lần gửi
            except Exception as e:
                print(f"Lỗi khi gửi link đến nhóm {group_id}: {e}")

        # Thông báo hoàn thành
        client.sendMessage(
            Message(text="✅ Hoàn thành gửi link mời nhóm đến tất cả nhóm!"),
            thread_id,
            thread_type,
            ttl=300000
        )
        print("Đã hoàn thành gửi link đến tất cả nhóm.")
    except Exception as e:
        client.sendMessage(
            Message(text=f"🚫 Lỗi khi gửi link: {e}"),
            thread_id,
            thread_type,
            ttl=300000
        )
        print(f"Lỗi trong quá trình gửi link: {e}")

def load_image(url, default_color=(200,200,200)):
    """Tải ảnh từ URL, trả về URL nếu hợp lệ, nếu không trả về None."""
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        Image.open(BytesIO(r.content)).convert("RGBA")  # Kiểm tra xem có phải ảnh hợp lệ
        return url
    except Exception:
        print(f"Lỗi khi tải ảnh từ {url}")
        return None

def handle_groupsharelink_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh group.sharelink để lấy link mời nhóm hiện tại và gửi đến tất cả nhóm."""
    print(f"[START] Xử lý command group.sharelink từ author_id: {author_id} trong thread: {thread_id}")

    # Kiểm tra quyền admin
    if author_id not in ADMIN_IDS:
        client.sendMessage(
            Message(text="🚫 Bạn không có quyền sử dụng lệnh này!"),
            thread_id,
            thread_type,
            ttl=30000
        )
        print("Quyền hạn không đủ. Dừng command.")
        return

    # Thêm phản ứng
    try:
        client.sendReaction(message_object, "⚡", thread_id, thread_type, reactionType=75)
        print("Đã thêm phản ứng ngay khi nhận lệnh.")
    except Exception as e:
        print(f"Lỗi khi thêm phản ứng: {e}")

    # Lấy thông tin nhóm
    try:
        group = client.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
        group_name = group.name

        # Thử tải ảnh mặc định trước
        thumbnail_url = load_image(DEFAULT_IMAGE_URL)
        
        # Nếu ảnh mặc định không tải được, dùng avatar nhóm
        if not thumbnail_url:
            thumbnail_url = load_image(group.avt) if group.avt else None
            if not thumbnail_url:
                client.sendMessage(
                    Message(text="🚫 Không thể tải ảnh mặc định hoặc avatar nhóm để làm ảnh nền!"),
                    thread_id,
                    thread_type,
                    ttl=30000
                )
                print("Không thể tải ảnh mặc định hoặc avatar nhóm. Dừng command.")
                return

        # Lấy link mời nhóm
        group_link = client.getGroupLink(chatID=thread_id)
        print("Dữ liệu từ Zalo API:", group_link)
        if group_link.get("error_code") == 0:
            data = group_link.get("data")
            if isinstance(data, dict):
                link_url = data.get('link') or data.get('url')
                if not link_url:
                    client.sendMessage(
                        Message(text=f"🚫 Không tìm thấy link group. Dữ liệu trả về: {data}"),
                        thread_id,
                        thread_type,
                        ttl=30000
                    )
                    print("Không tìm thấy link nhóm. Dừng command.")
                    return
            elif isinstance(data, str):
                link_url = data
            else:
                client.sendMessage(
                    Message(text="🚫 Không tìm thấy link group."),
                    thread_id,
                    thread_type,
                    ttl=30000
                )
                print("Không tìm thấy link nhóm. Dừng command.")
                return
        else:
            client.sendMessage(
                Message(text=f"🚫 Lỗi từ Zalo API: {group_link.get('error_message', 'Lỗi không xác định')}"),
                thread_id,
                thread_type,
                ttl=30000
            )
            print("Lỗi từ Zalo API. Dừng command.")
            return

        # Kiểm tra định dạng URL
        if not re.match(url_pattern, link_url):
            client.sendMessage(
                Message(text="🚫 Link nhóm không hợp lệ!"),
                thread_id,
                thread_type,
                ttl=30000
            )
            print("Link nhóm không hợp lệ. Dừng command.")
            return

        # Thiết lập các tham số
        title = group_name
        domain_url = "zalo.me"
        desc = "Bấm vào ảnh để vào nhóm"

        print(f"Command hợp lệ: link_url = {link_url}, title = {title}, thumbnail_url = {thumbnail_url}")

        # Thông báo bắt đầu gửi
        client.sendMessage(
            Message(text="⏳ Đang bắt đầu gửi link mời nhóm đến các nhóm..."),
            thread_id,
            thread_type,
            ttl=300000
        )

        # Khởi chạy gửi link trong một thread riêng
        threading.Thread(
            target=start_sharelink,
            args=(client, link_url, thumbnail_url, title, domain_url, desc, thread_id, thread_type),
            daemon=True
        ).start()

    except Exception as e:
        client.sendMessage(
            Message(text=f"🚫 Đã xảy ra lỗi khi xử lý lệnh: {e}"),
            thread_id,
            thread_type,
            ttl=30000
        )
        print(f"Lỗi khi xử lý lệnh: {e}")

def get_mitaizl():
    return {
        'group.sharelink': handle_groupsharelink_command
    }
