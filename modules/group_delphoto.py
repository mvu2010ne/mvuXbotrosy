import time
import logging
from zlapi.models import Message, MessageStyle, MultiMsgStyle
from config import ADMIN, PREFIX

# Cấu hình logger
logger = logging.getLogger("PhotoDeleter")

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🖼️ Xóa các tin nhắn chứa ảnh trong nhóm Zalo được chỉ định.",
    'tính năng': [
        "🖼️ Xóa tin nhắn chứa ảnh trong nhóm khi nhận lệnh.",
        "✅ Chỉ admin được phép sử dụng lệnh.",
        "⚠️ Ghi log chi tiết các hoạt động và lỗi."
    ],
    'hướng dẫn sử dụng': [
        f"📩 Gửi {PREFIX}deletephoto [group_id] hoặc tag nhóm để xóa tin nhắn ảnh ngay lập tức.",
        "📌 Ví dụ: deletephoto 123456789 hoặc deletephoto @groupname."
    ]
}

def send_reply_with_style(client, text, message_object, thread_id, thread_type, ttl=30000, color="#000000"):
    """
    Gửi tin nhắn phản hồi với định dạng màu sắc và in đậm.
    """
    base_length = len(text)
    adjusted_length = base_length + 355
    style = MultiMsgStyle([
        MessageStyle(
            offset=0,
            length=adjusted_length,
            style="color",
            color=color,
            auto_format=False
        ),
        MessageStyle(
            offset=0,
            length=adjusted_length,
            style="bold",
            size="8",
            auto_format=False
        )
    ])
    msg = Message(text=text, style=style)
    try:
        client.replyMessage(msg, message_object, thread_id, thread_type, ttl=ttl)
    except Exception as e:
        logger.error(f"Lỗi khi gửi tin nhắn phản hồi: {str(e)}")

def fetch_group_info(target_input, message_object, client, thread_id):
    """
    Xác định group_id từ tag, tham số nhập, hoặc thread_id nếu không có tham số.
    Trả về tuple (group_id, group_name) hoặc None nếu có lỗi.
    """
    if message_object.mentions and len(message_object.mentions) > 0:
        group_id = message_object.mentions[0]['uid']
    else:
        group_id = target_input.strip() if target_input.strip() else thread_id
    if not group_id:
        return None
    try:
        group_info = client.fetchGroupInfo(group_id)
        group = group_info.gridInfoMap[group_id]
        group_name = group.name
        return group_id, group_name
    except Exception as e:
        logger.error(f"Lỗi fetch thông tin cho group {group_id}: {e}")
        return None

def delete_photo_messages(client, group_id, group_name):
    """
    Lấy 50 tin nhắn gần nhất từ nhóm và xóa các tin nhắn chứa ảnh (chat.photo).
    """
    try:
        group_data = client.getRecentGroup(group_id)
        messages = group_data.groupMsgs if hasattr(group_data, 'groupMsgs') else []
        deleted_count = 0

        for msg in messages:
            # Kiểm tra nếu tin nhắn là ảnh (chat.photo)
            if getattr(msg, 'msgType', '') == 'chat.photo':
                try:
                    msg_id = getattr(msg, 'msgId', getattr(msg, 'globalMsgId', None))
                    owner_id = getattr(msg, 'uidFrom', getattr(msg, 'ownerId', None))
                    cli_msg_id = getattr(msg, 'cliMsgId', None)
                    client.deleteGroupMsg(
                        msgId=msg_id,
                        ownerId=owner_id,
                        clientMsgId=cli_msg_id,
                        groupId=group_id
                    )
                    deleted_count += 1
                    logger.info(f"Đã xóa tin nhắn ảnh trong nhóm {group_name} (ID: {group_id}), MsgID: {msg_id}")
                    time.sleep(0.5)  # Delay để tránh quá tải API
                except Exception as e:
                    logger.error(f"Lỗi khi xóa tin nhắn trong nhóm {group_name} (ID: {group_id}), MsgID: {msg_id}: {str(e)}")

        return deleted_count
    except Exception as e:
        logger.error(f"Lỗi khi lấy tin nhắn từ nhóm {group_name} (ID: {group_id}): {str(e)}")
        return None

def handle_deletephoto_command(message, message_object, thread_id, thread_type, author_id, client):
    """
    Xử lý lệnh xóa tin nhắn ảnh trong nhóm được chỉ định.
    Cú pháp: deletephoto [group_id] hoặc tag nhóm, hoặc không nhập để lấy nhóm hiện tại.
    """
    # Gửi phản hồi emoji "✅" xác nhận đã nhận lệnh
    action = "✅ "
    try:
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    except Exception as e:
        logger.error(f"Lỗi khi gửi reaction: {str(e)}")

    if author_id != ADMIN:
        error_msg = Message(text="❌ Chỉ admin mới có quyền sử dụng lệnh này.")
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    command_prefix = "deletephoto"
    param = message[len(command_prefix):].strip()
    group = fetch_group_info(param, message_object, client, thread_id)
    if group is None:
        error_msg = Message(text=f"Cú pháp: {PREFIX}deletephoto [group_id] hoặc tag nhóm.\nKhông thể lấy thông tin nhóm.")
        client.sendMessage(error_msg, thread_id, thread_type)
        return

    group_id, group_name = group

    # Thực hiện xóa tin nhắn ảnh và đếm số tin nhắn đã xóa
    result = delete_photo_messages(client, group_id, group_name)
    if result is None:
        reply_text = f"❌ Lỗi khi kiểm tra nhóm {group_name} (ID: {group_id})."
    else:
        reply_text = f"✅ Xóa hoàn tất trong nhóm {group_name} (ID: {group_id}).\nSố tin nhắn ảnh đã xóa: {result}."

    send_reply_with_style(client, reply_text, message_object, thread_id, thread_type, ttl=30000)

def get_mitaizl():
    """
    Trả về dictionary ánh xạ lệnh tới hàm xử lý.
    """
    return {
        'delphoto': handle_deletephoto_command
    }