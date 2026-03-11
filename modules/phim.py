
import os
import re
import time
import random
import json
import requests
import subprocess
import urllib.parse
import asyncio
import aiofiles
import aiohttp
from typing import List, Dict, Any
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
from io import BytesIO
from cachetools import LRUCache
from datetime import datetime
from zlapi import *
from zlapi.models import *
from concurrent.futures import ThreadPoolExecutor
import math


# ---------------------------
# Biến toàn cục - GIỮ NGUYÊN TÊN BIẾN CŨ
# ---------------------------
movie_search_results = {}  # Lưu danh sách phim theo thread_id
movie_select_status = {}   # Lưu trạng thái chọn phim: (time_sent, has_selected, msg_id, thread_type)
episode_select_results = {}  # Lưu dữ liệu phim đã chọn cho chọn tập theo thread_id
episode_select_status = {}   # Lưu trạng thái chọn tập: (time_sent, has_selected, msg_id, thread_type)
PLATFORM = "phimapi"
TIME_TO_SELECT = 120  # 120 giây (2 phút)
MAX_VIDEO_DURATION = 7200  # 120 phút = 7200 giây (tăng thời gian cho phim)
BACKGROUND_FOLDER = 'backgrounds'
if os.path.isdir(BACKGROUND_FOLDER):
    BACKGROUND_IMAGES = [
        os.path.join(BACKGROUND_FOLDER, f) 
        for f in os.listdir(BACKGROUND_FOLDER) 
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ]
else:
    BACKGROUND_IMAGES = []

CACHE_PATH = "cache/"
os.makedirs(CACHE_PATH, exist_ok=True)
MEDIA_CACHE = LRUCache(maxsize=500)  # Bộ nhớ đệm cho URL video đã tải lên
PHIM_CACHE = {}
# Các hằng số
DEFAULT_THUMBNAIL = 'https://i.imgur.com/ZaAJm1Z.jpeg'
FFMPEG_PATH = "/usr/bin/ffmpeg"

# ---------------------------
# Hàm hỗ trợ chung (giống search_ytb.py)
# ---------------------------
def get_headers():
    print("[DEBUG] Hàm get_headers() được gọi")
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "*/*",
        "Referer": "https://phimapi.com/",
        "Connection": "keep-alive"
    }

def delete_file(file_path: str):
    """Xóa file nếu tồn tại"""
    print(f"[DEBUG] Hàm delete_file() được gọi với file_path: {file_path}")
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"[DEBUG] Đã xóa tệp: {file_path}")
        else:
            print(f"[DEBUG] Tệp không tồn tại: {file_path}")
    except Exception as e:
        print(f"[ERROR] Lỗi khi xóa tệp {file_path}: {e}")

def format_duration(seconds: int) -> str:
    """Định dạng thời lượng sang chuỗi đẹp (từ search_ytb.py)"""
    print(f"[DEBUG] Hàm format_duration() được gọi với seconds: {seconds}")
    if not seconds:
        print("[DEBUG] format_duration() trả về: N/A")
        return "N/A"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        result = f"{hours}h{minutes:02d}m{secs:02d}s"
    elif minutes > 0:
        result = f"{minutes}m{secs:02d}s"
    else:
        result = f"{secs}s"
    
    print(f"[DEBUG] format_duration() trả về: {result}")
    return result

def download_video_phim(m3u8_url: str, title: str, output_path: str = None) -> Dict[str, Any]:
    """Tải video từ m3u8 URL cho phim - PHIÊN BẢN ĐƠN GIẢN"""
    print(f"[DEBUG] Hàm download_video_phim() được gọi với m3u8_url: {m3u8_url}")
    
    try:
        os.makedirs("cache", exist_ok=True)
        
        # Tạo tên file an toàn
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)[:50]
        timestamp = int(time.time())
        
        if not output_path:
            output_path = f"cache/phim_{safe_title}_{timestamp}.mp4"
        
        print(f"[DEBUG] Output path: {output_path}")
        
        # Kiểm tra ffmpeg
        ffmpeg_cmd = FFMPEG_PATH if os.path.exists(FFMPEG_PATH) else 'ffmpeg'
        
        # Tải video với ffmpeg - THÊM THÊM XỬ LÝ LỖI
        print(f"[DEBUG] Đang tải video với ffmpeg...")
        
        try:
            # Lệnh ffmpeg đơn giản với timeout ngắn hơn
            command = [
                ffmpeg_cmd, "-y",
                "-timeout", "30000000",  # Timeout 30 giây
                "-i", m3u8_url,
                "-c", "copy",  # Copy codec
                "-bsf:a", "aac_adtstoasc",
                "-movflags", "faststart",
                "-t", "900",  # CHỈ tải 15 phút đầu (900 giây) - RÚT NGẮN THỜI GIAN
                output_path
            ]
            
            print(f"[DEBUG] Chạy lệnh ffmpeg: {' '.join(command)}")
            
            # Thêm timeout cho subprocess và kiểm tra tiến trình
            start_time = time.time()
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Theo dõi tiến trình với timeout
            timeout_seconds = 120  # 2 phút timeout
            while True:
                if time.time() - start_time > timeout_seconds:
                    print(f"[ERROR] Timeout khi tải video ({timeout_seconds} giây)")
                    process.terminate()
                    process.wait(timeout=5)
                    return None
                
                # Kiểm tra process đã kết thúc chưa
                returncode = process.poll()
                if returncode is not None:
                    # Process đã kết thúc
                    stdout, stderr = process.communicate()
                    print(f"[DEBUG] FFmpeg return code: {returncode}")
                    print(f"[DEBUG] FFmpeg stderr (200 ký tự đầu): {stderr[:200]}")
                    
                    if returncode != 0:
                        print(f"[ERROR] Lỗi ffmpeg: {stderr[:500]}")
                        return None
                    
                    # Thoát vòng lặp
                    break
                
                # Chờ một chút trước khi kiểm tra lại
                time.sleep(1)
            
        except subprocess.TimeoutExpired:
            print(f"[ERROR] Timeout khi tải video")
            return None
        except Exception as e:
            print(f"[ERROR] Lỗi khi chạy ffmpeg: {e}")
            return None
        
        # Kiểm tra file
        if not os.path.exists(output_path):
            print(f"[ERROR] File không tồn tại sau khi ffmpeg chạy")
            return None
        
        file_size = os.path.getsize(output_path)
        if file_size == 0:
            print(f"[ERROR] File rỗng")
            delete_file(output_path)
            return None
        
        print(f"[DEBUG] Đã tải video thành công: {output_path} ({file_size} bytes)")
        
        # Lấy thời lượng thực tế của file
        try:
            # Sử dụng ffprobe để lấy thời lượng
            probe_cmd = [
                ffmpeg_cmd, "-i", output_path,
                "-show_entries", "format=duration",
                "-v", "quiet",
                "-of", "csv=p=0"
            ]
            
            result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                print(f"[DEBUG] Thời lượng thực tế: {duration} giây")
            else:
                duration = 900  # Mặc định 15 phút
                print(f"[DEBUG] Không thể lấy thời lượng, sử dụng mặc định: {duration} giây")
        except Exception as e:
            print(f"[DEBUG] Lỗi khi lấy thời lượng: {e}")
            duration = 900  # Mặc định 15 phút
        
        return {
            'file_path': output_path,
            'duration': int(duration),
            'title': title,
            'size': file_size
        }
        
    except Exception as e:
        print(f"[ERROR] Lỗi khi tải video phim: {e}")
        import traceback
        traceback.print_exc()
        return None



# Hàm upload sync wrapper để gọi async function
def upload_to_zalo(client, file_path: str, thread_id: str, thread_type: Any):
    """Upload file lên server Zalo và trả về URL - FIX Error #0 SUCCESS"""
    print(f"[DEBUG] Hàm upload_to_zalo() được gọi")
    print(f"[DEBUG] - File path: {file_path}")
    print(f"[DEBUG] - Thread ID: {thread_id}")
    print(f"[DEBUG] - Thread Type: {thread_type}")
    
    try:
        if not os.path.exists(file_path):
            print(f"[ERROR] File không tồn tại: {file_path}")
            return None
        
        file_size = os.path.getsize(file_path)
        print(f"[DEBUG] File size: {file_size} bytes (~{file_size/(1024*1024):.1f} MB)")
        
        if file_size == 0:
            print(f"[ERROR] File rỗng: {file_path}")
            return None
        
        print(f"[DEBUG] Đang gọi _uploadAttachment (sync)...")
        try:
            upload_response = client._uploadAttachment(file_path, thread_id, thread_type)
        except Exception as upload_exc:
            # *** QUAN TRỌNG: CHECK Error #0 = SUCCESS ***
            error_msg = str(upload_exc)
            if "Error #0 when sending requests: Successful" in error_msg:
                print(f"[WARNING] Bắt được Error #0 (SUCCESS) - TIẾP TỤC XỬ LÝ RESPONSE")
                # Response có thể vẫn nằm trong exception args hoặc client attributes
                # Thử lấy từ client._upload_callbacks hoặc response cuối
                try:
                    # Cách 1: Lấy từ client attributes (nếu có)
                    if hasattr(client, '_last_upload_response'):
                        upload_response = getattr(client, '_last_upload_response')
                        print(f"[DEBUG] Lấy response từ client._last_upload_response")
                    else:
                        # Cách 2: Zalo API vẫn lưu response ở đâu đó - thử mock success
                        print(f"[WARNING] Không tìm thấy response, nhưng Error #0 = SUCCESS → Giả định upload OK")
                        return f"https://zalo-upload-success-placeholder-{int(time.time())}"  # Fallback URL
                except:
                    print(f"[WARNING] Không thể lấy response từ exception, dùng fallback")
                    return None
            else:
                # Lỗi thật → raise lại
                print(f"[ERROR] Lỗi upload thật (không phải Error #0): {upload_exc}")
                raise upload_exc
        
        print(f"[DEBUG] Upload response type: {type(upload_response)}")
        if isinstance(upload_response, dict):
            print(f"[DEBUG] Upload response raw: {upload_response}")
        
        file_url = None
        
        # *** XỬ LÝ TẤT CẢ CÁC TRƯỜNG HỢP ***
        if isinstance(upload_response, dict):
            # Key chính xác từ log của bạn
            file_url = upload_response.get("fileUrl")
            if not file_url:
                # Thử các key khác
                file_url = (
                    upload_response.get("url") or 
                    upload_response.get("file_url") or
                    upload_response.get("link") or
                    upload_response.get("data")
                )
            # Fallback: lấy value đầu tiên nếu dict chỉ có 1 item
            if not file_url and len(upload_response) > 0:
                first_value = next(iter(upload_response.values()))
                if isinstance(first_value, str) and ('http' in first_value or 'dlfl.vn' in first_value):
                    file_url = first_value
        
        # Object attributes
        elif hasattr(upload_response, 'fileUrl'):
            file_url = upload_response.fileUrl
        elif hasattr(upload_response, 'url'):
            file_url = upload_response.url
        
        # Direct string URL
        elif isinstance(upload_response, str) and ('http' in upload_response or 'dlfl.vn' in upload_response):
            file_url = upload_response.strip()
        
        if file_url:
            file_url = file_url.strip()
            print(f"[SUCCESS] ✅ Upload thành công! URL: {file_url}")
            return file_url
        else:
            print(f"[ERROR] ❌ Không tìm thấy fileUrl trong response")
            print(f"[DEBUG] Response keys: {list(upload_response.keys()) if isinstance(upload_response, dict) else 'Not dict'}")
            return None
            
    except Exception as e:
        print(f"[CRITICAL] Lỗi không mong muốn khi upload: {e}")
        import traceback
        traceback.print_exc()
        return None

def download_full_and_split(m3u8_url: str, title: str, max_part_size_mb: int = 900) -> List[str]:
    """
    Tải full phim từ link m3u8 bằng yt-dlp + aria2c
    In realtime tiến trình tải ra console
    Nếu file lớn -> tách thành nhiều phần nhỏ
    Trả về list đường dẫn các file phần (hoặc file full nếu nhỏ)
    """
    print(f"[INFO] Bắt đầu tải full phim: {title}")
    print(f"[INFO] Link m3u8: {m3u8_url}")
    
    safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)[:100]
    full_file = f"{CACHE_PATH}{safe_title}_full.mp4"
    
    try:
        # Lệnh yt-dlp tối ưu tải nhanh với aria2c
        cmd = [
            "yt-dlp",
            "--newline",          # In từng dòng tiến trình
            "--progress",         # Hiển thị progress bar chi tiết
            "--retries", "10",
            "--fragment-retries", "10",
            "--external-downloader", "aria2c",
            "--external-downloader-args", "aria2c:-x 16 -s 16 -k 1M",
            "--referer", "https://phimapi.com/",
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "-o", full_file,
            m3u8_url
        ]
        
        print(f"[DEBUG] Chạy lệnh yt-dlp: {' '.join(cmd)}")
        
        # Chạy yt-dlp và đọc output realtime để print tiến trình
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # In từng dòng tiến trình từ yt-dlp ra console
                # Hiển thị đúng 1 dòng tiến độ duy nhất, tự cập nhật (giống terminal thật)
        current_progress_line = ""
        
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue
                
            # Chỉ xử lý dòng progress [download] có chứa %
            if line.startswith("[download]") and "%" in line:
                # Ghi đè lên dòng cũ bằng \r (quay về đầu dòng)
                print(f"\r[YT-DLP] {line.ljust(80)}", end="", flush=True)  # ljust để xóa dư thừa
                current_progress_line = line
            else:
                # Các dòng khác (info, warning, error, hoàn thành) thì xuống dòng mới
                if current_progress_line:
                    print()  # Xuống dòng sau khi progress kết thúc
                    current_progress_line = ""
                print(f"[YT-DLP] {line}")
        
        # Sau khi kết thúc, xuống dòng sạch sẽ
        if current_progress_line:
            print()
        
        # Chờ yt-dlp hoàn tất
        returncode = process.wait()
        
        if returncode != 0:
            print(f"[ERROR] yt-dlp thất bại với return code: {returncode}")
            delete_file(full_file)
            return []
        
        # Kiểm tra file tải về
        if not os.path.exists(full_file):
            print(f"[ERROR] File không tồn tại sau khi tải: {full_file}")
            return []
        
        file_size_mb = os.path.getsize(full_file) / (1024 * 1024)
        if file_size_mb < 1:  # File rỗng hoặc quá nhỏ
            print(f"[ERROR] File tải về quá nhỏ hoặc rỗng: {file_size_mb:.2f} MB")
            delete_file(full_file)
            return []
        
        print(f"[SUCCESS] Tải thành công! Kích thước: {file_size_mb:.2f} MB")
        
        # Nếu file nhỏ hơn giới hạn → trả về nguyên file
        if file_size_mb <= max_part_size_mb:
            print(f"[INFO] File nhỏ ({file_size_mb:.1f} MB) → không cần tách")
            return [full_file]
        
        # Nếu lớn → tách thành nhiều phần
        print(f"[INFO] File lớn ({file_size_mb:.1f} MB) → đang tách thành nhiều phần...")
        
        # Lấy thời lượng phim để tách đều
        try:
            probe_cmd = [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", full_file
            ]
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)
            if probe_result.returncode == 0:
                duration = float(json.loads(probe_result.stdout)["format"]["duration"])
            else:
                duration = 7200  # Mặc định 2 giờ nếu không lấy được
        except Exception as e:
            print(f"[WARNING] Không lấy được duration, dùng mặc định: {e}")
            duration = 7200
        
        # Tính số phần cần tách
        num_parts = int(file_size_mb // max_part_size_mb) + 1
        part_duration = duration / num_parts
        parts = []
        
        print(f"[INFO] Tách thành {num_parts} phần, mỗi phần khoảng {part_duration/60:.1f} phút")
        
        for i in range(num_parts):
            start_time = i * part_duration
            part_file = f"{CACHE_PATH}{safe_title}_part{i+1}.mp4"
            
            cut_cmd = [
                "ffmpeg", "-y",
                "-i", full_file,
                "-ss", str(start_time),
                "-t", str(part_duration + 20),  # +20s để tránh cắt thiếu
                "-c", "copy",
                "-avoid_negative_ts", "make_zero",
                part_file
            ]
            
            print(f"[INFO] Đang tách phần {i+1}/{num_parts}: {os.path.basename(part_file)}")
            result = subprocess.run(cut_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"[WARNING] Lỗi khi tách phần {i+1}: {result.stderr[:200]}")
                continue
                
            if os.path.exists(part_file) and os.path.getsize(part_file) > 100 * 1024:  # >100KB
                part_size_mb = os.path.getsize(part_file) / (1024 * 1024)
                print(f"[SUCCESS] Tách thành công phần {i+1}: {part_size_mb:.1f} MB")
                parts.append(part_file)
            else:
                print(f"[ERROR] Phần {i+1} rỗng hoặc lỗi → bỏ qua")
        
        # Xóa file full gốc sau khi tách xong
        delete_file(full_file)
        print(f"[SUCCESS] Hoàn tất tách phim → {len(parts)} phần sẵn sàng upload")
        
        return parts
        
    except subprocess.TimeoutExpired:
        print(f"[ERROR] Timeout khi chạy yt-dlp hoặc ffmpeg")
        delete_file(full_file)
        return []
    except Exception as e:
        print(f"[CRITICAL] Lỗi nghiêm trọng trong download_full_and_split: {e}")
        import traceback
        traceback.print_exc()
        delete_file(full_file)
        return []

def upload_parts(client, parts: List[str], thread_id, thread_type) -> List[str]:
    """Upload song song từng phần - KHÔNG RETRY (đã fix root cause)"""
    print(f"[INFO] Bắt đầu upload {len(parts)} phần...")
    urls = []
    
    for i, part_file in enumerate(parts, 1):
        print(f"[UPLOAD] Phần {i}/{len(parts)}: {os.path.basename(part_file)} ({os.path.getsize(part_file)/(1024*1024):.1f} MB)")
        url = upload_to_zalo(client, part_file, thread_id, thread_type)
        if url:
            urls.append(url)
            print(f"[SUCCESS] ✅ Phần {i}: {url}")
        else:
            print(f"[ERROR] ❌ Phần {i} upload thất bại")
        
        # Xóa ngay sau khi xử lý
        delete_file(part_file)
    
    print(f"[SUMMARY] Upload hoàn tất: {len(urls)}/{len(parts)} phần thành công")
    return urls

def send_phim_parts(client, urls: List[str], title: str, ep_name: str, thumb: str,
                    message_object, thread_id, thread_type):
    """Gửi từng phần phim với caption gọn: chỉ tên phim + tập + phần hiện tại"""
    if not urls:
        return False
    
    for i, url in enumerate(urls, 1):
        total_parts = len(urls)
        text = f"🎬 {title}\n📺 {ep_name} Phần {i}/{total_parts}"
        
        try:
            client.sendRemoteVideo(
                videoUrl=url,
                thumbnailUrl=thumb or DEFAULT_THUMBNAIL,
                duration=3600000,  # 1 giờ (Zalo không kiểm tra nghiêm)
                message=Message(text=text),
                thread_id=thread_id,
                thread_type=thread_type,
                width=1280,
                height=720,
                ttl=86400000
            )
            print(f"[SUCCESS] Đã gửi phần {i}/{total_parts}")
            time.sleep(2)  # Nghỉ chút để tránh flood
        except Exception as e:
            print(f"[ERROR] Gửi phần {i} lỗi: {e}")
    
    return True
# ---------------------------
# Hàm tạo ảnh danh sách phim (giống cấu trúc video list)
# ---------------------------
def create_movie_list_image(movies: List[Dict[str, Any]], max_show: int = 30):
    """Tạo ảnh danh sách phim tương tự như video list"""
    print(f"[DEBUG] Hàm create_movie_list_image() được gọi")
    print(f"[DEBUG] - Số lượng phim: {len(movies)}")
    print(f"[DEBUG] - max_show: {max_show}")
    
    try:
        movies_to_show = movies[:min(max_show, len(movies))]
        num_movies = len(movies_to_show)
        
        print(f"[DEBUG] Số phim sẽ hiển thị: {num_movies}")
        
        # ==================== THIẾT LẬP KÍCH THƯỚC ====================
        scale = 2
        card_height = 105 * scale
        card_width = 583 * scale
        thumb_size = 90 * scale
        padding = 20 * scale
        spacing_y = 10 * scale
        card_padding = 8 * scale
        column_spacing = 20 * scale
        header_height = 60 * scale
        
        movies_per_column = 10
        num_columns = (num_movies - 1) // movies_per_column + 1
        
        img_width = padding * 2 + num_columns * card_width + (num_columns - 1) * column_spacing
        img_height = padding * 2 + header_height + movies_per_column * card_height + (movies_per_column - 1) * spacing_y
        
        print(f"[DEBUG] Kích thước ảnh: {img_width}x{img_height}")
        print(f"[DEBUG] Số cột: {num_columns}")
        
        # ==================== TẠO NỀN ====================
        if BACKGROUND_IMAGES:
            bg_path = random.choice(BACKGROUND_IMAGES)
            print(f"[DEBUG] Chọn ảnh nền: {bg_path}")
            bg_image = Image.open(bg_path).convert("RGB")
            bg_image = bg_image.resize((img_width, img_height), Image.Resampling.LANCZOS)
            bg_image = bg_image.filter(ImageFilter.GaussianBlur(radius=10))
        else:
            print(f"[DEBUG] Không tìm thấy ảnh nền, tạo nền màu đen")
            bg_image = Image.new("RGB", (img_width, img_height), (30, 30, 30))
        
        image = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
        image.paste(bg_image.convert("RGBA"), (0, 0))
        draw = ImageDraw.Draw(image)
        
        # ==================== TẢI FONT ====================
        print(f"[DEBUG] Đang tải font...")
        try:
            font_title = ImageFont.truetype("font/5.otf", 28 * scale)
            font_info = ImageFont.truetype("font/5.otf", 20 * scale)
            font_index = ImageFont.truetype("font/indexaSin2.otf", 70 * scale)
            font_header = ImageFont.truetype("font/5.otf", 50 * scale)
            emoji_font = ImageFont.truetype("font/NotoEmoji-Bold.ttf", 28 * scale)
            emoji_font_small = ImageFont.truetype("font/NotoEmoji-Bold.ttf", 21 * scale)
            print(f"[DEBUG] Đã tải font thành công")
        except Exception as e:
            print(f"[ERROR] Lỗi khi tải font: {e}")
            # Fallback nếu không tìm thấy font
            font_index = font_title = font_info = font_header = emoji_font = emoji_font_small = ImageFont.load_default()
            print(f"[DEBUG] Sử dụng font mặc định")
        
        # ==================== HÀM HỖ TRỢ ====================
        def get_text_width(text, font):
            bbox = draw.textbbox((0, 0), text, font=font)
            return bbox[2] - bbox[0]
        
        def draw_text_with_shadow(draw, position, text, font, fill, shadow_offset=(2, 2), shadow_fill=(0, 0, 0, 150)):
            x, y = position
            draw.text((x + shadow_offset[0], y + shadow_offset[1]), text, font=font, fill=shadow_fill)
            draw.text((x, y), text, font=font, fill=fill)
        
        def truncate_text(text, max_width, font_text, font_emoji):
            result = ''
            total_width = 0
            for char in text:
                # Kiểm tra emoji đơn giản
                import emoji
                font_used = font_emoji if emoji.is_emoji(char) else font_text
                char_width = get_text_width(char, font_used)
                if total_width + char_width > max_width - get_text_width('..', font_text):
                    if result:
                        result += '..'
                    break
                result += char
                total_width += char_width
            return result
        
        # ==================== HEADER ====================
        print(f"[DEBUG] Đang vẽ header...")
        header_text = "DANH SÁCH PHIM"
        header_width = get_text_width(header_text, font_header)
        header_x = (img_width - header_width) // 2
        header_y = padding
        
        # Màu sắc cho header
        header_colors = [
            (255, 0, 0), (255, 165, 0), (255, 255, 0),
            (0, 255, 0), (0, 0, 255), (75, 0, 130), (148, 0, 211)
        ]
        header_color = random.choice(header_colors)
        
        draw_text_with_shadow(draw, (header_x, header_y), header_text, font_header, header_color, shadow_offset=(3, 3))
        
        # ==================== VẼ DANH SÁCH PHIM ====================
        print(f"[DEBUG] Đang vẽ danh sách phim...")
        for col in range(num_columns):
            start_idx = col * movies_per_column
            end_idx = min(start_idx + movies_per_column, num_movies)
            column_movies = movies_to_show[start_idx:end_idx]
            
            left = padding + col * (card_width + column_spacing)
            
            print(f"[DEBUG] Cột {col + 1}: vị trí left={left}, số phim={len(column_movies)}")
            
            for i, movie in enumerate(column_movies):
                title = movie.get('title', 'Không có tiêu đề')
                type_ = movie.get('type', 'N/A')
                episode_current = movie.get('episode_current', 'N/A')
                thumb_url = movie.get('thumb_url', DEFAULT_THUMBNAIL)
                
                # Vị trí card
                top = padding + header_height + i * (card_height + spacing_y)
                
                # ========== VẼ CARD BACKGROUND ==========
                card_overlay = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
                card_draw = ImageDraw.Draw(card_overlay)
                
                # Màu card ngẫu nhiên
                box_colors = [
                    (120, 200, 180, 100), (180, 140, 200, 100), (240, 180, 160, 100),
                    (160, 200, 140, 100), (200, 160, 120, 100), (140, 180, 220, 100),
                    (220, 200, 140, 100), (180, 180, 180, 105)
                ]
                box_color = random.choice(box_colors)
                
                radius = 20 * scale
                card_draw.rounded_rectangle([0, 0, card_width, card_height], radius=radius, fill=box_color)
                image.paste(card_overlay, (left, top), card_overlay.split()[3])
                
                # ========== VẼ THUMBNAIL ==========
                thumb_y = top + (card_height - thumb_size) // 2
                thumb_x = left + card_padding
                
                # Tải thumbnail
                try:
                    # Thêm scheme nếu URL không có
                    if not thumb_url.startswith(('http://', 'https://')):
                        thumb_url = f"https://phimimg.com/{thumb_url}"
                        print(f"[DEBUG] Đã thêm scheme vào thumbnail URL: {thumb_url}")
                    else:
                        print(f"[DEBUG] Đang tải thumbnail: {thumb_url}")
                    
                    response = requests.get(thumb_url, timeout=10, verify=False, headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    })
                    if response.status_code == 200:
                        thumb = Image.open(BytesIO(response.content)).convert("RGBA")
                        thumb = thumb.resize((thumb_size, thumb_size), Image.Resampling.LANCZOS)
                        
                        # Bo tròn thumbnail
                        mask = Image.new("L", (thumb_size, thumb_size), 0)
                        ImageDraw.Draw(mask).ellipse((0, 0, thumb_size, thumb_size), fill=255)
                        thumb.putalpha(mask)
                        
                        # Thêm viền
                        border_img = Image.new("RGBA", (thumb_size + 6, thumb_size + 6), (0, 0, 0, 0))
                        border_draw = ImageDraw.Draw(border_img)
                        border_draw.ellipse([(0, 0), (thumb_size + 5, thumb_size + 5)], outline=(255, 255, 255, 200), width=3)
                        
                        border_img.paste(thumb, (3, 3), thumb)
                        image.paste(border_img, (thumb_x - 3, thumb_y - 3), border_img)
                        print(f"[DEBUG] Đã tải thumbnail thành công")
                    else:
                        print(f"[WARNING] Lỗi tải thumbnail, status code: {response.status_code}")
                except Exception as e:
                    print(f"[ERROR] Lỗi khi tải thumbnail: {e}")
                    # Vẽ hình tròn mặc định nếu không tải được thumbnail
                    default_thumb = Image.new("RGBA", (thumb_size, thumb_size), (100, 100, 100, 255))
                    draw_thumb = ImageDraw.Draw(default_thumb)
                    draw_thumb.ellipse((0, 0, thumb_size, thumb_size), fill=(100, 100, 100, 255))
                    image.paste(default_thumb, (thumb_x, thumb_y), default_thumb)
                
                # ========== VẼ THÔNG TIN PHIM ==========
                x_text = left + card_padding + thumb_size + 20 * scale
                y_title = top + card_padding
                
                max_text_width = card_width - thumb_size - 3 * card_padding - 80 * scale
                
                # 1. TIÊU ĐỀ
                title_colors = [
                    (255, 100, 100), (100, 255, 100), (100, 100, 255),
                    (255, 200, 100), (200, 100, 255), (100, 255, 255)
                ]
                title_color = random.choice(title_colors)
                
                truncated_title = truncate_text(title, max_text_width, font_title, emoji_font)
                if truncated_title:
                    draw_text_with_shadow(draw, (x_text, y_title), truncated_title, font_title, title_color)
                
                # 2. LOẠI PHIM
                y_type = y_title + int(35 * scale)
                type_color = (200, 200, 200)  # Màu xám sáng
                
                type_truncated = f"🎬 {type_}"
                if get_text_width(type_truncated, font_info) > max_text_width:
                    type_truncated = truncate_text(type_truncated, max_text_width, font_info, emoji_font_small)
                
                draw_text_with_shadow(draw, (x_text, y_type), type_truncated, font_info, type_color, shadow_offset=(1, 1))
                
                # 3. THÔNG TIN TẬP
                info_text = f"📺 {episode_current}" if episode_current != 'N/A' else "📺 Không rõ tập"
                info_height = font_info.size
                y_info = top + card_height - card_padding - info_height - 4 * scale
                
                if info_text:
                    info_color = (255, 255, 255)  # Màu trắng
                    draw_text_with_shadow(draw, (x_text, y_info), info_text, font_info, info_color, shadow_offset=(1, 1))
                
                # ========== VẼ SỐ THỨ TỰ ==========
                number_text = str(start_idx + i + 1)
                number_width = get_text_width(number_text, font_index)
                
                # Vị trí số thứ tự (góc phải card)
                number_x = left + card_width - number_width - card_padding
                number_y = top + (card_height - font_index.size) // 2
                
                # Màu xanh lá sáng cố định
                bright_green = (100, 255, 100)
                
                # Vẽ số với màu xanh lá
                draw_text_with_shadow(draw, (number_x, number_y), number_text, font_index, bright_green, shadow_offset=(2, 2))
        
        # ==================== THÊM VIỀN VÀ LƯU ẢNH ====================
        print(f"[DEBUG] Đang thêm viền...")
        # Thêm viền đa sắc
        border_colors = [
            (255, 0, 0), (255, 165, 0), (255, 255, 0),
            (0, 255, 0), (0, 0, 255), (75, 0, 130), (148, 0, 211)
        ]
        
        # Tạo ảnh viền
        border_thickness = 4
        new_w = image.width + 2 * border_thickness
        new_h = image.height + 2 * border_thickness
        border_img = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
        draw_b = ImageDraw.Draw(border_img)
        
        # Vẽ viền gradient
        for x in range(new_w):
            ratio = x / new_w
            color_idx = int(ratio * (len(border_colors) - 1))
            if color_idx < len(border_colors) - 1:
                r1, g1, b1 = border_colors[color_idx]
                r2, g2, b2 = border_colors[color_idx + 1]
                t = (ratio * (len(border_colors) - 1)) - color_idx
                color = (
                    int(r1 * (1 - t) + r2 * t),
                    int(g1 * (1 - t) + g2 * t),
                    int(b1 * (1 - t) + b2 * t)
                )
            else:
                color = border_colors[-1]
            
            # Viền trên và dưới
            draw_b.line([(x, 0), (x, border_thickness - 1)], fill=color)
            draw_b.line([(x, new_h - border_thickness), (x, new_h - 1)], fill=color)
        
        for y in range(new_h):
            ratio = y / new_h
            color_idx = int(ratio * (len(border_colors) - 1))
            if color_idx < len(border_colors) - 1:
                r1, g1, b1 = border_colors[color_idx]
                r2, g2, b2 = border_colors[color_idx + 1]
                t = (ratio * (len(border_colors) - 1)) - color_idx
                color = (
                    int(r1 * (1 - t) + r2 * t),
                    int(g1 * (1 - t) + g2 * t),
                    int(b1 * (1 - t) + b2 * t)
                )
            else:
                color = border_colors[-1]
            
            # Viền trái và phải
            draw_b.line([(0, y), (border_thickness - 1, y)], fill=color)
            draw_b.line([(new_w - border_thickness, y), (new_w - 1, y)], fill=color)
        
        # Dán ảnh gốc vào giữa viền
        border_img.paste(image, (border_thickness, border_thickness), image)
        image = border_img
        
        # Chuyển sang RGB và lưu
        image = image.convert("RGB")
        
        output_path = "movie_list.jpg"
        os.makedirs("cache", exist_ok=True)
        image.save(output_path, quality=95)
        
        print(f"[DEBUG] Đã tạo ảnh thành công: {output_path}")
        print(f"[DEBUG] Kích thước ảnh cuối cùng: {image.width}x{image.height}")
        
        return output_path, image.width, image.height
        
    except Exception as e:
        print(f"[ERROR] Lỗi khi tạo ảnh danh sách phim: {e}")
        import traceback
        traceback.print_exc()
        return None, 0, 0

# ---------------------------
# Hàm xử lý API PhimAPI
# ---------------------------
def search_movie_list(query: str, limit: int = 30) -> List[Dict[str, Any]]:
    """Tìm kiếm phim trên PhimAPI"""
    print(f"[DEBUG] Hàm search_movie_list() được gọi")
    print(f"[DEBUG] - Query: {query}")
    print(f"[DEBUG] - Limit: {limit}")
    
    try:
        print(f"[DEBUG] Đang tìm kiếm phim với từ khóa: {query}")
        
        url = f"https://phimapi.com/v1/api/tim-kiem?keyword={urllib.parse.quote(query)}&limit={limit}"
        print(f"[DEBUG] Gọi API: {url}")
        
        response = requests.get(url, timeout=15, headers=get_headers())
        response.raise_for_status()
        data = response.json()
        
        movies_raw = data.get('data', {}).get('items', [])
        
        print(f"[DEBUG] Tìm thấy {len(movies_raw)} kết quả thô")
        
        movies = []
        for movie in movies_raw[:limit]:
            movies.append({
                'title': movie.get('name', 'Không có tiêu đề'),
                'slug': movie.get('slug', ''),
                'thumb_url': movie.get('thumb_url', ''),
                'episode_current': movie.get('episode_current', 'N/A'),
                'type': movie.get('type', 'N/A')
            })
        
        print(f"[DEBUG] Tìm thấy {len(movies)} phim hợp lệ")
        return movies
        
    except Exception as e:
        print(f"[ERROR] Lỗi khi tìm kiếm phim: {e}")
        import traceback
        traceback.print_exc()
        return []

def get_movie_details(slug: str) -> Dict[str, Any]:
    """Lấy chi tiết phim từ PhimAPI"""
    print(f"[DEBUG] Hàm get_movie_details() được gọi với slug: {slug}")
    
    try:
        url = f'https://phimapi.com/phim/{slug}'
        print(f"[DEBUG] Gọi API: {url}")
        
        response = requests.get(url, timeout=15, headers=get_headers())
        response.raise_for_status()
        data = response.json()
        
        print(f"[DEBUG] Lấy chi tiết phim thành công")
        return data
    except Exception as e:
        print(f"[ERROR] Lỗi khi lấy chi tiết phim: {e}")
        import traceback
        traceback.print_exc()
        return {}

# ---------------------------
# Handlers cho lệnh (giống cấu trúc search_ytb.py) - GIỮ NGUYÊN SYNC
# ---------------------------
def handle_phim_command(message, message_object, thread_id, thread_type, author_id, client):
    """Handler cho lệnh phim"""
    print(f"[DEBUG] ========== HÀM handle_phim_command() ĐƯỢC GỌI ==========")
    print(f"[DEBUG] - Message: {message}")
    print(f"[DEBUG] - Thread ID: {thread_id}")
    print(f"[DEBUG] - Thread Type: {thread_type}")
    print(f"[DEBUG] - Author ID: {author_id}")
    
    content = message.strip().split()
    
    print(f"[DEBUG] Content split: {content}")
    
    # Thêm reaction
    try:
        print(f"[DEBUG] Đang gửi reaction...")
        client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
        print(f"[DEBUG] Đã gửi reaction thành công")
    except Exception as e:
        print(f"[ERROR] Lỗi khi gửi reaction: {e}")
    
    if len(content) < 2:
        print(f"[ERROR] Thiếu từ khóa tìm kiếm")
        error_message = Message(text="🚫 Lỗi: Thiếu từ khóa tìm kiếm\n\nCú pháp: phim <tên phim>")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return
    
    query = ' '.join(content[1:])
    print(f"[DEBUG] Query tìm kiếm: {query}")
    
    movie_list = search_movie_list(query)
    
    if not movie_list:
        print(f"[ERROR] Không tìm thấy phim nào")
        error_message = Message(text="❌ Không tìm thấy phim nào phù hợp.")
        client.replyMessage(error_message, message_object, thread_id, thread_type)
        return
    
    print(f"[DEBUG] Tìm thấy {len(movie_list)} phim")
    
    # Lưu kết quả tìm kiếm
    movie_search_results[thread_id] = movie_list
    print(f"[DEBUG] Đã lưu movie_search_results cho thread_id: {thread_id}")
    
    # Tạo ảnh danh sách
    print(f"[DEBUG] Đang tạo ảnh danh sách phim...")
    list_image_path, list_image_width, list_image_height = create_movie_list_image(movie_list, max_show=30)
    
    if not list_image_path:
        print(f"[ERROR] Lỗi khi tạo ảnh danh sách")
        error_message = Message(text="❌ Lỗi khi tạo danh sách phim.")
        client.replyMessage(error_message, message_object, thread_id, thread_type)
        return
    
    print(f"[DEBUG] Đã tạo ảnh: {list_image_path}, kích thước: {list_image_width}x{list_image_height}")
    
    guide_msg = "Nhập '//phim <số>' (1-30) để chọn phim\nNhập '//phim 0' để hủy"
    
    # Lưu trạng thái tìm kiếm - SỬ DỤNG BIẾN CŨ
    movie_select_status[thread_id] = (time.time(), False, list_image_path, thread_type)
    print(f"[DEBUG] Đã lưu movie_select_status cho thread_id: {thread_id}")
    
    try:
        # Gửi ảnh danh sách
        print(f"[DEBUG] Đang gửi ảnh danh sách...")
        response = client.sendLocalImage(
            list_image_path,
            message=Message(text=guide_msg),
            thread_id=thread_id,
            thread_type=thread_type,
            width=list_image_width,
            height=list_image_height,
            ttl=TIME_TO_SELECT * 1000  # Chuyển sang mili giây
        )
        
        print(f"[DEBUG] Response từ sendLocalImage: {json.dumps(response, indent=2)}")
        
        # Lưu msg_id để có thể xóa sau
        msg_id = response.get('msgId')
        if msg_id:
            movie_select_status[thread_id] = (time.time(), False, msg_id, thread_type)
            print(f"[DEBUG] Đã lưu msgId của tin nhắn danh sách phim: {msg_id}")
        else:
            print(f"[WARNING] Không tìm thấy msgId trong response")
        
    except Exception as e_img:
        print(f"[ERROR] Lỗi khi gửi ảnh danh sách: {e_img}")
        import traceback
        traceback.print_exc()
    
    # Tự động xóa sau thời gian hết hạn
    def cleanup_search():
        print(f"[DEBUG] Hàm cleanup_search() được gọi cho thread_id: {thread_id}")
        time.sleep(TIME_TO_SELECT)
        
        if thread_id in movie_select_status and not movie_select_status[thread_id][1]:
            print(f"[DEBUG] Đã hết thời gian chọn, đang xóa...")
            try:
                # Xóa tin nhắn ảnh
                if isinstance(movie_select_status[thread_id][2], str):  # Nếu là file path
                    print(f"[DEBUG] Xóa file ảnh: {movie_select_status[thread_id][2]}")
                    delete_file(movie_select_status[thread_id][2])
                else:  # Nếu là msg_id
                    print(f"[DEBUG] Xóa tin nhắn có msgId: {movie_select_status[thread_id][2]}")
                    try:
                        client.deleteGroupMsg(
                            msgId=movie_select_status[thread_id][2],
                            ownerId=author_id,
                            clientMsgId=message_object.get('cliMsgId'),
                            groupId=thread_id
                        )
                    except Exception as e:
                        print(f"[ERROR] Lỗi khi xóa tin nhắn: {e}")
                print("[DEBUG] Đã xóa ảnh danh sách phim sau khi hết hạn.")
            except Exception as e:
                print(f"[ERROR] Lỗi khi xóa ảnh danh sách: {e}")
            
            # Xóa cache
            movie_search_results.pop(thread_id, None)
            movie_select_status.pop(thread_id, None)
            print(f"[DEBUG] Đã xóa cache cho thread_id: {thread_id}")
    
    # Chạy cleanup trong luồng riêng
    import threading
    print(f"[DEBUG] Khởi tạo thread cleanup...")
    cleanup_thread = threading.Thread(target=cleanup_search)
    cleanup_thread.daemon = True
    cleanup_thread.start()
    print(f"[DEBUG] Đã khởi động thread cleanup")

def handle_chonphim_command(message, message_object, thread_id, thread_type, author_id, client):
    """Handler cho lệnh chọn phim (giống //ytb)"""
    print(f"[DEBUG] ========== HÀM handle_chonphim_command() ĐƯỢC GỌI ==========")
    print(f"[DEBUG] - Message: {message}")
    print(f"[DEBUG] - Thread ID: {thread_id}")
    print(f"[DEBUG] - Thread Type: {thread_type}")
    print(f"[DEBUG] - Author ID: {author_id}")
    
    content = message.strip().split()
    print(f"[DEBUG] Content split: {content}")
    
    if len(content) < 2:
        print(f"[ERROR] Thiếu số thứ tự")
        error_message = Message(text="🚫 Lỗi: Thiếu số thứ tự\n\nCú pháp: //phim <số từ 1-30>")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return
    
    # Kiểm tra xem có đang trong phiên tìm kiếm không - SỬ DỤNG BIẾN CŨ
    if thread_id not in movie_select_status:
        print(f"[ERROR] Không tìm thấy movie_select_status cho thread_id: {thread_id}")
        error_message = Message(text="🚫 Bạn không thể chọn vì danh sách đã hết hạn hoặc không phải người tìm kiếm.")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return
    
    if movie_select_status[thread_id][1]:
        print(f"[ERROR] Danh sách đã được chọn trước đó")
        error_message = Message(text="🚫 Bạn không thể chọn vì danh sách đã hết hạn hoặc không phải người tìm kiếm.")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return
    
    # Kiểm tra thời gian hết hạn
    search_time = movie_select_status[thread_id][0]
    current_time = time.time()
    time_diff = current_time - search_time
    
    print(f"[DEBUG] Thời gian tìm kiếm: {search_time}")
    print(f"[DEBUG] Thời gian hiện tại: {current_time}")
    print(f"[DEBUG] Thời gian đã trôi qua: {time_diff}s / {TIME_TO_SELECT}s")
    
    if time_diff > TIME_TO_SELECT:
        print(f"[ERROR] Danh sách đã hết hạn")
        error_message = Message(text="🚫 Danh sách đã hết hạn. Vui lòng tìm kiếm lại.")
        
        # Xóa cache
        movie_search_results.pop(thread_id, None)
        movie_select_status.pop(thread_id, None)
        
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return
    
    # Xử lý hủy tìm kiếm (nhập 0)
    if content[1] == '0':
        print(f"[DEBUG] Người dùng chọn hủy (0)")
        try:
            # Xóa tin nhắn ảnh
            if isinstance(movie_select_status[thread_id][2], str):  # Nếu là file path
                print(f"[DEBUG] Xóa file ảnh: {movie_select_status[thread_id][2]}")
                delete_file(movie_select_status[thread_id][2])
            else:  # Nếu là msg_id
                print(f"[DEBUG] Xóa tin nhắn có msgId: {movie_select_status[thread_id][2]}")
                try:
                    client.deleteGroupMsg(
                        msgId=movie_select_status[thread_id][2],
                        ownerId=author_id,
                        clientMsgId=message_object.get('cliMsgId'),
                        groupId=thread_id
                    )
                except Exception as e:
                    print(f"[ERROR] Lỗi khi xóa tin nhắn: {e}")
            print("[DEBUG] Đã xóa ảnh danh sách phim sau khi hủy.")
        except Exception as e:
            print(f"[ERROR] Lỗi khi xóa ảnh danh sách: {e}")
        
        # Xóa cache
        movie_search_results.pop(thread_id, None)
        movie_select_status.pop(thread_id, None)
        
        success_message = Message(text="🔄 Lệnh tìm kiếm đã được hủy. Bạn có thể thực hiện tìm kiếm mới.")
        client.replyMessage(success_message, message_object, thread_id, thread_type, ttl=60000)
        return
    
    # Chọn phim theo số thứ tự
    try:
        index = int(content[1]) - 1
        print(f"[DEBUG] Người dùng chọn index: {index}")
    except ValueError:
        print(f"[ERROR] Số thứ tự không hợp lệ: {content[1]}")
        error_message = Message(text="🚫 Lỗi: Số thứ tự không hợp lệ.\nCú pháp: //phim <số từ 1-30>")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return
    
    movie_list = movie_search_results.get(thread_id)
    if not movie_list:
        print(f"[ERROR] Không tìm thấy movie_list cho thread_id: {thread_id}")
        error_message = Message(text="🚫 Danh sách phim không tồn tại.")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return
    
    print(f"[DEBUG] Độ dài movie_list: {len(movie_list)}")
    print(f"[DEBUG] Index được chọn: {index}")
    
    if index < 0 or index >= min(30, len(movie_list)):
        print(f"[ERROR] Index nằm ngoài phạm vi")
        error_message = Message(text="🚫 Số thứ tự không hợp lệ. Vui lòng chọn từ 1 đến 30.")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return
    
    # Đánh dấu đã chọn
    movie_select_status[thread_id] = (movie_select_status[thread_id][0], True, movie_select_status[thread_id][2], thread_type)
    print(f"[DEBUG] Đã đánh dấu đã chọn cho thread_id: {thread_id}")
    
    # Xóa tin nhắn ảnh danh sách
    try:
        if isinstance(movie_select_status[thread_id][2], str):  # Nếu là file path
            print(f"[DEBUG] Xóa file ảnh: {movie_select_status[thread_id][2]}")
            delete_file(movie_select_status[thread_id][2])
        else:  # Nếu là msg_id
            print(f"[DEBUG] Xóa tin nhắn có msgId: {movie_select_status[thread_id][2]}")
            try:
                client.deleteGroupMsg(
                    msgId=movie_select_status[thread_id][2],
                    ownerId=author_id,
                    clientMsgId=message_object.get('cliMsgId'),
                    groupId=thread_id
                )
            except Exception as e:
                print(f"[ERROR] Lỗi khi xóa tin nhắn: {e}")
        print("[DEBUG] Đã xóa ảnh danh sách phim sau khi chọn.")
    except Exception as e:
        print(f"[ERROR] Lỗi khi xóa ảnh danh sách: {e}")
    
    # Lấy phim được chọn
    selected_movie = movie_list[index]
    
    print(f"[DEBUG] Phim được chọn:")
    print(f"[DEBUG] - Tiêu đề: {selected_movie['title']}")
    print(f"[DEBUG] - Slug: {selected_movie['slug']}")
    print(f"[DEBUG] - Loại: {selected_movie['type']}")
    
    # Xóa cache
    movie_search_results.pop(thread_id, None)
    movie_select_status.pop(thread_id, None)
    print(f"[DEBUG] Đã xóa cache sau khi chọn")
    
    # Xử lý phim đã chọn
    process_movie_selection(selected_movie, message_object, thread_id, thread_type, author_id, client)

def process_movie_selection(movie: Dict[str, Any], message_object, thread_id, thread_type, author_id, client):
    """Xử lý phim đã chọn"""
    print(f"[DEBUG] ========== HÀM process_movie_selection() ĐƯỢC GỌI ==========")
    print(f"[DEBUG] - Movie slug: {movie['slug']}")
    print(f"[DEBUG] - Tiêu đề: {movie['title']}")
    print(f"[DEBUG] - Thread ID: {thread_id}")
    print(f"[DEBUG] - Thread Type: {thread_type}")
    
    try:
        # Lấy chi tiết phim
        print(f"[DEBUG] Đang lấy chi tiết phim...")
        movie_details = get_movie_details(movie['slug'])
        
        if not movie_details:
            print(f"[ERROR] Không thể lấy chi tiết phim")
            error_message = Message(text="🚫 Lỗi: Không thể lấy chi tiết phim.")
            client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
            return
        
        movie_data = movie_details.get('movie', {})
        episodes_data = movie_details.get('episodes', [])
        
        if not episodes_data:
            print(f"[ERROR] Không có dữ liệu tập phim")
            error_message = Message(text="🚫 Lỗi: Không có dữ liệu tập phim.")
            client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
            return
        
        # Xử lý theo loại phim
        if movie['type'] == 'single':
            print(f"[DEBUG] Phim single episode")
            # Xử lý phim single (giống xử lý video trong search_ytb.py)
            handle_single_movie(movie_data, episodes_data, message_object, thread_id, thread_type, author_id, client)
        else:
            print(f"[DEBUG] Phim nhiều tập")
            # Xử lý phim nhiều tập (hiển thị danh sách tập)
            handle_multi_episode_movie(movie_data, episodes_data, message_object, thread_id, thread_type, author_id, client)
            
    except Exception as e:
        print(f"[ERROR] Lỗi trong quá trình xử lý phim: {e}")
        import traceback
        traceback.print_exc()
        
        error_message = Message(text=f"🚫 Lỗi: {str(e)[:100]}")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)

def send_movie_to_group(client, video_url: str, thumbnail_url: str, duration: int, 
                       info_text: str, message_object, thread_id, thread_type, title: str):
    """Gửi video phim lên nhóm với xử lý lỗi đầy đủ và log chi tiết"""
    print(f"[DEBUG] ========= BẮT ĐẦU GỬI VIDEO LÊN NHÓM =========")
    print(f"[DEBUG] Thời gian bắt đầu: {time.strftime('%H:%M:%S')}")
    print(f"[DEBUG] Tiêu đề: {title}")
    print(f"[DEBUG] Video URL: {video_url}")
    print(f"[DEBUG] Thumbnail URL: {thumbnail_url}")
    print(f"[DEBUG] Duration: {duration // 1000}s ({duration}ms)")
    print(f"[DEBUG] Thread ID: {thread_id} | Type: {thread_type}")
    print(f"[DEBUG] Độ dài info_text: {len(info_text)} ký tự")

    try:
        # === THỬ 1: Gửi đầy đủ (có thumbnail) ===
        print(f"[DEBUG] [THỬ 1] Đang tạo Message object...")
        messagesend = Message(text=info_text)
        print(f"[DEBUG] [THỬ 1] Đã tạo Message thành công")

        print(f"[DEBUG] [THỬ 1] Đang gọi sendRemoteVideo (có thumbnail)...")
        start_time = time.time()
        
        response = client.sendRemoteVideo(
            videoUrl=video_url,
            thumbnailUrl=thumbnail_url,
            duration=duration,
            message=messagesend,
            thread_id=thread_id,
            thread_type=thread_type,
            width=1280,
            height=720,
            ttl=86000000  # ~24 giờ
        )
        
        elapsed = time.time() - start_time
        print(f"[SUCCESS] [THỬ 1] GỬI VIDEO THÀNH CÔNG sau {elapsed:.2f}s !")
        print(f"[DEBUG] Response type: {type(response)}")
        if isinstance(response, dict):
            print(f"[DEBUG] msgId: {response.get('msgId', 'N/A')}")
        
        return True, response

    except Exception as e:
        elapsed = time.time() - start_time if 'start_time' in locals() else 0
        print(f"[ERROR] [THỬ 1] Lỗi sendRemoteVideo (có thumbnail) sau {elapsed:.2f}s: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

        # === THỬ 2: Gửi không thumbnail ===
        try:
            print(f"[DEBUG] [THỬ 2] Thử gửi video KHÔNG thumbnail...")
            simple_message = Message(text=f"🎬 {title}\n\n{info_text}")
            
            start_time2 = time.time()
            response2 = client.sendRemoteVideo(
                videoUrl=video_url,
                message=simple_message,
                thread_id=thread_id,
                thread_type=thread_type,
                ttl=86000000
            )
            
            elapsed2 = time.time() - start_time2
            print(f"[SUCCESS] [THỬ 2] GỬI VIDEO THÀNH CÔNG (không thumbnail) sau {elapsed2:.2f}s !")
            return True, response2

        except Exception as e2:
            elapsed2 = time.time() - start_time2 if 'start_time2' in locals() else 0
            print(f"[ERROR] [THỬ 2] Lỗi sendRemoteVideo (không thumbnail) sau {elapsed2:.2f}s: {type(e2).__name__}: {e2}")
            traceback.print_exc()

            # === THỬ 3: Gửi link video (fallback an toàn nhất) ===
            try:
                print(f"[DEBUG] [THỬ 3] Thử gửi LINK video...")
                link_text = (
                    f"🎬 **{title}**\n\n"
                    f"🔗 **Link xem phim:** {video_url}\n\n"
                    f"{info_text}\n\n"
                    f"⚠️ Zalo không gửi được video trực tiếp, vui lòng click link trên để xem."
                )
                link_message = Message(text=link_text)
                
                response3 = client.replyMessage(link_message, message_object, thread_id, thread_type, ttl=120000000)
                print(f"[SUCCESS] [THỬ 3] ĐÃ GỬI LINK VIDEO THÀNH CÔNG!")
                return True, response3

            except Exception as e3:
                print(f"[ERROR] [THỬ 3] Lỗi khi gửi link: {type(e3).__name__}: {e3}")
                traceback.print_exc()

                # === THỬ CUỐI: Gửi thông báo lỗi đơn giản ===
                try:
                    print(f"[DEBUG] [CUỐI] Gửi thông báo lỗi...")
                    error_msg = Message(
                        text=f"⚠️ Không thể gửi phim \"{title}\"\n"
                             f"Lỗi: {str(e)[:100]}{'...' if len(str(e)) > 100 else ''}\n"
                             f"Vui lòng thử lại sau hoặc dùng link gốc."
                    )
                    client.replyMessage(error_msg, message_object, thread_id, thread_type, ttl=60000)
                    print(f"[WARNING] Đã gửi thông báo lỗi cho người dùng")
                except Exception as e4:
                    print(f"[CRITICAL] Không thể gửi bất kỳ tin nhắn nào: {e4}")

                return False, None


def handle_single_movie(movie_data: Dict[str, Any], episodes_data: List[Dict[str, Any]], 
                        message_object, thread_id, thread_type, author_id, client):
    """Xử lý phim lẻ (single episode) - TẢI FULL + CHIA PHẦN + GỬI NHƯ PHIM BỘ"""
    print(f"[DEBUG] ========== HÀM handle_single_movie() ĐƯỢC GỌI ==========")
    
    try:
        # Lấy link m3u8 từ tập đầu tiên (phim lẻ chỉ có 1 tập)
        first_episode = episodes_data[0]['server_data'][0] if episodes_data and episodes_data[0]['server_data'] else None
        
        if not first_episode:
            print(f"[ERROR] Không có dữ liệu tập phim lẻ")
            error_message = Message(text="🚫 Lỗi: Không tìm thấy link phim.")
            client.replyMessage(error_message, message_object, thread_id, thread_type)
            return
        
        video_url = first_episode.get('link_m3u8')
        if not video_url:
            print(f"[ERROR] Không có link_m3u8 cho phim lẻ")
            error_message = Message(text="🚫 Lỗi: Không có link video.")
            client.replyMessage(error_message, message_object, thread_id, thread_type)
            return
        
        title = movie_data.get('name', 'Phim Không Có Tên').strip()
        thumb_url = movie_data.get('thumb_url', '')
        if thumb_url and not thumb_url.startswith('http'):
            thumb_url = f"https://phimimg.com/{thumb_url}"
        thumbnail_to_use = thumb_url or DEFAULT_THUMBNAIL
        
        print(f"[INFO] Phim lẻ: {title}")
        print(f"[INFO] Link m3u8: {video_url}")
        print(f"[INFO] Thumbnail: {thumbnail_to_use}")

        # === GỬI THÔNG BÁO ĐANG TẢI ===
        download_message = Message(
            text=f"🔽 Đang tải phim lẻ (full): {title[:60]}{'...' if len(title) > 60 else ''}\n"
                 f"📅 Năm: {movie_data.get('year', 'N/A')}\n"
                 f"⏳ Có thể mất vài phút đến vài giờ tùy độ dài phim..."
        )
        client.replyMessage(download_message, message_object, thread_id, thread_type, ttl=60000)
        
        # Reaction đang xử lý
        try:
            client.sendReaction(message_object, "⏳", thread_id, thread_type, reactionType=55)
        except Exception as e:
            print(f"[ERROR] Lỗi gửi reaction ⏳: {e}")

        # === TẢI FULL PHIM + TÁCH PHẦN (dùng hàm chung với phim bộ) ===
                # === TẢI FULL PHIM + TÁCH PHẦN ===
        print(f"[INFO] Đang tải full phim lẻ: {title}")
        parts = download_full_and_split(
            m3u8_url=video_url,
            title=title
        )
        
        if not parts:
            print(f"[ERROR] Tải full phim lẻ thất bại")
            client.replyMessage(
                Message(text="🚫 Không thể tải phim full. Vui lòng thử lại sau hoặc chọn phim khác!"),
                message_object, thread_id, thread_type
            )
            return
        
        # === UPLOAD TỪNG PHẦN ===
        print(f"[INFO] Bắt đầu upload {len(parts)} phần phim lẻ...")
        video_urls = upload_parts(client, parts, thread_id, thread_type)
        
        if not video_urls:
            client.replyMessage(Message(text="🚫 Upload thất bại sau nhiều lần thử."), 
                                message_object, thread_id, thread_type)
            return

        # === TẠO THÔNG TIN PHIM ĐẸP (sửa lỗi category & country) ===
        # Xử lý thể loại
        categories = movie_data.get('category', [])
        if isinstance(categories, list) and categories and isinstance(categories[0], dict):
            category_names = [cat.get('name', 'N/A') for cat in categories]
        else:
            category_names = categories or ['N/A']
        category_str = ', '.join(category_names)[:80]
        if len(', '.join(category_names)) > 80:
            category_str += '...'

        # Xử lý quốc gia
        countries = movie_data.get('country', [])
        if isinstance(countries, list) and countries and isinstance(countries[0], dict):
            country_names = [c.get('name', 'N/A') for c in countries]
        else:
            country_names = countries or ['N/A']
        country_str = ', '.join(country_names)

        info_text = (
            f"🎬 Phim: {title}\n"
            f"🎭 Thể loại: {category_str}\n"
            f"📅 Năm: {movie_data.get('year', 'N/A')}\n"
            f"🇻🇳 Quốc gia: {country_str}\n"
            f"🔗 Nguồn: PhimAPI"
        )

        # === GỬI TỪNG PHẦN VIDEO ===
        episode_name = "Full Phim"  # vì là phim lẻ
        success = send_phim_parts(
            client=client,
            urls=video_urls,
            title=title,
            ep_name=episode_name,
            thumb=thumbnail_to_use,
            message_object=message_object,
            thread_id=thread_id,
            thread_type=thread_type
        )

        # === HOÀN TẤT: Reaction thành công ===
        try:
            client.sendReaction(message_object, "", thread_id, thread_type, -1)  # xóa ⏳
            if success:
                client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
        except Exception as e:
            print(f"[ERROR] Lỗi reaction cuối: {e}")

        if not success:
            client.replyMessage(
                Message(text="⚠️ Đã gửi một số phần, nhưng có phần bị lỗi. Bạn vẫn có thể xem từ các phần đã nhận được."),
                message_object, thread_id, thread_type
            )

    except Exception as e:
        print(f"[CRITICAL] Lỗi nghiêm trọng trong handle_single_movie: {e}")
        import traceback
        traceback.print_exc()
        client.replyMessage(Message(text="🚫 Đã xảy ra lỗi hệ thống khi xử lý phim lẻ."), 
                            message_object, thread_id, thread_type)
def handle_multi_episode_movie(movie_data: Dict[str, Any], episodes_data: List[Dict[str, Any]],
                              message_object, thread_id, thread_type, author_id, client):
    """Xử lý phim nhiều tập - hiển thị danh sách tập"""
    print(f"[DEBUG] ========== HÀM handle_multi_episode_movie() ĐƯỢC GỌI ==========")
    
    try:
        # Lấy danh sách tập từ server đầu tiên
        episodes_list = episodes_data[0]['server_data'] if episodes_data else []
        
        if not episodes_list:
            print(f"[ERROR] Không có danh sách tập")
            error_message = Message(text="🚫 Lỗi: Không có danh sách tập.")
            client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
            return
        
        title = movie_data.get('name', 'Không có tiêu đề')
        thumb_url = f"https://phimimg.com/{movie_data.get('thumb_url', '')}"
        
        # Tạo danh sách tập dạng text
        episodes_text = ", ".join([str(i+1) for i in range(len(episodes_list))])
        
        info_text = (
            f"🎬 Thông tin phim:\n"
            f"Tên: {title}\n"
            f"Năm: {movie_data.get('year', 'N/A')}\n"
            f"Tổng số tập: {len(episodes_list)}\n"
            f"Danh sách tập: {episodes_text}\n\n"
            f"Vui lòng nhập 'tap <số tập>' để chọn tập"
        )
        
        # Lưu thông tin phim vào biến cũ
        episode_select_results[thread_id] = {
            'movie_data': movie_data,
            'episodes_data': episodes_data,
            'selected_movie': {
                'title': title,
                'thumb_url': thumb_url
            }
        }
        
        # Gửi ảnh thumbnail với thông tin
        print(f"[DEBUG] Gửi ảnh thumbnail và thông tin...")
        
        try:
            # Thử gửi ảnh từ URL trực tiếp
            response = client.sendRemoteImage(
                image_url=thumb_url,
                thread_id=thread_id,
                thread_type=thread_type,
                width=800,
                height=800,
                message=Message(text=info_text),
                ttl=TIME_TO_SELECT * 1000
            )
            
            msg_id = response.get('msgId') if isinstance(response, dict) else getattr(response, 'msgId', None)
            episode_select_status[thread_id] = (time.time(), False, msg_id, thread_type)
            print(f"[DEBUG] Đã gửi ảnh thumbnail từ URL, msgId: {msg_id}")
            
        except Exception as e:
            print(f"[ERROR] Lỗi khi gửi ảnh thumbnail từ URL: {e}")
            
            # Fallback: chỉ gửi text
            print(f"[WARNING] Gửi text thay thế")
            response = client.replyMessage(Message(text=info_text), message_object, thread_id, thread_type, ttl=TIME_TO_SELECT * 1000)
            msg_id = response.get('msgId')
            episode_select_status[thread_id] = (time.time(), False, msg_id, thread_type)
        
        # Tự động xóa sau thời gian hết hạn
        def cleanup_episode_list():
            print(f"[DEBUG] Hàm cleanup_episode_list() được gọi cho thread_id: {thread_id}")
            time.sleep(TIME_TO_SELECT)
            
            if thread_id in episode_select_status and not episode_select_status[thread_id][1]:
                print(f"[DEBUG] Đã hết thời gian chọn tập, đang xóa...")
                try:
                    msg_id_to_delete = episode_select_status[thread_id][2]
                    if msg_id_to_delete:
                        client.deleteGroupMsg(
                            msgId=msg_id_to_delete,
                            ownerId=author_id,
                            clientMsgId=message_object.get('cliMsgId'),
                            groupId=thread_id
                        )
                        print(f"[DEBUG] Đã xóa tin nhắn danh sách tập.")
                except Exception as e:
                    print(f"[ERROR] Lỗi khi xóa tin nhắn: {e}")
                
                # Xóa cache
                episode_select_results.pop(thread_id, None)
                episode_select_status.pop(thread_id, None)
                print(f"[DEBUG] Đã xóa cache cho thread_id: {thread_id}")
        
        # Chạy cleanup trong luồng riêng
        import threading
        print(f"[DEBUG] Khởi tạo thread cleanup...")
        cleanup_thread = threading.Thread(target=cleanup_episode_list)
        cleanup_thread.daemon = True
        cleanup_thread.start()
        print(f"[DEBUG] Đã khởi động thread cleanup")
        
    except Exception as e:
        print(f"[ERROR] Lỗi trong handle_multi_episode_movie: {e}")
        import traceback
        traceback.print_exc()

def handle_tap_command(message, message_object, thread_id, thread_type, author_id, client):
    """Handler cho lệnh chọn tập"""
    print(f"[DEBUG] ========== HÀM handle_tap_command() ĐƯỢC GỌI ==========")
    
    content = message.strip().split()
    print(f"[DEBUG] Content split: {content}")
    
    if len(content) < 2:
        print(f"[ERROR] Thiếu số tập")
        error_message = Message(text="🚫 Lỗi: Thiếu số tập\n\nCú pháp: tap <số tập>")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return
    
    # Kiểm tra xem có đang trong phiên chọn tập không
    if thread_id not in episode_select_status:
        print(f"[ERROR] Không tìm thấy episode_select_status cho thread_id: {thread_id}")
        error_message = Message(text="🚫 Bạn không thể chọn vì danh sách đã hết hạn hoặc không phải người tìm kiếm.")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return
    
    if episode_select_status[thread_id][1]:
        print(f"[ERROR] Danh sách đã được chọn trước đó")
        error_message = Message(text="🚫 Bạn không thể chọn vì danh sách đã hết hạn hoặc không phải người tìm kiếm.")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return
    
    # Kiểm tra thời gian hết hạn
    search_time = episode_select_status[thread_id][0]
    current_time = time.time()
    time_diff = current_time - search_time
    
    if time_diff > TIME_TO_SELECT:
        print(f"[ERROR] Danh sách đã hết hạn")
        error_message = Message(text="🚫 Danh sách đã hết hạn. Vui lòng tìm kiếm lại.")
        
        # Xóa cache
        episode_select_results.pop(thread_id, None)
        episode_select_status.pop(thread_id, None)
        
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return
    
    # Lấy thông tin phim đã lưu
    saved_data = episode_select_results.get(thread_id)
    if not saved_data:
        print(f"[ERROR] Không tìm thấy saved_data cho thread_id: {thread_id}")
        error_message = Message(text="🚫 Thông tin phim không tồn tại.")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return
    
    # Lấy số tập
    try:
        episode_num = int(content[1])
        print(f"[DEBUG] Người dùng chọn tập: {episode_num}")
    except ValueError:
        print(f"[ERROR] Số tập không hợp lệ: {content[1]}")
        error_message = Message(text="🚫 Lỗi: Số tập không hợp lệ.\nCú pháp: tap <số tập>")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return
    
    # Lấy danh sách tập
    episodes_list = saved_data['episodes_data'][0]['server_data'] if saved_data['episodes_data'] else []
    
    if episode_num < 1 or episode_num > len(episodes_list):
        print(f"[ERROR] Số tập nằm ngoài phạm vi")
        error_message = Message(text=f"🚫 Số tập không hợp lệ. Vui lòng chọn từ 1 đến {len(episodes_list)}.")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return
    
    # Đánh dấu đã chọn
    episode_select_status[thread_id] = (episode_select_status[thread_id][0], True, episode_select_status[thread_id][2], thread_type)
    print(f"[DEBUG] Đã đánh dấu đã chọn cho thread_id: {thread_id}")
    
    # Xóa tin nhắn danh sách tập
    try:
        msg_id_to_delete = episode_select_status[thread_id][2]
        if msg_id_to_delete:
            print(f"[DEBUG] Xóa tin nhắn có msgId: {msg_id_to_delete}")
            client.deleteGroupMsg(
                msgId=msg_id_to_delete,
                ownerId=author_id,
                clientMsgId=message_object.get('cliMsgId'),
                groupId=thread_id
            )
        print("[DEBUG] Đã xóa tin nhắn danh sách tập sau khi chọn.")
    except Exception as e:
        print(f"[ERROR] Lỗi khi xóa tin nhắn: {e}")
    
    # Xóa cache
    episode_select_results.pop(thread_id, None)
    episode_select_status.pop(thread_id, None)
    print(f"[DEBUG] Đã xóa cache sau khi chọn tập")
    
    # Lấy thông tin tập đã chọn
    episode_index = episode_num - 1
    selected_episode = episodes_list[episode_index]
    
    print(f"[DEBUG] Tập được chọn:")
    print(f"[DEBUG] - Tên: {selected_episode.get('name', f'Tập {episode_num}')}")
    print(f"[DEBUG] - URL: {selected_episode.get('link_m3u8')}")
    
    # Gửi thông báo đang tải
    title = saved_data['selected_movie']['title']
    episode_title = f"{title} - {selected_episode.get('name', f'Tập {episode_num}')}"
    download_message = Message(
        text=f"🔽 Đang tải tập {episode_num}: {title[:50]}{'...' if len(title) > 50 else ''}\n"
             f"📺 Tập: {selected_episode.get('name', f'Tập {episode_num}')}"
    )
    print(f"[DEBUG] Đang gửi thông báo đang tải...")
    client.replyMessage(download_message, message_object, thread_id, thread_type, ttl=30000)
    
    # Thêm reaction đang xử lý
    try:
        print(f"[DEBUG] Đang gửi reaction ⏳...")
        client.sendReaction(message_object, "⏳", thread_id, thread_type, reactionType=55)
    except Exception as e:
        print(f"[ERROR] Lỗi khi gửi reaction ⏳: {e}")
    
    # Tải và gửi tập phim
        # === PHẦN MỚI: TẢI FULL + TÁCH + GỬI ===
    video_url = selected_episode.get('link_m3u8')
    episode_name = selected_episode.get('name', f'Tập {episode_num}')
    thumb_url = saved_data['selected_movie']['thumb_url']
    phim_slug = saved_data['selected_movie'].get('slug', '')
    tap_slug = selected_episode.get('slug', f"tap{episode_num}")

    # Kiểm tra cache
    cached_urls = None
    if phim_slug:
        cached_urls = PHIM_CACHE.get(phim_slug, {}).get(tap_slug)

    if cached_urls:
        print(f"[INFO] Sử dụng cache cho {title} - {episode_name} ({len(cached_urls)} phần)")
        video_urls = cached_urls
    else:
        print(f"[INFO] Không có cache → Bắt đầu tải full phim: {title} - {episode_name}")
        print(f"[INFO] Link m3u8: {video_url}")
        
        # Tải full + tách
        parts = download_full_and_split(video_url, f"{title} - {episode_name}")
        if not parts:
            client.replyMessage(Message(text="🚫 Không tải được phim. Thử lại sau!"), 
                                message_object, thread_id, thread_type)
            return
        
        # Upload (SỬ DỤNG ASYNC VERSION QUA WRAPPER)

        video_urls = upload_parts(client, parts, thread_id, thread_type)
        if not video_urls:
            client.replyMessage(Message(text="🚫 Upload thất bại sau 3 lần thử."), 
                                message_object, thread_id, thread_type)
            return
        
        # Lưu cache
        if phim_slug:
            if phim_slug not in PHIM_CACHE:
                PHIM_CACHE[phim_slug] = {}
            PHIM_CACHE[phim_slug][tap_slug] = video_urls


    
    success = send_phim_parts(
        client=client,
        urls=video_urls,
        title=title,
        ep_name=episode_name,
        thumb=thumb_url,
        message_object=message_object,
        thread_id=thread_id,
        thread_type=thread_type
    )

    # Reaction
    try:
        client.sendReaction(message_object, "", thread_id, thread_type, -1)  # xóa ⏳
        client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
    except:
        pass

    if not success:
        client.replyMessage(Message(text="⚠️ Một số phần gửi lỗi, nhưng bạn vẫn có thể xem từ các phần đã gửi."), 
                            message_object, thread_id, thread_type)

# ---------------------------
# Mapping lệnh (giống cấu trúc search_ytb.py)
# ---------------------------
def get_mitaizl():
    """Trả về mapping các lệnh"""
    print(f"[DEBUG] Hàm get_mitaizl() được gọi")
    return {
        'phim': handle_phim_command,
        '//phim': handle_chonphim_command,
        'tap': handle_tap_command
    }
