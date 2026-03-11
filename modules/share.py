from zlapi.models import Message, MultiMsgStyle, MessageStyle
import random

des = {
    'tác giả': "Unknown",
    'mô tả': "Chia sẻ danh sách mã hoặc chi tiết mã cụ thể với định dạng văn bản tùy chỉnh.",
    'tính năng': [
        "✅ Hiển thị danh sách các mã được chia sẻ khi dùng lệnh !share.",
        "📌 Hiển thị chi tiết mã (tác giả, tính năng, link, lưu ý) khi chỉ định tên mã.",
        "🎨 Áp dụng kiểu chữ in đậm, màu sắc nổi bật cho thông báo.",
        "⏳ Tin nhắn tự động hết hạn sau 30 giây (TTL=30000).",
        "🚫 Trả về cảnh báo nếu mã không tồn tại."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh !share để xem danh sách mã.",
        "📌 Gửi lệnh !share [tên_mã] để xem chi tiết mã. Ví dụ: !share art",
        "✅ Nhận thông báo lỗi nếu tên mã không hợp lệ."
    ]
}

def handle_share_command(message, message_object, thread_id, thread_type, author_id, client):
    # Danh sách mã và thông tin chi tiết
    contents = {
        'art': {
            'url': "https://link4m.com/zynR1ry0",
            'author': "Bot Name",
            'update_date': "08-01-24",
            'features': "Vẽ text art 3 chữ cái không dấu",
            'notes': [
                "1️⃣ Thay imei và cookie",
                "2️⃣ Dùng lệnh !art [xxx] [emoji]. Ví dụ: !art tot 🍉"
            ]
        },
        'bot_info': {
            'url': "https://link4m.com/E6bYAj",
            'author': "Bot Name",
            'update_date': "08-01-24",
            'features': "Quản lý nhóm\n📎 Đính kèm: Sử dụng kèm với file setting.json\n🔗 File setting.json: https://link4m.com/jinRErv",
            'notes': [
                "1️⃣ Thay imei và cookie",
                "2️⃣ Dùng lệnh !bot on vào nhóm muốn Bật bot",
                "3️⃣ Dùng lệnh !bot setup on để cấu hình nội quy nhóm",
                "4️⃣ Dùng lệnh !bot noiquy để áp nội quy cho nhóm"
            ]
        },
        'chui_khanh_tai': {
            'url': "https://link4m.com/vIrILZA",
            'author': "Bot Name",
            'update_date': "08-01-24",
            'features': "Tạo 2 luồng gửi tin nhắn chửi Khánh và Tài. Nó cắm 2 Bot tele để lấy cắp thông tin anh em. Dùng api tele nó chửi ngược lại nó",
            'notes': [
                "1️⃣ Mở file và run chỉ thế thôi"
            ]
        },
        'kickall': {
            'url': "https://link4m.com/IvWCPjQf",
            'author': "Bot Name",
            'update_date': "08-01-24",
            'features': "Kick all member, suy nghĩ sáng suốt trước khi sử dụng nhé",
            'notes': [
                "1️⃣ Thay imei và cookie",
                "2️⃣ Dùng lệnh !kickall Phá kick toàn bộ member. Điều kiện là phải cầm key vàng hoặc bạc"
            ]
        },
        'reaction': {
            'url': "https://link4m.com/9ZqSAyMf",
            'author': "Bot Name",
            'update_date': "08-01-24",
            'features': "Thả cảm xúc all tin nhắn",
            'notes': [
                "1️⃣ Thay imei và cookie",
                "2️⃣ Run"
            ]
        },
        'var': {
            'url': "https://link4m.com/6UslPHh",
            'author': "Bot Name",
            'update_date': "08-01-24",
            'features': "Tính năng đi var",
            'notes': [
                "1️⃣ Thay imei và cookie",
                "2️⃣ Có 3 lệnh var, stop và kickall"
            ]
        },
        'color': {
            'url': "https://link4m.com/NOuwq",
            'author': "Bot Name",
            'update_date': "08-01-24",
            'features': "Tạo Color chữ màu Gradient (chỉ 77 ký tự giới hạn của Zalo, vượt quá 77 ký tự gởi thường không đổi màu)",
            'notes': [
                "1️⃣ Thay imei và cookie. Tìm dòng imei và session_cookies lần lượt thay bằng imei và cookie của mình",
                "2️⃣ Dùng lệnh /color Nội dung đổi màu"
            ]
        },
        'fake_hack': {
            'url': "https://link4m.com/SNoB7",
            'author': "Bot Name",
            'update_date': "08-01-24",
            'features': "Fake hack by A Sìn. Đổi tên, avatar, chặn toàn bộ danh sách bạn! ⚠️ Cảnh báo: Tuyệt đối không sử dụng đối với người thiếu hiểu biết",
            'notes': [
                "1️⃣ Thay imei và cookie",
                "2️⃣ Run file là lụm"
            ]
        },
        'group': {
            'url': "https://link4m.com/ong2UsCV",
            'author': "Bot Name",
            'update_date': "08-01-24",
            'features': "Xem thông tin nhóm",
            'notes': [
                "1️⃣ Thay imei và cookie. Tìm dòng imei và session_cookies lần lượt thay bằng imei và cookie của mình",
                "2️⃣ Dùng lệnh /gr"
            ]
        },
        'info': {
            'url': "https://link4m.com/9ZqSAyMf",
            'author': "Bot Name",
            'update_date': "08-01-24",
            'features': "Thả cảm xúc all tin nhắn",
            'notes': [
                "1️⃣ Thay imei và cookie",
                "2️⃣ Run"
            ]
        },
        'infoadv3': {
            'url': "https://link4m.com/XULfcD",
            'author': "Bot Name",
            'update_date': "08-01-24",
            'features': "Thông tin tác giả\n🔗 Link folder: https://link4m.com/reAlLD",
            'notes': [
                "1️⃣ Thay imei và cookie",
                "2️⃣ Thư mục anime để ngang hàng với file infoad.py. Sau đó copy các ảnh yêu thích vào thư mục anime",
                "3️⃣ Chạy lệnh !infoad"
            ]
        },
        'nhai_theo': {
            'url': "https://link4m.com/9W7ql",
            'author': "Bot Name",
            'update_date': "08-01-24",
            'features': "Nhái theo tin nhắn text của người khác",
            'notes': [
                "1️⃣ Thay imei và cookie",
                "2️⃣ Dùng lệnh !nhai on để bật, !nhai off để tắt"
            ]
        },
        'voice': {
            'url': "https://link4m.com/qC4roZ7a",
            'author': "Bot Name",
            'update_date': "08-01-24",
            'features': "Chuyển Text sang Voice",
            'notes': [
                "1️⃣ Thay imei và cookie",
                "2️⃣ Cài thư viện pip install gtts",
                "3️⃣ Run và dùng lệnh !vi"
            ]
        },
        'welcome': {
            'url': "https://link4m.com/aQAQ6qsi",
            'author': "Bot Name",
            'update_date': "08-01-24",
            'features': "Chào mừng thành viên ra vào nhóm",
            'notes': [
                "1️⃣ Thay imei và cookie",
                "2️⃣ Chọn nhóm cần bật welcome. Gõ lệnh !wl on để bật chế độ welcome. Tắt bằng lệnh !wl off"
            ]
        },
        'welcome2': {
            'url': "https://link4m.com/f6to3r",
            'author': "Bot Name",
            'update_date': "08-01-24",
            'features': "Chào mừng thành viên ra vào nhóm V2\n🔗 Link Font và toàn bộ file: https://link4m.com/KAKasDdS",
            'notes': [
                "1️⃣ Thay imei và cookie",
                "2️⃣ Cài thư viện pip install pillow, pip install emoji. Run file chính welcome2.py. Thư mục Font, file và welcome2.py đặt ngang hàng nhau",
                "3️⃣ Chọn nhóm cần bật welcome. Gõ lệnh !wl on để bật chế độ welcome. Tắt bằng lệnh !wl off"
            ]
        }
    }

    # Gửi phản ứng ngẫu nhiên
    reactions = ["✅", "🚀", "🌟", "💡", "🎉", "😎", "💖", "📬"]
    client.sendReaction(message_object, random.choice(reactions), thread_id, thread_type, reactionType=99)

    # Xử lý lệnh
    text = message.strip().split(" ", 1)
    command = "share"

    if len(text) == 1:
        # Hiển thị danh sách mã
        code_list = "\n".join([f"➜ {key}" for key in contents.keys()])
        response_text = (
            f"🚦 Danh sách mã được chia sẻ:\n"
            f"{code_list}\n"
            f"📌 Ví dụ: {command} art"
        )
    else:
        # Hiển thị chi tiết mã
        code_name = text[1].strip().lower()
        share_info = contents.get(code_name)

        if not share_info:
            response_text = f"⚠ Lệnh [{command} {code_name}] không tồn tại!"
        else:
            notes_formatted = "\n".join([f"   {i+1}️⃣ {note}" for i, note in enumerate(share_info['notes'])])
            response_text = (
                f"🚦 Chi tiết mã {code_name}\n"
                f"👨‍💻 Tác giả: {share_info['author']}\n"
                f"🔄 Cập nhật: {share_info['update_date']}\n"
                f"🚀 Tính năng: {share_info['features']}\n"
                f"📌 Lưu ý:\n"
                f"{notes_formatted}\n"
                f"🔗 Link: {share_info['url']}"
            )

    # Tạo kiểu chữ
    style = MultiMsgStyle(
        [
            MessageStyle(
                offset=0,
                length=len(response_text),
                style="color",
                color="#1e90ff",  # Màu xanh dương
                auto_format=False,
            ),
            MessageStyle(
                offset=0,
                length=len(response_text),
                style="bold",
                size="16",
                auto_format=False,
            ),
        ]
    )

    # Gửi tin nhắn
    response_message = Message(text=response_text, style=style)
    client.sendMessage(response_message, thread_id, thread_type, ttl=30000)

def get_mitaizl():
    return {
        'share': handle_share_command
    }