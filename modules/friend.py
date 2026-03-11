from zlapi.models import Message, MessageStyle, MultiMsgStyle
from config import ADMIN
import time
import json
import os
from datetime import datetime


des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Quản lý kết bạn: gửi lời mời, chấp nhận, xóa kết bạn, xem danh sách bạn bè và cập nhật danh sách lời mời.",
    'tính năng': [
        "🤖 Gửi lời mời kết bạn tới một hoặc nhiều người dùng (@user hoặc user_id).",
        "✅ Chấp nhận lời mời kết bạn từ một hoặc nhiều người dùng.",
        "🗑️ Xóa kết bạn với một hoặc nhiều người dùng.",
        "📩 Báo cáo chi tiết: đã là bạn bè, đã gửi lời mời trước, hoặc gửi kết bạn thành công.",
        "🔒 Kiểm tra tag hoặc ID hợp lệ trước khi gửi lời mời kết bạn.",
        "🎨 Tin nhắn phản hồi có màu sắc và định dạng in đậm.",
        "⏳ Thêm độ trễ tùy chỉnh và tự động điều chỉnh khi bị giới hạn.",
        "📑 Lưu tiến trình gửi lời mời vào file JSON để tránh trùng lặp.",
        "🔍 Kiểm tra trạng thái bạn bè trước khi thực hiện hành động.",
        "🔄 Cập nhật danh sách bạn bè và xóa người dùng đã là bạn bè khỏi danh sách lời mời, hiển thị danh sách bạn mới.",
        "📋 Xem danh sách bạn bè với định dạng số thứ tự, tên và ID, chia thành nhiều tin nhắn nếu dài."
    ],
    'hướng dẫn sử dụng': [
        "💬 Nhập `bot.addfri @user1 @user2 ...` hoặc `bot.addfri id1 id2 ...` để gửi lời mời kết bạn.",
        "💬 Nhập `bot.okfri @user1 @user2 ...` hoặc `bot.okfri id1 id2 ...` để chấp nhận lời mời kết bạn.",
        "💬 Nhập `bot.delfri @user1 @user2 ...` hoặc `bot.delfri id1 id2 ...` để xóa kết bạn.",
        "💬 Nhập `bot.friupdate` để cập nhật danh sách bạn bè và file JSON lời mời, hiển thị danh sách bạn mới.",
        "💬 Nhập `bot.filist` để xem danh sách bạn bè (số thứ tự, tên, ID).",
        "⚙️ Tùy chọn: `--delay=<giây>` (độ trễ), `--max=<số_lượng>` (số người tối đa).",
        "⚠️ Chỉ quản trị viên mới có thể sử dụng các lệnh này."
    ]
}

def send_reply_with_style(client, text, message_object, thread_id, thread_type, ttl=60000, color="#db342e"):
    """Gửi tin nhắn phản hồi với định dạng màu sắc và in đậm."""
    base_length = len(text)
    adjusted_length = base_length + 355
    style = MultiMsgStyle([
        MessageStyle(offset=0, length=adjusted_length, style="color", color=color, auto_format=False),
        MessageStyle(offset=0, length=adjusted_length, style="bold", size="8", auto_format=False)
    ])
    msg = Message(text=text, style=style)
    client.replyMessage(msg, message_object, thread_id, thread_type, ttl=ttl)

def send_long_message(client, text, message_object, thread_id, thread_type, color="#db342e", max_length=1500, delay=5):
    """Nếu nội dung quá dài, chia thành nhiều phần và gửi với thời gian trễ giữa các phần."""
    chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
    for chunk in chunks:
        send_reply_with_style(client, chunk, message_object, thread_id, thread_type, color=color, ttl=60000)
        time.sleep(delay)

def is_admin(author_id):
    return author_id in ADMIN

def load_sent_requests():
    """Tải danh sách user_id đã gửi lời mời từ file JSON."""
    try:
        if os.path.exists("sent_requests.json"):
            with open("sent_requests.json", "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"⚠️ Lỗi khi tải sent_requests.json: {str(e)}")
        return {}

def save_sent_requests(sent_requests):
    """Lưu danh sách user_id đã gửi lời mời vào file JSON."""
    try:
        with open("sent_requests.json", "w", encoding="utf-8") as f:
            json.dump(sent_requests, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"⚠️ Lỗi khi lưu sent_requests.json: {str(e)}")

def is_friend(client, user_id):
    """Kiểm tra xem user_id đã là bạn bè hay chưa."""
    try:
        friends = client.fetchAllFriends()
        return any(friend.userId == user_id for friend in friends)
    except Exception as e:
        print(f"⚠️ Lỗi khi kiểm tra trạng thái bạn bè: {str(e)}")
        return False

def get_user_name(client, user_id):
    """Lấy tên người dùng từ user_id."""
    try:
        info_response = client.fetchUserInfo(user_id)
        profiles = info_response.unchanged_profiles or info_response.changed_profiles
        info = profiles.get(str(user_id))
        return info.zaloName if hasattr(info, 'zaloName') and info.zaloName else "Người dùng không xác định"
    except Exception as e:
        print(f"⚠️ Lỗi khi lấy thông tin người dùng {user_id}: {str(e)}")
        return "Người dùng không xác định"

def parse_command_options(command_parts):
    """Phân tích các tùy chọn từ lệnh (delay, max)."""
    delay = 1.0
    max_members = float('inf')
    for part in command_parts:
        if part.startswith('--delay='):
            try:
                delay = float(part.split('=')[1])
            except ValueError:
                pass
        if part.startswith('--max='):
            try:
                max_members = int(part.split('=')[1])
            except ValueError:
                pass
    return delay, max_members

def generate_simple_report(successful, already_friends, already_sent, action_type):
    """Tạo báo cáo chi tiết liệt kê tên người dùng theo trạng thái."""
    report_lines = []
    if already_friends:
        report_lines.append("👥 Đã là bạn bè: " + " ".join(name for _, name in already_friends))
    if already_sent:
        report_lines.append("📩 Đã gửi lời mời trước đó: " + " ".join(name for _, name in already_sent))
    if successful:
        report_lines.append("✅ Đã gửi kết bạn thành công: " + " ".join(name for _, name in successful))
    if not (successful or already_friends or already_sent):
        return f"❌ Không có {action_type} nào thành công."
    return "\n".join(report_lines)

def handle_add_friend_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh bot.addfri để gửi lời mời kết bạn."""
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
    
    if not is_admin(author_id):
        action = "🚫 Bạn không có quyền sử dụng lệnh này!"
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
        send_reply_with_style(client, action, message_object, thread_id, thread_type)
        return

    command_parts = message.strip().split()
    mentions = getattr(message_object, 'mentions', None)
    target_users = []

    # Lấy danh sách user_id từ mentions hoặc command_parts
    if mentions and len(mentions) > 0:
        target_users = [mention['uid'] for mention in mentions]
    elif len(command_parts) > 1:
        target_users = [part for part in command_parts[1:] if not part.startswith('--')]

    # Kiểm tra xem target_users có rỗng hoặc chứa phần tử không hợp lệ
    if not target_users:
        error_message = "❌ Vui lòng tag người dùng hoặc nhập ID hợp lệ! Cú pháp: bot.addfri @user1 @user2 ... hoặc bot.addfri id1 id2 ..."
        send_reply_with_style(client, error_message, message_object, thread_id, thread_type)
        client.sendReaction(message_object, "⚠️", thread_id, thread_type, reactionType=75)
        return

    # Kiểm tra xem tất cả target_users có phải là dãy số hợp lệ (ID) nếu không có mentions
    if not mentions:
        for user_id in target_users:
            if not user_id.isdigit():
                error_message = "❌ Vui lòng tag người dùng hoặc nhập ID hợp lệ! Cú pháp: bot.addfri @user1 @user2 ... hoặc bot.addfri id1 id2 ..."
                send_reply_with_style(client, error_message, message_object, thread_id, thread_type)
                client.sendReaction(message_object, "⚠️", thread_id, thread_type, reactionType=75)
                return

    delay, max_members = parse_command_options(command_parts)
    sent_requests = load_sent_requests()
    successful_requests = []
    already_friends = []
    already_sent = []

    for user_id in target_users[:min(len(target_users), max_members)]:
        user_name = get_user_name(client, user_id)
        if is_friend(client, user_id):
            already_friends.append((user_id, user_name))
            if user_id in sent_requests:
                del sent_requests[user_id]
                print(f"🔄 {user_name} ({user_id}) đã là bạn bè, xóa khỏi sent_requests.json.")
            continue
        if user_id in sent_requests:
            already_sent.append((user_id, user_name))
            print(f"⏭️ Bỏ qua {user_name} ({user_id}): Đã gửi lời mời trước đó.")
            continue

        try:
            friend_request_message = f"Xin chào {user_name} ĐỒNG Ý KB IK"
            client.sendFriendRequest(userId=user_id, msg=friend_request_message)
            successful_requests.append((user_id, user_name))
            sent_requests[user_id] = datetime.now().isoformat()
            print(f"✔️ Đã gửi lời mời kết bạn đến: {user_name} ({user_id})")
        except Exception as e:
            print(f"❌ Lỗi khi gửi lời mời đến {user_id}: {str(e)}")
            if "rate limit" in str(e).lower() or "too many requests" in str(e).lower():
                delay = min(delay * 2, 10.0)
                print(f"⚠️ Phát hiện rate limit, tăng độ trễ lên {delay} giây.")
                time.sleep(60)
            elif is_friend(client, user_id):
                already_friends.append((user_id, user_name))
                print(f"🔄 {user_name} ({user_id}) đã là bạn bè, sẽ cập nhật sent_requests.json.")
                if user_id in sent_requests:
                    del sent_requests[user_id]
        time.sleep(delay)

    save_sent_requests(sent_requests)
    report = generate_simple_report(successful_requests, already_friends, already_sent, "gửi kết bạn")
    send_reply_with_style(client, report, message_object, thread_id, thread_type)
    client.sendReaction(message_object, "🎉", thread_id, thread_type, reactionType=75)

def handle_accept_friend_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh bot.okfri để chấp nhận lời mời kết bạn."""
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)

    if not is_admin(author_id):
        action = "🚫 Bạn không có quyền sử dụng lệnh này!"
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
        send_reply_with_style(client, action, message_object, thread_id, thread_type)
        return

    command_parts = message.strip().split()
    mentions = getattr(message_object, 'mentions', None)
    target_users = []

    if mentions and len(mentions) > 0:
        target_users = [mention['uid'] for mention in mentions]
    elif len(command_parts) > 1:
        target_users = [part for part in command_parts[1:] if not part.startswith('--')]

    if not target_users:
        error_message = "❌ Vui lòng cung cấp ít nhất một @user hoặc user_id! Cú pháp: bot.okfri @user1 @user2 ... hoặc bot.okfri id1 id2 ..."
        send_reply_with_style(client, error_message, message_object, thread_id, thread_type)
        client.sendReaction(message_object, "⚠️", thread_id, thread_type, reactionType=75)
        return

    delay, max_members = parse_command_options(command_parts)
    successful_requests = []

    for user_id in target_users[:min(len(target_users), max_members)]:
        try:
            user = client.acceptFriendRequest(userId=user_id, language="vi")
            user_name = user.zaloName if user and hasattr(user, 'zaloName') else "Người dùng không xác định"
            successful_requests.append((user_id, user_name))
            print(f"✔️ Đã chấp nhận lời mời kết bạn từ: {user_name} ({user_id})")
        except Exception as e:
            print(f"❌ Lỗi khi chấp nhận lời mời từ {user_id}: {str(e)}")
            if "rate limit" in str(e).lower() or "too many requests" in str(e).lower():
                delay = min(delay * 2, 10.0)
                print(f"⚠️ Phát hiện rate limit, tăng độ trễ lên {delay} giây.")
                time.sleep(60)
        time.sleep(delay)

    report = generate_simple_report(successful_requests, [], [], "chấp nhận kết bạn")
    send_reply_with_style(client, report, message_object, thread_id, thread_type)
    client.sendReaction(message_object, "🎉", thread_id, thread_type, reactionType=75)

def handle_delete_friend_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh bot.delfri để xóa kết bạn."""
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)

    if not is_admin(author_id):
        action = "🚫 Bạn không có quyền sử dụng lệnh này!"
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
        send_reply_with_style(client, action, message_object, thread_id, thread_type)
        return

    command_parts = message.strip().split()
    mentions = getattr(message_object, 'mentions', None)
    target_users = []

    if mentions and len(mentions) > 0:
        target_users = [mention['uid'] for mention in mentions]
    elif len(command_parts) > 1:
        target_users = [part for part in command_parts[1:] if not part.startswith('--')]

    if not target_users:
        error_message = "❌ Vui lòng cung cấp ít nhất một @user hoặc user_id! Cú pháp: bot.delfri @user1 @user2 ... hoặc bot.delfri id1 id2 ..."
        send_reply_with_style(client, error_message, message_object, thread_id, thread_type)
        client.sendReaction(message_object, "⚠️", thread_id, thread_type, reactionType=75)
        return

    delay, max_members = parse_command_options(command_parts)
    successful_requests = []

    for user_id in target_users[:min(len(target_users), max_members)]:
        if not is_friend(client, user_id):
            print(f"⏭️ Bỏ qua {user_id}: Không phải bạn bè.")
            continue

        try:
            client.unfriendUser(userId=user_id, language="vi")
            user_name = get_user_name(client, user_id)
            successful_requests.append((user_id, user_name))
            print(f"✔️ Đã xóa kết bạn với: {user_name} ({user_id})")
        except Exception as e:
            print(f"❌ Lỗi khi xóa kết bạn với {user_id}: {str(e)}")
            if "rate limit" in str(e).lower() or "too many requests" in str(e).lower():
                delay = min(delay * 2, 10.0)
                print(f"⚠️ Phát hiện rate limit, tăng độ trễ lên {delay} giây.")
                time.sleep(60)
        time.sleep(delay)

    report = generate_simple_report(successful_requests, [], [], "hủy kết bạn")
    send_reply_with_style(client, report, message_object, thread_id, thread_type)
    client.sendReaction(message_object, "🎉", thread_id, thread_type, reactionType=75)

def handle_update_friend_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh bot.friupdate để cập nhật danh sách bạn bè và file JSON sent_requests.json."""
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)

    if not is_admin(author_id):
        action = "🚫 Bạn không có quyền sử dụng lệnh này!"
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
        send_reply_with_style(client, action, message_object, thread_id, thread_type)
        return

    sent_requests = load_sent_requests()
    if not sent_requests:
        report = "📋 Không có lời mời kết bạn nào trong danh sách để cập nhật."
        send_reply_with_style(client, report, message_object, thread_id, thread_type)
        client.sendReaction(message_object, "ℹ️", thread_id, thread_type, reactionType=75)
        return

    try:
        friends = client.fetchAllFriends()
        friend_ids = {friend.userId for friend in friends}
    except Exception as e:
        error_msg = f"❌ Đã xảy ra lỗi khi lấy danh sách bạn bè: {str(e)}"
        send_reply_with_style(client, error_msg, message_object, thread_id, thread_type)
        client.sendReaction(message_object, "⚠️", thread_id, thread_type, reactionType=75)
        return

    updated_count = 0
    new_friends = []
    for user_id in list(sent_requests.keys()):
        if user_id in friend_ids:
            user_name = get_user_name(client, user_id)
            new_friends.append(user_name)
            del sent_requests[user_id]
            print(f"✔️ Đã xóa {user_name} ({user_id}) khỏi danh sách lời mời vì đã là bạn bè.")
            updated_count += 1

    save_sent_requests(sent_requests)
    report = f"✅ Đã cập nhật danh sách bạn bè. Xóa {updated_count} người dùng đã là bạn bè khỏi sent_requests.json."
    if new_friends:
        report += "\n\nDanh sách bạn mới:\n"
        for i, name in enumerate(new_friends, 1):
            report += f"{i}. {name}\n"
    send_long_message(client, report, message_object, thread_id, thread_type, color="#db342e", max_length=1500, delay=5)
    client.sendReaction(message_object, "🎉", thread_id, thread_type, reactionType=75)

def handle_list_friends_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh bot.filist để hiển thị danh sách bạn bè với định dạng: 1. {tên} ID: {user_id}."""
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)

    if not is_admin(author_id):
        action = "🚫 Bạn không có quyền sử dụng lệnh này!"
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
        send_reply_with_style(client, action, message_object, thread_id, thread_type)
        return

    try:
        friends = client.fetchAllFriends()
        total_friends = len(friends)
    except Exception as e:
        error_msg = f"❌ Đã xảy ra lỗi khi lấy danh sách bạn bè: {str(e)}"
        send_reply_with_style(client, error_msg, message_object, thread_id, thread_type)
        client.sendReaction(message_object, "⚠️", thread_id, thread_type, reactionType=75)
        return

    if total_friends == 0:
        report = "📋 Danh sách bạn bè trống."
        send_reply_with_style(client, report, message_object, thread_id, thread_type)
        client.sendReaction(message_object, "ℹ️", thread_id, thread_type, reactionType=75)
        return

    msg = f"DANH SÁCH BẠN BÈ:\nTổng số bạn bè: {total_friends}\n\n"
    count = 1
    for friend in friends:
        friend_name = friend.zaloName[:30] + "..." if len(friend.zaloName) > 30 else friend.zaloName
        friend_id = friend.userId
        msg += f"{count}. {friend_name}\nID: {friend_id}\n\n"
        count += 1

    send_long_message(client, msg, message_object, thread_id, thread_type, color="#db342e", max_length=1500, delay=5)
    client.sendReaction(message_object, "🎉", thread_id, thread_type, reactionType=75)

def handle_list_sent_requests_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh bot.sentlist để hiển thị danh sách lời mời kết bạn đã gửi."""
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)

    if not is_admin(author_id):
        action = "🚫 Bạn không có quyền sử dụng lệnh này!"
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
        send_reply_with_style(client, action, message_object, thread_id, thread_type)
        return

    sent_requests = load_sent_requests()
    if not sent_requests:
        report = "📋 Danh sách lời mời kết bạn đã gửi trống."
        send_reply_with_style(client, report, message_object, thread_id, thread_type)
        client.sendReaction(message_object, "ℹ️", thread_id, thread_type, reactionType=75)
        return

    msg = f"DANH SÁCH LỜI MỜI ĐÃ GỬI:\nTổng số lời mời: {len(sent_requests)}\n\n"
    count = 1
    for user_id, timestamp in sent_requests.items():
        user_name = get_user_name(client, user_id)
        try:
            time_sent = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            time_sent = "Thời gian không xác định"
        msg += f"{count}. {user_name}\nID: {user_id}\nThời gian gửi: {time_sent}\n\n"
        count += 1

    send_long_message(client, msg, message_object, thread_id, thread_type, color="#db342e", max_length=1500, delay=5)
    client.sendReaction(message_object, "🎉", thread_id, thread_type, reactionType=75)

def handle_cancel_friend_request_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh bot.cancelfri để hủy lời mời kết bạn đã gửi."""
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)

    if not is_admin(author_id):
        action = "🚫 Bạn không có quyền sử dụng lệnh này!"
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
        send_reply_with_style(client, action, message_object, thread_id, thread_type)
        return

    command_parts = message.strip().split()
    mentions = getattr(message_object, 'mentions', None)
    target_users = []

    if mentions and len(mentions) > 0:
        target_users = [mention['uid'] for mention in mentions]
    elif len(command_parts) > 1:
        target_users = [part for part in command_parts[1:] if not part.startswith('--')]

    if not target_users:
        error_message = "❌ Vui lòng cung cấp ít nhất một @user hoặc user_id! Cú pháp: bot.cancelfri @user1 @user2 ... hoặc bot.cancelfri id1 id2 ..."
        send_reply_with_style(client, error_message, message_object, thread_id, thread_type)
        client.sendReaction(message_object, "⚠️", thread_id, thread_type, reactionType=75)
        return

    delay, max_members = parse_command_options(command_parts)
    sent_requests = load_sent_requests()
    successful_requests = []
    not_sent = []

    for user_id in target_users[:min(len(target_users), max_members)]:
        if user_id not in sent_requests:
            user_name = get_user_name(client, user_id)
            not_sent.append((user_id, user_name))
            print(f"⏭️ Bỏ qua {user_name} ({user_id}): Không có trong danh sách lời mời đã gửi.")
            continue

        try:
            # Giả sử client có phương thức cancelFriendRequest để hủy lời mời
            client.cancelFriendRequest(userId=user_id, language="vi")
            user_name = get_user_name(client, user_id)
            successful_requests.append((user_id, user_name))
            del sent_requests[user_id]
            print(f"✔️ Đã hủy lời mời kết bạn tới: {user_name} ({user_id})")
        except Exception as e:
            print(f"❌ Lỗi khi hủy lời mời tới {user_id}: {str(e)}")
            if "rate limit" in str(e).lower() or "too many requests" in str(e).lower():
                delay = min(delay * 2, 10.0)
                print(f"⚠️ Phát hiện rate limit, tăng độ trễ lên {delay} giây.")
                time.sleep(60)
        time.sleep(delay)

    save_sent_requests(sent_requests)
    report_lines = []
    if not_sent:
        report_lines.append("🚫 Không có trong danh sách lời mời: " + " ".join(name for _, name in not_sent))
    if successful_requests:
        report_lines.append("✅ Đã hủy lời mời thành công: " + " ".join(name for _, name in successful_requests))
    if not (successful_requests or not_sent):
        report = "❌ Không có lời mời nào được hủy."
    else:
        report = "\n".join(report_lines)

    send_reply_with_style(client, report, message_object, thread_id, thread_type)
    client.sendReaction(message_object, "🎉", thread_id, thread_type, reactionType=75)
    
def handle_reset_sent_requests_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh bot.resetsentlist để đặt lại danh sách lời mời đã gửi."""
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)

    if not is_admin(author_id):
        action = "🚫 Bạn không có quyền sử dụng lệnh này!"
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
        send_reply_with_style(client, action, message_object, thread_id, thread_type)
        return

    try:
        # Ghi đè file sent_requests.json với nội dung rỗng
        with open("sent_requests.json", "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
        report = "✅ Đã đặt lại danh sách lời mời kết bạn. File sent_requests.json đã được xóa toàn bộ."
        print("✔️ Đã đặt lại sent_requests.json thành rỗng.")
    except Exception as e:
        report = f"❌ Lỗi khi đặt lại danh sách lời mời: {str(e)}"
        print(f"⚠️ Lỗi khi đặt lại sent_requests.json: {str(e)}")
    
    send_reply_with_style(client, report, message_object, thread_id, thread_type)
    client.sendReaction(message_object, "🎉", thread_id, thread_type, reactionType=75)
    
def get_mitaizl():
    """Trả về mapping các lệnh của bot."""
    return {
        'bot.addfri': handle_add_friend_command,
        'bot.okfri': handle_accept_friend_command,
        'bot.delfri': handle_delete_friend_command,
        'bot.friupdate': handle_update_friend_command,
        'bot.frilist': handle_list_friends_command,
        'bot.sentlist': handle_list_sent_requests_command,
        'bot.cancelfri': handle_cancel_friend_request_command,
        'bot.rssentlist': handle_reset_sent_requests_command
    }