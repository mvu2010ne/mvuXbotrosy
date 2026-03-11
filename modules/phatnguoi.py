from zlapi import ZaloAPI
from zlapi.models import Message
import requests
import json
import time

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Kiểm tra thông tin phạt nguội",
    'tính năng': [
        "🔍 Tra cứu thông tin vi phạm giao thông dựa trên biển số xe.",
        "📨 Gửi phản hồi với kết quả tra cứu và thông tin chi tiết về các vi phạm.",
        "🔔 Thông báo lỗi cụ thể nếu có vấn đề xảy ra khi gọi API hoặc xử lý dữ liệu.",
        "⏳ Tự động chia nhỏ tin nhắn nếu kết quả quá dài."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh phatnguoi <biển số xe> để kiểm tra thông tin vi phạm.",
        "📌 Ví dụ: phatnguoi 30A12345 để tra cứu thông tin vi phạm của biển số xe 30A12345.",
        "✅ Nhận thông báo trạng thái tra cứu và kết quả chi tiết ngay lập tức."
    ]
}


def handle_phatnguoi_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản ứng ngay khi người dùng soạn đúng lệnh
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    
    try:
        # Trích xuất biển số xe từ tin nhắn, ví dụ: "phatnguoi 30A12345"
        parts = message.split(" ", 1)
        if len(parts) < 2 or not parts[1].strip():
            error_message = Message(text="Vui lòng cung cấp biển số xe sau lệnh 'phatnguoi'.")
            client.sendMessage(error_message, thread_id, thread_type)
            return
        
        plate_number = parts[1].strip()  # Lấy biển số xe

        # Gửi phản hồi vào tin nhắn người đã soạn
        reply_message = f"Đang tiến hành lấy thông tin vi phạm\nNguồn: Cục Cảnh Sát Giao Thông"
        client.sendMessage(Message(text=reply_message), thread_id, thread_type, ttl=30000)
        
        api_url = f'https://api.sumiproject.net/checkpn?bienso={plate_number}'  # Gửi yêu cầu đến API
        response = requests.get(api_url)
        
        if response.status_code == 200:
            api_data = response.json()
            
            # Nếu API trả về lỗi (status khác 1), thông báo lỗi cho người dùng
            if api_data.get("status") != 1:
                message_content = f"{api_data.get('msg', 'Biển số xe này chưa vi phạm')}"
            else:
                violations = api_data.get("data", [])
                info = api_data.get("data_info", {})
                lines = []
                lines.append("🔎 Thông tin phạt nguội:\n")
                
                if violations:
                    for idx, v in enumerate(violations, start=1):
                        lines.append(f"🚨 Vi phạm {idx}:")
                        lines.append(f"🔢 Biển kiểm soát: {v.get('Biển kiểm soát', 'N/A')}")
                        lines.append(f"🎨 Màu biển: {v.get('Màu biển', 'N/A')}")
                        lines.append(f"🚗 Loại phương tiện: {v.get('Loại phương tiện', 'N/A')}")
                        lines.append(f"⏰ Thời gian vi phạm: {v.get('Thời gian vi phạm', 'N/A')}")
                        lines.append(f"📍 Địa điểm vi phạm: {v.get('Địa điểm vi phạm', 'N/A')}")
                        lines.append(f"⚠️ Hành vi vi phạm: {v.get('Hành vi vi phạm', 'N/A')}")
                        lines.append(f"📌 Trạng thái: {v.get('Trạng thái', 'N/A')}")
                        lines.append(f"🏢 Đơn vị phát hiện: {v.get('Đơn vị phát hiện vi phạm', 'N/A')}")
                        
                        noi_giai_quyet = v.get("Nơi giải quyết vụ việc", [])
                        if isinstance(noi_giai_quyet, list) and noi_giai_quyet:
                            lines.append(" - Nơi giải quyết vụ việc:")
                            for item in noi_giai_quyet:
                                lines.append(f" • {item}")
                        else:
                            lines.append(f"🏛️ Nơi giải quyết vụ việc: {noi_giai_quyet}")
                        
                        lines.append("")  # Dòng trống để phân cách các vi phạm
                else:
                    lines.append("✅ Không có thông tin vi phạm nào được tìm thấy.")
                
                # Thêm thông tin tổng quan nếu có
                if info:
                    lines.append("📊 Thông tin tổng quan:")
                    lines.append(f"📌 Tổng số vi phạm: {info.get('total', 'N/A')}")
                    lines.append(f"⏳ Chưa xử phạt: {info.get('chuaxuphat', 'N/A')}")
                    lines.append(f"✔️ Đã xử phạt: {info.get('daxuphat', 'N/A')}")
                    lines.append(f"📅 Cập nhật mới nhất: {info.get('latest', 'N/A')}")
                
                message_content = "\n".join(lines)  # In kết quả ra terminal
                print("Kết quả tra cứu:")
                print(message_content)
                
                # Nếu tin nhắn quá dài thì chia thành nhiều phần (giới hạn 2000 ký tự)
                MAX_MESSAGE_LENGTH = 2000
                if len(message_content) > MAX_MESSAGE_LENGTH:
                    chunks = [message_content[i:i+MAX_MESSAGE_LENGTH] for i in range(0, len(message_content), MAX_MESSAGE_LENGTH)]
                    for chunk in chunks:
                        msg = Message(text=chunk)
                        client.replyMessage(msg, message_object, thread_id, thread_type, ttl=120000)
                        time.sleep(3)  # Delay 3 giây giữa các tin nhắn
                else:
                    msg = Message(text=message_content)
                    client.replyMessage(msg, message_object, thread_id, thread_type, ttl=120000)
        else:
            error_message = Message(text="API không phản hồi hoặc trả về lỗi.")
            client.sendMessage(error_message, thread_id, thread_type)
    
    except requests.exceptions.RequestException as e:
        error_message = Message(text=f"Đã xảy ra lỗi khi gọi API: {str(e)}")
        client.sendMessage(error_message, thread_id, thread_type)
    except Exception as e:
        error_message = Message(text=f"Đã xảy ra lỗi không xác định: {str(e)}")
        client.sendMessage(error_message, thread_id, thread_type)

def get_mitaizl():
    return {
        'phatnguoi': handle_phatnguoi_command
    }
