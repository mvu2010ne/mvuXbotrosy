from datetime import datetime
import time
import re
from zlapi.models import Message, MultiMsgStyle, MessageStyle, ThreadType
from zlapi import ZaloAPIException
from config import ADMIN, PREFIX

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Hiển thị danh sách thành viên bị khóa trong nhóm Zalo bằng tin nhắn văn bản, chia thành nhiều phần nếu quá dài.",
    'tính năng': [
        "📋 Liệt kê tên, ID và ngày tạo tài khoản của các thành viên bị khóa trong nhóm.",
        "📩 Gửi tin nhắn văn bản với định dạng đơn giản, chia thành nhiều phần nếu vượt giới hạn.",
        "🔒 Chỉ quản trị viên hoặc chủ nhóm mới có quyền sử dụng.",
        "⚠️ Thông báo nếu không có thành viên bị khóa, nhóm rỗng, hoặc có thành viên không lấy được thông tin."
    ],
    'hướng dẫn sử dụng': [
        f"📩 Gửi lệnh `{PREFIX}group.blocked` để xem danh sách tất cả thành viên bị khóa.",
        "📢 Nhận tin nhắn chứa tên, ID và ngày tạo tài khoản của các thành viên bị khóa."
    ]
}

# Hằng số
MAX_MESSAGE_LENGTH = 1500  # Độ dài tối đa của mỗi đoạn tin nhắn
API_CALL_DELAY = 1.0       # Thời gian trễ giữa các lệnh API
BATCH_SIZE = 50            # Số thành viên xử lý mỗi lô
BATCH_PAUSE = 2            # Thời gian dừng giữa các lô (giây)

def send_message_with_style(client, text, thread_id, thread_type, color="#000000"):
    """Gửi tin nhắn với định dạng màu sắc và font chữ."""
    print(f"[DEBUG] Gửi tin nhắn đến thread_id={thread_id}, thread_type={thread_type}, color={color}, text_length={len(text)}")
    style = MultiMsgStyle([
        MessageStyle(
            offset=0,
            length=len(text),
            style="color",
            color=color,
            auto_format=False,
        ),
        MessageStyle(
            offset=0,
            length=len(text),
            style="font",
            size="3",
            auto_format=False
        )
    ])
    try:
        client.sendMessage(Message(text=text, style=style), thread_id=thread_id, thread_type=thread_type, ttl=60000)
        print(f"[DEBUG] Gửi tin nhắn thành công đến thread_id={thread_id}")
    except Exception as e:
        print(f"[ERROR] Không thể gửi tin nhắn đến thread_id={thread_id}: {e}")

def send_long_message(client, text, thread_id, thread_type, color="#000000", max_length=1500, delay=5):
    """Chia tin nhắn thành nhiều phần nếu quá dài và gửi với thời gian trễ."""
    print(f"[DEBUG] Chia tin nhắn dài, total_length={len(text)}, max_length={max_length}")
    chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
    print(f"[DEBUG] Tạo {len(chunks)} đoạn tin nhắn")
    for i, chunk in enumerate(chunks, 1):
        print(f"[DEBUG] Gửi đoạn {i}/{len(chunks)}, length={len(chunk)}")
        send_message_with_style(client, chunk, thread_id, thread_type, color)
        if i < len(chunks):
            time.sleep(delay)
    print(f"[DEBUG] Đã gửi tất cả {len(chunks)} đoạn")

def get_user_info(client, user_id):
    """Lấy thông tin tài khoản của thành viên và kiểm tra trạng thái khóa."""
    print(f"[DEBUG] Lấy thông tin người dùng cho user_id={user_id}")
    if isinstance(user_id, str) and user_id.endswith('_0'):
        user_id = user_id.rsplit('_', 1)[0]
        print(f"[DEBUG] Đã xóa hậu tố '_0', user_id mới={user_id}")

    # Kiểm tra định dạng ID
    if not re.match(r'^\d+$', user_id):
        print(f"[ERROR] user_id không hợp lệ={user_id}")
        return None, f"ID không hợp lệ: {user_id}"

    try:
        info_response = client.fetchUserInfo(user_id)
        print(f"[DEBUG] Phản hồi API cho user_id={user_id}: {vars(info_response)}")
        profiles = info_response.unchanged_profiles or info_response.changed_profiles
        if not profiles:
            print(f"[WARNING] Không có dữ liệu profile cho user_id={user_id}")
            return None, f"Không có dữ liệu profile: {user_id}"

        info = profiles.get(str(user_id))
        if not info:
            print(f"[WARNING] Không tìm thấy user_id={user_id} trong profiles")
            return None, f"Không tìm thấy người dùng: {user_id}"

        is_blocked = getattr(info, 'isBlocked', 0)
        print(f"[DEBUG] user_id={user_id}, isBlocked={is_blocked}")

        if is_blocked == 1:
            create_time = info.createdTs
            if isinstance(create_time, int):
                create_time = datetime.fromtimestamp(create_time).strftime("%d/%m/%Y")
            else:
                create_time = "Không xác định"
            user_data = {
                'name': info.zaloName or "Unknown",
                'id': user_id,
                'create_time': create_time
            }
            print(f"[DEBUG] Tìm thấy người dùng bị khóa: {user_data}")
            return user_data, None
        return None, None
    except ZaloAPIException as e:
        print(f"[ERROR] Lỗi API Zalo cho user_id={user_id}: {e}")
        return None, f"Lỗi API: {str(e)}"
    except Exception as e:
        print(f"[ERROR] Lỗi không mong muốn cho user_id={user_id}: {e}")
        return None, f"Lỗi không mong muốn: {str(e)}"

def handle_blocked_members_command(message, message_object, thread_id, thread_type, author_id, client):
    """Lấy danh sách thành viên bị khóa trong nhóm và gửi dưới dạng tin nhắn."""
    print(f"[DEBUG] Xử lý lệnh group.blocked, thread_id={thread_id}, author_id={author_id}")
    try:
        # Gửi phản ứng
        print(f"[DEBUG] Gửi phản ứng cho message_id={message_object.msgId}")
        client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
        print(f"[DEBUG] Gửi phản ứng thành công")

        # Kiểm tra xem có phải là nhóm không
        if thread_type != ThreadType.GROUP:
            error_message = "Lệnh này chỉ sử dụng được trong nhóm."
            print(f"[ERROR] Không phải nhóm, thread_type={thread_type}")
            send_message_with_style(client, error_message, thread_id, thread_type, color="#db342e")
            return

        # Lấy thông tin nhóm
        print(f"[DEBUG] Lấy thông tin nhóm cho thread_id={thread_id}")
        try:
            group_info = client.fetchGroupInfo(thread_id).gridInfoMap.get(thread_id)
            if not group_info:
                raise ValueError("Không tìm thấy thông tin nhóm")
            print(f"[DEBUG] Lấy thông tin nhóm thành công: name={group_info.get('name', 'Unknown')}")
        except Exception as e:
            error_message = f"Không thể lấy thông tin nhóm: {e}"
            print(f"[ERROR] Không thể lấy thông tin nhóm: {e}")
            send_message_with_style(client, error_message, thread_id, thread_type, color="#db342e")
            return

        # Kiểm tra quyền quản trị
        creator_id = group_info.get('creatorId')
        admin_ids = group_info.get('adminIds', []) or []
        print(f"[DEBUG] Creator ID: {creator_id}, Admin IDs: {admin_ids}")
        if author_id not in admin_ids and author_id != creator_id and author_id not in ADMIN:
            error_message = "Chỉ quản trị viên hoặc chủ nhóm mới có thể sử dụng lệnh này."
            print(f"[ERROR] Người dùng {author_id} không có quyền")
            send_message_with_style(client, error_message, thread_id, thread_type, color="#db342e")
            return

        # Lấy và xác thực danh sách thành viên
        member_ids = group_info.get('memVerList', [])
        # Loại bỏ _0 ngay từ đầu
        cleaned_member_ids = [mid.rsplit('_', 1)[0] if isinstance(mid, str) and mid.endswith('_0') else mid for mid in member_ids]
        valid_members = set(cleaned_member_ids)
        member_ids = [mid for mid in cleaned_member_ids if mid in valid_members and re.match(r'^\d+$', mid)]
        print(f"[DEBUG] Tìm thấy {len(member_ids)} thành viên hợp lệ sau khi làm sạch")

        if not member_ids:
            no_members = "Nhóm hiện tại không có thành viên nào."
            print(f"[DEBUG] Không có thành viên trong nhóm")
            send_message_with_style(client, no_members, thread_id, thread_type, color="#db342e")
            return

        # Xử lý thành viên theo lô
        blocked_members = []
        failed_members = []
        failed_reasons = {}
        for i in range(0, len(member_ids), BATCH_SIZE):
            batch = member_ids[i:i + BATCH_SIZE]
            print(f"[DEBUG] Xử lý lô {i//BATCH_SIZE + 1}, kích thước={len(batch)}")
            for member_id in batch:
                print(f"[DEBUG] Xử lý thành viên {member_id}")
                user_info, reason = get_user_info(client, member_id)
                if user_info:
                    blocked_members.append(user_info)
                elif reason:  # Chỉ thêm nếu có lỗi thực sự
                    failed_members.append(member_id)
                    failed_reasons[member_id] = reason
                time.sleep(API_CALL_DELAY)
            time.sleep(BATCH_PAUSE)

        print(f"[DEBUG] Tìm thấy {len(blocked_members)} thành viên bị khóa")

        # Chuẩn bị tin nhắn
        if not blocked_members:
            no_blocked = "Không có thành viên nào bị khóa trong nhóm."
            if failed_members:
                no_blocked += "\n⚠️ Không thể lấy thông tin cho các thành viên:\n"
                for mid in failed_members[:5]:
                    no_blocked += f"- {mid}: {failed_reasons.get(mid, 'Lỗi không xác định')}\n"
                if len(failed_members) > 5:
                    no_blocked += "...\n"
            print(f"[DEBUG] Không tìm thấy thành viên bị khóa")
            send_message_with_style(client, no_blocked, thread_id, thread_type, color="#db342e")
            return

        header = f"📋 Danh sách thành viên bị khóa ({len(blocked_members)}):\n\n"
        msg = header
        for idx, member in enumerate(blocked_members, 1):
            member_info = (
                f"{idx}. {member['name']}:\n"
                f"🔣 ID: {member['id']}\n"
                f"📅 Ngày tạo tài khoản: {member['create_time']}\n"
                "──────────\n"
            )
            msg += member_info

        if failed_members:
            msg += "\n⚠️ Không thể lấy thông tin cho các thành viên:\n"
            for mid in failed_members[:5]:
                msg += f"- {mid}: {failed_reasons.get(mid, 'Lỗi không xác định')}\n"
            if len(failed_members) > 5:
                msg += "...\n"

        print(f"[DEBUG] Chuẩn bị tin nhắn, total_length={len(msg)}")

        # Gửi tin nhắn
        send_long_message(client, msg, thread_id, thread_type, color="#000000", max_length=MAX_MESSAGE_LENGTH, delay=5)
        print(f"[DEBUG] Hoàn thành lệnh group.blocked")

    except ZaloAPIException as e:
        error_message = f"🔴 Lỗi API: {str(e)}"
        print(f"[ERROR] Lỗi API Zalo: {e}")
        send_message_with_style(client, error_message, thread_id, thread_type, color="#db342e")
    except Exception as e:
        error_message = f"🔴 Lỗi: {str(e)}"
        print(f"[ERROR] Lỗi không mong muốn: {e}")
        send_message_with_style(client, error_message, thread_id, thread_type, color="#db342e")

def get_mitaizl():
    return {
        'group.blocked': handle_blocked_members_command
    }