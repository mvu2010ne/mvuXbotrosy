import json
from zlapi.models import Message, MessageStyle, MultiMsgStyle

def send_message_with_style(client, text, thread_id, thread_type, ttl=60000, color="#2e86de"):
    base_length = len(text)
    adjusted_length = base_length + 355
    style = MultiMsgStyle([
        MessageStyle(offset=0, length=adjusted_length, style="color", color=color, auto_format=False),
        MessageStyle(offset=0, length=adjusted_length, style="bold", size="8", auto_format=False)
    ])
    msg = Message(text=text, style=style)
    client.send(msg, thread_id=thread_id, thread_type=thread_type, ttl=ttl)

def handle_src_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        # Lấy toàn bộ nội dung của message_object hiện tại
        full_msg_data = message_object.__dict__ if hasattr(message_object, '__dict__') else dict(message_object)
        full_json = json.dumps(full_msg_data, indent=2, ensure_ascii=False)

        # Cắt nếu quá dài
        chunks = [full_json[i:i+3000] for i in range(0, len(full_json), 3000)]
        for chunk in chunks:
            send_message_with_style(client, chunk, thread_id, thread_type)
    except Exception as e:
        send_message_with_style(client, f"❌ Lỗi khi xử lý message object: {str(e)}", thread_id, thread_type)

def get_mitaizl():
    return {
        'srcreply': handle_src_command
    }
