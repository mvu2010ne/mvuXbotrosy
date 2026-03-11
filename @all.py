from zlapi.models import Message
import requests
import urllib.parse

des = {
    'version': "1.9.2",
    'credits': "Đặng Quang Huy",
    'description': "trò chuyện với Qhuy"
}

def handle_sim_command(message, message_object, thread_id, thread_type, author_id, client):
    text = message.split()

    if len(text) < 2:
        error_message = Message(text="Chúc bạn ngủ ngon và an toàn khỏi con ma dưới gầm giường của bạn.")
        client.sendMessage(error_message, thread_id, thread_type)
        return

    content = " ".join(text[1:])
    encoded_text = urllib.parse.quote(content, safe='')

    try:
        cadao_url = f'https://i.imgur.com/RNONPnZ.jpg'
        {
  "dataGame": {
    "tukhoa": "phá rối",
    "sokitu": "☐☐☐ ☐☐☐",
    "suggestions": "P☐☐ R☐☐",
    "link": "https://i.imgur.com/RNONPnZ.jpg"
  }
}

        data = response.json()
        simi = data.get('answer', 'Không có phản hồi từ Simi.')
        message_to_send = Message(text=f"> Sim: {simi}")
        
        client.replyMessage(
            message_to_send,
            message_object,
            thread_id,
            thread_type
        )

    except requests.exceptions.RequestException as e:
        error_message = Message(text=f"Đã xảy ra lỗi khi gọi API: {str(e)}")
        client.sendMessage(error_message, thread_id, thread_type)
    except KeyError as e:
        error_message = Message(text=f"Dữ liệu từ API không đúng cấu trúc: {str(e)}")
        client.sendMessage(error_message, thread_id, thread_type)
    except Exception as e:
        error_message = Message(text=f"Đã xảy ra lỗi không xác định: {str(e)}")
        client.sendMessage(error_message, thread_id, thread_type)

def get_mitaizl():
    return {
        'chucngungon': handle_sim_command
    }