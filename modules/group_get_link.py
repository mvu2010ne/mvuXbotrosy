from zlapi.models import Message

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Lấy link mời của nhóm Zalo",
    'tính năng': [
        "🔗 Lấy link mời nhóm Zalo thông qua API Zalo.",
        "📋 Hỗ trợ trả về link dưới dạng URL hoặc thông báo lỗi nếu không tìm thấy.",
        "🔍 Kiểm tra và xử lý dữ liệu trả về từ API để đảm bảo tính chính xác.",
        "🔔 Thông báo lỗi cụ thể nếu thiếu ID nhóm hoặc gặp sự cố khi truy xuất link.",
        "📩 Gửi kết quả trực tiếp dưới dạng tin nhắn trả lời trong nhóm."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh group.getlink để lấy link mời của nhóm hiện tại.",
        "📌 Ví dụ: group.getlink (không cần tham số, lệnh sẽ tự động lấy ID nhóm).",
        "✅ Nhận link mời nhóm hoặc thông báo lỗi ngay lập tức."
    ]
}

def handle_grouplink_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        group_link = client.getGroupLink(chatID=thread_id)
        print("Dữ liệu từ Zalo API:", group_link)
        if group_link.get("error_code") == 0:
            data = group_link.get("data")
            if isinstance(data, dict):
                if data.get('link'):
                    response_message = f"{data['link']}"
                elif data.get('url'):
                    response_message = f"{data['url']}"
                else:
                    response_message = f"Không tìm thấy link group. Dữ liệu trả về: {data}"
            elif isinstance(data, str):
                response_message = f"{data}"
            else:
                response_message = f"Không tìm thấy link group."
        else:
            response_message = f"Lỗi từ Zalo API: {group_link.get('error_message', 'Lỗi không xác định')}"
    except ValueError as e:
        response_message = f"Lỗi: Cần có Group ID."
    except Exception as e:
        response_message = f"Đã xảy ra lỗi: {str(e)}"

    message_to_send = Message(text=response_message)
    client.replyMessage(message_to_send, message_object, thread_id, thread_type)

def get_mitaizl():
    return {
        'group.getlink': handle_grouplink_command
    }
