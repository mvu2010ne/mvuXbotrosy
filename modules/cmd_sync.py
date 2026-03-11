import os
import importlib
import time
import logging
from zlapi.models import Message, ThreadType

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Biến des cho module này
des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🔍 So sánh tên lệnh được đăng ký trong hàm get_mitaizl với tên tệp của tất cả các module trong thư mục 'modules'.",
    'tính năng': [
        "📋 Quét và so sánh tên lệnh trong dictionary của get_mitaizl với tên tệp (không bao gồm .py).",
        "🔄 Chia kết quả so sánh thành nhiều tin nhắn nếu vượt quá giới hạn ký tự.",
        "⏱️ Gửi các tin nhắn với độ trễ 1 giây để tránh spam.",
        "⚠️ Thông báo lỗi nếu không tìm thấy module, hàm get_mitaizl, hoặc gặp vấn đề hệ thống."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh compare_command_names để nhận kết quả so sánh tên lệnh và tên tệp.",
        "📌 Ví dụ: compare_command_names (không cần tham số).",
        "✅ Nhận danh sách kết quả so sánh, chia nhỏ nếu dài."
    ]
}

# Giới hạn độ dài tối đa cho mỗi tin nhắn
MAX_MESSAGE_LENGTH = 1500

def get_all_comparisons():
    """Thu thập kết quả so sánh tên lệnh trong get_mitaizl với tên tệp từ các module."""
    logger.info("[get_all_comparisons] Bắt đầu thu thập kết quả so sánh từ các module...")
    comparisons = []
    module_count = 0

    if not os.path.exists('modules'):
        logger.warning("[get_all_comparisons] Thư mục 'modules' không tồn tại.")
        return comparisons

    for module_name in os.listdir('modules'):
        if module_name.endswith('.py') and module_name != '__init__.py':
            module_count += 1
            module_path = f'modules.{module_name[:-3]}'
            file_name = module_name[:-3]  # Tên tệp không có .py
            logger.info(f"[get_all_comparisons] Đang xử lý module: {module_name}")
            try:
                module = importlib.import_module(module_path)
                if hasattr(module, 'get_mitaizl'):
                    try:
                        command_dict = module.get_mitaizl()
                        if not isinstance(command_dict, dict):
                            comparisons.append(
                                f"🔹 Module: {file_name}\n"
                                f"   - Lỗi: get_mitaizl không trả về dictionary ⚠️\n"
                            )
                            logger.info(f"[get_all_comparisons] Module {module_name}: get_mitaizl không trả về dictionary")
                            continue

                        if not command_dict:
                            comparisons.append(
                                f"🔹 Module: {file_name}\n"
                                f"   - Không có lệnh nào được đăng ký ⚠️\n"
                            )
                            logger.info(f"[get_all_comparisons] Module {module_name}: Không có lệnh nào được đăng ký")
                            continue

                        for command_name in command_dict.keys():
                            comparison_result = (
                                f"🔹 Module: {file_name}\n"
                                f"   - Tên lệnh: {command_name}\n"
                                f"   - Tên tệp: {file_name}\n"
                                f"   - Kết quả: {'Giống nhau ✅' if command_name == file_name else 'Khác nhau ❌'}\n"
                            )
                            comparisons.append(comparison_result)
                            logger.info(f"[get_all_comparisons] Đã so sánh {module_name}: {command_name} vs {file_name}")
                    except Exception as e:
                        comparisons.append(
                            f"🔹 Module: {file_name}\n"
                            f"   - Lỗi khi gọi get_mitaizl: {str(e)} ❌\n"
                        )
                        logger.error(f"[get_all_comparisons] Lỗi khi gọi get_mitaizl trong {module_name}: {str(e)}")
                else:
                    comparisons.append(
                        f"🔹 Module: {file_name}\n"
                        f"   - Không có hàm get_mitaizl ⚠️\n"
                    )
                    logger.info(f"[get_all_comparisons] Module {module_name} không có hàm 'get_mitaizl'")
            except Exception as e:
                logger.error(f"[get_all_comparisons] Lỗi khi xử lý {module_name}: {str(e)}")
                comparisons.append(
                    f"🔹 Module: {file_name}\n"
                    f"   - Lỗi hệ thống: {str(e)} ❌\n"
                )

    logger.info(f"[get_all_comparisons] Hoàn tất: Đã xử lý {module_count} module, tìm thấy {len(comparisons)} kết quả.")
    return comparisons

def split_messages(comparisons, total_comparisons):
    """Chia danh sách kết quả so sánh thành các tin nhắn."""
    logger.info(f"[split_messages] Bắt đầu chia {total_comparisons} kết quả thành các tin nhắn...")
    messages = []
    current_message = [f"📌 Tổng số kết quả so sánh: {total_comparisons}\n📋 Kết quả so sánh tên lệnh và tên tệp:\n\n"]
    current_length = len(current_message[0])

    for comparison in comparisons:
        comparison_length = len(comparison) + 1
        if current_length + comparison_length > MAX_MESSAGE_LENGTH:
            message_content = "\n".join(current_message)
            messages.append(message_content)
            logger.info(f"[split_messages] Đã tạo tin nhắn {len(messages)} với {len(current_message)-1} kết quả, độ dài: {current_length} ký tự.")
            current_message = [f"📋 Kết quả so sánh (tiếp theo):\n\n"]
            current_length = len(current_message[0])

        current_message.append(comparison)
        current_length += comparison_length

    if len(current_message) > 1 or current_message[0].endswith("\n\n"):
        message_content = "\n".join(current_message)
        messages.append(message_content)
        logger.info(f"[split_messages] Đã tạo tin nhắn {len(messages)} với {len(current_message)-1} kết quả, độ dài: {current_length} ký tự.")

    logger.info(f"[split_messages] Hoàn tất: Đã tạo {len(messages)} tin nhắn.")
    return messages

def handle_compare_command_names_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh 'compare_command_names'."""
    logger.info(f"[handle_compare_command_names_command] Nhận lệnh 'compare_command_names' từ author_id: {author_id}, thread_id: {thread_id}")
    logger.info(f"[handle_compare_command_names_command] Message object: {message_object}")
    logger.info(f"[handle_compare_command_names_command] thread_type: {thread_type}, type: {type(thread_type)}")

    # Gửi reaction
    action = "✅"
    try:
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
        logger.info(f"[handle_compare_command_names_command] Đã gửi reaction '{action}'.")
    except Exception as e:
        logger.error(f"[handle_compare_command_names_command] Lỗi khi gửi reaction: {str(e)}")

    # Lấy danh sách kết quả so sánh
    try:
        comparisons = get_all_comparisons()
    except Exception as e:
        logger.error(f"[handle_compare_command_names_command] Lỗi khi gọi get_all_comparisons: {str(e)}")
        error_message = "❌ Lỗi hệ thống khi lấy danh sách so sánh."
        try:
            message_to_send = Message(text=error_message)
            client.sendMessage(message_to_send, thread_id, thread_type)
            logger.info("[handle_compare_command_names_command] Đã gửi tin nhắn lỗi hệ thống.")
        except Exception as e:
            logger.error(f"[handle_compare_command_names_command] Lỗi khi gửi tin nhắn lỗi: {str(e)}")
        return

    if not comparisons:
        error_message = "❌ Không tìm thấy module nào trong thư mục 'modules' hoặc không có lệnh nào được đăng ký."
        logger.info(f"[handle_compare_command_names_command] Không có kết quả, gửi tin nhắn lỗi: {error_message}")
        try:
            message_to_send = Message(text=error_message)
            client.sendMessage(message_to_send, thread_id, thread_type)
            logger.info("[handle_compare_command_names_command] Đã gửi tin nhắn lỗi.")
        except Exception as e:
            logger.error(f"[handle_compare_command_names_command] Lỗi khi gửi tin nhắn lỗi: {str(e)}")
        return

    total_comparisons = len(comparisons)
    logger.info(f"[handle_compare_command_names_command] Tìm thấy {total_comparisons} kết quả, bắt đầu chia tin nhắn...")
    try:
        messages = split_messages(comparisons, total_comparisons)
    except Exception as e:
        logger.error(f"[handle_compare_command_names_command] Lỗi khi chia tin nhắn: {str(e)}")
        error_message = "❌ Lỗi hệ thống khi xử lý danh sách kết quả so sánh."
        try:
            message_to_send = Message(text=error_message)
            client.sendMessage(message_to_send, thread_id, thread_type)
            logger.info("[handle_compare_command_names_command] Đã gửi tin nhắn lỗi hệ thống.")
        except Exception as e:
            logger.error(f"[handle_compare_command_names_command] Lỗi khi gửi tin nhắn lỗi: {str(e)}")
        return

    # Gửi tin nhắn
    for i, msg in enumerate(messages):
        logger.info(f"[handle_compare_command_names_command] Chuẩn bị gửi tin nhắn {i+1}/{len(messages)}, độ dài: {len(msg)} ký tự.")
        try:
            message_to_send = Message(text=msg)
            client.sendMessage(message_to_send, thread_id, thread_type)
            logger.info(f"[handle_compare_command_names_command] Đã gửi tin nhắn {i+1}/{len(messages)}.")
        except Exception as e:
            logger.error(f"[handle_compare_command_names_command] Lỗi khi gửi tin nhắn {i+1}: {str(e)}")
        if i < len(messages) - 1:
            logger.info("[handle_compare_command_names_command] Tạm dừng 1 giây trước tin nhắn tiếp theo...")
            time.sleep(1)

    logger.info(f"[handle_compare_command_names_command] Hoàn tất xử lý lệnh 'compare_command_names', đã gửi {len(messages)} tin nhắn.")

def get_mitaizl():
    """Đăng ký lệnh 'compare_command_names'."""
    logger.info("[get_mitaizl] Đăng ký lệnh 'compare_command_names'.")
    return {
        'cmd.sync': handle_compare_command_names_command
    }