import json
from zlapi.models import Message, MessageStyle, MultiMsgStyle

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🔍 Lấy và hiển thị thông tin chi tiết của tin nhắn được trích dẫn hoặc tin nhắn gần nhất trong nhóm dưới dạng JSON.",
    'tính năng': [
        "📩 Hỗ trợ lấy dữ liệu tin nhắn khi người dùng reply (trích dẫn) một tin nhắn.",
        "🔄 Tự động lấy tin nhắn gần nhất trước đó nếu không có trích dẫn.",
        "📋 Định dạng dữ liệu tin nhắn thành JSON với mã hóa Unicode và hiển thị có định dạng.",
        "✂️ Cắt nhỏ dữ liệu JSON thành nhiều phần nếu vượt quá 3000 ký tự để gửi.",
        "🎨 Gửi tin nhắn với định dạng màu sắc và chữ in đậm tùy chỉnh."
    ],
    'hướng dẫn sử dụng': [
        "📌 Gửi lệnh src khi reply một tin nhắn để lấy thông tin chi tiết của tin nhắn được trích dẫn.",
        "📩 Gửi lệnh src mà không reply để lấy thông tin của tin nhắn gần nhất trước đó trong nhóm.",
        "✅ Kết quả sẽ được gửi dưới dạng JSON, chia nhỏ nếu dữ liệu dài."
    ]
}

def send_message_with_style(client, text, thread_id, thread_type, ttl=60000, color="#2e86de"):
    base_length = len(text)
    adjusted_length = base_length + 355
    style = MultiMsgStyle([
        MessageStyle(offset=0, length=adjusted_length, style="color", color=color, auto_format=False),
        MessageStyle(offset=0, length=adjusted_length, style="font", size="8", auto_format=False)
    ])
    msg = Message(text=text, style=style)
    client.send(msg, thread_id=thread_id, thread_type=thread_type, ttl=ttl)

def handle_src_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        # Kiểm tra xem tin nhắn có reply (quote) không
        if hasattr(message_object, 'quote') and message_object.quote:
            quote_data = message_object.quote
            quoted_msg_id = quote_data.get('globalMsgId') or quote_data.get('cliMsgId')
            if quoted_msg_id:
                # Lấy danh sách tin nhắn gần đây trong nhóm
                recent_messages = client.getRecentGroup(thread_id)
                if recent_messages and hasattr(recent_messages, 'groupMsgs'):
                    # Tìm tin nhắn khớp với quoted_msg_id
                    for msg in recent_messages.groupMsgs:
                        if str(msg.get('msgId')) == str(quoted_msg_id) or str(msg.get('cliMsgId')) == str(quoted_msg_id):
                            full_msg_data = msg
                            full_json = json.dumps(full_msg_data, indent=2, ensure_ascii=False)
                            break
                    else:
                        full_json = "Không tìm thấy tin nhắn được trích dẫn trong lịch sử gần đây."
                else:
                    full_json = "Không thể lấy lịch sử tin nhắn nhóm."
            else:
                full_json = "Không tìm thấy ID của tin nhắn được trích dẫn."
        else:
            # Nếu không reply, lấy tin nhắn gần nhất trước đó
            recent_messages = client.getRecentGroup(thread_id)
            if recent_messages and hasattr(recent_messages, 'groupMsgs') and len(recent_messages.groupMsgs) > 1:
                # Sắp xếp theo timestamp (ts) để đảm bảo lấy tin nhắn trước đó
                sorted_msgs = sorted(recent_messages.groupMsgs, key=lambda x: int(x.get('ts', 0)), reverse=True)
                # Bỏ qua tin nhắn hiện tại (src) nếu nó là tin nhắn mới nhất
                for msg in sorted_msgs:
                    if str(msg.get('msgId')) != str(message_object.msgId) and int(msg.get('ts', 0)) < int(message_object.ts):
                        full_msg_data = msg
                        full_json = json.dumps(full_msg_data, indent=2, ensure_ascii=False)
                        break
                else:
                    full_json = "Không tìm thấy tin nhắn trước đó."
            else:
                full_json = "Không có tin nhắn trước đó trong lịch sử nhóm."

        # Cắt nếu quá dài
        chunks = [full_json[i:i+3000] for i in range(0, len(full_json), 3000)]
        for chunk in chunks:
            send_message_with_style(client, chunk, thread_id, thread_type)
    except Exception as e:
        send_message_with_style(client, f"❌ Lỗi khi xử lý message object: {str(e)}", thread_id, thread_type)

def get_mitaizl():
    return {
        'src': handle_src_command
    }