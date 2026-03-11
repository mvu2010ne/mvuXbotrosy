from zlapi.models import Message, MessageStyle, MultiMsgStyle
from PIL import Image, ImageDraw, ImageFont
import os
import re

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "🔍 Thực hiện phép tính toán và hiển thị kết quả kèm hình ảnh.",
    'tính năng': [
        "📝 Nhận biểu thức toán học từ người dùng và tính toán kết quả.",
        "🖼️ Tạo hình ảnh hiển thị biểu thức và kết quả, căn chỉnh đẹp mắt.",
        "🎨 Gửi kết quả với định dạng văn bản màu sắc và in đậm.",
        "⚠️ Kiểm tra lỗi cú pháp, chia cho 0, và thông báo lỗi chi tiết."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh casio <phép toán> để thực hiện tính toán.",
        "📌 Ví dụ: casio 2 + 2 để tính kết quả của 2 + 2.",
        "✅ Nhận kết quả văn bản và hình ảnh minh họa ngay lập tức."
    ]
}

def send_message_with_style(client, text, thread_id, thread_type, ttl=None, color="#db342e"):
    """
    Gửi tin nhắn với định dạng màu sắc và in đậm.
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
            style="bold",
            size="8",
            auto_format=False
        )
    ])
    msg = Message(text=text, style=style)
    if ttl is not None:
        client.sendMessage(msg, thread_id, thread_type, ttl=ttl)
    else:
        client.sendMessage(msg, thread_id, thread_type)

def create_calculator_image(expression, result, output_path="calculator_result.png"):
    """
    Tạo hình ảnh dọc với biểu thức, đường gạch ngang và kết quả, căn phải theo chiều ngang và căn giữa theo chiều cao.
    """
    # Tạo ảnh dọc với nền trắng
    img = Image.new('RGB', (200, 300), color='white')
    draw = ImageDraw.Draw(img)
    
    # Font chữ (cố gắng dùng font monospaced để giống máy tính)
    try:
        font = ImageFont.truetype("cour.ttf", 100)  # Dùng font Courier New (monospaced)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", 100)
        except:
            font = ImageFont.load_default()
    
    # Màu xanh dương giống ví dụ
    text_color = (0, 102, 204)  # RGB cho màu xanh dương
    
    # Tính toán vị trí để căn phải theo chiều ngang
    image_width = 200
    padding_right = 20  # Khoảng cách từ mép phải
    
    # Tính chiều cao của nội dung
    line_spacing = 10  # Khoảng cách giữa các dòng
    expression_height = 40  # Ước lượng chiều cao của dòng biểu thức (dựa trên font size)
    line_height = 2  # Chiều cao của đường gạch ngang
    result_height = 40  # Ước lượng chiều cao của dòng kết quả
    total_content_height = expression_height + line_spacing + line_height + line_spacing + result_height
    
    # Tính vị trí y để căn giữa theo chiều cao
    image_height = 300
    start_y = (image_height - total_content_height) // 2
    
    # Căn phải cho biểu thức
    expression_width = font.getlength(expression)
    expression_x = image_width - expression_width - padding_right
    draw.text((expression_x, start_y), expression, fill=text_color, font=font)
    
    # Vẽ đường gạch ngang (màu đen)
    line_y = start_y + expression_height + line_spacing
    draw.line((20, line_y, 180, line_y), fill='black', width=line_height)
    
    # Căn phải cho kết quả
    result_str = str(result)
    result_width = font.getlength(result_str)
    result_x = image_width - result_width - padding_right
    result_y = line_y + line_spacing + result_height
    draw.text((result_x, result_y), result_str, fill=text_color, font=font)
    
    # Lưu ảnh
    img.save(output_path)
    return output_path

def handle_calculator_command(message, message_object, thread_id, thread_type, author_id, client):
    """
    Xử lý lệnh tính toán từ người dùng.
    """
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    text = message.split()
    if len(text) < 2:
        error_message = "🚨 Hãy nhập phép toán cần tính.\nCú pháp: calc <phép toán>"
        send_message_with_style(client, error_message, thread_id, thread_type)
        return

    expression = " ".join(text[1:])  # Lấy toàn bộ phép tính người dùng nhập

    # Kiểm tra biểu thức có chứa ký tự không hợp lệ không
    valid_pattern = r'^[\d\s\+\-\*/\(\)\.]+$'
    if not re.match(valid_pattern, expression):
        error_message = "❌ Biểu thức không hợp lệ: Chỉ sử dụng số, toán tử (+, -, *, /), và dấu ngoặc."
        send_message_with_style(client, error_message, thread_id, thread_type)
        return

    try:
        result = eval(expression, {"__builtins__": None}, {"abs": abs})
        # Gửi tin nhắn văn bản
        send_message_with_style(
            client, 
            f"━━━━━━━━━━━━━━━━\n💡 KẾT QUẢ:\n🎯 = {result}\n━━━━━━━━━━━━━━━━", 
            thread_id, 
            thread_type
        )
        # Tạo và gửi ảnh
        img_path = create_calculator_image(expression, result)
        client.sendLocalImage(img_path, thread_id, thread_type)
        os.remove(img_path)  # Xóa ảnh tạm sau khi gửi
    except SyntaxError:
        send_message_with_style(
            client, 
            f"❌ Lỗi cú pháp: Biểu thức không hợp lệ.", 
            thread_id, 
            thread_type
        )
    except ZeroDivisionError:
        send_message_with_style(
            client, 
            f"❌ Lỗi: Không thể chia cho 0.", 
            thread_id, 
            thread_type
        )
    except Exception as e:
        send_message_with_style(
            client, 
            f"❌ Lỗi khi tính toán: {e}", 
            thread_id, 
            thread_type
        )

def get_mitaizl():
    return {
        'casio': handle_calculator_command  # Lệnh tính toán
    }