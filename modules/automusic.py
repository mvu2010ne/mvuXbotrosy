import time
import random
import json
import requests
import threading
import os
from zlapi import ZaloAPI
from zlapi.models import Message, ThreadType
from datetime import datetime
import pytz
import sys
from cachetools import LRUCache
from modules.ms_scl import (
    create_song_cover_image, create_rotating_gif_from_cover,
    upload_to_zalo, delete_file, download, convert_mp3_to_m4a,
    get_headers, get_client_id, upload_to_uguu  # THÊM upload_to_uguu
)
from config import ADMIN

# Múi giờ Việt Nam
VN_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

# Cấu hình file
MUSIC_SETTINGS_FILE = "json_data/automusic_settings.json"
MUSIC_DATA_FILE = "json_data/automusic_songs.json"
SETTINGS_LOCK = threading.Lock()
MEDIA_CACHE = LRUCache(maxsize=200)

# Session HTTP
music_session = requests.Session()
music_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': '*/*',
    'Referer': 'https://soundcloud.com/'
})

# ---------------------------
# Hàm hỗ trợ
# ---------------------------
def load_music_settings():
    with SETTINGS_LOCK:
        try:
            if os.path.exists(MUSIC_SETTINGS_FILE):
                with open(MUSIC_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    # Tự sửa nếu sai định dạng
                    if isinstance(data, list):
                        print("[AutoMusic] Cảnh báo: settings.json đang là LIST → chuyển về dict rỗng")
                        data = {}
                    elif not isinstance(data, dict):
                        print("[AutoMusic] settings.json không phải dict → trả về {}")
                        data = {}
                        
                    return data
            return {}
        except Exception as e:
            print(f"[AutoMusic] Lỗi đọc {MUSIC_SETTINGS_FILE}: {e}")
            return {}

def save_music_settings(settings):
    with SETTINGS_LOCK:
        try:
            # Đảm bảo thư mục tồn tại
            os.makedirs(os.path.dirname(MUSIC_SETTINGS_FILE), exist_ok=True)
            
            with open(MUSIC_SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[AutoMusic] Lỗi ghi {MUSIC_SETTINGS_FILE}: {e}")

def load_music_list():
    try:
        if os.path.exists(MUSIC_DATA_FILE):
            with open(MUSIC_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # Sửa tự động nếu dữ liệu sai định dạng
                if isinstance(data, dict):
                    print("[AutoMusic] Cảnh báo: file songs.json đang ở dạng dict → chuyển về list")
                    data = list(data.values())  # Lấy tất cả values thành list
                    
                if not isinstance(data, list):
                    print("[AutoMusic] File songs.json không phải list → trả về rỗng")
                    return []
                    
                return data
        return []
    except Exception as e:
        print(f"[AutoMusic] Lỗi đọc {MUSIC_DATA_FILE}: {e}")
        return []

def save_music_list(songs):
    try:
        # Đảm bảo thư mục tồn tại
        os.makedirs(os.path.dirname(MUSIC_DATA_FILE), exist_ok=True)
        
        with open(MUSIC_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(songs, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"[AutoMusic] Lỗi ghi {MUSIC_DATA_FILE}: {e}")

def search_soundcloud(query, limit=5):
    try:
        client_id = get_client_id()
        if not client_id:
            print("[AutoMusic] Không lấy được client_id!")
            return []

        url = f"https://api-v2.soundcloud.com/search/tracks?q={requests.utils.quote(query)}&client_id={client_id}&limit={limit}"
        response = music_session.get(url, timeout=10)

        if response.status_code == 401:
            print("[AutoMusic] client_id hết hạn → lấy lại...")
            client_id = get_client_id()
            if not client_id:
                return []
            url = url.split("&client_id=")[0] + f"&client_id={client_id}"
            response = music_session.get(url, timeout=10)

        response.raise_for_status()
        data = response.json()
        results = []
        for track in data.get('collection', []):
            if not track.get('streamable', False):
                continue
            duration_ms = track.get('duration', 0)
            duration = f"{duration_ms // 60000}:{(duration_ms % 60000) // 1000:02d}"
            results.append({
                'title': track['title'],
                'artist': track['user']['username'],
                'duration': duration,
                'cover': (track['artwork_url'] or track['user']['avatar_url']).replace('-large', '-t500x500'),
                'url': track['permalink_url'],
                'track_id': str(track['id']),
                'track_authorization': track.get('track_authorization', '')
            })
        return results
    except Exception as e:
        print(f"[AutoMusic] Lỗi tìm kiếm SoundCloud: {e}")
        return []

def send_music_track(client, thread_id, song):
    try:
        cache_key = f"automusic_{song['track_id']}"
        cached = MEDIA_CACHE.get(cache_key)

        # === 1. Lấy voice URL ===
        if cached:
            voice_url = cached
            print(f"[AutoMusic] Dùng cache voice: {song['title']}")
        else:
            print(f"[AutoMusic] Đang tải: {song['title']}...")
            mp3_path = download(song['url'], song['track_authorization'])
            if not mp3_path:
                print(f"[AutoMusic] Tải thất bại: {song['title']}")
                return False

            # Chuyển MP3 → M4A
            m4a_path = convert_mp3_to_m4a(mp3_path, song['title'])
            delete_file(mp3_path)  # Xóa MP3 ngay
            if not m4a_path:
                print(f"[AutoMusic] Chuyển đổi M4A thất bại: {song['title']}")
                return False

            # UPLOAD LÊN UGUU (THAY ĐỔI DÒNG NÀY)
            voice_url = upload_to_uguu(m4a_path)
            delete_file(m4a_path)  # Xóa M4A

            if not voice_url:
                print(f"[AutoMusic] Upload M4A lên Uguu thất bại: {song['title']}")
                return False

            MEDIA_CACHE[cache_key] = voice_url
            print(f"[AutoMusic] Đã cache voice Uguu: {voice_url}")

        # === 2. Gửi GIF xoay ===
        gif_url = create_rotating_gif_from_cover(
            song['cover'],
            client=client,
            thread_id=thread_id,
            thread_type=ThreadType.GROUP
        )
        if gif_url:
            try:
                client.sendCustomSticker(
                    staticImgUrl=gif_url, animationImgUrl=gif_url,
                    thread_id=thread_id, thread_type=ThreadType.GROUP,
                    width=250, height=250, ttl=300000
                )
            except:
                client.sendRemoteImage(imageUrl=gif_url, thread_id=thread_id, thread_type=ThreadType.GROUP)

        # === 3. Gửi ảnh bìa ===
        cover_path = create_song_cover_image(
            title=song['title'],
            artist=song['artist'],
            duration=song['duration'],
            is_official=False,
            is_hd=False,
            cover_url=song['cover']
        )
        if cover_path and os.path.exists(cover_path):
            try:
                client.sendLocalImage(
                    imagePath=cover_path,
                    thread_id=thread_id,
                    thread_type=ThreadType.GROUP,
                    width=1200,
                    height=400,
                    ttl=300000
                )
                print(f"[AutoMusic] Gửi ảnh bìa thành công")
            except Exception as e:
                print(f"[AutoMusic] Lỗi gửi ảnh bìa: {e}")
            finally:
                delete_file(cover_path)

        # === 4. Gửi voice ===
        try:
            client.sendRemoteVoice(voiceUrl=voice_url, thread_id=thread_id, thread_type=ThreadType.GROUP, ttl=300000)
            print(f"[AutoMusic] Gửi voice thành công!")
        except Exception as e:
            print(f"[AutoMusic] Lỗi gửi voice: {e}")

        print(f"[AutoMusic] ĐÃ GỬI HOÀN TẤT: {song['title']}")
        return True

    except Exception as e:
        print(f"[AutoMusic] Lỗi gửi nhạc: {e}")
        return False

# ---------------------------
# Vòng lặp tự động (GỬI NGẪU NHIÊN)
# ---------------------------
music_groups = {}

def auto_send_music(client, thread_id, delay_minutes):
    stop_event = threading.Event()
    if thread_id not in music_groups:
        music_groups[thread_id] = {}
    music_groups[thread_id]['stop_event'] = stop_event

    songs = load_music_list()
    if not songs:
        print(f"[AutoMusic] Danh sách trống cho nhóm {thread_id}")
        return

    while music_groups.get(thread_id, {}).get('enabled', False) and not stop_event.is_set():
        song = random.choice(songs)  # GỬI NGẪU NHIÊN
        send_music_track(client, thread_id, song)
        
        # Chờ X phút
        for _ in range(int(delay_minutes * 60)):
            if stop_event.is_set() or not music_groups.get(thread_id, {}).get('enabled', False):
                break
            time.sleep(1)
    print(f"[AutoMusic] Dừng gửi nhạc cho nhóm {thread_id}")

# ---------------------------
# Quản lý nhóm
# ---------------------------
def start_auto_music(client, thread_id, delay_minutes):
    try:
        group_info = client.fetchGroupInfo(thread_id)
        group = group_info.gridInfoMap.get(str(thread_id))
        if not group:
            return "Không lấy được thông tin nhóm!"
        group_name = group.name
        group_id = group.groupId

        if thread_id in music_groups and music_groups[thread_id].get('enabled'):
            return f"Đã bật tự động gửi nhạc cho nhóm {group_name}!"

        music_groups[thread_id] = {
            'enabled': True,
            'delay_minutes': delay_minutes,
            'group_name': group_name,
            'group_id': group_id,
            'thread': threading.Thread(target=auto_send_music, args=(client, thread_id, delay_minutes), daemon=True),
            'stop_event': None
        }
        music_groups[thread_id]['thread'].start()

        settings = load_music_settings()
        settings[str(thread_id)] = {
            'enabled': True,
            'delay_minutes': delay_minutes,
            'group_name': group_name,
            'group_id': group_id
        }
        save_music_settings(settings)

        return f"BẬT THÀNH CÔNG\nTự động gửi nhạc NGẪU NHIÊN mỗi {delay_minutes} phút cho nhóm:\n{group_name} (ID: {group_id})"
    except Exception as e:
        return f"LỖI: {str(e)}"

def stop_auto_music(thread_id):
    """Tắt chức năng tự động gửi nhạc cho một nhóm."""
    try:
        settings = load_music_settings()
        config = settings.get(str(thread_id), {})
        if thread_id in music_groups and music_groups[thread_id].get('enabled'):
            music_groups[thread_id]['enabled'] = False
            if music_groups[thread_id].get('stop_event'):
                music_groups[thread_id]['stop_event'].set()
            music_groups[thread_id]['thread'] = None
        settings[str(thread_id)] = {**config, 'enabled': False}
        save_music_settings(settings)
        
        # Trả về dictionary chứa thông tin chi tiết
        return {
            'success': True,
            'message': f"TẮT THÀNH CÔNG\nĐã dừng gửi nhạc cho nhóm {config.get('group_name', 'Unknown')}",
            'group_name': config.get('group_name', 'Unknown'),
            'group_id': config.get('group_id', str(thread_id))
        }
    except Exception as e:
        return {
            'success': False,
            'message': f"LỖI: {str(e)}"
        }

def initialize_groups(client):
    settings = load_music_settings()
    for tid, config in settings.items():
        if config.get('enabled', False):
            try:
                thread_id = int(tid)
                delay = float(config.get('delay_minutes', 1))
                start_auto_music(client, thread_id, delay)
            except Exception as e:
                print(f"[AutoMusic] Lỗi khởi tạo nhóm {tid}: {e}")

# ---------------------------
# Xử lý lệnh
# ---------------------------
def handle_automusic(message, message_object, thread_id, thread_type, author_id, client):
    try:
        client.sendReaction(message_object, "Đã nhận", thread_id, thread_type, reactionType=75)
    except:
        pass

    if author_id not in ADMIN:
        client.replyMessage(
            Message(text="QUYỀN TRUY CẬP BỊ TỪ CHỐI\nChỉ admin mới được dùng lệnh này!"), 
            message_object, thread_id, thread_type
        )
        return

    parts = message.strip().split()
    
    # Kiểm tra lệnh cơ bản
    if len(parts) == 0 or parts[0].lower() != "automusic":
        return
    
    # Chỉ có "automusic" → hiển thị hướng dẫn
    if len(parts) == 1:
        response = (
            "🎵 TỰ ĐỘNG GỬI NHẠC - HƯỚNG DẪN 🎵\n"
            "─────────────────────────────────\n"
            "• automusic on <phút>  → Bật gửi nhạc tự động\n"
            "   Ví dụ: automusic on 30 (gửi mỗi 30 phút)\n\n"
            "• automusic off        → Tắt gửi nhạc tự động\n"
            "   (Bot sẽ tự động khởi động lại sau 5s)\n\n"
            "• automusic add <tên>  → Thêm bài hát vào danh sách\n"
            "   Ví dụ: automusic add Shape of You\n"
            "          automusic add Lạc Trôi\n\n"
            "• automusic del <số>   → Xóa bài hát theo số thứ tự\n"
            "   Ví dụ: automusic del 1 3 5\n\n"
            "• automusic list       → Xem danh sách bài hát hiện có\n"
            "─────────────────────────────────\n"
            "📝 Lưu ý: Tất cả lệnh chỉ dành cho Admin!"
        )
        client.replyMessage(
            Message(text=response), 
            message_object, 
            thread_id, 
            thread_type, 
            ttl=30000
        )
        return

    # Xử lý lệnh có tham số
    cmd = parts[1].lower()

    if cmd == "on" and len(parts) == 3:
        try:
            delay = float(parts[2])
            if delay <= 0:
                response = "❌ LỖI: Thời gian phải lớn hơn 0 phút!"
            else:
                response = start_auto_music(client, thread_id, delay)
        except ValueError:
            response = "❌ LỖI: Thời gian phải là số hợp lệ (ví dụ: 30, 60, 0.5)!"
        except Exception as e:
            response = f"❌ LỖI HỆ THỐNG: {str(e)}"
        
        client.replyMessage(
            Message(text=response), 
            message_object, 
            thread_id, 
            thread_type, 
            ttl=30000
        )

    elif cmd == "off":
        # Gọi hàm stop và nhận kết quả
        result = stop_auto_music(thread_id)
        
        # Gửi thông báo đầu tiên
        first_message = f"{result['message']}\n\nBot sẽ khởi động lại trong ~5s để áp dụng thay đổi..."
        client.replyMessage(
            Message(text=first_message), 
            message_object, 
            thread_id, 
            thread_type, 
            ttl=5000
        )
        
        # Đợi 5 giây để người dùng đọc thông báo
        time.sleep(5)
        
        # Khởi động lại bot
        print(f"[AutoMusic] Đã tắt tính năng cho nhóm {result.get('group_name', 'Unknown')}, khởi động lại bot...")
        python = sys.executable
        os.execl(python, python, *sys.argv)

    elif cmd == "add":
        raw_query = message.strip()[len("automusic add"):].strip()
        if not raw_query:
            response = "❌ LỖI: Vui lòng nhập tên bài hát cần thêm!\nVí dụ: automusic add Shape of You"
        else:
            queries = [q.strip() for q in raw_query.split('\n') if q.strip()]
            if not queries:
                response = "❌ LỖI: Không tìm thấy tên bài hát hợp lệ!"
            else:
                added_count = 0
                failed_queries = []
                client.replyMessage(
                    Message(text=f"🔄 Đang tìm và thêm {len(queries)} bài hát..."), 
                    message_object, thread_id, thread_type, ttl=15000
                )

                for idx, query in enumerate(queries):
                    try:
                        search_msg = client.replyMessage(
                            Message(text=f"[{idx+1}/{len(queries)}] 🔍 Tìm: {query}..."), 
                            message_object, thread_id, thread_type, ttl=10000
                        )
                        results = search_soundcloud(query, limit=1)
                        
                        # FIX: Kiểm tra kết quả trả về
                        if not results or not isinstance(results, list) or len(results) == 0:
                            failed_queries.append(f"• {query} → Không tìm thấy")
                            continue
                        
                        song = results[0]
                        
                        # FIX: Kiểm tra cấu trúc của song
                        if not isinstance(song, dict) or 'track_id' not in song:
                            failed_queries.append(f"• {query} → Dữ liệu không hợp lệ")
                            continue
                            
                        songs = load_music_list()
                        if any(s.get('track_id') == song['track_id'] for s in songs):
                            failed_queries.append(f"• {query} → Đã tồn tại")
                            continue
                        songs.append(song)
                        save_music_list(songs)
                        added_count += 1
                        print(f"[AutoMusic] Đã thêm: {song.get('title', 'Unknown')} (ID: {song.get('track_id', 'N/A')})")
                        try:
                            client.editMessage(
                                Message(text=f"[{idx+1}/{len(queries)}] ✅ ĐÃ THÊM: {song.get('title', query)}"), 
                                search_msg, thread_id, thread_type
                            )
                        except:
                            pass
                    except Exception as e:
                        print(f"[AutoMusic] Lỗi khi thêm bài hát '{query}': {e}")
                        failed_queries.append(f"• {query} → Lỗi: {str(e)[:50]}...")
                    
                    time.sleep(1.5)

                # Tổng kết
                summary = [f"✅ HOÀN TẤT THÊM NHẠC"]
                summary.append(f"Đã thêm: {added_count}/{len(queries)} bài")
                if added_count > 0:
                    summary.append(f"Danh sách hiện có: {len(load_music_list())} bài")
                
                if failed_queries:
                    summary.append("\n❌ THẤT BẠI:")
                    summary.extend(failed_queries[:5])
                    if len(failed_queries) > 5:
                        summary.append(f"... và {len(failed_queries)-5} bài khác")
                
                response = "\n".join(summary)
                
        client.replyMessage(
            Message(text=response), 
            message_object, 
            thread_id, 
            thread_type, 
            ttl=30000
        )

    elif cmd == "del" and len(parts) >= 3:
        try:
            indices = []
            for p in parts[2:]:
                idx = int(p) - 1
                if idx < 0:
                    raise ValueError()
                indices.append(idx)
            songs = load_music_list()
            if not songs:
                response = "📭 DANH SÁCH TRỐNG\nKhông có bài nào để xóa!"
            else:
                removed = []
                failed = []
                indices = sorted(set(indices), reverse=True)
                for idx in indices:
                    if 0 <= idx < len(songs):
                        removed_song = songs.pop(idx)
                        removed.append(f"{len(removed)+1}. {removed_song['title']}")
                    else:
                        failed.append(str(idx + 1))
                save_music_list(songs)
                summary = [f"🗑️ ĐÃ XÓA {len(removed)} BÀI:"]
                summary.extend(removed[:10])
                if len(removed) > 10:
                    summary.append(f"... và {len(removed)-10} bài khác")
                if failed:
                    summary.append(f"\n⚠ KHÔNG TỒN TẠI: {', '.join(failed)}")
                summary.append(f"\n📊 Còn lại: {len(songs)} bài trong danh sách")
                response = "\n".join(summary)
        except ValueError:
            response = "❌ LỖI: Vui lòng nhập số hợp lệ!\nVí dụ: automusic del 1 2 3"
        except Exception as e:
            response = f"❌ LỖI HỆ THỐNG: {str(e)}"
        
        client.replyMessage(
            Message(text=response), 
            message_object, 
            thread_id, 
            thread_type, 
            ttl=30000
        )
        
    elif cmd == "delall":
        songs = load_music_list()
        song_count = len(songs)
        
        if song_count == 0:
            response = "📭 Danh sách đã trống, không có gì để xóa!"
        else:
            # Xóa tất cả
            save_music_list([])
            # Xóa cache
            MEDIA_CACHE.clear()
            
            response = (
                f"🗑️ ĐÃ XÓA TOÀN BỘ {song_count} BÀI HÁT\n"
                f"───────────────────────\n"
                f"• Đã xóa: {song_count} bài\n"
                f"• Cache: Đã xóa\n"
                f"• Danh sách hiện tại: 0 bài"
            )
            print(f"[AutoMusic] Đã xóa toàn bộ {song_count} bài hát")
        
        client.replyMessage(
            Message(text=response),
            message_object,
            thread_id,
            thread_type,
            ttl=30000
        )    

    elif cmd == "list":
        songs = load_music_list()
        if not songs:
            response = "📭 DANH SÁCH TRỐNG\nChưa có bài hát nào trong danh sách!"
            client.replyMessage(Message(text=response), message_object, thread_id, thread_type, ttl=30000)
            return

        MAX_CHARS = 2000
        messages = []
        current_msg = [f"📋 DANH SÁCH NHẠC ({len(songs)} bài):"]
        current_len = len(current_msg[0]) + 1

        for i, s in enumerate(songs, 1):
            line = f"{i}. {s['title']} - {s['artist']} ({s['duration']})"
            line_len = len(line) + 1

            if current_len + line_len > MAX_CHARS:
                messages.append("\n".join(current_msg))
                current_msg = [line]
                current_len = line_len
            else:
                current_msg.append(line)
                current_len += line_len

        if current_msg:
            messages.append("\n".join(current_msg))

        for idx, msg_text in enumerate(messages):
            prefix = f"[{idx+1}/{len(messages)}] " if len(messages) > 1 else ""
            final_text = prefix + msg_text

            try:
                if idx == 0:
                    client.replyMessage(
                        Message(text=final_text),
                        message_object,
                        thread_id,
                        thread_type,
                        ttl=30000
                    )
                else:
                    client.sendMessage(
                        Message(text=final_text),
                        thread_id,
                        thread_type,
                        ttl=30000
                    )
                time.sleep(0.8)
            except Exception as e:
                print(f"[AutoMusic] Lỗi gửi danh sách (phần {idx+1}): {e}")
                try:
                    client.sendMessage(
                        Message(text=f"[LỖI] Không gửi được phần {idx+1}/{len(messages)}"),
                        thread_id, thread_type
                    )
                except:
                    pass
        return  # Không gửi thêm response nào sau khi đã xử lý list

    else:
        response = (
            "❌ LỆNH KHÔNG HỢP LỆ\n"
            "──────────────────\n"
            "Sử dụng lệnh 'automusic' để xem hướng dẫn đầy đủ.\n"
            "Các lệnh hợp lệ:\n"
            "• automusic on <phút>\n"
            "• automusic off\n"
            "• automusic add <tên>\n"
            "• automusic del <số>\n"
            "• automusic list"
        )
        
        client.replyMessage(
            Message(text=response), 
            message_object, 
            thread_id, 
            thread_type, 
            ttl=30000
        )

# ---------------------------
# Khởi tạo
# ---------------------------
def get_mitaizl():
    return {
        'automusic': handle_automusic,
        'on_start_music': initialize_groups
    }