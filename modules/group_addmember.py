import re
import time
from zlapi.models import Message

des = {
    'tác giả': "Đội ngũ phát triển zlapi",
    'mô tả': "📩 Mời người dùng vào nhiều nhóm chat bằng lệnh addmember.",
    'tính năng': [
        "📌 Mời người dùng vào các nhóm với cú pháp: addmember user_id | group_id1 group_id2 ...",
        "🔒 Chỉ admin trong danh sách ADMIN_IDS được sử dụng lệnh.",
        "👥 Kiểm tra user_id có trong danh sách bạn bè của bot.",
        "⚠️ Kiểm tra nhóm đầy (1000 thành viên) trước khi mời.",
        "⏳ Độ trễ 5 giây giữa các lời mời để tránh giới hạn API.",
        "📊 Báo cáo chi tiết số nhóm mời thành công và thất bại.",
        "✅ Gửi emoji '✅' và thông báo trạng thái xử lý."
    ],
    'hướng dẫn sử dụng': [
        "📝 Gửi lệnh: addmember user_id | group_id1 group_id2 ...",
        "📌 Ví dụ: addmember 123456789 | 987654321 456789123",
        "🔐 Yêu cầu: Phải là admin và user_id là bạn bè của bot.",
        "❌ Nhập sai định dạng hoặc không có quyền sẽ nhận thông báo lỗi.",
        "✅ Nhận báo cáo kết quả sau khi hoàn tất."
    ]
}
# Danh sách admin
ADMIN_IDS = {"3299675674241805615", "5835232686339531421", "3041646020640969809"}

def send_reply_with_style(client, text, message_object, thread_id, thread_type, ttl=None):
    """Gửi tin nhắn phản hồi plain text."""
    msg = Message(text=text)
    client.replyMessage(msg, message_object, thread_id, thread_type, ttl=ttl)

def send_message_with_style(client, text, thread_id, thread_type, ttl=None):
    """Gửi tin nhắn plain text."""
    msg = Message(text=text)
    client.sendMessage(msg, thread_id, thread_type, ttl=ttl)

def validate_user_id_in_friends(client, user_id):
    """Kiểm tra xem user_id có trong danh sách bạn bè của bot không."""
    try:
        friends = client.fetchAllFriends()
        friend_ids = [friend.userId for friend in friends]
        return user_id in friend_ids
    except Exception as e:
        print(f"Lỗi khi kiểm tra danh sách bạn bè: {e}")
        return False

def add_user_to_groups(client, user_id, group_ids, thread_id, thread_type):
    """Mời một người dùng vào danh sách các nhóm được chỉ định."""
    success_count = 0
    failed_groups = []
    max_members = 1000

    for group_id in group_ids:
        try:
            # Kiểm tra số lượng thành viên nhóm
            group_info = client.fetchGroupInfo(group_id)
            print(f"Kết quả API từ fetchGroupInfo cho nhóm {group_id}: {group_info}")  # In kết quả API
            group_info = group_info.gridInfoMap.get(group_id)
            if not group_info:
                failed_groups.append((group_id, "Nhóm không tồn tại hoặc bot không có quyền truy cập."))
                continue
            members = group_info.get('memVerList', [])
            current_members = len(members)
            if current_members >= max_members:
                failed_groups.append((group_id, f"Nhóm đã đầy ({max_members} thành viên)."))
                continue

            # Mời người dùng vào nhóm
            result = client.addUsersToGroup(user_id, group_id)
            print(f"Kết quả API từ addUsersToGroup cho user {user_id} vào nhóm {group_id}: {result}")  # In kết quả API
            success_count += 1
            time.sleep(5)  # Độ trễ 5 giây để tránh giới hạn API
        except Exception as e:
            print(f"Lỗi khi mời user {user_id} vào nhóm {group_id}: {e}")
            failed_groups.append((group_id, str(e)))

    return success_count, failed_groups

def handle_addmember_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh addmember với định dạng: addmember user_id | group_id1 group_id2 ..."""
    # Gửi phản ứng emoji "✅"
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)

    try:
        # Kiểm tra quyền admin
        if author_id not in ADMIN_IDS:
            send_reply_with_style(client, "Bạn không có quyền thực hiện lệnh này.",
                                 message_object, thread_id, thread_type, ttl=30000)
            return

        # Hỗ trợ "addmember" và ",addmember"
        if message.lower().startswith("group.addmember"):
            message_body = message[len("group.addmember"):].strip()
        elif message.lower().startswith(",group.addmember"):
            message_body = message[len(",group.addmember"):].strip()
        else:
            print("Không phải lệnh addmember, bỏ qua.")
            return

        # Kiểm tra dấu "|"
        if "|" not in message_body:
            send_reply_with_style(client, "Vui lòng nhập đúng định dạng: group.addmember user_id | group_id1 group_id2 ...",
                                 message_object, thread_id, thread_type, ttl=30000)
            return

        # Tách user_id và group_ids
        left, right = message_body.split("|", 1)
        user_id = left.strip()
        group_ids = [token for token in right.strip().split() if token.isdigit()]

        # Kiểm tra user_id và group_ids
        if not user_id.isdigit():
            send_reply_with_style(client, "ID người dùng phải là một số hợp lệ!",
                                 message_object, thread_id, thread_type, ttl=30000)
            return
        if not group_ids:
            send_reply_with_style(client, "Không tìm thấy danh sách ID nhóm hợp lệ!",
                                 message_object, thread_id, thread_type, ttl=30000)
            return

        # Kiểm tra user_id trong danh sách bạn bè
        if not validate_user_id_in_friends(client, user_id):
            send_reply_with_style(client, f"ID người dùng {user_id} không phải bạn bè của bot!",
                                 message_object, thread_id, thread_type, ttl=30000)
            return

        # Phản hồi bắt đầu xử lý
        start_msg = f"⏳ Đang mời user {user_id} vào {len(group_ids)} nhóm: {', '.join(group_ids)}"
        send_message_with_style(client, start_msg, thread_id, thread_type, ttl=600000)

        # Xử lý mời đồng bộ
        success_count, failed_groups = add_user_to_groups(client, user_id, group_ids, thread_id, thread_type)

        # Tạo thông báo kết quả
        total_groups = len(group_ids)
        result_msg = (
            f"👥 Tổng số nhóm: {total_groups}\n"
            f"✅ Mời thành công: {success_count}\n"
            f"❌ Mời thất bại: {len(failed_groups)}"
        )
        if failed_groups:
            result_msg += "\n📛 Danh sách nhóm thất bại:\n" + "\n".join([f"Nhóm {gid}: {error}" for gid, error in failed_groups])
        if success_count == total_groups:
            result_msg += "\n🎉 Tất cả lời mời thành công!"

        finish_msg = f"✅✅ Mời user {user_id} hoàn tất:\n{result_msg}"
        send_message_with_style(client, finish_msg, thread_id, thread_type, ttl=600000)

    except Exception as e:
        print(f"Lỗi khi xử lý lệnh addmember: {e}")
        send_reply_with_style(client, f"Lỗi khi xử lý lệnh: {str(e)}",
                             message_object, thread_id, thread_type, ttl=30000)

def get_mitaizl():
    """Trả về dictionary ánh xạ lệnh tới hàm xử lý."""
    return {
        'group.addmember': handle_addmember_command
    }