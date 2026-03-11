
from zlapi.models import *
import re
from config import IMEI, ADMIN  # Nhập IMEI và danh sách ADMIN từ file cấu hình
import time

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Bot hỗ trợ rời khỏi nhóm Zalo dựa trên danh sách ID nhóm hoặc liên kết mời do người dùng cung cấp.",
    'tính năng': [
        "🚪 Rời khỏi các nhóm Zalo theo danh sách ID nhóm hoặc liên kết mời[](https://zalo.me/g/...).",
        "🔍 Lấy thông tin chi tiết nhóm trước khi rời, bao gồm tên trưởng nhóm, phó nhóm và số thành viên.",
        "🔔 Thông báo kết quả rời khỏi nhóm với thời gian sống (TTL) khác nhau.",
        "🔒 Chỉ quản trị viên mới có quyền sử dụng lệnh này.",
        "⏱️ Thêm độ trễ giữa các yêu cầu để tránh lỗi API."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh để bot rời khỏi nhóm Zalo kèm theo danh sách ID nhóm hoặc liên kết mời.",
        "📌 Hỗ trợ nhập nhiều ID nhóm hoặc liên kết cùng lúc, cách nhau bằng dấu cách.",
        "✅ Nhận thông báo trạng thái rời khỏi nhóm ngay lập tức.",
        "📌 Ví dụ: bot.leaveid 1234567890 https://zalo.me/g/abc123456"
    ]
}

def send_message_with_style(client, text, thread_id, thread_type, color="#000000", max_length=1500, delay=3):
    """
    Gửi tin nhắn với định dạng màu sắc và font chữ, chia nhỏ tin nhắn nếu quá dài.
    """
    base_length = len(text)
    adjusted_length = base_length + 355
    style = MultiMsgStyle([
        MessageStyle(
            offset=0,
            length=adjusted_length,
            style="color",
            color=color,
            auto_format=False,
        ),
        MessageStyle(
            offset=0,
            length=adjusted_length,
            style="font",
            size="1",
            auto_format=False
        )
    ])
    
    chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
    for chunk in chunks:
        client.send(Message(text=chunk, style=style), thread_id=thread_id, thread_type=thread_type, ttl=60000)
        time.sleep(delay)

def handle_leave_group_by_id(message, message_object, thread_id, thread_type, author_id, bot):
    """
    Rời nhóm dựa trên danh sách ID nhóm hoặc liên kết mời do người dùng cung cấp, đồng thời lấy thông tin chi tiết nhóm.
    """
    if author_id not in ADMIN:
        error_msg = "🚫 Bạn không có quyền sử dụng lệnh này!"
        send_message_with_style(bot, error_msg, thread_id, thread_type)
        print(f"[DEBUG] Người dùng {author_id} không có quyền sử dụng lệnh.")
        return
    
    bot.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
    print(f"[DEBUG] Đã gửi phản hồi ✅ cho tin nhắn từ {author_id}")
    
    args = message.split()
    if len(args) < 2:
        send_message_with_style(bot, "⚠️ Vui lòng nhập ít nhất một ID nhóm hoặc liên kết mời. Ví dụ: bot.leaveid 1234567890 https://zalo.me/g/abc123456", thread_id, thread_type)
        print("[DEBUG] Không đủ tham số: ", args)
        return
    
    inputs = args[1:]
    msg = "🚪 Đang rời khỏi các nhóm:\n"
    print(f"[DEBUG] Đầu vào nhận được: {inputs}")
    
    for input_item in inputs:
        try:
            # Kiểm tra xem đầu vào là liên kết hay ID nhóm
            if input_item.startswith("http://") or input_item.startswith("https://"):
                # Xử lý liên kết mời
                url = input_item.strip()
                print(f"[DEBUG] Xử lý liên kết: {url}")
                try:
                    group_info = bot.getiGroup(url)
                    print(f"[DEBUG] Phản hồi từ getiGroup({url}): {group_info}")
                    if not isinstance(group_info, dict) or 'groupId' not in group_info:
                        error_msg = group_info.get("error_message", "Không nhận được dữ liệu từ API") if group_info else "Không nhận được dữ liệu từ liên kết"
                        msg += f"❌ Lỗi khi xử lý liên kết {url} : {error_msg}\n"
                        print(f"[DEBUG] Lỗi khi xử lý liên kết {url}: {error_msg}")
                        continue
                    group_id = group_info.get("groupId")
                    if not group_id:
                        msg += f"❌ Không thể lấy ID nhóm từ liên kết: {url}\n"
                        print(f"[DEBUG] Không lấy được groupId từ liên kết: {url}")
                        continue
                except Exception as e:
                    msg += f"❌ Lỗi khi xử lý liên kết {url}: {str(e)}\n"
                    print(f"[DEBUG] Ngoại lệ khi xử lý liên kết {url}: {str(e)}")
                    continue
            else:
                # Xử lý ID nhóm
                if not input_item.isdigit():
                    msg += f"❌ ID nhóm không hợp lệ: {input_item}\n"
                    print(f"[DEBUG] ID nhóm không hợp lệ: {input_item}")
                    continue
                group_id = input_item
                print(f"[DEBUG] Xử lý ID nhóm: {group_id}")

            # Lấy thông tin nhóm trước khi rời
            try:
                group_info_response = bot.fetchGroupInfo(group_id)
                print(f"[DEBUG] Phản hồi từ fetchGroupInfo({group_id}): {group_info_response}")
                if not group_info_response or not hasattr(group_info_response, 'gridInfoMap'):
                    msg += f"❌ Không tìm thấy thông tin nhóm {group_id}: Nhóm không tồn tại hoặc bot không có quyền truy cập\n"
                    print(f"[DEBUG] fetchGroupInfo({group_id}) trả về None hoặc không có gridInfoMap")
                    continue
                group_data = group_info_response.gridInfoMap.get(group_id)
                print(f"[DEBUG] group_data cho {group_id}: {group_data}")
                if not group_data:
                    msg += f"❌ Không tìm thấy thông tin nhóm {group_id}: Nhóm không tồn tại\n"
                    print(f"[DEBUG] gridInfoMap.get({group_id}) trả về None")
                    continue
            except Exception as e:
                msg += f"❌ Lỗi khi lấy thông tin nhóm {group_id}: {str(e)}\n"
                print(f"[DEBUG] Ngoại lệ khi lấy thông tin nhóm {group_id}: {str(e)}")
                continue
            
            # Lấy tên trưởng nhóm và phó nhóm
            def get_name(user_id):
                try:
                    user_info = bot.fetchUserInfo(user_id)
                    print(f"[DEBUG] Phản hồi từ fetchUserInfo({user_id}): {user_info}")
                    return user_info.changed_profiles[user_id].zaloName
                except (KeyError, AttributeError) as e:
                    print(f"[DEBUG] Lỗi khi lấy tên người dùng {user_id}: {str(e)}")
                    return "Không tìm thấy tên"
            
            group_name = group_data.name
            leader_name = get_name(group_data.creatorId)
            admin_names = ", ".join([get_name(admin_id) for admin_id in group_data.adminIds])
            total_members = group_data.totalMember
            print(f"[DEBUG] Thông tin nhóm {group_id}: tên={group_name}, trưởng nhóm={leader_name}, phó nhóm={admin_names}, số thành viên={total_members}")
            
            # Rời nhóm
            try:
                bot.leaveGroup(group_id, imei=IMEI)
                msg += (
                    f"✅ Đã rời khỏi nhóm: {group_name}\n"
                    f"👤 Trưởng nhóm: {leader_name}\n"
                    f"👥 Phó nhóm: {admin_names}\n"
                    f"👤 Số thành viên: {total_members}\n"
                    f"-----------------------------------\n"
                )
                print(f"[DEBUG] Đã rời nhóm {group_id} thành công")
            except Exception as e:
                msg += f"❌ Lỗi khi rời nhóm {group_id}: {str(e)}\n"
                print(f"[DEBUG] Lỗi khi rời nhóm {group_id}: {str(e)}")
                
            time.sleep(1)  # Độ trễ giữa các yêu cầu để tránh lỗi API
                
        except Exception as e:
            msg += f"❌ Lỗi không xác định khi xử lý {input_item}: {str(e)}\n"
            print(f"[DEBUG] Lỗi không xác định khi xử lý {input_item}: {str(e)}")
    
    send_message_with_style(bot, msg, thread_id, thread_type, color="#db342e", max_length=1500, delay=3)
    print("[DEBUG] Đã gửi thông báo kết quả rời nhóm")

def get_mitaizl():
    return {
        '`': handle_leave_group_by_id
    }
