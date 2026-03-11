from zlapi.models import Message
from config import ADMIN
import time

des = {
    'version': "1.0.2",
    'credits': "時崎狂三",
    'description': "add multiple members by phone numbers\nUsage: addsdt\n<phone_number1>\n<phone_number2>\n..."
}

def handle_add_multiple_users_by_phone_command(message, message_object, thread_id, thread_type, author_id, client):
    text = message.split('\n')

    if len(text) < 2:
        error_message = Message(text="Vui lòng nhập ít nhất một số điện thoại.\nVí dụ:\naddsdt\nsdt1\nsdt2\n...")
        client.sendMessage(error_message, thread_id, thread_type)
        return

    phone_numbers = [num.strip() for num in text[1:] if num.strip()]
    
    if not phone_numbers:
        error_message = Message(text="Không tìm thấy số điện thoại hợp lệ.")
        client.sendMessage(error_message, thread_id, thread_type)
        return

    success_count = 0
    failed_numbers = []

    for phone_number in phone_numbers:
        try:
            user_info = client.fetchPhoneNumber(phone_number)
            print(f"Kết quả API fetchPhoneNumber cho {phone_number}: {user_info}")

            if user_info and hasattr(user_info, 'uid'):
                user_id = user_info.uid
                user_name = user_info.zalo_name

                api_response = client.addUsersToGroup(user_id, thread_id)
                print(f"Kết quả API addUsersToGroup cho {user_name} ({user_id}): {api_response}")

                if api_response and hasattr(api_response, 'success') and api_response.success:
                    success_count += 1
                else:
                    failed_numbers.append(f"{phone_number} (API không xác nhận thành công: {api_response})")
            else:
                failed_numbers.append(f"{phone_number} (Không tìm thấy người dùng)")

        except Exception as e:
            failed_numbers.append(f"{phone_number} (Lỗi: {str(e)})")

    # Tạo thông báo kết quả
    send_message = f"Đã thêm thành công {success_count} người dùng vào nhóm.\n"
    if failed_numbers:
        send_message += "Không thể thêm các số sau:\n" + "\n".join(failed_numbers)

    gui = Message(text=send_message)
    client.sendMessage(gui, thread_id, thread_type)

def get_mitaizl():
    return {
        'addsdt': handle_add_multiple_users_by_phone_command
    }