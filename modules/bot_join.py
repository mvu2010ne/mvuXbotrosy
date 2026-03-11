import time  # Import module time để sử dụng sleep
from zlapi.models import Message, ZaloAPIException
from config import ADMIN

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Tham gia nhóm Zalo bằng liên kết mời một cách tự động.",
    'tính năng': [
        "🔗 Hỗ trợ tham gia nhiều nhóm Zalo cùng lúc từ danh sách link.",
        "🚀 Xử lý phản hồi từ API Zalo và hiển thị thông báo kết quả.",
        "⏳ Thêm thời gian chờ giữa các yêu cầu để tránh bị giới hạn.",
        "🔒 Chỉ quản trị viên mới có quyền sử dụng lệnh này."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh kèm theo link nhóm Zalo để bot tham gia.",
        "📌 Hỗ trợ nhập nhiều link cùng lúc, cách nhau bằng dấu cách.",
        "✅ Nhận thông báo trạng thái tham gia ngay lập tức."
    ]
}

def handle_join_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản hồi emoji "✅" xác nhận đã nhận lệnh
    action = "✅ "
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    if author_id not in ADMIN:
        client.replyMessage(
            Message(text="🚫 Bot không có quyền sử dụng lệnh này!"),
            message_object,
            thread_id,
            thread_type,
            ttl=30000
        )
        return

    try:
        parts = message.split(" ", 1)
        if len(parts) < 2:
            client.replyMessage(
                Message(text="⚠ Thiếu link rồi! Hãy nhập link nhóm Zalo."),
                message_object,
                thread_id,
                thread_type,
                ttl=30000
            )
            return

        # Giả sử các link được cách nhau bởi dấu cách
        links_str = parts[1].strip()
        links = [link.strip() for link in links_str.split() if link.strip().startswith("https://zalo.me/")]

        if not links:
            client.replyMessage(
                Message(text="⛔ Không tìm thấy link hợp lệ! Link phải bắt đầu bằng https://zalo.me/"),
                message_object,
                thread_id,
                thread_type,
                ttl=30000
            )
            return

        results = []
        for url in links:
            join_result = client.joinGroup(url)
            print(f"[DEBUG] Kết quả từ API: {join_result}")
            if isinstance(join_result, dict) and 'error_code' in join_result:
                error_code = join_result['error_code']
                error_messages = {
                    0:   "✅ Tham gia nhóm thành công!",
                    240: "⏳ Yêu cầu đang chờ duyệt!",
                    178: "ℹ️ Bot đã là thành viên của nhóm!",
                    227: "❌ Nhóm hoặc link không tồn tại!",
                    175: "🚫 Bot đã bị chặn khỏi nhóm!",
                    1003: "⚠️ Nhóm đã đầy thành viên!",
                    1004: "⚠️ Nhóm đạt giới hạn thành viên!",
                    1022: "🔄 Bot đã yêu cầu tham gia trước đó!",
                    221: "⚠ Vượt quá số request cho phép",
                    271: "⚠ Trưởng nhóm chưa xác thực tài khoản"
                }
                msg = error_messages.get(error_code, "⚠ Có lỗi xảy ra, vui lòng thử lại sau!")
            else:
                msg = f"⚙️ Phản hồi không xác định: {join_result}"
            results.append(f"{url} : {msg}")

            # Thêm khoảng thời gian trễ trước khi thực hiện yêu cầu tiếp theo (ví dụ: 1 giây)
            time.sleep(1)
            
        result_text = "\n".join(results)
        client.replyMessage(
            Message(text=result_text),
            message_object,
            thread_id,
            thread_type,
            ttl=180000
        )

    except ZaloAPIException as e:
        client.replyMessage(
            Message(text=f"🚨 Lỗi từ API Zalo: {e}"),
            message_object,
            thread_id,
            thread_type,
            ttl=30000
        )
    except Exception as e:
        client.replyMessage(
            Message(text=f"❗ Lỗi không xác định: {e}"),
            message_object,
            thread_id,
            thread_type,
            ttl=30000
        )

def get_mitaizl():
    return {
        'bot.join': handle_join_command
    }
