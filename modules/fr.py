from zlapi import ZaloAPIException
from zlapi.models import Message, MessageStyle, MultiMsgStyle
from config import PREFIX
import json
import logging

# Thiết lập logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

des = {
    'tác giả': "Grok (dựa trên mã của Minh Vũ Shinn Cte)",
    'mô tả': "📬 Kiểm tra danh sách yêu cầu kết bạn đang chờ trên Zalo.",
    'tính năng': [
        "🔍 Liệt kê tất cả yêu cầu kết bạn từ người dùng khác.",
        "📋 Hiển thị tên Zalo và UID của người gửi yêu cầu.",
        "🎨 Gửi phản hồi với định dạng màu sắc và in đậm.",
        "⚠️ Thông báo nếu không có yêu cầu kết bạn nào đang chờ."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh fr để kiểm tra danh sách yêu cầu kết bạn.",
        "📌 Ví dụ: fr",
        "✅ Nhận danh sách yêu cầu kết bạn hoặc thông báo nếu không có yêu cầu."
    ]
}

def send_message_with_style(client, text, thread_id, thread_type, ttl=60000, color="#db342e"):
    """Gửi tin nhắn với định dạng màu sắc và in đậm."""
    base_length = len(text)
    adjusted_length = base_length + 355
    style = MultiMsgStyle([
        MessageStyle(offset=0, length=adjusted_length, style="color", color=color, auto_format=False),
        MessageStyle(offset=0, length=adjusted_length, style="bold", size="8", auto_format=False)
    ])
    msg = Message(text=text, style=style)
    client.send(msg, thread_id=thread_id, thread_type=thread_type, ttl=ttl)

def fetch_pending_friend_requests(client):
    """
    Lấy danh sách yêu cầu kết bạn đang chờ (giả định endpoint).

    Args:
        client (ZaloAPI): Đối tượng client ZaloAPI.

    Returns:
        list: Danh sách các yêu cầu kết bạn (mỗi yêu cầu chứa UID và thông tin người dùng).
        dict: Thông tin lỗi nếu yêu cầu thất bại.
    """
    params = {
        "zpw_ver": 645,
        "zpw_type": 30,
        "params": client._encode({
            "imei": client._imei,
            "language": "vi",
            "avatar_size": 120
        })
    }

    try:
        # Giả định endpoint để lấy danh sách yêu cầu kết bạn
        response = client._get("https://tt-friend-wpa.chat.zalo.me/api/friend/getrequests", params=params)
        
        # In và ghi log phản hồi thô từ API
        print(f"API raw response: {response.text}")
        logger.debug(f"API raw response: {response.text}")

        # Kiểm tra trạng thái HTTP
        if response.status_code != 200:
            logger.error(f"HTTP error: {response.status_code} - {response.text}")
            raise ZaloAPIException(f"HTTP error {response.status_code}: {response.text}")

        # Phân tích JSON
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}. Response content: {response.text}")
            raise ZaloAPIException(f"Invalid JSON response: {str(e)}")

        # Kiểm tra lỗi từ API
        results = data.get("data") if data.get("error_code") == 0 else None
        if results:
            results = client._decode(results)
            results = results.get("data") if results.get("data") else results
            if results is None:
                results = {"error_code": 1337, "error_message": "Data is None"}

            if isinstance(results, str):
                try:
                    results = json.loads(results)
                except json.JSONDecodeError:
                    results = {"error_code": 1337, "error_message": results}

            return results.get("requests", [])  # Giả định dữ liệu trả về có trường 'requests'

        error_code = data.get("error_code")
        error_message = data.get("error_message") or data.get("data")
        raise ZaloAPIException(f"Error #{error_code} when fetching pending friend requests: {error_message}")

    except ZaloAPIException as e:
        raise e
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        raise ZaloAPIException(f"An unexpected error occurred: {str(e)}")

def handle_friendreq_command(message, message_object, thread_id, thread_type, author_id, client):
    """
    Xử lý lệnh kiểm tra danh sách yêu cầu kết bạn đang chờ.

    Args:
        message (str): Nội dung tin nhắn.
        message_object (Message): Đối tượng tin nhắn.
        thread_id (str): ID của thread.
        thread_type (ThreadType): Loại thread (USER/GROUP).
        author_id (str): ID của người gửi.
        client (ZaloAPI): Đối tượng client ZaloAPI.
    """
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    msg_error = "🔴 Lỗi: Không thể lấy danh sách yêu cầu kết bạn."

    try:
        if message.strip() != f"{PREFIX}fr":
            send_message_with_style(client, "🔴 Cú pháp đúng: fr", thread_id, thread_type)
            return

        # Lấy danh sách yêu cầu kết bạn
        pending_requests = fetch_pending_friend_requests(client)

        if not pending_requests:
            msg = "📭 Hiện tại không có yêu cầu kết bạn nào đang chờ."
            send_message_with_style(client, msg, thread_id, thread_type)
            return

        # Xử lý danh sách yêu cầu
        msg_lines = ["📬 Danh sách yêu cầu kết bạn:"]
        for request in pending_requests:
            user_id = request.get("uid")
            if user_id:
                try:
                    user_info = client.fetchUserInfo(user_id)
                    user_info = user_info.unchanged_profiles or user_info.changed_profiles
                    user_info = user_info[str(user_id)]
                    user_name = user_info.zaloName if user_info.zaloName else "Người dùng"
                    msg_lines.append(f"👤 {user_name} (ID: {user_id})")
                except ZaloAPIException:
                    msg_lines.append(f"👤 Người dùng (ID: {user_id}) - Không lấy được thông tin")
            else:
                msg_lines.append("👤 Người dùng không xác định")

        msg = "\n".join(msg_lines)
        send_message_with_style(client, msg, thread_id, thread_type)

    except ZaloAPIException as e:
        send_message_with_style(client, f"⚠️ Lỗi: {str(e)}", thread_id, thread_type)
    except Exception as e:
        send_message_with_style(client, f"⚠️ Đã xảy ra lỗi: {str(e)}", thread_id, thread_type)

def get_mitaizl():
    """
    Đăng ký lệnh 'fr' cho hệ thống.

    Returns:
        dict: Bản đồ lệnh với key là tên lệnh và value là hàm xử lý.
    """
    return {
        'fr': handle_friendreq_command
    }