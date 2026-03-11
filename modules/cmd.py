import os
import importlib
from zlapi.models import Message, MultiMsgStyle, MessageStyle
from config import ADMIN

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Quản lý các lệnh bằng cách mở hoặc đóng chúng theo yêu cầu.",
    'tính năng': [
        "📂 Mở lệnh riêng lẻ hoặc nhiều lệnh cùng lúc",
        "📌 Đóng lệnh riêng lẻ hoặc nhiều lệnh đã mở",
        "⚡ Mở tất cả các lệnh cùng lúc",
        "🗑️ Đóng toàn bộ lệnh chỉ với một lệnh duy nhất",
        "🧾 Liệt kê các lệnh đã bị đóng",
        "🚀 Kiểm tra lỗi khi mở hoặc đóng lệnh và thông báo rõ ràng",
        "🔍 Tự động quét thư mục 'modules' để lấy danh sách lệnh có sẵn"
    ],
    'hướng dẫn sử dụng': [
        "📩 Dùng lệnh 'cmd [open|close|openall|closeall|list] [tên lệnh]' để quản lý lệnh.",
        "📌 Ví dụ: cmd open example1 example2 để mở nhiều lệnh",
        "📌 Ví dụ: cmd close example1,example2 để đóng nhiều lệnh",
        "📌 Ví dụ: cmd list để xem các lệnh chưa được mở.",
        "✅ Nhận thông báo trạng thái và kết quả ngay lập tức."
    ]
}

def is_admin(author_id):
    return author_id in ADMIN

def get_all_mitaizl():
    mitaizl = {}
    for module_name in os.listdir('modules'):
        if module_name.endswith('.py') and module_name != '__init__.py':
            module_path = f'modules.{module_name[:-3]}'
            try:
                module = importlib.import_module(module_path)
                if hasattr(module, 'get_mitaizl'):
                    module_mitaizl = module.get_mitaizl()
                    mitaizl.update(module_mitaizl)
            except Exception as e:
                print(f"Lỗi khi load module {module_name}: {e}")
    return mitaizl

# Hàm hỗ trợ định dạng tin nhắn với style
def format_message(text, color="#db342e", bold=True, size="16"):
    styles = [
        MessageStyle(offset=0, length=len(text), style="color", color=color, auto_format=False),
        MessageStyle(offset=0, length=len(text), style="bold" if bold else "regular", size=size, auto_format=False)
    ]
    return Message(text=text, style=MultiMsgStyle(styles))

def handle_cmd_command(message, message_object, thread_id, thread_type, author_id, client):
    if not is_admin(author_id):
        error_msg = "• Bạn Không Có Quyền! Chỉ có admin mới có thể sử dụng lệnh này."
        client.replyMessage(format_message(error_msg), message_object, thread_id, thread_type)
        return
            
    content = message.strip().split()

    if len(content) < 2:
        error_message = "❌ Bạn cần cung cấp lệnh (open, close, openall, closeall, list)."
        client.replyMessage(format_message(error_message), message_object, thread_id, thread_type)
        return

    action = content[1].lower()
    command_map = client.command_handler.mitaizl

    if action == 'open' and len(content) >= 3:
        # Lấy danh sách lệnh, hỗ trợ phân tách bằng dấu cách hoặc dấu phẩy
        command_names = []
        for cmd in content[2:]:
            command_names.extend(cmd.split(','))
        command_names = [cmd.strip() for cmd in command_names if cmd.strip()]
        
        if not command_names:
            error_message = "❌ Không có lệnh nào được cung cấp để mở."
            client.replyMessage(format_message(error_message), message_object, thread_id, thread_type)
            return

        all_mitaizl = get_all_mitaizl()
        results = []
        for command_name in command_names:
            if command_name in all_mitaizl:
                try:
                    command_map[command_name] = all_mitaizl[command_name]
                    results.append(f"✅ Mở thành công lệnh '{command_name}'.")
                except Exception as e:
                    results.append(f"❌ Mở lệnh '{command_name}' thất bại: {str(e)}")
            else:
                results.append(f"⚠️ Lệnh '{command_name}' không tồn tại.")
        
        result_message = "\n".join(results)
        client.replyMessage(format_message(result_message), message_object, thread_id, thread_type)

    elif action == 'close' and len(content) >= 3:
        # Lấy danh sách lệnh, hỗ trợ phân tách bằng dấu cách hoặc dấu phẩy
        command_names = []
        for cmd in content[2:]:
            command_names.extend(cmd.split(','))
        command_names = [cmd.strip() for cmd in command_names if cmd.strip()]
        
        if not command_names:
            error_message = "❌ Không có lệnh nào được cung cấp để đóng."
            client.replyMessage(format_message(error_message), message_object, thread_id, thread_type)
            return

        results = []
        for command_name in command_names:
            if command_name in command_map:
                del command_map[command_name]
                results.append(f"✅ Đóng thành công lệnh '{command_name}'.")
            else:
                results.append(f"⚠️ Lệnh '{command_name}' chưa được mở hoặc không tồn tại.")
        
        result_message = "\n".join(results)
        client.replyMessage(format_message(result_message), message_object, thread_id, thread_type)

    elif action == 'openall':
        all_mitaizl = get_all_mitaizl()
        success_count = 0
        for command_name, command_func in all_mitaizl.items():
            try:
                command_map[command_name] = command_func
                success_count += 1
            except Exception as e:
                print(f"Không thể mở {command_name}: {e}")
        message_text = f"✅ Đã mở thành công {success_count} lệnh."
        client.replyMessage(format_message(message_text), message_object, thread_id, thread_type)

    elif action == "closeall":
        safe_commands = {"cmd", "menu", "help", "rs"}
        is_safe_mode = len(content) >= 3 and content[2].lower() == "safe"

        if is_safe_mode:
            removed = 0
            for key in list(command_map.keys()):
                if key not in safe_commands:
                    del command_map[key]
                    removed += 1
            kept = [k for k in safe_commands if k in command_map]
            message_text = f"🧹 Đã đóng {removed} lệnh. Các lệnh giữ lại: {', '.join(kept)}"
            client.replyMessage(format_message(message_text), message_object, thread_id, thread_type)
        else:
            count = len(command_map)
            command_map.clear()
            message_text = f"🧨 Đã đóng toàn bộ {count} lệnh."
            client.replyMessage(format_message(message_text), message_object, thread_id, thread_type)

    elif action == 'list':
        all_mitaizl = get_all_mitaizl()
        current_loaded = set(command_map.keys())
        all_available = set(all_mitaizl.keys())
        unloaded = sorted(all_available - current_loaded)

        if not unloaded:
            message_text = "✅ Tất cả các lệnh đều đang được mở."
        else:
            message_text = "📋 Danh sách lệnh bị đóng :\n• " + "\n• ".join(unloaded)
        client.replyMessage(format_message(message_text), message_object, thread_id, thread_type)

    else:
        error_message = "❌ Cú pháp không đúng hoặc thiếu tham số."
        client.replyMessage(format_message(error_message), message_object, thread_id, thread_type)

def get_mitaizl():
    return {
        'cmd': handle_cmd_command
    }