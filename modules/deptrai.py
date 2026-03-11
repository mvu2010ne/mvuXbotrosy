import random
import json
import os
from datetime import datetime, timedelta
from zlapi import Message, ThreadType, ZaloAPIException

# Đường dẫn tới tệp lưu trữ thông tin sử dụng
GAY_TEST_FILE = 'gay_test_usage.json'

# Hàm tải thông tin sử dụng từ tệp JSON
def load_usage_data():
    if os.path.exists(GAY_TEST_FILE):
        with open(GAY_TEST_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

# Hàm lưu thông tin sử dụng vào tệp JSON
def save_usage_data(data):
    with open(GAY_TEST_FILE, 'w') as f:
        json.dump(data, f)

# Hàm xử lý đo độ đẹp trai
def handle_deptrai(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản ứng ngay khi người dùng soạn đúng lệnh
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    
    mentions = message_object.mentions  # Lấy danh sách người dùng được tag
    usage_data = load_usage_data()  # Tải thông tin sử dụng

    # Kiểm tra nếu không có ai được tag
    if not mentions or len(mentions) < 1:
        client.replyMessage(
            Message(text="Cú pháp: deptrai @tênngườidùng."),
            message_object, thread_id, thread_type, ttl=10000
        )
        return

    # Lấy ID và tên của người được tag
    person_id = mentions[0]['uid']  # Use 'uid' for consistency with zaloi4
    try:
        # Fetch user info to get accurate name, inspired by zaloi4
        info_response = client.fetchUserInfo(person_id)
        profiles = info_response.unchanged_profiles or info_response.changed_profiles
        person_info = profiles.get(str(person_id), {})
        person_name = person_info.get('zaloName', mentions[0].get('name', 'Người dùng không xác định'))
    except ZaloAPIException as e:
        print(f"Error fetching user info for {person_id}: {e}")
        person_name = mentions[0].get('name', 'Người dùng không xác định')  # Fallback
    except Exception as e:
        print(f"Unexpected error for {person_id}: {e}")
        person_name = mentions[0].get('name', 'Người dùng không xác định')  # Fallback

    # Kiểm tra số lần sử dụng
    now = datetime.now()

    # Nếu người này đã từng được tính phần trăm trước đó, lấy lại giá trị đó
    if person_id in usage_data:
        deptrai_percentage = usage_data[person_id]['gay_percentage']
        last_used = datetime.fromisoformat(usage_data[person_id]['last_used'])
        count = usage_data[person_id]['count']


        # Cập nhật số lần sử dụng và thời gian gần nhất
        usage_data[person_id]['count'] += 1
        usage_data[person_id]['last_used'] = str(now)
    else:
        # Nếu đây là lần đầu tiên, tạo ngẫu nhiên phần trăm độ đẹp trai và lưu lại
        deptrai_percentage = random.randint(1, 100)
        usage_data[person_id] = {
            'gay_percentage': deptrai_percentage,
            'count': 1,
            'last_used': str(now)
        }

    # Lưu lại thông tin sử dụng
    save_usage_data(usage_data)

    # Phản hồi kết quả với phần trăm đẹp trai đã lưu
    client.replyMessage(
        Message(text=f"{person_name} có độ đẹp trai là {deptrai_percentage}% 💤"),
        message_object, thread_id, thread_type, ttl=120000
    )

# Hàm trả về lệnh của bot
def get_mitaizl():
    return {
        'deptrai': handle_deptrai
    }