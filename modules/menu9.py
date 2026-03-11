import os
import importlib
from zlapi.models import Message
from datetime import datetime

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Hiển thị toàn bộ các lệnh hiện có của bot.",
    'tính năng': [
        "📜 Liệt kê tất cả các lệnh hiện có",
        "🔍 Tự động quét thư mục 'modules' để lấy danh sách lệnh",
        "🖼️ Gửi kèm hình ảnh minh họa menu",
        "⚡ Phản hồi ngay khi người dùng nhập lệnh"
    ],
    'hướng dẫn sử dụng': [
        "📩 Dùng lệnh 'menu9' để hiển thị toàn bộ các lệnh hiện có của bot.",
        "📌 Ví dụ: nhập menu9 để hiển thị danh sách lệnh.",
        "✅ Nhận thông báo trạng thái và kết quả ngay lập tức."
    ]
}

def get_all_mitaizl():
    """
    Lấy toàn bộ các lệnh từ thư mục modules.
    """
    mitaizl = {}
    for module_name in os.listdir('modules'):
        if module_name.endswith('.py') and module_name != '__init__.py':
            module_path = f'modules.{module_name[:-3]}'
            module = importlib.import_module(module_path)
            if hasattr(module, 'get_mitaizl'):
                get_mitaizl = module.get_mitaizl()
                mitaizl.update(get_mitaizl)
    command_names = list(mitaizl.keys())
    return command_names

def split_message(content, max_length=2000):
    """
    Chia nội dung thành nhiều phần nếu vượt quá độ dài tối đa.
    """
    if len(content) <= max_length:
        return [content]
    
    messages = []
    current_message = ""
    lines = content.split('\n')
    
    for line in lines:
        if len(current_message) + len(line) + 1 > max_length:
            messages.append(current_message.strip())
            current_message = line + "\n"
        else:
            current_message += line + "\n"
    
    if current_message:
        messages.append(current_message.strip())
    
    return messages

def handle_menu_command(message, message_object, thread_id, thread_type, author_id, client):
    """
    Xử lý lệnh menu để liệt kê toàn bộ các lệnh hiện có, chia thành nhiều tin nhắn nếu cần.
    """
    # Lấy tất cả các lệnh
    command_names = get_all_mitaizl()
    # Tính tổng số lệnh và tạo danh sách các lệnh
    total_mitaizl = len(command_names)
    # Tạo danh sách lệnh với số thứ tự
    numbered_mitaizl = [f"✧ {i+1}. {name}" for i, name in enumerate(command_names)]
    
    # Tạo nội dung menu
    menu_message = (
        f"📜 Danh sách lệnh - 𝑹𝑶𝑺𝒀 𝑨𝑹𝑬𝑵𝑨 𝑺𝑯𝑶𝑷 📜\n"
        f"────────────────────\n"
        f"👾 Admin: \n"
        f"⚙️ Phiên bản: 1.0.0\n"
        f"🌸 Tổng số lệnh: {total_mitaizl}\n"
        f"────────────────────\n"
        f"Danh sách lệnh:\n" + "\n".join(numbered_mitaizl) + "\n"
        f"────────────────────\n"
        f"ℹ️ Hướng dẫn: Gõ 'menu9' để xem danh sách.\n"
        f"📌 Ví dụ: menu9\n"
        f"────────────────────"
    )
    
    # Chia tin nhắn nếu cần
    messages = split_message(menu_message, max_length=2000)
    
    # Gửi lần lượt các tin nhắn
    for i, msg in enumerate(messages):
        if i == 0:  # Tin nhắn đầu tiên kèm ảnh
            client.sendLocalImage(
                "2.jpg",
                thread_id=thread_id,
                thread_type=thread_type,
                message=Message(text=msg),
                ttl=120000
            )
        else:  # Các tin nhắn tiếp theo chỉ gửi text
            client.sendMessage(
                Message(text=msg),
                thread_id=thread_id,
                thread_type=thread_type,
                ttl=120000
            )

def get_mitaizl():
    """
    Hàm trả về danh sách lệnh và hàm xử lý tương ứng.
    """
    return {
        'menu9': handle_menu_command
    }