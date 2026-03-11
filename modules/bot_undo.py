from zlapi import ZaloAPIException, ThreadType
from zlapi.models import Message, MessageStyle, MultiMsgStyle
from config import PREFIX
from datetime import datetime
import threading

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🔍 Thu hồi tin nhắn bot đã gửi trong nhóm.",
    'tính năng': [
        "📋 Thu hồi tin nhắn gần nhất hoặc nhiều tin nhắn bot gửi trong nhóm.",
        "📌 Thu hồi chính tin nhắn được reply nếu lệnh kèm reply.",
        "🔎 Sử dụng API lấy tin nhắn gần đây để xác định chính xác tin nhắn của bot.",
        "🎨 Gửi thông báo trạng thái với định dạng màu sắc và in đậm.",
        "🔐 Chỉ admin được chỉ định hoặc bot có thể sử dụng lệnh.",
        "⚠️ Thông báo lỗi chi tiết nếu không thể thu hồi."
    ],
    'hướng dẫn sử dụng': [
        f"📩 Gửi {PREFIX}bot.undo để thu hồi tin nhắn gần nhất của bot.",
        f"📩 Gửi {PREFIX}bot.undo <số lượng> để thu hồi nhiều tin nhắn (tối đa 50).",
        f"📌 Reply tin nhắn của bot và gửi {PREFIX}bot.undo để thu hồi chính tin nhắn đó.",
        "📌 Ví dụ: {PREFIX}bot.undo hoặc {PREFIX}bot.undo 3.",
        "✅ Nhận thông báo trạng thái thu hồi trong nhóm."
    ]
}

def send_message_with_style(client, text, thread_id, thread_type, ttl=60000, color="#db342e"):
    """Gửi tin nhắn với định dạng màu sắc và in đậm."""
    try:
        base_length = len(text)
        adjusted_length = base_length + 355
        style = MultiMsgStyle([
            MessageStyle(offset=0, length=adjusted_length, style="color", color=color, auto_format=False),
            MessageStyle(offset=0, length=adjusted_length, style="bold", size="8", auto_format=False)
        ])
        msg = Message(text=text, style=style)
        return client.send(msg, thread_id=thread_id, thread_type=thread_type, ttl=ttl)
    except Exception as e:
        return None

def _process_undo_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh bot.undo trong một luồng riêng biệt."""
    try:
        client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
    except Exception as e:
        pass

    if thread_type != ThreadType.GROUP:
        send_message_with_style(client, "🔴 Lệnh chỉ hoạt động trong nhóm!", thread_id, thread_type, color="#db342e")
        return

    if not hasattr(client, 'bot_id'):
        client.bot_id = "715870970611339054"
        try:
            bot_info = client.fetchUserInfo("715870970611339054")
            client.bot_id = getattr(bot_info, 'zaloId', bot_info.uid)
        except ZaloAPIException as e:
            pass

    allowed_users = ["3299675674241805615", client.bot_id]
    if str(author_id) not in allowed_users:
        send_message_with_style(client, "🔴 Chỉ admin hoặc bot mới có thể thu hồi tin nhắn!", thread_id, thread_type, color="#db342e")
        return

    # Kiểm tra xem tin nhắn có reply không
    quoted_msg = getattr(message_object, 'quote', None)
    if quoted_msg and hasattr(quoted_msg, 'globalMsgId') and hasattr(quoted_msg, 'cliMsgId'):
        # Kiểm tra xem tin nhắn reply có phải của bot không
        uid_from = str(quoted_msg.get('ownerId', quoted_msg.get('uidFrom', '')))
        d_name = quoted_msg.get('fromD', quoted_msg.get('dName', ''))
        if uid_from == str(client.bot_id) or uid_from == "0" or d_name == "Bé Bot Của Minh Vũ Shinn Cte":
            try:
                result = client.undoMessage(quoted_msg.globalMsgId, quoted_msg.cliMsgId, thread_id, thread_type)
                send_message_with_style(client, "✅ Đã thu hồi tin nhắn được reply!", thread_id, thread_type, color="#00ff00")
                print("Đã thu hồi tin nhắn được reply!")
                return
            except ZaloAPIException as e:
                error_msg = "🔴 Tin nhắn quá cũ, không thể thu hồi!" if e.error_code == 1206 else f"🔴 Lỗi #{e.error_code}: {str(e)}"
                send_message_with_style(client, error_msg, thread_id, thread_type, color="#db342e")
                return
            except Exception as e:
                send_message_with_style(client, f"🔴 Đã xảy ra lỗi: {str(e)}", thread_id, thread_type, color="#db342e")
                return
        else:
            send_message_with_style(client, "🔴 Tin nhắn được reply không phải của bot!", thread_id, thread_type, color="#db342e")
            return

    # Logic hiện tại nếu không có reply hoặc reply không phải của bot
    count = 1
    if message.strip().startswith(f"{PREFIX}bot.undo "):
        try:
            count = int(message.strip().split()[1])
            count = min(count, 50)
        except ValueError:
            send_message_with_style(client, "🔴 Vui lòng nhập số lượng hợp lệ!", thread_id, thread_type, color="#db342e")
            return

    try:
        group_data = client.getRecentGroup(thread_id)
        if not group_data or not hasattr(group_data, 'groupMsgs') or not group_data.groupMsgs:
            send_message_with_style(client, "🔴 Không có tin nhắn nào trong nhóm!", thread_id, thread_type, color="#db342e")
            return

        messages = group_data.groupMsgs
        bot_messages = []
        for msg in messages:
            try:
                uid_from = str(msg.get('uidFrom', ''))
                d_name = msg.get('dName', '')
                msg_id = msg.get('msgId')
                cli_msg_id = msg.get('cliMsgId')

                if (uid_from == str(client.bot_id) or uid_from == "0" or d_name == "Bé Bot Của Minh Vũ Shinn Cte") and msg_id and cli_msg_id:
                    bot_messages.append(msg)
            except Exception as e:
                continue

        bot_messages = bot_messages[:count]
        if not bot_messages:
            send_message_with_style(client, "🔴 Không tìm thấy tin nhắn của bot để thu hồi!", thread_id, thread_type, color="#db342e")
            return

        success_count = 0
        for msg in bot_messages:
            try:
                result = client.undoMessage(msg['msgId'], msg['cliMsgId'], thread_id, thread_type)
                success_count += 1
            except ZaloAPIException as e:
                continue
            except Exception as e:
                continue

        color = "#00ff00" if success_count > 0 else "#db342e"
        result_message = f"✅ Đã thu hồi {success_count}/{len(bot_messages)} tin nhắn!" if success_count > 0 else "🔴 Không thể thu hồi tin nhắn!"
        send_message_with_style(client, result_message, thread_id, thread_type, color=color)
        print(result_message)

    except ZaloAPIException as e:
        error_msg = "🔴 Tin nhắn quá cũ, không thể thu hồi!" if e.error_code == 1206 else f"🔴 Lỗi #{e.error_code}: {str(e)}"
        send_message_with_style(client, error_msg, thread_id, thread_type, color="#db342e")
    except Exception as e:
        send_message_with_style(client, f"🔴 Đã xảy ra lỗi: {str(e)}", thread_id, thread_type, color="#db342e")

def handle_undo_command(message, message_object, thread_id, thread_type, author_id, client):
    """Khởi tạo luồng xử lý bot.undo."""
    threading.Thread(
        target=_process_undo_command,
        args=(message, message_object, thread_id, thread_type, author_id, client),
        daemon=True
    ).start()

def get_mitaizl():
    return {
        'bot.undo': handle_undo_command
    }