import time
import json
import logging
import random
import threading
import re
from zlapi.models import Message, ThreadType, MultiMsgStyle, MessageStyle
from config import ADMIN


# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Danh sách màu
COLORS = [
    "#db342e",  # Đỏ đậm
    "#15a85f",  # Xanh lá đậm
    "#f27806",  # Cam đậm
    "#f7b503"   # Vàng đậm
]

# Nội dung tin nhắn chính
MESSAGE_TEXT = """═══ Minh Vũ Shinn Cte═══
═══CUNG CẤP MAP LQ ═══
📢 THÔNG BÁO UPDATE ANDROID - IOS
🔗 https://zalo.me/g/ohcfct225
🔶LQ ACE 3 MIỀN
🔗 https://zalo.me/g/rrywmq953
═══ ĐẤU TRƯỜNG LIÊN QUÂN ═══
🔶 Box 1: Bá chủ Liên quân
🔗 https://zalo.me/g/cayqae880
🔶 Box 4: Kẻ thống trị Liên quân
🔗 https://zalo.me/g/ochyyh448
🔶 Box 6: Hội Kẻ Hủy Diệt Rank
🔗 https://zalo.me/g/qlhssk809
🔶 Box 7: 100 ⭐ K phải giấc mơ
🔗 https://zalo.me/g/xvtszw104
🔶 Box 13: Leo rank bằng 4 Chân
   https://zalo.me/g/spaqlb267
🔶 Box 19: Chinh phục rank đồng
🔗 https://zalo.me/g/lulmlw377
🔶 Box 21: Người gác cổng Bình Nguyên
🔗 https://zalo.me/g/lalvob031
🔶 Box 22: Bộ lạc Liên Quân
🔗 https://zalo.me/g/crgyqw748
═══ HẠ RANK CẤP TỐC ═══
🔶 Box 8: Sẵn sàng 1 VS 9
🔗 https://zalo.me/g/sjrbqa638
🔶 Box 10: Hạ rank không phanh
🔗 https://zalo.me/g/vtgpfr533
🔶 Box 11: Hạn rank Xuống Đáy Xã Hội
🔗 https://zalo.me/g/dmgtoc729
🔶 Box 12: Cuộc chiến Hạ Rank
🔗 https://zalo.me/g/tlxiin969
🔶 Box 14: Hạ Rank Cũng vui
🔗 https://zalo.me/g/byuqks230
🔶 Box 15: Hạ Rank Trải Nghiệm
🔗 https://zalo.me/g/khjrna643
🔶 Box 17: Hạ Rank Chờ Cơ hội
🔗 https://zalo.me/g/smibnr474
🔶 Box 20: Binh Đoàn Tụt Hạng
🔗 https://zalo.me/g/ysdgtu142
🔶 Box 23: Thắng làm vua - Thua làm lại
🔗 https://zalo.me/g/lnuarr372
═══ ĐI BOT ═══
⚡ Box 2: Đăng ký đi bot
🔗 https://zalo.me/g/bjnwqv874
⚡ Box 3: Đăng ký bot 5 game
🔗 https://zalo.me/g/jlgahh907
⚡ Box 5: TLT - Nor 5v5
🔗 https://zalo.me/g/lzygxi684
⚡ Box 18: TLT 3v3
🔗 https://zalo.me/g/zaiqug348
═══ CỘNG ĐỒNG NGHIỆN GAME ═══
🎮 Box 16: Hội những người mê LQ
🔗 https://zalo.me/g/zfziaz213
"""

# Cấu trúc JSON phân tách từ MESSAGE_TEXT
MESSAGE_JSON = {
    "headers": [
        {"text": "═══ Minh Vũ Shinn Cte═══", "color": "#db342e"},
        {"text": "═══CUNG CẤP MAP LQ ═══", "color": "#db342e"},
        {"text": "═══ ĐẤU TRƯỜNG LIÊN QUÂN ═══", "color": "#db342e"},
        {"text": "═══ HẠ RANK CẤP TỐC ═══", "color": "#db342e"},
        {"text": "═══ ĐI BOT ═══", "color": "#db342e"},
        {"text": "═══ CỘNG ĐỒNG NGHIỆN GAME ═══", "color": "#db342e"}
    ],
    "announcements": [
        {"text": "📢 THÔNG BÁO UPDATE ANDROID - IOS", "color": "#f7b503"},
        {"text": "🔶LQ ACE 3 MIỀN", "color": "#f7b503"}
    ],
    "groups": [
        {"name": "🔶 Box 1: Bá chủ Liên quân", "link": "https://zalo.me/g/pszswa548", "color": "random"},
        {"name": "🔶 Box 4: Kẻ thống trị Liên quân", "link": "https://zalo.me/g/ochyyh448", "color": "random"},
        {"name": "🔶 Box 6: Hội Kẻ Hủy Diệt Rank", "link": "https://zalo.me/g/qlhssk809", "color": "random"},
        {"name": "🔶 Box 7: 100 ⭐ K phải giấc mơ", "link": "https://zalo.me/g/xvtszw104", "color": "random"},
        {"name": "🔶 Box 13: Leo rank bằng 4 Chân", "link": "https://zalo.me/g/spaqlb267", "color": "random"},
        {"name": "🔶 Box 19: Chinh phục rank đồng", "link": "https://zalo.me/g/lulmlw377", "color": "random"},
        {"name": "🔶 Box 21: Người gác cổng Bình Nguyên", "link": "https://zalo.me/g/lalvob031", "color": "random"},
        {"name": "🔶 Box 22: Bộ lạc Liên Quân", "link": "https://zalo.me/g/crgyqw748", "color": "random"},
        {"name": "🔶 Box 8: Sẵn sàng 1 VS 9", "link": "https://zalo.me/g/sjrbqa638", "color": "random"},
        {"name": "🔶 Box 10: Hạ rank không phanh", "link": "https://zalo.me/g/vtgpfr533", "color": "random"},
        {"name": "🔶 Box 11: Hạn rank Xuống Đáy Xã Hội", "link": "https://zalo.me/g/dmgtoc729", "color": "random"},
        {"name": "🔶 Box 12: Cuộc chiến Hạ Rank", "link": "https://zalo.me/g/tlxiin969", "color": "random"},
        {"name": "🔶 Box 14: Hạ Rank Cũng vui", "link": "https://zalo.me/g/byuqks230", "color": "random"},
        {"name": "🔶 Box 15: Hạ Rank Trải Nghiệm", "link": "https://zalo.me/g/khjrna643", "color": "random"},
        {"name": "🔶 Box 17: Hạ Rank Chờ Cơ hội", "link": "https://zalo.me/g/smibnr474", "color": "random"},
        {"name": "🔶 Box 20: Binh Đoàn Tụt Hạng", "link": "https://zalo.me/g/ysdgtu142", "color": "random"},
        {"name": "🔶 Box 23: Thắng làm vua - Thua làm lại", "link": "https://zalo.me/g/lnuarr372", "color": "random"},
        {"name": "⚡ Box 2: Đăng ký đi bot", "link": "https://zalo.me/g/bjnwqv874", "color": "random"},
        {"name": "⚡ Box 3: Đăng ký bot 5 game", "link": "https://zalo.me/g/jlgahh907", "color": "random"},
        {"name": "⚡ Box 5: TLT - Nor 5v5", "description": "TLT - Nor 5v5", "link": "https://zalo.me/g/lzygxi684", "color": "random"},
        {"name": "⚡ Box 18: TLT 3v3", "link": "https://zalo.me/g/zaiqug348", "color": "random"},
        {"name": "🎮 Box 16: Hội những người mê LQ", "link": "https://zalo.me/g/zfziaz213", "color": "random"}
    ],
    "links": [
        "https://zalo.me/g/ohcfct225",
        "https://zalo.me/g/rrywmq953",
        "https://zalo.me/g/pszswa548",
        "https://zalo.me/g/ochyyh448",
        "https://zalo.me/g/qlhssk809",
        "https://zalo.me/g/xvtszw104",
        "https://zalo.me/g/spaqlb267",
        "https://zalo.me/g/lulmlw377",
        "https://zalo.me/g/lalvob031",
        "https://zalo.me/g/crgyqw748",
        "https://zalo.me/g/sjrbqa638",
        "https://zalo.me/g/vtgpfr533",
        "https://zalo.me/g/dmgtoc729",
        "https://zalo.me/g/tlxiin969",
        "https://zalo.me/g/byuqks230",
        "https://zalo.me/g/khjrna643",
        "https://zalo.me/g/smibnr474",
        "https://zalo.me/g/ysdgtu142",
        "https://zalo.me/g/lnuarr372",
        "https://zalo.me/g/bjnwqv874",
        "https://zalo.me/g/jlgahh907",
        "https://zalo.me/g/lzygxi684",
        "https://zalo.me/g/zaiqug348",
        "https://zalo.me/g/zfziaz213"
    ]
}

def get_excluded_group_ids(filename="danhsachnhom.json"):
    """
    Đọc tệp JSON và trả về tập hợp các group_id cần loại trừ.
    Nếu file không tồn tại hoặc định dạng sai, trả về tập rỗng.
    """
    try:
        with open(filename, "r", encoding="utf-8") as f:
            groups = json.load(f)
            return {grp.get("group_id") for grp in groups if "group_id" in grp}
    except Exception as e:
        logging.error("Lỗi khi đọc file %s: %s", filename, e)
        return set()

def create_styled_msg(text, color="#db342e", bold_size="16"):
    """
    Tạo Message với định dạng màu và kiểu chữ in đậm cho thông báo trạng thái.
    """
    style = MultiMsgStyle([
        MessageStyle(
            offset=0,
            length=len(text.encode('utf-8').decode('utf-8')) + 5,  # Thêm khoảng bù
            style="color",
            color=color,
            auto_format=False,
        ),
        MessageStyle(
            offset=0,
            length=len(text.encode('utf-8').decode('utf-8')) + 5,
            style="bold",
            size=bold_size,
            auto_format=False,
        ),
    ])
    return Message(text=text, style=style)

def find_links(text):
    """
    Tìm tất cả các link trong văn bản và trả về danh sách các tuple (start, end).
    """
    link_pattern = r'https?://[^\s]+'
    links = []
    for match in re.finditer(link_pattern, text):
        links.append((match.start(), match.end()))
    return links

def is_line_containing_link(line_start, line_end, link_ranges):
    """
    Kiểm tra xem toàn bộ dòng có chứa link không.
    """
    for link_start, link_end in link_ranges:
        if link_start >= line_start and link_end <= line_end:
            return True
    return False

def send_message_now(client):
    """
    Gửi tin nhắn đã định dạng đến toàn bộ nhóm không nằm trong danh sách loại trừ.
    Áp dụng style dựa trên cấu trúc JSON, thêm khoảng bù để đảm bảo màu sắc bao phủ đủ.
    """
    PADDING = 50  # Khoảng bù thêm cho length
    styles = []
    current_offset = 0
    message_lines = MESSAGE_TEXT.split("\n")
    link_ranges = find_links(MESSAGE_TEXT)

    # Duyệt qua từng dòng để áp dụng style dựa trên MESSAGE_JSON
    for line in message_lines:
        line_length = len(line.encode('utf-8').decode('utf-8'))
        line_start = current_offset
        line_end = current_offset + line_length
        is_link_line = is_line_containing_link(line_start, line_end, link_ranges)

        if not is_link_line:
            applied_style = False

            # Kiểm tra tiêu đề phần
            for header in MESSAGE_JSON["headers"]:
                if header["text"] in line:
                    styles.append(MessageStyle(
                        offset=line_start,
                        length=line_length + PADDING,
                        style="color",
                        color=header["color"],
                        auto_format=False
                    ))
                    logging.info("Applied color %s to header: %s (offset: %d, length: %d)", header["color"], line, line_start, line_length + PADDING)
                    applied_style = True
                    break

            # Kiểm tra thông báo
            if not applied_style:
                for announcement in MESSAGE_JSON["announcements"]:
                    if announcement["text"] in line:
                        styles.append(MessageStyle(
                            offset=line_start,
                            length=line_length + PADDING,
                            style="color",
                            color=announcement["color"],
                            auto_format=False
                        ))
                        logging.info("Applied color %s to announcement: %s (offset: %d, length: %d)", announcement["color"], line, line_start, line_length + PADDING)
                        applied_style = True
                        break

            # Kiểm tra tên nhóm và mô tả
            if not applied_style:
                for group in MESSAGE_JSON["groups"]:
                    if group["name"] in line:
                        color = random.choice(COLORS) if group["color"] == "random" else group["color"]
                        styles.append(MessageStyle(
                            offset=line_start,
                            length=line_length + PADDING,
                            style="color",
                            color=color,
                            auto_format=False
                        ))
                        logging.info("Applied color %s to group name: %s (offset: %d, length: %d)", color, line, line_start, line_length + PADDING)
                        applied_style = True
                        break
                    elif "description" in group and group["description"] in line:
                        color = random.choice(COLORS) if group["color"] == "random" else group["color"]
                        styles.append(MessageStyle(
                            offset=line_start,
                            length=line_length + PADDING,
                            style="color",
                            color=color,
                            auto_format=False
                        ))
                        logging.info("Applied color %s to description: %s (offset: %d, length: %d)", color, line, line_start, line_length + PADDING)
                        applied_style = True
                        break

        else:
            logging.info("Skipped styling for link line: %s (offset: %d, length: %d)", line, line_start, line_length)

        current_offset += line_length + 1  # +1 cho ký tự xuống dòng "\n"

    # Tạo MultiMsgStyle
    style_message = MultiMsgStyle(styles)

    # Lấy danh sách nhóm được phép gửi
    all_groups = client.fetchAllGroups()
    excluded_ids = get_excluded_group_ids()
    allowed_thread_ids = [
        gid for gid in all_groups.gridVerMap.keys() if gid not in excluded_ids
    ]

    for thread_id in allowed_thread_ids:
        logging.info("Đang gửi tin nhắn đến nhóm %s...", thread_id)
        msg = Message(text=MESSAGE_TEXT, style=style_message)
        try:
            client.sendMessage(msg, thread_id, thread_type=ThreadType.GROUP, ttl=30000)
            logging.info("Đã gửi tin nhắn đến nhóm %s", thread_id)
            time.sleep(2)
        except Exception as e:
            logging.error("Error sending message to %s: %s", thread_id, e)

def handle_autosend_start(message, message_object, thread_id, thread_type, author_id, client):
    """
    Xử lý khi lệnh 'autolink' được kích hoạt:
      - Gửi phản hồi ban đầu với style.
      - Gửi tin nhắn đến toàn bộ nhóm trong luồng riêng.
      - Sau đó trả lời lại người dùng với kết quả.
    """
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
    if author_id not in ADMIN:
        error_message = "Bạn không có quyền sử dụng lệnh này."
        style_error = MultiMsgStyle([
            MessageStyle(offset=0, length=len(error_message), style="color", color="#db342e", auto_format=False),
            MessageStyle(offset=0, length=len(error_message), style="bold", size="16", auto_format=False),
        ])
        client.replyMessage(Message(text=error_message, style=style_error), message_object, thread_id, thread_type, ttl=30000)
        return
    initial_msg = create_styled_msg("Đang gửi tin nhắn đến toàn bộ nhóm...", bold_size="16")
    client.sendMessage(initial_msg, thread_id, thread_type, ttl=30000)
    threading.Thread(target=send_message_now, args=(client,), daemon=True).start()
    response_msg = create_styled_msg("Đã bắt đầu gửi tin nhắn đến toàn bộ nhóm ✅", bold_size="10")
    client.replyMessage(response_msg, message_object, thread_id, thread_type, ttl=30000)
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)

def get_mitaizl():
    return {
        'autolink': handle_autosend_start
    }