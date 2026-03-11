from datetime import datetime
import time
import logging
import threading
from zlapi.models import Message, MessageStyle, MultiMsgStyle
from config import ADMIN

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Mời toàn bộ bạn bè của bot vào nhóm trong một luồng riêng, ngoại trừ danh sách ID được chỉ định trên các dòng riêng biệt.",
    'tính năng': [
        "👥 Duyệt qua toàn bộ danh sách bạn bè của bot.",
        "🚀 Tự động mời bạn bè vào nhóm thông qua addUsersToGroup, ngoại trừ các ID được loại trừ.",
        "🔔 Thông báo kết quả sau khi thực hiện mời.",
        "⏱️ Có độ trễ 1 giây giữa các lời mời để tránh bị hạn chế từ server.",
        "🔔 Thông báo khi bắt đầu và hoàn tất mời bạn bè.",
        "🔍 Cho phép chỉ định danh sách ID để loại trừ, mỗi ID trên một dòng.",
        "🧵 Chạy quá trình mời trong một luồng riêng để không chặn bot."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh với cú pháp: bot.invite\n<id1>\n<id2>\n<id3>\n...",
        "✅ Nhận thông báo trạng thái mời thành công, thất bại và danh sách ID được loại trừ."
    ]
}

def send_message_with_style(client, text, thread_id, thread_type, ttl=30000, color="#db342e"):
    """Gửi tin nhắn với định dạng màu sắc và in đậm, TTL mặc định là 30000."""
    logging.info(f"Gửi tin nhắn: {text[:50]}... đến thread_id: {thread_id}")
    base_length = len(text)
    adjusted_length = base_length + 355
    style = MultiMsgStyle([
        MessageStyle(offset=0, length=adjusted_length, style="color", color=color, auto_format=False),
        MessageStyle(offset=0, length=adjusted_length, style="bold", size=" 친구", auto_format=False)
    ])
    msg = Message(text=text, style=style)
    client.sendMessage(msg, thread_id, thread_type, ttl=ttl)

def invite_friends_thread(client, friends, thread_id, member_ids, exclude_ids, max_members, result):
    """Hàm chạy trong luồng riêng để mời bạn bè vào nhóm."""
    skipped_count = 0
    success_count = 0
    failed_count = 0
    failed_ids = []
    excluded_count = 0

    for friend in friends:
        friend_id = friend.userId
        logging.info(f"Xử lý bạn bè với ID: {friend_id}")

        if friend_id in member_ids:
            skipped_count += 1
            logging.info(f"Bỏ qua ID {friend_id}: Đã trong nhóm")
            continue
        if friend_id in exclude_ids:
            excluded_count += 1
            logging.info(f"Bỏ qua ID {friend_id}: Trong danh sách loại trừ")
            continue

        if result['current_members'] + success_count >= max_members:
            logging.warning("Nhóm đã đầy, ngừng mời")
            break

        try:
            client.addUsersToGroup(friend_id, thread_id)
            success_count += 1
            logging.info(f"Mời thành công ID: {friend_id}")
            time.sleep(0.3)  # Độ trễ 1 giây giữa các lời mời
        except Exception as e:
            failed_count += 1
            failed_ids.append(friend_id)
            logging.error(f"Mời thất bại ID {friend_id}: {e}")

    # Lưu kết quả vào từ điển để sử dụng ngoài luồng
    result.update({
        'skipped_count': skipped_count,
        'success_count': success_count,
        'failed_count': failed_count,
        'failed_ids': failed_ids,
        'excluded_count': excluded_count,
        'total_after_invite': result['current_members'] + success_count
    })

def handle_invite_exclude(message, message_object, thread_id, thread_type, author_id, client):
    """Mời tất cả bạn bè vào nhóm, ngoại trừ danh sách ID được chỉ định trên các dòng riêng biệt."""
    logging.info(f"Nhận lệnh từ author_id: {author_id}, tin nhắn: {message}")
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
    
    if author_id not in ADMIN:
        error_message = "Bạn không có quyền sử dụng lệnh này."
        logging.warning(f"Quyền truy cập bị từ chối cho author_id: {author_id}")
        style_error = MultiMsgStyle([
            MessageStyle(offset=0, length=len(error_message), style="color", color="#db342e", auto_format=False),
            MessageStyle(offset=0, length=len(error_message), style="bold", size="16", auto_format=False),
        ])
        client.replyMessage(Message(text=error_message, style=style_error), message_object, thread_id, thread_type, ttl=30000)
        return

    # Tách tin nhắn thành các dòng và lấy danh sách ID loại trừ
    lines = message.strip().split('\n')
    logging.info(f"Dòng tin nhắn nhận được: {lines}")
    if not lines or lines[0].strip().lower() != 'bot.invite':
        error_message = "Cú pháp không hợp lệ. Vui lòng sử dụng: bot.invite\n<id1>\n<id2>\n..."
        logging.error(f"Cú pháp không hợp lệ: {lines[0] if lines else 'Không có dòng nào'}")
        send_message_with_style(client, error_message, thread_id, thread_type, color="#ff0000")
        return

    exclude_ids = set(line.strip() for line in lines[1:] if line.strip())
    logging.info(f"Danh sách ID loại trừ: {exclude_ids}")
    
    if not exclude_ids:
        warning_msg = "Không có ID nào được chỉ định để loại trừ. Bot sẽ mời tất cả bạn bè."
        logging.info(warning_msg)
        send_message_with_style(client, warning_msg, thread_id, thread_type, color="#FFA500", ttl=600000)

    start_msg = "⏳ Đang bắt đầu mời tất cả bạn bè vào nhóm (ngoại trừ các ID được chỉ định). Vui lòng chờ..."
    send_message_with_style(client, start_msg, thread_id, thread_type, color="#FFA500", ttl=600000)

    try:
        friends = client.fetchAllFriends()
        logging.info(f"Tổng số bạn bè lấy được: {len(friends)}")
        group_info = client.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
        members = group_info.get('memVerList', [])
        member_ids = set(members)
        current_members = len(member_ids)
        max_members = 2000
        logging.info(f"Thành viên nhóm hiện tại: {current_members}, giới hạn: {max_members}")
    except Exception as e:
        error_msg = f"Đã xảy ra lỗi khi lấy danh sách: {e}"
        logging.error(error_msg)
        send_message_with_style(client, error_msg, thread_id, thread_type)
        return

    total_friends = len(friends)
    result = {'current_members': current_members}  # Từ điển để lưu kết quả từ luồng

    # Tạo và chạy luồng riêng để mời bạn bè
    invite_thread = threading.Thread(
        target=invite_friends_thread,
        args=(client, friends, thread_id, member_ids, exclude_ids, max_members, result)
    )
    invite_thread.start()

    # Chờ luồng hoàn tất và lấy kết quả
    invite_thread.join()

    # Lấy kết quả từ từ điển
    skipped_count = result.get('skipped_count', 0)
    success_count = result.get('success_count', 0)
    failed_count = result.get('failed_count', 0)
    failed_ids = result.get('failed_ids', [])
    excluded_count = result.get('excluded_count', 0)
    total_after_invite = result.get('total_after_invite', current_members)

    result_msg = (
        f"👥 Tổng số bạn bè: {total_friends}\n"
        f"👤 Thành viên nhóm hiện tại: {current_members} ➜ {total_after_invite}\n"
        f"⏭️ Đã trong nhóm (bỏ qua): {skipped_count}\n"
        f"🚫 Đã loại trừ: {excluded_count}\n"
        f"✅ Mời thành công: {success_count}\n"
        f"❌ Mời thất bại: {failed_count}"
    )
    if total_after_invite >= max_members:
        result_msg += f"\n🚫 Nhóm đã đạt giới hạn {max_members} thành viên."

    if failed_ids:
        result_msg += f"\n📛 Danh sách ID thất bại: {', '.join(map(str, failed_ids))}"

    if exclude_ids:
        result_msg += f"\n📌 Danh sách ID loại trừ: {', '.join(map(str, exclude_ids))}"

    finish_msg = f"✅✅ Mời bạn bè vào nhóm hoàn tất:\n{result_msg}"
    logging.info("Gửi thông báo kết quả cuối cùng")
    send_message_with_style(client, finish_msg, thread_id, thread_type, color="#000000", ttl=600000)

def get_mitaizl():
    """Trả về mapping các lệnh của bot."""
    return {
        'bot.invite': handle_invite_exclude
    }