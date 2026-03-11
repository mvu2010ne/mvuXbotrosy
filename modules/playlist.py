import random
import time
import threading
import requests
import os
from zlapi.models import Message, ThreadType

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Bot hỗ trợ phát danh sách nhạc tự động và gửi thông báo bài hát tới các nhóm.",
    'tính năng': [
        "🎶 Phát nhạc tự động từ danh sách các bài hát có sẵn.",
        "🔗 Tải nhạc từ URL và tạo liên kết tạm thời.",
        "📨 Gửi thông báo bài hát và file nhạc tới các nhóm.",
        "🔔 Thông báo trạng thái bật/tắt Auto Playlist.",
        "⏳ Áp dụng thời gian chờ giữa các lần phát nhạc.",
        "🔒 Chỉ quản trị viên mới có quyền sử dụng lệnh này."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh `play_on` để bật Auto Playlist.",
        "📩 Gửi lệnh `play_off` để tắt Auto Playlist.",
        "📌 Bot sẽ phát nhạc tự động và gửi thông báo bài hát tới các nhóm.",
        "✅ Nhận thông báo trạng thái bật/tắt Auto Playlist ngay lập tức."
    ]
}

# Danh sách các bài hát có sẵn
songs = [
    {"title": "Bài hát 1", "url": "https://example.com/song1.mp3"},
    {"title": "Bài hát 2", "url": "https://example.com/song2.mp3"},
    {"title": "Bài hát 3", "url": "https://example.com/song3.mp3"},
    {"title": "Bài hát 4", "url": "https://example.com/song4.mp3"},
]

# Trạng thái Auto Playlist
playlist_status = False

# Danh sách ID quản trị viên
ADMIN = ["admin_user_id_1", "admin_user_id_2"]

# Danh sách nhóm bị chặn (nếu có)
BLOCKED_THREAD_IDS = []

# Tải nhạc từ URL và tạo liên kết tạm thời
def download_song(song_url):
    try:
        response = requests.get(song_url, stream=True)
        if response.status_code == 200:
            temp_filename = f"temp_song_{int(time.time())}.mp3"
            with open(temp_filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    f.write(chunk)
            return temp_filename, None
        return None, "Không thể tải bài hát từ URL."
    except Exception as e:
        return None, str(e)

# Tính năng Auto Playlist
def start_auto_playlist(client):
    global playlist_status
    while playlist_status:
        try:
            # Chọn ngẫu nhiên một bài hát từ danh sách
            song = random.choice(songs)
            song_title = song["title"]
            song_url = song["url"]

            # Lấy danh sách tất cả các nhóm
            all_group = client.fetchAllGroups()
            allowed_thread_ids = [gid for gid in all_group.gridVerMap.keys() if gid not in BLOCKED_THREAD_IDS]

            # Tải bài hát
            local_song_path, error = download_song(song_url)
            if error:
                print(f"Lỗi tải bài hát '{song_title}': {error}")
                continue

            # Kiểm tra nếu có nhóm hợp lệ
            if allowed_thread_ids:
                message = f"🎶 Danh sách nhạc tự động: {song_title}\n🔗 Nghe trực tiếp tại đây: {song_url}"
                for thread_id in allowed_thread_ids:
                    try:
                        # Gửi tin nhắn thông báo
                        client.sendMessage(Message(text=message), thread_id=thread_id, thread_type=ThreadType.GROUP)

                        # Gửi voice
                        if local_song_path and os.path.exists(local_song_path):
                            client.sendVoice(filePath=local_song_path, thread_id=thread_id, thread_type=ThreadType.GROUP)
                            print(f"Gửi bài hát '{song_title}' đến nhóm {thread_id}")

                    except Exception as e:
                        print(f"Lỗi khi gửi bài hát đến nhóm {thread_id}: {e}")

                # Xóa file tạm sau khi gửi
                if local_song_path and os.path.exists(local_song_path):
                    os.remove(local_song_path)

            # Chờ một khoảng thời gian trước khi gửi bài tiếp theo
            time.sleep(600)  # 10 phút

        except Exception as e:
            print(f"Lỗi trong vòng lặp Auto Playlist: {e}")

# Bắt đầu Auto Playlist
def handle_playlist_start(message, message_object, thread_id, thread_type, author_id, client):
    global playlist_status
    if author_id not in ADMIN:
        response_message = Message(text="⛔ Bạn không có quyền sử dụng lệnh này!")
        client.replyMessage(response_message, message_object, thread_id, thread_type, ttl=18000)
        return

    if playlist_status:
        response_message = Message(text="⚙️ Auto Playlist đã được bật trước đó!")
        client.replyMessage(response_message, message_object, thread_id, thread_type, ttl=18000)
        return

    playlist_status = True
    threading.Thread(target=start_auto_playlist, args=(client,)).start()
    response_message = Message(text="✅ Đã bật Auto Playlist!")
    client.replyMessage(response_message, message_object, thread_id, thread_type, ttl=18000)

# Dừng Auto Playlist
def handle_playlist_stop(message, message_object, thread_id, thread_type, author_id, client):
    global playlist_status
    if author_id not in ADMIN:
        response_message = Message(text="⛔ Bạn không có quyền sử dụng lệnh này!")
        client.replyMessage(response_message, message_object, thread_id, thread_type, ttl=18000)
        return

    if not playlist_status:
        response_message = Message(text="❌ Auto Playlist đã tắt trước đó!")
        client.replyMessage(response_message, message_object, thread_id, thread_type, ttl=18000)
        return

    playlist_status = False
    response_message = Message(text="❌ Đã tắt Auto Playlist!")
    client.replyMessage(response_message, message_object, thread_id, thread_type, ttl=18000)

# Đăng ký lệnh
def get_mitaizl():
    return {
        'play_on': handle_playlist_start,
        'play_off': handle_playlist_stop
    }
