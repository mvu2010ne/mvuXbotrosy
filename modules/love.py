from zlapi import ZaloAPI, ZaloAPIException
from zlapi.models import *
import requests
import json
import os
import random
import urllib.parse

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Bói tình duyên dựa trên tên người dùng, đảm bảo người dùng nhận được kết quả hài hước và thú vị.",
    'tính năng': [
        "✅ Gửi phản ứng xác nhận khi lệnh được nhập đúng.",
        "🚀 Tính toán và bói tình duyên dựa trên tên của hai người dùng.",
        "🔗 Lấy thông tin người dùng từ UID.",
        "📊 Gửi phản hồi khi tính toán thành công hoặc thất bại.",
        "⚡ Gửi kết quả bói tình duyên hài hước với nhiều khả năng khác nhau."
    ],
    'hướng dẫn sử dụng': [
        "📌 Gửi lệnh `love` kèm theo tag tên hai người cần bói tình duyên.",
        "📎 Nếu chỉ soạn lệnh `love` thì bot sẽ trả về cú pháp hướng dẫn.",
        "📢 Hệ thống sẽ gửi phản hồi kết quả khi tính toán hoàn thành."
    ]
}

# Hàm bói tình duyên với nhiều khả năng kết quả
def boi_tinh_duyen(ten_nam, ten_nu):
    ten_nam = ten_nam.lower()
    ten_nu = ten_nu.lower()
    # Tính số lượng ký tự chung giữa 2 tên
    common = 0
    for ch in "abcdefghijklmnopqrstuvwxyz":
        if ch in ten_nam and ch in ten_nu:
            common += 1

    # Tùy theo số ký tự chung, chọn kết quả khác nhau
    if common == 0:
        results = [
            "Người dưng nước đái.",
            "Tình duyên ấm áp chỉ là mơ ước."
        ]
    elif common == 1:
        results = [
            "Đã từng chịch nhau.",
            "Chỉ đủ để nảy mùi thân tình thôi."
        ]
    elif common == 2:
        results = [
            "Đang yêu nhau lén lút.",
            "Mối tình bí mật đầy kịch tính."
        ]
    else:
        results = [
            "Tình duyên trọn vẹn như mộng mơ.",
            "Định mệnh đã sắp đặt, tình yêu mãi bên nhau."
        ]
    return random.choice(results)

# Hàm xử lý lệnh bói tình duyên
def handle_boi_tinh_duyen_command(message, message_object, thread_id, thread_type, author_id, client):
    # Gửi phản ứng ngay khi người dùng soạn đúng lệnh
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
    
    # Nếu người dùng chỉ soạn lệnh "love" mà không kèm tag thì gửi hướng dẫn sử dụng
    if message.strip().lower() == "love":
        reply_message = "Cú pháp: love @tênnguoinam @tênngườinữ..."
        client.sendMessage(Message(text=reply_message), thread_id, thread_type, ttl=30000)
        return

    # Nếu tin nhắn không chứa đúng 2 tag, báo lỗi
    if len(message_object.mentions) != 2:
        client.replyMessage(
            Message(text="Vui lòng tag tên 2 người vào tin nhắn."),
            message_object, thread_id, thread_type, ttl=5000
        )
        return

    uid1 = message_object.mentions[0].uid
    uid2 = message_object.mentions[1].uid

    try:
        # Lấy thông tin người dùng từ UID
        name1 = client.fetchUserInfo(uid1).changed_profiles[uid1].displayName
        name2 = client.fetchUserInfo(uid2).changed_profiles[uid2].displayName
    except Exception as e:
        client.replyMessage(
            Message(text="Lỗi khi lấy thông tin người dùng."),
            message_object, thread_id, thread_type
        )
        return

    # Tính kết quả bói tình duyên
    ket_qua = boi_tinh_duyen(name1, name2)
    # Gửi kết quả cho người dùng
    client.replyMessage(
        Message(text=ket_qua),
        message_object, thread_id, thread_type, ttl=60000
    )

# Class kế thừa ZaloAPI
class Client(ZaloAPI):
    def __init__(self, api_key, secret_key, imei, session_cookies):
        super().__init__(api_key, secret_key, imei=imei, session_cookies=session_cookies)

    def onMessage(self, mid, author_id, message, message_object, thread_id, thread_type):
        if not isinstance(message, str):
            return
        if author_id == self.uid:  # Không phản hồi tin nhắn của chính mình
            return
        # Xử lý lệnh "boi" hoặc "love"
        if message.startswith("boi") or message.startswith("love"):
            handle_boi_tinh_duyen_command(message, message_object, thread_id, thread_type, author_id, self)

# Hàm trả về các lệnh
def get_mitaizl():
    return {
        'love': handle_boi_tinh_duyen_command
    }
