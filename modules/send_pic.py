import json
import threading
import time
import os
import requests
from io import BytesIO
from zlapi.models import Message, ThreadType

{
    "tác giả": "Minh Vũ",
    "mô tả": "📷 Gửi ảnh đến toàn bộ nhóm chat một cách nhanh chóng và hiệu quả.",
    "tính năng": [
        "📷 Tải và gửi ảnh từ URL đến tất cả nhóm, ngoại trừ các nhóm trong danh sách loại trừ.",
        "🔍 Xác minh URL hợp lệ và đảm bảo nội dung là định dạng ảnh (JPEG, PNG, ...).",
        "🔗 Hỗ trợ gửi ảnh kèm chú thích tùy chỉnh đến các nhóm.",
        "🔒 Chỉ người dùng trong danh sách ADMIN_IDS được phép sử dụng lệnh.",
        "🗑️ Tự động xóa tệp ảnh tạm sau khi hoàn tất gửi.",
        "📊 Cung cấp báo cáo chi tiết về số nhóm gửi thành công và thất bại.",
        "⏳ Thêm độ trễ 1 giây giữa các lần gửi để tuân thủ giới hạn API."
    ],
    "hướng dẫn sử dụng": [
        "📩 Sử dụng lệnh: send.pic <URL ảnh> <chú thích> để gửi ảnh đến tất cả nhóm.",
        "📌 Ví dụ: send.pic https://example.com/image.jpg Ảnh đẹp quá!",
        "✅ Nhận thông báo trạng thái và báo cáo kết quả sau khi gửi hoàn tất."
    ]
}

# Danh sách admin
ADMIN_IDS = {"3299675674241805615", "5664399554139282940"}

def get_excluded_group_ids():
    """
    Đọc tệp danhsachnhom.json và trả về tập hợp các group_id.
    Giả sử tệp chứa danh sách các đối tượng với các khóa "group_id" và "group_name".
    """
    try:
        with open("danhsachnhom.json", "r", encoding="utf-8") as f:
            groups = json.load(f)
            return {grp.get("group_id") for grp in groups}
    except Exception as e:
        print(f"Lỗi khi đọc file danhsachnhom.json: {e}")
        return set()

def get_allowed_groups(client, excluded_group_ids):
    """Lọc danh sách nhóm không nằm trong danh sách loại trừ."""
    try:
        all_groups = client.fetchAllGroups()
        if not all_groups or not hasattr(all_groups, 'gridVerMap'):
            return set()
        return {gid for gid in all_groups.gridVerMap.keys() if gid not in excluded_group_ids}
    except Exception as e:
        print(f"Lỗi khi lấy danh sách nhóm: {e}")
        return set()

def download_and_send_image(client, image_url, caption, thread_id, thread_type):
    temp_image_path = "temp_image.jpg"
    try:
        # Tải ảnh từ URL
        response = requests.get(image_url, timeout=10)
        content_type = response.headers.get('Content-Type', '')
        if not content_type.startswith('image/'):
            print(f"URL {image_url} không phải ảnh (Content-Type: {content_type})")
            return False
        
        if response.status_code == 200:
            # Lưu ảnh vào bộ nhớ và file tạm
            image_data = BytesIO(response.content)
            with open(temp_image_path, 'wb') as f:
                f.write(image_data.read())
            
            # Gửi ảnh với chú thích
            message = Message(text=caption or "Ảnh được gửi từ bot")
            client.sendLocalImage(
                temp_image_path,
                message=message,
                thread_id=thread_id,
                thread_type=thread_type,
                width=1920,
                height=1080,
                ttl=180000
            )
            print(f"Đã gửi ảnh thành công đến nhóm {thread_id}")
            return True
        else:
            print(f"Không thể tải ảnh từ URL {image_url}, mã trạng thái: {response.status_code}")
            return False
    except Exception as e:
        if "permission" in str(e).lower() or "access" in str(e).lower():
            print(f"Bot không có quyền gửi tin nhắn đến nhóm {thread_id}")
        else:
            print(f"Lỗi khi gửi ảnh đến nhóm {thread_id}: {e}")
        return False
    finally:
        # Xóa file tạm nếu tồn tại
        if os.path.exists(temp_image_path):
            try:
                os.remove(temp_image_path)
            except Exception as e:
                print(f"Lỗi khi xóa file tạm {temp_image_path}: {e}")

def start_sendall_image(client, image_url, caption, thread_id, thread_type):
    try:
        # Lấy danh sách nhóm loại trừ từ file JSON
        excluded_group_ids = get_excluded_group_ids()
        
        # Lấy danh sách nhóm được phép
        allowed_thread_ids = get_allowed_groups(client, excluded_group_ids)
        if not allowed_thread_ids:
            error_msg = "Không có nhóm nào hợp lệ để gửi ảnh."
            print(error_msg)
            client.sendMessage(Message(text=error_msg), thread_id, thread_type, ttl=60000)
            return
        
        # Theo dõi kết quả
        success_groups = []
        failed_groups = []
        
        for gid in allowed_thread_ids:
            if download_and_send_image(client, image_url, caption, gid, ThreadType.GROUP):
                success_groups.append(gid)
            else:
                failed_groups.append(gid)
            time.sleep(0.3)  # Độ trễ để tránh giới hạn API
        
        # Gửi báo cáo kết quả
        total_groups = len(allowed_thread_ids)
        result_msg = (
            f"📷 Gửi ảnh hoàn tất!\n"
            f"👥 Tổng số nhóm: {total_groups}\n"
            f"✅ Gửi thành công: {len(success_groups)}\n"
            f"❌ Gửi thất bại: {len(failed_groups)}"
        )
        if failed_groups:
            result_msg += f"\n📛 Nhóm thất bại: {', '.join(failed_groups)}"
        if success_groups == allowed_thread_ids:
            result_msg += "\n🎉 Tất cả nhóm đều nhận được ảnh!"
        
        client.sendMessage(Message(text=result_msg), thread_id, thread_type, ttl=60000)
    except Exception as e:
        print(f"Lỗi khi xử lý gửi ảnh: {e}")
        client.sendMessage(Message(text=f"Lỗi khi xử lý: {str(e)}"), thread_id, thread_type, ttl=60000)

def handle_sendanh_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản ứng emoji
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
    
    try:
        # Kiểm tra quyền admin
        if author_id not in ADMIN_IDS:
            response_message = Message(text="⚠️ Bạn không có quyền thực hiện lệnh này.")
            client.replyMessage(response_message, message_object, thread_id, thread_type, ttl=30000)
            return
        
        # Kiểm tra lệnh
        message_lower = message.lower().strip()
        if message_lower.startswith("send.pic"):
            content = message[8:].strip()
        elif message_lower.startswith(",send.pic"):
            content = message[9:].strip()
        else:
            response_message = Message(text="❌ Lệnh không hợp lệ. Sử dụng: send.pic <link ảnh> <chú thích>")
            client.replyMessage(response_message, message_object, thread_id, thread_type, ttl=30000)
            return
        
        # Kiểm tra nội dung
        if not content:
            response_message = Message(text="❌ Vui lòng cung cấp ít nhất link ảnh!")
            client.replyMessage(response_message, message_object, thread_id, thread_type, ttl=30000)
            return
        
        # Tách link ảnh và chú thích
        parts = content.split(" ", 1)
        image_url = parts[0]
        caption = parts[1] if len(parts) > 1 else ""
        
        # Kiểm tra URL
        if not image_url.startswith(("http://", "https://")):
            response_message = Message(text="❌ Link ảnh không hợp lệ!")
            client.replyMessage(response_message, message_object, thread_id, thread_type, ttl=30000)
            return
        
        # Phản hồi bắt đầu
        response_text = f"⏳ Đang gửi ảnh đến tất cả nhóm{' với chú thích: ' + caption if caption else ''}..."
        client.replyMessage(Message(text=response_text), message_object, thread_id, thread_type, ttl=30000)
        
        # Chạy trong luồng riêng
        threading.Thread(
            target=start_sendall_image,
            args=(client, image_url, caption, thread_id, thread_type),
            daemon=True
        ).start()
    
    except Exception as e:
        print(f"Lỗi khi xử lý lệnh send.pic: {e}")
        response_message = Message(text=f"🚫 Lỗi khi xử lý lệnh: {str(e)}")
        client.replyMessage(response_message, message_object, thread_id, thread_type, ttl=30000)

def get_mitaizl():
    return {'send.pic': handle_sendanh_command}