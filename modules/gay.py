import random
import json
import os
from datetime import datetime, timedelta
from zlapi import Message, ThreadType, MultiMsgStyle, MessageStyle, ZaloAPIException

# [Existing 'des' dictionary unchanged]

GAY_TEST_FILE = 'gay_test_usage.json'

def load_usage_data():
    if os.path.exists(GAY_TEST_FILE):
        with open(GAY_TEST_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_usage_data(data):
    with open(GAY_TEST_FILE, 'w') as f:
        json.dump(data, f)

def classify_gay_percentage(percentage):
    if 1 <= percentage <= 20:
        return "trai thẳng"
    elif 21 <= percentage <= 40:
        return "bóng"
    elif 41 <= percentage <= 60:
        return "thích mặc váy"
    elif 61 <= percentage <= 80:
        return "bê đê chúa"
    elif 81 <= percentage <= 100:
        return "chuẩn bị đi Thái"
    else:
        return "không xác định"

def handle_gay_test(message, message_object, thread_id, thread_type, author_id, client):
    # Send reaction immediately
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    mentions = message_object.mentions
    usage_data = load_usage_data()

    # Check if no users are tagged
    if not mentions or len(mentions) < 1:
        menu_message = "Vui lòng nhập cú pháp: 'gay @name'"
        style = MultiMsgStyle([
            MessageStyle(offset=0, length=len(menu_message), style="color", color="#15a85f", auto_format=False),
            MessageStyle(offset=0, length=len(menu_message), style="font", size="16", auto_format=False),
        ])
        client.replyMessage(
            Message(text=menu_message, style=style),
            message_object, thread_id, thread_type, ttl=10000
        )
        return

    now = datetime.now()
    results = []

    # Process each tagged user
    for mention in mentions:
        person_id = mention['uid']  # Use 'uid' as in zaloi4 for consistency
        try:
            # Fetch user info to get accurate name, inspired by zaloi4
            info_response = client.fetchUserInfo(person_id)
            profiles = info_response.unchanged_profiles or info_response.changed_profiles
            person_info = profiles.get(str(person_id), {})
            person_name = person_info.get('zaloName', mention.get('name', 'Người dùng không xác định'))
        except ZaloAPIException as e:
            print(f"Error fetching user info for {person_id}: {e}")
            person_name = mention.get('name', 'Người dùng không xác định')  # Fallback
        except Exception as e:
            print(f"Unexpected error for {person_id}: {e}")
            person_name = mention.get('name', 'Người dùng không xác định')  # Fallback

        # Handle usage data and limits
        if person_id in usage_data:
            gay_percentage = usage_data[person_id]['gay_percentage']
            last_used = datetime.fromisoformat(usage_data[person_id]['last_used'])
            count = usage_data[person_id]['count']

            if count >= 2 and now < last_used + timedelta(days=1):
                time_remaining = (last_used + timedelta(days=1) - now).total_seconds()
                hours_remaining = int(time_remaining // 3600)
                minutes_remaining = int((time_remaining % 3600) // 60)
                results.append(f"{person_name} đã sử dụng quá số lần cho phép. Vui lòng thử lại sau {hours_remaining} giờ {minutes_remaining} phút.")
                continue
            else:
                usage_data[person_id]['count'] += 1
                usage_data[person_id]['last_used'] = str(now)
        else:
            gay_percentage = random.randint(1, 100)
            usage_data[person_id] = {
                'gay_percentage': gay_percentage,
                'count': 1,
                'last_used': str(now)
            }

        classification = classify_gay_percentage(gay_percentage)
        results.append(f"{person_name} có độ gay là {gay_percentage}% ({classification}).")

    # Save updated usage data
    save_usage_data(usage_data)

    # Send combined results
    final_message = "\n".join(results)
    style = MultiMsgStyle([
        MessageStyle(offset=0, length=len(final_message), style="color", color="#15a85f", auto_format=False),
        MessageStyle(offset=0, length=len(final_message), style="font", size="16", auto_format=False),
    ])
    client.replyMessage(
        Message(text=final_message, style=style),
        message_object, thread_id, thread_type, ttl=120000
    )

def get_mitaizl():
    return {
        'gay': handle_gay_test
    }