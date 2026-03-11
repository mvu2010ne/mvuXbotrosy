from datetime import datetime
import time
import os
import importlib
from zoneinfo import ZoneInfo
from zlapi.models import Message, MultiMsgStyle, MessageStyle, Mention

# Lưu thời gian bot khởi động (theo múi giờ Hồ Chí Minh)
bot_start_time = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))

def send_message_with_style(client, text, thread_id, thread_type, color="#db342e"):
    base_length = len(text)
    adjusted_length = base_length + 355
    style = MultiMsgStyle([
        MessageStyle(offset=0, length=adjusted_length, style="color", color=color, auto_format=False),
        MessageStyle(offset=0, length=adjusted_length, style="font", size="6", auto_format=False)
    ])
    client.send(Message(text=text, style=style), thread_id=thread_id, thread_type=thread_type, ttl=60000)

def get_total_friends(bot):
    try:
        friends = bot.fetchAllFriends()
        return len(friends)
    except Exception as e:
        print(f"Lỗi khi lấy danh sách bạn bè: {e}")
        return 0

def get_all_mitaizl():
    mitaizl = {}
    for module_name in os.listdir('modules'):
        if module_name.endswith('.py') and module_name != '__init__.py':
            module_path = f'modules.{module_name[:-3]}'
            module = importlib.import_module(module_path)
            if hasattr(module, 'get_mitaizl'):
                module_mitaizl = module.get_mitaizl()
                mitaizl.update(module_mitaizl)
    return list(mitaizl.keys())

def handle_boti4_command(message, message_object, thread_id, thread_type, author_id, bot):
    # Sử dụng bot.sendReaction thay vì client.sendReaction
    action = "✅ "
    bot.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    
    # Lấy thời gian hiện tại theo múi giờ Hồ Chí Minh
    current_time = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%H:%M %d/%m/%Y")
    
    # Tính thời gian bot đã online được bao lâu
    uptime_delta = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")) - bot_start_time
    uptime_seconds = int(uptime_delta.total_seconds())
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours} giờ {minutes} phút {seconds} giây"
    
    # Lấy thông tin các nhóm bot đã tham gia
    all_groups = bot.fetchAllGroups()
    total_groups = len(all_groups.gridVerMap) if hasattr(all_groups, "gridVerMap") else 0
    
    # Tính tổng số thành viên từ tất cả các nhóm
    group_ids = set(all_groups.gridVerMap.keys()) if hasattr(all_groups, "gridVerMap") else set()
    total_members = 0
    for gid in group_ids:
        group_info = bot.fetchGroupInfo(gid).gridInfoMap[gid]
        total_members += group_info.totalMember

    # Định dạng tổng số thành viên theo kiểu phân cách phần nghìn với dấu chấm
    formatted_total_members = format(total_members, ",").replace(",", ".")
    
    # Lấy tổng số bạn bè
    total_friends = get_total_friends(bot)
    
    # Lấy tổng số lệnh của bot
    commands = get_all_mitaizl()
    total_commands = len(commands)
    
    # Soạn tin nhắn phản hồi với icon và khung viền
    text = (
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ Thời gian hiện tại: {current_time}\n"
        f"🟢 Bot đã online được: {uptime_str}\n"
        f"👥 Tổng số nhóm đang hoạt động: {total_groups}\n"
        f"👤 Tổng số thành viên: {formatted_total_members} người\n"
        f"🤝 Tổng số bạn bè của bot: {total_friends}\n"
        f"📋 Tổng số lệnh bot có: {total_commands}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    send_message_with_style(bot, text, thread_id, thread_type)

def get_mitaizl():
    return {
        'bot.i4': handle_boti4_command  
    }
