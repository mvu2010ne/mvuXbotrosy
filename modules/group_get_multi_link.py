from zlapi.models import Message

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Lấy link mời của nhiều nhóm Zalo thông qua danh sách ID nhóm",
    'tính năng': [
        "🔗 Lấy link mời của nhiều nhóm Zalo thông qua API Zalo dựa trên danh sách ID nhóm.",
        "📋 Hỗ trợ trả về danh sách link dưới dạng URL hoặc thông báo lỗi nếu không tìm thấy.",
        "🔍 Kiểm tra và xử lý dữ liệu trả về từ API để đảm bảo tính chính xác.",
        "🔔 Thông báo lỗi cụ thể nếu ID nhóm không hợp lệ hoặc gặp sự cố khi truy xuất link.",
        "📩 Gửi kết quả trực tiếp dưới dạng tin nhắn trả lời trong nhóm hoặc người dùng."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh group.getmultilink kèm danh sách ID nhóm (mỗi ID trên một dòng).",
        "📌 Ví dụ:\n group.getmultilink\n2325851487330397984\n6067869905888176466\n5812569935518462669",
        "✅ Nhận danh sách link mời nhóm hoặc thông báo lỗi ngay lập tức."
    ]
}

def handle_groupmultilink_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản hồi emoji "✅" xác nhận đã nhận lệnh
    action = "✅ "
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    try:
        # Tách nội dung tin nhắn thành các dòng
        lines = message.strip().split('\n')
        if len(lines) < 2:
            response_message = "Vui lòng cung cấp ít nhất một ID nhóm. Ví dụ:\n group.getmultilink\n2325851487330397984\n6067869905888176466"
            message_to_send = Message(text=response_message)
            client.replyMessage(message_to_send, message_object, thread_id, thread_type)
            return

        # Bỏ dòng đầu tiên (lệnh 'group.getmultilink') và lấy danh sách ID nhóm
        group_ids = [line.strip() for line in lines[1:] if line.strip().isdigit()]

        if not group_ids:
            response_message = "Không tìm thấy ID nhóm hợp lệ trong danh sách."
            message_to_send = Message(text=response_message)
            client.replyMessage(message_to_send, message_object, thread_id, thread_type)
            return

        # Lưu trữ kết quả cho từng nhóm
        results = []
        for group_id in group_ids:
            try:
                group_link = client.getGroupLink(chatID=group_id)
                print(f"Dữ liệu từ Zalo API cho nhóm {group_id}:", group_link)
                if group_link.get("error_code") == 0:
                    data = group_link.get("data")
                    if isinstance(data, dict):
                        if data.get('link'):
                            results.append(f"{data['link']}")
                        elif data.get('url'):
                            results.append(f"✅ Nhóm {group_id}: {data['url']}")
                        else:
                            results.append(f"❌ Nhóm {group_id}: Không tìm thấy link group. Dữ liệu trả về: {data}")
                    elif isinstance(data, str):
                        results.append(f"✅ Nhóm {group_id}: {data}")
                    else:
                        results.append(f"❌ Nhóm {group_id}: Không tìm thấy link group.")
                else:
                    results.append(f"❌ Nhóm {group_id}: Lỗi từ Zalo API: {group_link.get('error_message', 'Lỗi không xác định')}")
            except ValueError:
                results.append(f"❌ Nhóm {group_id}: Lỗi: ID nhóm không hợp lệ.")
            except Exception as e:
                results.append(f"❌ Nhóm {group_id}: Đã xảy ra lỗi: {str(e)}")

        # Tạo phản hồi với tất cả kết quả
        response_message = "\n".join(results)
        if not response_message:
            response_message = "Không có kết quả nào được trả về."

    except Exception as e:
        response_message = f"Đã xảy ra lỗi khi xử lý lệnh: {str(e)}"

    message_to_send = Message(text=response_message)
    client.replyMessage(message_to_send, message_object, thread_id, thread_type)

def get_mitaizl():
    return {
        'group.getmultilink': handle_groupmultilink_command
    }