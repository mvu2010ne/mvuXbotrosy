from zlapi.models import Message, ThreadType
from datetime import datetime
import requests

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Lấy danh thiếp người dùng hoặc danh thiếp người được tag.",
    'tính năng': [
        "✅ Gửi phản ứng xác nhận khi lệnh được nhập đúng.",
        "📇 Lấy thông tin danh thiếp từ người dùng được tag, user_id cụ thể hoặc chính người dùng nếu không có tag.",
        "🔗 Sử dụng thông tin người dùng để tạo danh thiếp và hiển thị mã QR hoặc ảnh đại diện nếu không có mã QR.",
        "❗ Hiển thị thông báo lỗi nếu không lấy được thông tin hoặc không tạo được danh thiếp."
    ],
    'hướng dẫn sử dụng': [
        "Dùng lệnh 'user.idcard' để lấy danh thiếp của bạn.",
        "Dùng 'user.idcard @tag' để lấy danh thiếp của người được tag.",
        "Dùng 'user.idcard <user_id>' để lấy danh thiếp của người dùng với ID cụ thể."
    ]
}

def handle_cardinfo_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản ứng ngay khi người dùng soạn đúng lệnh
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    # Tách nội dung lệnh để kiểm tra tham số
    command_parts = message.strip().split()
    
    # Xác định userId
    if len(command_parts) > 1 and command_parts[1].isdigit():
        # Trường hợp: user.idcard <user_id>
        userId = command_parts[1]
    elif message_object.mentions:
        # Trường hợp: user.idcard @tag
        userId = message_object.mentions[0]['uid']
    else:
        # Trường hợp: user.idcard
        userId = author_id
    
    if not userId:
        client.send(
            Message(text="Không tìm thấy người dùng."),
            thread_id=thread_id,
            thread_type=thread_type
        )
        return
    
    user_info = client.fetchUserInfo(userId).changed_profiles.get(userId)
    
    if not user_info:
        client.send(
            Message(text="Không thể lấy thông tin người dùng."),
            thread_id=thread_id,
            thread_type=thread_type
        )
        return
    
    dob = user_info.dob
    if dob:
        if isinstance(dob, int):
            dob = datetime.fromtimestamp(dob).strftime("%d/%m/%Y")
    else:
        dob = "Không công khai"
    
    # Sửa lỗi: phone không nên bằng dob
    phone = user_info.get('phone', 'Không công khai')
    
    # Lấy mã QR hoặc avatarUrl làm dự phòng
    qr_url = ""
    try:
        qr_data = client.getQrUser(userId)
        qr_url = qr_data.get(str(userId), "") if qr_data else ""
    except Exception as e:
        client.send(
            Message(text=f"Lỗi lấy mã QR: {e}"),
            thread_id=thread_id,
            thread_type=thread_type
        )
    
    # Nếu không có mã QR, sử dụng avatarUrl
    if not qr_url:
        qr_url = user_info.get('avatarUrl', "")
        if not qr_url:
            client.send(
                Message(text="Không thể lấy mã QR hoặc ảnh đại diện của người dùng."),
                thread_id=thread_id,
                thread_type=thread_type, ttl=60000
            )
            return
    
    client.sendBusinessCard(userId=userId, qrCodeUrl=qr_url, thread_id=thread_id, thread_type=thread_type, phone=phone, ttl=60000)

def get_mitaizl():
    return {
        'user.idcard': handle_cardinfo_command
    }