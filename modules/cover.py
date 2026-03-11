import os
import requests
from zlapi.models import Message
#hoàng anh zalo bot 
#xóa hai dòng này làm chó
# Thư mục cache
CACHE_DIR = 'modules/cache'
os.makedirs(CACHE_DIR, exist_ok=True)

# Hàm gọi API để lấy ảnh bìa
def get_anh_bia(name, year_of_birth):
    # Địa chỉ API với thông tin tên và năm sinh
    url = f"https://subhatde.id.vn/anhbia?name={name}&age={year_of_birth}"
    
    try:
        response = requests.get(url)
        
        # Kiểm tra xem API có trả về dữ liệu hợp lệ không
        if response.status_code == 200:
            # Lưu ảnh vào thư mục cache
            image_path = os.path.join(CACHE_DIR, "anh_bia.png")
            with open(image_path, 'wb') as file:
                file.write(response.content)
            return image_path
        else:
            return None
    except Exception as e:
        print(f"Lỗi khi gọi API: {e}")
        return None

# Hàm xử lý lệnh *anhbia và gửi ảnh
def handle_anh_bia_command(message, message_object, thread_id, thread_type, author_id, client):
    content = message.strip().split()

    if len(content) < 3:
        error_message = Message(text="❌ Vui lòng nhập tên và năm sinh.")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)  # TTL 1 phút
        return

    # Lấy tên và năm sinh từ lệnh
    name = " ".join(content[1:-1])  # Tên sẽ là các từ trong phần trước số năm sinh
    try:
        year_of_birth = int(content[-1])  # Năm sinh là số cuối cùng
    except ValueError:
        error_message = Message(text="❌ Năm sinh không hợp lệ. Vui lòng nhập số.")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return
    loading_message = Message(text="✨Ha x at Đang tạo ảnh bìa... Vui lòng đợi một chút.")
    client.replyMessage(loading_message, message_object, thread_id, thread_type, ttl=60000)

    # Gọi API để lấy ảnh bìa
    image_path = get_anh_bia(name, year_of_birth)

    if image_path:
        # Gửi ảnh bìa cho người dùng
        success_message = Message(text="✨ Đã tạo ảnh bìa thành công!Hãy lưu ảnh để load full kích cỡ ảnh:")
        client.sendLocalImage(
            imagePath=image_path,
            message=success_message,
            thread_id=thread_id,
            thread_type=thread_type,
            ttl=60000
        )

        # Xóa ảnh tạm sau khi gửi
        os.remove(image_path)
    else:
        error_message = Message(text="❌ Đã xảy ra lỗi khi tạo ảnh bìa. Vui lòng thử lại.")
        client.replyMessage(error_message, message_object, thread_id, thread_type)

# Đăng ký các lệnh
def get_mitaizl():
    return {
        'cover': handle_anh_bia_command,
    }
