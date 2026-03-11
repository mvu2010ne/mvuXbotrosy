import re
import threading
import time
from zlapi.models import Message, ThreadType

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Gửi tin nhắn đến danh sách id cố định",
    'tính năng': [
        "📨 Gửi tin nhắn đến danh sách id được chỉ định.",
        "🕵️‍♂️ Kiểm tra và xử lý định dạng lệnh gửi tin nhắn.",
        "🔒 Chỉ quản trị viên mới có quyền sử dụng lệnh này.",
        "⏳ Gửi tin nhắn với khoảng cách thời gian cố định giữa các lần gửi.",
        "🔍 Kiểm tra quyền admin trước khi thực hiện lệnh."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh send.idlist id1 id2 ... | nội dung tin nhắn để gửi tin nhắn đến danh sách id.",
        "📌 Ví dụ: send.idlist 123 456 | Đây là nội dung tin nhắn để gửi tin nhắn đến id 123 và 456.",
        "✅ Nhận thông báo trạng thái và kết quả gửi tin nhắn ngay lập tức."
    ]
}

# Danh sách admin (giữ nguyên)
ADMIN_IDS = {"3299675674241805615", "5835232686339531421", "3041646020640969809"}

def send_message_with_style(client, text, thread_id, thread_type, ttl=None, color="#db342e"):
    """
    Gửi tin nhắn plain text (không áp dụng định dạng style)
    """
    msg = Message(text=text)
    if ttl is not None:
        client.sendMessage(msg, thread_id, thread_type, ttl=ttl)
    else:
        client.sendMessage(msg, thread_id, thread_type)

def send_reply_with_style(client, text, message_object, thread_id, thread_type, ttl=None, color="#db342e"):
    """
    Gửi tin nhắn phản hồi plain text (không áp dụng định dạng style)
    """
    msg = Message(text=text)
    if ttl is not None:
        client.replyMessage(msg, message_object, thread_id, thread_type, ttl=ttl)
    else:
        client.replyMessage(msg, message_object, thread_id, thread_type)

def send_reply_with_custom_style(client, prefix, content, message_object, thread_id, thread_type, ttl=None, prefix_color="#db342e"):
    """
    Gửi tin nhắn phản hồi với phần prefix và content được nối lại,
    nhưng toàn bộ tin nhắn sẽ được gửi dưới dạng plain text.
    """
    full_text = prefix + content
    msg = Message(text=full_text)
    if ttl is not None:
        client.replyMessage(msg, message_object, thread_id, thread_type, ttl=ttl)
    else:
        client.replyMessage(msg, message_object, thread_id, thread_type)

def start_sendto(client, id_list, content):
    """
    Gửi tin nhắn đến danh sách id được chỉ định.
    Mỗi id được coi là thread_id và tin nhắn được gửi với khoảng cách 5 giây giữa các lần gửi.
    """
    for target_id in id_list:
        try:
            send_message_with_style(client, content, target_id, ThreadType.GROUP, ttl=5000)
            print(f"Đã gửi tin nhắn đến {target_id}")
            time.sleep(5)  # Khoảng thời gian chờ giữa các lần gửi
        except Exception as e:
            print(f"Lỗi khi gửi tin nhắn đến {target_id}: {e}")

def handle_sendids_command(message, message_object, thread_id, thread_type, author_id, client):
    """
    Xử lý lệnh send.idlist với định dạng:
      send.idlist id1 id2 id3 ... | nội dung tin nhắn
    Phần bên trái dấu "|" là danh sách id (chỉ bao gồm số),
    phần bên phải là nội dung tin nhắn cần gửi.
    """
    # Gửi phản ứng ngay khi nhận lệnh
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    
    try:
        # Kiểm tra quyền admin
        if author_id not in ADMIN_IDS:
            send_reply_with_style(client, "Bạn không có quyền thực hiện lệnh này.", 
                                  message_object, thread_id, thread_type, ttl=30000)
            return
        
        # Hỗ trợ cả "send.idlist" và ",send.idlist"
        if message.lower().startswith("send.idlist"):
            message_body = message[len("send.idlist"):].strip()
        elif message.lower().startswith(",send.idlist"):
            message_body = message[len(",send.idlist"):].strip()
        else:
            print("Không phải lệnh send.idlist, bỏ qua.")
            return
        
        # Kiểm tra dấu phân cách "|"
        if "|" not in message_body:
            send_reply_with_style(client, "Vui lòng nhập đúng định dạng: send.idlist id1 id2 ... | nội dung tin nhắn", 
                                  message_object, thread_id, thread_type, ttl=30000)
            return
        
        # Tách nội dung theo dấu "|"
        left, right = message_body.split("|", 1)
        left = left.strip()
        right = right.strip()
        
        # Lấy danh sách id từ phần bên trái
        tokens = left.split()
        id_list = [token for token in tokens if token.isdigit()]
        
        if not id_list:
            send_reply_with_style(client, "Không tìm thấy danh sách id hợp lệ!", 
                                  message_object, thread_id, thread_type, ttl=30000)
            return
        
        if not right:
            send_reply_with_style(client, "Vui lòng nhập nội dung tin nhắn sau dấu |!", 
                                  message_object, thread_id, thread_type, ttl=30000)
            return
        
        content = right
        
        # Khởi chạy gửi tin nhắn đến các id trong một luồng mới
        threading.Thread(target=start_sendto, args=(client, id_list, content), daemon=True).start()
        
        # Phản hồi lại cho người dùng
        prefix = "Đang gửi nội dung đến các id:\n"
        send_reply_with_custom_style(client, prefix, content, message_object, thread_id, thread_type, ttl=180000)
    except Exception as e:
        print(f"Lỗi khi xử lý lệnh send.idlist: {e}")

def get_mitaizl():
    return {
        'send.idlist': handle_sendids_command
    }
