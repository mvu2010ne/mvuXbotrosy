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
    'tác giả': "Minh Vũ Shinn Cte (sửa lại bởi Grok)",
    'mô tả': "Tải video ngẫu nhiên, chia nhỏ, upload trực tiếp lên Zalo và gửi bằng remote video.",
    'tính năng': [
        "Lấy video ngẫu nhiên từ txt_data/vdx.txt",
        "Chia video không re-encode → siêu nhanh",
        "Upload trực tiếp lên server Zalo (dùng _uploadAttachment)",
        "Gửi remote video + thumbnail chính chủ Zalo",
        "Tự động dọn file tạm"
    ]
}

headers = {
    'User-Agent': 'Mozilla/5.0'
}

processing_locks = {}
lock = threading.Lock()

# ====================================
# 🟢 Đọc danh sách link video
# ====================================
def get_video_links_from_file(filepath="txt_data/vdx.txt"):
    if not os.path.exists(filepath):
        return None, "Tệp txt_data/vdx.txt không tồn tại."
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
            return lines, None
    except Exception as e:
        return None, str(e)

# ====================================
# 🟢 Tải video về
# ====================================
def download_video(url, output_path):
    try:
        with requests.get(url, headers=headers, stream=True, timeout=30) as r:
            r.raise_for_status()
            total_size = int(r.headers.get("content-length", 0)) or None
            with open(output_path, "wb") as f, tqdm(
                desc="Đang tải video",
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
# 🟢 Lấy metadata video bằng FFprobe
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
        duration = float(result[2])
        return width, height, int(duration * 1000), None
    except Exception as e:
        return 1280, 720, 60000, str(e)  # fallback

# ====================================
# 🟢 Tạo thumbnail bằng FFmpeg
# ====================================
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
# 🟢 Chia video nhanh (copy stream - không re-encode)
# ====================================
def split_video_fast(input_file, max_size_mb=128):
    max_bytes = max_size_mb * 1024 * 1024
    file_size = os.path.getsize(input_file)
    if file_size <= max_bytes:
        return [input_file], None
    _, _, duration_ms, _ = get_video_metadata(input_file)
    duration_sec = duration_ms / 1000.0
    bitrate = (file_size * 8) / duration_sec if duration_sec > 0 else 4000000
    max_duration_per_part = (max_bytes * 8) / bitrate
    parts = []
    start = 0.0
    part_index = 0
    while start < duration_sec:
        end = min(start + max_duration_per_part, duration_sec)
        out_name = f"temp_part_{part_index}.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-i", input_file,
            "-ss", str(start),
            "-to", str(end),
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            out_name
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        actual_size = os.path.getsize(out_name)
        if actual_size <= max_bytes + 1024*1024:
            parts.append(out_name)
            part_index += 1
        else:
            os.remove(out_name)
            break
        start = end
    return parts, None

# ====================================
# 🔵 Hàm xử lý lệnh vdx – CHỈ FIX THUMBNAIL
# ====================================
def handle_vdx_command(message, message_object, thread_id, thread_type, author_id, client):
    with lock:
        if thread_id in processing_locks:
            client.sendMessage(Message(text="⏳ Đang xử lý video khác, vui lòng đợi chút nhé!"), thread_id, thread_type, ttl=10000)
            return
        processing_locks[thread_id] = True

    try:
        client.sendMessage(Message(text="⬇️ Đang lấy và xử lý video..."), thread_id, thread_type, ttl=15000)

        # 1. Lấy link ngẫu nhiên
        links, err = get_video_links_from_file()
        if err:
            client.sendMessage(Message(text=f"Lỗi: {err}"), thread_id, thread_type)
            return
        video_url = random.choice(links)

        # 2. Tải video gốc
        temp_video = "temp_original.mp4"
        success, err = download_video(video_url, temp_video)
        if not success:
            client.sendMessage(Message(text=f"Tải video thất bại: {err}"), thread_id, thread_type)
            return

        # 3. Chia video
        parts, err = split_video_fast(temp_video, max_size_mb=128)
        if err or not parts:
            client.sendMessage(Message(text=f"Chia video thất bại: {err}"), thread_id, thread_type)
            return

        # 4. Chuẩn bị upload thumbnail + video từng phần
        upload_tasks = []
        for i, part_file in enumerate(parts):
            width, height, duration_ms, _ = get_video_metadata(part_file)
            thumb_file = f"thumb_part_{i}.jpg"
            generate_thumbnail(part_file, thumb_file)
            upload_tasks.append((i, part_file, thumb_file, width, height, duration_ms))

        # 5. Upload song song – FIX LẤY URL THUMBNAIL
        uploaded_results = {}
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {}
            for idx, video_path, thumb_path, w, h, dur in upload_tasks:
                # Upload video
                future_video = executor.submit(client._uploadAttachment, video_path, thread_id, thread_type)
                futures[future_video] = ("video", idx)

                # Upload thumbnail (ưu tiên _uploadImage nếu có)
                if os.path.exists(thumb_path):
                    if hasattr(client, '_uploadImage'):
                        future_thumb = executor.submit(client._uploadImage, thumb_path, thread_id, thread_type)
                        print(f"[VDX] Upload thumbnail phần {idx} bằng _uploadImage")
                    else:
                        future_thumb = executor.submit(client._uploadAttachment, thumb_path, thread_id, thread_type)
                        print(f"[VDX] Upload thumbnail phần {idx} bằng _uploadAttachment")
                    futures[future_thumb] = ("thumb", idx)

            for future in as_completed(futures):
                f_type, idx = futures[future]
                try:
                    result = future.result()

                    # FIX CHÍNH: Lấy URL đúng cho thumbnail và video
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

                    if url:
                        print(f"[VDX] Upload {f_type} phần {idx} THÀNH CÔNG")
                    else:
                        print(f"[VDX] Upload {f_type} phần {idx} thành công nhưng không có URL")

                    if idx not in uploaded_results:
                        uploaded_results[idx] = {}
                    uploaded_results[idx][f_type] = url

                except Exception as e:
                    print(f"[VDX] Upload {f_type} phần {idx} lỗi: {e}")
                    if idx not in uploaded_results:
                        uploaded_results[idx] = {}
                    uploaded_results[idx][f_type] = None

        # 6. Gửi remote video từng phần (giữ nguyên như cũ)
        for idx, _, thumb_path, w, h, dur in upload_tasks:
            video_url = uploaded_results.get(idx, {}).get("video")
            thumb_url = uploaded_results.get(idx, {}).get("thumb")

            if not video_url:
                client.sendMessage(Message(text=f"Phần {idx+1}: Upload video thất bại, bỏ qua."), thread_id, thread_type)
                continue

            title = "" if len(parts) == 1 else (f"Phần {idx+1}/{len(parts)}" if idx < len(parts)-1 else "Phần cuối")

            client.sendRemoteVideo(
                video_url,
                thumb_url,  # Bây giờ sẽ có URL hợp lệ → thumbnail đẹp
                duration=dur,
                width=w,
                height=h,
                thread_id=thread_id,
                thread_type=thread_type,
                message=Message(text=title),
                ttl=180000
            )
            time.sleep(1)  # tránh flood

    except Exception as e:
        client.sendMessage(Message(text=f"Lỗi nghiêm trọng: {str(e)}"), thread_id, thread_type)
    finally:
        # Dọn dẹp file tạm (giữ nguyên như cũ)
        files_to_remove = [temp_video] if 'temp_video' in locals() and os.path.exists(temp_video) else []
        for _, part, thumb, *_ in upload_tasks:
            if os.path.exists(part):
                files_to_remove.append(part)
            if os.path.exists(thumb):
                files_to_remove.append(thumb)
        for f in files_to_remove:
            try:
                os.remove(f)
            except:
                pass
        with lock:
            if thread_id in processing_locks:
                del processing_locks[thread_id]

def get_mitaizl():
    return {
        'vdx': handle_vdx_command
    }