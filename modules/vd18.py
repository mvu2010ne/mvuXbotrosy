import random
import os
import requests
import time
import subprocess
import threading
from zlapi.models import Message, ThreadType
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

des = {
    'tác giả': "Minh Vũ Shinn Cte (cải tiến bởi Grok)",
    'mô tả': "🎥 Gửi video 18+ ngẫu nhiên từ txt_data/vd18.txt, chia nhỏ nhanh (không re-encode), upload trực tiếp lên Zalo và gửi remote video.",
    'tính năng': [
        "Lấy video ngẫu nhiên từ txt_data/vd18.txt (chọn thẳng, giống vdx)",
        "Chia video siêu nhanh bằng -c copy (FFmpeg)",
        "Upload trực tiếp lên server Zalo bằng _uploadAttachment",
        "Gửi remote video + thumbnail chính chủ Zalo (fix đẹp 100%)",
        "Hiển thị 'Phần X' hoặc 'Phần cuối' thông minh",
        "Tự động dọn file tạm, chống flood"
    ]
}

headers = {
    'User-Agent': 'Mozilla/5.0'
}

# Locking
processing_locks = {}
lock = threading.Lock()

# ====================================
# 🟢 Đọc danh sách link video
# ====================================
def get_video_links_from_file(filepath="txt_data/vd18.txt"):
    if not os.path.exists(filepath):
        return None, "Tệp txt_data/vd18.txt không tồn tại."
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
            return lines, None
    except Exception as e:
        return None, str(e)

# ====================================
# 🟢 Tải video
# ====================================
def download_video(url, output_path):
    try:
        with requests.get(url, headers=headers, stream=True, timeout=30) as r:
            r.raise_for_status()
            total_size = int(r.headers.get("content-length", 0)) or None
            with open(output_path, "wb") as f, tqdm(
                desc="Đang tải video 18+",
                total=total_size,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                leave=False
            ) as pb:
                for chunk in r.iter_content(8192):
                    if chunk:
                        f.write(chunk)
                        pb.update(len(chunk))
        return True, None
    except Exception as e:
        return False, str(e)

# ====================================
# 🟢 Metadata & Thumbnail
# ====================================
def get_video_metadata(file_path):
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        result = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip().split('\n')
        width = int(result[0])
        height = int(result[1])
        duration = int(float(result[2]) * 1000)
        return width, height, duration, None
    except Exception as e:
        return 1280, 720, 60000, str(e)  # fallback

def generate_thumbnail(video_path, output_path):
    try:
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-ss", "00:00:01", "-vframes", "1",
            "-q:v", "2",
            output_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True, None
    except Exception as e:
        return False, str(e)

# ====================================
# 🟢 Chia video nhanh (copy stream)
# ====================================
def split_video_fast(input_file, max_size_mb=128):
    max_bytes = max_size_mb * 1024 * 1024
    file_size = os.path.getsize(input_file)
    if file_size <= max_bytes:
        return [input_file], None
    _, _, duration_ms, _ = get_video_metadata(input_file)
    duration_sec = duration_ms / 1000.0
    if duration_sec <= 0:
        return [input_file], None
    bitrate = (file_size * 8) / duration_sec
    max_duration_per_part = (max_bytes * 8) / bitrate
    parts = []
    start = 0.0
    part_index = 0
    while start < duration_sec:
        end = min(start + max_duration_per_part, duration_sec)
        out_name = f"temp_part18_{part_index}.mp4"
        cmd = [
            "ffmpeg", "-y", "-i", input_file,
            "-ss", str(start), "-to", str(end),
            "-c", "copy", "-avoid_negative_ts", "make_zero",
            out_name
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        if os.path.getsize(out_name) > max_bytes + 1024*1024:
            os.remove(out_name)
            break
        parts.append(out_name)
        part_index += 1
        start = end
    return parts, None

# ====================================
# 🔵 Handler lệnh vd18 – FIX THUMBNAIL HOÀN HẢO (giống vdx/vdgai)
# ====================================
def handle_vd18_command(message, message_object, thread_id, thread_type, author_id, client):
    with lock:
        if thread_id in processing_locks:
            client.sendMessage(Message(text="⏳ Đang xử lý video 18+ khác, vui lòng đợi chút nhé!"), thread_id, thread_type, ttl=10000)
            return
        processing_locks[thread_id] = True

    temp_video = None
    upload_tasks = []
    try:
        client.sendMessage(Message(text="🔥 Video 18+ đang được chuẩn bị, chờ tí nhé..."), thread_id, thread_type, ttl=20000)

        links, err = get_video_links_from_file()
        if err:
            client.sendMessage(Message(text=f"Lỗi: {err}"), thread_id, thread_type)
            return
        if not links:
            client.sendMessage(Message(text="Không có link nào trong txt_data/vd18.txt"), thread_id, thread_type)
            return

        video_url = random.choice(links)
        temp_video = "temp_vd18_original.mp4"
        success, err = download_video(video_url, temp_video)
        if not success:
            client.sendMessage(Message(text=f"Tải video thất bại: {err}"), thread_id, thread_type)
            return

        parts, err = split_video_fast(temp_video, max_size_mb=128)
        if err or not parts:
            client.sendMessage(Message(text=f"Chia video thất bại: {err or 'Không rõ'}"), thread_id, thread_type)
            return

        # Chuẩn bị task upload
        for i, part_file in enumerate(parts):
            width, height, duration_ms, _ = get_video_metadata(part_file)
            thumb_file = f"thumb18_part_{i}.jpg"
            generate_thumbnail(part_file, thumb_file)
            upload_tasks.append((i, part_file, thumb_file, width, height, duration_ms))

        # Upload song song – FIX LẤY THUMBNAIL ĐẸP
        uploaded_results = {}
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {}
            for idx, video_path, thumb_path, w, h, dur in upload_tasks:
                # Video
                future_video = executor.submit(client._uploadAttachment, video_path, thread_id, thread_type)
                futures[future_video] = ("video", idx)

                # Thumbnail – ưu tiên _uploadImage
                if os.path.exists(thumb_path):
                    if hasattr(client, '_uploadImage'):
                        future_thumb = executor.submit(client._uploadImage, thumb_path, thread_id, thread_type)
                    else:
                        future_thumb = executor.submit(client._uploadAttachment, thumb_path, thread_id, thread_type)
                    futures[future_thumb] = ("thumb", idx)

            for future in as_completed(futures):
                f_type, idx = futures[future]
                try:
                    result = future.result()

                    # FIX CHÍNH: Lấy URL thumbnail đầy đủ
                    if f_type == "thumb":
                        url = (
                            result.get("normalUrl") or
                            result.get("hdUrl") or
                            result.get("thumbUrl") or
                            result.get("fileUrl") or
                            result.get("url")
                        )
                    else:  # video
                        url = result.get("fileUrl") or result.get("url")

                    if idx not in uploaded_results:
                        uploaded_results[idx] = {}
                    uploaded_results[idx][f_type] = url

                except Exception as e:
                    print(f"[VD18] Upload {f_type} phần {idx} lỗi: {e}")
                    if idx not in uploaded_results:
                        uploaded_results[idx] = {}
                    uploaded_results[idx][f_type] = None

        # Gửi từng phần – giữ nguyên caption và logic như cũ
        for idx, _, thumb_path, w, h, dur in upload_tasks:
            video_url_up = uploaded_results.get(idx, {}).get("video")
            thumb_url = uploaded_results.get(idx, {}).get("thumb")

            if not video_url_up:
                client.sendMessage(Message(text=f"Phần {idx+1}: Upload thất bại, bỏ qua."), thread_id, thread_type)
                continue

            title = "Video 18+ của bạn đây, chúc ngon miệng 🍒"
            if len(parts) > 1:
                title += f" - Phần {idx+1}/{len(parts)}" if idx < len(parts)-1 else " - Phần cuối"

            client.sendRemoteVideo(
                video_url_up,
                thumb_url,  # Bây giờ thumbnail sẽ đẹp rõ nét
                duration=dur,
                width=w,
                height=h,
                thread_id=thread_id,
                thread_type=thread_type,
                message=Message(text=title),
                ttl=300000
            )
            time.sleep(1.5)

    except Exception as e:
        client.sendMessage(Message(text=f"Lỗi nghiêm trọng: {str(e)}"), thread_id, thread_type)
    finally:
        # Dọn dẹp – giữ nguyên như cũ
        files_to_remove = []
        if temp_video and os.path.exists(temp_video):
            files_to_remove.append(temp_video)
        for _, part, thumb, *_ in upload_tasks:
            if os.path.exists(part):
                files_to_remove.append(part)
            if os.path.exists(thumb):
                files_to_remove.append(thumb)
        for f in set(files_to_remove):
            try:
                os.remove(f)
            except:
                pass
        with lock:
            if thread_id in processing_locks:
                del processing_locks[thread_id]

def get_mitaizl():
    return {
        'vd18': handle_vd18_command
    }