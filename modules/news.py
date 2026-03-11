from zlapi import ZaloAPI
from zlapi.models import Message
import requests
from bs4 import BeautifulSoup
from gtts import gTTS
import random
import time
import os
from io import BytesIO

# Constants
CACHE_PATH = "modules/cache/"
OUTPUT_IMAGE_PATH = os.path.join(CACHE_PATH, "news.png")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

URL_VNEXPRESS = "https://vnexpress.net/"
URL_TUOITRE = "https://tuoitre.vn/"
URL_ZINGNEWS = "https://zingnews.vn/"
URL_DANTRI = "https://dantri.com.vn/tin-moi-nhat.htm"
URL_VOV = "https://vov.vn/"
URL_THETHAO247 = "https://thethao247.vn/"
URL_CAFEF = "https://cafef.vn/"

des = {
    'tác giả': "Minh Vũ",
    'mô tả': "Tra cứu tin tức từ các nguồn báo chí Việt Nam",
    'tính năng': [
        "🔍 Lấy tin tức từ các nguồn như VNExpress, Tuổi Trẻ, Zing News, Dân Trí, VOV, Thể Thao 247, CafeF.",
        "📨 Gửi phản hồi với tiêu đề, mô tả và liên kết bài báo.",
        "🔔 Tạo voice clip tóm tắt các tiêu đề tin tức.",
        "⏳ Hỗ trợ tra cứu tối đa 5 tin tức từ một hoặc nhiều nguồn."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh news [số lượng] [tên nguồn] để lấy tin từ nguồn cụ thể.",
        "📩 Gửi lệnh news [số lượng] tổng hợp để lấy tin ngẫu nhiên từ tất cả các nguồn.",
        "📌 Ví dụ: news 3 vnexpress hoặc news 4 tổng hợp."
    ]
}

def handle_news_command(message, message_object, thread_id, thread_type, author_id, client):
    # Send reaction to confirm command received
    action = "✅"
    client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)

    try:
        # Extract parameters from message, e.g., "news 3 vnexpress"
        parts = message.split(" ", 2)
        if len(parts) < 2 or not parts[1].strip():
            error_message = Message(text="Vui lòng cung cấp số lượng tin tức (tối đa 5).")
            client.sendMessage(error_message, thread_id, thread_type, ttl= 120000)
            return
        
        try:
            num_articles = int(parts[1])
            if num_articles <= 0 or num_articles > 5:
                raise ValueError
        except ValueError:
            error_message = Message(text="Số lượng tin phải là số nguyên dương, tối đa 5.")
            client.sendMessage(error_message, thread_id, thread_type)
            return

        source_name = parts[2].strip().lower() if len(parts) > 2 else "tổng hợp"

        # Define news sources
        news_sources = {
            "vnexpress": get_news_vnexpress,
            "tuoitre": get_news_tuoitre,
            "zingnews": get_news_zingnews,
            "dantri": get_news_dantri,
            "vov": get_news_vov,
            "thethao247": get_news_thethao247,
            "cafef": get_news_cafef
        }

        source_names_humanized = {
            "vnexpress": "VNExpress chấm net",
            "tuoitre": "Tuổi Trẻ chấm VN",
            "zingnews": "Zing News chấm VN",
            "dantri": "Dân Trí chấm com chấm VN",
            "vov": "VOV chấm VN",
            "thethao247": "Thể Thao Hai Bốn Bảy chấm VN",
            "cafef": "CafeF chấm VN"
        }

        articles = []
        sent_links = set()

        # Handle news fetching
        if source_name in news_sources:
            try:
                news = news_sources[source_name]()
                if news:
                    unique_articles = [article for article in news if article['link'] not in sent_links]
                    if len(unique_articles) >= num_articles:
                        articles = random.sample(unique_articles, num_articles)
                    else:
                        articles = unique_articles
                    sent_links.update(article['link'] for article in articles)
            except Exception as e:
                print(f"Lỗi khi lấy tin từ nguồn {source_name}: {e}")
                error_message = Message(text=f"Không thể lấy tin từ nguồn {source_name}.")
                client.sendMessage(error_message, thread_id, thread_type)
                return
        elif source_name == "tổng hợp":
            for source in news_sources.values():
                if len(articles) >= num_articles:
                    break
                try:
                    news = source()
                    if news:
                        unique_articles = [article for article in news if article['link'] not in sent_links]
                        if unique_articles:
                            random_article = random.choice(unique_articles)
                            articles.append(random_article)
                            sent_links.add(random_article['link'])
                except Exception as e:
                    print(f"Lỗi khi lấy tin từ nguồn {source.__name__}: {e}")
        else:
            error_message = Message(text=f"Nguồn '{source_name}' không hợp lệ. Các nguồn hỗ trợ: {', '.join(news_sources.keys())} hoặc 'tổng hợp'.")
            client.sendMessage(error_message, thread_id, thread_type)
            return

        if not articles:
            error_message = Message(text="Không tìm thấy tin tức nào từ nguồn yêu cầu.")
            client.sendMessage(error_message, thread_id, thread_type)
            return

        # Send news articles with delay
        summary_text = f"Tin tức từ {source_names_humanized.get(source_name, 'tổng hợp')} hôm nay:\n"
        for i, article in enumerate(articles, 1):
            title = article.get('title', 'Không có tiêu đề')
            description = article.get('description', 'Không có mô tả.')
            link = article.get('link', '#')

            detailed_message = f"📰 [Tin {i}: {title}]\n📝 Mô tả: {description}\n"
            client.sendLink(
                link,
                title=title,
                thread_id=thread_id,
                thread_type=thread_type,
                message=Message(text=detailed_message),
                ttl=100000
            )
            summary_text += f"Tin {i}: {title}.\n"
            time.sleep(1)  # Delay 3 seconds between sending each article

        # Generate and send voice clip
        try:
            mp3_file_path = create_voice_clip(summary_text)
            if mp3_file_path and os.path.exists(mp3_file_path):
                uploaded_url = upload_to_uguu(mp3_file_path)
                if uploaded_url:
                    client.sendRemoteVoice(
                        uploaded_url,
                        thread_id,
                        thread_type,
                        fileSize=os.path.getsize(mp3_file_path),
                        ttl=100000
                    )
                os.remove(mp3_file_path)
        except Exception as e:
            print(f"Lỗi khi xử lý voice: {e}")
            client.sendMessage(Message(text="Không thể tạo hoặc gửi voice clip."), thread_id, thread_type)

    except Exception as e:
        print(f"Lỗi: {e}")
        error_message = Message(text="Đã xảy ra lỗi khi xử lý yêu cầu.")
        client.sendMessage(error_message, thread_id, thread_type)

def get_news_vnexpress():
    try:
        response = requests.get(URL_VNEXPRESS, headers=HEADERS)
        if response.status_code != 200:
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        articles = []
        for item in soup.select("article.item-news")[:5]:
            title_element = item.select_one("h3.title-news a")
            desc_element = item.select_one("p.description a")
            articles.append({
                "title": title_element.text.strip() if title_element else "Không có tiêu đề",
                "link": title_element["href"].strip() if title_element else "#",
                "description": desc_element.text.strip() if desc_element else "Không có mô tả."
            })
        return articles
    except Exception as e:
        print(f"Lỗi khi lấy tin từ VNExpress: {e}")
        return []

def get_news_tuoitre():
    try:
        response = requests.get(URL_TUOITRE, headers=HEADERS)
        if response.status_code != 200:
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        articles = []
        for item in soup.select(".box-category-item")[:5]:
            title_element = item.select_one("h3 a")
            desc_element = item.select_one(".box-category-lead")
            articles.append({
                "title": title_element.text.strip() if title_element else "Không có tiêu đề",
                "link": "https://tuoitre.vn" + title_element["href"].strip() if title_element else "#",
                "description": desc_element.text.strip() if desc_element else "Không có mô tả."
            })
        return articles
    except Exception as e:
        print(f"Lỗi khi lấy tin từ Tuổi Trẻ: {e}")
        return []

def get_news_zingnews():
    try:
        response = requests.get(URL_ZINGNEWS, headers=HEADERS)
        if response.status_code != 200:
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        articles = []
        for item in soup.select(".article-item")[:5]:
            title_element = item.select_one("p.article-title a")
            desc_element = item.select_one("p.article-summary")
            link = title_element["href"].strip() if title_element else "#"
            if not link.startswith("https"):
                link = "https://zingnews.vn" + link
            articles.append({
                "title": title_element.text.strip() if title_element else "Không có tiêu đề",
                "link": link,
                "description": desc_element.text.strip() if desc_element else "Không có mô tả."
            })
        return articles
    except Exception as e:
        print(f"Lỗi khi lấy tin từ Zing News: {e}")
        return []

def get_news_dantri():
    try:
        response = requests.get(URL_DANTRI, headers=HEADERS)
        if response.status_code != 200:
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        articles = []
        for item in soup.select("article.article-item")[:5]:
            title_element = item.select_one("h3.article-title a")
            desc_element = item.select_one(".article-excerpt")
            link = title_element["href"].strip() if title_element else "#"
            if not link.startswith("https"):
                link = "https://dantri.com.vn" + link
            articles.append({
                "title": title_element.text.strip() if title_element else "Không có tiêu đề",
                "link": link,
                "description": desc_element.text.strip() if desc_element else "Không có mô tả."
            })
        return articles
    except Exception as e:
        print(f"Lỗi khi lấy tin từ Dân Trí: {e}")
        return []

def get_news_vov():
    try:
        response = requests.get(URL_VOV, headers=HEADERS)
        if response.status_code != 200:
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        articles = []
        for item in soup.select(".carousel .item .article-card")[:5]:
            title_element = item.select_one(".vovvn-title h3")
            link_element = item.select_one(".vovvn-title")
            desc_element = item.select_one(".sapo")
            articles.append({
                "title": title_element.text.strip() if title_element else "Không có tiêu đề",
                "link": URL_VOV.rstrip('/') + link_element["href"].strip() if link_element else "#",
                "description": desc_element.text.strip() if desc_element else "Không có mô tả."
            })
        return articles
    except Exception as e:
        print(f"Lỗi khi lấy tin từ VOV: {e}")
        return []

def get_news_thethao247():
    try:
        response = requests.get(URL_THETHAO247, headers=HEADERS)
        if response.status_code != 200:
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        articles = []
        for item in soup.select(".bot-pick ul li")[:5]:
            title_element = item.select_one("h2 a")
            link_element = item.select_one("a")
            desc_element = item.select_one(".sapo")
            articles.append({
                "title": title_element.text.strip() if title_element else "Không có tiêu đề",
                "link": link_element["href"].strip() if link_element else "#",
                "description": desc_element.text.strip() if desc_element else "Không có mô tả."
            })
        return articles
    except Exception as e:
        print(f"Lỗi khi lấy tin từ Thể Thao 247: {e}")
        return []

def get_news_cafef():
    try:
        response = requests.get(URL_CAFEF, headers=HEADERS)
        if response.status_code != 200:
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        articles = []
        for item in soup.select(".tlitem")[:5]:
            title_element = item.select_one("h3 a")
            desc_element = item.select_one(".sapo")
            articles.append({
                "title": title_element.text.strip() if title_element else "Không có tiêu đề",
                "link": "https://cafef.vn" + title_element["href"].strip() if title_element else "#",
                "description": desc_element.text.strip() if desc_element else "Không có mô tả."
            })
        return articles
    except Exception as e:
        print(f"Lỗi khi lấy tin từ CafeF: {e}")
        return []

def create_voice_clip(text):
    try:
        tts = gTTS(text, lang='vi', slow=False)
        mp3_file_path = os.path.join(CACHE_PATH, "news_summary.mp3")
        os.makedirs(CACHE_PATH, exist_ok=True)
        tts.save(mp3_file_path)
        return mp3_file_path
    except Exception as e:
        print(f"Lỗi khi tạo voice clip: {e}")
        return None

def upload_to_uguu(file_path):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
    }
    try:
        with open(file_path, 'rb') as file:
            files = {'files[]': file}
            print(f"➜ Uploading file to Uguu: {file_path}")
            response = requests.post("https://uguu.se/upload", files=files, headers=headers)
            response.raise_for_status()
        result = response.json()
        if result.get("success"):
            print(f"➜ Upload thành công: {result['files'][0]['url']}")
            return result["files"][0]["url"]
        else:
            print(f"Upload thất bại: {result}")
            return None
    except Exception as e:
        print(f"➜ Lỗi khi upload file lên Uguu: {e}")
        return None

def get_mitaizl():
    return {
        'news': handle_news_command
    }