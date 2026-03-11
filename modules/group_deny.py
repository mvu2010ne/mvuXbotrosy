from zlapi.models import Message, ZaloAPIException, ThreadType
from datetime import datetime
import json

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🔍 Tìm và từ chối thành viên trong danh sách chờ duyệt của nhóm Zalo theo tên hoặc viết tắt.",
    'tính năng': [
        "📋 Tìm thành viên chờ duyệt theo tên hoặc viết tắt.",
        "❌ Từ chối thành viên tìm thấy (yêu cầu quyền admin).",
        "✅ Kiểm tra quyền admin tự động.",
        "⚠️ Thông báo lỗi chi tiết nếu không tìm thấy thành viên hoặc gặp vấn đề API.",
        "📅 Hiển thị tên, ID và ngày tạo tài khoản của thành viên chờ duyệt."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh group.findandreject <tên> để tìm và từ chối thành viên chờ duyệt.",
        "📌 Ví dụ: group.findandreject Minh.",
        "✅ Nhận thông báo kết quả từ chối hoặc lỗi nếu không tìm thấy thành viên."
    ]
}

# Giới hạn độ dài tin nhắn (ký tự)
MAX_MESSAGE_LENGTH = 1000

# Hàm gửi tin nhắn phản hồi
def send_response(client, message_object, thread_id, thread_type, text):
    print(f"[GỬI_TIN_NHẮN] Đang gửi tin nhắn: {text}")
    client.sendMessage(Message(text=text.strip()), thread_id, thread_type, ttl=60000)

# Hàm kiểm tra xem người dùng có phải là admin không
def is_admin(client, thread_id, author_id, message_object, thread_type):
    print(f"[KIỂM_TRA_QUYỀN] Kiểm tra quyền admin cho author_id {author_id} trong thread_id {thread_id}")
    try:
        group_info = client.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
        creator_id = group_info.get('creatorId')
        admin_ids = group_info.get('adminIds', []) or []
        all_admin_ids = set(admin_ids)
        all_admin_ids.add(creator_id)
        all_admin_ids.add("3299675674241805615")  # ID admin cứng
        print(f"[KIỂM_TRA_QUYỀN] ID người tạo: {creator_id}, Danh sách admin: {admin_ids}, Tất cả admin: {all_admin_ids}")
        is_admin_user = str(author_id) in all_admin_ids
        print(f"[KIỂM_TRA_QUYỀN] Người dùng có phải admin? {is_admin_user}")
        return is_admin_user, None
    except Exception as e:
        print(f"[KIỂM_TRA_QUYỀN] Lỗi: {str(e)}")
        return False, f"Lỗi kiểm tra quyền admin: {str(e)}"

# Hàm lấy danh sách thành viên đang chờ duyệt (tương tự group_pending.py)
def get_pending_members(client, group_id, message_object):
    print(f"[LẤY_THÀNH_VIÊN_CHỜ] Đang lấy danh sách thành viên chờ duyệt cho group_id {group_id}")
    try:
        group_info = client.fetchGroupInfo(group_id).gridInfoMap[group_id]
        pending_members = group_info.pendingApprove.get('uids', [])
        print(f"[LẤY_THÀNH_VIÊN_CHỜ] Danh sách ID thành viên chờ: {pending_members}")
        
        if not pending_members:
            print("[LẤY_THÀNH_VIÊN_CHỜ] Không tìm thấy thành viên chờ duyệt")
            return None, {"error_code": 1337, "error_message": "Không có thành viên đang chờ duyệt hoặc bot không có quyền"}
        
        member_info_list = []
        for member_id in pending_members:
            print(f"[LẤY_THÀNH_VIÊN_CHỜ] Lấy thông tin cho member_id {member_id}")
            try:
                info_response = client.fetchUserInfo(member_id)
                profiles = info_response.unchanged_profiles or info_response.changed_profiles
                info = profiles[str(member_id)]
                create_time = info.createdTs
                if isinstance(create_time, int):
                    create_time = datetime.fromtimestamp(create_time).strftime("%d/%m/%Y")
                else:
                    create_time = "Không xác định"
                member_info_list.append({
                    'id': member_id,
                    'zaloName': info.zaloName,
                    'create_time': create_time
                })
                print(f"[LẤY_THÀNH_VIÊN_CHỜ] Thêm thành viên: ID={member_id}, Tên={info.zaloName}, Ngày_tạo={create_time}")
            except Exception as e:
                print(f"[LẤY_THÀNH_VIÊN_CHỜ] Lỗi khi lấy thông tin cho member_id {member_id}: {str(e)}")
                member_info_list.append({
                    'id': member_id,
                    'zaloName': "Không xác định",
                    'create_time': "Không xác định"
                })
        print(f"[LẤY_THÀNH_VIÊN_CHỜ] Danh sách thành viên cuối cùng: {member_info_list}")
        return member_info_list, None
    except ZaloAPIException as e:
        print(f"[LẤY_THÀNH_VIÊN_CHỜ] Lỗi ZaloAPIException: {str(e)}")
        return None, {"error_code": -1, "error_message": f"Lỗi API: {str(e)}"}
    except Exception as e:
        print(f"[LẤY_THÀNH_VIÊN_CHỜ] Lỗi chung: {str(e)}")
        return None, {"error_code": -1, "error_message": f"Lỗi không xác định: {str(e)}"}

# Hàm từ chối thành viên trong danh sách chờ duyệt
def reject_pending_members(client, members, group_id):
    print(f"[TỪ_CHỐI_THÀNH_VIÊN] Đang từ chối thành viên: {members} cho group_id {group_id}")
    try:
        if isinstance(members, list):
            members = [str(member) for member in members]
        else:
            members = [str(members)]
        
        params = {
            "params": client._encode({
                "grid": str(group_id),
                "members": members,
                "isApprove": 0
            }),
            "zpw_ver": 645,
            "zpw_type": 30
        }
        
        response = client._get("https://tt-group-wpa.chat.zalo.me/api/group/pending-mems/review", params=params)
        data = response.json()
        print(f"[TỪ_CHỐI_THÀNH_VIÊN] Phản hồi API: {data}")
        results = data.get("data") if data.get("error_code") == 0 else None
        if results:
            results = client._decode(results)
            results = results.get("data") if results.get("data") else results
            if results is None:
                print("[TỪ_CHỐI_THÀNH_VIÊN] Dữ liệu trả về rỗng")
                return {"error_code": 1337, "error_message": "Dữ liệu trống"}
            if isinstance(results, str):
                try:
                    results = json.loads(results)
                    print(f"[TỪ_CHỐI_THÀNH_VIÊN] Kết quả phân tích: {results}")
                except:
                    print(f"[TỪ_CHỐI_THÀNH_VIÊN] Lỗi phân tích kết quả: {results}")
                    return {"error_code": 1337, "error_message": results}
            print(f"[TỪ_CHỐI_THÀNH_VIÊN] Thành công: {results}")
            return results
        error_code = data.get("error_code")
        error_message = data.get("error_message") or data.get("data")
        print(f"[TỪ_CHỐI_THÀNH_VIÊN] Lỗi: mã_lỗi={error_code}, thông_báo={error_message}")
        return {"error_code": error_code, "error_message": error_message}
    except ZaloAPIException as e:
        print(f"[TỪ_CHỐI_THÀNH_VIÊN] Lỗi ZaloAPIException: {str(e)}")
        return {"error_code": -1, "error_message": f"Lỗi API: {str(e)}"}
    except Exception as e:
        print(f"[TỪ_CHỐI_THÀNH_VIÊN] Lỗi chung: {str(e)}")
        return {"error_code": -1, "error_message": f"Lỗi không xác định: {str(e)}"}

# Hàm xử lý lệnh 'findandreject'
def handle_findandreject(message, message_object, thread_id, thread_type, author_id, client):
    print(f"[XỬ_LÝ_LỆNH] Xử lý lệnh: {message}, thread_id: {thread_id}, author_id: {author_id}")
    if thread_type != ThreadType.GROUP:
        print("[XỬ_LÝ_LỆNH] Không phải nhóm")
        send_response(client, message_object, thread_id, thread_type, "Lệnh này chỉ hoạt động trong nhóm.")
        return
    
    # Kiểm tra quyền admin
    is_admin_user, error = is_admin(client, thread_id, author_id, message_object, thread_type)
    if error:
        print(f"[XỬ_LÝ_LỆNH] Lỗi kiểm tra quyền admin: {error}")
        send_response(client, message_object, thread_id, thread_type, error)
        return
    if not is_admin_user:
        print("[XỬ_LÝ_LỆNH] Người dùng không phải admin")
        send_response(client, message_object, thread_id, thread_type, "Chỉ admin mới có thể sử dụng lệnh này.")
        return
    
    # Kiểm tra cú pháp
    parts = message.strip().split(" ", 1)
    if len(parts) < 2 or not parts[1].strip():
        print("[XỬ_LÝ_LỆNH] Cú pháp lệnh không hợp lệ")
        send_response(client, message_object, thread_id, thread_type, 
                      "Nhập tên thành viên cần từ chối.\nVí dụ: group.findandreject Minh")
        return

    search_term = parts[1].strip().lower()
    print(f"[XỬ_LÝ_LỆNH] Từ khóa tìm kiếm: {search_term}")

    # Gửi phản ứng để xác nhận lệnh
    print("[XỬ_LÝ_LỆNH] Gửi phản ứng")
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)

    # Lấy danh sách thành viên chờ duyệt
    pending_members, error = get_pending_members(client, thread_id, message_object)
    if error:
        print(f"[XỬ_LÝ_LỆNH] Lỗi lấy danh sách thành viên chờ: {error}")
        send_response(client, message_object, thread_id, thread_type, f"Lỗi: {error['error_message']}")
        return
    if not pending_members:
        print("[XỬ_LÝ_LỆNH] Không có thành viên chờ duyệt")
        send_response(client, message_object, thread_id, thread_type, 
                      "Không có thành viên nào trong danh sách chờ duyệt.")
        return

    # Tìm thành viên khớp với từ khóa
    found_members = [
        member for member in pending_members 
        if search_term == member['zaloName'].lower() or
        search_term in member['zaloName'].lower() or
        search_term in "".join(c[0] for c in member['zaloName'].split()).lower()
    ]
    print(f"[XỬ_LÝ_LỆNH] Thành viên tìm thấy: {found_members}")

    if not found_members:
        print("[XỬ_LÝ_LỆNH] Không tìm thấy thành viên khớp với từ khóa")
        send_response(client, message_object, thread_id, thread_type, 
                      f"Không tìm thấy thành viên chờ duyệt nào có tên chứa '{search_term}'.")
        return

    # Từ chối các thành viên được tìm thấy
    member_ids = [member['id'] for member in found_members]
    print(f"[XỬ_LÝ_LỆNH] Từ chối các ID thành viên: {member_ids}")
    result = reject_pending_members(client, member_ids, thread_id)
    
    # Kiểm tra kết quả từ chối
    if isinstance(result, dict) and any(v != 0 for v in result.values()):
        print(f"[XỬ_LÝ_LỆNH] Lỗi khi từ chối thành viên: {result}")
        error_message = "Lỗi khi từ chối một số thành viên: "
        for member_id, code in result.items():
            if code != 0:
                error_message += f"ID {member_id}: mã lỗi {code}, "
        send_response(client, message_object, thread_id, thread_type, error_message.rstrip(", "))
        return

    # Chuẩn bị tin nhắn kết quả
    header = f"📋 Đã từ chối {len(found_members)} thành viên chờ duyệt:\n\n"
    messages_to_send = []
    current_message = header
    current_length = len(header)

    for idx, member in enumerate(found_members, 1):
        member_info = (
            f"{idx} - {member['zaloName']}:\n"
            f"🔣 ID: {member['id']}\n"
            f"📅 Ngày tạo tài khoản: {member['create_time']}\n"
            "──────────"
        )
        member_length = len(member_info) + 1
        if current_length + member_length > MAX_MESSAGE_LENGTH:
            messages_to_send.append(current_message)
            current_message = ""
            current_length = 0
        current_message += member_info + "\n"
        current_length += member_length

    if current_message and current_message != header:
        messages_to_send.append(current_message)
    print(f"[XỬ_LÝ_LỆNH] Tin nhắn sẽ gửi: {messages_to_send}")

    # Gửi tin nhắn kết quả
    if not messages_to_send:
        print("[XỬ_LÝ_LỆNH] Không có tin nhắn để gửi")
        send_response(client, message_object, thread_id, thread_type, 
                      "Không có thông tin để hiển thị.")
        return

    for msg in messages_to_send:
        print(f"[XỬ_LÝ_LỆNH] Gửi tin nhắn kết quả: {msg}")
        send_response(client, message_object, thread_id, thread_type, msg)

# Hàm trả về lệnh
def get_mitaizl():
    return {
        'group.deny': handle_findandreject
    }