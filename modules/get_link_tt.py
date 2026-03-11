import os
import requests
import json
import time
from zlapi.models import Message
from zlapi import ZaloAPIException, ThreadType
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

def print_banner(keyword=None):
    banner = "=" * 50 + "\n"
    banner += "📽️  TIKTOK VIDEO FETCHER & CATBOX UPLOADER  📤\n"
    banner += "=" * 50 + "\n"
    if keyword:
        banner += f"Từ khóa: {keyword}\n"
    banner += "Chức năng: Tải video từ TikTok ➤ Tải lên Catbox qua URL ➤ Lưu vào gainhay.json\n"
    print(banner.encode('utf-8').decode('utf-8'))

def fetch_tiktok_videos(keyword):
    url = f'https://api.sumiproject.net/tiktok?search={keyword}'
    print(f"🔍 Đang tìm video với từ khóa: {keyword}".encode('utf-8').decode('utf-8'))
    
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        data = response.json()

        if data.get('code') != 0:
            print(f"❌ Lỗi: API trả về mã lỗi - {data.get('msg', 'Không có thông tin lỗi')}".encode('utf-8').decode('utf-8'))
            return []

        videos = data.get('data', {}).get('videos', [])
        if not isinstance(videos, list):
            print("❌ Lỗi: Dữ liệu video không đúng định dạng.".encode('utf-8').decode('utf-8'))
            return []

        print(f"✅ Tìm thấy {len(videos)} video.".encode('utf-8').decode('utf-8'))
        return videos

    except requests.RequestException as e:
        print(f"❌ Lỗi khi gọi TikTok API: {e}".encode('utf-8').decode('utf-8'))
        return []

def is_tiktok_url(input_string):
    """Check if the input string is a valid TikTok URL."""
    return input_string.startswith('https://www.tiktok.com/') or input_string.startswith('https://vt.tiktok.com/')

def fetch_tiktok_video_by_url(video_url):
    """Fetch a single TikTok video using the provided URL."""
    api_url = f'https://api.sumiproject.net/tiktok?video={video_url}'
    print(f"🔍 Đang lấy video từ URL: {video_url}".encode('utf-8').decode('utf-8'))
    
    try:
        response = requests.get(api_url, timeout=60)
        response.raise_for_status()
        data = response.json()

        if data.get('code') != 0:
            print(f"❌ Lỗi: API trả về mã lỗi - {data.get('msg', 'Không có thông tin lỗi')}".encode('utf-8').decode('utf-8'))
            return []

        video_data = data.get('data', {})
        if not video_data:
            print("❌ Lỗi: Không tìm thấy dữ liệu video.".encode('utf-8').decode('utf-8'))
            return []

        # Format the response to match the structure expected by the processing logic
        video = {
            'play': video_data.get('play'),
            'title': video_data.get('title', 'Untitled Video'),
            'duration': video_data.get('duration')
        }
        print(f"✅ Tìm thấy 1 video.".encode('utf-8').decode('utf-8'))
        return [video]  # Return as a list to match the keyword-based function

    except requests.RequestException as e:
        print(f"❌ Lỗi khi gọi TikTok API: {e}".encode('utf-8').decode('utf-8'))
        return []
        
def upload_to_catbox(video_url, retries=3, wait_time=120):
    """Tải video lên Catbox bằng URL."""
    temp_file = f"temp_video_{uuid.uuid4()}.mp4"
    for attempt in range(retries):
        print(f"🚀 Đang tải video lên Catbox (lần thử {attempt + 1}/{retries})...".encode('utf-8').decode('utf-8'))
        try:
            # Tải video từ TikTok
            video_response = requests.get(video_url, timeout=20)
            video_response.raise_for_status()
            
            # Lưu tạm thời
            with open(temp_file, 'wb') as f:
                f.write(video_response.content)

            # Tải lên Catbox
            with open(temp_file, 'rb') as file_handle:
                files = {'fileToUpload': ('video.mp4', file_handle, 'video/mp4')}
                data = {'reqtype': 'fileupload'}
                response = requests.post("https://catbox.moe/user/api.php", data=data, files=files)
            
            if response.status_code == 200:
                link = response.text.strip()
                print(f"✅ Tải lên thành công: {link}".encode('utf-8').decode('utf-8'))
                return link
            else:
                print(f"❌ Lỗi từ phía Catbox: {response.status_code}".encode('utf-8').decode('utf-8'))
                if attempt < retries - 1:
                    print(f"⏳ Chờ {wait_time} giây trước khi thử lại...".encode('utf-8').decode('utf-8'))
                    time.sleep(wait_time)
                continue

        except requests.RequestException as e:
            print(f"❌ Lỗi khi tải lên Catbox: {e}".encode('utf-8').decode('utf-8'))
            if attempt < retries - 1:
                print(f"⏳ Chờ {wait_time} giây trước khi thử lại...".encode('utf-8').decode('utf-8'))
                time.sleep(wait_time)
            continue
        except OSError as e:
            print(f"❌ Lỗi khi xử lý file tạm: {e}".encode('utf-8').decode('utf-8'))
            if attempt < retries - 1:
                print(f"⏳ Chờ {wait_time} giây trước khi thử lại...".encode('utf-8').decode('utf-8'))
                time.sleep(wait_time)
            continue
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    print(f"❌ Đã thử {retries} lần nhưng không thể tải lên Catbox.".encode('utf-8').decode('utf-8'))
    return None

def load_existing_videos():
    """Đọc danh sách video hiện có từ gainhay.json."""
    try:
        if os.path.exists('gainhay.json'):
            with open('gainhay.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except (IOError, json.JSONDecodeError) as e:
        print(f"❌ Lỗi khi đọc file gainhay.json: {e}".encode('utf-8').decode('utf-8'))
        return []

def save_videos(videos):
    """Lưu danh sách video vào gainhay.json."""
    try:
        with open('gainhay.json', 'w', encoding='utf-8') as f:
            json.dump(videos, f, ensure_ascii=False, indent=4)
        print("✅ Danh sách video đã lưu vào gainhay.json".encode('utf-8').decode('utf-8'))
        return True
    except IOError as e:
        print(f"❌ Lỗi khi ghi file gainhay.json: {e}".encode('utf-8').decode('utf-8'))
        return False

def fetch_and_upload_videos(message, message_object, thread_id, thread_type, author_id, client):
    action = "✅"
    try:
        client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
        print("📢 Phản ứng ✅ đã gửi.".encode('utf-8').decode('utf-8'))
    except ZaloAPIException as e:
        print(f"❌ Lỗi khi gửi phản ứng: {e}".encode('utf-8').decode('utf-8'))

    # Phân tích tin nhắn để lấy từ khóa hoặc URL
    message_parts = message.strip().split()
    if len(message_parts) < 2:
        try:
            error_message = Message(text="❌ Vui lòng cung cấp từ khóa hoặc URL TikTok. Ví dụ: getlinktt gái xinh hoặc getlinktt https://www.tiktok.com/@user/video/123")
            client.sendMessage(error_message, thread_id, thread_type)
            print("📩 Thông báo thiếu từ khóa/URL đã gửi.".encode('utf-8').decode('utf-8'))
            return
        except ZaloAPIException as e:
            print(f"❌ Lỗi khi gửi thông báo thiếu từ khóa/URL: {e}".encode('utf-8').decode('utf-8'))
            return

    input_data = " ".join(message_parts[1:])
    print_banner(input_data)
    
    # Check if the input is a TikTok URL
    if is_tiktok_url(input_data):
        videos = fetch_tiktok_video_by_url(input_data)
    else:
        videos = fetch_tiktok_videos(input_data)

    if not videos:
        print("❌ Không có video nào để xử lý.".encode('utf-8').decode('utf-8'))
        try:
            message = Message(text=f"❌ Không tìm thấy video nào với {'URL' if is_tiktok_url(input_data) else 'từ khóa'} '{input_data}'.")
            client.sendMessage(message, thread_id, thread_type)
            print("📢 Thông báo không tìm thấy video đã gửi.".encode('utf-8').decode('utf-8'))
        except ZaloAPIException as e:
            print(f"❌ Lỗi khi gửi thông báo không tìm thấy video: {e}".encode('utf-8').decode('utf-8'))
        return

    existing_videos = load_existing_videos()
    existing_links = {v['link'] for v in existing_videos}
    new_videos = []
    next_index = max([v.get('index', 0) for v in existing_videos], default=0) + 1

    # Chuẩn bị danh sách video để tải lên (xử lý tất cả video hợp lệ)
    video_tasks = []
    for i, video in enumerate(videos):
        video_url = video.get('play')
        title = video.get('title', f'Video {i+1}')
        duration = video.get('duration')

        if not video_url:
            print(f"⚠️ Bỏ qua video {i+1} do thiếu URL.".encode('utf-8').decode('utf-8'))
            continue
        if duration is None:
            print(f"⚠️ Bỏ qua video {i+1} do thiếu thời lượng.".encode('utf-8').decode('utf-8'))
            continue
        if duration > 60:
            print(f"⚠️ Bỏ qua video {i+1} vì thời lượng ({duration}s) vượt quá 60s.".encode('utf-8').decode('utf-8'))
            continue

        clean_title = title.split('#')[0].strip() if '#' in title else title
        if not clean_title:
            clean_title = f'Video {i+1}'
        video_tasks.append((video_url, clean_title))

    # Tải đồng thời các video lên Catbox
    if video_tasks:
        print(f"📦 Chuẩn bị tải lên {len(video_tasks)} video hợp lệ.".encode('utf-8').decode('utf-8'))
        with ThreadPoolExecutor(max_workers=min(len(video_tasks), 30)) as executor:
            future_to_video = {executor.submit(upload_to_catbox, task[0]): task for task in video_tasks}
            results = []
            for future in as_completed(future_to_video):
                video_url, clean_title = future_to_video[future]
                try:
                    catbox_link = future.result()
                    if catbox_link and catbox_link not in existing_links:
                        results.append((catbox_link, clean_title))
                    elif catbox_link in existing_links:
                        print(f"⚠️ Video đã tồn tại trong gainhay.json: {catbox_link}".encode('utf-8').decode('utf-8'))
                    else:
                        print(f"⚠️ Tải lên thất bại cho video: {video_url}".encode('utf-8').decode('utf-8'))
                except Exception as e:
                    print(f"❌ Lỗi khi xử lý video {video_url}: {e}".encode('utf-8').decode('utf-8'))

        # Gán index và thêm vào new_videos
        for i, (catbox_link, clean_title) in enumerate(results):
            video_entry = {
                'id': str(uuid.uuid4()),
                'index': next_index + i,
                'title': clean_title,
                'link': catbox_link
            }
            new_videos.append(video_entry)
            existing_links.add(catbox_link)
            print(f"✅ Đã thêm video vào danh sách: {next_index + i}. {clean_title} - {catbox_link}".encode('utf-8').decode('utf-8'))
    else:
        print("⚠️ Không có video hợp lệ để tải lên.".encode('utf-8').decode('utf-8'))

    # Lưu và gửi kết quả
    if new_videos:
        existing_videos.extend(new_videos)
        if save_videos(existing_videos):
            try:
                success_message = Message(
                    text=f"✅ Đã xử lý và lưu {len(new_videos)} video mới vào gainhay.json!\n" +
                         "\n".join([f"{v['index']}. {v['title']}\n{v['link']}" for v in new_videos])
                )
                client.sendMessage(success_message, thread_id, thread_type)
                print("📩 Thông báo thành công đã gửi.".encode('utf-8').decode('utf-8'))
            except ZaloAPIException as e:
                print(f"❌ Lỗi khi gửi thông báo thành công: {e}".encode('utf-8').decode('utf-8'))
        else:
            try:
                error_message = Message(text="❌ Lỗi khi lưu file gainhay.json.")
                client.sendMessage(error_message, thread_id, thread_type)
                print("📩 Thông báo lỗi đã gửi.".encode('utf-8').decode('utf-8'))
            except ZaloAPIException as e:
                print(f"❌ Lỗi khi gửi thông báo lỗi lưu: {e}".encode('utf-8').decode('utf-8'))
    else:
        print("\n⚠️ Không có video mới nào để lưu.".encode('utf-8').decode('utf-8'))
        try:
            no_link_message = Message(
                text="⚠️ Không có video nào được tải lên thành công hoặc tất cả video đã tồn tại."
            )
            client.sendMessage(no_link_message, thread_id, thread_type)
            print("📩 Thông báo không có link đã gửi.".encode('utf-8').decode('utf-8'))
        except ZaloAPIException as e:
            print(f"❌ Lỗi khi gửi thông báo không có link: {e}".encode('utf-8').decode('utf-8'))

def delete_video(message, message_object, thread_id, thread_type, author_id, client):
    try:
        client.sendReaction(message_object, "🗑️", thread_id, thread_type, reactionType=75)
        print("📢 Phản ứng 🗑️ đã gửi.".encode('utf-8').decode('utf-8'))
    except ZaloAPIException as e:
        print(f"❌ Lỗi khi gửi phản ứng: {e}".encode('utf-8').decode('utf-8'))

    # Lấy danh sách các số thứ tự từ tin nhắn
    message_parts = message.strip().split()
    if len(message_parts) < 2:
        try:
            error_message = Message(text="❌ Vui lòng cung cấp ít nhất một số thứ tự video để xóa. Ví dụ: delete 35 36")
            client.sendMessage(error_message, thread_id, thread_type)
            print("📩 Thông báo lỗi index đã gửi.".encode('utf-8').decode('utf-8'))
            return
        except ZaloAPIException as e:
            print(f"❌ Lỗi khi gửi thông báo lỗi: {e}".encode('utf-8').decode('utf-8'))
            return

    try:
        video_indices = [int(idx) for idx in message_parts[1:]]
        if not video_indices:
            raise ValueError("Không tìm thấy số thứ tự video hợp lệ.")
    except ValueError:
        try:
            error_message = Message(text="❌ Vui lòng cung cấp các số thứ tự hợp lệ. Ví dụ: delete 35 36")
            client.sendMessage(error_message, thread_id, thread_type)
            print("📩 Thông báo lỗi index đã gửi.".encode('utf-8').decode('utf-8'))
            return
        except ZaloAPIException as e:
            print(f"❌ Lỗi khi gửi thông báo lỗi: {e}".encode('utf-8').decode('utf-8'))
            return

    existing_videos = load_existing_videos()
    if not existing_videos:
        try:
            error_message = Message(text="❌ Không có video nào trong danh sách.")
            client.sendMessage(error_message, thread_id, thread_type)
            print("📩 Thông báo danh sách rỗng đã gửi.".encode('utf-8').decode('utf-8'))
            return
        except ZaloAPIException as e:
            print(f"❌ Lỗi khi gửi thông báo danh sách rỗng: {e}".encode('utf-8').decode('utf-8'))
            return

    initial_len = len(existing_videos)
    # Lọc bỏ các video có index nằm trong danh sách video_indices
    deleted_indices = []
    existing_videos = [v for v in existing_videos if v['index'] not in video_indices]
    deleted_indices = [idx for idx in video_indices if any(v['index'] == idx for v in load_existing_videos())]

    if len(existing_videos) < initial_len:
        # Không đánh số lại index, giữ nguyên index của các video còn lại
        if save_videos(existing_videos):
            try:
                success_message = Message(
                    text=f"✅ Đã xóa {len(deleted_indices)} video với số thứ tự: {', '.join(map(str, deleted_indices))} khỏi danh sách."
                )
                client.sendMessage(success_message, thread_id, thread_type)
                print("📩 Thông báo xóa thành công đã gửi.".encode('utf-8').decode('utf-8'))
            except ZaloAPIException as e:
                print(f"❌ Lỗi khi gửi thông báo xóa thành công: {e}".encode('utf-8').decode('utf-8'))
        else:
            try:
                error_message = Message(text="❌ Lỗi khi lưu danh sách sau khi xóa.")
                client.sendMessage(error_message, thread_id, thread_type)
                print("📩 Thông báo lỗi lưu đã gửi.".encode('utf-8').decode('utf-8'))
            except ZaloAPIException as e:
                print(f"❌ Lỗi khi gửi thông báo lỗi lưu: {e}".encode('utf-8').decode('utf-8'))
    else:
        try:
            error_message = Message(
                text=f"❌ Không tìm thấy video với số thứ tự: {', '.join(map(str, video_indices))}."
            )
            client.sendMessage(error_message, thread_id, thread_type)
            print("📩 Thông báo không tìm thấy index đã gửi.".encode('utf-8').decode('utf-8'))
        except ZaloAPIException as e:
            print(f"❌ Lỗi khi gửi thông báo không tìm thấy index: {e}".encode('utf-8').decode('utf-8'))

            
def get_mitaizl():
    return {
        'getlinktt': fetch_and_upload_videos,
        'delete': delete_video
    }