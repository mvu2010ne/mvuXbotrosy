import google.generativeai as genai
from PIL import Image
from io import BytesIO
import base64
import os
import time
from zlapi.models import *
from datetime import datetime, timedelta
import random

# Lấy API Key từ biến môi trường hoặc sử dụng giá trị mặc định
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyA2LsN62uY3YDm1KNX6vkiTitEgb23_LsI")
if not GEMINI_API_KEY:
    print("GEMINI_API_KEY không được thiết lập!")
    raise ValueError("GEMINI_API_KEY không được thiết lập!")

# Khởi tạo client
genai.configure(api_key=GEMINI_API_KEY)
client = genai.GenerativeModel('gemini-2.0-flash-preview-image-generation')

# Danh sách màu sắc cho tin nhắn
COLORS = [
    "#db342e",  # Đỏ đậm
    "#15a85f",  # Xanh lá đậm
    "#f27806",  # Cam đậm
    "#f7b503"   # Vàng đậm
]

def apply_default_style(text):
    """
    Áp dụng style mặc định cho tin nhắn phản hồi.
    """
    base_length = len(text)
    adjusted_length = base_length + 100
    
    return MultiMsgStyle([
        MessageStyle(
            offset=0,
            length=adjusted_length,
            style="color",
            color=random.choice(COLORS),
            auto_format=False,
        ),
        MessageStyle(
            offset=0,
            length=adjusted_length,
            style="font",
            size="16",
            auto_format=False,
        ),
    ])

def send_message_with_style(client, text, message_object, thread_id, thread_type, mention=None, author_id=None, ttl=None):
    """
    Gửi tin nhắn với style và mention.
    """
    if mention:
        full_text = f"{mention}\n{text}"
    else:
        full_text = text
    
    mention_obj = None
    if mention and author_id:
        mention_obj = Mention(
            uid=author_id,
            length=len(mention),
            offset=0
        )
    
    style = apply_default_style(full_text)
    
    msg = Message(text=full_text, style=style, mention=mention_obj)
    if ttl is not None:
        client.replyMessage(msg, message_object, thread_id, thread_type, ttl=ttl)
    else:
        client.replyMessage(msg, message_object, thread_id, thread_type)

def get_user_name_by_id(client, author_id):
    """
    Lấy tên người dùng từ Zalo API.
    """
    try:
        user_info = client.fetchUserInfo(author_id).changed_profiles[author_id]
        return user_info.zaloName or user_info.displayName
    except Exception:
        return "Người Dùng Ẩn Danh"

def generate_image(prompt, output_file='generated_image.png'):
    """
    Tạo hình ảnh từ prompt văn bản và lưu vào file.
    
    Args:
        prompt (str): Mô tả văn bản để tạo hình ảnh
        output_file (str): Tên file để lưu hình ảnh
    
    Returns:
        bool: True nếu thành công, False nếu thất bại
    """
    try:
        response = client.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=2048,
                response_mime_type="image/png"
            ),
            request_options={"timeout": 10}
        )
        
        if not response.candidates:
            print("Không nhận được phản hồi hợp lệ từ API")
            return False
        
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                image_data = base64.b64decode(part.inline_data.data)
                image = Image.open(BytesIO(image_data))
                image.save(output_file)
                print(f"Đã lưu hình ảnh vào {output_file}")
                return True
            elif hasattr(part, 'text') and part.text:
                print(f"Phản hồi văn bản: {part.text}")
        
        print("Không tìm thấy hình ảnh trong phản hồi")
        return False
    
    except Exception as e:
        print(f"Lỗi khi tạo hình ảnh: {str(e)}")
        return False

def handle_image_command(content, message_object, thread_id, thread_type, author_id, client):
    """
    Xử lý lệnh tạo hình ảnh từ nội dung người dùng cung cấp.
    
    Args:
        content (str): Nội dung lệnh (mô tả hình ảnh)
        message_object: Đối tượng tin nhắn Zalo
        thread_id: ID thread
        thread_type: Loại thread
        author_id: ID người gửi
        client: Client Zalo
    
    Returns:
        None
    """
    user_name = get_user_name_by_id(client, author_id)
    mention = f"@{user_name}"
    
    if not content.strip():
        send_message_with_style(
            client,
            "Chưa nhập mô tả hình ảnh nha! 😅 Gõ gì đi để tui tạo ảnh! 🎨",
            message_object,
            thread_id,
            thread_type,
            mention=mention,
            author_id=author_id,
            ttl=180000
        )
        return
    
    output_file = f"generated_image_{int(time.time())}.png"
    success = generate_image(content, output_file)
    
    if success:
        response = f"Đã tạo ảnh thành công, lưu tại {output_file}! 😎"
    else:
        response = "Lỗi rồi, không tạo được ảnh! 😓 Thử lại nha!"
    
    send_message_with_style(
        client,
        response,
        message_object,
        thread_id,
        thread_type,
        mention=mention,
        author_id=author_id,
        ttl=180000
    )
    client.sendReaction(message_object, 'YES', thread_id, thread_type)



def get_mitaizl():
    """
    Trả về từ điển xử lý lệnh.
    """
    return {'cat': handle_image_command}