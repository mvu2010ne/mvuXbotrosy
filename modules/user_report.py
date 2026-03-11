from zlapi.models import Message
from config import ADMIN
import random
import json


des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Tố cáo người dùng trên Zalo với lý do cụ thể",
    'tính năng': [
        "🚨 Tố cáo người dùng với lý do được chỉ định hoặc tùy chỉnh.",
        "🔒 Kiểm tra quyền admin trước khi thực hiện lệnh.",
        "🔍 Xử lý cú pháp lệnh và kiểm tra các giá trị hợp lệ.",
        "🔔 Thông báo lỗi cụ thể nếu cú pháp lệnh không chính xác hoặc giá trị không hợp lệ."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh user.rp <user_id> <reason> [content] để tố cáo người dùng.",
        "📌 Lý do: 1 = Nội dung nhạy cảm, 2 = Làm phiền, 3 = Lừa đảo, 0 = Tùy chỉnh (yêu cầu nội dung).",
        "📌 Ví dụ: user.rp 123456789 1 để tố cáo người dùng có ID 123456789 vì nội dung nhạy cảm.",
        "📌 Ví dụ: user.rp 123456789 0 'Nội dung vi phạm' để tố cáo với lý do tùy chỉnh.",
        "✅ Nhận thông báo trạng thái và kết quả tố cáo ngay lập tức."
    ]
}

def is_admin(author_id):
    return author_id in ADMIN

def sendReport(self, user_id, reason=0, content=None):
    """Send report to Zalo.
    
    Args:
        user_id (int | str): User ID to report
        reason (int): Reason for reporting
            1 = Nội dung nhạy cảm
            2 = Làm phiền
            3 = Lừa đảo
            0 = custom
        content (str): Report content (works if reason = custom)
    
    Returns:
        dict: Response from Zalo API
    
    Raises:
        Exception: If request failed
    """
    params = {
        "zpw_ver": 645,
        "zpw_type": 30
    }
    
    payload = {
        "params": {
            "idTo": str(user_id),
            "objId": "person.profile"
        }
    }
    
    content = content if content and not reason else "" if not content and not reason else ""
    if content:
        payload["params"]["content"] = content
    
    payload["params"]["reason"] = str(random.randint(1, 3) if not content else reason)
    payload["params"] = self._encode(payload["params"])
    
    response = self._post("https://tt-profile-wpa.chat.zalo.me/api/report/abuse-v2", params=params, data=payload)
    data = response.json()
    results = data.get("data") if data.get("error_code") == 0 else None
    
    if results:
        results = self._decode(results)
        results = results.get("data") if results.get("data") else results
        if results is None:
            results = {"error_code": 1337, "error_message": "Data is None"}
        
        if isinstance(results, str):
            try:
                results = json.loads(results)
            except:
                results = {"error_code": 1337, "error_message": results}
        
        return results
    
    error_code = data.get("error_code")
    error_message = data.get("error_message") or data.get("data")
    raise Exception(f"Error #{error_code} when sending requests: {error_message}")

def handle_reportuser_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản ứng ngay khi người dùng soạn đúng lệnh
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    
    try:
        if not is_admin(author_id):
            msg = "• Bạn Không Có Quyền! Chỉ có admin mới có thể sử dụng được lệnh này."
            client.replyMessage(Message(text=msg), message_object, thread_id, thread_type, ttl=20000)
            return
        
        # Phân tích cú pháp lệnh
        command_parts = message.split(' ', 3)
        if len(command_parts) < 3:
            client.replyMessage(Message(text="❌ Lệnh không hợp lệ\n Định dạng: user.rp <user_id> <reason> [content]"), message_object, thread_id, thread_type, ttl=30000)
            return
        
        target_user_id = command_parts[1]  # ID người bị tố cáo
        try:
            reason = int(command_parts[2])  # Lý do tố cáo
            if reason not in [0, 1, 2, 3]:
                raise ValueError("Lý do phải là 0 (tùy chỉnh), 1 (nội dung nhạy cảm), 2 (làm phiền), hoặc 3 (lừa đảo).")
        except (IndexError, ValueError):
            client.replyMessage(Message(text="Lý do phải là một số nguyên hợp lệ (0, 1, 2, hoặc 3)."), message_object, thread_id, thread_type, ttl=30000)
            return
        
        # Kiểm tra nội dung nếu lý do là tùy chỉnh (0)
        content = command_parts[3] if len(command_parts) > 3 and reason == 0 else None
        if reason == 0 and not content:
            client.replyMessage(Message(text="Vui lòng cung cấp nội dung tố cáo khi chọn lý do tùy chỉnh (0)."), message_object, thread_id, thread_type, ttl=30000)
            return
        
        # Gọi hàm sendReport để gửi tố cáo
        result = sendReport(client, target_user_id, reason, content)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # Xử lý phản hồi
        reason_text = {
            0: "Tùy chỉnh" if content else "Không xác định",
            1: "Nội dung nhạy cảm",
            2: "Làm phiền",
            3: "Lừa đảo"
        }.get(reason, "Không xác định")
        
        response = f"Đã gửi tố cáo cho người dùng {target_user_id} với lý do: {reason_text}"
        if content:
            response += f" (Nội dung: {content})"
        client.replyMessage(Message(text=response), message_object, thread_id, thread_type, ttl=500000)
    
    except Exception as e:
        error_message = f"Lỗi khi gửi tố cáo: {str(e)}"
        client.replyMessage(Message(text=error_message), message_object, thread_id, thread_type, ttl=30000)

def get_mitaizl():
    return { 'user.rp': handle_reportuser_command }