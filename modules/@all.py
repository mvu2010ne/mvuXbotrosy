from zlapi.models import Message, MultiMsgStyle, MessageStyle

des = {
    'tác giả': "Unknown",
    'mô tả': "Phản hồi cảnh báo khi người dùng gửi lệnh không hợp lệ, với định dạng văn bản tùy chỉnh.",
    'tính năng': [
        "✅ Gửi phản ứng (reaction) ngay khi nhận lệnh.",
        "⚠️ Hiển thị thông báo lỗi với văn bản được tùy chỉnh màu đỏ và in đậm.",
        "🎨 Áp dụng kiểu chữ với kích thước 16 và màu sắc nổi bật.",
        "⏳ Tin nhắn lỗi tự động hết hạn sau 20 giây (TTL=20000).",
        "🚫 Kiểm tra đầu vào và từ chối nếu lệnh không đủ tham số."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh @all để kích hoạt phản hồi.",
        "📌 Ví dụ: @all (lưu ý: cần cung cấp thêm tham số, nếu không sẽ nhận cảnh báo).",
        "✅ Nhận thông báo lỗi với định dạng tùy chỉnh nếu lệnh không hợp lệ."
    ]
}

def handle_sim_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản ứng ngay khi người dùng soạn đúng lệnh
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=99)
    text = message.split()

    if len(text) < 2:
        # Create the error message
        error_text = "⚠ Cảnh báo: Bạn đang làm phiền người khác, hãy lịch sự nếu không bạn sẽ bị sút"

        # Define the style
        style = MultiMsgStyle(
            [
                MessageStyle(
                    offset=0,
                    length=len(error_text),  # Use the actual length of the message
                    style="color",
                    color="#db342e",  # The red color you want
                    auto_format=False,
                ),
                MessageStyle(
                    offset=0,
                    length=len(error_text),
                    style="bold",
                    size="16",  # Font size 16
                    auto_format=False,
                ),
            ]
        )

        # Create the styled error message
        error_message = Message(text=error_text, style=style)
        
        # Send the styled error message
        client.sendMessage(error_message, thread_id, thread_type, ttl=20000)
        return

def get_mitaizl():
    return {
        '@alll': handle_sim_command
    }