import time
import random
import json
import requests
import threading
import os
import re
from zlapi import ZaloAPI
from zlapi.models import Message, ThreadType
from datetime import datetime
import pytz
from PIL import Image
from io import BytesIO
import tempfile
import feedparser
from bs4 import BeautifulSoup
from config import ADMIN

# === CẤU HÌNH – 18 NGUỒN BÁO UY TÍN NHẤT VIỆT NAM ===
RSS_FEEDS = [
    "https://vnexpress.net/rss/thoi-su.rss",
    "https://vnexpress.net/rss/doi-song.rss",
    "https://vnexpress.net/rss/phap-luat.rss",
    "https://tuoitre.vn/rss/thoi-su.rss",
    "https://tuoitre.vn/rss/the-gioi.rss",
    "https://tuoitre.vn/rss/phap-luat.rss",
    "https://thanhnien.vn/rss/thoi-su.rss",
    "https://dantri.com.vn/rss/thoi-su.rss",
    "https://dantri.com.vn/rss/tin-moi-nhat.rss",      
    "https://cand.com.vn/rssfeed/",
    "https://cand.com.vn/rssfeed/thong-tin-phap-luat",
    "https://cand.com.vn/rssfeed/quoc-te",
    "https://cand.com.vn/rssfeed/ban-tin-113",   
    "https://phaply.net.vn/rss/phia-sau-ban-an.rss",
]

# Múi giờ Việt Nam
VN_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

# Cài đặt nhóm
news_group_settings = {}
SETTINGS_LOCK = threading.Lock()

# Session HTTP riêng
news_session = requests.Session()
news_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})



# ===================================================================
# === 3. LẤY TIN TỪ RSS ===
# ===================================================================
def fetch_news():
    all_entries = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:30]:
                image = None

                if 'enclosures' in entry:
                    for enc in entry.enclosures:
                        if enc.type and enc.type.startswith('image/') and 'url' in enc:
                            image = enc.url
                            break

                if not image and hasattr(entry, 'thumb'):
                    image = entry.thumb

                if not image and hasattr(entry, 'media_content'):
                    for media in entry.media_content:
                        if 'url' in media:
                            image = media['url']
                            break

                if not image and hasattr(entry, 'g_image_link'):
                    image = entry.g_image_link
                elif not image and hasattr(entry, 'image_link'):
                    image = entry.image_link

                if not image and 'description' in entry:
                    desc = entry.description
                    match = re.search(r'src=["\'](.*?)["\']', desc)
                    if match:
                        image = match.group(1)

                if image and 'genk.vn' in url:
                    image = re.sub(r'/zoom/\d+_\d+/', '/thumb_w/1200/', image)
                    if 'thumb_w' not in image:
                        image = image.split('-crop-')[0] + '.jpg'

                all_entries.append({
                    'title': entry.title,
                    'link': entry.link,
                    'image': image,
                    'published': entry.get('published', 'Không rõ thời gian')
                })
        except Exception as e:
            print(f"[News] Lỗi RSS {url}: {e}")
  
    if not all_entries:
        return None
  
    with_image = [e for e in all_entries if e['image']]
    return random.choice(with_image or all_entries)

# ===================================================================
# === 4. TẢI ẢNH ===
# ===================================================================
def download_image(image_url):
    try:
        if not image_url or not image_url.startswith('http'):
            return None
        response = news_session.get(image_url, timeout=15, stream=True)
        response.raise_for_status()
        if 'image' not in response.headers.get('Content-Type', ''):
            return None
        image_data = BytesIO(response.content)
        image = Image.open(image_data)
        if image.mode in ('RGBA', 'LA'):
            bg = Image.new('RGB', image.size, (255, 255, 255))
            bg.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = bg
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            image_path = tmp.name
            image.save(image_path, 'PNG', optimize=True)
        return {
            'path': image_path,
            'width': image.width,
            'height': image.height
        }
    except Exception as e:
        print(f"[News] Lỗi tải ảnh: {e}")
        return None

# ===================================================================
# === 5. LẤY NỘI DUNG CHI TIẾT ===
# ===================================================================
def fetch_article_content(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'vi-VN,vi;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        response = news_session.get(url, timeout=20, headers=headers)
        response.raise_for_status()
        
        response.encoding = response.apparent_encoding or 'utf-8'
        text = response.text
        if 'Ã¢' in text or 'á»' in text or 'Dá»±' in text:
            text = response.content.decode('utf-8', errors='replace')
        
        soup = BeautifulSoup(text, 'lxml')
        title = ""
        content = ""

        # CÁC BÁO CỤ THỂ
        if 'cand.com.vn' in url:
            title_tag = soup.find('h1', class_='title') or soup.find('h1')
            article = soup.find('div', class_='content') or soup.find('div', class_=re.compile(r'content|detail|body', re.I))
        elif 'tuoitre.vn' in url:
            title_tag = soup.find('h1', class_='article-title') or soup.find('h1')
            article = soup.find('div', class_='detail-content') or soup.find('article') or soup.find('div', class_=re.compile(r'content|article|body', re.I))
        elif 'vnexpress.net' in url:
            title_tag = soup.find('h1', class_='title-detail') or soup.find('h1')
            article = soup.find('article', class_='fck_detail') or soup.find('article') or soup.find('div', class_='content')
        elif 'thanhnien.vn' in url:
            title_tag = soup.find('h1', class_='detail-title') or soup.find('h1')
            article = soup.find('div', class_='detail-content') or soup.find('div', class_='content') or soup.find('article')
        elif 'plo.vn' in url:
            title_tag = soup.find('h1', class_='story-title') or soup.find('h1')
            article = soup.find('div', class_='story-detail') or soup.find('div', class_='content')
        elif 'baophapluat.vn' in url:
            title_tag = soup.find('h1', class_='title-detail') or soup.find('h1')
            article = soup.find('div', class_='content-detail') or soup.find('div', class_='content')
        elif 'anninhthudo.vn' in url:
            title_tag = soup.find('h1', class_='detail-title') or soup.find('h1')
            article = soup.find('div', class_='detail-content') or soup.find('div', class_='content')
        elif 'znews.vn' in url:
            title_tag = soup.find('h1', class_='the-title') or soup.find('h1')
            article = soup.find('div', class_='the-article-content') or soup.find('div', class_='content')
        elif 'phaply.net.vn' in url:
            title_tag = soup.find('h1', class_='post-title') or soup.find('h1')
            article = soup.find('div', class_='post-content') or soup.find('div', class_='content')
        else:
            title_tag = soup.find('h1')
            article = soup.find('article') or soup.find('div', class_=re.compile(r'content|detail|body|article', re.I))

        title = title_tag.get_text(strip=True) if title_tag else ""

        if article:
            for tag in article.find_all(['script', 'iframe', 'div', 'section'], class_=re.compile(r'ads|ad|banner|relate|sidebar', re.I)):
                tag.decompose()
            for tag in article.find_all(attrs={'class': re.compile(r'VCSortableInPreviewMode|image_desc|relate-news')}):
                tag.decompose()

            paragraphs = article.find_all('p')
            content_parts = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True) and len(p.get_text(strip=True)) > 10]
            content = "\n".join(content_parts)

        if len(content) > 2000:
            content = content[:2000].rsplit('\n', 1)[0] + "\n... (đọc tiếp tại link)"

        return {
            'title': title or "Không rõ tiêu đề",
            'content': content or "Không tải được nội dung."
        }

    except Exception as e:
        print(f"[News] Lỗi lấy nội dung {url}: {e}")
        return {'title': '', 'content': 'Không thể tải nội dung bài viết.'}

# ===================================================================
# === 6. GỬI TIN TỨC ===
# ===================================================================
def send_news(client, thread_id, ttl_ms):
    news = fetch_news()
    if not news:
        return False
    article = fetch_article_content(news['link'])
    full_title = article['title'] or news['title']
    image_info = download_image(news['image']) if news['image'] else None
    try:
        pub_dt = datetime.strptime(news['published'], '%a, %d %b %Y %H:%M:%S %z')
    except:
        try:
            pub_dt = datetime.strptime(news['published'][:-6], '%a, %d %b %Y %H:%M:%S')
            pub_dt = VN_TZ.localize(pub_dt)
        except:
            pub_dt = datetime.now(VN_TZ)
    days_vn = ['Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy', 'Chủ Nhật']
    formatted_time = f"{days_vn[pub_dt.weekday()]}, {pub_dt.day}/{pub_dt.month}/{pub_dt.year} {pub_dt.strftime('%H:%M')} GMT+7"
    caption = f"{full_title}\n\nLink: {news['link']}\n{formatted_time}\n\nChi tiết bài viết:\n{article['content']}"
    try:
        if image_info:
            client.sendLocalImage(
                imagePath=image_info['path'],
                thread_id=thread_id,
                thread_type=ThreadType.GROUP,
                message=Message(text=caption),
                width=image_info['width'],
                height=image_info['height'],
                ttl=ttl_ms
            )
            os.remove(image_info['path'])
        else:
            client.sendMessage(Message(text=caption), thread_id, ThreadType.GROUP, ttl=ttl_ms)
        return True
    except Exception as e:
        print(f"[News] Lỗi gửi tin: {e}")
        if image_info and os.path.exists(image_info['path']):
            os.remove(image_info['path'])
        return False

# ===================================================================
# === 7. VÒNG LẶP TỰ ĐỘNG ===
# ===================================================================
def auto_send_news(client, thread_id, delay_minutes):
    stop_event = threading.Event()
    news_group_settings[thread_id]['stop_event'] = stop_event
    ttl_ms = int(delay_minutes * 60 * 1000)

    while news_group_settings.get(thread_id, {}).get('enabled', False) and not stop_event.is_set():
        send_news(client, thread_id, ttl_ms)
        for _ in range(int(delay_minutes * 60)):
            if stop_event.is_set() or not news_group_settings.get(thread_id, {}).get('enabled', False):
                break
            time.sleep(1)
    print(f"[News] Đã dừng tự động gửi tin tức cho nhóm {thread_id}")

# ===================================================================
# === 8. BẬT / TẮT TỰ ĐỘNG ===
# ===================================================================
def start_auto_news(client, thread_id, delay_minutes):
    try:
        group_info = client.fetchGroupInfo(thread_id)
        group = group_info.gridInfoMap[str(thread_id)]
        group_name = group.name
        group_id = group.groupId
        settings = load_group_settings()

        if thread_id not in news_group_settings or not news_group_settings[thread_id].get('enabled', False):
            news_group_settings[thread_id] = {
                'enabled': True,
                'delay_minutes': delay_minutes,
                'group_id': group_id,
                'group_name': group_name,
                'thread': threading.Thread(
                    target=auto_send_news,
                    args=(client, thread_id, delay_minutes),
                    daemon=True
                )
            }
            news_group_settings[thread_id]['thread'].start()

            settings[str(thread_id)] = {
                'enabled': True,
                'delay_minutes': delay_minutes,
                'group_id': group_id,
                'group_name': group_name
            }
            save_group_settings(settings)
            return f"THÀNH CÔNG\nĐã bật tự động gửi tin tức cho {group_name}, mỗi {delay_minutes} phút"
        else:
            return f"THÀNH CÔNG\nTính năng đã được bật cho nhóm {group_name}!"
    except Exception as e:
        return f"THẤT BẠI\nLỗi khi bật: {str(e)}"

def stop_auto_news(thread_id):
    try:
        settings = load_group_settings()
        current = settings.get(str(thread_id), {})
        if thread_id in news_group_settings and news_group_settings[thread_id].get('enabled', False):
            news_group_settings[thread_id]['enabled'] = False
            if 'stop_event' in news_group_settings[thread_id]:
                news_group_settings[thread_id]['stop_event'].set()
        settings[str(thread_id)] = {
            'enabled': False,
            'delay_minutes': current.get('delay_minutes', 1.0),
            'group_id': current.get('group_id', str(thread_id)),
            'group_name': current.get('group_name', 'Unknown')
        }
        save_group_settings(settings)
        return f"THÀNH CÔNG\nĐã tắt tự động gửi tin tức cho nhóm {current.get('group_name', thread_id)}"
    except Exception as e:
        return f"THẤT BẠI\nLỗi khi tắt: {str(e)}"

# ===================================================================
# === 9. LƯU / ĐỌC CÀI ĐẶT ===
# ===================================================================
def load_group_settings():
    with SETTINGS_LOCK:
        try:
            if os.path.exists("auto_news_setting.json"):
                with open("auto_news_setting.json", "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"[News] Lỗi đọc file cài đặt: {e}")
            return {}

def save_group_settings(settings):
    with SETTINGS_LOCK:
        try:
            with open("auto_news_setting.json", "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[News] Lỗi lưu cài đặt: {e}")

# ===================================================================
# === 10. KHỞI ĐỘNG LẠI ===
# ===================================================================
def initialize_groups(client):
    settings = load_group_settings()
    for thread_id, config in settings.items():
        if config.get('enabled', False):
            try:
                tid = int(thread_id)
                delay = float(config.get('delay_minutes', 1))
                if 'group_name' not in config or config['group_name'] == 'Unknown':
                    try:
                        info = client.fetchGroupInfo(tid)
                        group = info.gridInfoMap[str(tid)]
                        config['group_name'] = group.name
                        config['group_id'] = group.groupId
                        settings[thread_id] = config
                        save_group_settings(settings)
                    except:
                        pass
                start_auto_news(client, tid, delay)
            except Exception as e:
                print(f"[News] Lỗi khởi tạo nhóm {thread_id}: {e}")

# ===================================================================
# === 11. XỬ LÝ LỆNH ===
# ===================================================================
def handle_auto_news(message, message_object, thread_id, thread_type, author_id, client):
    try:
        client.sendReaction(message_object, "Đã nhận lệnh", thread_id, thread_type, reactionType=75)
    except:
        pass

    if author_id not in ADMIN:
        client.replyMessage(Message(text="THẤT BẠI\nBạn không có quyền dùng lệnh này!"), message_object, thread_id, thread_type, ttl=20000)
        return

    parts = message.lower().strip().split()
    if len(parts) < 2 or parts[0] != "autonew":
        msg = "THẤT BẠI\nLệnh sai! Dùng:\nautonew on <phút>\nautonew off\nautonew list"
        client.replyMessage(Message(text=msg), message_object, thread_id, thread_type, ttl=20000)
        return

    cmd = parts[1]
    if cmd == "on" and len(parts) == 3:
        try:
            delay = float(parts[2])
            if delay <= 0:
                raise ValueError
            result = start_auto_news(client, thread_id, delay)
        except:
            result = "THẤT BẠI\nThời gian phải là số dương!"
    elif cmd == "off":
        result = stop_auto_news(thread_id)
    elif cmd == "list":
        settings = load_group_settings()
        lines = []
        for tid, conf in settings.items():
            status = "Bật" if conf.get('enabled') else "Tắt"
            lines.append(f"{conf.get('group_name', 'Unknown')} (ID: {conf.get('group_id', tid)}) | {conf.get('delay_minutes', '?')} phút | {status}")
        result = "THÀNH CÔNG\nDanh sách nhóm gửi tin tức:\n\n" + ("\n".join(lines) if lines else "Chưa có nhóm nào.")
    else:
        result = "THẤT BẠI\nLệnh không hợp lệ!"

    client.replyMessage(Message(text=result), message_object, thread_id, thread_type, ttl=20000)

# ===================================================================
# === 12. XUẤT MODULE ===
# ===================================================================
def get_mitaizl():
    return {
        'autonew': handle_auto_news,
        'on_start_news': initialize_groups
    }