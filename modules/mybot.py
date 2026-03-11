import os
import time
import json
import base64
import re
import threading
from datetime import datetime
from zlapi.models import Message
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException

# Hàm hỗ trợ để in log với thời gian
def print_log(message):
    """In log với thời gian hiện tại."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

# Biến toàn cục
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
DIRECTORY = os.path.join(MODULE_DIR, "data")
browser = None
browser_lock = threading.Lock()
is_in_use = False
current_user_id = None

def check_chromedriver_version():
    """Kiểm tra phiên bản ChromeDriver."""
    try:
        import subprocess
        result = subprocess.run(['chromedriver', '--version'], capture_output=True, text=True)
        version = result.stdout.strip()
        print(f"🛠️ Phiên bản ChromeDriver: {version}")
        return version
    except Exception as e:
        print(f"⚠️ Lỗi kiểm tra phiên bản ChromeDriver: {str(e)}")
        return None

def create_driver():
    """Khởi tạo trình duyệt Chrome với các thiết lập tối ưu (chạy được trên VPS Ubuntu)."""
    print("🚀 Bắt đầu khởi tạo trình duyệt Chrome (VPS headless)...")
    check_chromedriver_version()  # Kiểm tra phiên bản ChromeDriver
    try:
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager

        chrome_options = Options()
        # ⚙️ Đường dẫn Chrome bản .deb (đã cài trong /usr/bin/google-chrome)
        chrome_options.binary_location = "/usr/bin/google-chrome"

        # ⚙️ Cấu hình cần thiết cho VPS không có giao diện
        chrome_options.add_argument("--headless=new")  # chạy ẩn, không mở cửa sổ
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2, "media_stream": 2, "geolocation": 2
            },
            "profile.password_manager_enabled": False
        }
        chrome_options.add_experimental_option("prefs", prefs)
        chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

        print("🔧 Đang khởi tạo ChromeDriver...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("✅ Đã khởi tạo trình duyệt Chrome headless thành công")

        driver.delete_all_cookies()
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        print("🔒 Đã vô hiệu hóa thuộc tính 'navigator.webdriver'")
        return driver

    except WebDriverException as e:
        print(f"❌ WebDriverException: {str(e)}")
        return None
    except Exception as e:
        print(f"❌ Lỗi tạo trình duyệt: {str(e)}")
        return None


def initialize_browser():
    """Khởi tạo trình duyệt và tải trang Zalo."""
    global browser
    print("🚀 Đang khởi tạo trình duyệt và mở trang Zalo...")
    try:
        browser = create_driver()
        if not browser:
            print("❌ Không thể khởi tạo trình duyệt: create_driver trả về None")
            return False

        print("🌐 Đang mở trang https://chat.zalo.me/...")
        browser.get("https://chat.zalo.me/")
        print("⏳ Đang chờ trang Zalo tải hoàn tất (timeout: 30s)...")
        WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        print("✅ Trang Zalo đã tải thành công")
        return True
    except TimeoutException:
        print("❌ Hết thời gian chờ khi tải trang Zalo")
        return False
    except Exception as e:
        print(f"❍ Lỗi khởi tạo trình duyệt: {str(e)}")
        return False

def acquire_browser(user_id):
    """Chiếm quyền sử dụng trình duyệt cho người dùng cụ thể."""
    global is_in_use, current_user_id
    print(f"🔒 Đang kiểm tra quyền sử dụng trình duyệt cho user {user_id}...")
    with browser_lock:
        if not browser or is_in_use:
            print(f"⚠️ Trình duyệt không khả dụng hoặc đang được sử dụng bởi user {current_user_id}")
            return False
        is_in_use = True
        current_user_id = user_id
        print(f"✅ Đã chiếm quyền sử dụng trình duyệt cho user {user_id}")
        return True

def release_browser():
    """Giải phóng trình duyệt cho người dùng tiếp theo."""
    global is_in_use, current_user_id
    print("🔓 Đang giải phóng trình duyệt...")
    with browser_lock:
        is_in_use = False
        current_user_id = None
        print("✅ Trình duyệt đã được giải phóng")

def close_browser():
    """Đóng trình duyệt hoàn toàn."""
    global browser
    print("🛑 Đang đóng trình duyệt...")
    try:
        if browser:
            browser.quit()
            browser = None
            print("✅ Trình duyệt đã được đóng")
        else:
            print("⚠️ Trình duyệt chưa được khởi tạo")
    except Exception as e:
        print(f"❍ Lỗi khi đóng trình duyệt: {str(e)}")

class ZaloQRScanner:
    """Lớp xử lý quét mã QR và đăng nhập Zalo."""
    def __init__(self, user_id, driver):
        self.user_id = user_id
        self.driver = driver
        self.user_info = {}
        self.cookies = []
        self.imei = None
        self.success = False
        print(f"🔧 Khởi tạo ZaloQRScanner cho user {user_id}")

    def refresh_and_wait_for_qr(self, timeout=90):
        """Làm mới trang Zalo và chờ mã QR xuất hiện."""
        print(f"🔄 Làm mới trang Zalo cho user {self.user_id}")
        try:
            self.driver.refresh()
            print("✅ Đã làm mới trang Zalo")
            time.sleep(3)
            qr_selector = "#app > div > div > div.body > div.zcard.body-container.show-pc-banner > div.zcard-body > div.form-signin.animated.fadeIn > div > div > div.qr-container > img"
            print(f"⏳ Đang chờ mã QR xuất hiện (timeout: {timeout}s)...")
            qr_element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, qr_selector))
            )
            print("✅ Đã tìm thấy phần tử mã QR")
            return qr_element
        except TimeoutException:
            print("❍ Hết thời gian chờ mã QR")
            return None
        except Exception as e:
            print(f"❍ Lỗi làm mới trang: {str(e)}")
            return None

    def get_qr_code_image(self, qr_element, client, thread_id, thread_type, message_object):
        """Lấy và gửi hình ảnh mã QR."""
        print("📷 Đang lấy và gửi hình ảnh mã QR...")
        try:
            qr_src = qr_element.get_attribute("src")
            print(f"🔍 Đã lấy src của mã QR: {qr_src[:50]}...")
            if qr_src and qr_src.startswith("data:image"):
                base64_data = qr_src.split(",")[1]
                image_data = base64.b64decode(base64_data)
                qr_filename = f"zalo_qr_{self.user_id}_{int(time.time())}.png"
                qr_filepath = os.path.join(DIRECTORY, qr_filename)
                os.makedirs(DIRECTORY, exist_ok=True)
                print(f"📁 Đã tạo thư mục {DIRECTORY} nếu chưa tồn tại")

                with open(qr_filepath, "wb") as f:
                    f.write(image_data)
                print(f"💾 Đã lưu mã QR vào file: {qr_filepath}")

                client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
                print("✅ Đã gửi phản ứng xác nhận lệnh")
                if os.path.exists(qr_filepath):
                    client.sendLocalImage(
                        qr_filepath,
                        message=Message(text="📷 Quét mã QR này bằng Zalo trong 90 giây!\n✅ Vui lòng nhấn 'Xác nhận' trên ứng dụng Zalo để đăng nhập!"),
                        thread_id=thread_id,
                        thread_type=thread_type,
                        width=400,
                        height=400,
                        ttl=85000
                    )
                    print("✅ Đã gửi mã QR và thông báo xác nhận")
                    os.remove(qr_filepath)
                    print(f"🗑️ Đã xóa file mã QR: {qr_filepath}")
                    return qr_src
                else:
                    print("❍ Lỗi: File mã QR không tồn tại sau khi lưu")
                    return None
            print("❍ Lỗi: Mã QR không hợp lệ hoặc không phải định dạng data:image")
            return None
        except Exception as e:
            print(f"❍ Lỗi lấy mã QR: {str(e)}")
            return None

    def check_qr_scanned(self):
        """Kiểm tra trạng thái quét mã QR."""
        print("🔍 Đang kiểm tra trạng thái quét mã QR...")
        confirmation_selector = "#app > div > div > div.body > div.zcard.body-container.show-pc-banner > div.zcard-body > div.form-signin.animated.fadeIn > div > p"
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, confirmation_selector)
            if not elements:
                print("⚠️ Không tìm thấy phần tử xác nhận quét QR")
                return False, None
            for element in elements:
                if element.is_displayed():
                    text = element.text.strip()
                    if text:
                        self.user_info['confirmation_text'] = text
                        print(f"✅ Mã QR đã được quét, thông báo: {text}")
                        return True, text
            print("⚠️ Không có phần tử xác nhận nào hiển thị")
            return False, None
        except Exception as e:
            print(f"❌ Lỗi kiểm tra trạng thái quét mã QR: {str(e)}")
            return False, None

    def check_login_rejected(self):
        """Kiểm tra nếu đăng nhập bị từ chối."""
        print("🔍 Đang kiểm tra trạng thái từ chối đăng nhập...")
        reject_selector = "#app > div > div > div.body > div.zcard.body-container.show-pc-banner > div.zcard-body > div.form-signin.animated.fadeIn > div > div.textAlign-center > em"
        try:
            reject_elements = self.driver.find_elements(By.CSS_SELECTOR, reject_selector)
            if not reject_elements:
                print("✅ Không tìm thấy thông báo từ chối đăng nhập")
                return False, None
            for element in reject_elements:
                if element.is_displayed():
                    reject_text = element.text.strip()
                    if reject_text:
                        print(f"❍ Đăng nhập bị từ chối: {reject_text}")
                        return True, reject_text
            print("✅ Không có thông báo từ chối nào hiển thị")
            return False, None
        except Exception as e:
            print(f"❍ Lỗi kiểm tra trạng thái từ chối: {str(e)}")
            return False, None

    def extract_imei_from_network(self):
        """Trích xuất IMEI từ log mạng."""
        print("🆔 Đang trích xuất IMEI từ log mạng...")
        try:
            logs = self.driver.get_log('performance')
            print(f"📋 Tìm thấy {len(logs)} log mạng")
            for log in logs:
                message = json.loads(log['message'])
                if message.get('message', {}).get('method') == 'Network.requestWillBeSent':
                    params = message['message']['params']
                    url = params.get('request', {}).get('url', '')
                    headers = params.get('request', {}).get('headers', {})
                    imei_patterns = [
                        r'imei=([A-Za-z0-9_-]+)',
                        r'deviceId=([A-Za-z0-9_-]+)',
                        r'device_id=([A-Za-z0-9_-]+)',
                        r'uuid=([A-Za-z0-9_-]+)'
                    ]
                    for pattern in imei_patterns:
                        match = re.search(pattern, url)
                        if match and len(match.group(1)) > 10:
                            self.imei = match.group(1)
                            print(f"✅ Tìm thấy IMEI từ URL: {self.imei}")
                            return True
                    for key, value in headers.items():
                        if any(x in key.lower() for x in ['imei', 'device', 'uuid']) and len(str(value)) > 10:
                            self.imei = str(value)
                            print(f"✅ Tìm thấy IMEI từ headers: {self.imei}")
                            return True
            print("⚠️ Không tìm thấy IMEI trong log mạng")
            return False
        except Exception as e:
            print(f"❍ Lỗi trích xuất IMEI từ log mạng: {str(e)}")
            return False

    def extract_imei_from_page(self):
        """Trích xuất IMEI từ localStorage của trang."""
        print("🆔 Đang trích xuất IMEI từ localStorage...")
        try:
            z_uuid_script = """
                try {
                    return localStorage.getItem('z_uuid');
                } catch(e) {
                    return null;
                }
            """
            z_uuid = self.driver.execute_script(z_uuid_script)
            if z_uuid:
                self.imei = z_uuid
                print(f"✅ Tìm thấy IMEI từ z_uuid: {self.imei}")
                return True

            storage_script = """
                let result = {};
                try {
                    for(let i = 0; i < localStorage.length; i++) {
                        let key = localStorage.key(i);
                        let value = localStorage.getItem(key);
                        if(key.includes('uuid') || key.includes('z_')) {
                            result[key] = value;
                        }
                    }
                } catch(e) {}
                return result;
            """
            storage_data = self.driver.execute_script(storage_script)
            if storage_data and 'z_uuid' in storage_data:
                self.imei = storage_data['z_uuid']
                print(f"✅ Tìm thấy IMEI từ localStorage: {self.imei}")
                return True
            print("⚠️ Không tìm thấy IMEI trong localStorage")
            return False
        except Exception as e:
            print(f"❍ Lỗi trích xuất IMEI từ trang: {str(e)}")
            return False

    def extract_imei_and_cookies(self, client, thread_id, thread_type):
        """Trích xuất và lưu IMEI cùng cookies."""
        print("💾 Đang trích xuất và lưu cookie/IMEI...")
        try:
            cookies = self.driver.get_cookies()
            cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
            cookie_string = json.dumps(cookie_dict, separators=(',', ':'), ensure_ascii=False)
            print(f"🔑 Đã lấy cookie: {cookie_string}")
            cookie_dir = os.path.join(DIRECTORY, "copy")
            os.makedirs(cookie_dir, exist_ok=True)
            print(f"📁 Đã tạo thư mục {cookie_dir} nếu chưa tồn tại")

            cookie_file = os.path.join(cookie_dir, "cookie.txt")
            imei_file = os.path.join(cookie_dir, "imei.txt")

            with open(cookie_file, "w", encoding="utf-8") as f:
                f.write(cookie_string)
            print(f"💾 Đã lưu cookie vào file: {cookie_file}")

            imei_found = self.extract_imei_from_page() or self.extract_imei_from_network()
            if not imei_found:
                client.sendMessage(Message(text="❍ Không tìm thấy IMEI."), thread_id, thread_type)
                print("❍ Không tìm thấy IMEI")
                return False

            with open(imei_file, "w", encoding="utf-8") as f:
                f.write(self.imei)
            print(f"💾 Đã lưu IMEI vào file: {imei_file}")

            client.sendMessage(Message(text=f"✅ Đăng nhập thành công!\nIMEI = \"{self.imei}\"\nSESSION_COOKIES = {cookie_string}"), thread_id, thread_type)
            print(f"✅ Đăng nhập thành công. Cookie: {cookie_string}, IMEI: {self.imei}")
            return True
        except Exception as e:
            client.sendMessage(Message(text=f"❍ Lỗi lưu cookie/IMEI: {str(e)}"), thread_id, thread_type)
            print(f"❍ Lỗi lưu cookie/IMEI: {str(e)}")
            return False

    def monitor_login_status(self, client, thread_id, thread_type, message_object, qr_src, check_interval=2, max_wait_time=90):
        """Theo dõi trạng thái đăng nhập và tự động tải lại mã QR mới nếu hết hạn."""
        print("⏳ Bắt đầu theo dõi trạng thái đăng nhập (có tự động tải lại QR)...")
        start_time = time.time()
        stable_url = self.driver.current_url
        print(f"🔗 URL ban đầu: {stable_url}")
        qr_scanned = False
        qr_selector = "#app > div > div > div.body > div.zcard.body-container.show-pc-banner > div.zcard-body > div.form-signin.animated.fadeIn > div > div > div.qr-container > img"
        last_qr_src = qr_src
        last_qr_check_time = start_time
        qr_refresh_cooldown = 5  # thời gian chờ giữa các lần reload khi QR hết hạn

        while time.time() - start_time < max_wait_time:
            try:
                current_time = time.time()
                current_url = self.driver.current_url
                remaining_time = max_wait_time - int(current_time - start_time)
                print(f"⏱️ Còn lại {remaining_time}s, URL hiện tại: {current_url}")

                # Hết thời gian chờ
                if remaining_time <= 0:
                    client.sendMessage(Message(text=f"⏰ Hết thời gian chờ {max_wait_time}s."), thread_id, thread_type)
                    print("⏰ Hết thời gian chờ")
                    return False

                # Kiểm tra nếu người dùng từ chối / mã QR hết hạn
                rejected, reject_text = self.check_login_rejected()
                if rejected:
                    if "hết hạn" in reject_text.lower():
                        print("♻️ Mã QR đã hết hạn — đang tải lại mã mới...")
                        client.sendMessage(Message(text="♻️ Mã QR đã hết hạn — đang tải lại mã mới..."), thread_id, thread_type, ttl=5000)
                        # Làm mới và lấy QR mới
                        time.sleep(qr_refresh_cooldown)
                        qr_element = self.refresh_and_wait_for_qr()
                        if qr_element:
                            new_qr_src = self.get_qr_code_image(qr_element, client, thread_id, thread_type, message_object)
                            if new_qr_src:
                                last_qr_src = new_qr_src
                                print("✅ Đã gửi mã QR mới, tiếp tục theo dõi...")
                                continue
                        else:
                            print("❍ Không thể tải lại mã QR mới, dừng theo dõi.")
                            return False
                    else:
                        client.sendMessage(Message(text=f"❍ Đăng nhập bị từ chối: {reject_text}"), thread_id, thread_type)
                        print(f"❍ Đăng nhập bị từ chối: {reject_text}")
                        return False

                # Kiểm tra nếu mã QR mới được sinh ra
                if not qr_scanned:
                    try:
                        qr_element = WebDriverWait(self.driver, 2).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, qr_selector))
                        )
                        current_qr_src = qr_element.get_attribute("src")
                        if current_qr_src and current_qr_src != last_qr_src and current_qr_src.startswith("data:image"):
                            print("🔄 Phát hiện mã QR mới, đang gửi lại...")
                            last_qr_src = self.get_qr_code_image(qr_element, client, thread_id, thread_type, message_object)
                            last_qr_check_time = current_time
                    except TimeoutException:
                        pass  # Không thấy mã QR, có thể đã quét rồi

                # Kiểm tra nếu mã QR được quét
                if not qr_scanned:
                    scanned, confirmation_text = self.check_qr_scanned()
                    if scanned:
                        qr_scanned = True
                        client.sendMessage(Message(
                            text=f"✅ Mã QR đã được quét! Đang chờ xác nhận đăng nhập...\n⏱️ Còn lại: {remaining_time}s"),
                            thread_id, thread_type, ttl=remaining_time * 1000)
                        print("✅ Mã QR đã được quét, chờ xác nhận...")
                        self.extract_imei_from_network()

                # Kiểm tra nếu đã login thành công
                if current_url != stable_url and "chat.zalo.me" in current_url:
                    client.sendMessage(Message(text="🎉 Đăng nhập thành công! Đang lưu cookie và IMEI..."), thread_id, thread_type, ttl=10000)
                    print("🎉 Đăng nhập thành công")
                    time.sleep(1)
                    success = self.extract_imei_and_cookies(client, thread_id, thread_type)
                    self.success = success
                    print(f"✅ Kết quả lưu cookie/IMEI: {success}")
                    return success

                time.sleep(check_interval)
            except Exception as e:
                print(f"❍ Lỗi theo dõi trạng thái: {str(e)}")
                time.sleep(check_interval)

        # Hết thời gian mà chưa đăng nhập
        if qr_scanned:
            client.sendMessage(Message(text=f"⏰ Hết thời gian chờ {max_wait_time}s - Đã quét QR nhưng chưa xác nhận."), thread_id, thread_type)
            print("⏰ Hết thời gian chờ - Đã quét QR nhưng chưa xác nhận")
        else:
            client.sendMessage(Message(text=f"⏰ Hết thời gian chờ {max_wait_time}s - Chưa quét QR."), thread_id, thread_type)
            print("⏰ Hết thời gian chờ - Chưa quét QR")
        return False

    def cleanup_session(self):
        """Dọn dẹp phiên trình duyệt."""
        print("🧹 Đang dọn dẹp phiên trình duyệt...")
        try:
            if self.driver:
                self.driver.delete_all_cookies()
                print("✅ Đã xóa tất cả cookie")
                self.driver.execute_script("localStorage.clear();")
                print("✅ Đã xóa localStorage")
                self.driver.execute_script("sessionStorage.clear();")
                print("✅ Đã xóa sessionStorage")
            print("✅ Đã dọn dẹp phiên trình duyệt")
        except Exception as e:
            print(f"⚠️ Lỗi dọn dẹp phiên: {str(e)}")

def handle_mybot_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh 'mybot' để tạo và quét mã QR."""
    print(f"📩 Nhận lệnh 'mybot' từ user {author_id}")
    try:
        client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
        print("✅ Phản ứng xác nhận lệnh được gửi")

        # Khởi tạo trình duyệt khi lệnh mybot được gọi
        if not initialize_browser():
            client.sendMessage(Message(text="❍ Hệ thống chưa sẵn sàng, vui lòng thử lại sau."), thread_id, thread_type)
            print("❍ Hệ thống chưa sẵn sàng")
            return

        if not acquire_browser(author_id):
            client.sendMessage(Message(text=f"⚠️ Trình duyệt đang được sử dụng bởi user {current_user_id}. Vui lòng đợi!"), thread_id, thread_type)
            print(f"⚠️ Trình duyệt đang được sử dụng bởi user {current_user_id}")
            return

        try:
            print(f"🔧 Khởi tạo ZaloQRScanner cho user {author_id}")
            scanner = ZaloQRScanner(author_id, browser)
            print("⏳ Đang làm mới và chờ mã QR...")
            qr_element = scanner.refresh_and_wait_for_qr()
            if not qr_element:
                client.sendMessage(Message(text="❍ Không thể tải mã QR."), thread_id, thread_type)
                print("❍ Không thể tải mã QR")
                return

            print("📷 Đang lấy hình ảnh mã QR...")
            qr_src = scanner.get_qr_code_image(qr_element, client, thread_id, thread_type, message_object)
            if not qr_src:
                client.sendMessage(Message(text="❍ Không thể lấy mã QR."), thread_id, thread_type)
                print("❍ Không thể lấy mã QR")
                return

            print("⏳ Bắt đầu theo dõi trạng thái đăng nhập...")
            scanner.monitor_login_status(client, thread_id, thread_type, message_object, qr_src=qr_src)
        finally:
            print("🧹 Bắt đầu dọn dẹp phiên...")
            scanner.cleanup_session()
            release_browser()
            close_browser()
            client.sendMessage(Message(text="🔓 Trình duyệt đã được giải phóng."), thread_id, thread_type, ttl=10000)
            print("✅ Đã gửi thông báo giải phóng trình duyệt")

    except Exception as e:
        client.sendMessage(Message(text=f"❍ Lỗi không xác định: {str(e)}"), thread_id, thread_type)
        print(f"❍ Lỗi không xác định: {str(e)}")
        if browser:
            release_browser()
            close_browser()

def get_mitaizl():
    """Thiết lập lệnh cho bot."""
    print("🚀 Đang thiết lập lệnh 'mybot'...")
    return {"getqrck": handle_mybot_command}