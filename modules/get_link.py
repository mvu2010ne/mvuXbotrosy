from zlapi.models import Message
import json
import urllib.parse

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Lấy link của hình ảnh, file, gif, video hoặc link từ tin nhắn hoặc tin nhắn reply.",
    'tính năng': [
        "✅ Gửi phản ứng xác nhận khi lệnh được nhập đúng.",
        "🔗 Tự động lấy link từ hình ảnh, file, gif, video hoặc link trong tin nhắn.",
        "📤 Gửi link trực tiếp đến người dùng.",
        "❗ Hiển thị thông báo lỗi nếu không nhận được nội dung phù hợp."
    ],
    'hướng dẫn sử dụng': [
        "📩 Dùng lệnh 'getlink' để lấy link của hình ảnh, file, gif, video hoặc link.",
        "📌 Reply tin nhắn chứa nội dung cần lấy link và nhập lệnh 'getlink'.",
        "✅ Nhận link trực tiếp ngay lập tức."
    ]
}

last_sent_image_url = None  

def handle_getlink_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản ứng ngay khi người dùng soạn đúng lệnh
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    global last_sent_image_url
    msg_obj = message_object

    if msg_obj.msgType == "chat.photo":
        img_url = msg_obj.content.href.replace("\\/", "/")
        img_url = urllib.parse.unquote(img_url)
        # Chuyển đổi link từ .jxl sang .jpg
        if img_url.endswith('.jxl'):
            img_url = img_url.replace('/jxl/', '/jpg/').replace('.jxl', '.jpg')
        last_sent_image_url = img_url
        send_image_link(img_url, thread_id, thread_type, client)

    elif msg_obj.quote:
        attach = msg_obj.quote.attach
        if attach:
            try:
                attach_data = json.loads(attach)
            except json.JSONDecodeError as e:
                print(f"Lỗi khi phân tích JSON: {str(e)}")
                return

            image_url = attach_data.get('hdUrl') or attach_data.get('href')
            if image_url:
                # Chuyển đổi link từ .jxl sang .jpg
                if image_url.endswith('.jxl'):
                    image_url = image_url.replace('/jxl/', '/jpg/').replace('.jxl', '.jpg')
                send_image_link(image_url, thread_id, thread_type, client)
            else:
                send_error_message(thread_id, thread_type, client)
        else:
            send_error_message(thread_id, thread_type, client)
    else:
        send_error_message(thread_id, thread_type, client)

def send_image_link(image_url, thread_id, thread_type, client):
    if image_url:
        message_to_send = Message(text=f"{image_url}")
        
        if hasattr(client, 'send'):
            client.send(message_to_send, thread_id, thread_type)
        else:
            print("Client không hỗ trợ gửi tin nhắn.")

def send_error_message(thread_id, thread_type, client):
    error_message = Message(text="Vui lòng reply(phản hồi) hình ảnh, gif, file, video cần getlink.")
    
    if hasattr(client, 'send'):
        client.send(error_message, thread_id, thread_type, ttl=10000)
    else:
        print("Client không hỗ trợ gửi tin nhắn.")

def get_mitaizl():
    return {
        'getlink': handle_getlink_command
    }