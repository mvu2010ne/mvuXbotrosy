import os
import importlib
import time
from zlapi.models import Message, ThreadType
import logging

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Biến des cho module này
des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🔍 Lấy danh sách mô tả của tất cả các lệnh trong hệ thống.",
    'tính năng': [
        "📋 Thu thập mô tả từ tất cả các module trong thư mục 'modules'.",
        "🔍 Kiểm tra và báo cáo các module thiếu thuộc tính 'des'.",
        "🔄 Chia danh sách mô tả thành nhiều tin nhắn nếu vượt quá giới hạn ký tự.",
        "⏱️ Gửi các tin nhắn với độ trễ 1 giây để tránh spam.",
        "⚠️ Thông báo lỗi nếu không tìm thấy mô tả hoặc gặp vấn đề hệ thống."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh code.desc để nhận danh sách mô tả các lệnh.",
        "📌 Ví dụ: code.desc (không cần tham số).",
        "✅ Nhận danh sách mô tả các lệnh, danh sách module thiếu 'des', chia nhỏ nếu dài."
    ]
}

# Giới hạn độ dài tối đa cho mỗi tin nhắn
MAX_MESSAGE_LENGTH = 1500

def get_all_descriptions():
    """Thu thập mô tả từ các module trong thư mục 'modules' và kiểm tra module thiếu 'des'."""
    logger.info("[get_all_descriptions] Bắt đầu thu thập mô tả từ các module...")
    descriptions = []
    missing_des_modules = []  # Danh sách các module thiếu 'des'
    module_count = 0
    
    if not os.path.exists('modules'):
        logger.warning("[get_all_descriptions] Thư mục 'modules' không tồn tại.")
        return descriptions, missing_des_modules

    for module_name in os.listdir('modules'):
        if module_name.endswith('.py') and module_name != '__init__.py':
            module_count += 1
            module_path = f'modules.{module_name[:-3]}'
            logger.info(f"[get_all_descriptions] Đang xử lý module: {module_name}")
            try:
                module = importlib.import_module(module_path)
                if hasattr(module, 'des'):
                    des = getattr(module, 'des')
                    description = des.get('mô tả', 'Chưa có mô tả')
                    descriptions.append(f"🔹 {module_name[:-3]}: {description}")
                    logger.info(f"[get_all_descriptions] Đã lấy mô tả từ {module_name}: {description}")
                else:
                    missing_des_modules.append(module_name[:-3])
                    logger.info(f"[get_all_descriptions] Module {module_name} không có thuộc tính 'des'")
            except Exception as e:
                logger.error(f"[get_all_descriptions] Lỗi khi lấy mô tả từ {module_name}: {str(e)}")
    
    logger.info(f"[get_all_descriptions] Hoàn tất: Đã xử lý {module_count} module, tìm thấy {len(descriptions)} mô tả, {len(missing_des_modules)} module thiếu 'des'.")
    return descriptions, missing_des_modules

def split_messages(descriptions, missing_des_modules, total_desc):
    """Chia danh sách mô tả và danh sách module thiếu 'des' thành các tin nhắn."""
    logger.info(f"[split_messages] Bắt đầu chia {total_desc} mô tả và {len(missing_des_modules)} module thiếu 'des' thành các tin nhắn...")
    messages = []
    current_message = [f"📌 Tổng số lệnh hiện có: {total_desc}\n📋 Danh sách mô tả các lệnh:\n\n"]
    current_length = len(current_message[0])
    
    # Thêm danh sách mô tả
    for desc in descriptions:
        desc_length = len(desc) + 1
        if current_length + desc_length > MAX_MESSAGE_LENGTH:
            message_content = "\n".join(current_message)
            messages.append(message_content)
            logger.info(f"[split_messages] Đã tạo tin nhắn {len(messages)} với {len(current_message)-1} mô tả, độ dài: {current_length} ký tự.")
            current_message = [f"📋 Danh sách mô tả các lệnh (tiếp theo):\n\n"]
            current_length = len(current_message[0])
        
        current_message.append(desc)
        current_length += desc_length
    
    # Thêm danh sách module thiếu 'des' vào tin nhắn cuối
    if missing_des_modules:
        missing_des_text = "\n\n⚠️ Các module thiếu thuộc tính 'des':\n" + "\n".join(f"🔸 {module}" for module in missing_des_modules)
        missing_des_length = len(missing_des_text)
        if current_length + missing_des_length > MAX_MESSAGE_LENGTH:
            message_content = "\n".join(current_message)
            messages.append(message_content)
            logger.info(f"[split_messages] Đã tạo tin nhắn {len(messages)} với {len(current_message)-1} mô tả, độ dài: {current_length} ký tự.")
            current_message = [f"📋 Danh sách mô tả các lệnh (tiếp theo):\n\n"]
            current_length = len(current_message[0])
        
        current_message.append(missing_des_text)
        current_length += missing_des_length
    
    if len(current_message) > 1 or current_message[0].endswith("\n\n"):
        message_content = "\n".join(current_message)
        messages.append(message_content)
        logger.info(f"[split_messages] Đã tạo tin nhắn {len(messages)} với {len(current_message)-1} mô tả, độ dài: {current_length} ký tự.")
    
    logger.info(f"[split_messages] Hoàn tất: Đã tạo {len(messages)} tin nhắn.")
    return messages

def handle_desc_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh 'desc'."""
    logger.info(f"[handle_desc_command] Nhận lệnh 'desc' từ author_id: {author_id}, thread_id: {thread_id}")
    logger.info(f"[handle_desc_command] Message object: {message_object}")
    logger.info(f"[handle_desc_command] thread_type: {thread_type}, type: {type(thread_type)}")
    
    # Gửi reaction
    action = "✅"
    try:
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
        logger.info(f"[handle_desc_command] Đã gửi reaction '{action}'.")
    except Exception as e:
        logger.error(f"[handle_desc_command] Lỗi khi gửi reaction: {str(e)}")
    
    # Lấy danh sách mô tả và module thiếu 'des'
    try:
        descriptions, missing_des_modules = get_all_descriptions()
    except Exception as e:
        logger.error(f"[handle_desc_command] Lỗi khi gọi get_all_descriptions: {str(e)}")
        desc_message = "❌ Lỗi hệ thống khi lấy danh sách mô tả."
        try:
            message_to_send = Message(text=desc_message)
            client.sendMessage(message_to_send, thread_id, thread_type)
            logger.info("[handle_desc_command] Đã gửi tin nhắn lỗi hệ thống.")
        except Exception as e:
            logger.error(f"[handle_desc_command] Lỗi khi gửi tin nhắn lỗi: {str(e)}")
        return
    
    if not descriptions and not missing_des_modules:
        desc_message = "❌ Không tìm thấy mô tả nào trong hệ thống."
        logger.info(f"[handle_desc_command] Không có mô tả, gửi tin nhắn lỗi: {desc_message}")
        try:
            message_to_send = Message(text=desc_message)
            client.sendMessage(message_to_send, thread_id, thread_type)
            logger.info("[handle_desc_command] Đã gửi tin nhắn lỗi.")
        except Exception as e:
            logger.error(f"[handle_desc_command] Lỗi khi gửi tin nhắn lỗi: {str(e)}")
        return

    total_desc = len(descriptions)
    logger.info(f"[handle_desc_command] Tìm thấy {total_desc} mô tả và {len(missing_des_modules)} module thiếu 'des', bắt đầu chia tin nhắn...")
    try:
        messages = split_messages(descriptions, missing_des_modules, total_desc)
    except Exception as e:
        logger.error(f"[handle_desc_command] Lỗi khi chia tin nhắn: {str(e)}")
        desc_message = "❌ Lỗi hệ thống khi xử lý danh sách mô tả."
        try:
            message_to_send = Message(text=desc_message)
            client.sendMessage(message_to_send, thread_id, thread_type)
            logger.info("[handle_desc_command] Đã gửi tin nhắn lỗi hệ thống.")
        except Exception as e:
            logger.error(f"[handle_desc_command] Lỗi khi gửi tin nhắn lỗi: {str(e)}")
        return
    
    # Gửi tin nhắn
    for i, msg in enumerate(messages):
        logger.info(f"[handle_desc_command] Chuẩn bị gửi tin nhắn {i+1}/{len(messages)}, độ dài: {len(msg)} ký tự.")
        try:
            message_to_send = Message(text=msg)
            client.sendMessage(message_to_send, thread_id, thread_type)
            logger.info(f"[handle_desc_command] Đã gửi tin nhắn {i+1}/{len(messages)}.")
        except Exception as e:
            logger.error(f"[handle_desc_command] Lỗi khi gửi tin nhắn {i+1}: {str(e)}")
        if i < len(messages) - 1:
            logger.info("[handle_desc_command] Tạm dừng 1 giây trước tin nhắn tiếp theo...")
            time.sleep(1)

    logger.info(f"[handle_desc_command] Hoàn tất xử lý lệnh 'desc', đã gửi {len(messages)} tin nhắn.")

def get_mitaizl():
    """Đăng ký lệnh 'desc'."""
    logger.info("[get_mitaizl] Đăng ký lệnh 'desc'.")
    return {
        'code.desc': handle_desc_command
    }