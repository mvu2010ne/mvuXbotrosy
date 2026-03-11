import requests
from zlapi.models import Message, Mention

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Lấy mã QR Zalo của người dùng hoặc người được tag.",
    'tính năng': [
        "📷 Tải và gửi mã QR từ Zalo API.",
        "🏷️ Hỗ trợ lấy QR của người dùng hoặc người được tag.",
        "✅ Gửi phản ứng xác nhận khi nhận lệnh hợp lệ.",
        "⚠️ Thông báo lỗi nếu không lấy được QR hoặc tải ảnh thất bại."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh getqr để lấy mã QR của bạn.",
        "📩 Gửi getqr với tag để lấy mã QR của người khác.",
        "📌 Ví dụ: getqr hoặc getqr @username.",
        "✅ Nhận mã QR trong tin nhắn."
    ]
}

def handle_qruser_command(message, message_object, thread_id, thread_type, author_id, client):
    print("👉 Bắt đầu xử lý lệnh qruser")
    print(f"🔍 message: {message}")
    print(f"🔍 thread_id: {thread_id}, thread_type: {thread_type}, author_id: {author_id}")
    print(f"🔍 mentions: {message_object.mentions}")

    mentions = message_object.mentions
    target_id = mentions[0]['uid'] if mentions else author_id
    print(f"🎯 target_id: {target_id}")

    try:
        qr_data = client.getQrUser(target_id)
        print(f"🧩 QR data: {qr_data}")
    except Exception as e:
        print(f"❌ Lỗi khi gọi client.getQrUser: {e}")
        client.sendMessage(Message(text=f"Lỗi lấy QR: {e}"), thread_id=thread_id, thread_type=thread_type)
        return

    if qr_data:
        qr_url = qr_data.get(str(target_id), "")
        print(f"🌐 QR URL: {qr_url}")

        if qr_url:
            img_path = "qr_code.jpg"
            try:
                print("⬇️ Đang tải ảnh QR code...")
                response = requests.get(qr_url, stream=True, timeout=10)
                response.raise_for_status()

                with open(img_path, "wb") as file:
                    for chunk in response.iter_content(1024):
                        file.write(chunk)

                print("✅ Tải ảnh thành công, gửi ảnh...")
                client.sendLocalImage(
                    img_path,
                    message=Message(
                        text="@Member Đây là mã QR code của bạn",
                        mention=Mention(author_id, length=len("@Member"), offset=0)
                    ),
                    thread_id=thread_id,
                    thread_type=thread_type
                )

            except requests.exceptions.RequestException as e:
                print(f"❌ Lỗi khi tải ảnh QR: {e}")
                client.sendMessage(Message(text=f"Lỗi tải ảnh QR: {e}"), thread_id=thread_id, thread_type=thread_type)
            except Exception as e:
                print(f"❌ Lỗi không xác định khi tải/gửi ảnh: {e}")
                client.sendMessage(Message(text=f"Lỗi không xác định: {e}"), thread_id=thread_id, thread_type=thread_type)

        else:
            print("⚠️ Không tìm thấy URL ảnh QR.")
            client.sendMessage(Message(text="Không tìm thấy URL ảnh QR."), thread_id=thread_id, thread_type=thread_type)
    else:
        print("⚠️ Không thể lấy mã QR của người dùng.")
        client.sendMessage(Message(text="Không thể lấy mã QR của người dùng."), thread_id=thread_id, thread_type=thread_type)

def get_mitaizl():
    return {
        'user.qr': handle_qruser_command
    }
