import json
import os
from zlapi.models import Message

des = {
    'version': "1.0.2",
    'credits': "Vũ Xuân Kiên",
    'description': "Bật/tắt auto send tin nhắn cho nhóm",
    'power': "Quản trị viên Bot"
}

ALLOWED_GROUPS_FILE = "modules/cache/sendtask_autosend.json"

def load_allowed_groups():
    if os.path.exists(ALLOWED_GROUPS_FILE):
        with open(ALLOWED_GROUPS_FILE, "r") as f:
            return json.load(f)
    return {"groups": []}

def save_allowed_groups(allowed_groups):
    with open(ALLOWED_GROUPS_FILE, "w") as f:
        json.dump(allowed_groups, f, indent=4)

def handle_autosend_command(message, message_object, thread_id, thread_type, author_id, client):
    command_parts = message.split()
    if len(command_parts) != 2:
         response_message = "Sử dụng: .autosend on/off"
    else:
        action = command_parts[1].lower()
        allowed_groups_data = load_allowed_groups()
        allowed_groups = allowed_groups_data.get("groups",[])
        if action == "on":
            if thread_id not in allowed_groups:
                allowed_groups.append(thread_id)
                allowed_groups_data["groups"] = allowed_groups
                save_allowed_groups(allowed_groups_data)
                response_message = f"Đã bật AutoSend cho nhóm này!"
            else:
                  response_message = f"Nhóm này đã được bật AutoSend trước đó!"
        elif action == "off":
            if thread_id in allowed_groups:
                allowed_groups.remove(thread_id)
                allowed_groups_data["groups"] = allowed_groups
                save_allowed_groups(allowed_groups_data)
                response_message = f"Đã tắt AutoSend cho nhóm này"
            else:
                response_message = f"Nhóm này đã được tắt AutoSend trước đó rồi!"
        else:
            response_message ="Sử dụng: autosend on/off"
    message_to_send = Message(text=response_message)
    client.replyMessage(message_to_send, message_object, thread_id, thread_type, ttl=5000)

def get_mitaizl():
    return {
         'autosend': handle_autosend_command
    }