from zlapi.models import Message
import requests
import urllib.parse
import os

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Tạo mã QR từ văn bản với thiết kế tùy chỉnh.",
    'tính năng': [
        "📷 Tạo mã QR với kích thước 500x500, màu xanh dương, nền trắng, viền 10px.",
        "🔗 Chuyển đổi văn bản nhập vào thành mã QR thông qua API qrserver.",
        "✅ Gửi phản ứng xác nhận khi nhận lệnh hợp lệ.",
        "⚠️ Thông báo lỗi nếu không nhập nội dung hoặc API gặp sự cố."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh qrcode <nội dung> để tạo mã QR.",
        "📌 Ví dụ: qrcode https://example.com.",
        "✅ Nhận ảnh mã QR trong tin nhắn ngay lập tức."
    ]
}

def handle_qrcode_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản ứng ngay khi người dùng soạn đúng lệnh
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    text = message.split()

    if len(text) < 2 or not text[1].strip():
        error_message = Message(text="Vui lòng nhập nội dung muốn tạo qrcode.")
        client.replyMessage(error_message, message_object, thread_id, thread_type)
        return

    content = " ".join(text[1:])
    encoded_text = urllib.parse.quote(content, safe='')

    try:
        # Tùy chỉnh QR code: kích thước 500x500, màu xanh dương, nền trắng, viền 10px
        apiqrcode = (
            f'https://api.qrserver.com/v1/create-qr-code/'
            f'?size=500x500'  # Kích thước hợp lý
            f'&data={encoded_text}'  # Nội dung QR
            f'&color=1E90FF'  # Màu QR: xanh dương (#1E90FF)
            f'&bgcolor=FFFFFF'  # Màu nền: trắng
            f'&margin=10'  # Viền 10px
            f'&qzone=2'  # Vùng yên tĩnh để quét dễ hơn
            f'&format=png'  # Định dạng PNG cho chất lượng tốt
        )
        image_response = requests.get(apiqrcode)
        image_response.raise_for_status()  # Kiểm tra lỗi HTTP

        image_path = 'modules/cache/temp_image1.png'  # Đổi sang .png để khớp format
        with open(image_path, 'wb') as f:
            f.write(image_response.content)

        if os.path.exists(image_path):
            client.sendLocalImage(
                image_path, 
                message=None,
                thread_id=thread_id,
                thread_type=thread_type,
                width=500,  # Điều chỉnh kích thước hiển thị
                height=500
            )
            os.remove(image_path)
        else:
            error_message = Message(text="Không thể tạo được QR code.")
            client.sendMessage(error_message, thread_id, thread_type)

    except requests.exceptions.RequestException as e:
        error_message = Message(text=f"Đã xảy ra lỗi khi gọi API: {str(e)}")
        client.sendMessage(error_message, thread_id, thread_type)
    except Exception as e:
        error_message = Message(text=f"Đã xảy ra lỗi không xác định: {str(e)}")
        client.sendMessage(error_message, thread_id, thread_type)

def get_mitaizl():
    return {
        'qrcode': handle_qrcode_command
    }