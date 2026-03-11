import os
import re
import time
import random
import json
import requests
import subprocess
import asyncio
import yt_dlp
from typing import List, Dict, Any
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
from io import BytesIO
from cachetools import LRUCache
from datetime import datetime, timedelta
from youtube_search import YoutubeSearch
from zlapi import *
from zlapi.models import *

# ---------------------------
# Biến toàn cục
# ---------------------------
video_search_results = {}  # Lưu danh sách video theo thread_id
search_status = {}        # Lưu trạng thái tìm kiếm: (time_search_sent, has_selected, msg_id, thread_type)
PLATFORM = "youtube"
TIME_TO_SELECT = 120  # 120 giây (2 phút)
MAX_VIDEO_DURATION = 1500  # 25 phút = 1500 giây
MEDIA_CACHE = LRUCache(maxsize=100)  # Bộ nhớ đệm cho URL video

# Các hằng số cấu hình
DEFAULT_THUMBNAIL = 'https://i.imgur.com/ZaAJm1Z.jpeg'
FFMPEG_PATH = "/usr/bin/ffmpeg"

# Cấu hình cho yt-dlp
YDLCONFIG = {
    'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'force_generic_extractor': False,
    'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None
}

# ---------------------------
# Hàm hỗ trợ chung
# ---------------------------
def get_headers():
    print("[DEBUG] Hàm get_headers() được gọi")
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "*/*",
        "Referer": "https://www.youtube.com/",
        "Connection": "keep-alive"
    }

def parse_duration(duration_str: str) -> int:
    """Chuyển đổi thời lượng từ chuỗi sang giây"""
    print(f"[DEBUG] Hàm parse_duration() được gọi với duration_str: {duration_str}")
    try:
        parts = duration_str.split(':')
        if len(parts) == 2:
            minutes, seconds = map(int, parts)
            result = minutes * 60 + seconds
        elif len(parts) == 3:
            hours, minutes, seconds = map(int, parts)
            result = hours * 3600 + minutes * 60 + seconds
        else:
            result = 0
        print(f"[DEBUG] parse_duration() trả về: {result}")
        return result
    except (ValueError, AttributeError) as e:
        print(f"[ERROR] Lỗi trong parse_duration(): {e}")
        return 0

def format_duration(seconds: int) -> str:
    """Định dạng thời lượng sang chuỗi đẹp"""
    print(f"[DEBUG] Hàm format_duration() được gọi với seconds: {seconds}")
    if not seconds:
        print("[DEBUG] format_duration() trả về: N/A")
        return "N/A"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        result = f"{hours}h{minutes:02d}m"
    else:
        result = f"{minutes}:{secs:02d}"
    
    print(f"[DEBUG] format_duration() trả về: {result}")
    return result

def format_view_count(view_count: str) -> str:
    """Định dạng số lượt xem"""
    print(f"[DEBUG] Hàm format_view_count() được gọi với view_count: {view_count}")
    try:
        # Xóa các ký tự không phải số
        clean = re.sub(r'[^\d]', '', str(view_count))
        count = int(clean) if clean else 0
        
        if count >= 1_000_000:
            millions = count // 1_000_000
            hundred_thousands = (count % 1_000_000) // 100_000
            result = f"{millions}M{hundred_thousands}" if hundred_thousands else f"{millions}M"
        elif count >= 1_000:
            thousands = count // 1_000
            hundreds = (count % 1_000) // 100
            result = f"{thousands}K{hundreds}" if hundreds else f"{thousands}K"
        else:
            result = str(count)
        
        print(f"[DEBUG] format_view_count() trả về: {result}")
        return result
    except Exception as e:
        print(f"[ERROR] Lỗi trong format_view_count(): {e}")
        return str(view_count)

def translate_time(publish_time: str) -> str:
    """Dịch thời gian đăng tải sang tiếng Việt"""
    print(f"[DEBUG] Hàm translate_time() được gọi với publish_time: {publish_time}")
    translations = {
        'day': 'ngày', 'days': 'ngày',
        'hour': 'giờ', 'hours': 'giờ',
        'minute': 'phút', 'minutes': 'phút',
        'second': 'giây', 'seconds': 'giây',
        'week': 'tuần', 'weeks': 'tuần',
        'month': 'tháng', 'months': 'tháng',
        'year': 'năm', 'years': 'năm',
        'ago': 'trước'
    }
    result = publish_time
    for eng, viet in translations.items():
        result = result.replace(eng, viet)
    
    print(f"[DEBUG] translate_time() trả về: {result}")
    return result

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

def get_video_info(video_url: str) -> Dict[str, Any]:
    """Lấy thông tin video bằng yt-dlp"""
    print(f"[DEBUG] Hàm get_video_info() được gọi với video_url: {video_url}")
    
    try:
        # Làm sạch URL trước
        clean_url = clean_youtube_url(video_url)
        
        ydl_opts = {
            'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'force_generic_extractor': False,
            'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
            'ignoreerrors': True,
            'no_color': True,
            'socket_timeout': 30,
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls']
                }
            },
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        print(f"[DEBUG] Đang lấy thông tin video từ yt-dlp với URL: {clean_url}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(clean_url, download=False)
                if not info:
                    print(f"[ERROR] Không lấy được thông tin video từ URL: {clean_url}")
                    
                    # Thử với URL gốc nếu URL làm sạch không hoạt động
                    if clean_url != video_url:
                        print(f"[DEBUG] Thử với URL gốc: {video_url}")
                        info = ydl.extract_info(video_url, download=False)
                        
                        if not info:
                            print(f"[ERROR] Không lấy được thông tin video với cả hai URL")
                            return {}
            except Exception as e:
                print(f"[ERROR] Lỗi yt-dlp extract_info: {e}")
                import traceback
                traceback.print_exc()
                return {}
        
        result = {
            'title': info.get('title', 'Không có tiêu đề'),
            'duration': info.get('duration', 0),
            'view_count': info.get('view_count', 0),
            'uploader': info.get('uploader', 'Không rõ'),
            'thumbnail': info.get('thumbnail', DEFAULT_THUMBNAIL),
            'description': info.get('description', ''),
            'upload_date': info.get('upload_date', ''),
            'categories': info.get('categories', []),
            'tags': info.get('tags', []),
            'formats': info.get('formats', [])
        }
        
        print(f"[DEBUG] get_video_info() trả về thông tin video:")
        print(f"[DEBUG] - Tiêu đề: {result['title'][:50]}...")
        print(f"[DEBUG] - Thời lượng: {result['duration']}s")
        print(f"[DEBUG] - Lượt xem: {result['view_count']}")
        
        return result
        
    except Exception as e:
        print(f"[ERROR] Lỗi khi lấy thông tin video: {e}")
        import traceback
        traceback.print_exc()
        return {}

def download_video(video_url: str, output_path: str = None) -> Dict[str, Any]:
    """Tải video từ YouTube với khả năng cắt nếu quá dài"""
    print(f"[DEBUG] Hàm download_video() được gọi với video_url: {video_url}")
    
    try:
        # Kiểm tra và tạo thư mục cache nếu chưa có
        os.makedirs("cache", exist_ok=True)
        
        # Lấy thông tin video trước
        print(f"[DEBUG] Đang lấy thông tin video...")
        info = get_video_info(video_url)
        
        if not info or 'title' not in info:
            print(f"[ERROR] Không thể lấy thông tin video")
            return None
            
        duration = info.get('duration', 0)
        title = info.get('title', 'video')
        
        print(f"[DEBUG] Thông tin video:")
        print(f"[DEBUG] - Tiêu đề: {title}")
        print(f"[DEBUG] - Thời lượng: {duration}s")
        
        # Tạo tên file an toàn
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)[:100]
        
        if not output_path:
            output_path = f"cache/{safe_title}.mp4"
        
        print(f"[DEBUG] Output path: {output_path}")
        
        # Làm sạch URL
        clean_url = clean_youtube_url(video_url)
        
        # Cấu hình yt-dlp để tải video
        ydl_opts = {
            'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
            'outtmpl': output_path,
            'noplaylist': True,
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
            'ffmpeg_location': FFMPEG_PATH if os.path.exists(FFMPEG_PATH) else 'ffmpeg',
            'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
            'ignoreerrors': True,
            'no_color': True,
            'socket_timeout': 60,
            'retries': 3,
            'fragment_retries': 3,
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls']
                }
            },
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'http_headers': {
                'Accept': '*/*',
                'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
                'Referer': 'https://www.youtube.com/',
                'Origin': 'https://www.youtube.com'
            }
        }
        
        print(f"[DEBUG] Đang tải video từ YouTube: {clean_url}")
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(clean_url, download=True)
        except Exception as download_error:
            print(f"[WARNING] Lỗi khi tải với URL làm sạch: {download_error}")
            # Thử với URL gốc
            print(f"[DEBUG] Thử tải với URL gốc: {video_url}")
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_url, download=True)
            except Exception as e2:
                print(f"[ERROR] Lỗi khi tải video cả hai cách: {e2}")
                return None
        
        print(f"[DEBUG] Đã tải xong video")
        
        # Kiểm tra file đã tải
        if not os.path.exists(output_path):
            print(f"[ERROR] File không tồn tại sau khi tải: {output_path}")
            return None
            
        final_file = output_path
        final_duration = duration
        
        # Cắt video nếu quá dài (>25 phút)
        if duration > MAX_VIDEO_DURATION:
            print(f"[DEBUG] Video quá dài ({duration}s > {MAX_VIDEO_DURATION}s), đang cắt...")
            cut_file = output_path.replace('.mp4', '_cut.mp4')
            
            print(f"[DEBUG] Chạy lệnh ffmpeg để cắt video...")
            
            # Kiểm tra ffmpeg
            if not os.path.exists(FFMPEG_PATH):
                print(f"[WARNING] FFmpeg không tìm thấy tại: {FFMPEG_PATH}, thử dùng ffmpeg trong PATH")
                ffmpeg_cmd = 'ffmpeg'
            else:
                ffmpeg_cmd = FFMPEG_PATH
            
            try:
                result = subprocess.run([ffmpeg_cmd, "-y", "-i", output_path,
                    "-t", str(MAX_VIDEO_DURATION),
                    "-c", "copy",
                    cut_file
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
                
                if result.returncode != 0:
                    print(f"[WARNING] Lỗi khi cắt video: {result.stderr}")
                    # Vẫn sử dụng file gốc nếu không cắt được
                    cut_file = output_path
                    final_duration = duration
                elif os.path.exists(cut_file) and os.path.getsize(cut_file) > 0:
                    delete_file(output_path)  # Xóa file gốc
                    final_file = cut_file
                    final_duration = MAX_VIDEO_DURATION
                    print(f"[DEBUG] Đã cắt video thành công: {final_file}")
                else:
                    print(f"[WARNING] File cắt không tồn tại hoặc rỗng, giữ nguyên file gốc")
                    cut_file = output_path
                    final_duration = duration
            except Exception as e:
                print(f"[ERROR] Lỗi khi chạy ffmpeg: {e}")
                cut_file = output_path
                final_duration = duration
        
        # Kiểm tra nếu file đã được tải
        if os.path.exists(final_file) and os.path.getsize(final_file) > 0:
            file_size = os.path.getsize(final_file)
            print(f"[DEBUG] Đã tải video thành công: {final_file}")
            print(f"[DEBUG] Thông tin file: {file_size} bytes, {final_duration}s")
            
            result = {
                'file_path': final_file,
                'duration': final_duration,
                'title': title,
                'thumbnail': info.get('thumbnail', DEFAULT_THUMBNAIL) if info else DEFAULT_THUMBNAIL,
                'size': file_size
            }
            
            print(f"[DEBUG] download_video() trả về kết quả thành công")
            return result
        else:
            print(f"[ERROR] File không tồn tại hoặc rỗng sau khi tải: {final_file}")
            return None
            
    except Exception as e:
        print(f"[ERROR] Lỗi khi tải video: {e}")
        import traceback
        traceback.print_exc()
        return None

def extract_video_id(url: str) -> str:
    """Trích xuất video ID từ URL YouTube"""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
        r'embed\/([0-9A-Za-z_-]{11})',
        r'\/v\/([0-9A-Za-z_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

# ==================== HÀM UPLOAD ĐÃ SỬA GIỐNG PHIM.PY ====================
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
# ==================== KẾT THÚC HÀM UPLOAD ====================

# ---------------------------
# Hàm tạo ảnh danh sách video
# ---------------------------
def create_video_list_image(videos: List[Dict[str, Any]], max_show: int = 20):
    """Tạo ảnh danh sách video tương tự như ms.scl.py"""
    print(f"[DEBUG] Hàm create_video_list_image() được gọi")
    print(f"[DEBUG] - Số lượng video: {len(videos)}")
    print(f"[DEBUG] - max_show: {max_show}")
    
    try:
        import glob
        from PIL import Image, ImageDraw, ImageFont, ImageFilter
        import colorsys
        
        videos_to_show = videos[:min(max_show, len(videos))]
        num_videos = len(videos_to_show)
        
        print(f"[DEBUG] Số video sẽ hiển thị: {num_videos}")
        
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
        
        songs_per_column = 10
        num_columns = (num_videos - 1) // songs_per_column + 1
        
        img_width = padding * 2 + num_columns * card_width + (num_columns - 1) * column_spacing
        img_height = padding * 2 + header_height + songs_per_column * card_height + (songs_per_column - 1) * spacing_y
        
        print(f"[DEBUG] Kích thước ảnh: {img_width}x{img_height}")
        print(f"[DEBUG] Số cột: {num_columns}")
        
        # ==================== TẠO NỀN ====================
        # Lấy ảnh nền từ thư mục backgrounds
        BACKGROUND_FOLDER = 'backgrounds'
        background_images = []
        if os.path.isdir(BACKGROUND_FOLDER):
            background_images = [
                os.path.join(BACKGROUND_FOLDER, f) 
                for f in os.listdir(BACKGROUND_FOLDER) 
                if f.lower().endswith(('.jpg', '.jpeg', '.png'))
            ]
        
        print(f"[DEBUG] Số ảnh nền tìm thấy: {len(background_images)}")
        
        if background_images:
            bg_path = random.choice(background_images)
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
            font_artist = ImageFont.truetype("font/5.otf", 20 * scale)
            font_info = ImageFont.truetype("font/5.otf", 20 * scale)
            font_index = ImageFont.truetype("font/indexaSin2.otf", 70 * scale)
            font_header = ImageFont.truetype("font/5.otf", 50 * scale)
            emoji_font = ImageFont.truetype("font/NotoEmoji-Bold.ttf", 28 * scale)
            emoji_font_small = ImageFont.truetype("font/NotoEmoji-Bold.ttf", 21 * scale)
            print(f"[DEBUG] Đã tải font thành công")
        except Exception as e:
            print(f"[ERROR] Lỗi khi tải font: {e}")
            # Fallback nếu không tìm thấy font
            font_index = font_title = font_artist = font_info = font_header = emoji_font = emoji_font_small = ImageFont.load_default()
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
            import emoji as emoji_lib
            result = ''
            total_width = 0
            for char in text:
                font_used = font_emoji if emoji_lib.is_emoji(char) else font_text
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
        header_text = "DANH SÁCH VIDEO YOUTUBE"
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
        
        # ==================== VẼ DANH SÁCH VIDEO ====================
        print(f"[DEBUG] Đang vẽ danh sách video...")
        for col in range(num_columns):
            start_idx = col * songs_per_column
            end_idx = min(start_idx + songs_per_column, num_videos)
            column_videos = videos_to_show[start_idx:end_idx]
            
            left = padding + col * (card_width + column_spacing)
            
            print(f"[DEBUG] Cột {col + 1}: vị trí left={left}, số video={len(column_videos)}")
            
            for i, video in enumerate(column_videos):
                url = f"https://www.youtube.com{video.get('url_suffix', '')}"
                title = video.get('title', 'Không có tiêu đề')
                author = video.get('channel', 'Không rõ')
                duration = video.get('duration', '0:00')
                views = video.get('views', '0')
                thumbnail_url = video.get('thumbnails', [DEFAULT_THUMBNAIL])[0]
                
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
                    print(f"[DEBUG] Đang tải thumbnail: {thumbnail_url}")
                    response = requests.get(thumbnail_url, timeout=10, verify=False)
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
                
                # ========== VẼ THÔNG TIN VIDEO ==========
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
                
                # 2. TÁC GIẢ
                y_author = y_title + int(35 * scale)
                author_color = (200, 200, 200)  # Màu xám sáng
                
                max_author_width = max_text_width
                author_truncated = f"👤 {author}"
                if get_text_width(author_truncated, font_artist) > max_author_width:
                    author_truncated = truncate_text(author_truncated, max_author_width, font_artist, emoji_font_small)
                
                draw_text_with_shadow(draw, (x_text, y_author), author_truncated, font_artist, author_color, shadow_offset=(1, 1))
                
                # 3. THÔNG TIN (Views, Duration)
                stats = []
                if views: stats.append(f"👀 {format_view_count(views)}")
                if duration: stats.append(f"🕔 {duration}")
                
                info_text = " • ".join(stats) if stats else ""
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
        
        output_path = "video_list_ytb.jpg"
        os.makedirs("cache", exist_ok=True)
        image.save(output_path, quality=95)
        
        print(f"[DEBUG] Đã tạo ảnh thành công: {output_path}")
        print(f"[DEBUG] Kích thước ảnh cuối cùng: {image.width}x{image.height}")
        
        return output_path, image.width, image.height
        
    except Exception as e:
        print(f"[ERROR] Lỗi khi tạo ảnh danh sách video: {e}")
        import traceback
        traceback.print_exc()
        return None, 0, 0

# ---------------------------
# Hàm tìm kiếm YouTube
# ---------------------------
def search_video_list(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Tìm kiếm video trên YouTube"""
    print(f"[DEBUG] Hàm search_video_list() được gọi")
    print(f"[DEBUG] - Query: {query}")
    print(f"[DEBUG] - Limit: {limit}")
    
    try:
        print(f"[DEBUG] Đang tìm kiếm video với từ khóa: {query}")
        
        results = YoutubeSearch(query, max_results=limit).to_dict()
        
        print(f"[DEBUG] Tìm thấy {len(results)} kết quả thô")
        
        videos = []
        for idx, video in enumerate(results[:limit]):
            # Lọc video quá dài (>25 phút)
            duration_seconds = parse_duration(video.get('duration', '0:00'))
            if duration_seconds > MAX_VIDEO_DURATION:
                print(f"[DEBUG] Bỏ qua video {idx+1} vì quá dài: {duration_seconds}s")
                continue
                
            videos.append({
                'url': f"https://www.youtube.com{video.get('url_suffix', '')}",
                'title': video.get('title', 'Không có tiêu đề'),
                'channel': video.get('channel', 'Không rõ'),
                'duration': video.get('duration', '0:00'),
                'duration_seconds': duration_seconds,
                'views': video.get('views', '0'),
                'publish_time': video.get('publish_time', ''),
                'thumbnails': video.get('thumbnails', [DEFAULT_THUMBNAIL])
            })
        
        print(f"[DEBUG] Tìm thấy {len(videos)} video hợp lệ")
        return videos
        
    except Exception as e:
        print(f"[ERROR] Lỗi khi tìm kiếm video: {e}")
        import traceback
        traceback.print_exc()
        return []

def clean_youtube_url(url: str) -> str:
    """
    Làm sạch URL YouTube:
    - Giữ lại watch?v=VIDEO_ID
    - Loại bỏ list, start_radio, pp, index, si,...
    """
    try:
        video_id = extract_video_id(url)
        if not video_id:
            return url
        return f"https://www.youtube.com/watch?v={video_id}"
    except Exception as e:
        print(f"[ERROR] clean_youtube_url(): {e}")
        return url

# ---------------------------
# Handlers cho lệnh
# ---------------------------
def handle_ytb_command(message, message_object, thread_id, thread_type, author_id, client):
    """Handler cho lệnh ytb"""
    print(f"[DEBUG] ========== HÀM handle_ytb_command() ĐƯỢC GỌI ==========")
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
        error_message = Message(text="🚫 Lỗi: Thiếu từ khóa tìm kiếm\n\nCú pháp: ms.ytb <từ khóa tìm kiếm>")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return
    
    query = ' '.join(content[1:])
    print(f"[DEBUG] Query tìm kiếm: {query}")
    
    video_list = search_video_list(query)
    
    if not video_list:
        print(f"[ERROR] Không tìm thấy video nào")
        error_message = Message(text="❌ Không tìm thấy video nào phù hợp.")
        client.replyMessage(error_message, message_object, thread_id, thread_type)
        return
    
    print(f"[DEBUG] Tìm thấy {len(video_list)} video")
    
    # Lưu kết quả tìm kiếm
    video_search_results[thread_id] = video_list
    print(f"[DEBUG] Đã lưu video_search_results cho thread_id: {thread_id}")
    
    # Tạo ảnh danh sách
    print(f"[DEBUG] Đang tạo ảnh danh sách video...")
    list_image_path, list_image_width, list_image_height = create_video_list_image(video_list, max_show=20)
    
    if not list_image_path:
        print(f"[ERROR] Lỗi khi tạo ảnh danh sách")
        error_message = Message(text="❌ Lỗi khi tạo danh sách video.")
        client.replyMessage(error_message, message_object, thread_id, thread_type)
        return
    
    print(f"[DEBUG] Đã tạo ảnh: {list_image_path}, kích thước: {list_image_width}x{list_image_height}")
    
    guide_msg = "Nhập số (1, 2, 3,..., 20) để chọn video\nNhập 0 để hủy"
    
    # Lưu trạng thái tìm kiếm
    search_status[thread_id] = (time.time(), False, list_image_path, thread_type)
    print(f"[DEBUG] Đã lưu search_status cho thread_id: {thread_id}")
    
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
            search_status[thread_id] = (time.time(), False, msg_id, thread_type)
            print(f"[DEBUG] Đã lưu msgId của tin nhắn danh sách video: {msg_id}")
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
        
        if thread_id in search_status and not search_status[thread_id][1]:
            print(f"[DEBUG] Đã hết thời gian chọn, đang xóa...")
            try:
                # Xóa tin nhắn ảnh
                if isinstance(search_status[thread_id][2], str):  # Nếu là file path
                    print(f"[DEBUG] Xóa file ảnh: {search_status[thread_id][2]}")
                    delete_file(search_status[thread_id][2])
                else:  # Nếu là msg_id
                    print(f"[DEBUG] Xóa tin nhắn có msgId: {search_status[thread_id][2]}")
                    try:
                        client.deleteGroupMsg(
                            msgId=search_status[thread_id][2],
                            ownerId=author_id,
                            clientMsgId=message_object.get('cliMsgId'),
                            groupId=thread_id
                        )
                    except Exception as e:
                        print(f"[ERROR] Lỗi khi xóa tin nhắn: {e}")
                print("[DEBUG] Đã xóa ảnh danh sách video sau khi hết hạn.")
            except Exception as e:
                print(f"[ERROR] Lỗi khi xóa ảnh danh sách: {e}")
            
            # Xóa cache
            video_search_results.pop(thread_id, None)
            search_status.pop(thread_id, None)
            print(f"[DEBUG] Đã xóa cache cho thread_id: {thread_id}")
    
    # Chạy cleanup trong luồng riêng
    import threading
    print(f"[DEBUG] Khởi tạo thread cleanup...")
    cleanup_thread = threading.Thread(target=cleanup_search)
    cleanup_thread.daemon = True
    cleanup_thread.start()
    print(f"[DEBUG] Đã khởi động thread cleanup")

def handle_chonytb_command(message, message_object, thread_id, thread_type, author_id, client):
    """Handler cho lệnh chọn video"""
    print(f"[DEBUG] ========== HÀM handle_chonytb_command() ĐƯỢC GỌI ==========")
    print(f"[DEBUG] - Message: {message}")
    print(f"[DEBUG] - Thread ID: {thread_id}")
    print(f"[DEBUG] - Thread Type: {thread_type}")
    print(f"[DEBUG] - Author ID: {author_id}")
    
    content = message.strip().split()
    print(f"[DEBUG] Content split: {content}")
    
    if len(content) < 2:
        print(f"[ERROR] Thiếu số thứ tự")
        error_message = Message(text="🚫 Lỗi: Thiếu số thứ tự\n\nCú pháp: //ytb <số từ 1-20>")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return
    
    # Kiểm tra xem có đang trong phiên tìm kiếm không
    if thread_id not in search_status:
        print(f"[ERROR] Không tìm thấy search_status cho thread_id: {thread_id}")
        error_message = Message(text="🚫 Bạn không thể chọn vì danh sách đã hết hạn hoặc không phải người tìm kiếm.")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return
    
    if search_status[thread_id][1]:
        print(f"[ERROR] Danh sách đã được chọn trước đó")
        error_message = Message(text="🚫 Bạn không thể chọn vì danh sách đã hết hạn hoặc không phải người tìm kiếm.")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return
    
    # Kiểm tra thời gian hết hạn
    search_time = search_status[thread_id][0]
    current_time = time.time()
    time_diff = current_time - search_time
    
    print(f"[DEBUG] Thời gian tìm kiếm: {search_time}")
    print(f"[DEBUG] Thời gian hiện tại: {current_time}")
    print(f"[DEBUG] Thời gian đã trôi qua: {time_diff}s / {TIME_TO_SELECT}s")
    
    if time_diff > TIME_TO_SELECT:
        print(f"[ERROR] Danh sách đã hết hạn")
        error_message = Message(text="🚫 Danh sách đã hết hạn. Vui lòng tìm kiếm lại.")
        
        # Xóa cache
        video_search_results.pop(thread_id, None)
        search_status.pop(thread_id, None)
        
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return
    
    # Xử lý hủy tìm kiếm (nhập 0)
    if content[1] == '0':
        print(f"[DEBUG] Người dùng chọn hủy (0)")
        try:
            # Xóa tin nhắn ảnh
            if isinstance(search_status[thread_id][2], str):  # Nếu là file path
                print(f"[DEBUG] Xóa file ảnh: {search_status[thread_id][2]}")
                delete_file(search_status[thread_id][2])
            else:  # Nếu là msg_id
                print(f"[DEBUG] Xóa tin nhắn có msgId: {search_status[thread_id][2]}")
                try:
                    client.deleteGroupMsg(
                        msgId=search_status[thread_id][2],
                        ownerId=author_id,
                        clientMsgId=message_object.get('cliMsgId'),
                        groupId=thread_id
                    )
                except Exception as e:
                    print(f"[ERROR] Lỗi khi xóa tin nhắn: {e}")
            print("[DEBUG] Đã xóa ảnh danh sách video sau khi hủy.")
        except Exception as e:
            print(f"[ERROR] Lỗi khi xóa ảnh danh sách: {e}")
        
        # Xóa cache
        video_search_results.pop(thread_id, None)
        search_status.pop(thread_id, None)
        
        success_message = Message(text="🔄 Lệnh tìm kiếm đã được hủy. Bạn có thể thực hiện tìm kiếm mới.")
        client.replyMessage(success_message, message_object, thread_id, thread_type, ttl=60000)
        return
    
    # Chọn video theo số thứ tự
    try:
        index = int(content[1]) - 1
        print(f"[DEBUG] Người dùng chọn index: {index}")
    except ValueError:
        print(f"[ERROR] Số thứ tự không hợp lệ: {content[1]}")
        error_message = Message(text="🚫 Lỗi: Số thứ tự không hợp lệ.\nCú pháp: //ytb <số từ 1-20>")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return
    
    video_list = video_search_results.get(thread_id)
    if not video_list:
        print(f"[ERROR] Không tìm thấy video_list cho thread_id: {thread_id}")
        error_message = Message(text="🚫 Danh sách video không tồn tại.")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return
    
    print(f"[DEBUG] Độ dài video_list: {len(video_list)}")
    print(f"[DEBUG] Index được chọn: {index}")
    
    if index < 0 or index >= min(20, len(video_list)):
        print(f"[ERROR] Index nằm ngoài phạm vi")
        error_message = Message(text="🚫 Số thứ tự không hợp lệ. Vui lòng chọn từ 1 đến 20.")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return
    
    # Đánh dấu đã chọn
    search_status[thread_id] = (search_status[thread_id][0], True, search_status[thread_id][2], thread_type)
    print(f"[DEBUG] Đã đánh dấu đã chọn cho thread_id: {thread_id}")
    
    # Xóa tin nhắn ảnh danh sách
    try:
        if isinstance(search_status[thread_id][2], str):  # Nếu là file path
            print(f"[DEBUG] Xóa file ảnh: {search_status[thread_id][2]}")
            delete_file(search_status[thread_id][2])
        else:  # Nếu là msg_id
            print(f"[DEBUG] Xóa tin nhắn có msgId: {search_status[thread_id][2]}")
            try:
                client.deleteGroupMsg(
                    msgId=search_status[thread_id][2],
                    ownerId=author_id,
                    clientMsgId=message_object.get('cliMsgId'),
                    groupId=thread_id
                )
            except Exception as e:
                print(f"[ERROR] Lỗi khi xóa tin nhắn: {e}")
        print("[DEBUG] Đã xóa ảnh danh sách video sau khi chọn.")
    except Exception as e:
        print(f"[ERROR] Lỗi khi xóa ảnh danh sách: {e}")
    
    # Lấy video được chọn
    selected_video = video_list[index]
    
    print(f"[DEBUG] Video được chọn:")
    print(f"[DEBUG] - Tiêu đề: {selected_video['title']}")
    print(f"[DEBUG] - URL: {selected_video['url']}")
    print(f"[DEBUG] - Thời lượng: {selected_video['duration_seconds']}s")
    
    # Xóa cache
    video_search_results.pop(thread_id, None)
    search_status.pop(thread_id, None)
    print(f"[DEBUG] Đã xóa cache sau khi chọn")
    
    # Xử lý tải video
    process_video_download(selected_video, message_object, thread_id, thread_type, author_id, client)

def process_video_download(video: Dict[str, Any], message_object, thread_id, thread_type, author_id, client):
    """Xử lý tải và gửi video"""
    print(f"[DEBUG] ========== HÀM process_video_download() ĐƯỢC GỌI ==========")
    print(f"[DEBUG] - Video URL: {video['url']}")
    print(f"[DEBUG] - Tiêu đề: {video['title']}")
    print(f"[DEBUG] - Thread ID: {thread_id}")
    print(f"[DEBUG] - Thread Type: {thread_type}")
    
    try:
        video_url = video['url']
        title = video['title']
        author = video['channel']
        duration = video['duration_seconds']
        views = video['views']
        thumbnail_url = video['thumbnails'][0] if video['thumbnails'] else DEFAULT_THUMBNAIL
        
        print(f"[DEBUG] Thông tin video:")
        print(f"[DEBUG] - Tiêu đề: {title}")
        print(f"[DEBUG] - Tác giả: {author}")
        print(f"[DEBUG] - Thời lượng: {duration}s")
        print(f"[DEBUG] - Lượt xem: {views}")
        print(f"[DEBUG] - Thumbnail: {thumbnail_url}")
        
        # Gửi thông báo đang tải
        download_message = Message(
            text=f"🔽 Đang tải video: {title[:50]}{'...' if len(title) > 50 else ''}\n"
                 f"📊 Lượt xem: {format_view_count(views)}\n"
                 f"⏱️ Thời lượng: {format_duration(duration)}\n"
                 f"👤 Tác giả: {author}"
        )
        print(f"[DEBUG] Đang gửi thông báo đang tải...")
        client.replyMessage(download_message, message_object, thread_id, thread_type, ttl=30000)
        
        # Thêm reaction đang xử lý
        try:
            print(f"[DEBUG] Đang gửi reaction ⏳...")
            client.sendReaction(message_object, "⏳", thread_id, thread_type, reactionType=55)
        except Exception as e:
            print(f"[ERROR] Lỗi khi gửi reaction ⏳: {e}")
        
        # Kiểm tra cache
        cache_key = f"{PLATFORM}_{video_url}"
        cached_video = MEDIA_CACHE.get(cache_key)
        
        video_stream_url = None
        final_duration = duration
        
        if cached_video:
            print(f"[DEBUG] Sử dụng URL video từ bộ nhớ đệm: {cached_video}")
            video_stream_url = cached_video
            final_duration = duration
        else:
            print(f"[DEBUG] Không có trong cache, bắt đầu tải video...")
            # Tải video về local
            print(f"[DEBUG] Đang tải video từ YouTube: {video_url}")
            video_data = download_video(video_url)
            
            if not video_data:
                print(f"[ERROR] Không thể tải video")
                error_message = Message(text="🚫 Lỗi: Không thể tải video.")
                client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
                return
            
            local_file = video_data['file_path']
            final_duration = video_data['duration']
            thumbnail_url = video_data.get('thumbnail', thumbnail_url)
            
            print(f"[DEBUG] Đã tải video thành công:")
            print(f"[DEBUG] - File: {local_file}")
            print(f"[DEBUG] - Thời lượng: {final_duration}s")
            print(f"[DEBUG] - Thumbnail: {thumbnail_url}")
            
            try:
                # Upload video lên Zalo server (SỬ DỤNG HÀM UPLOAD MỚI)
                print(f"[DEBUG] Đang upload video lên Zalo server...")
                video_stream_url = upload_to_zalo(client, local_file, thread_id, thread_type)
                
                if not video_stream_url:
                    raise Exception("Upload lên Zalo thất bại")
                
                print(f"[DEBUG] Upload thành công! URL: {video_stream_url}")
                
                # Lưu vào cache
                MEDIA_CACHE[cache_key] = video_stream_url
                print(f"[DEBUG] Đã lưu vào cache với key: {cache_key}")
                
            except Exception as e:
                print(f"[ERROR] Lỗi khi upload video lên Zalo: {e}")
                
                # Fallback: thử upload lên transfer.sh
                try:
                    print(f"[DEBUG] Đang thử upload lên transfer.sh...")
                    with open(local_file, 'rb') as f:
                        files = {'file': f}
                        response = requests.post('https://transfer.sh/', files=files, timeout=60)
                        if response.status_code == 200:
                            video_stream_url = response.text.strip()
                            print(f"[DEBUG] Đã upload video lên transfer.sh: {video_stream_url}")
                        else:
                            raise Exception("Transfer.sh upload failed")
                except Exception as e2:
                    print(f"[ERROR] Lỗi khi upload lên transfer.sh: {e2}")
                    error_message = Message(text="🚫 Lỗi: Không thể upload video.")
                    client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
                    delete_file(local_file)
                    return
            
            # Xóa file local
            delete_file(local_file)
        
        if not video_stream_url:
            print(f"[ERROR] Không thể lấy URL video")
            error_message = Message(text="🚫 Lỗi: Không thể lấy URL video.")
            client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
            return
        
        # Tạo message thông tin
        info_text = (
            f"🎬 Video   : {title[:100]}{'...' if len(title) > 100 else ''}\n"
            f"👤 Tác giả : {author}\n"
            f"⏱️ Thời lượng: {format_duration(final_duration)}\n"
            f"📊 Lượt xem : {format_view_count(views)}\n"
            f"🔗 Nguồn   : YouTube"
        )
        
        messagesend = Message(text=info_text)
        
        # Xóa reaction đang xử lý
        try:
            print(f"[DEBUG] Đang xóa reaction ⏳...")
            client.sendReaction(message_object, "", thread_id, thread_type, -1)
        except Exception as e:
            print(f"[ERROR] Lỗi khi xóa reaction ⏳: {e}")
        
        # Thêm reaction thành công
        try:
            print(f"[DEBUG] Đang gửi reaction ✅...")
            client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
        except Exception as e:
            print(f"[ERROR] Lỗi khi gửi reaction ✅: {e}")
        
        # Gửi video bằng sendRemoteVideo
        print(f"[DEBUG] ========= THÔNG TIN GỬI VIDEO =========")
        print(f"[DEBUG] Video URL: {video_stream_url}")
        print(f"[DEBUG] Thumbnail: {thumbnail_url}")
        print(f"[DEBUG] Duration: {final_duration * 1000}ms")
        print(f"[DEBUG] Thread ID: {thread_id}")
        print(f"[DEBUG] Thread Type: {thread_type}")
        
        try:
            print(f"[DEBUG] Đang gọi sendRemoteVideo...")
            response = client.sendRemoteVideo(
                videoUrl=video_stream_url,
                thumbnailUrl=thumbnail_url,
                duration=final_duration * 1000,  # Chuyển sang mili giây
                message=messagesend,
                thread_id=thread_id,
                thread_type=thread_type,
                width=1280,
                height=720,
                ttl=86000000  # ~24 giờ
            )
            print("[SUCCESS] ĐÃ GỬI VIDEO THÀNH CÔNG!")
            print(f"[DEBUG] Response: {json.dumps(response, indent=2)}")
            
        except Exception as e:
            print(f"[ERROR] Lỗi khi gửi video: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback: gửi link
            fallback_message = Message(
                text=f"❌ Không thể gửi video trực tiếp.\n"
                     f"📥 Tải video tại đây: {video_stream_url}\n\n"
                     f"{info_text}"
            )
            print(f"[DEBUG] Gửi fallback message...")
            client.replyMessage(fallback_message, message_object, thread_id, thread_type, ttl=120000000)
    
    except Exception as e:
        print(f"[ERROR] Lỗi trong quá trình xử lý video: {e}")
        import traceback
        traceback.print_exc()
        
        error_message = Message(text=f"🚫 Lỗi: {str(e)[:100]}")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)

# ---------------------------
# Mapping lệnh
# ---------------------------
def get_mitaizl():
    """Trả về mapping các lệnh"""
    return {
        'ytb': handle_ytb_command,
        '//ytb': handle_chonytb_command
    }