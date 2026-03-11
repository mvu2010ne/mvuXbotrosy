from datetime import datetime
import time
from zlapi.models import Message, MessageStyle, MultiMsgStyle
from config import ADMIN
des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Mời toàn bộ bạn bè của bot vào nhóm",
    'tính năng': [
        "👥 Duyệt qua toàn bộ danh sách bạn bè của bot.",
        "🚀 Tự động mời bạn bè vào nhóm thông qua addUsersToGroup.",
        "🔔 Thông báo kết quả sau khi thực hiện mời.",
        "⏱️ Có độ trễ 0.5 giây giữa các lời mời để tránh bị hạn chế từ server.",
        "🔔 Thông báo khi bắt đầu và hoàn tất mời bạn bè."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh bot.inviteall để mời tất cả bạn bè của bot vào nhóm.",
        "✅ Nhận thông báo trạng thái mời thành công và thất bại."
    ]
}

def send_message_with_style(client, text, thread_id, thread_type, ttl=30000, color="#db342e"):
    """Gửi tin nhắn với định dạng màu sắc và in đậm, TTL mặc định là 30000."""
    base_length = len(text)
    adjusted_length = base_length + 355  # Tăng độ dài để đảm bảo style được áp dụng đầy đủ
    style = MultiMsgStyle([
        MessageStyle(offset=0, length=adjusted_length, style="color", color=color, auto_format=False),
        MessageStyle(offset=0, length=adjusted_length, style="bold", size="8", auto_format=False)
    ])
    msg = Message(text=text, style=style)
    client.sendMessage(msg, thread_id, thread_type, ttl=ttl)

def handle_invite_all(message, message_object, thread_id, thread_type, author_id, client):
    """Duyệt qua toàn bộ danh sách bạn bè của bot và mời họ vào nhóm."""
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
    if author_id not in ADMIN:
        error_message = "Bạn không có quyền sử dụng lệnh này."
        style_error = MultiMsgStyle([
            MessageStyle(offset=0, length=len(error_message), style="color", color="#db342e", auto_format=False),
            MessageStyle(offset=0, length=len(error_message), style="bold", size="16", auto_format=False),
        ])
        client.replyMessage(Message(text=error_message, style=style_error), message_object, thread_id, thread_type, ttl=30000)
        return

    start_msg = "⏳ Đang bắt đầu mời tất cả bạn bè vào nhóm. Vui lòng chờ..."
    send_message_with_style(client, start_msg, thread_id, thread_type, color="#FFA500", ttl=600000)

    try:
        friends = client.fetchAllFriends()
        group_info = client.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
        members = group_info.get('memVerList', [])
        member_ids = set(members)
        current_members = len(member_ids)
        max_members = 1000  # Số lượng tối đa của nhóm
    except Exception as e:
        error_msg = f"Đã xảy ra lỗi khi lấy danh sách: {e}"
        send_message_with_style(client, error_msg, thread_id, thread_type)
        return

    total_friends = len(friends)
    skipped_count = 0
    success_count = 0
    failed_count = 0
    failed_ids = []

    for friend in friends:
        friend_id = friend.userId

        if friend_id in member_ids:
            skipped_count += 1
            continue  # Bỏ qua ngay, không chờ

        if current_members + success_count >= max_members:
            break  # Nhóm đầy, ngừng mời

        try:
            client.addUsersToGroup(friend_id, thread_id)
            success_count += 1
            time.sleep(5)  # Chờ giữa các lời mời để tránh bị chặn
        except Exception as e:
            failed_count += 1
            failed_ids.append(friend_id)

    total_after_invite = current_members + success_count

    result_msg = (
        f"👥 Tổng số bạn bè: {total_friends}\n"
        f"👤 Thành viên nhóm hiện tại: {current_members} ➜ {total_after_invite}\n"
        f"⏭️ Đã trong nhóm (bỏ qua): {skipped_count}\n"
        f"✅ Mời thành công: {success_count}\n"
        f"❌ Mời thất bại: {failed_count}"
    )
    if total_after_invite >= max_members:
        result_msg += f"\n🚫 Nhóm đã đạt giới hạn {max_members} thành viên."

    if failed_ids:
        result_msg += f"\n📛 Danh sách ID thất bại: {', '.join(map(str, failed_ids))}"

    finish_msg = f"✅✅ Mời bạn bè vào nhóm hoàn tất:\n{result_msg}"
    send_message_with_style(client, finish_msg, thread_id, thread_type, color="#000000", ttl=600000)

def get_mitaizl():
    """Trả về mapping các lệnh của bot."""
    return {
        'bot.inviteall': handle_invite_all
    }
