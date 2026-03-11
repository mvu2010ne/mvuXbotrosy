from zlapi.models import *
import datetime
import os
import subprocess
import time

admin_ids = ['3299675674241805615']  # Thay thế bằng ID admin thực tế

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Gửi SMS và gọi điện một cách an toàn",
    'tính năng': [
        "📨 Gửi SMS và thực hiện cuộc gọi điện thoại.",
        "🔒 Kiểm tra quyền admin trước khi thực hiện lệnh.",
        "🔍 Kiểm tra định dạng số điện thoại và xử lý các lỗi liên quan.",
        "🔔 Thông báo lỗi cụ thể nếu cú pháp lệnh không chính xác hoặc giá trị không hợp lệ."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh spam.sms <số điện thoại> <số lần gửi> để gửi SMS và thực hiện cuộc gọi.",
        "📌 Ví dụ: spam.sms 0123456789 5 để gửi SMS và thực hiện cuộc gọi đến số 0123456789 5 lần.",
        "✅ Nhận thông báo trạng thái và kết quả gửi SMS ngay lập tức."
    ]
}

def handle_sms_command(message, message_object, thread_id, thread_type, author_id, client):
    parts = message.split()
    if len(parts) < 3:
        client.replyMessage(
            Message(text='🚫 Nhập số đt con chó cần spam và số lần gửi'),
            message_object, thread_id=thread_id, thread_type=thread_type, ttl=60000
        )
        return

    attack_phone_number, number_of_times = parts[1], int(parts[2])

    if not (attack_phone_number.isnumeric() and len(attack_phone_number) == 10 and attack_phone_number not in ['113', '911', '114', '115', '0347460743']):
        client.replyMessage(
            Message(text='📛 Số điện thoại không hợp lệ!\n➡️ Vui lòng nhập đúng định dạng 10 chữ số 📱'),
            message_object, thread_id=thread_id, thread_type=thread_type, ttl=60000
        )
        return

    current_time = datetime.datetime.now()
    is_admin = author_id in admin_ids  # Hạn chế key FREE: Người dùng không phải admin chỉ được spam với số lần gửi từ 5 đến 10

    if not is_admin and (number_of_times < 5 or number_of_times > 10):
        client.replyMessage(
            Message(text='🚫 Bot đang xử lý một số điện thoại khác.\n📵 Số này đã nằm trong danh sách spam!'),
            message_object, thread_id=thread_id, thread_type=thread_type, ttl=60000
        )
        return

    # 🧾 Chuẩn bị thông tin cho thông báo
    time_str = current_time.strftime("%d/%m/%Y %H:%M:%S")  # Thời gian định dạng đẹp

    # Ẩn phần giữa số điện thoại để tránh lộ thông tin
    masked_number = f"{attack_phone_number[:3]}***{attack_phone_number[-3:]}"

    # Tạo mention tag đến người thực hiện lệnh
    mention_text = "@Người quản lý"
    mention = Mention(author_id, offset=0, length=len(mention_text))

    # Style tin nhắn: màu chữ xanh lá cây toàn bộ
    style = MultiMsgStyle([
        MessageStyle(
            style="color",
            color="#4caf50",
            offset=0,
            length=1000  # Áp dụng style cho toàn bộ tin nhắn
        )
    ])


    # 📢 Thông báo bắt đầu thực hiện spam
    start_msg_content = (
        f"{mention_text}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🚨 𝙳ã 𝚗𝚑ậ𝚗 𝚕ệ𝚗𝚑 𝚜𝚙𝚊𝚖 𝚂𝙼𝚂 🚨\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📞 𝚂𝙳𝚃: {masked_number}\n"
        f"🔁 𝚂ố 𝚕ư𝚘̛̣𝚗𝚐: {number_of_times} 𝚕ầ𝚗\n"
        f"🕒 𝚃𝚑ờ𝚒 𝚐𝚒𝚊𝚗: {time_str}\n"
        f"🚀 𝙱ắ𝚝 𝚍ầ𝚞 𝚝ấ𝚗 𝚌𝚘̂𝚗𝚐\n"
        f"━━━━━━━━━━━━━━━"
    )



    client.replyMessage(
        Message(text=start_msg_content.strip(), style=style, mention=mention),
        message_object, thread_id=thread_id, thread_type=thread_type, ttl=600000
    )

    # Chạy quá trình gửi SMS mà không gửi thông báo giữa chừng
    process = subprocess.Popen([
        "python", os.path.join(os.getcwd(), "smsv2.py"), attack_phone_number, str(number_of_times)
    ])
    process.wait()

    # 📢 Thông báo kết thúc thực hiện spam
    end_msg_content = (
        f"{mention_text}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"✅ 𝙷𝚘𝚊̀𝚗 𝚝𝚑𝚊̀𝚗𝚑 𝚜𝚙𝚊𝚖 𝚂𝙼𝚂 ✅\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📞 𝚂𝙳𝚃: {masked_number}\n"
        f"🔁 𝚂ố 𝚕ư𝚘̛̣𝚗𝚐: {number_of_times}/{number_of_times} 𝚕ầ𝚗\n"
        f"🕒 𝚃𝚑ờ𝚒 𝚐𝚒𝚊𝚗: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        f"⏳ 𝚃𝚑ờ𝚒 𝚐𝚒𝚊𝚗 𝚌𝚑𝚘̛̀: 120 𝚐𝚒𝚊𝚢\n"
        f"🚀 Kết thúc tiến trình spam!\n"
        f"━━━━━━━━━━━━━━━"
    )


    client.replyMessage(
        Message(text=end_msg_content.strip(), style=style, mention=mention),
        message_object, thread_id=thread_id, thread_type=thread_type, ttl=600000
    )

def get_mitaizl():
    return {'spam.sms': handle_sms_command}