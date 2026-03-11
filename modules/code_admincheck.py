import os
import ast
import time
from zlapi.models import Message, ThreadType
import logging

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Biến mô tả cho module này
module_info = {
    'tác giả': "Minh Vũ",
    'mô tả': "🔍 Kiểm tra danh sách các module yêu cầu quyền admin trong hệ thống.",
    'tính năng': [
        "📋 Quét tất cả các module trong thư mục 'modules' để kiểm tra yêu cầu quyền admin.",
        "🔎 Phát hiện module có hàm 'is_admin' hoặc logic kiểm tra quyền admin (so sánh với biến 'ADMIN').",
        "📊 Báo cáo danh sách module yêu cầu quyền admin và không yêu cầu quyền admin.",
        "🔄 Chia danh sách kết quả thành nhiều tin nhắn nếu vượt quá giới hạn ký tự.",
        "⏱️ Gửi các tin nhắn với độ trễ 1 giây để tránh spam.",
        "⚠️ Thông báo lỗi nếu không tìm thấy module hoặc gặp vấn đề hệ thống."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh code.admincheck để nhận danh sách các module yêu cầu quyền admin.",
        "📌 Ví dụ: code.admincheck (không cần tham số).",
        "✅ Nhận danh sách các module yêu cầu quyền admin và không yêu cầu quyền admin."
    ]
}

# Giới hạn độ dài tối đa cho mỗi tin nhắn
MAX_MESSAGE_LENGTH = 1500

def check_admin_requirement(file_path):
    """Kiểm tra xem module có yêu cầu quyền admin hay không bằng cách phân tích mã nguồn."""
    logger.info(f"[check_admin_requirement] Đang kiểm tra module: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        tree = ast.parse(source)
        
        # Kiểm tra sự tồn tại của hàm 'is_admin' hoặc so sánh với biến 'ADMIN'
        for node in ast.walk(tree):
            # Kiểm tra định nghĩa hàm 'is_admin'
            if isinstance(node, ast.FunctionDef) and node.name == 'is_admin':
                logger.info(f"[check_admin_requirement] Tìm thấy hàm 'is_admin' trong {file_path}")
                return True
            # Kiểm tra so sánh với biến 'ADMIN'
            if isinstance(node, ast.Compare):
                for comparator in node.comparators:
                    if isinstance(comparator, ast.Name) and comparator.id == 'ADMIN':
                        logger.info(f"[check_admin_requirement] Tìm thấy so sánh với biến 'ADMIN' trong {file_path}")
                        return True
        logger.info(f"[check_admin_requirement] Không tìm thấy yêu cầu quyền admin trong {file_path}")
        return False
    except Exception as e:
        logger.error(f"[check_admin_requirement] Lỗi khi phân tích {file_path}: {str(e)}")
        return False

def get_admin_requirements():
    """Thu thập danh sách các module yêu cầu quyền admin và không yêu cầu quyền admin."""
    logger.info("[get_admin_requirements] Bắt đầu quét các module để kiểm tra yêu cầu quyền admin...")
    admin_required = []
    no_admin_required = []
    module_count = 0
    
    if not os.path.exists('modules'):
        logger.warning("[get_admin_requirements] Thư mục 'modules' không tồn tại.")
        return admin_required, no_admin_required

    for module_name in os.listdir('modules'):
        if module_name.endswith('.py') and module_name != '__init__.py':
            module_count += 1
            module_path = os.path.join('modules', module_name)
            logger.info(f"[get_admin_requirements] Đang xử lý module: {module_name}")
            if check_admin_requirement(module_path):
                admin_required.append(module_name[:-3])
            else:
                no_admin_required.append(module_name[:-3])
    
    logger.info(f"[get_admin_requirements] Hoàn tất: Đã xử lý {module_count} module, "
                f"{len(admin_required)} module yêu cầu quyền admin, "
                f"{len(no_admin_required)} module không yêu cầu quyền admin.")
    return admin_required, no_admin_required

def split_messages(admin_required, no_admin_required, total_modules):
    """Chia danh sách module thành các tin nhắn."""
    logger.info(f"[split_messages] Bắt đầu chia {total_modules} module thành các tin nhắn...")
    messages = []
    current_message = [f"📌 Tổng số module hiện có: {total_modules}\n📋 Danh sách module theo yêu cầu quyền admin:\n\n"]
    current_length = len(current_message[0])
    
    # Thêm danh sách module yêu cầu quyền admin
    if admin_required:
        admin_text = "🔐 Module yêu cầu quyền admin:\n" + "\n".join(f"🔸 {module}" for module in admin_required) + "\n"
        admin_length = len(admin_text)
        if current_length + admin_length > MAX_MESSAGE_LENGTH:
            message_content = "\n".join(current_message)
            messages.append(message_content)
            logger.info(f"[split_messages] Đã tạo tin nhắn {len(messages)} với tiêu đề, độ dài: {current_length} ký tự.")
            current_message = [f"📋 Danh sách module (tiếp theo):\n\n"]
            current_length = len(current_message[0])
        current_message.append(admin_text)
        current_length += admin_length
    
    # Thêm danh sách module không yêu cầu quyền admin
    if no_admin_required:
        no_admin_text = "\n🔓 Module không yêu cầu quyền admin:\n" + "\n".join(f"🔸 {module}" for module in no_admin_required)
        no_admin_length = len(no_admin_text)
        if current_length + no_admin_length > MAX_MESSAGE_LENGTH:
            message_content = "\n".join(current_message)
            messages.append(message_content)
            logger.info(f"[split_messages] Đã tạo tin nhắn {len(messages)} với {len(admin_required)} module, độ dài: {current_length} ký tự.")
            current_message = [f"📋 Danh sách module (tiếp theo):\n\n"]
            current_length = len(current_message[0])
        current_message.append(no_admin_text)
        current_length += no_admin_length
    
    if len(current_message) > 1 or current_message[0].endswith("\n\n"):
        message_content = "\n".join(current_message)
        messages.append(message_content)
        logger.info(f"[split_messages] Đã tạo tin nhắn {len(messages)} với phần còn lại, độ dài: {current_length} ký tự.")
    
    logger.info(f"[split_messages] Hoàn tất: Đã tạo {len(messages)} tin nhắn.")
    return messages

def handle_admincheck_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh 'admincheck'."""
    logger.info(f"[handle_admincheck_command] Nhận lệnh 'admincheck' từ author_id: {author_id}, thread_id: {thread_id}")
    logger.info(f"[handle_admincheck_command] Message object: {message_object}")
    logger.info(f"[handle_admincheck_command] thread_type: {thread_type}, type: {type(thread_type)}")
    
    # Gửi reaction
    action = "✅"
    try:
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
        logger.info(f"[handle_admincheck_command] Đã gửi reaction '{action}'.")
    except Exception as e:
        logger.error(f"[handle_admincheck_command] Lỗi khi gửi reaction: {str(e)}")
    
    # Lấy danh sách module yêu cầu quyền admin
    try:
        admin_required, no_admin_required = get_admin_requirements()
    except Exception as e:
        logger.error(f"[handle_admincheck_command] Lỗi khi gọi get_admin_requirements: {str(e)}")
        error_message = "❌ Lỗi hệ thống khi kiểm tra yêu cầu quyền admin."
        try:
            message_to_send = Message(text=error_message)
            client.sendMessage(message_to_send, thread_id, thread_type)
            logger.info("[handle_admincheck_command] Đã gửi tin nhắn lỗi hệ thống.")
        except Exception as e:
            logger.error(f"[handle_admincheck_command] Lỗi khi gửi tin nhắn lỗi: {str(e)}")
        return
    
    if not admin_required and not no_admin_required:
        error_message = "❌ Không tìm thấy module nào trong hệ thống."
        logger.info(f"[handle_admincheck_command] Không tìm thấy module, gửi tin nhắn lỗi: {error_message}")
        try:
            message_to_send = Message(text=error_message)
            client.sendMessage(message_to_send, thread_id, thread_type)
            logger.info("[handle_admincheck_command] Đã gửi tin nhắn lỗi.")
        except Exception as e:
            logger.error(f"[handle_admincheck_command] Lỗi khi gửi tin nhắn lỗi: {str(e)}")
        return

    total_modules = len(admin_required) + len(no_admin_required)
    logger.info(f"[handle_admincheck_command] Tìm thấy {total_modules} module: "
                f"{len(admin_required)} yêu cầu quyền admin, {len(no_admin_required)} không yêu cầu.")
    
    try:
        messages = split_messages(admin_required, no_admin_required, total_modules)
    except Exception as e:
        logger.error(f"[handle_admincheck_command] Lỗi khi chia tin nhắn: {str(e)}")
        error_message = "❌ Lỗi hệ thống khi xử lý danh sách module."
        try:
            message_to_send = Message(text=error_message)
            client.sendMessage(message_to_send, thread_id, thread_type)
            logger.info("[handle_admincheck_command] Đã gửi tin nhắn lỗi hệ thống.")
        except Exception as e:
            logger.error(f"[handle_admincheck_command] Lỗi khi gửi tin nhắn lỗi: {str(e)}")
        return
    
    # Gửi tin nhắn
    for i, msg in enumerate(messages):
        logger.info(f"[handle_admincheck_command] Chuẩn bị gửi tin nhắn {i+1}/{len(messages)}, độ dài: {len(msg)} ký tự.")
        try:
            message_to_send = Message(text=msg)
            client.sendMessage(message_to_send, thread_id, thread_type)
            logger.info(f"[handle_admincheck_command] Đã gửi tin nhắn {i+1}/{len(messages)}.")
        except Exception as e:
            logger.error(f"[handle_admincheck_command] Lỗi khi gửi tin nhắn {i+1}: {str(e)}")
        if i < len(messages) - 1:
            logger.info("[handle_admincheck_command] Tạm dừng 1 giây trước tin nhắn tiếp theo...")
            time.sleep(1)

    logger.info(f"[handle_admincheck_command] Hoàn tất xử lý lệnh 'admincheck', đã gửi {len(messages)} tin nhắn.")

def get_mitaizl():
    """Đăng ký lệnh 'admincheck'."""
    logger.info("[get_mitaizl] Đăng ký lệnh 'admincheck'.")
    return {
        'code.admincheck': handle_admincheck_command
    }