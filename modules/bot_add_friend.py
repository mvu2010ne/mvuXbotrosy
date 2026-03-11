import time
import json
import os
from datetime import datetime
from zlapi.models import Message, MessageStyle, MultiMsgStyle
from config import ADMIN


des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Gửi lời mời kết bạn đến tất cả thành viên trong nhóm, một người dùng cụ thể, hoặc những người được gắn thẻ.",
    'tính năng': [
        "🤖 Tự động gửi lời mời kết bạn cho tất cả thành viên trong nhóm, một người cụ thể, hoặc người được gắn thẻ (@user).",
        "📩 Hiển thị số lượng lời mời đã gửi thành công và thất bại.",
        "🎨 Tin nhắn phản hồi có màu sắc và định dạng in đậm.",
        "⏳ Thêm độ trễ tùy chỉnh và tự động điều chỉnh khi bị giới hạn.",
        "📑 Lưu tiến trình gửi lời mời vào file JSON để tiếp tục nếu bị gián đoạn.",
        "🔍 Kiểm tra trạng thái bạn bè để tránh gửi trùng lặp.",
        "🛑 Dừng tiến trình gửi lời mời cho nhóm với lệnh bot.cancelrequest.",
        "📊 Báo cáo chi tiết với tên người dùng thay vì ID, chia thành nhiều tin nhắn nếu quá dài."
    ],
    'hướng dẫn sử dụng': [
        "💬 Nhập `bot.addfriend` để gửi lời mời cho tất cả thành viên trong nhóm.",
        "📌 Nhập `bot.addfriend <user_id>` để gửi lời mời cho một người cụ thể.",
        "📌 Nhập `bot.addfriend @user1 @user2 ...` để gửi lời mời cho những người được gắn thẻ.",
        "⚙️ Tùy chọn: `--delay=<giây>` (độ trễ), `--max=<số_lượng>` (số thành viên tối đa).",
        "🛑 Nhập `bot.cancelrequest` để dừng tiến trình gửi lời mời kết bạn cho nhóm.",
        "⚠️ Chỉ quản trị viên mới có thể sử dụng lệnh này.",
        "📝 Lưu ý: Báo cáo dài sẽ được chia thành nhiều tin nhắn."
    ]
}

def send_message_with_style(client, text, thread_id, thread_type, ttl=60000, color="#db342e"):
    """Gửi tin nhắn với định dạng màu sắc và font chữ."""
    base_length = len(text)
    adjusted_length = base_length + 355
    style = MultiMsgStyle([
        MessageStyle(offset=0, length=adjusted_length, style="color", color=color, auto_format=False),
        MessageStyle(offset=0, length=adjusted_length, style="font", size="6", auto_format=False)
    ])
    msg = Message(text=text, style=style)
    client.send(msg, thread_id, thread_type, ttl=ttl)

def send_reply_with_style(client, text, message_object, thread_id, thread_type, ttl=60000, color="#db342e"):
    """Gửi tin nhắn phản hồi với định dạng màu sắc và font chữ."""
    base_length = len(text)
    adjusted_length = base_length + 355
    style = MultiMsgStyle([
        MessageStyle(offset=0, length=adjusted_length, style="color", color=color, auto_format=False),
        MessageStyle(offset=0, length=adjusted_length, style="font", size="6", auto_format=False)
    ])
    msg = Message(text=text, style=style)
    client.replyMessage(msg, message_object, thread_id, thread_type, ttl=ttl)

def send_long_message(client, text, thread_id, thread_type, color="#000000", max_length=1500, delay=2):
    """Chia tin nhắn dài thành nhiều phần và gửi với độ trễ."""
    chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
    total_parts = len(chunks)
    for idx, chunk in enumerate(chunks, 1):
        part_message = f"📄 Phần {idx}/{total_parts}\n{chunk}" if total_parts > 1 else chunk
        send_message_with_style(client, part_message, thread_id, thread_type, color)
        if idx < total_parts:
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
    """Lấy tên người dùng từ user_id, sử dụng logic từ bot_friend_list.py."""
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

def load_cancel_signal():
    """Tải tín hiệu dừng từ file JSON."""
    try:
        if os.path.exists("cancel_signal.json"):
            with open("cancel_signal.json", "r", encoding="utf-8") as f:
                return json.load(f).get("cancel", False)
        return False
    except Exception as e:
        print(f"⚠️ Lỗi khi tải cancel_signal.json: {str(e)}")
        return False

def save_cancel_signal(cancel):
    """Lưu tín hiệu dừng vào file JSON."""
    try:
        with open("cancel_signal.json", "w", encoding="utf-8") as f:
            json.dump({"cancel": cancel}, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"⚠️ Lỗi khi lưu cancel_signal.json: {str(e)}")

def send_friend_requests_in_batches(client, members, thread_id, thread_type, batch_size=50, delay=1.0, max_members=float('inf')):
    """Gửi lời mời kết bạn theo lô với độ trễ và giới hạn số lượng, hỗ trợ dừng tiến trình."""
    sent_requests = load_sent_requests()
    successful_requests = []  # Lưu (user_id, user_name)
    failed_requests = []     # Lưu (user_id, user_name, reason)
    total_members = min(len(members), max_members)
    
    for i in range(0, total_members, batch_size):
        # Kiểm tra tín hiệu dừng trước khi xử lý lô mới
        if load_cancel_signal():
            print(f"🛑 Tiến trình gửi lời mời kết bạn đã bị dừng tại lô {i//batch_size + 1}.")
            break
        
        batch = members[i:min(i + batch_size, total_members)]
        for mem in batch:
            user_id = mem.split('_')[0] if isinstance(mem, str) else mem
            if user_id in sent_requests or is_friend(client, user_id):
                user_name = get_user_name(client, user_id)
                failed_requests.append((user_id, user_name, "Đã gửi lời mời hoặc đã là bạn bè"))
                print(f"⏭️ Bỏ qua {user_id}: Đã gửi lời mời hoặc đã là bạn bè.")
                continue
            
            try:
                user_name = get_user_name(client, user_id)
                friend_request_message = f"Hi {user_name} chơi Liên quân thì add mình với nha ❤"
                
                client.sendFriendRequest(userId=user_id, msg=friend_request_message)
                successful_requests.append((user_id, user_name))
                sent_requests[user_id] = datetime.now().isoformat()
                print(f"✔️ Đã gửi lời mời kết bạn đến: {user_name} ({user_id})")
                
            except Exception as e:
                error_msg = str(e).lower()
                user_name = get_user_name(client, user_id)
                failed_requests.append((user_id, user_name, str(e)))
                print(f"❌ Lỗi khi gửi lời mời đến {user_id}: {str(e)}")
                
                # Tự động điều chỉnh độ trễ nếu phát hiện lỗi rate limit
                if "rate limit" in error_msg or "too many requests" in error_msg:
                    delay = min(delay * 2, 10.0)  # Tăng độ trễ, tối đa 10 giây
                    print(f"⚠️ Phát hiện rate limit, tăng độ trễ lên {delay} giây.")
                    time.sleep(60)  # Tạm dừng 1 phút
                
            time.sleep(delay)
        
        save_sent_requests(sent_requests)
        print(f"📑 Đã xử lý lô {i//batch_size + 1}/{total_members//batch_size + 1}")
    
    # Lưu trạng thái cuối cùng và xóa tín hiệu dừng
    save_sent_requests(sent_requests)
    save_cancel_signal(False)
    return successful_requests, failed_requests, delay

def generate_report(successful, failed, total_processed, thread_id):
    """Tạo báo cáo chi tiết về quá trình gửi lời mời với tên người dùng."""
    header = (
        f"📊 Báo cáo gửi lời mời kết bạn (Nhóm {thread_id}):\n"
        f"👥 Tổng số thành viên được xử lý: {total_processed}\n"
        f"✔️ Thành công: {len(successful)}\n"
        f"❌ Thất bại: {len(failed)}\n"
    )
    
    failed_section = ""
    if failed:
        failed_section = "\nDanh sách thất bại:\n" + "\n".join(f"- {name}: {reason}" for _, name, reason in failed)
    
    successful_section = ""
    if successful:
        successful_section = "\nDanh sách thành công:\n" + "\n".join(f"- {name}" for _, name in successful)
    
    # Trả về các phần riêng biệt để xử lý chia tin nhắn
    return header, failed_section, successful_section

def handle_add_group_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh bot.addfriend để gửi lời mời kết bạn."""
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)

    if not is_admin(author_id):
        action = "🚫 ĐÉO QUYỀN"
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
        send_reply_with_style(client, action, message_object, thread_id, thread_type)
        return

    # Xóa tín hiệu dừng trước khi bắt đầu tiến trình mới
    save_cancel_signal(False)

    command_parts = message.strip().split()
    specific_user_id = None
    mentions = getattr(message_object, 'mentions', None)
    target_users = []

    # Kiểm tra nếu có mentions (@user1 @user2 ...)
    if mentions and len(mentions) > 0:
        target_users = [mention['uid'] for mention in mentions]
    
    # Kiểm tra nếu có user_id cụ thể (không phải mention)
    elif len(command_parts) > 1 and not command_parts[1].startswith('--'):
        specific_user_id = command_parts[1]
        target_users = [specific_user_id]

    delay, max_members = parse_command_options(command_parts)

    try:
        if target_users:
            # Gửi lời mời kết bạn đến danh sách người dùng được chỉ định (mentions hoặc user_id)
            sent_requests = load_sent_requests()
            successful_requests = []
            failed_requests = []

            start_message = f"🔄 Đang gửi lời mời kết bạn cho {len(target_users)} người dùng. Vui lòng chờ..."
            send_reply_with_style(client, start_message, message_object, thread_id, thread_type)

            for user_id in target_users:
                if user_id in sent_requests or is_friend(client, user_id):
                    user_name = get_user_name(client, user_id)
                    failed_requests.append((user_id, user_name, "Đã gửi lời mời hoặc đã là bạn bè"))
                    print(f"⏭️ Bỏ qua {user_id}: Đã gửi lời mời hoặc đã là bạn bè.")
                    continue

                try:
                    user_name = get_user_name(client, user_id)
                    friend_request_message = f"Xin chào {user_name} ĐỒNG Ý KB IK"
                    
                    client.sendFriendRequest(userId=user_id, msg=friend_request_message)
                    successful_requests.append((user_id, user_name))
                    sent_requests[user_id] = datetime.now().isoformat()
                    print(f"✔️ Đã gửi lời mời kết bạn đến: {user_name} ({user_id})")
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    user_name = get_user_name(client, user_id)
                    failed_requests.append((user_id, user_name, str(e)))
                    print(f"❌ Lỗi khi gửi lời mời đến {user_id}: {str(e)}")
                    
                    # Tự động điều chỉnh độ trễ nếu phát hiện lỗi rate limit
                    if "rate limit" in error_msg or "too many requests" in error_msg:
                        delay = min(delay * 2, 10.0)
                        print(f"⚠️ Phát hiện rate limit, tăng độ trễ lên {delay} giây.")
                        time.sleep(60)
                
                time.sleep(delay)
            
            save_sent_requests(sent_requests)
            header, failed_section, successful_section = generate_report(successful_requests, failed_requests, len(target_users), thread_id)
            # Gửi báo cáo, chia thành nhiều tin nhắn nếu cần
            report_parts = [header]
            if failed_section:
                report_parts.append(failed_section)
            if successful_section:
                report_parts.append(successful_section)
            
            for part in report_parts:
                send_long_message(client, part, thread_id, thread_type, color="#000000", max_length=1500, delay=2)
            
            client.sendReaction(message_object, "🎉", thread_id, thread_type, reactionType=75)

        else:
            # Gửi lời mời kết bạn đến tất cả thành viên trong nhóm
            group_info = client.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
            members = group_info.get('memVerList', [])
            total_members = min(len(members), max_members)
            
            start_message = f"🔄 Đang gửi lời mời kết bạn cho {total_members} thành viên. Vui lòng chờ..."
            send_reply_with_style(client, start_message, message_object, thread_id, thread_type)
            
            successful_requests, failed_requests, final_delay = send_friend_requests_in_batches(
                client, members, thread_id, thread_type, batch_size=50, delay=delay, max_members=max_members
            )
            
            header, failed_section, successful_section = generate_report(successful_requests, failed_requests, len(successful_requests) + len(failed_requests), thread_id)
            # Gửi báo cáo, chia thành nhiều tin nhắn nếu cần
            report_parts = [header]
            if failed_section:
                report_parts.append(failed_section)
            if successful_section:
                report_parts.append(successful_section)
            
            for part in report_parts:
                send_long_message(client, part, thread_id, thread_type, color="#000000", max_length=1500, delay=2)
            
            client.sendReaction(message_object, "🎉", thread_id, thread_type, reactionType=75)

    except Exception as e:
        error_message = f"❌ Lỗi: {str(e)}"
        send_reply_with_style(client, error_message, message_object, thread_id, thread_type)
        client.sendReaction(message_object, "⚠️", thread_id, thread_type, reactionType=75)

def handle_cancel_request_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh bot.cancelrequest để dừng tiến trình gửi lời mời kết bạn cho nhóm."""
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)

    if not is_admin(author_id):
        action = "🚫 ĐÉO QUYỀN"
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
        send_reply_with_style(client, action, message_object, thread_id, thread_type)
        return

    try:
        save_cancel_signal(True)
        success_message = "🛑 Đã yêu cầu dừng tiến trình gửi lời mời kết bạn. Bot sẽ dừng sau khi hoàn thành lô hiện tại."
        send_reply_with_style(client, success_message, message_object, thread_id, thread_type)
        client.sendReaction(message_object, "🎉", thread_id, thread_type, reactionType=75)
    except Exception as e:
        error_message = f"❌ Lỗi khi yêu cầu dừng tiến trình: {str(e)}"
        send_reply_with_style(client, error_message, message_object, thread_id, thread_type)
        client.sendReaction(message_object, "⚠️", thread_id, thread_type, reactionType=75)

def get_mitaizl():
    """Trả về mapping các lệnh của bot."""
    return {
        'bot.addfriend': handle_add_group_command,
        'bot.cancelrequest': handle_cancel_request_command
    }