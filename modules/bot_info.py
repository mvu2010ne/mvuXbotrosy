import json, re, time, threading
from threading import Thread
from zlapi import ZaloAPI
from zlapi.models import *
from config import ADMIN, SUPER_ADMIN  # Import ADMIN từ config.py
import regex as re  # Cần cài đặt thư viện 'regex' (pip install regex)
import os
import random
import math
import logging
import requests
import shutil
import glob
from io import BytesIO
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
from nudenet import NudeDetector  # Thêm import NudeNet
import imageio
import cv2
import numpy as np
import colorsys  # Thêm colorsys để hỗ trợ viền cầu vồng
from pyzbar import pyzbar


SETTING_FILE, CONFIG_FILE = 'setting.json', 'config.json'
URL_REGEX = re.compile(r'http[s]?://(?:[a-zA-Z0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
# Thêm vào phần đầu của file, trong phần khai báo regex
PHONE_REGEX = re.compile(r'\b0\d{9}\b')
# Biểu thức regex để kiểm tra chuỗi chỉ chứa emoji (có thể tùy chỉnh thêm)
EMOJI_PATTERN = re.compile(r'^(?:\p{Emoji}|\p{Extended_Pictographic})+$')
# THÊM NGAY SAU DÒNG ĐÓ (sau dòng EMOJI_PATTERN):
STICKER_LIMIT_KEY = "sticker_limit_settings"
STICKER_BAN_KEY = "ban_sticker"  # Key cấm sticker hoàn toàn
REACTION_LIMIT_KEY = "reaction_limit_settings"  # Thêm key cho hạn chế reaction
sticker_limit_cache = {}  # Cache theo dõi số sticker người dùng gửi
reaction_limit_cache = {}  # Thêm cache cho reaction
MUTE_STICKER_KEY = "mute_sticker_users"
# Đường dẫn file lưu trữ danh sách nhóm bị loại khỏi sự kiện chào mừng
EXCLUDED_EVENTS_FILE = "excluded_event.json"
# Global cache dùng để kiểm tra nội dung tin nhắn trùng lặp
last_message_cache = {}
last_message_cache_lock = threading.Lock()  # Thêm lock cho biến toàn cục này
group_chat_status = {}  # Lưu trạng thái theo thread_id
# Khởi tạo NudeDetector
nude_detector = NudeDetector()

# -----------------------------------------
# Lớp SettingsManager: Quản lý việc đọc/ghi file settings
# -----------------------------------------
class SettingsManager:
    def __init__(self, filename=SETTING_FILE):
        self.filename = filename
        self.lock = threading.RLock()  # Sử dụng RLock để hỗ trợ giao dịch cập nhật nhiều bước
        self._cache = None

    def load(self):
        with self.lock:
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if not isinstance(data, dict):
                        logging.error("File settings không hợp lệ, khởi tạo mới")
                        data = {}
                    self._cache = data
            except (FileNotFoundError, json.JSONDecodeError) as e:
                logging.error(f"Lỗi khi tải settings: {e}")
                self._cache = {}
            return self._cache

    def save(self):
        with self.lock:
            try:
                with open(self.filename, 'w', encoding='utf-8') as f:
                    json.dump(self._cache, f, ensure_ascii=False, indent=4)
            except Exception as e:
                logging.error(f"Lỗi khi lưu settings: {e}")
                raise

    def atomic_update(self, update_fn):
        """Thực hiện cập nhật settings dưới 1 giao dịch duy nhất"""
        with self.lock:
            self.load()  # Tải settings hiện tại
            update_fn(self._cache)  # Thực hiện các thay đổi qua hàm callback
            self.save()

    def get(self, key, default=None):
        with self.lock:
            self.load()
            return self._cache.get(key, default)

    def update(self, key, value):
        self.atomic_update(lambda s: s.update({key: value}))

    def setdefault(self, key, default):
        with self.lock:
            self.load()
            result = self._cache.setdefault(key, default)
            self.save()
            return result

    def delete_key(self, key):
        with self.lock:
            self.load()
            if key in self._cache:
                del self._cache[key]
                self.save()

# Tạo instance settings_manager
settings_manager = SettingsManager()

# Thư mục lưu trữ bản sao lưu
BACKUP_FOLDER = 'backups'

# Đảm bảo thư mục backup tồn tại
if not os.path.exists(BACKUP_FOLDER):
    os.makedirs(BACKUP_FOLDER)

def create_backup():
    """Tạo bản sao lưu file setting.json với tên bao gồm thời gian."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = os.path.join(BACKUP_FOLDER, f"setting_backup_{timestamp}.json")
        shutil.copy(SETTING_FILE, backup_filename)
        logging.info(f"Đã tạo bản sao lưu: {backup_filename}")
        return f"✅ Đã tạo bản sao lưu: {backup_filename}"
    except Exception as e:
        logging.error(f"Lỗi khi tạo bản sao lưu: {e}")
        return f"⚠️ Lỗi khi tạo bản sao lưu: {str(e)}"

def restore_backup(backup_filename):
    """Khôi phục file setting.json từ bản sao lưu."""
    try:
        backup_path = os.path.join(BACKUP_FOLDER, backup_filename)
        if not os.path.exists(backup_path):
            return f"⚠️ File sao lưu {backup_filename} không tồn tại!"
        # Kiểm tra file JSON hợp lệ trước khi khôi phục
        with open(backup_path, 'r', encoding='utf-8') as f:
            json.load(f)  # Kiểm tra JSON hợp lệ
        shutil.copy(backup_path, SETTING_FILE)
        settings_manager.load()  # Tải lại settings vào cache
        logging.info(f"Đã khôi phục từ: {backup_filename}")
        return f"✅ Đã khôi phục settings từ: {backup_filename}"
    except json.JSONDecodeError:
        logging.error(f"File sao lưu {backup_filename} không hợp lệ")
        return f"⚠️ File sao lưu {backup_filename} không phải JSON hợp lệ!"
    except Exception as e:
        logging.error(f"Lỗi khi khôi phục bản sao lưu: {e}")
        return f"⚠️ Lỗi khi khôi phục: {str(e)}"

def list_backups():
    """Liệt kê các file sao lưu trong thư mục backups."""
    try:
        backup_files = glob.glob(os.path.join(BACKUP_FOLDER, "setting_backup_*.json"))
        if not backup_files:
            return "⚠️ Không có bản sao lưu nào!"
        backup_list = sorted([os.path.basename(f) for f in backup_files], reverse=True)
        return ("📋 Danh sách bản sao lưu:\n" +
                "\n".join(f"{i+1}. {f}" for i, f in enumerate(backup_list)))
    except Exception as e:
        logging.error(f"Lỗi khi liệt kê bản sao lưu: {e}")
        return f"⚠️ Lỗi khi liệt kê bản sao lưu: {str(e)}"

def delete_backup(backup_filename):
    """Xóa file sao lưu được chỉ định trong thư mục backups."""
    try:
        backup_path = os.path.join(BACKUP_FOLDER, backup_filename)
        if not os.path.exists(backup_path):
            return f"⚠️ File sao lưu {backup_filename} không tồn tại!"
        os.remove(backup_path)
        logging.info(f"Đã xóa bản sao lưu: {backup_filename}")
        return f"✅ Đã xóa bản sao lưu: {backup_filename}"
    except Exception as e:
        logging.error(f"Lỗi khi xóa bản sao lưu: {e}")
        return f"⚠️ Lỗi khi xóa bản sao lưu: {str(e)}"        

def read_settings():
    return settings_manager.load()

def write_settings(s):
    # Ghi đè toàn bộ settings (đã được cập nhật qua giao dịch atomic nếu cần)
    settings_manager.atomic_update(lambda cache: cache.update(s))

def load_message_log():
    return read_settings().get("message_log", {})

def save_message_log(log):
    def updater(s):
        s["message_log"] = log
    settings_manager.atomic_update(updater)

def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return config.get('imei'), config.get('cookies')
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"Error: File {CONFIG_FILE} không tồn tại hoặc định dạng không hợp lệ.")
        return None, None

# -----------------------------------------
# Các hàm xử lý tin nhắn
# -----------------------------------------
# Sửa hàm extract_message_text
def extract_message_text(msg_obj):
    if msg_obj.msgType == 'chat.sticker':
        return ""
    c = msg_obj.content
    text = ""
    if isinstance(c, dict):
        text += c.get('title', "")
        if 'description' in c:
            try:
                desc = c.get('description', "")
                if desc:
                    desc_json = json.loads(desc) if isinstance(desc, str) else desc
                    phone = desc_json.get('phone', "")
                    if phone:
                        text += " " + phone
            except (json.JSONDecodeError, TypeError):
                text += " " + str(c.get('description', ""))
    elif isinstance(c, str):
        text = c
    return text

get_content_message = extract_message_text

def is_url_in_message(msg_obj):
    return bool(URL_REGEX.search(extract_message_text(msg_obj)))

# -----------------------------------------
# Hàm kiểm soát spam (dựa trên message_log)
# -----------------------------------------
def is_spamming(author_id, thread_id):
    s = read_settings()
    spam_rule = s.get("rules", {}).get("spam", {"max_msgs": 5, "time_win": 5})
    max_msgs, time_win = spam_rule["max_msgs"], spam_rule["time_win"]
    log = load_message_log()
    key = f"{thread_id}_{author_id}"
    now = time.time()
    user_data = log.get(key, {"message_times": []})
    times = [t for t in user_data["message_times"] if now - t <= time_win]
    times.append(now)
    user_data["message_times"] = times
    log[key] = user_data
    save_message_log(log)
    return len(times) > max_msgs

# -----------------------------------------
# Các hàm quản lý admin, nhóm, từ cấm
# -----------------------------------------
# Hàm kiểm tra - dùng str() để an toàn với mọi kiểu dữ liệu UID
def is_super_admin(uid):
    """
    Kiểm tra xem uid có phải là SUPER_ADMIN duy nhất không.
    Luôn so sánh dưới dạng string.
    """
    if uid is None:
        return False
    return str(uid) == SUPER_ADMIN

def is_admin(author_id):
    """
    Thứ tự ưu tiên:
    1. SUPER_ADMIN (cao nhất, không thể bị override hay loại bỏ)
    2. ADMIN (danh sách cứng từ config)
    3. admin_bot (danh sách động từ setting.json)
    """
    if is_super_admin(author_id):
        return True
    
    author_str = str(author_id)
    if author_str in ADMIN:
        return True
    
    return author_str in read_settings().get("admin_bot", [])
    

def handle_bot_admin(bot):
    s = read_settings()
    admin_bot = s.get("admin_bot", [])
    if bot.uid not in admin_bot:
        admin_bot.append(bot.uid)
        s['admin_bot'] = admin_bot
        write_settings(s)
        print(f"Đã thêm {get_user_name_by_id(bot, bot.uid)} (ID: {bot.uid}) vào danh sách Admin BOT.")

def get_allowed_thread_ids():
    return read_settings().get('allowed_threads', [])

def toggle_group(bot, thread_id, enable=True):
    s = read_settings()
    allowed = s.get('allowed_threads', [])
    
    try:
        group = bot.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
        group_name = group.name
    except Exception as e:
        logging.error(f"Lỗi lấy thông tin nhóm {thread_id}: {e}")
        return "Không thể lấy thông tin nhóm!"

    # === TẮT BOT (TỰ ĐỘNG SETUP OFF) ===
    if not enable:
        if thread_id not in allowed:
            return f"⚠ Group {group_name} chưa được kích hoạt."
        
        # XÓA group_admins (như setup off)
        if 'group_admins' in s and thread_id in s['group_admins']:
            del s['group_admins'][thread_id]
            write_settings(s)
            logging.info(f"[SETUP OFF] Xóa quyền admin nhóm {thread_id}")

        # TẮT BOT
        allowed.remove(thread_id)
        s['allowed_threads'] = allowed
        write_settings(s)

        return (f"🚻: {group_name}\n"
                f"🆔: {thread_id}\n"
                f"❌ Bot đã TẮT\n"
                f"❌ Đã xóa cấu hình quyền")

    # === BẬT BOT (TỰ ĐỘNG SETUP ON) ===
    if thread_id in allowed:
        return f"⚠ Group {group_name} đã được bật trước đó."

    # BƯỚC 1: CẬP NHẬT group_admins – ĐÃ SỬA LỖI
    try:
        info = bot.fetchGroupInfo(thread_id)
        if thread_id not in info.gridInfoMap:
            return "Không tìm thấy nhóm!"
        
        group = info.gridInfoMap[thread_id]
        
        # Lấy danh sách admin được bổ nhiệm
        admins = group.adminIds or []
        
        # === THÊM TRƯỞNG NHÓM (creatorId) NẾU CHƯA CÓ TRONG DANH SÁCH ===
        creator_id = getattr(group, 'creatorId', None)  # Lấy creatorId nếu tồn tại
        if creator_id and creator_id not in admins:
            admins.append(creator_id)
            logging.info(f"[SETUP ON] Đã thêm trưởng nhóm (creatorId: {creator_id}) vào danh sách admin")
        
        # Lưu vào setting
        if 'group_admins' not in s:
            s['group_admins'] = {}
        s['group_admins'][thread_id] = admins
        write_settings(s)
        
        logging.info(f"[SETUP ON] Cập nhật thành công admin nhóm {thread_id}: {admins} (đã bao gồm trưởng nhóm)")

    except Exception as e:
        logging.error(f"Lỗi khi lấy thông tin nhóm hoặc lưu group_admins: {e}")
        return "❌ Lỗi khi cập nhật quyền quản trị viên"

    # BƯỚC 2: KIỂM TRA QUYỀN ADMIN
    if not check_admin_group(bot, thread_id):
        # XÓA group_admins nếu không có quyền
        if thread_id in s['group_admins']:
            del s['group_admins'][thread_id]
            write_settings(s)
        return (f"🚻: {group_name}\n"
                f"🆔: {thread_id}\n"
                f"❌ Bot KHÔNG THỂ BẬT\n"
                f"❌ Không có quyền Quản trị viên!\n"
                f"Gợi ý: Thêm @Bot làm Quản trị viên")

    # BƯỚC 3: BẬT BOT
    allowed.append(thread_id)
    s['allowed_threads'] = allowed
    write_settings(s)

    return (f"🚻: {group_name}\n"
            f"🆔: {thread_id}\n"
            f"✅ Bot đã BẬT\n"
            f"✅ Đã cập nhật quyền Quản trị viên")

def add_forbidden_word(word):
    s = read_settings()
    words = s.get('forbidden_words', [])
    if word not in words:
        words.append(word)
        s['forbidden_words'] = words
        write_settings(s)
        return f"✅ Từ '{word}' đã được thêm vào danh sách từ cấm."
    return f"⚠️️ Từ '{word}' đã tồn tại trong danh sách từ cấm."

def remove_forbidden_word(word):
    s = read_settings()
    words = s.get('forbidden_words', [])
    if word in words:
        words.remove(word)
        s['forbidden_words'] = words
        write_settings(s)
        return f"✅ Từ '{word}' đã được xóa khỏi danh sách từ cấm."
    return f"❌ Từ '{word}' không có trong danh sách từ cấm."

def is_forbidden_word(msg_obj):
    forbidden = read_settings().get('forbidden_words', [])
    content = extract_message_text(msg_obj).lower()
    if isinstance(msg_obj.content, dict):
        title = msg_obj.content.get('title', '').lower()
        return any(re.search(r'\b' + re.escape(word) + r'\b', content) or 
                   re.search(r'\b' + re.escape(word) + r'\b', title) for word in forbidden)
    return any(re.search(r'\b' + re.escape(word) + r'\b', content) for word in forbidden)

def setup_bot_on(bot, thread_id):
    try:
        # LẤY THÔNG TIN NHÓM MỚI NHẤT
        info = bot.fetchGroupInfo(thread_id)
        if thread_id not in info.gridInfoMap:
            return "Không tìm thấy nhóm!"

        group = info.gridInfoMap[thread_id]
        admins = group.adminIds or []  # Danh sách UID admin

        # LƯU VÀO CẤU HÌNH
        s = read_settings()
        if 'group_admins' not in s:
            s['group_admins'] = {}
        s['group_admins'][thread_id] = admins
        write_settings(s)

        # GHI LOG ĐỂ TEST
        logging.info(f"[SETUP] Cập nhật admin nhóm {thread_id}: {admins}")
        return "Đã cập nhật danh sách quản trị viên nhóm"
    except Exception as e:
        logging.error(f"[LỖI SETUP] {e}")
        return "Lỗi khi cập nhật quyền"

def setup_bot_off(bot, thread_id):
    group = bot.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
    s = read_settings()
    if s.get('group_admins', {}).pop(thread_id, None) is not None:
        write_settings(s)
        return f"⚙️ Cấu hình: 🔴 TẮT\n👥 {group.name}\n🆔 ID: {thread_id}"
    return f"⚙️ Cấu hình: 🔴 TẮT\n👥 {group.name}\n🆔 ID: {thread_id}\n❌ Không tìm thấy cấu hình quản trị cho nhóm này"
    
def reset_group_config(bot, thread_ids):
    """
    🧹 Xóa toàn bộ cấu hình của một hoặc nhiều nhóm.
    thread_ids: str hoặc list[str]
    """
    if isinstance(thread_ids, str):
        thread_ids = [thread_ids]
    
    thread_ids = [tid.strip() for tid in thread_ids if tid.strip().isdigit()]
    if not thread_ids:
        return "❌ ID nhóm không hợp lệ!"

    s = read_settings()
    results = ["🧹 RESET ĐA NHÓM"]
    results.append("════════════════════════")
    total_removed = 0

    for thread_id in thread_ids:
        group_name = "Không xác định"
        try:
            group = bot.fetchGroupInfo(thread_id).gridInfoMap.get(thread_id)
            group_name = group.name if group else "Không xác định"
        except:
            pass

        removed = False

        # 1. XÓA khỏi allowed_threads
        if 'allowed_threads' in s and thread_id in s['allowed_threads']:
            s['allowed_threads'].remove(thread_id)
            removed = True

        # 2. XÓA group_admins
        if 'group_admins' in s and thread_id in s['group_admins']:
            del s['group_admins'][thread_id]
            removed = True

        # 3. XÓA các ban settings
        ban_keys = [
            'ban_image', 'ban_video', 'ban_sticker', 'ban_gif', 'ban_sex', 'ban_file',
            'ban_voice', 'ban_emoji', 'ban_longmsg', 'ban_duplicate', 'ban_tag',
            'ban_word', 'ban_link', 'ban_contact_card', 'ban_phone', 'ban_vehinh','ban_stickerphoto'
        ]
        for key in ban_keys:
            if key in s and thread_id in s[key]:
                del s[key][thread_id]
                removed = True

        # 4. XÓA violations
        if 'violations' in s:
            violations = s['violations']
            keys_to_remove = [k for k in violations if k.startswith(f"{thread_id}_")]
            for k in keys_to_remove:
                del violations[k]
            if not violations:
                s.pop('violations', None)
            if keys_to_remove:
                removed = True

        # 5. XÓA block_user_group
        if 'block_user_group' in s and thread_id in s['block_user_group']:
            del s['block_user_group'][thread_id]
            removed = True

        # 6. XÓA muted_users
        if 'muted_users' in s:
            before_count = len(s['muted_users'])
            s['muted_users'] = [u for u in s['muted_users'] if u['thread_id'] != thread_id]
            if len(s['muted_users']) < before_count:
                removed = True

        # 7. XÓA excluded_event.json
        if os.path.exists(EXCLUDED_EVENTS_FILE):
            try:
                with open(EXCLUDED_EVENTS_FILE, 'r', encoding='utf-8') as f:
                    excluded = json.load(f)
                before_len = len(excluded)
                excluded = [g for g in excluded if g['group_id'] != thread_id]
                if len(excluded) < before_len:
                    removed = True
                with open(EXCLUDED_EVENTS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(excluded, f, ensure_ascii=False, indent=4)
            except:
                pass

        # Ghi lại settings (chỉ 1 lần sau vòng lặp)
        write_settings(s)

        # Kết quả từng nhóm
        if removed:
            results.append(f"📁 {group_name}")
            results.append(f"🆔 ID: {thread_id}")
            results.append("✅ ĐÃ XÓA HOÀN TOÀN")
            total_removed += 1
        else:
            results.append(f"📁 {group_name}")
            results.append(f"🆔 ID: {thread_id}")
            results.append("⚙️ Không có cấu hình")

        results.append("────────────────────────")

    results.append(f"📄 TỔNG: {total_removed}/{len(thread_ids)} nhóm đã được reset.")
    return "\n".join(results)

def reset_hidden_groups(bot):
    """Reset các nhóm KHÔNG lấy được tên (lỗi, nhóm ẩn, nhóm ma)"""
    s = read_settings()
    allowed_threads = s.get("allowed_threads", [])
    if not allowed_threads:
        return "Không có nhóm nào đang bật bot!"

    failed_groups = []

    for thread_id in allowed_threads:
        try:
            info = bot.fetchGroupInfo(thread_id)
            group = info.gridInfoMap.get(thread_id)
            if not (group and hasattr(group, 'name') and group.name):
                failed_groups.append(thread_id)
        except:
            failed_groups.append(thread_id)  # Lỗi API → coi như nhóm lỗi

    if not failed_groups:
        return "Tất cả nhóm đều hoạt động bình thường!"

    return reset_group_config(bot, failed_groups)

def check_admin_group(bot, thread_id):
    try:
        group_info = bot.fetchGroupInfo(thread_id).gridInfoMap.get(thread_id)
        if not group_info:
            logging.error(f"Không tìm thấy thông tin nhóm cho thread_id: {thread_id}")
            return False
        admin_ids = group_info.adminIds.copy()
        if group_info.creatorId not in admin_ids:
            admin_ids.append(group_info.creatorId)
        s = read_settings()
        s.setdefault('group_admins', {})[thread_id] = admin_ids
        write_settings(s)
        return bot.uid in admin_ids
    except Exception as e:
        logging.error(f"Lỗi khi kiểm tra quyền admin nhóm {thread_id}: {e}")
        return False

def get_ban_link_status(thread_id):
    return read_settings().get('ban_link', {}).get(thread_id, False)

def is_user_muted(author_id, thread_id):
    s = read_settings()
    now = time.time()
    for user in s.get("muted_users", []):
        if user["author_id"] == author_id and user["thread_id"] == thread_id and now < user["muted_until"]:
            return True
    return False

# -----------------------------------------
# Các hàm quản lý cấm media và link
# -----------------------------------------
def set_media_ban(thread_id, media_type, status):
    settings = read_settings()
    key = f"ban_{media_type}"
    group_settings = settings.get(key, {})
    if group_settings.get(thread_id) == status:
        return f"⚠️ {media_type.capitalize()} đã được {'bật' if status else 'tắt'} trước đó."
    group_settings[thread_id] = status
    settings[key] = group_settings
    write_settings(settings)
    return f"✅ Đã {'bật' if status else 'tắt'} cấm {media_type} trong nhóm."

def set_ban_link(thread_id, status):
    settings = read_settings()
    group_settings = settings.get('ban_link', {})
    if group_settings.get(thread_id) == status:
        return f"⚠️ Link đã được {'cấm' if status else 'cho phép'} trước đó."
    group_settings[thread_id] = status
    settings['ban_link'] = group_settings
    write_settings(settings)
    return f"✅ Đã {'cấm' if status else 'cho phép'} gửi link trong nhóm."

def is_image_message(msg_obj):
    return msg_obj.msgType == "chat.photo"

def is_video_message(msg_obj):
    return msg_obj.msgType == "chat.video.msg"

def is_sticker_message(msg_obj):
    return msg_obj.msgType == "chat.sticker"

def is_gif_message(msg_obj):
    return msg_obj.msgType == "chat.gif"

def is_file_message(msg_obj):
    return msg_obj.msgType in ["chat.file", "share.file", "chat.attachment", "chat.doc"]

def is_voice_message(msg_obj):
    return msg_obj.msgType == "chat.voice"
    
# Thêm vào phần các hàm kiểm tra loại tin nhắn
def is_contact_card_message(msg_obj):
    return msg_obj.msgType == "chat.recommended" and msg_obj.content.get("action") in ["recommended.user", "recommened.user"]

def is_phone_number_message(msg_obj):
    content = extract_message_text(msg_obj)
    if not isinstance(content, str):
        return False
    return bool(PHONE_REGEX.search(content.strip()))    

def is_emoji_message(msg_obj):
    content = extract_message_text(msg_obj).strip()
    if content and EMOJI_PATTERN.fullmatch(content):
        return True
    return False
 
def set_stickerphoto_ban(thread_id, status):
    """Cấm gửi sticker tự chế dưới dạng ảnh (pStickerType=1)"""
    settings = read_settings()
    key = "ban_stickerphoto"
    group_settings = settings.get(key, {})
    if group_settings.get(thread_id) == status:
        return f"Chế độ cấm sticker ảnh đã được {'bật' if status else 'tắt'} trước đó."
    group_settings[thread_id] = status
    settings[key] = group_settings
    write_settings(settings)
    return f"Đã {'bật' if status else 'tắt'} cấm gửi sticker ảnh (sticker tự chế)."

def is_stickerphoto_message(msg_obj):
    """
    Kiểm tra tin nhắn có phải sticker tự chế không (sticker gửi dưới dạng ảnh/video).
    Đã được cập nhật để bắt chính xác các loại sticker tự chế mới nhất 2025.
    """
    try:
        content = msg_obj.content
        if not isinstance(content, dict):
            return False

        href = content.get("href", "") or ""
        thumb = content.get("thumb", "") or ""
        params_str = content.get("params", "") or ""
        description = content.get("description", "") or ""
        title = content.get("title", "") or ""

        # ============================== ẢNH – chat.photo ==============================
        if msg_obj.msgType == "chat.photo":
            # 1. DẤU HIỆU CHÍNH THỨC MẠNH NHẤT: Zalo đánh dấu nội bộ @STICKER
            if hasattr(msg_obj, 'propertyExt') and msg_obj.propertyExt:
                ext = msg_obj.propertyExt.get('ext', '') or ""
                if '@STICKER' in ext:
                    print("[STICKERPHOTO DETECT] Ảnh – Bắt qua propertyExt: @STICKER")
                    return True

            # 2. Có webp trong params (dạng mới 2025, webp nằm sâu trong params)
            if 'webp' in params_str.lower() and not title and not description:
                print("[STICKERPHOTO DETECT] Ảnh – Bắt qua 'webp' trong params + không title/desc")
                return True

            # 3. Đuôi .webp trực tiếp trong href hoặc thumb + không title/desc
            if (".webp" in href.lower() or ".webp" in thumb.lower()) and not title and not description:
                print("[STICKERPHOTO DETECT] Ảnh – Bắt qua đuôi .webp (href/thumb) + không title/desc")
                return True

            # 4. Vuông nghiêm ngặt + không title/desc (bắt sticker cũ .jpg vuông như Pentol, Q-bie)
            try:
                import json
                params = json.loads(params_str) if params_str else {}
                width = int(params.get("width", 0))
                height = int(params.get("height", 0))
                if (width > 0 and height > 0 and
                    width <= 512 and height <= 512 and
                    abs(width - height) <= 20 and
                    not title and not description):
                    print(f"[STICKERPHOTO DETECT] Ảnh – Vuông nghiêm ngặt {width}x{height} + không title/desc")
                    return True
            except Exception as e:
                logging.debug(f"Lỗi parse params cho kiểm tra vuông: {e}")

            # 5. Các dấu hiệu cũ (giữ lại để tương thích)
            if "stickerCreatedBy" in href or "stickerCreatedBy" in thumb:
                print("[STICKERPHOTO DETECT] Ảnh – URL chứa stickerCreatedBy")
                return True

            if params_str and '"pStickerType":1' in params_str:
                print("[STICKERPHOTO DETECT] Ảnh – pStickerType=1")
                return True

            if re.search(r'"source"\s*:\s*7', params_str):
                print("[STICKERPHOTO DETECT] Ảnh – source=7")
                return True

            return False

        # ============================== VIDEO STICKER ==============================
        elif msg_obj.msgType == "chat.video.msg":
            if not params_str:
                return False

            duration_match = re.search(r'"duration"\s*:\s*(\d+)', params_str)
            width_match = re.search(r'"(?:video_original_width|video_width)"\s*:\s*(\d+)', params_str)
            height_match = re.search(r'"(?:video_original_height|video_height)"\s*:\s*(\d+)', params_str)
            file_size_match = re.search(r'"fileSize"\s*:\s*(\d+)', params_str)

            duration = int(duration_match.group(1)) if duration_match else 99999
            width = int(width_match.group(1)) if width_match else 0
            height = int(height_match.group(1)) if height_match else 0
            file_size = int(file_size_match.group(1)) if file_size_match else 9999999

            if (duration <= 8000 and
                width >= 150 and height >= 150 and
                abs(width - height) <= 150 and
                file_size < 4_000_000):
                print(f"[STICKERPHOTO DETECT] Video sticker – {width}x{height}, {duration}ms, {file_size} bytes")
                return True

            return False

    except Exception as e:
        logging.error(f"Lỗi trong is_stickerphoto_message: {e}")

    return False
    
def is_vehinh_message(msg_obj):
    return msg_obj.msgType == "chat.doodle"  

def set_sticker_limit_rule(thread_id, max_stickers, time_minutes):
    """Đặt quy tắc hạn chế sticker: số sticker trong số phút"""
    settings = read_settings()
    key = STICKER_LIMIT_KEY
    
    if 'group_settings' not in settings.setdefault(key, {}):
        settings[key]['group_settings'] = {}
    
    settings[key]['group_settings'][thread_id] = {
        'max_stickers': max_stickers,
        'time_minutes': time_minutes,
        'enabled': True,
        'time_seconds': time_minutes * 60
    }
    
    write_settings(settings)
    return f"✅ Đã đặt quy tắc: {max_stickers} sticker trong {time_minutes} phút"

def get_sticker_limit_rule(thread_id):
    """Lấy quy tắc hạn chế sticker của nhóm"""
    settings = read_settings()
    key = STICKER_LIMIT_KEY
    
    if key not in settings or 'group_settings' not in settings[key]:
        return None
    
    return settings[key]['group_settings'].get(thread_id)

def set_sticker_limit_enabled(thread_id, enabled):
    """Bật/tắt chế độ hạn chế sticker"""
    settings = read_settings()
    key = STICKER_LIMIT_KEY
    
    if key not in settings or 'group_settings' not in settings[key]:
        return f"⚠️ Chưa có quy tắc hạn chế sticker. Dùng: bott stickerlimit rule 2 5"
    
    if thread_id not in settings[key]['group_settings']:
        return f"⚠️ Chưa có quy tắc hạn chế sticker. Dùng: bott stickerlimit rule 2 5"
    
    settings[key]['group_settings'][thread_id]['enabled'] = enabled
    write_settings(settings)
    
    status = "BẬT" if enabled else "TẮT"
    return f"✅ Đã {status.lower()} chế độ hạn chế sticker"

def is_sticker_limit_enabled(thread_id):
    """Kiểm tra xem chế độ hạn chế sticker có bật không"""
    rule = get_sticker_limit_rule(thread_id)
    return rule and rule.get('enabled', False)

def handle_sticker_limit(bot, author_id, thread_id, msg_obj, thread_type):
    """Xử lý hạn chế sticker theo quy tắc + mute khi gửi 5 sticker liên tục + mention @user"""
    print(f"[STICKER LIMIT] Kiểm tra sticker từ user {author_id} trong nhóm {thread_id}")
    
    if not is_sticker_limit_enabled(thread_id):
        print(f"[STICKER LIMIT] Chế độ hạn chế sticker TẮT cho nhóm {thread_id}")
        return False
  
    if author_id == bot.uid or is_admin(author_id):
        print(f"[STICKER LIMIT] Bỏ qua: user {author_id} là bot hoặc admin")
        return False
  
    if not (is_sticker_message(msg_obj) or is_stickerphoto_message(msg_obj)):
        print(f"[STICKER LIMIT] Không phải sticker → bỏ qua")
        return False
  
    rule = get_sticker_limit_rule(thread_id)
    if not rule:
        print(f"[STICKER LIMIT] Không tìm thấy quy tắc cho nhóm {thread_id}")
        return False
    
    max_stickers = rule['max_stickers']
    time_seconds = rule['time_seconds']
    now = time.time()
    cache_key = f"{thread_id}_{author_id}"
  
    if cache_key not in sticker_limit_cache:
        sticker_limit_cache[cache_key] = {
            "count": 0,
            "last_warning_time": 0,
            "first_sticker_time": now,
            "stickers": [],
            "first_warning_sent": False,
            "consecutive_stickers": 0,
            "last_message_was_sticker": False
        }
  
    user_data = sticker_limit_cache[cache_key]
    
    # Dọn timestamp cũ
    user_data["stickers"] = [t for t in user_data["stickers"] if now - t <= time_seconds]
    user_data["count"] = len(user_data["stickers"])
    
    # Đếm sticker liên tục
    if user_data.get("last_message_was_sticker", False):
        user_data["consecutive_stickers"] += 1
    else:
        user_data["consecutive_stickers"] = 1
    user_data["last_message_was_sticker"] = True
    
    # Thêm sticker mới
    user_data["stickers"].append(now)
    user_data["count"] = len(user_data["stickers"])
    sticker_count = user_data["count"]

    # === LẤY TÊN NGƯỜI DÙNG ĐỂ MENTION ===
    try:
        user_info = bot.fetchUserInfo(author_id)
        user_name = user_info.changed_profiles.get(author_id)
        display_name = user.zaloName if user and hasattr(user, 'zaloName') else "Bạn"
    except:
        display_name = "Bạn"

    # Tạo chuỗi có @Tên để mention
    mention_text = f"@{display_name}"
    # UID thật (trong Zalo đôi khi là "12345_abc" → chỉ lấy phần trước)
    real_uid = author_id.split('_')[0] if '_' in author_id else author_id

    # === CẢNH BÁO LẦN 1 (khi gửi 2 sticker) ===
    if sticker_count == 2 and not user_data.get("first_warning_sent", False):
        warning_msg = f"{mention_text} ơi! Bớt gửi sticker đi nha\nChỉ được gửi tối đa {max_stickers} sticker trong {rule['time_minutes']} phút thôi!"
        
        mention = Mention(uid=real_uid, offset=0, length=len(mention_text))
        message = Message(text=warning_msg, mention=mention)
        
        bot.replyMessage(message, msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=300000)
        user_data["first_warning_sent"] = True
        user_data["last_warning_time"] = now

    # === KHI ĐẠT ĐỦ SỐ LƯỢNG CHO PHÉP ===
    elif sticker_count == max_stickers and now - user_data["last_warning_time"] > 60:
        time_left = int((min(user_data["stickers"]) + time_seconds - now) / 60) + 1
        warning_msg = f"{mention_text} đã gửi đủ {max_stickers} sticker rồi!\nChờ {time_left} phút nữa mới được gửi tiếp nha!"
        
        mention = Mention(uid=real_uid, offset=0, length=len(mention_text))
        message = Message(text=warning_msg, mention=mention)
        
        bot.replyMessage(message, msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=300000)
        user_data["last_warning_time"] = now

    # === VƯỢT QUÁ GIỚI HẠN → XÓA + CẢNH BÁO ===
    if sticker_count > max_stickers:
        try:
            bot.deleteGroupMsg(msg_obj.msgId, author_id, msg_obj.cliMsgId, thread_id)
            print(f"[STICKER LIMIT] Đã xóa sticker vượt giới hạn của {author_id}")
        except Exception as e:
            logging.error(f"Lỗi xóa sticker: {e}")

        if now - user_data["last_warning_time"] > 30:
            remaining = sticker_count - max_stickers
            time_left = int((min(user_data["stickers"]) + time_seconds - now) / 60) + 1
            warning_msg = (
                f"{mention_text} ơi, đã vượt quá {remaining} sticker rồi!\n"
                f"Quy định chỉ {max_stickers} sticker/{rule['time_minutes']} phút thôi!\n"
                f"Chờ {time_left} phút nữa nhé!"
            )
            
            mention = Mention(uid=real_uid, offset=0, length=len(mention_text))
            message = Message(text=warning_msg, mention=mention)
            
            bot.replyMessage(message, msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=300000)
            user_data["last_warning_time"] = now

        sticker_limit_cache[cache_key] = user_data
        return True  # Đã xử lý (xóa + cảnh báo)

    # Lưu cache + dọn dẹp định kỳ
    sticker_limit_cache[cache_key] = user_data
    if random.random() < 0.01:
        cleanup_sticker_limit_cache(time_seconds * 2)

    return False
    
def set_reaction_limit_rule(thread_id, max_reactions, time_minutes):
    """Đặt quy tắc hạn chế reaction: số reaction trong số phút"""
    settings = read_settings()
    key = REACTION_LIMIT_KEY
    
    if 'group_settings' not in settings.setdefault(key, {}):
        settings[key]['group_settings'] = {}
    
    settings[key]['group_settings'][thread_id] = {
        'max_reactions': max_reactions,
        'time_minutes': time_minutes,
        'enabled': True,
        'time_seconds': time_minutes * 60
    }
    
    write_settings(settings)
    return f"✅ Đã đặt quy tắc: {max_reactions} reaction trong {time_minutes} phút"

def get_reaction_limit_rule(thread_id):
    """Lấy quy tắc hạn chế reaction của nhóm"""
    settings = read_settings()
    key = REACTION_LIMIT_KEY
    
    if key not in settings or 'group_settings' not in settings[key]:
        return None
    
    return settings[key]['group_settings'].get(thread_id)

def set_reaction_limit_enabled(thread_id, enabled):
    """Bật/tắt chế độ hạn chế reaction"""
    settings = read_settings()
    key = REACTION_LIMIT_KEY
    
    if key not in settings or 'group_settings' not in settings[key]:
        return f"⚠️ Chưa có quy tắc hạn chế reaction. Dùng: bott reactionlimit rule 5 1"
    
    if thread_id not in settings[key]['group_settings']:
        return f"⚠️ Chưa có quy tắc hạn chế reaction. Dùng: bott reactionlimit rule 5 1"
    
    settings[key]['group_settings'][thread_id]['enabled'] = enabled
    write_settings(settings)
    
    status = "BẬT" if enabled else "TẮT"
    return f"✅ Đã {status.lower()} chế độ hạn chế reaction"

def is_reaction_limit_enabled(thread_id):
    """Kiểm tra xem chế độ hạn chế reaction có bật không"""
    rule = get_reaction_limit_rule(thread_id)
    return rule and rule.get('enabled', False)

def handle_reaction_limit(bot, author_id, thread_id, msg_obj, thread_type):
    """Xử lý hạn chế reaction theo quy tắc + cảnh báo và xử phạt khi vượt giới hạn"""
    print(f"[REACTION LIMIT] Kiểm tra reaction từ user {author_id} trong nhóm {thread_id}")
    
    # Kiểm tra nếu là tin nhắn reaction
    if msg_obj.msgType != 'chat.reaction':
        print(f"[REACTION LIMIT] Không phải reaction → bỏ qua")
        return False
    
    if not is_reaction_limit_enabled(thread_id):
        print(f"[REACTION LIMIT] Chế độ hạn chế reaction TẮT cho nhóm {thread_id}")
        return False
  
    if author_id == bot.uid or is_admin(author_id):
        print(f"[REACTION LIMIT] Bỏ qua: user {author_id} là bot hoặc admin")
        return False
  
    rule = get_reaction_limit_rule(thread_id)
    if not rule:
        print(f"[REACTION LIMIT] Không tìm thấy quy tắc cho nhóm {thread_id}")
        return False
    
    max_reactions = rule['max_reactions']
    time_seconds = rule['time_seconds']
    now = time.time()
    cache_key = f"{thread_id}_{author_id}_reaction"
  
    if cache_key not in reaction_limit_cache:
        reaction_limit_cache[cache_key] = {
            "count": 0,
            "last_warning_time": 0,
            "first_reaction_time": now,
            "reactions": [],
            "first_warning_sent": False,
            "consecutive_reactions": 0,
            "last_action_was_reaction": False
        }
  
    user_data = reaction_limit_cache[cache_key]
    
    # Dọn timestamp cũ
    user_data["reactions"] = [t for t in user_data["reactions"] if now - t <= time_seconds]
    user_data["count"] = len(user_data["reactions"])
    
    # Đếm reaction liên tục
    if user_data.get("last_action_was_reaction", False):
        user_data["consecutive_reactions"] += 1
    else:
        user_data["consecutive_reactions"] = 1
    user_data["last_action_was_reaction"] = True
    
    # Thêm reaction mới
    user_data["reactions"].append(now)
    user_data["count"] = len(user_data["reactions"])
    reaction_count = user_data["count"]

    # === LẤY TÊN NGƯỜI DÙNG ĐỂ MENTION ===
    try:
        user_info = bot.fetchUserInfo(author_id)
        user_name = user_info.changed_profiles.get(author_id)
        display_name = user_name.zaloName if user_name and hasattr(user_name, 'zaloName') else "Bạn"
    except:
        display_name = "Bạn"

    # Tạo chuỗi có @Tên để mention
    mention_text = f"@{display_name}"
    # UID thật (trong Zalo đôi khi là "12345_abc" → chỉ lấy phần trước)
    real_uid = author_id.split('_')[0] if '_' in author_id else author_id

    # === CẢNH BÁO LẦN 1 (khi gửi 3 reaction) ===
    if reaction_count == 3 and not user_data.get("first_warning_sent", False):
        warning_msg = f"{mention_text} ⚠️ Bạn đang spam! Nếu tiếp tục, bạn sẽ bị sút."
        
        mention = Mention(uid=real_uid, offset=0, length=len(mention_text))
        message = Message(text=warning_msg, mention=mention)
        
        bot.replyMessage(message, msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=300000)
        user_data["first_warning_sent"] = True
        user_data["last_warning_time"] = now

    # === KHI ĐẠT ĐỦ SỐ LƯỢNG CHO PHÉP ===
    elif reaction_count == max_reactions and now - user_data["last_warning_time"] > 60:
        time_left = int((min(user_data["reactions"]) + time_seconds - now) / 60) + 1
        warning_msg = f"{mention_text} ⚠️ Bạn đang spam! Nếu tiếp tục, bạn sẽ bị sút."
        
        mention = Mention(uid=real_uid, offset=0, length=len(mention_text))
        message = Message(text=warning_msg, mention=mention)
        
        bot.replyMessage(message, msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=300000)
        user_data["last_warning_time"] = now

    # === VƯỢT QUÁ GIỚI HẠN → XÓA + CẢNH BÁO + CHẶN ===
    if reaction_count > max_reactions:
        # Xóa reaction hiện tại
        try:
            # Lấy message ID từ reaction để xóa
            target_msg_id = msg_obj.content.get('msgId') if isinstance(msg_obj.content, dict) else None
            if target_msg_id:
                bot.deleteGroupMsg(msg_obj.msgId, author_id, msg_obj.cliMsgId, thread_id)
                print(f"[REACTION LIMIT] Đã xóa reaction vượt giới hạn của {author_id}")
        except Exception as e:
            logging.error(f"Lỗi xóa reaction: {e}")

        if now - user_data["last_warning_time"] > 30:
            remaining = reaction_count - max_reactions
            time_left = int((min(user_data["reactions"]) + time_seconds - now) / 60) + 1
            warning_msg = (
                f"{mention_text} ơi, đã vượt quá {remaining} reaction rồi!\n"
                f"Quy định chỉ {max_reactions} reaction/{rule['time_minutes']} phút thôi!\n"
                f"Đã bị chặn khỏi nhóm do vi phạm nhiều lần!"
            )
            
            mention = Mention(uid=real_uid, offset=0, length=len(mention_text))
            message = Message(text=warning_msg, mention=mention)
            
            bot.replyMessage(message, msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=300000)
            user_data["last_warning_time"] = now
            
            # CHẶN NGƯỜI DÙNG KHỎI NHÓM NẾU VƯỢT QUÁ 5 REACTION
            if reaction_count >= max_reactions + 5 and check_admin_group(bot, thread_id):
                try:
                    bot.kickUsersInGroup(author_id, thread_id)
                    time.sleep(1)
                    bot.blockUsersInGroup(author_id, thread_id)
                    block_msg = f"🚫 {display_name} đã bị chặn khỏi nhóm do spam reaction quá nhiều!"
                    bot.replyMessage(Message(text=block_msg), msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=300000)
                    print(f"[REACTION LIMIT] Đã chặn {author_id} khỏi nhóm do spam reaction")
                except Exception as e:
                    logging.error(f"Lỗi khi chặn người dùng {author_id} khỏi nhóm: {e}")

        reaction_limit_cache[cache_key] = user_data
        return True  # Đã xử lý (xóa + cảnh báo + chặn)

    # Lưu cache + dọn dẹp định kỳ
    reaction_limit_cache[cache_key] = user_data
    if random.random() < 0.01:
        cleanup_reaction_limit_cache(time_seconds * 2)

    return False

def cleanup_reaction_limit_cache(max_age_seconds=1200):
    """Dọn dẹp cache reaction limit cũ"""
    now = time.time()
    keys_to_remove = []
    
    for key, data in reaction_limit_cache.items():
        if not data.get("reactions"):
            keys_to_remove.append(key)
        elif now - max(data.get("reactions", [now])) > max_age_seconds:
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del reaction_limit_cache[key]

def show_reaction_limit_status(thread_id):
    """Hiển thị trạng thái hạn chế reaction"""
    rule = get_reaction_limit_rule(thread_id)
    
    if not rule:
        return "❌ Chưa có quy tắc hạn chế reaction. Dùng: bott reactionlimit rule 5 1"
    
    status = "✅ BẬT" if rule['enabled'] else "❌ TẮT"
    return (f"👍 Trạng thái hạn chế reaction: {status}\n"
            f"📊 Quy tắc: {rule['max_reactions']} reaction trong {rule['time_minutes']} phút\n"
            f"⚙️ Dùng: bott reactionlimit on/off để bật/tắt\n"
            f"⚠️ Vượt quá {rule['max_reactions'] + 5} reaction sẽ bị chặn khỏi nhóm!")    

def cleanup_sticker_limit_cache(max_age_seconds=1200):
    """Dọn dẹp cache sticker limit cũ"""
    now = time.time()
    keys_to_remove = []
    
    for key, data in sticker_limit_cache.items():
        if not data.get("stickers"):
            keys_to_remove.append(key)
        elif now - max(data.get("stickers", [now])) > max_age_seconds:
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del sticker_limit_cache[key]

def show_sticker_limit_status(thread_id):
    """Hiển thị trạng thái hạn chế sticker"""
    rule = get_sticker_limit_rule(thread_id)
    
    if not rule:
        return "❌ Chưa có quy tắc hạn chế sticker. Dùng: bott stickerlimit rule 2 5"
    
    status = "✅ BẬT" if rule['enabled'] else "❌ TẮT"
    return (f"🎭 Trạng thái hạn chế sticker: {status}\n"
            f"📊 Quy tắc: {rule['max_stickers']} sticker trong {rule['time_minutes']} phút\n"
            f"⚙️ Dùng: bott stickerlimit on/off để bật/tắt")    

SEX_KEYWORDS = ["sex", "nude", "porn", "xxx"]

MAX_CACHE_SIZE = 1000
nude_check_cache = {}
def is_sex_image(msg_obj):
    """
    Kiểm tra nội dung nhạy cảm trong ảnh, GIF hoặc video sử dụng NudeNet.
    Trả về: (is_nude, reason, score, level)
    """
    caption = extract_message_text(msg_obj)
    # Kiểm tra từ khóa nhạy cảm trong caption
    for keyword in SEX_KEYWORDS:
        if keyword.lower() in caption.lower():
            print(f"Phát hiện từ khóa nhạy cảm trong caption: {keyword}")
            return True, "Từ khóa nhạy cảm trong caption", 100, "high"
    
    if msg_obj.msgType in ["chat.photo", "chat.gif", "chat.video.msg"]:
        media_url = msg_obj.content.get('href', '')
        if not media_url:
            print("Không tìm thấy URL media trong message object")
            logging.warning("Không tìm thấy URL media trong msg_obj")
            return False, "Không có URL media", 0, "none"
        
        try:
            # Tải media từ URL
            response = requests.get(media_url, timeout=10)
            response.raise_for_status()
            content_type = response.headers.get('Content-Type', '').lower()
            
            temp_files = []
            if 'image' in content_type and msg_obj.msgType == "chat.photo":
                # Xử lý ảnh
                image = Image.open(BytesIO(response.content))
                temp_image_path = f"temp_image_{msg_obj.msgId}.jpg"
                image.save(temp_image_path, format="JPEG")
                temp_files.append(temp_image_path)
            elif 'image/gif' in content_type or msg_obj.msgType == "chat.gif":
                # Xử lý GIF
                temp_gif_path = f"temp_gif_{msg_obj.msgId}.gif"
                with open(temp_gif_path, "wb") as f:
                    f.write(response.content)
                gif = imageio.mimread(temp_gif_path)
                total_frames = len(gif)
                # Lấy 3 khung: đầu, giữa, cuối
                frame_indices = [0, total_frames // 2, total_frames - 1] if total_frames >= 3 else list(range(total_frames))
                frames = [gif[i] for i in frame_indices]
                for i, frame in enumerate(frames):
                    # Chuyển đổi khung hình thành PIL Image và đảm bảo chế độ RGB
                    pil_image = Image.fromarray(frame)
                    if pil_image.mode == 'RGBA':
                        pil_image = pil_image.convert('RGB')
                    temp_image_path = f"temp_gif_frame_{msg_obj.msgId}_{i}.jpg"
                    pil_image.save(temp_image_path, format="JPEG")
                    temp_files.append(temp_image_path)
                os.remove(temp_gif_path)  # Xóa file GIF tạm
            elif 'video' in content_type or msg_obj.msgType == "chat.video.msg":
                # Xử lý video
                temp_video_path = f"temp_video_{msg_obj.msgId}.mp4"
                with open(temp_video_path, "wb") as f:
                    f.write(response.content)
                cap = cv2.VideoCapture(temp_video_path)
                if not cap.isOpened():
                    os.remove(temp_video_path)
                    return False, "Không thể mở video", 0, "none"
                
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                # Lấy 3 khung: đầu, giữa, cuối
                frame_indices = [0, total_frames // 2, total_frames - 1] if total_frames >= 3 else list(range(total_frames))
                for i, frame_idx in enumerate(frame_indices):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                    ret, frame = cap.read()
                    if ret:
                        temp_image_path = f"temp_video_frame_{msg_obj.msgId}_{i}.jpg"
                        cv2.imwrite(temp_image_path, frame)
                        temp_files.append(temp_image_path)
                
                cap.release()
                os.remove(temp_video_path)  # Xóa file video tạm
            
            if not temp_files:
                return False, "Không thể xử lý media", 0, "none"
            
            # Các nhãn nhạy cảm từ NudeNet
            sensitive_labels = [
                'BUTTOCKS_EXPOSED', 'FEMALE_BREAST_EXPOSED', 'MALE_GENITALIA_EXPOSED',
                'FEMALE_GENITALIA_EXPOSED', 'ANUS_EXPOSED', 'BUTTOCKS', 'FEMALE_BREAST',
                'BELLY', 'ARMPIT'
            ]
            
            # Phân tích tất cả khung hình
            max_score = 0
            reasons = []
            is_nude = False
            
            for i, temp_image_path in enumerate(temp_files):
                results = nude_detector.detect(temp_image_path)
                frame_reasons = []
                
                for detection in results:
                    label = detection['class']
                    score = detection['score']
                    if label in sensitive_labels and score > 0.1:  # Ngưỡng 0.1
                        vietnamese_label = {
                            'BUTTOCKS_EXPOSED': 'Mông lộ rõ',
                            'FEMALE_BREAST_EXPOSED': 'Ngực nữ lộ rõ',
                            'MALE_GENITALIA_EXPOSED': 'Bộ phận sinh dục nam lộ rõ',
                            'FEMALE_GENITALIA_EXPOSED': 'Bộ phận sinh dục nữ lộ rõ',
                            'ANUS_EXPOSED': 'Hậu môn lộ rõ',
                            'BUTTOCKS': 'Mông',
                            'FEMALE_BREAST': 'Ngực nữ',
                            'BELLY': 'Bụng',
                            'ARMPIT': 'Nách'
                        }.get(label, label)
                        frame_reasons.append(f"{vietnamese_label}: Xác suất {score*100:.0f}%")
                        max_score = max(max_score, score)
                        is_nude = True
                
                if frame_reasons:
                    frame_name = f"Khung hình {i+1}" if len(temp_files) > 1 else "Ảnh"
                    reasons.append(f"{frame_name}:\n" + "\n".join(frame_reasons))
                
                # Xóa file tạm ngay sau khi xử lý
                if os.path.exists(temp_image_path):
                    os.remove(temp_image_path)
            
            reason = "\n".join(reasons) if reasons else "Media không nhạy cảm"
            nude_level = "high" if max_score > 0.8 else "medium" if max_score > 0.5 else "low"
            
            print(f"Kết quả NudeNet cho {media_url}: is_nude={is_nude}, reason={reason}, score={max_score*100:.0f}, level={nude_level}")
            if is_nude:
                logging.info(f"NudeNet phát hiện media nhạy cảm: {media_url}, score: {max_score*100:.0f}%, reason: {reason}")
            
            return is_nude, reason, max_score*100, nude_level
        
        except Exception as e:
            print(f"Lỗi khi xử lý media {media_url}: {str(e)}")
            logging.error(f"Lỗi khi kiểm tra media với NudeNet: {e}")
            # Xóa bất kỳ file tạm nào còn sót lại
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            return False, f"Lỗi xử lý media: {str(e)}", 0, "none"
    
    return False, "Không phải tin nhắn media", 0, "none"

def has_qr_code_in_media(msg_obj):
    print(f"[QR CHECK] Bắt đầu kiểm tra QR cho msgId: {msg_obj.msgId}, type: {msg_obj.msgType}")
    if msg_obj.msgType not in ["chat.photo", "chat.gif"]:
        print(f"[QR CHECK] Không phải ảnh/GIF → bỏ qua")
        return False, None, None
    media_url = msg_obj.content.get('href', '')
    if not media_url:
        print(f"[QR CHECK] Không có URL media → bỏ qua")
        return False, None, None
    try:
        print(f"[QR CHECK] Đang tải media từ: {media_url}")
        r = requests.get(media_url, timeout=10)
        r.raise_for_status()
        path = f"temp_qr_{msg_obj.msgId}.jpg"
        with open(path, "wb") as f: f.write(r.content)
        print(f"[QR CHECK] Đã lưu tạm: {path}")

        if msg_obj.msgType == "chat.gif":
            gif = imageio.mimread(path)
            if gif:
                Image.fromarray(gif[0]).save(path)
                print(f"[QR CHECK] GIF → chỉ kiểm tra frame đầu")

        has_qr, data = is_qr_in_image(path)
        if has_qr:
            print(f"[QR DETECTED] Phát hiện QR: {data}")
        else:
            print(f"[QR CHECK] Không tìm thấy QR")
        return has_qr, data, path
    except Exception as e:
        print(f"[QR ERROR] Lỗi kiểm tra QR: {e}")
        logging.error(f"Lỗi kiểm tra QR: {e}")
        return False, None, None

def is_qr_in_image(image_path):
    """
    Kiểm tra ảnh có chứa mã QR không.
    Trả về: (has_qr: bool, qr_data: str hoặc None)
    """
    print(f"[QR SCAN] Đang quét QR trong ảnh: {image_path}")
    try:
        image = cv2.imread(image_path)
        if image is None:
            print(f"[QR ERROR] Không đọc được ảnh: {image_path}")
            return False, None
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        qr_codes = pyzbar.decode(gray)
        if qr_codes:
            data = qr_codes[0].data.decode('utf-8')
            print(f"[QR FOUND] Phát hiện mã QR: {data}")
            return True, data
        else:
            print(f"[QR SCAN] Không tìm thấy QR trong ảnh")
            return False, None
    except Exception as e:
        print(f"[QR ERROR] Lỗi khi quét QR: {e}")
        logging.error(f"Lỗi quét QR trong {image_path}: {e}")
        return False, None

def handle_media_content(bot, author_id, thread_id, msg_obj, thread_type):
    if author_id == bot.uid:
        return
    if is_admin(author_id):
        return    
    if is_user_muted(author_id, thread_id):
        bot.deleteGroupMsg(msg_obj.msgId, author_id, msg_obj.cliMsgId, thread_id)
        return        
    s = read_settings()
    if author_id in s.get("excluded_users", []):
        return
    if (is_sticker_message(msg_obj) or is_stickerphoto_message(msg_obj)) and is_mute_sticker_user(thread_id, author_id):
        bot.deleteGroupMsg(msg_obj.msgId, author_id, msg_obj.cliMsgId, thread_id)
        bot.replyMessage(
            Message(text="⚠️ Bạn đã bị cấm gửi sticker trong nhóm này!"),
            msg_obj,
            thread_id=thread_id,
            thread_type=thread_type,
            ttl=10000
        )
        return True  # Thoát ngay, không xử lý limit hay ban nhóm nữa    
    if is_sticker_message(msg_obj) or is_stickerphoto_message(msg_obj):
        handle_sticker_limit(bot, author_id, thread_id, msg_obj, thread_type)
# Đã xử lý (cảnh báo + xóa) → thoát sớm, không check gì nữa        
    settings = read_settings()
    if settings.get("ban_contact_card", {}).get(thread_id, False) and is_contact_card_message(msg_obj):
        bot.deleteGroupMsg(msg_obj.msgId, author_id, msg_obj.cliMsgId, thread_id)
        return True
    if settings.get("ban_phone", {}).get(thread_id, False) and is_phone_number_message(msg_obj):
        bot.deleteGroupMsg(msg_obj.msgId, author_id, msg_obj.cliMsgId, thread_id)
        return True
    # === XỬ LÝ ẢNH & GIF ===
    if is_image_message(msg_obj) or is_gif_message(msg_obj):
        # 1. Cấm ảnh hoàn toàn
        if settings.get("ban_image", {}).get(thread_id, False):
            bot.deleteGroupMsg(msg_obj.msgId, author_id, msg_obj.cliMsgId, thread_id)
            return True

        # 2. Cấm link → kiểm tra QR trước
    if get_ban_link_status(thread_id):
        print(f"[BAN_LINK] Đang kiểm tra QR do ban_link = ON")
        has_qr, qr_data, temp_path = has_qr_code_in_media(msg_obj)
        if has_qr:
            print(f"[ACTION] XÓA ẢNH/GIF CHỨA QR - User: {author_id}, msgId: {msg_obj.msgId}")
            bot.deleteGroupMsg(msg_obj.msgId, author_id, msg_obj.cliMsgId, thread_id)
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
                print(f"[CLEANUP] Đã xóa file tạm: {temp_path}")
            return True
        else:
            print(f"[PASS] Không có QR → cho phép ảnh/GIF")
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
            print(f"[CLEANUP] Đã xóa file tạm (không QR): {temp_path}")
    if settings.get("ban_video", {}).get(thread_id, False) and is_video_message(msg_obj):
        bot.deleteGroupMsg(msg_obj.msgId, author_id, msg_obj.cliMsgId, thread_id)
        return True
        # === XỬ LÝ STICKER THƯỜNG + STICKERPHO TO (tự chế) ===
    

    # Nếu không vượt limit, mới kiểm tra cấm riêng (nếu có bật)
    if is_sticker_message(msg_obj) and settings.get("ban_sticker", {}).get(thread_id, False):
        bot.deleteGroupMsg(msg_obj.msgId, author_id, msg_obj.cliMsgId, thread_id)
        return True

    if is_stickerphoto_message(msg_obj) and settings.get("ban_stickerphoto", {}).get(thread_id, False):
        bot.deleteGroupMsg(msg_obj.msgId, author_id, msg_obj.cliMsgId, thread_id)
        return True
    if settings.get("ban_gif", {}).get(thread_id, False) and is_gif_message(msg_obj):
        bot.deleteGroupMsg(msg_obj.msgId, author_id, msg_obj.cliMsgId, thread_id)
        return True
    if settings.get("ban_stickerphoto", {}).get(thread_id, False) and is_stickerphoto_message(msg_obj):
        bot.deleteGroupMsg(msg_obj.msgId, author_id, msg_obj.cliMsgId, thread_id)
        return True    
    if settings.get("ban_sex", {}).get(thread_id, False) and msg_obj.msgType in ["chat.photo", "chat.gif", "chat.video.msg"]:
        is_nude, reason, nsfw_score, nude_level = is_sex_image(msg_obj)
        if is_nude:
            # Lưu lịch sử vi phạm nội dung nhạy cảm
            now = time.time()
            violations = s.get("violations", {})
            key = f"{thread_id}_{author_id}"
            user_violations = violations.setdefault(key, {"sensitive_image_times": [], "sensitive_image_count": 0})
            
            # Lọc các vi phạm trong 10 giây
            user_violations["sensitive_image_times"] = [t for t in user_violations["sensitive_image_times"] if now - t <= 60]
            user_violations["sensitive_image_times"].append(now)
            user_violations["sensitive_image_count"] = len(user_violations["sensitive_image_times"])
            
            violations[key] = user_violations
            s["violations"] = violations
            write_settings(s)
            
            # Gửi thông báo xóa media
            media_type = {"chat.photo": "Ảnh", "chat.gif": "GIF", "chat.video.msg": "Video"}[msg_obj.msgType]
            bot.replyMessage(
                Message(text=f"⚠️ {media_type} của bạn chứa nội dung nhạy cảm:\n{reason}\n{media_type} đã bị xóa!"),
                msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=10000
            )
            bot.deleteGroupMsg(msg_obj.msgId, author_id, msg_obj.cliMsgId, thread_id)
            
            # Kiểm tra nếu vi phạm quá 3 lần trong 10 giây
            if user_violations["sensitive_image_count"] > 2:
                if check_admin_group(bot, thread_id):
                    try:
                        bot.kickUsersInGroup(author_id, thread_id)
                        time.sleep(1)  # Chờ 1 giây để tránh lỗi API
                        bot.blockUsersInGroup(author_id, thread_id)
                        bot.replyMessage(
                            Message(text=f"🚫 {get_user_name_by_id(bot, author_id)} đã gửi quá nhiều {media_type.lower()} nhạy cảm và bị kick/block khỏi nhóm!"),
                            msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=10000000
                        )
                        # Xóa lịch sử vi phạm sau khi kick/block
                        del violations[key]
                        s["violations"] = violations
                        write_settings(s)
                    except Exception as e:
                        logging.error(f"Lỗi khi kick/block {author_id} khỏi nhóm {thread_id}: {e}")
                        bot.replyMessage(
                            Message(text=f"⚠️ Lỗi khi kick/block {get_user_name_by_id(bot, author_id)}: {str(e)}"),
                            msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=10000
                        )
            
            return True
    if settings.get("ban_file", {}).get(thread_id, False) and is_file_message(msg_obj):
        bot.deleteGroupMsg(msg_obj.msgId, author_id, msg_obj.cliMsgId, thread_id)
        return True
    if settings.get("ban_voice", {}).get(thread_id, False) and is_voice_message(msg_obj):
        bot.deleteGroupMsg(msg_obj.msgId, author_id, msg_obj.cliMsgId, thread_id)
        return True
    if settings.get("ban_emoji", {}).get(thread_id, False) and is_emoji_message(msg_obj):
        bot.deleteGroupMsg(msg_obj.msgId, author_id, msg_obj.cliMsgId, thread_id)
        return True
    if settings.get("ban_vehinh", {}).get(thread_id, False) and is_vehinh_message(msg_obj):
        bot.deleteGroupMsg(msg_obj.msgId, author_id, msg_obj.cliMsgId, thread_id)
        return True    
    return False

# -----------------------------------------
# Các hàm cài đặt chế độ cấm tin nhắn dài, nội dung trùng lặp, tag người dùng
# -----------------------------------------
def set_longmsg_ban(thread_id, status):
    settings = read_settings()
    key = "ban_longmsg"
    group_settings = settings.get(key, {})
    if group_settings.get(thread_id) == status:
        return f"⚠️ Chế độ cấm tin nhắn quá dài đã được {'bật' if status else 'tắt'} trước đó."
    group_settings[thread_id] = status
    settings[key] = group_settings
    write_settings(settings)
    return f"✅ Đã {'bật' if status else 'tắt'} cấm tin nhắn quá dài trong nhóm."

def set_duplicate_ban(thread_id, status):
    settings = read_settings()
    key = "ban_duplicate"
    group_settings = settings.get(key, {})
    if group_settings.get(thread_id) == status:
        return f"⚠️ Chế độ cấm nội dung trùng lặp đã được {'bật' if status else 'tắt'} trước đó."
    group_settings[thread_id] = status
    settings[key] = group_settings
    write_settings(settings)
    return f"✅ Đã {'bật' if status else 'tắt'} cấm nội dung trùng lặp trong nhóm."

def set_tag_ban(thread_id, status):
    settings = read_settings()
    key = "ban_tag"
    group_settings = settings.get(key, {})
    if group_settings.get(thread_id) == status:
        return f"⚠️ Chế độ cấm tag người dùng đã được {'bật' if status else 'tắt'} trước đó."
    group_settings[thread_id] = status
    settings[key] = group_settings
    write_settings(settings)
    return f"✅ Đã {'bật' if status else 'tắt'} cấm tag người dùng trong nhóm."

def set_word_ban(thread_id, status):
    settings = read_settings()
    key = "ban_word"
    group_settings = settings.get(key, {})
    if group_settings.get(thread_id) == status:
        return f"⚠️ Chế độ cấm từ khóa đã được {'bật' if status else 'tắt'} trước đó."
    group_settings[thread_id] = status
    settings[key] = group_settings
    write_settings(settings)
    return f"✅ Đã {'bật' if status else 'tắt'} cấm từ khóa trong nhóm."

def set_contact_card_ban(thread_id, status):
    settings = read_settings()
    key = "ban_contact_card"
    group_settings = settings.get(key, {})
    if group_settings.get(thread_id) == status:
        return f"⚠️ Chế độ cấm gửi danh thiếp đã được {'bật' if status else 'tắt'} trước đó."
    group_settings[thread_id] = status
    settings[key] = group_settings
    write_settings(settings)
    return f"✅ Đã {'bật' if status else 'tắt'} cấm gửi danh thiếp trong nhóm."

def set_phone_ban(thread_id, status):
    settings = read_settings()
    key = "ban_phone"
    group_settings = settings.get(key, {})
    if group_settings.get(thread_id) == status:
        return f"⚠️ Chế độ cấm gửi số điện thoại đã được {'bật' if status else 'tắt'} trước đó."
    group_settings[thread_id] = status
    settings[key] = group_settings
    write_settings(settings)
    return f"✅ Đã {'bật' if status else 'tắt'} cấm gửi số điện thoại trong nhóm."

def set_mute_sticker_user(bot, thread_id, user_id, status=True):
    """Cấm (True) hoặc bỏ cấm (False) một user gửi sticker trong nhóm"""
    settings = read_settings()
    mute_dict = settings.get(MUTE_STICKER_KEY, {})
    
    if thread_id not in mute_dict:
        mute_dict[thread_id] = []
    
    user_id_str = str(user_id)
    
    if status:
        if user_id_str not in mute_dict[thread_id]:
            mute_dict[thread_id].append(user_id_str)
            settings[MUTE_STICKER_KEY] = mute_dict
            write_settings(settings)
            name = get_user_name_by_id(bot, user_id)  # Giờ bot đã có
            return f"✅ Đã cấm {name} gửi sticker trong nhóm này."
        else:
            return f"⚠️ Người dùng này đã bị cấm gửi sticker trước đó."
    else:
        if user_id_str in mute_dict[thread_id]:
            mute_dict[thread_id].remove(user_id_str)
            if not mute_dict[thread_id]:
                del mute_dict[thread_id]
            settings[MUTE_STICKER_KEY] = mute_dict
            write_settings(settings)
            name = get_user_name_by_id(bot, user_id)
            return f"✅ Đã bỏ cấm {name} gửi sticker."
        else:
            return f"⚠️ Người dùng này chưa bị cấm gửi sticker."

def is_mute_sticker_user(thread_id, author_id):
    """Kiểm tra xem user có bị cấm gửi sticker trong nhóm không"""
    settings = read_settings()
    mute_dict = settings.get(MUTE_STICKER_KEY, {})
    return str(author_id) in mute_dict.get(thread_id, [])
    
def set_vehinh_ban(thread_id, status):
    settings = read_settings()
    key = "ban_vehinh"
    group_settings = settings.get(key, {})
    if group_settings.get(thread_id) == status:
        return f"⚠️ Chế độ cấm vẽ hình đã được {'bật' if status else 'tắt'} trước đó."
    group_settings[thread_id] = status
    settings[key] = group_settings
    write_settings(settings)
    return f"✅ Đã {'bật' if status else 'tắt'} cấm vẽ hình trong nhóm."    
    
import time

def add_to_blacklist(bot, uids):
    """Thêm người dùng vào danh sách đen và xóa họ khỏi các nhóm bot có quyền với thời gian chờ 1 giây giữa mỗi lần kick."""
    s = read_settings()
    blacklist = s.get("blacklist_users", [])
    added = []
    for uid in uids:
        uname = get_user_name_by_id(bot, uid)
        if uid not in blacklist:
            blacklist.append(uid)
            added.append(uname)
            # Tự động xóa khỏi các nhóm mà bot có quyền
            allowed_threads = s.get("allowed_threads", [])
            for thread_id in allowed_threads:
                if check_admin_group(bot, thread_id):
                    try:
                        bot.kickUsersInGroup(uid, thread_id)
                        bot.blockUsersInGroup(uid, thread_id)
                        logging.info(f"Đã xóa và chặn {uname} khỏi nhóm {thread_id}")
                        time.sleep(1)  # Chờ 1 giây giữa mỗi lần kick/block
                    except Exception as e:
                        logging.error(f"Lỗi khi xóa {uname} khỏi nhóm {thread_id}: {e}")
    s["blacklist_users"] = blacklist
    write_settings(s)
    return f"✅ Đã thêm {', '.join(added)} vào danh sách đen!" if added else "⚠️ Không có ai được thêm vào danh sách đen."

def remove_from_blacklist(bot, uids):
    """Xóa người dùng khỏi danh sách đen."""
    s = read_settings()
    blacklist = s.get("blacklist_users", [])
    removed = []
    for uid in uids:
        uname = get_user_name_by_id(bot, uid)
        if uid in blacklist:
            blacklist.remove(uid)
            removed.append(uname)
    s["blacklist_users"] = blacklist
    write_settings(s)
    return f"✅ Đã xóa {', '.join(removed)} khỏi danh sách đen!" if removed else "⚠️ Không có ai trong danh sách đen."

def list_blacklist(bot):
    """Hiển thị danh sách đen."""
    s = read_settings()
    blacklist = s.get("blacklist_users", [])
    if blacklist:
        lst = [{"author_id": uid, "name": get_user_name_by_id(bot, uid)} for uid in blacklist]
        lst.sort(key=lambda x: x["name"])
        return ("🚫 Danh sách đen:\n" +
                "\n".join(f"{i}. {u['name']} (ID: {u['author_id']})" for i, u in enumerate(lst, 1)))
    return "✅ Không có ai trong danh sách đen!" 

# Danh sách sticker bị cấm (thêm ID sticker cần chặn)
BANNED_STICKERS = {23297, 23298}  # Thêm ID sticker bạn muốn chặn

# Cache theo dõi số lần gửi sticker cấm
sticker_violation_cache = {}
sticker_cache_lock = threading.Lock()

def is_banned_sticker(msg_obj):
    if msg_obj.msgType != "chat.sticker":
        return False
    sticker_id = msg_obj.content.get("id")
    return sticker_id in BANNED_STICKERS

def handle_sticker_violation(bot, author_id, thread_id, msg_obj, thread_type):
    if author_id == bot.uid or is_admin(author_id) or is_user_muted(author_id, thread_id):
        return

    with sticker_cache_lock:
        key = f"{thread_id}_{author_id}"
        now = time.time()
        violations = sticker_violation_cache.get(key, {"times": [], "count": 0})
        # Lọc trong 60 giây
        violations["times"] = [t for t in violations["times"] if now - t <= 60]
        violations["times"].append(now)
        violations["count"] = len(violations["times"])
        sticker_violation_cache[key] = violations

        # Xóa tin nhắn ngay lập tức
        try:
            bot.deleteGroupMsg(msg_obj.msgId, author_id, msg_obj.cliMsgId, thread_id)
        except:
            pass

        if violations["count"] >= 3:
            if check_admin_group(bot, thread_id):
                try:
                    # Khóa nhóm
                    bot.changeGroupSetting(thread_id, lockSendMsg=1)
                    time.sleep(2)
                    # Kick + block
                    bot.kickUsersInGroup(author_id, thread_id)
                    time.sleep(1)
                    bot.blockUsersInGroup(author_id, thread_id)
                    # Gửi thông báo
                    bot.replyMessage(
                        Message(text=f"Đã tiến hành xử lí {get_user_name_by_id(bot, author_id)} vì spam sticker lag"),
                        msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=60000
                    )
                    # Mở lại nhóm
                    bot.changeGroupSetting(thread_id, lockSendMsg=0)
                    # Xóa cache
                    sticker_violation_cache.pop(key, None)
                except Exception as e:
                    logging.error(f"Lỗi xử lý sticker spam: {e}")
                    try:
                        bot.changeGroupSetting(thread_id, lockSendMsg=0)
                    except:
                        pass  
   
# -----------------------------------------
# Xử lý vi phạm: spam, từ cấm và các chế độ cấm bổ sung
# -----------------------------------------
def handle_check_profanity(bot, author_id, thread_id, msg_obj, thread_type, message):
    if author_id == bot.uid:
        return
    if is_admin(author_id):
        return
     # === XỬ LÝ REACTION LIMIT ===
    if msg_obj.msgType == 'chat.reaction':
        handle_reaction_limit(bot, author_id, thread_id, msg_obj, thread_type)
        return   

    s = read_settings()
    # Kiểm tra danh sách đen
    if author_id in s.get("blacklist_users", []):
        if check_admin_group(bot, thread_id):
            try:
                bot.deleteGroupMsg(msg_obj.msgId, author_id, msg_obj.cliMsgId, thread_id)
                bot.kickUsersInGroup(author_id, thread_id)
                time.sleep(1)  # Chờ 1 giây sau khi kick
                bot.blockUsersInGroup(author_id, thread_id)
                bot.replyMessage(
                    Message(text=f"🚫 {get_user_name_by_id(bot, author_id)} thuộc danh sách đen và đã bị xóa khỏi nhóm!"),
                    msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=1000000
                )
            except Exception as e:
                logging.error(f"Lỗi khi xóa {author_id} khỏi nhóm {thread_id}: {e}")
        return

    def send_response():
        s = read_settings()
        if author_id in s.get("excluded_users", []):
            return
        admin_ids = s.get('group_admins', {}).get(thread_id, [])
        if bot.uid not in admin_ids:
            return
        # Kiểm tra spam trước, bất kể trạng thái mute
        if is_spamming(author_id, thread_id):
            if check_admin_group(bot, thread_id):
                try:
                    user_name = get_user_name_by_id(bot, author_id)
                    
                    # 1. Thêm vào danh sách mute
                    now = int(time.time())
                    dur = s.get("rules", {}).get("word", {}).get("duration", 30)
                    mute_duration = 60 * dur
                    
                    if not is_user_muted(author_id, thread_id):
                        muted_users = s.get("muted_users", [])
                        muted_users.append({
                            "author_id": author_id,
                            "thread_id": thread_id,
                            "reason": "Spam quá nhiều tin nhắn",
                            "muted_until": now + mute_duration
                        })
                        s["muted_users"] = muted_users
                        
                        # Cập nhật violations
                        violations = s.get('violations', {})
                        key = f"{thread_id}_{author_id}"
                        user_v = violations.setdefault(key, {
                            "profanity_count": 0,
                            "spam_count": 0,
                            "penalty_level": 0,
                            "sensitive_image_count": 0
                        })
                        user_v["spam_count"] = user_v.get("spam_count", 0) + 1
                        violations[key] = user_v
                        s["violations"] = violations
                        
                        write_settings(s)
                        
                        # 2. Thông báo cho người dùng
                        bot.replyMessage(
                            Message(text=f"⚠️ {user_name}, bạn đã bị cấm chat trong {dur} phút do spam!"),
                            msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=30000
                        )
                        
                        # 3. Xóa tin nhắn spam
                        bot.deleteGroupMsg(msg_obj.msgId, author_id, msg_obj.cliMsgId, thread_id)
                        
                except Exception as e:
                    logging.error(f"Lỗi khi xử lý spam: {e}")
            return

        # Kiểm tra mute sau khi kiểm tra spam
        if is_user_muted(author_id, thread_id):
            bot.deleteGroupMsg(msg_obj.msgId, author_id, msg_obj.cliMsgId, thread_id)

        # === CHỐNG SPAM STICKER CẤM ===
        if is_banned_sticker(msg_obj):
            Thread(target=handle_sticker_violation, args=(bot, author_id, thread_id, msg_obj, thread_type)).start()
            return


        # Gộp content và title để kiểm tra từ cấm
        txt = extract_message_text(msg_obj)
        if isinstance(msg_obj.content, dict):
            txt += " " + msg_obj.content.get('title', '')
        if not isinstance(txt, str):
            return

        group_admin_ids = s.get('group_admins', {}).get(thread_id, [])
        if not (is_admin(author_id) or author_id in group_admin_ids):
            if get_ban_link_status(thread_id) and is_url_in_message(msg_obj):
                bot.deleteGroupMsg(msg_obj.msgId, author_id, msg_obj.cliMsgId, thread_id)
                return
            if s.get("ban_longmsg", {}).get(thread_id, False):
                threshold_long = 200
                if len(txt) > threshold_long:
                    bot.deleteGroupMsg(msg_obj.msgId, author_id, msg_obj.cliMsgId, thread_id)
                    return
            if s.get("ban_duplicate", {}).get(thread_id, False):
                duplicate_window = 60
                key = f"last_msg_{thread_id}_{author_id}"
                with last_message_cache_lock:
                    last_info = last_message_cache.get(key, {"msg": "", "time": 0})
                    current_time = time.time()
                    if current_time - last_info["time"] < duplicate_window and \
                       last_info["msg"].strip().lower() == txt.strip().lower():
                        bot.deleteGroupMsg(msg_obj.msgId, author_id, msg_obj.cliMsgId, thread_id)
                        return
                    last_message_cache[key] = {"msg": txt, "time": current_time}
            if s.get("ban_tag", {}).get(thread_id, False):
                if hasattr(msg_obj, "mentions") and msg_obj.mentions:
                    bot.deleteGroupMsg(msg_obj.msgId, author_id, msg_obj.cliMsgId, thread_id)
                    return
            if s.get("ban_word", {}).get(thread_id, False):  # Check ban_word status
                forbidden = s.get('forbidden_words', [])
                violations = s.get('violations', {})
                rules = s.get("rules", {})
                now = int(time.time())
                word_rule = rules.get("word", {"threshold": 3, "duration": 30})
                thresh, dur = word_rule["threshold"], word_rule["duration"]
                if any(re.search(r'\b' + re.escape(word.lower()) + r'\b', txt.lower()) for word in forbidden):
                    violating_words = [
                        word
                        for word in forbidden
                        if re.search(r'\b' + re.escape(word.lower()) + r'\b', txt.lower())
                    ]
                    print(f"[TỪ CẤM] Người dùng {author_id} gửi tin nhắn vi phạm. Nội dung: '{txt}'. Từ vi phạm: {violating_words}")
                    bot.deleteGroupMsg(msg_obj.msgId, author_id, msg_obj.cliMsgId, thread_id)
                    # KIỂM TRA ĐÃ MUTE CHƯA
                    if is_user_muted(author_id, thread_id):
                        return  # ĐÃ MUTE → KHÔNG GỬI THÔNG BÁO NỮA
                    user_v = violations.setdefault(author_id, {}).setdefault(thread_id, {"profanity_count": 0, "spam_count": 0, "penalty_level": 0})
                    user_v["profanity_count"] += 1
                    count = user_v["profanity_count"]
                    if count >= thresh:
                        user_v["penalty_level"] += 1
                        s.setdefault("muted_users", []).append({
                            "author_id": author_id,
                            "thread_id": thread_id,
                            "reason": txt,
                            "muted_until": now + 60 * dur
                        })
                        write_settings(s)
                        resp = f"❌ Bạn đã vượt quá {thresh} lần vi phạm và bị mute {dur} phút"
                        bot.replyMessage(Message(text=resp), msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=60000)
                        return
                    elif count == thresh - 1:
                        resp = f"⚠️️ Cảnh báo: {count}/{thresh} lần vi phạm. Nếu tái phạm, bạn sẽ bị mute {dur} phút"
                        bot.replyMessage(Message(text=resp), msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=100000)
                    else:
                        resp = f"⚠️️ Bạn đã vi phạm {count}/{thresh} lần. Hãy kiểm soát lời nói!"
                        bot.replyMessage(Message(text=resp), msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=10000)
                    write_settings(s)
    Thread(target=send_response).start()
# -----------------------------------------
# Các hàm hiển thị thông tin
# -----------------------------------------
def get_user_name_by_id(bot, author_id):
    try:
        return bot.fetchUserInfo(author_id).changed_profiles[author_id].displayName
    except:
        return "Unknown User"

def print_muted_users_in_group(bot, thread_id):
    s = read_settings()
    now = int(time.time())
    muted = [{
        "author_id": u['author_id'],
        "name": get_user_name_by_id(bot, u['author_id']),
        "minutes_left": (u['muted_until'] - now) // 60,
        "reason": u['reason']
    } for u in s.get("muted_users", []) if u['thread_id'] == thread_id and u['muted_until'] > now]
    muted.sort(key=lambda x: x['minutes_left'])
    if muted:
        return ("🔒 Danh sách thành viên bị mute:\n" +
                "\n".join(f"{i}. {u['name']} - {u['minutes_left']} phút - Lý do: {u['reason']}" for i, u in enumerate(muted, 1)))
    else:
        return "✅ Nhóm này không có thành viên bị mute!"

def print_blocked_users_in_group(bot, thread_id):
    s = read_settings()
    blocked = s.get("block_user_group", {}).get(thread_id, {}).get("blocked_users", [])
    lst = [{"author_id": uid, "name": get_user_name_by_id(bot, uid)} for uid in blocked]
    lst.sort(key=lambda x: x['name'])
    if lst:
        return ("🚫 Danh sách thành viên bị chặn:\n" +
                "\n".join(f"{i}. {u['name']} (ID: {u['author_id']})" for i, u in enumerate(lst, 1)))
    else:
        return "✅ Không có thành viên nào bị chặn trong nhóm!"

def add_users_to_ban_list(bot, author_ids, thread_id, reason):
    s = read_settings()
    now = int(time.time())
    
    # DỌN DẸP MUTE HẾT HẠN TRƯỚC KHI XỬ LÝ
    s["muted_users"] = [m for m in s.get("muted_users", []) if m['muted_until'] > now]
    
    muted = s.get("muted_users", [])
    violations = s.get("violations", {})
    dur = s.get("rules", {}).get("word", {}).get("duration", 30)
    resp = ""
    
    for uid in author_ids:
        uname = get_user_name_by_id(bot, uid)
        
        # Kiểm tra xem user có đang bị mute trong thread này không
        user_currently_muted = any(m["author_id"] == uid and m["thread_id"] == thread_id for m in muted)
        
        if not user_currently_muted:
            muted.append({"author_id": uid, "thread_id": thread_id, "reason": reason, "muted_until": now + 60 * dur})
            violations.setdefault(uid, {}).setdefault(thread_id, {"profanity_count": 0, "spam_count": 0, "penalty_level": 0})
            violations[uid][thread_id]["profanity_count"] += 1
            violations[uid][thread_id]["penalty_level"] += 1
            resp += f"⛔ {uname} đã bị cấm phát ngôn {dur} phút!\n"
        else:
            resp += f"⚠️ {uname} đã bị mute trước đó!\n"
    
    s["muted_users"] = muted
    s["violations"] = violations
    write_settings(s)
    return resp

def remove_users_from_ban_list(bot, author_ids, thread_id):
    s = read_settings()
    muted = s.get("muted_users", [])
    violations = s.get("violations", {})
    resp = ""
    for uid in author_ids:
        uname = get_user_name_by_id(bot, uid)
        new_muted = [m for m in muted if not (m["author_id"] == uid and m["thread_id"] == thread_id)]
        removed = len(muted) != len(new_muted)
        muted = new_muted
        if uid in violations and thread_id in violations[uid]:
            del violations[uid][thread_id]
            if not violations[uid]:
                del violations[uid]
            removed = True
        resp += f"✅ {uname} đã được gỡ cấm phát ngôn!\n" if removed else f"⚠️️ {uname} không có trong danh sách cấm!\n"
    s["muted_users"], s["violations"] = muted, violations
    write_settings(s)
    return resp

def block_users_from_group(bot, author_ids, thread_id):
    s = read_settings()
    s.setdefault("block_user_group", {}).setdefault(thread_id, {"blocked_users": []})
    blocked = []
    for uid in author_ids:
        uname = get_user_name_by_id(bot, uid)
        bot.blockUsersInGroup(uid, thread_id)
        if uid not in s["block_user_group"][thread_id]["blocked_users"]:
            s["block_user_group"][thread_id]["blocked_users"].append(uid)
        blocked.append(uname)
    write_settings(s)
    if blocked:
        return f"🚫 {', '.join(blocked)} đã bị chặn khỏi nhóm!"
    else:
        return "✅ Không có ai bị chặn khỏi nhóm!"

def unblock_users_from_group(bot, author_ids, thread_id):
    s = read_settings()
    unblocked = []
    if thread_id in s.get("block_user_group", {}):
        blocked = s["block_user_group"][thread_id]["blocked_users"]
        for uid in author_ids:
            uname = get_user_name_by_id(bot, uid)
            if uid in blocked:
                bot.unblockUsersInGroup(uid, thread_id)
                blocked.remove(uid)
                unblocked.append(uname)
        if not blocked:
            del s["block_user_group"][thread_id]
        write_settings(s)
    if unblocked:
        return f"✅ {', '.join(unblocked)} đã được bỏ chặn khỏi nhóm"
    else:
        return "🚫 Không có ai bị chặn trong nhóm"

def kick_users_from_group(bot, uids, thread_id):
    resp = ""
    for uid in uids:
        try:
            bot.kickUsersInGroup(uid, thread_id)
            bot.blockUsersInGroup(uid, thread_id)
            resp += f"✅ Đã kick {get_user_name_by_id(bot, uid)} khỏi nhóm thành công\n"
        except Exception:
            resp += f"🚫 Không thể kick {get_user_name_by_id(bot, uid)} khỏi nhóm\n"
    return resp

def extract_uids_from_mentions(msg_obj):
    return [m["uid"] for m in msg_obj.mentions if "uid" in m]

def add_admin(bot, author_id, mentioned_uids, s):
    admin_bot = s.get("admin_bot", [])
    resp = ""
    for uid in mentioned_uids:
        if author_id not in admin_bot:
            resp = "🚫 Bạn không có quyền sử dụng lệnh này!"
        elif uid not in admin_bot:
            admin_bot.append(uid)
            resp = f"☑️ Đã thêm {get_user_name_by_id(bot, uid)} vào danh sách Admin BOT"
        else:
            resp = f"⚠️️ {get_user_name_by_id(bot, uid)} đã có trong danh sách Admin BOT"
    s["admin_bot"] = admin_bot
    write_settings(s)
    return resp

def remove_admin(bot, author_id, mentioned_uids, s):
    admin_bot = s.get("admin_bot", [])
    resp = ""
    for uid in mentioned_uids:
        if author_id not in admin_bot:
            resp = "⛔ Bạn không có quyền sử dụng lệnh này!"
        elif uid in admin_bot:
            admin_bot.remove(uid)
            resp = f"☑️ Đã xóa {get_user_name_by_id(bot, uid)} khỏi danh sách Admin BOT"
        else:
            resp = f"⚠️️ {get_user_name_by_id(bot, uid)} không có trong danh sách Admin BOT"
    s["admin_bot"] = admin_bot
    write_settings(s)
    return resp

def list_forbidden_groups(bot):
    s = read_settings()
    ban_keys = ['ban_link', 'ban_image', 'ban_video', 'ban_sticker', 'ban_gif',
                'ban_longmsg', 'ban_duplicate', 'ban_tag', 'ban_sex',
                'ban_file', 'ban_voice', 'ban_emoji', 'ban_word', 'ban_contact_card', 'ban_phone', 'ban_vehinh']
    
    # Ánh xạ ngắn gọn: icon + tên
    config_map = {
        'ban_link': '🔗 Link',
        'ban_image': '🖼️ Ảnh', 
        'ban_video': '🎥 Video',
        'ban_sticker': '💬 Sticker',
        'ban_gif': '🎞️ GIF',
        'ban_sex': '🔞 Nhạy cảm',
        'ban_file': '📄 File',
        'ban_voice': '🎤 Voice',
        'ban_emoji': '😀 Emoji',
        'ban_longmsg': '🗨️ Tin dài',
        'ban_duplicate': '📑 Trùng lặp',
        'ban_tag': '🏷️ Tag',
        'ban_word': '📜 Từ cấm',
        'ban_contact_card': '📇 Danh thiếp',
        'ban_phone': '📱 SĐT',
        'ban_vehinh': '✍️ Vẽ hình'
    }
    
    # Thu thập cài đặt từng nhóm
    groups = {}
    for key in ban_keys:
        ban_dict = s.get(key, {})
        for thread_id, status in ban_dict.items():
            if status:
                groups.setdefault(thread_id, []).append(config_map[key])
    
    # Thêm bot status
    allowed = s.get('allowed_threads', [])
    for thread_id in allowed:
        groups.setdefault(thread_id, []).append('🤖 Bot')
    
    if not groups:
        return "✅ Không có nhóm nào bật cấu hình"
    
    # Tạo output gọn
    lines = ["📋 NHÓM BẬT CẤU HÌNH"]
    for i, (thread_id, configs) in enumerate(groups.items(), 1):
        try:
            group = bot.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
            name = group.name[:25]  # Giới hạn tên nhóm
        except:
            name = "Nhóm ẩn"
        
        lines.append(f"{i}. {name}")
        lines.append(f"   🆔 {thread_id}")
        lines.append(f"   {' | '.join(configs)}")
        lines.append("")
    
    lines.append(f"📊 Tổng: {len(groups)} nhóm")
    return "\n".join(lines)


# ----------------- HẰNG SỐ & DẢI MÀU -----------------
MULTICOLOR_GRADIENT = [
    (255, 0, 0), (255, 165, 0), (255, 255, 0),
    (0, 255, 0), (0, 0, 255), (75, 0, 130), (148, 0, 211)
]

GRADIENT_SETS = [
    [(255, 0, 255), (0, 255, 255), (255, 255, 0), (0, 255, 0)],
    [(255, 0, 0), (255, 165, 0), (255, 255, 0)],
    [(255, 182, 193), (173, 216, 230), (152, 251, 152), (240, 230, 140)],
    [(255, 94, 77), (255, 160, 122), (255, 99, 71), (255, 215, 0)],
    [(255, 165, 0), (255, 69, 0), (255, 0, 0)],
    [(255, 182, 193), (255, 105, 180), (255, 20, 147), (255, 0, 255)],
    [(0, 255, 127), (0, 255, 255), (30, 144, 255)],
    [(0, 255, 127), (0, 191, 255), (123, 104, 238)],
    [(0, 255, 0), (138, 43, 226), (0, 255, 255)],
    [(255, 127, 80), (255, 165, 0), (255, 69, 0), (255, 99, 71)],
    [(255, 223, 186), (255, 182, 193), (255, 160, 122), (255, 99, 71)],
    [(176, 196, 222), (135, 206, 250), (70, 130, 180)],
    [(255, 105, 180), (0, 191, 255), (30, 144, 255)],
    [(255, 140, 0), (255, 99, 71), (255, 69, 0)],
    [(255, 0, 0), (0, 255, 0), (0, 255, 255)],
    [(0, 255, 255), (70, 130, 180)],
    [(0, 255, 127), (60, 179, 113)],
    [(0, 255, 255), (30, 144, 255), (135, 206, 235)],
    [(0, 255, 0), (50, 205, 50), (154, 205, 50)],
    [(255, 165, 0), (255, 223, 0), (255, 140, 0), (255, 69, 0)],
    [(255, 105, 180), (138, 43, 226), (255, 20, 147)],
    [(173, 216, 230), (216, 191, 216), (255, 182, 193)],
    [(152, 251, 152), (255, 255, 224), (245, 245, 245)],
    [(255, 192, 203), (255, 218, 185), (255, 250, 205)],
    [(224, 255, 255), (175, 238, 238), (255, 255, 255)],
    [(255, 204, 204), (255, 255, 204), (204, 255, 204), (204, 255, 255), (204, 204, 255), (255, 204, 255)],
    [(255, 239, 184), (255, 250, 250), (255, 192, 203)],
    [(173, 255, 47), (255, 255, 102), (255, 204, 153)],
    [(189, 252, 201), (173, 216, 230)],
    [(255, 182, 193), (250, 250, 250), (216, 191, 216)],
    [(173, 216, 230), (255, 255, 255), (255, 255, 102)],
]

# Đường dẫn thư mục chứa ảnh nền
BACKGROUND_FOLDER = 'Resource/background/'
def BackgroundGetting():
    files = glob.glob(BACKGROUND_FOLDER + "*.jpg") + glob.glob(BACKGROUND_FOLDER + "*.png") + glob.glob(BACKGROUND_FOLDER + "*.jpeg")
    if not files:
        return None
    chosen = random.choice(files)
    try:
        return Image.open(chosen).convert("RGB")
    except Exception as e:
        logging.error(f"Lỗi khi mở ảnh nền từ {chosen}: {e}")
        return None

# ----------------- HÀM HỖ TRỢ ẢNH -----------------
_FONT_CACHE = {}
def get_font(font_path, size):
    """Load font (cache lại) để không load nhiều lần."""
    key = (font_path, size)
    if key not in _FONT_CACHE:
        try:
            _FONT_CACHE[key] = ImageFont.truetype(font_path, size)
        except Exception as e:
            logging.error(f"Lỗi load font {font_path} với size {size}: {e}")
            _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]

def FetchImage(url):
    """Tải ảnh từ URL hoặc base64."""
    if not url:
        return None
    try:
        if url.startswith('data:image'):
            h, e = url.split(',', 1)
            i = base64.b64decode(e)
            return Image.open(BytesIO(i)).convert("RGB")
        r = requests.get(url, stream=True, timeout=10)
        r.raise_for_status()
        return Image.open(BytesIO(r.content)).convert("RGB")
    except Exception as e:
        logging.error(f"Lỗi tải ảnh từ {url}: {e}")
        return None

def Dominant(image):
    """Tính màu chủ đạo của ảnh."""
    try:
        img = image.convert("RGB").resize((150, 150), Image.Resampling.LANCZOS)
        pixels = img.getdata()
        if not pixels:
            return (0, 0, 0)
        r, g, b = 0, 0, 0
        for pixel in pixels:
            r += pixel[0]
            g += pixel[1]
            b += pixel[2]
        total = len(pixels)
        if total == 0:
            return (0, 0, 0)
        r, g, b = r // total, g // total, b // total
        return (r, g, b)
    except Exception as e:
        logging.error(f"Lỗi tính màu chủ đạo: {e}")
        return (0, 0, 0)

def RandomContrast(Base):
    """Tạo màu tương phản ngẫu nhiên dựa trên màu nền."""
    r, g, b, _ = Base
    box_luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    if box_luminance > 0.5:
        r = random.randint(80, 140)
        g = random.randint(80, 140)
        b = random.randint(80, 140)
    else:
        r = random.randint(160, 220)
        g = random.randint(160, 220)
        b = random.randint(160, 220)
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    s = min(0.5, s + 0.3)
    v = min(0.85, v + 0.1)
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    text_luminance = (0.299 * r + 0.587 * g + 0.114 * b)
    if abs(text_luminance - box_luminance) < 0.4:
        if box_luminance > 0.5:
            r, g, b = colorsys.hsv_to_rgb(h, s, min(0.7, v * 0.6))
        else:
            r, g, b = colorsys.hsv_to_rgb(h, s, min(0.9, v * 1.2))
    return (int(r * 255), int(g * 255), int(b * 255), 255)

def get_random_gradient():
    """Chọn ngẫu nhiên một dải màu từ GRADIENT_SETS."""
    return random.choice(GRADIENT_SETS)

# --------------------- HÀM HIỆU ỨNG CHỮ VỚI GRADIENT ---------------------
emoji_pattern = re.compile(
    "("
    "[\U0001F1E6-\U0001F1FF]{2}|"
    "[\U0001F600-\U0001F64F]|"
    "[\U0001F300-\U0001F5FF]|"
    "[\U0001F680-\U0001F6FF]|"
    "[\U0001F700-\U0001F77F]|"
    "[\U0001F780-\U0001F7FF]|"
    "[\U0001F800-\U0001F8FF]|"
    "[\U0001F900-\U0001F9FF]|"
    "[\U0001FA00-\U0001FA6F]|"
    "[\U0001FA70-\U0001FAFF]|"
    "[\U0001FB00-\U0001FBFF]|"
    "[\u2600-\u26FF]|"
    "[\u2700-\u27BF]|"
    "[\u2300-\u23FF]|"
    "[\u2B00-\u2BFF]|"
    "\d\uFE0F?\u20E3|"
    "[#*]\uFE0F?\u20E3|"
    "[\U00013000-\U000134AF]"
    ")",
    flags=re.UNICODE
)

def split_text_by_emoji(text):
    """Tách văn bản thành danh sách các tuple (segment, is_emoji)."""
    segments = []
    buffer = ""
    for ch in text:
        if emoji_pattern.match(ch):
            if buffer:
                segments.append((buffer, False))
                buffer = ""
            segments.append((ch, True))
        else:
            buffer += ch
    if buffer:
        segments.append((buffer, False))
    return segments

def draw_mixed_gradient_text(draw, text, position, normal_font, emoji_font, gradient_colors, shadow_offset=(2,2)):
    """Vẽ văn bản hỗn hợp với gradient cho chữ thường và emoji."""
    if not text:
        return
    total_chars = len(text)
    change_every = 4
    color_list = []
    num_segments = len(gradient_colors) - 1
    steps_per_segment = (total_chars // change_every) + 1
    for i in range(num_segments):
        for j in range(steps_per_segment):
            if len(color_list) < total_chars:
                ratio = j / steps_per_segment
                c1, c2 = gradient_colors[i], gradient_colors[i+1]
                interpolated = (
                    int(c1[0]*(1 - ratio) + c2[0]*ratio),
                    int(c1[1]*(1 - ratio) + c2[1]*ratio),
                    int(c1[2]*(1 - ratio) + c2[2]*ratio)
                )
                color_list.append(interpolated)
    while len(color_list) < total_chars:
        color_list.append(gradient_colors[-1])
    
    x, y = position
    shadow_color = (0, 0, 0, 150)
    segments = split_text_by_emoji(text)
    char_index = 0
    for seg, is_emoji in segments:
        current_font = emoji_font if is_emoji else normal_font
        for ch in seg:
            draw.text((x + shadow_offset[0], y + shadow_offset[1]), ch, font=current_font, fill=shadow_color)
            draw.text((x, y), ch, font=current_font, fill=color_list[char_index])
            bbox = draw.textbbox((0, 0), ch, font=current_font)
            char_width = bbox[2] - bbox[0]
            x += char_width
            char_index += 1

def DrawPillowBase1(draw, position, text, font, fill, shadow_offset=(4, 4), shadow_fill=(0, 0, 0, 150)):
    """Vẽ văn bản với bóng đổ."""
    x, y = position
    draw.text((x + shadow_offset[0], y + shadow_offset[1]), text, font=font, fill=shadow_fill)
    draw.text((x, y), text, font=font, fill=fill)

# ----------------- HÀM TẠO ẢNH MENU CHÀO MỪNG -----------------
def create_bott_welcome_image(user_name, user_avatar_url, user_cover_url, bot_avatar_url, menu_text):
    """
    Tạo ảnh menu chào mừng với phong cách tương tự da.py.
    """
    SIZE = (3000, 880)
    FINAL_SIZE = (1500, 460)

    # 1) Tạo nền ảnh
    if user_cover_url and user_cover_url != "https://cover-talk.zadn.vn/default":
        bg_image = FetchImage(user_cover_url)
        if bg_image:
            bg_image = bg_image.resize(SIZE, Image.Resampling.LANCZOS)
            bg_image = bg_image.filter(ImageFilter.GaussianBlur(radius=20))
        else:
            bg_image = BackgroundGetting()
    else:
        bg_image = BackgroundGetting()
    if not bg_image:
        bg_image = Image.new("RGB", SIZE, (130, 190, 255))
    bg_image = bg_image.convert("RGBA")

    # 2) Tạo lớp phủ với hình chữ nhật bo góc
    overlay = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    dominant_color = Dominant(bg_image)
    luminance = (0.299 * dominant_color[0] + 0.587 * dominant_color[1] + 0.114 * dominant_color[2]) / 255
    box_color = random.choice([
        (120, 200, 180, 100), (180, 140, 200, 100), (240, 180, 160, 100),
        (160, 200, 140, 100), (200, 160, 120, 100), (140, 180, 220, 100),
        (220, 200, 140, 100), (180, 180, 180, 105)
    ]) if luminance >= 0.5 else random.choice([
        (200, 140, 160, 105), (140, 120, 180, 105), (100, 140, 160, 105),
        (160, 140, 120, 105), (120, 160, 180, 105), (60, 60, 60, 80)
    ])

    box_x1, box_y1 = 60, 70
    box_x2, box_y2 = SIZE[0] - 60, SIZE[1] - 80
    draw.rounded_rectangle([(box_x1, box_y1), (box_x2, box_y2)], radius=100, fill=box_color)

    # 3) Load font
    font_top_path = "font/5.otf"
    font_emoji_path = "font/NotoEmoji-Bold.ttf"
    try:
        font_text_large = ImageFont.truetype(font_top_path, 120)
        font_text_big = ImageFont.truetype(font_top_path, 110)
        font_text_small = ImageFont.truetype(font_top_path, 105)
        font_time = ImageFont.truetype(font_top_path, 65)
        font_icon = ImageFont.truetype(font_emoji_path, 65)
    except Exception as e:
        logging.error(f"Lỗi load font: {e}")
        font_text_large = font_text_big = font_text_small = font_time = font_icon = ImageFont.load_default()

    # 4) Chuẩn bị văn bản
    time_line = datetime.now(timezone(timedelta(hours=7))).strftime("%H:%M:%S %Y-%m-%d")
    dt = datetime.strptime(time_line, "%H:%M:%S %Y-%m-%d")
    gio_phut = dt.strftime("%H:%M")
    ngay_thang = dt.strftime("%d-%m")
    text_lines = [
        f"Chào {user_name.upper()}!",
        "Chào mừng đến với menu Shinn",
        "Chức năng : kiểm soát nhóm",
        "Admin : Minh Vũ Shinn Cte",
        "Xin mời chọn lệnh"
    ]
    text_fonts = [font_text_large, font_text_big, font_text_small, font_text_small, font_time]
    emoji_fonts = [font_icon, font_icon, font_icon, font_icon, font_icon]
    random_gradients = random.sample(GRADIENT_SETS, 3)
    text_colors = [
        MULTICOLOR_GRADIENT,  # dòng 1
        random_gradients[0],  # dòng 2
        MULTICOLOR_GRADIENT,  # dòng 3
        random_gradients[1],  # dòng 4
        random_gradients[2]   # dòng 5
    ]

    # 5) Vẽ văn bản với gradient và hỗ trợ emoji
    line_spacing = 150
    start_y = box_y1 + 80 - 30
    avatar_left_edge = box_x1 + 50 + 430 + 1
    avatar_right_edge = box_x2 - 460 - 25
    safe_text_width = avatar_right_edge - avatar_left_edge - 50

    def truncate_text(line, font, max_width):
        if not line:
            return line
        truncated = line
        ellipsis = ".."
        ellipsis_width = draw.textbbox((0, 0), ellipsis, font=font)[2]
        while True:
            text_bbox = draw.textbbox((0, 0), truncated + ellipsis, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            if text_width <= max_width or len(truncated) <= 3:
                break
            if ord(truncated[-1]) > 0xFFFF:
                truncated = truncated[:-1]
            else:
                truncated = truncated[:-1]
        return truncated + ellipsis if truncated != line else line

    for i, (line, font, emoji_font, colors) in enumerate(zip(text_lines, text_fonts, emoji_fonts, text_colors)):
        if line:
            truncated_line = truncate_text(line, font, safe_text_width)
            text_bbox = draw.textbbox((0, 0), truncated_line, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_x = (box_x1 + box_x2 - text_width) // 2
            text_y = start_y + i * line_spacing
            draw_mixed_gradient_text(draw, truncated_line, (text_x, text_y), normal_font=font, emoji_font=emoji_font, gradient_colors=colors, shadow_offset=(2, 2))

    # 6) Xử lý avatar
    avatar_size = 430
    center_y = (box_y1 + box_y2) // 2 + 60
    left_avatar_x = box_x1 + 50
    right_avatar_x = box_x2 - 460

    def load_avatar(url):
        if not url:
            return Image.new("RGBA", (avatar_size, avatar_size), (200, 200, 200, 255))
        try:
            img = FetchImage(url)
            if img:
                img = img.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS).convert("RGBA")
                return img
            return Image.new("RGBA", (avatar_size, avatar_size), (200, 200, 200, 255))
        except Exception as e:
            logging.error(f"Lỗi tải avatar: {e}")
            return Image.new("RGBA", (avatar_size, avatar_size), (200, 200, 200, 255))

    user_avatar = load_avatar(user_avatar_url)
    bot_avatar = load_avatar(bot_avatar_url)

    for avatar, x in [(user_avatar, left_avatar_x), (bot_avatar, right_avatar_x)]:
        mask = Image.new("L", (avatar_size, avatar_size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
        border_size = avatar_size + 20
        border_offset = (border_size - avatar_size) // 2
        rainbow_border = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
        draw_border = ImageDraw.Draw(rainbow_border)
        for i in range(360):
            h = i / 360
            r, g, b = colorsys.hsv_to_rgb(h, 0.5, 0.8)
            draw_border.arc([(3, 3), (border_size - 4, border_size - 4)], i, i + 1, fill=(int(r * 255), int(g * 255), int(b * 255), 255), width=6)
        overlay.paste(rainbow_border, (x - border_offset, center_y - border_size // 2), rainbow_border)
        overlay.paste(avatar, (x, center_y - avatar_size // 2), mask)

    # 7) Vẽ logo và chữ "design by Minh Vũ Shinn Cte"
    logo_path = "zalo.png"
    if os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo_size = 80
            logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
            mask = Image.new("L", (logo_size, logo_size), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, logo_size, logo_size), fill=255)
            round_logo = Image.new("RGBA", (logo_size, logo_size), (0, 0, 0, 0))
            round_logo.paste(logo, (0, 0), mask)
            logo_x = box_x1 + 50
            logo_y = SIZE[1] - logo_size - 5
            overlay.paste(round_logo, (logo_x, logo_y), round_logo)
        except Exception as e:
            logging.error(f"Lỗi khi xử lý logo zalo.png: {e}")

    designer_text = "design by Minh Vũ Shinn Cte"
    designer_font = ImageFont.truetype(font_top_path, 65)
    text_bbox = draw.textbbox((0, 0), designer_text, font=designer_font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]
    designer_x = box_x2 - text_w - 20
    designer_y = SIZE[1] - text_h - 25
    draw_mixed_gradient_text(
        draw,
        text=designer_text,
        position=(designer_x, designer_y),
        normal_font=designer_font,
        emoji_font=font_icon,
        gradient_colors=get_random_gradient(),
        shadow_offset=(2, 2)
    )

    # 8) Vẽ thời gian
    left_info = f"⏰ {gio_phut}   📆 {ngay_thang}"
    left_font = ImageFont.truetype(font_top_path, 65)
    text_bbox = draw.textbbox((0, 0), left_info, font=left_font)
    text_h = text_bbox[3] - text_bbox[1]
    left_x = box_x1 + 150
    left_y = SIZE[1] - text_h - 5
    draw_mixed_gradient_text(
        draw,
        text=left_info,
        position=(left_x, left_y),
        normal_font=left_font,
        emoji_font=font_icon,
        gradient_colors=MULTICOLOR_GRADIENT,
        shadow_offset=(2, 2)
    )

    # 9) Gộp và lưu ảnh
    final_image = Image.alpha_composite(bg_image, overlay).resize(FINAL_SIZE, Image.Resampling.LANCZOS).convert("RGB")
    image_path = "menu_welcome.jpg"
    final_image.save(image_path, quality=95)
    return image_path
    
def delete_file(file_path):
    """Xóa file nếu tồn tại."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
        else:
            logging.error(f"Không tìm thấy file: {file_path}")
    except Exception as e:
        logging.error(f"Lỗi khi xóa file {file_path}: {e}")
        


def load_excluded_groups():
    """Tải dữ liệu từ file JSON chứa danh sách nhóm bị loại. Trả về danh sách rỗng nếu file không tồn tại hoặc lỗi."""
    if not os.path.exists(EXCLUDED_EVENTS_FILE):
        return []
    try:
        with open(EXCLUDED_EVENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Lỗi tải danh sách nhóm bị loại: {str(e)}")
        return []

def save_excluded_groups(excluded_groups):
    """Lưu danh sách nhóm bị loại vào file JSON với định dạng UTF-8."""
    try:
        with open(EXCLUDED_EVENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(excluded_groups, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Lỗi lưu danh sách nhóm bị loại: {str(e)}")
        raise

def add_excluded_group(group_id, group_name):
    """Thêm nhóm vào danh sách bị loại. Trả về True nếu thành công, False nếu group_id đã tồn tại."""
    excluded_groups = load_excluded_groups()
    for group in excluded_groups:
        if group.get("group_id") == group_id:
            return False
    excluded_groups.append({"group_id": group_id, "group_name": group_name})
    save_excluded_groups(excluded_groups)
    return True

def remove_excluded_group(group_id):
    """Xóa nhóm khỏi danh sách bị loại. Trả về True nếu xóa thành công, False nếu group_id không tồn tại."""
    excluded_groups = load_excluded_groups()
    for group in excluded_groups:
        if group.get("group_id") == group_id:
            excluded_groups.remove(group)
            save_excluded_groups(excluded_groups)
            return True
    return False

def list_excluded_groups():
    """Trả về danh sách nhóm bị loại khỏi sự kiện chào mừng."""
    return load_excluded_groups()

def send_reply_with_style(bot, text, msg_obj, thread_id, thread_type, ttl=30000, color="#000000"):
    """Gửi tin nhắn phản hồi với định dạng màu sắc và in đậm."""
    try:
        base_length = len(text)
        adjusted_length = base_length + 355
        style = MultiMsgStyle([
            MessageStyle(offset=0, length=adjusted_length, style="color", color=color, auto_format=False),
            MessageStyle(offset=0, length=adjusted_length, style="bold", size="8", auto_format=False)
        ])
        msg = Message(text=text, style=style)
        bot.replyMessage(msg, msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=ttl)
    except Exception as e:
        logging.error(f"Lỗi gửi tin nhắn với định dạng: {str(e)}")
        bot.replyMessage(Message(text="⚠️ Đã xảy ra lỗi khi gửi tin nhắn"), msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=20000)

def fetch_group_info(target_input, msg_obj, bot):
    """
    Lấy group_id từ mentions, target_input, hoặc msg_obj.idTo.
    Trả về tuple (group_id, group_name) hoặc None nếu có lỗi.
    """
    if msg_obj.mentions and len(msg_obj.mentions) > 0:
        group_id = msg_obj.mentions[0]['uid']
    elif target_input:
        group_id = target_input.strip()
    else:
        group_id = msg_obj.idTo

    if not group_id:
        return None

    try:
        group_info = bot.fetchGroupInfo(group_id)
        group = group_info.gridInfoMap[group_id]
        group_name = group.name
        return group_id, group_name
    except Exception as e:
        logging.error(f"Lỗi lấy thông tin nhóm {group_id}: {e}")
        return None        
def send_message_with_style(bot, text, thread_id, thread_type, ttl=60000, color="#db342e"):
    """Gửi tin nhắn với định dạng màu sắc và in đậm."""
    base_length = len(text)
    adjusted_length = base_length + 355
    style = MultiMsgStyle([
        MessageStyle(offset=0, length=adjusted_length, style="color", color=color, auto_format=False),
        MessageStyle(offset=0, length=adjusted_length, style="bold", size="8", auto_format=False)
    ])
    msg = Message(text=text, style=style)
    bot.send(msg, thread_id=thread_id, thread_type=thread_type, ttl=ttl)

def get_group_members(bot, thread_id, thread_type, message_object):
    try:
        group_info = bot.fetchGroupInfo(thread_id).gridInfoMap.get(thread_id)
        if not group_info:
            return None, "Không thể lấy thông tin nhóm."
        member_ids = group_info.get('memVerList', [])
        if not member_ids:
            return None, "Nhóm không có thành viên hoặc danh sách trống."
        members = []
        for member_id in member_ids:
            if isinstance(member_id, str) and member_id.endswith('_0'):
                member_id = member_id.rsplit('_', 1)[0]
            try:
                info = bot.fetchUserInfo(member_id)
                info = info.unchanged_profiles or info.changed_profiles
                info = info.get(str(member_id))
                if info:
                    members.append({
                        'id': member_id,
                        'dName': info.zaloName,
                        'zaloName': info.zaloName
                    })
            except Exception:
                continue
        return members, None
    except ZaloAPIException as e:
        return None, f"Lỗi API: {str(e)}"
    except Exception as e:
        return None, f"Lỗi không xác định: {str(e)}"  

def make_round_avatar(avatar):
    """Tăng sáng nhẹ, cắt avatar thành hình tròn."""
    avatar = ImageEnhance.Brightness(avatar).enhance(1.2)
    w, h = avatar.size
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, w, h), fill=255)
    round_img = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    round_img.paste(avatar, (0, 0), mask)
    return round_img

def create_admin_list_image(admin_list, bot):
    print("Bắt đầu tạo ảnh danh sách admin...")
    
    WIDTH = 1500
    HEIGHT = 460
    AVATAR_SIZE = 200  # Giảm kích thước avatar để cân đối
    OVERLAY_HEIGHT = 180  # Tăng chiều cao overlay
    OVERLAY_SPACING = 40  # Tăng khoảng cách giữa các overlay
    BORDER_THICKNESS = 15  # Tăng độ dày viền
    TITLE_OVERLAY_HEIGHT = 140  # Tăng chiều cao tiêu đề

    # Tính chiều cao cần thiết
    total_height = TITLE_OVERLAY_HEIGHT + OVERLAY_SPACING + len(admin_list) * (OVERLAY_HEIGHT + OVERLAY_SPACING) + 2 * BORDER_THICKNESS + 80
    HEIGHT = max(460, total_height)
    print(f"Kích thước ảnh: {WIDTH}x{HEIGHT}, Số admin: {len(admin_list)}")

    # 1) Tạo nền ảnh
    print("Tạo nền ảnh...")
    bg_image = BackgroundGetting()
    if not bg_image:
        print("Không lấy được nền, sử dụng màu mặc định (130, 190, 255)")
        bg_image = Image.new("RGB", (WIDTH, HEIGHT), (130, 190, 255))
    bg_image = bg_image.convert("RGBA").resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    bg_image = bg_image.filter(ImageFilter.GaussianBlur(radius=20))
    print("Đã tạo và xử lý nền ảnh thành công")

    # 2) Tạo lớp phủ với hình chữ nhật bo góc
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    dominant_color = Dominant(bg_image)
    luminance = (0.299 * dominant_color[0] + 0.587 * dominant_color[1] + 0.114 * dominant_color[2]) / 255
    box_color = random.choice([
        (120, 200, 180, 100), (180, 140, 200, 100), (240, 180, 160, 100),
        (160, 200, 140, 100), (200, 160, 120, 100), (140, 180, 220, 100),
        (220, 200, 140, 100), (180, 180, 180, 105)
    ]) if luminance >= 0.5 else random.choice([
        (200, 140, 160, 105), (140, 120, 180, 105), (100, 140, 160, 105),
        (160, 140, 120, 105), (120, 160, 180, 105), (60, 60, 60, 80)
    ])
    print(f"Màu overlay được chọn: {box_color}, luminance: {luminance}")

    box_x1, box_y1 = 50, 50  # Tăng lề
    box_x2, box_y2 = WIDTH - 50, HEIGHT - 50
    draw.rounded_rectangle([(box_x1, box_y1), (box_x2, box_y2)], radius=50, fill=box_color)
    print("Đã vẽ lớp phủ chính")

    # 3) Load font
    print("Tải font chữ...")
    font_top_path = "font/5.otf"
    font_emoji_path = "font/NotoEmoji-Bold.ttf"
    try:
        font_title = ImageFont.truetype(font_top_path, 120)
        font_text = ImageFont.truetype(font_top_path, 65)
        font_emoji = ImageFont.truetype(font_emoji_path, 65)
        print("Tải font thành công")
    except Exception as e:
        logging.error(f"Lỗi load font: {e}")
        print(f"Lỗi tải font: {e}, sử dụng font mặc định")
        font_title = font_text = font_emoji = ImageFont.load_default()

    # 4) Vẽ tiêu đề "DANH SÁCH ADMIN BOT"
    print("Vẽ tiêu đề...")
    title_text = "DANH SÁCH ADMIN BOT"
    random_gradients = random.sample(GRADIENT_SETS, 3)
    title_colors = MULTICOLOR_GRADIENT
    text_bbox = draw.textbbox((0, 0), title_text, font=font_title)
    title_width = text_bbox[2] - text_bbox[0]
    title_x = (WIDTH - title_width) // 2
    title_y = box_y1 + 20
    draw_mixed_gradient_text(
        draw, title_text, (title_x, title_y), normal_font=font_title, emoji_font=font_emoji,
        gradient_colors=title_colors, shadow_offset=(2, 2)
    )
    print("Đã vẽ tiêu đề thành công")

    # 5) Vẽ danh sách admin
    print("Bắt đầu vẽ danh sách admin...")
    y_offset = box_y1 + TITLE_OVERLAY_HEIGHT + OVERLAY_SPACING
    for i, admin in enumerate(admin_list):
        print(f"Xử lý admin {i+1}: {admin['name']} (ID: {admin['id']})")
        # Tạo overlay cho admin
        overlay_admin = Image.new("RGBA", (WIDTH - 100, OVERLAY_HEIGHT), (0, 0, 0, 0))
        draw_admin = ImageDraw.Draw(overlay_admin)
        draw_admin.rounded_rectangle(
            (0, 0, WIDTH - 100, OVERLAY_HEIGHT), radius=20, fill=box_color
        )
        overlay_admin = overlay_admin.filter(ImageFilter.GaussianBlur(radius=1))
        overlay.alpha_composite(overlay_admin, (50, y_offset))
        print(f"Đã tạo overlay cho admin {admin['name']}")

        # Tải và xử lý avatar
        print(f"Tải avatar từ URL: {admin['avatar_url']}")
        try:
            resp = requests.get(admin['avatar_url'], timeout=5)
            resp.raise_for_status()
            avatar = Image.open(BytesIO(resp.content)).convert("RGBA")
            avatar = avatar.resize((AVATAR_SIZE, AVATAR_SIZE), Image.Resampling.LANCZOS)
            avatar = make_round_avatar(avatar)
            border_size = AVATAR_SIZE + 30  # Tăng kích thước viền
            border_offset = (border_size - AVATAR_SIZE) // 2
            rainbow_border = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
            draw_border = ImageDraw.Draw(rainbow_border)
            for j in range(360):
                h = j / 360
                r, g, b = colorsys.hsv_to_rgb(h, 0.5, 0.8)
                draw_border.arc([(3, 3), (border_size - 4, border_size - 4)], j, j + 1, fill=(int(r * 255), int(g * 255), int(b * 255), 255), width=8)  # Tăng độ dày viền
            overlay.alpha_composite(rainbow_border, (70 - border_offset, y_offset + (OVERLAY_HEIGHT - border_size) // 2))
            overlay.alpha_composite(avatar, (70, y_offset + (OVERLAY_HEIGHT - AVATAR_SIZE) // 2))
            print(f"Đã xử lý avatar cho admin {admin['name']}")
        except Exception as e:
            logging.error(f"Lỗi tải avatar {admin['avatar_url']}: {e}")
            print(f"Lỗi tải avatar {admin['avatar_url']}: {e}, sử dụng avatar mặc định")
            avatar = Image.new("RGBA", (AVATAR_SIZE, AVATAR_SIZE), (200, 200, 200, 255))
            avatar = make_round_avatar(avatar)
            overlay.alpha_composite(avatar, (70, y_offset + (OVERLAY_HEIGHT - AVATAR_SIZE) // 2))

        # Vẽ tên và ID admin
        name_text = admin['name']
        id_text = f"ID: {admin['id']}"
        text_x = 70 + AVATAR_SIZE + 100
        name_y = y_offset + 30
        id_y = name_y + 70
        gradient_colors = random_gradients[i % len(random_gradients)]
        for text, y in [(name_text, name_y), (id_text, id_y)]:
            text_bbox = draw.textbbox((0, 0), text, font=font_text)
            text_width = text_bbox[2] - text_bbox[0]
            safe_text_width = box_x2 - text_x - 50
            truncated_text = text if text_width <= safe_text_width else text[:int(safe_text_width / (text_width / len(text)))] + ".."
            draw_mixed_gradient_text(
                draw, truncated_text, (text_x, y), normal_font=font_text, emoji_font=font_emoji,
                gradient_colors=gradient_colors, shadow_offset=(2, 2)
            )
        print(f"Đã vẽ tên và ID cho admin {admin['name']}")

        y_offset += OVERLAY_HEIGHT + OVERLAY_SPACING

    # 6) Vẽ logo và chữ "design by Minh Vũ Shinn Cte"
    print("Vẽ logo và chữ ký...")
    logo_path = "zalo.png"
    if os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo_size = 80
            logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
            mask = Image.new("L", (logo_size, logo_size), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, logo_size, logo_size), fill=255)
            round_logo = Image.new("RGBA", (logo_size, logo_size), (0, 0, 0, 0))
            round_logo.paste(logo, (0, 0), mask)
            overlay.paste(round_logo, (box_x1 + 50, HEIGHT - logo_size - 10), round_logo)
            print("Đã vẽ logo zalo.png")
        except Exception as e:
            logging.error(f"Lỗi xử lý logo zalo.png: {e}")
            print(f"Lỗi xử lý logo zalo.png: {e}")
    else:
        print("Không tìm thấy file logo zalo.png")

    designer_text = "design by Minh Vũ Shinn Cte"
    text_bbox = draw.textbbox((0, 0), designer_text, font=font_text)
    text_w = text_bbox[2] - text_bbox[0]
    designer_x = box_x2 - text_w - 30
    designer_y = HEIGHT - 90
    draw_mixed_gradient_text(
        draw, designer_text, (designer_x, designer_y), normal_font=font_text, emoji_font=font_emoji,
        gradient_colors=get_random_gradient(), shadow_offset=(2, 2)
    )
    print("Đã vẽ chữ ký 'design by Minh Vũ Shinn Cte'")

    # 7) Gộp và lưu ảnh
    print("Gộp và lưu ảnh...")
    final_image = Image.alpha_composite(bg_image, overlay).convert("RGB")
    image_path = f"admin_list_{random.randint(1000, 9999)}.jpg"
    try:
        final_image.save(image_path, quality=95)
        print(f"Đã lưu ảnh thành công tại: {image_path}")
        return image_path, WIDTH, HEIGHT
    except Exception as e:
        logging.error(f"Lỗi khi lưu ảnh danh sách admin: {e}")
        print(f"Lỗi khi lưu ảnh: {e}")
        raise

def clean_message_log(thread_id=None, older_than_days=None):
    """Dọn dẹp message_log, có thể chỉ định thread_id hoặc thời gian."""
    log = load_message_log()
    now = time.time()
    cleaned_log = {}
    for key, user_data in log.items():
        try:
            thread_id_key, author_id = key.split('_')
            if thread_id and thread_id_key != thread_id:
                cleaned_log[key] = user_data
                continue
            if older_than_days:
                times = [t for t in user_data["message_times"] if now - t <= older_than_days * 86400]
            else:
                times = user_data["message_times"]
            if times:
                cleaned_log[key] = {"message_times": times}
        except ValueError:
            logging.error(f"Invalid key format in message_log: {key}")
            continue
    save_message_log(cleaned_log)
    return f"✅ Đã dọn dẹp message_log. Còn lại {len(cleaned_log)} bản ghi."

def clear_message_log():
    """Xóa toàn bộ message_log."""
    save_message_log({})
    return "✅ Đã xóa toàn bộ message_log. Còn lại 0 bản ghi."
    
# -----------------------------------------
# Hàm xử lý lệnh của BOT
# -----------------------------------------
def handle_bot_command(message, msg_obj, thread_id, thread_type, author_id, bot):
    if "bott" in msg_obj.content.lower():
        bot.sendReaction(msg_obj, "✅", thread_id, thread_type, reactionType=75)
    parts = msg_obj.content.split()
    if len(parts) == 1:
        # Lấy thông tin người dùng
        try:
            user_info = bot.fetchUserInfo(author_id)
            user_name = user_info.changed_profiles[author_id].zaloName
            user_avatar_url = user_info.changed_profiles[author_id].avatar
            user_cover_url = user_info.changed_profiles[author_id].cover
        except Exception as e:
            logging.error(f"Lỗi khi lấy thông tin người dùng: {e}")
            user_name = "Người dùng"
            user_avatar_url = ""
            user_cover_url = ""

        # Lấy thông tin bot
        try:
            bot_uid = "127225959075940390"
            bot_info = bot.fetchUserInfo(bot_uid)
            bot_avatar_url = bot_info.changed_profiles[bot_uid].avatar
        except Exception as e:
            logging.error(f"Lỗi khi lấy thông tin bot: {e}")
            bot_avatar_url = ""

        # Nội dung menu
        menu_text = """
## CÀI ĐẶT & QUẢN LÝ ⚙️
➜ ℹ️ bott info — Xem Thông Tin Bot
➜ 🔄 bott [ on/off ] — Bật/Tắt Bot
➜ ⚙️ bott setup [ on/off ] — Cho phép bot xử phạt
➜ 👑 bott ad [ add/del/list ] — Thêm/Xóa/Xem Admin
➜ 📚 bott preset [create/apply/delete/list] — Quản lý preset cài đặt
➜ 📋 bott rules — Xem Nội Quy Nhóm
➜ 🚫 bott rule word [lần] [phút] — Cập nhật quy tắc từ cấm
➜ 🚫 bott rule spam [tin] [giây] — Cập nhật quy tắc chống spam
➜ 🔧 bott update [cài đặt] [group_id] — Cập nhật cài đặt
➜ 🌐 bott batch [cài đặt 1 | cài đặt 2...] — Áp dụng nhiều cài đặt
➜ 👋 bott welcome [ on/off/list ] — Chế Độ Chào Mừng
➜ 📚 bott stat — Lịch sử vi phạm
➜ ⏪ bott undo [ on/off/list ] — Chế Độ Hoàn Tác
➜ 💬 bott reply [ on/off ] — Trả Lời Tag
➜ ✉️ bott pm [ on/off ] — Trả Lời Tin Nhắn Riêng
➜ 🛡️ antispam [ on/off/set ] — Chống Spam
➜ 💾 bott backup [create/list/restore/delete] — Sao lưu/khôi phục cài đặt
➜ 💾 bott cleanlog/clearlog — Dọn dẹp bộ nhớ
➜ 🔗 bott [ newlink/dislink ] — Tạo/ Hủy link tham gia nhóm
➜ ✅ bott duyet [on/off/list/all] — Quản lý duyệt thành viên
➜ ✅ bott autoduyet [on/off] — Tự động duyệt thành viên
➜ 🔍 bott find/findtag [tên] — Tìm/tag thành viên trong nhóm
➜ 🛠️ admin [ on/off ] — Bật/Tắt Chế Độ Admin
➜ 🔧 cmd [ open/close/openall/closeall/closeall safe ] — Đóng Mở Toàn Bộ Lệnh Của Bot
➜ 🔇 bott mute [ mute/unmute/list ] — Quản Lý Khóa Mõm
➜ 🚪 bott [ kick/ block ] @user — Xóa/ Chặn Thành Viên
➜ 📛 bott blacklist [add/del/list] — Quản lý danh sách đen
➜ ✅ bott skip [add/del/list] — Quản lý danh sách trắng (bỏ qua xử phạt)
➜ 📜 bott word [ on/off/add/del/list ] — Quản Lý Từ Cấm
➜ 📞 bott phone [ on/off ] — Cấm số điện thoại
➜ 📇 bott contact [ on/off ] — Cấm Danh thiếp
➜ 🔗 bott link [ on/off ] — Cấm Link
➜ 🖼️ bott img [ on/off ] — Cấm Ảnh
➜ 🎥 bott video [ on/off ] — Cấm/Cho Phép Video
➜ 😺 bott sticker [ on/off ] — Cấm Sticker
➜ 🎞️ bott gif [ on/off ] — Cấm Gif
➜ 📁 bott file [ on/off ] — Cấm File
➜ 🎙️ bott voice [ on/off ] — Cấm Voice
➜ 😊 bott emoji [ on/off ] — Cấm Emoji
➜ 📜 bott longmsg [ on/off ] — Cấm Tin nhắn Dài
➜ 🔁 bott dupe [ on/off ] — Cấm Tin Trùng Lặp
➜ 🏷️ bott tag [ on/off ] — Cấm Tag
➜ 🔞 bott asex [ on/off ] — Cấm 18+
➜ 🔞 bott vehinh [ on/off ] — Bật/Cho Phép Vẽ Hình
➜ 🗑️ bott del [image/video/sticker/link/gif/file/voice/emoji/contact/phone/msg/all] — Xóa nội dung theo loại
➜ 🌐 bott all [ on/off ] — Bật/Tắt Tất Cả Lệnh
➜ 📋 bott banlist — Xem Lệnh Cấm Hiện Tại
➜ 👥 bott groupban — Xem Nhóm Bật Lệnh Cấm"""

        # Tạo ảnh chào mừng
        image_path = create_bott_welcome_image(user_name, user_avatar_url, user_cover_url, bot_avatar_url, menu_text)

        # Gửi ảnh kèm tin nhắn menu
        bot.sendLocalImage(
            image_path,
            thread_id=thread_id,
            thread_type=thread_type,
            message=Message(text=menu_text),
            ttl=30000,
            width=1500,
            height=460
        )

        # Xóa file ảnh tạm
        delete_file(image_path)
        return
    if parts[1].lower() == 'info':
         response = (
            "THÔNG TIN BOT\n"
            "--------------\n"
            "🆙 Phiên bản         - Mới nhất\n"
            "📅 Ngày cập nhật     - 29/10/2024\n"
            "👑 Admin             - Minh Vũ Shinn Cte\n"
            "📖 Hướng dẫn         - /bot help\n"
            "⏳ Thời gian phản hồi - 1s\n"
            "⚡ Tổng lệnh hỗ trợ   - 160\n"
            "💻 Công nghệ          - Python, ZaloAPI\n"
            "🔒 Chế độ bảo vệ      - Link, Image, Video, Sticker, GIF, Sex, File, Voice, Emoji, Tin nhắn dài, Tag\n"
            "👥 Nhóm kích hoạt     - [Số nhóm]\n"
            "📢 Thông báo         - Mới mỗi giờ\n"
            "💬 Hỗ trợ            - support@example.com\n"
            "🌐 Website           - www.botMinh Vũ Shinn Cte.com\n"
            "📝 Ghi chú           - Team Minh Vũ Shinn Cte phát triển\n"
            "Chúc bạn một ngày tuyệt vời! 😊"
         )
         bot.replyMessage(Message(text=response), msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=25000)
         return
    if not is_admin(author_id):
         bot.replyMessage(Message(text="⛔ Bạn không có quyền sử dụng lệnh này!"), msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=25000)
         return

    def send_bot_response():
        try:
            parts = msg_obj.content.split()
            if len(parts) == 1:
                response = (
                    ""
                )
            else:
                act = parts[1].lower()
                if act == 'on':
                    if thread_type != ThreadType.GROUP:
                        response = "⚠️ Lệnh này chỉ dùng trong nhóm!"
                    else:
                        response = toggle_group(bot, thread_id, True)
                elif act == 'off':
                    if thread_type != ThreadType.GROUP:
                        response = "⚠️ Lệnh này chỉ dùng trong nhóm!"
                    else:
                        response = toggle_group(bot, thread_id, False)
                elif act == 'info':
                    response = (
                        "📌 Thông tin BOT\n"
                        "🆙 Phiên bản: Mới nhất\n"
                        "📅 Ngày cập nhật: 29/10/2024\n"
                        "👑 Admin: Minh Vũ Shinn Cte\n"
                        "📖 Cách dùng: /bot help\n"
                        "⏳ Thời gian phản hồi: 1s\n"
                        "⚡ Tổng lệnh hỗ trợ: 160\n"
                    )
                elif act == 'ad':
                    if len(parts) < 3:
                        response = "⚠️ Cú pháp: bot ad [add/del/list] @user"
                    else:
                        s = read_settings()
                        admin_bot = s.get("admin_bot", [])
                        sub = parts[2].lower()
                        if sub == 'add':
                            if len(parts) < 4:
                                response = "⚠️ Cú pháp: bot ad add @user"
                            else:
                                uids = extract_uids_from_mentions(msg_obj)
                                response = add_admin(bot, author_id, uids, s)
                        elif sub == 'del':
                            if len(parts) < 4:
                                response = "⚠️ Cú pháp: bot ad del @user"
                            else:
                                uids = extract_uids_from_mentions(msg_obj)
                                response = remove_admin(bot, author_id, uids, s)
                        elif sub == 'list':
                            if not admin_bot:
                                response = "⚠️️ Không có Admin BOT nào."
                            else:
                                # Tạo danh sách admin với thông tin avatar
                                admin_list = []
                                for uid in admin_bot:
                                    try:
                                        user_info = bot.fetchUserInfo(uid).changed_profiles[uid]
                                        admin_list.append({
                                            'id': uid,
                                            'name': user_info.displayName,
                                            'avatar_url': user_info.avatar
                                        })
                                    except Exception as e:
                                        logging.error(f"Lỗi khi lấy thông tin admin {uid}: {e}")
                                        admin_list.append({
                                            'id': uid,
                                            'name': "Unknown User",
                                            'avatar_url': ""
                                        })
                                admin_list.sort(key=lambda x: x['name'])
                                
                                # Tạo và gửi ảnh danh sách admin
                                image_path = None
                                try:
                                    image_path, img_width, img_height = create_admin_list_image(admin_list, bot)
                                    bot.sendLocalImage(
                                        image_path,
                                        thread_id=thread_id,
                                        thread_type=thread_type,
                                        message=Message(text="📋 Danh sách admin bot"),
                                        ttl=300000,
                                        width=img_width,
                                        height=img_height
                                    )
                                    return  # Thoát để tránh gửi response text
                                except Exception as e:
                                    logging.error(f"Lỗi khi tạo/gửi ảnh danh sách admin: {e}")
                                    # Fallback: Gửi danh sách dạng text
                                    response = ("📋 Danh sách Admin BOT:\n" +
                                                "\n".join(f"{i}. {admin['name']} (ID: {admin['id']})" 
                                                        for i, admin in enumerate(admin_list, 1)))
                                finally:
                                    if image_path and os.path.exists(image_path):
                                        try:
                                            os.remove(image_path)
                                        except Exception as e:
                                            logging.error(f"Lỗi khi xóa file ảnh {image_path}: {e}")
                        else:
                            response = f"⚠️️ Lệnh bot ad {sub} không được hỗ trợ."
                elif act == 'setup':
                    if len(parts) < 3:
                        response = "⚠️ Cú pháp: bot setup on/off"
                    else:
                        sub = parts[2].lower()
                        if sub == 'on':
                            response = setup_bot_on(bot, thread_id)
                        elif sub == 'off':
                            response = setup_bot_off(bot, thread_id)
                        else:
                            response = f"⚠️ Lệnh bot setup {sub} không được hỗ trợ."
                elif act == 'link':
                    if len(parts) < 3:
                        response = "⚠️ Cú pháp: bot link on/off"
                    else:
                        sub = parts[2].lower()
                        if sub == 'on':
                            response = set_ban_link(thread_id, True)
                        elif sub == 'off':
                            response = set_ban_link(thread_id, False)
                        else:
                            response = "⚠️ Cú pháp: bot link on/off"
                elif act == 'tag':
                    if len(parts) < 3:
                        response = "⚠️ Cú pháp: bot tag on/off"
                    else:
                        toggle = parts[2].lower()
                        if toggle in ['on', 'off']:
                            status = (toggle == 'on')
                            # Kiểm tra trạng thái hiện tại
                            settings = read_settings()
                            current_status = settings.get("ban_tag", {}).get(thread_id, False)
                            if current_status == status:
                                response = f"⚠️ Chế độ cấm tag người dùng đã được {'bật' if status else 'tắt'} trước đó."
                            else:
                                response = set_tag_ban(thread_id, status)
                        else:
                            response = "⚠️ Cú pháp: bot tag on/off"            
                elif act == 'word':
                    if len(parts) < 3:
                        response = "⚠️ Cú pháp: bot word on/off/add/del/list [từ khóa]"
                    else:
                        sub = parts[2].lower()
                        if sub == 'on':
                            response = set_word_ban(thread_id, True)
                        elif sub == 'off':
                            response = set_word_ban(thread_id, False)
                        elif sub == 'list':
                            s = read_settings()
                            words = s.get('forbidden_words', [])
                            response = "📋 Danh sách từ cấm:\n" + "\n".join(f"- {w}" for w in words) if words else "✅ Không có từ cấm nào."
                        elif sub == 'add':
                            # Lấy toàn bộ nội dung tin nhắn
                            full_content = msg_obj.content
                            # Tách các dòng, bỏ dòng đầu tiên (bot word add)
                            lines = full_content.split('\n')[1:]
                            # Lọc các từ cấm, loại bỏ khoảng trắng thừa
                            words = [line.strip() for line in lines if line.strip()]
                            
                            if not words:
                                response = "⚠️ Vui lòng cung cấp ít nhất một từ cấm, mỗi từ trên một dòng!"
                            else:
                                s = read_settings()
                                forbidden_words = s.get('forbidden_words', [])
                                results = []
                                for word in words:
                                    if word not in forbidden_words:
                                        forbidden_words.append(word)
                                        results.append(f"🟢 Từ '{word}' đã được thêm vào danh sách từ cấm.")
                                    else:
                                        results.append(f"⚠️ Từ '{word}' đã tồn tại trong danh sách từ cấm.")
                                s['forbidden_words'] = forbidden_words
                                write_settings(s)
                                response = "\n".join(results)
                        elif sub == 'del':
                            # Lấy toàn bộ nội dung tin nhắn
                            full_content = msg_obj.content
                            # Tách các dòng, bỏ dòng đầu tiên (bot word remove)
                            lines = full_content.split('\n')[1:]
                            # Lọc các từ cấm, loại bỏ khoảng trắng thừa
                            words = [line.strip() for line in lines if line.strip()]
                            
                            if not words:
                                response = "⚠️ Vui lòng cung cấp ít nhất một từ cấm, mỗi từ trên một dòng!"
                            else:
                                s = read_settings()
                                forbidden_words = s.get('forbidden_words', [])
                                results = []
                                for word in words:
                                    if word in forbidden_words:
                                        forbidden_words.remove(word)
                                        results.append(f"✅ Từ '{word}' đã được xóa khỏi danh sách từ cấm.")
                                    else:
                                        results.append(f"❌ Từ '{word}' không có trong danh sách từ cấm.")
                                s['forbidden_words'] = forbidden_words
                                write_settings(s)
                                response = "\n".join(results)
                        else:
                            response = f"⚠️ Lệnh bot word {sub} không được hỗ trợ."
                elif act == 'img':
                    if len(parts) < 3:
                        response = "⚠️ Cú pháp: bot img on/off"
                    else:
                        toggle = parts[2].lower()
                        if toggle in ['on', 'off']:
                            status = (toggle == 'on')
                            response = set_media_ban(thread_id, 'image', status)
                        else:
                            response = "⚠️ Cú pháp: bot img on/off"
                elif act == 'video':
                    if len(parts) < 3:
                        response = "⚠️ Cú pháp: bot video on/off"
                    else:
                        toggle = parts[2].lower()
                        if toggle in ['on', 'off']:
                            status = (toggle == 'on')
                            response = set_media_ban(thread_id, 'video', status)
                        else:
                            response = "⚠️ Cú pháp: bot video on/off"
                elif act == 'sticker':
                    if len(parts) < 3:
                        response = "⚠️ Cú pháp: bot sticker on/off"
                    else:
                        toggle = parts[2].lower()
                        if toggle in ['on', 'off']:
                            status = (toggle == 'on')
                            response = set_media_ban(thread_id, 'sticker', status)
                        else:
                            response = "⚠️ Cú pháp: bot sticker on/off"
                elif act == 'stickerlimit':
                    if len(parts) < 3:
                        response = show_sticker_limit_status(thread_id)
                    else:
                        sub = parts[2].lower()
                        if sub == 'on':
                            response = set_sticker_limit_enabled(thread_id, True)
                        elif sub == 'off':
                            response = set_sticker_limit_enabled(thread_id, False)
                        elif sub == 'rule':
                            if len(parts) < 5:
                                response = "⚠️ Cú pháp: bott stickerlimit rule <số_sticker> <số_phút>\nVí dụ: bott stickerlimit rule 2 5"
                            else:
                                try:
                                    max_stickers = int(parts[3])
                                    time_minutes = int(parts[4])
                                    if max_stickers < 1 or time_minutes < 1:
                                        response = "⚠️ Số sticker và số phút phải lớn hơn 0"
                                    else:
                                        response = set_sticker_limit_rule(thread_id, max_stickers, time_minutes)
                                except ValueError:
                                    response = "⚠️ Số sticker và số phút phải là số nguyên"
                        elif sub == 'status':
                            response = show_sticker_limit_status(thread_id)
                        else:
                            response = "⚠️ Cú pháp:\n• bott stickerlimit on/off\n• bott stickerlimit rule 2 5\n• bott stickerlimit status"
                elif act == 'reactionlimit':
                    if len(parts) < 3:
                        response = show_reaction_limit_status(thread_id)
                    else:
                        sub = parts[2].lower()
                        if sub == 'on':
                            response = set_reaction_limit_enabled(thread_id, True)
                        elif sub == 'off':
                            response = set_reaction_limit_enabled(thread_id, False)
                        elif sub == 'rule':
                            if len(parts) < 5:
                                response = "⚠️ Cú pháp: bott reactionlimit rule <số_reaction> <số_phút>\nVí dụ: bott reactionlimit rule 5 1"
                            else:
                                try:
                                    max_reactions = int(parts[3])
                                    time_minutes = int(parts[4])
                                    if max_reactions < 1 or time_minutes < 1:
                                        response = "⚠️ Số reaction và số phút phải lớn hơn 0"
                                    else:
                                        response = set_reaction_limit_rule(thread_id, max_reactions, time_minutes)
                                except ValueError:
                                    response = "⚠️ Số reaction và số phút phải là số nguyên"
                        elif sub == 'status':
                            response = show_reaction_limit_status(thread_id)
                        else:
                            response = "⚠️ Cú pháp:\n• bott reactionlimit on/off\n• bott reactionlimit rule 5 1\n• bott reactionlimit status"                          
                elif act == 'gif':
                    if len(parts) < 3:
                        response = "⚠️ Cú pháp: bot gif on/off"
                    else:
                        toggle = parts[2].lower()
                        if toggle in ['on', 'off']:
                            status = (toggle == 'on')
                            response = set_media_ban(thread_id, 'gif', status)
                        else:
                            response = "⚠️ Cú pháp: bot gif on/off"
                elif act == 'stickerphoto':
                    if len(parts) < 3:
                        response = "Cú pháp: bot stickerphoto on/off"
                    else:
                        toggle = parts[2].lower()
                        if toggle in ['on', 'off']:
                            status = (toggle == 'on')
                            response = set_stickerphoto_ban(thread_id, status)
                        else:
                            response = "Cú pháp: bot stickerphoto on/off"            
                elif act == 'asex':
                    if len(parts) < 3:
                        response = "⚠️ Cú pháp: bot asex on/off"
                    else:
                        toggle = parts[2].lower()
                        if toggle in ['on', 'off']:
                            status = (toggle == 'on')
                            response = set_media_ban(thread_id, 'sex', status)
                        else:
                            response = "⚠️ Cú pháp: bot asex on/off"
                elif act == 'file':
                    if len(parts) < 3:
                        response = "⚠️ Cú pháp: bot file on/off"
                    else:
                        toggle = parts[2].lower()
                        if toggle in ['on', 'off']:
                            status = (toggle == 'on')
                            response = set_media_ban(thread_id, 'file', status)
                        else:
                            response = "⚠️ Cú pháp: bot file on/off"
                elif act == 'voice':
                    if len(parts) < 3:
                        response = "⚠️ Cú pháp: bot voice on/off"
                    else:
                        toggle = parts[2].lower()
                        if toggle in ['on', 'off']:
                            status = (toggle == 'on')
                            response = set_media_ban(thread_id, 'voice', status)
                        else:
                            response = "⚠️ Cú pháp: bot voice on/off"
                elif act == 'emoji':
                    if len(parts) < 3:
                        response = "⚠️ Cú pháp: bot emoji on/off"
                    else:
                        toggle = parts[2].lower()
                        if toggle in ['on', 'off']:
                            status = (toggle == 'on')
                            response = set_media_ban(thread_id, 'emoji', status)
                        else:
                            response = "⚠️ Cú pháp: bot emoji on/off"
                # Phần thêm cho duplicate:
                elif act == 'dupe':
                    if len(parts) < 3:
                        response = "⚠️ Cú pháp: bot dupe on/off"
                    else:
                        toggle = parts[2].lower()
                        if toggle in ['on', 'off']:
                            status = (toggle == 'on')
                            response = set_duplicate_ban(thread_id, status)
                        else:
                            response = "⚠️ Cú pháp: bot dupe on/off"
                elif act == 'contact':
                    if len(parts) < 3:
                        response = "⚠️ Cú pháp: bot contact on/off"
                    else:
                        toggle = parts[2].lower()
                        if toggle in ['on', 'off']:
                            status = (toggle == 'on')
                            response = set_contact_card_ban(thread_id, status)
                        else:
                            response = "⚠️ Cú pháp: bot contact on/off"
                elif act == 'phone':
                    if len(parts) < 3:
                        response = "⚠️ Cú pháp: bot phone on/off"
                    else:
                        toggle = parts[2].lower()
                        if toggle in ['on', 'off']:
                            status = (toggle == 'on')
                            response = set_phone_ban(thread_id, status)
                        else:
                            response = "⚠️ Cú pháp: bot phone on/off"            
                elif act == 'all':
                    if thread_type != ThreadType.GROUP:
                        response = "⚠️ Lệnh này chỉ dùng trong nhóm!"
                    elif not check_admin_group(bot, thread_id) and not is_admin(author_id):
                        response = "🚫 Bạn cần là quản trị viên nhóm hoặc admin bot!"
                    else:
                        if len(parts) < 3 or parts[2].lower() not in ['on', 'off']:
                            response = "📝 Cú pháp: bot all on/off"
                        else:
                            status = parts[2].lower() == 'on'
                            group = bot.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
                            group_name = group.name

                            responses = [
                                "⚙️ CẤU HÌNH TẤT CẢ CHỨC NĂNG",
                                "══════════════════════",
                                f"🏷️ Nhóm: {group_name}",
                                f"🆔 ID: {thread_id}",
                                "══════════════════════"
                            ]
                            total = 0

                            def short(res, name, on_text, off_text):
                                nonlocal total
                                if any(k in res for k in ["bật trước đó", "tắt trước đó", "cấm trước đó"]):
                                    return f"{name} → ⚠️ Đã thiết lập"
                                total += 1
                                return f"{name} → {'✅ ' + on_text if status else '❌ ' + off_text}"

                            # BOT & ADMIN
                            responses.append(short(toggle_group(bot, thread_id, status), "🤖 Bot", "Bật", "Tắt"))
                            setup_res = setup_bot_on(bot, thread_id) if status else setup_bot_off(bot, thread_id)
                            responses.append("🛠️ Cấu hình → ✅ Cập nhật" if "Đã cập nhật" in setup_res else "🛠️ Cấu hình → ⚠️ Không thay đổi")

                            # LINK
                            responses.append(short(set_ban_link(thread_id, status), "🔗 Link", "Cấm", "Mở"))

                            # MEDIA
                            media_cmds = [
                                ('image', '📷 Ảnh'), ('video', '🎥 Video'), ('sticker', '💟 Sticker'),
                                ('gif', '🌀 GIF'), ('sex', '🔞 Nhạy cảm'), ('file', '📁 Tệp'),
                                ('voice', '🎙️ Thoại'), ('emoji', '😄 Emoji'),
                                ('contact', '👤 Danh thiếp'), ('phone', '☎️ SĐT'),
                                ('stickerlimit', '🎭 Hạn chế sticker')
                            ]
                            for cmd, name in media_cmds:
                                if cmd == 'contact':
                                    res = set_contact_card_ban(thread_id, status)
                                elif cmd == 'phone':
                                    res = set_phone_ban(thread_id, status)
                                elif cmd == 'stickerlimit':  # THÊM ĐIỀU KIỆN NÀY
                                    res = set_sticker_limit_enabled(tid, status)    
                                else:
                                    res = set_media_ban(thread_id, cmd, status)
                                responses.append(short(res, name, "Cấm", "Mở"))

                            # KHÁC
                            other_cmds = [
                                ('longmsg', '🧾 Tin dài'), ('duplicate', '🔁 Trùng lặp'),
                                ('tag', '🏷️ Tag'), ('word', '🚫 Từ cấm'), ('vehinh', '🎨 Vẽ hình')
                            ]
                            for cmd, name in other_cmds:
                                fn = {
                                    'longmsg': set_longmsg_ban, 'duplicate': set_duplicate_ban,
                                    'tag': set_tag_ban, 'word': set_word_ban, 'vehinh': set_vehinh_ban
                                }[cmd]
                                responses.append(short(fn(thread_id, status), name, "Cấm", "Mở"))

                            responses.append("═════════════════════")
                            responses.append(f"🎯 Hoàn tất! {total} chức năng đã được {'🔓 bật' if status else '🔒 tắt'}.")
                            response = "\n".join(responses)


                elif act == 'banlist':
                    s = read_settings()
                    config_str = "📋 *Cài đặt cấm hiện tại của nhóm:*\n\n"
                    allowed_threads = s.get("allowed_threads", [])
                    bot_status = "✅" if thread_id in allowed_threads else "❌"
                    config_str += f" 🤖 Bot: {bot_status}\n"
                    group_admins = s.get("group_admins", {})
                    setup_status = "✅" if thread_id in group_admins else "❌"
                    config_str += f" ⚙️ Bot setup: {setup_status}\n"
                    ban_link = s.get("ban_link", {}).get(thread_id, False)
                    link_status = "✅" if ban_link else "❌"
                    config_str += f" 🔗 Gửi link: {link_status}\n"
                    ban_image = s.get("ban_image", {}).get(thread_id, False)
                    image_status = "✅" if ban_image else "❌"
                    config_str += f" 🖼️ Gửi ảnh: {image_status}\n"
                    ban_video = s.get("ban_video", {}).get(thread_id, False)
                    video_status = "✅" if ban_video else "❌"
                    config_str += f" 🎥 Gửi video: {video_status}\n"
                    ban_sticker = s.get("ban_sticker", {}).get(thread_id, False)
                    sticker_status = "✅" if ban_sticker else "❌"
                    config_str += f" 💬 Sticker: {sticker_status}\n"
                    rule = get_sticker_limit_rule(thread_id)
                    if rule:
                        status = "✅" if rule['enabled'] else "❌"
                        config_str += f" 🎭 Hạn chế sticker ({rule['max_stickers']}/{rule['time_minutes']} phút): {status}\n"
                    else:
                        config_str += f" 🎭 Hạn chế sticker: ❌ Chưa cài đặt\n"
                    reaction_rule = get_reaction_limit_rule(thread_id)   
                    ban_gif = s.get("ban_gif", {}).get(thread_id, False)
                    gif_status = "✅" if ban_gif else "❌"
                    config_str += f" 🎞️ GIF: {gif_status}\n"
                    ban_file = s.get("ban_file", {}).get(thread_id, False)
                    file_status = "✅" if ban_file else "❌"
                    config_str += f" 📄 File: {file_status}\n"
                    ban_voice = s.get("ban_voice", {}).get(thread_id, False)
                    voice_status = "✅" if ban_voice else "❌"
                    config_str += f" 🎤 Voice: {voice_status}\n"
                    ban_emoji = s.get("ban_emoji", {}).get(thread_id, False)
                    ban_stickerphoto = s.get("ban_stickerphoto", {}).get(thread_id, False)
                    stickerphoto_status = "✅" if ban_stickerphoto else "❌"
                    config_str += f" Sticker ảnh (tự chế): {stickerphoto_status}\n"
                    emoji_status = "✅" if ban_emoji else "❌"
                    config_str += f" 😀 Emoji: {emoji_status}\n"
                    ban_longmsg = s.get("ban_longmsg", {}).get(thread_id, False)
                    longmsg_status = "✅" if ban_longmsg else "❌"
                    config_str += f" ⏱️ Tin nhắn dài: {longmsg_status}\n"
                    ban_duplicate = s.get("ban_duplicate", {}).get(thread_id, False)
                    duplicate_status = "✅" if ban_duplicate else "❌"
                    config_str += f" 📑 Nội dung trùng lặp: {duplicate_status}\n"
                    ban_tag = s.get("ban_tag", {}).get(thread_id, False)
                    tag_status = "✅" if ban_tag else "❌"
                    config_str += f" 🏷️ Tag người dùng: {tag_status}\n"
                    ban_sex = s.get("ban_sex", {}).get(thread_id, False)
                    sex_status = "✅" if ban_sex else "❌"
                    config_str += f" 🔞 Ảnh sex: {sex_status}\n"
                    ban_word = s.get("ban_word", {}).get(thread_id, False)
                    word_status = "✅" if ban_word else "❌"
                    config_str += f" 📜 Từ khóa cấm: {word_status}\n"
                    ban_contact_card = s.get("ban_contact_card", {}).get(thread_id, False)
                    contact_card_status = "✅" if ban_contact_card else "❌"
                    config_str += f" 📇 Danh thiếp: {contact_card_status}\n"
                    ban_vehinh = s.get("ban_vehinh", {}).get(thread_id, False)
                    vehinh_status = "✅" if ban_vehinh else "❌"
                    config_str += f" ✍️ Vẽ hình: {vehinh_status}\n"
                    ban_phone = s.get("ban_phone", {}).get(thread_id, False)
                    phone_status = "✅" if ban_phone else "❌"
                    config_str += f" 📱 Số điện thoại: {phone_status}\n"
                    response = config_str
                elif act == 'rules':
                    response = None  # Khởi tạo response để tránh lỗi
                    if thread_type != ThreadType.GROUP:
                        response = "⚠️ Lệnh này chỉ dùng trong nhóm!"
                    else:
                        # Lấy thông tin nhóm
                        try:
                            group = bot.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
                            group_name = group.name
                            group_avatar_url = group.avt
                        except Exception as e:
                            logging.warning(f"Không thể lấy thông tin nhóm, sử dụng giá trị mặc định: {e}")
                            group_name = "Nhóm Không Xác Định"
                            group_avatar_url = ""

                        # Đọc cài đặt
                        s = read_settings()
                        rules = s.get("rules", {})
                        word_rule = rules.get("word", {"threshold": 3, "duration": 30})
                        spam_rule = rules.get("spam", {"max_msgs": 5, "time_win": 5})
                        allowed_threads = s.get("allowed_threads", [])
                        bot_status = thread_id in allowed_threads
                        group_admins = s.get("group_admins", {})
                        setup_status = thread_id in group_admins
                        ban_link = s.get("ban_link", {}).get(thread_id, False)
                        ban_image = s.get("ban_image", {}).get(thread_id, False)
                        ban_video = s.get("ban_video", {}).get(thread_id, False)
                        ban_sticker = s.get("ban_sticker", {}).get(thread_id, False)
                        ban_gif = s.get("ban_gif", {}).get(thread_id, False)
                        ban_sex = s.get("ban_sex", {}).get(thread_id, False)
                        ban_file = s.get("ban_file", {}).get(thread_id, False)
                        ban_voice = s.get("ban_voice", {}).get(thread_id, False)
                        ban_emoji = s.get("ban_emoji", {}).get(thread_id, False)
                        ban_longmsg = s.get("ban_longmsg", {}).get(thread_id, False)
                        ban_duplicate = s.get("ban_duplicate", {}).get(thread_id, False)
                        ban_tag = s.get("ban_tag", {}).get(thread_id, False)
                        ban_word = s.get("ban_word", {}).get(thread_id, False)
                        ban_vehinh = s.get("ban_vehinh", {}).get(thread_id, False)
                        forbidden_words = s.get("forbidden_words", [])
                        ban_contact_card = s.get("ban_contact_card", {}).get(thread_id, False)
                        ban_phone = s.get("ban_phone", {}).get(thread_id, False)

                        # Tạo danh sách nội dung nội quy với kích thước font đồng bộ với menu.py
                        rules_text = [
                            {"text": "📌 Nội quy nhóm", "normal_font_size": 120, "emoji_font_size": 120},  # Dòng 1: Tiêu đề
                            {"text": f"{group_name}", "normal_font_size": 80, "emoji_font_size": 80},      # Dòng 2: Tên nhóm
                            {"text": f"🆔 ID: {thread_id}", "normal_font_size": 65, "emoji_font_size": 65},
                            {"text": f"🤖 Bot: ", "normal_font_size": 65, "emoji_font_size": 65, "status": bot_status},
                            {"text": f"⚙️ Setup: ", "normal_font_size": 65, "emoji_font_size": 65, "status": setup_status},
                            {"text": "📌 Quy tắc cấm", "normal_font_size": 65, "emoji_font_size": 65},
                            {"text": f"🔗 Link: ", "normal_font_size": 65, "emoji_font_size": 65, "status": ban_link},
                            {"text": f"🖼️ Ảnh: ", "normal_font_size": 65, "emoji_font_size": 65, "status": ban_image},
                            {"text": f"🎥 Video: ", "normal_font_size": 65, "emoji_font_size": 65, "status": ban_video},
                            {"text": f"💬 Sticker: ", "normal_font_size": 65, "emoji_font_size": 65, "status": ban_sticker},
                            {"text": f"🎞️ GIF: ", "normal_font_size": 65, "emoji_font_size": 65, "status": ban_gif},
                            {"text": f"🔞 Nội dung 18+: ", "normal_font_size": 65, "emoji_font_size": 65, "status": ban_sex},
                            {"text": f"📄 File: ", "normal_font_size": 65, "emoji_font_size": 65, "status": ban_file},
                            {"text": f"🎤 Voice: ", "normal_font_size": 65, "emoji_font_size": 65, "status": ban_voice},
                            {"text": f"😀 Emoji: ", "normal_font_size": 65, "emoji_font_size": 65, "status": ban_emoji},
                            {"text": f"🗨️ Tin nhắn dài: ", "normal_font_size": 65, "emoji_font_size": 65, "status": ban_longmsg},
                            {"text": f"📑 Tin trùng lặp: ", "normal_font_size": 65, "emoji_font_size": 65, "status": ban_duplicate},
                            {"text": f"🏷️ Tag: ", "normal_font_size": 65, "emoji_font_size": 65, "status": ban_tag},
                            {"text": f"📜 Từ cấm: ", "normal_font_size": 65, "emoji_font_size": 65, "status": ban_word},
                            {"text": f"📇 Danh thiếp: ", "normal_font_size": 65, "emoji_font_size": 65, "status": ban_contact_card},
                            {"text": f"📱 Số điện thoại: ", "normal_font_size": 65, "emoji_font_size": 65, "status": ban_phone},
                            {"text": f"✍️ Vẽ hình: ", "normal_font_size": 65, "emoji_font_size": 65, "status": ban_vehinh},
                            {"text": f"🚫 Vi phạm từ cấm {word_rule['threshold']} lần: Mute {word_rule['duration']} phút", "normal_font_size": 65, "emoji_font_size": 65},
                            {"text": f"🚫 Spam {spam_rule['max_msgs']} tin trong {spam_rule['time_win']}s: Kick & Block", "normal_font_size": 65, "emoji_font_size": 65},
                        ]

                        # Thêm danh sách từ cấm (giới hạn tối đa 5 từ)
                        MAX_WORDS_DISPLAY = 5
                        if ban_word and forbidden_words:
                            rules_text.append({"text": "📜 Danh sách từ cấm:", "normal_font_size": 65, "emoji_font_size": 65})
                            displayed_words = forbidden_words[:MAX_WORDS_DISPLAY]
                            for word in displayed_words:
                                rules_text.append({"text": f"- {word}", "normal_font_size": 65, "emoji_font_size": 65})
                            if len(forbidden_words) > MAX_WORDS_DISPLAY:
                                rules_text.append({"text": f"- Và {len(forbidden_words) - MAX_WORDS_DISPLAY} từ khác", "normal_font_size": 65, "emoji_font_size": 65})

                        # Hàm tạo ảnh nội quy
                        def create_rules_image(group_name, group_avatar_url, rules_text):
                            WIDTH = 3000
                            HEIGHT = 3000
                            OVERLAY_MARGIN = 30
                            MIN_FONT_SIZE = 30
                            FONT_REDUCTION_STEP = 5
                            COLUMN_SPACING = 50
                            HORIZONTAL_LINE_MARGIN = 20

                            # Hàm vẽ nút ON/OFF
                            def create_toggle_switch(is_on, width=60, height=34, corner_radius=17):
                                toggle = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                                draw = ImageDraw.Draw(toggle)
                                bg_color = (52, 199, 89, 255) if is_on else (255, 0, 0, 255)
                                draw.rounded_rectangle(
                                    (0, 0, width, height),
                                    radius=corner_radius,
                                    fill=bg_color
                                )
                                circle_size = height - 4
                                circle_x = width - circle_size - 2 if is_on else 2
                                circle_y = 2
                                draw.ellipse(
                                    (circle_x, circle_y, circle_x + circle_size, circle_y + circle_size),
                                    fill=(255, 255, 255, 255)
                                )
                                return toggle

                            # Tính chiều cao nội dung
                            def calculate_content_height(text_list, spacing):
                                total_height = 0
                                line_heights = []
                                for item in text_list:
                                    normal_font = ImageFont.truetype("font/5.otf", item["normal_font_size"])
                                    bbox = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), item["text"], font=normal_font)
                                    line_height = bbox[3] - bbox[1]
                                    line_heights.append(line_height)
                                    total_height += line_height + spacing
                                return total_height, line_heights

                            # Tách rules_text thành 2 cột
                            forbidden_words_text = [item for item in rules_text if item["text"].startswith("- ") or item["text"] == "📜 Danh sách từ cấm:"]
                            rules_content = [item for item in rules_text if not (item["text"].startswith("- ") or item["text"] == "📜 Danh sách từ cấm:")]

                            # Tính chiều cao và spacing động
                            spacing = 30  # Khoảng cách dòng lớn hơn để tránh đè
                            rules_height, rules_line_heights = calculate_content_height(rules_content, spacing)
                            forbidden_height, forbidden_line_heights = calculate_content_height(forbidden_words_text, spacing)
                            avatar_size = 300
                            overlay_height = HEIGHT - 140  # Trừ lề trên/dưới
                            content_area_height = overlay_height - avatar_size - 60  # Trừ avatar và tên nhóm

                            total_height = max(rules_height, forbidden_height)
                            if total_height > content_area_height:
                                # Tính spacing động để phân bố đều
                                extra_height = total_height - content_area_height
                                num_lines = max(len(rules_content), len(forbidden_words_text))
                                if num_lines > 1:
                                    spacing = min(40, (content_area_height - sum(rules_line_heights)) / (len(rules_content) - 1))
                                    if spacing < 10:
                                        spacing = 10
                                        # Giảm font nếu spacing quá nhỏ
                                        while total_height > content_area_height and min(item["normal_font_size"] for item in rules_content + forbidden_words_text) > MIN_FONT_SIZE:
                                            for item in rules_content + forbidden_words_text:
                                                item["normal_font_size"] = max(MIN_FONT_SIZE, item["normal_font_size"] - FONT_REDUCTION_STEP)
                                                item["emoji_font_size"] = max(MIN_FONT_SIZE, item["emoji_font_size"] - FONT_REDUCTION_STEP)
                                            rules_height, rules_line_heights = calculate_content_height(rules_content, spacing)
                                            forbidden_height, forbidden_line_heights = calculate_content_height(forbidden_words_text, spacing)
                                            total_height = max(rules_height, forbidden_height)

                            # Tạo nền
                            bg_image = BackgroundGetting()
                            if not bg_image:
                                bg_image = Image.new("RGB", (WIDTH, HEIGHT), (130, 190, 255))
                            bg_image = bg_image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS).convert("RGBA")
                            bg_image = bg_image.filter(ImageFilter.GaussianBlur(radius=20))

                            # Vẽ overlay
                            overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
                            draw = ImageDraw.Draw(overlay)
                            dominant_color = Dominant(bg_image)
                            luminance = (0.299 * dominant_color[0] + 0.587 * dominant_color[1] + 0.114 * dominant_color[2]) / 255
                            box_color = random.choice([
                                (120, 200, 180, 100), (180, 140, 200, 100), (240, 180, 160, 100),
                                (160, 200, 140, 100), (200, 160, 120, 100), (140, 180, 220, 100),
                                (220, 200, 140, 100), (180, 180, 180, 105)
                            ]) if luminance >= 0.5 else random.choice([
                                (200, 140, 160, 105), (140, 120, 180, 105), (100, 140, 160, 105),
                                (160, 140, 120, 105), (120, 160, 180, 105), (60, 60, 60, 80)
                            ])
                            box_x1, box_y1 = OVERLAY_MARGIN, 70
                            box_x2, box_y2 = WIDTH - OVERLAY_MARGIN, HEIGHT - 70
                            draw.rounded_rectangle([(box_x1, box_y1), (box_x2, box_y2)], radius=50, fill=box_color)

                            # Load font
                            font_top_path = "font/5.otf"
                            font_emoji_path = "font/NotoEmoji-Bold.ttf"
                            try:
                                font_title = ImageFont.truetype(font_top_path, 120)
                                font_name = ImageFont.truetype(font_top_path, 80)
                                font_text = ImageFont.truetype(font_top_path, 65)
                                font_icon = ImageFont.truetype(font_emoji_path, 65)
                            except Exception as e:
                                logging.error(f"Lỗi load font: {e}")
                                font_title = font_name = font_text = font_icon = ImageFont.load_default()

                            # Xử lý avatar nhóm
                            avatar = FetchImage(group_avatar_url)
                            if not avatar:
                                avatar = Image.new("RGBA", (avatar_size, avatar_size), (200, 200, 200, 255))
                            avatar = avatar.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS).convert("RGBA")
                            mask = Image.new("L", (avatar_size, avatar_size), 0)
                            ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
                            border_size = avatar_size + 20
                            border_offset = (border_size - avatar_size) // 2
                            rainbow_border = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
                            draw_border = ImageDraw.Draw(rainbow_border)
                            for i in range(360):
                                h = i / 360
                                r, g, b = colorsys.hsv_to_rgb(h, 0.5, 0.8)
                                draw_border.arc([(3, 3), (border_size - 4, border_size - 4)], i, i + 1, fill=(int(r * 255), int(g * 255), int(b * 255), 255), width=6)
                            overlay.paste(rainbow_border, (box_x1 + 20 - border_offset, box_y1 + 20 - border_offset), rainbow_border)
                            overlay.paste(avatar, (box_x1 + 20, box_y1 + 20), mask)

                            # Vẽ tiêu đề và tên nhóm
                            title_text = "📌 Nội quy nhóm"
                            title_bbox = draw.textbbox((0, 0), title_text, font=font_title)
                            title_width = title_bbox[2] - title_bbox[0]
                            title_x = (box_x1 + box_x2 - title_width) // 2
                            title_y = box_y1 + 20
                            draw_mixed_gradient_text(
                                draw, title_text, (title_x, title_y), font_title, font_icon,
                                MULTICOLOR_GRADIENT, shadow_offset=(2, 2)
                            )

                            name_text = group_name
                            name_bbox = draw.textbbox((0, 0), name_text, font=font_name)
                            name_width = name_bbox[2] - name_bbox[0]
                            name_x = (box_x1 + box_x2 - name_width) // 2
                            name_y = title_y + 120
                            draw_mixed_gradient_text(
                                draw, name_text, (name_x, name_y), font_name, font_icon,
                                get_random_gradient(), shadow_offset=(2, 2)
                            )

                            # Vẽ đường kẻ ngang
                            line_y = name_y + 90
                            draw.line(
                                [(box_x1 + HORIZONTAL_LINE_MARGIN, line_y), (box_x2 - HORIZONTAL_LINE_MARGIN, line_y)],
                                fill=(255, 255, 255, 200), width=4
                            )

                            # Vẽ 2 cột nội dung
                            start_y = line_y + 20
                            column_width = (box_x2 - box_x1 - COLUMN_SPACING) // 2
                            rules_x = box_x1 + 20
                            forbidden_x = box_x1 + column_width + COLUMN_SPACING
                            safe_text_width = column_width - 50

                            def truncate_text(line, font, max_width):
                                if not line:
                                    return line
                                truncated = line
                                ellipsis = ".."
                                ellipsis_width = draw.textbbox((0, 0), ellipsis, font=font)[2]
                                while True:
                                    text_bbox = draw.textbbox((0, 0), truncated + ellipsis, font=font)
                                    text_width = text_bbox[2] - text_bbox[0]
                                    if text_width <= max_width or len(truncated) <= 3:
                                        break
                                    if ord(truncated[-1]) > 0xFFFF:
                                        truncated = truncated[:-1]
                                    else:
                                        truncated = truncated[:-1]
                                return truncated + ellipsis if truncated != line else line

                            # Vẽ cột nội quy
                            current_y = start_y
                            gradients_for_rules = random.sample(GRADIENT_SETS, len(rules_content))
                            for i, item in enumerate(rules_content):
                                text = truncate_text(item["text"], font_text, safe_text_width)
                                text_bbox = draw.textbbox((0, 0), text, font=font_text)
                                text_width = text_bbox[2] - text_bbox[0]
                                x_text = rules_x + (column_width - text_width) // 2
                                draw_mixed_gradient_text(
                                    draw, text, (x_text, current_y), font_text, font_icon,
                                    MULTICOLOR_GRADIENT if i % 2 == 0 else gradients_for_rules[i], shadow_offset=(2, 2)
                                )
                                if "status" in item:
                                    toggle_img = create_toggle_switch(item["status"])
                                    toggle_x = x_text + text_width + 10
                                    toggle_y = current_y + (rules_line_heights[i] - 34) // 2
                                    overlay.paste(toggle_img, (int(toggle_x), int(toggle_y)), toggle_img)
                                current_y += rules_line_heights[i] + spacing

                            # Vẽ cột từ cấm
                            current_y = start_y
                            gradients_for_forbidden = random.sample(GRADIENT_SETS, len(forbidden_words_text))
                            for i, item in enumerate(forbidden_words_text):
                                text = truncate_text(item["text"], font_text, safe_text_width)
                                text_bbox = draw.textbbox((0, 0), text, font=font_text)
                                text_width = text_bbox[2] - text_bbox[0]
                                x_text = forbidden_x + (column_width - text_width) // 2
                                draw_mixed_gradient_text(
                                    draw, text, (x_text, current_y), font_text, font_icon,
                                    MULTICOLOR_GRADIENT if i % 2 == 0 else gradients_for_forbidden[i], shadow_offset=(2, 2)
                                )
                                current_y += forbidden_line_heights[i] + spacing

                            # Vẽ logo và chữ "design by Minh Vũ Shinn Cte"
                            logo_path = "zalo.png"
                            if os.path.exists(logo_path):
                                try:
                                    logo = Image.open(logo_path).convert("RGBA")
                                    logo_size = 80
                                    logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                                    mask = Image.new("L", (logo_size, logo_size), 0)
                                    ImageDraw.Draw(mask).ellipse((0, 0, logo_size, logo_size), fill=255)
                                    round_logo = Image.new("RGBA", (logo_size, logo_size), (0, 0, 0, 0))
                                    round_logo.paste(logo, (0, 0), mask)
                                    logo_x = box_x1 + 50
                                    logo_y = HEIGHT - logo_size - 50
                                    overlay.paste(round_logo, (logo_x, logo_y), round_logo)
                                except Exception as e:
                                    logging.error(f"Lỗi khi xử lý logo zalo.png: {e}")

                            designer_text = "design by Minh Vũ Shinn Cte"
                            text_bbox = draw.textbbox((0, 0), designer_text, font=font_text)
                            text_w = text_bbox[2] - text_bbox[0]
                            text_h = text_bbox[3] - text_bbox[1]
                            designer_x = box_x2 - text_w - 20
                            designer_y = HEIGHT - text_h - 20
                            draw_mixed_gradient_text(
                                draw, designer_text, (designer_x, designer_y), font_text, font_icon,
                                get_random_gradient(), shadow_offset=(2, 2)
                            )

                            # Vẽ thời gian
                            time_line = datetime.now(timezone(timedelta(hours=7))).strftime("%H:%M:%S %Y-%m-%d")
                            dt = datetime.strptime(time_line, "%H:%M:%S %Y-%m-%d")
                            left_info = f"⏰ {dt.strftime('%H:%M')}   📆 {dt.strftime('%d-%m')}"
                            text_bbox = draw.textbbox((0, 0), left_info, font=font_text)
                            text_h = text_bbox[3] - text_bbox[1]
                            left_x = box_x1 + 150
                            left_y = HEIGHT - text_h - 50
                            draw_mixed_gradient_text(
                                draw, left_info, (left_x, left_y), font_text, font_icon,
                                MULTICOLOR_GRADIENT, shadow_offset=(2, 2)
                            )

                            # Gộp và lưu ảnh
                            final_image = Image.alpha_composite(bg_image, overlay).convert("RGB")
                            image_path = f"rules_{thread_id}.jpg"
                            final_image.save(image_path, quality=95)
                            return image_path

                        # Tạo và gửi ảnh
                        image_path = None
                        try:
                            image_path = create_rules_image(group_name, group_avatar_url, rules_text)
                            bot.sendLocalImage(
                                image_path,
                                thread_id=thread_id,
                                thread_type=thread_type,
                                message=Message(text="📌 Nội quy nhóm"),
                                ttl=300000,
                                width=1500,
                                height=1500
                            )
                        except Exception as e:
                            logging.error(f"Lỗi khi tạo/gửi ảnh nội quy: {e}")
                            text_response = "\n".join(item["text"] for item in rules_text)
                            bot.replyMessage(Message(text=text_response), msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=25000)
                            response = "📌 Đã gửi nội quy nhóm dưới dạng text do lỗi tạo/gửi ảnh."
                        finally:
                            if image_path:
                                delete_file(image_path)
                elif act == 'longmsg':
                    if len(parts) < 3:
                        response = "⚠️ Cú pháp: bot longmsg on/off"
                    else:
                        toggle = parts[2].lower()
                        if toggle in ['on', 'off']:
                            status = (toggle == 'on')
                            response = set_longmsg_ban(thread_id, status)
                        else:
                            response = "⚠️ Cú pháp: bot longmsg on/off"                
                elif act == 'mute':
                    if len(parts) < 3:
                        response = "⚠️ Cú pháp: bot mute/unmute/list [@user]"
                    else:
                        sub = parts[2].lower()
                        if sub == 'list':
                            response = print_muted_users_in_group(bot, thread_id)
                        else:
                            if thread_type != ThreadType.GROUP or not check_admin_group(bot, thread_id):
                                response = "⚠️ Lệnh này chỉ dùng trong nhóm với quyền phù hợp!"
                            else:
                                uids = extract_uids_from_mentions(msg_obj)
                                response = add_users_to_ban_list(bot, uids, thread_id, "Quản trị viên cấm")
                elif act == 'unmute':
                    if len(parts) < 3:
                        response = "⚠️ Cú pháp: bot unmute [@user]"
                    else:
                        if thread_type != ThreadType.GROUP:
                            response = "⚠️ Lệnh này chỉ dùng trong nhóm!"
                        else:
                            uids = extract_uids_from_mentions(msg_obj)
                            response = remove_users_from_ban_list(bot, uids, thread_id)
                elif act == 'block':
                    if len(parts) < 3:
                        response = "⚠️ Cú pháp: bot block/unblock/list [@user]"
                    else:
                        sub = parts[2].lower()
                        if sub == 'list':
                            response = print_blocked_users_in_group(bot, thread_id)
                        else:
                            if thread_type != ThreadType.GROUP or not check_admin_group(bot, thread_id):
                                response = "⚠️ Lệnh này chỉ dùng trong nhóm với quyền phù hợp!"
                            else:
                                uids = extract_uids_from_mentions(msg_obj)
                                response = block_users_from_group(bot, uids, thread_id)
                elif act == 'mutestk':
                    if thread_type != ThreadType.GROUP:
                        response = "⚠️ Lệnh này chỉ dùng trong nhóm!"
                    elif not check_admin_group(bot, thread_id) and not is_admin(author_id):
                        response = "⚠️ Bạn cần là quản trị viên nhóm hoặc admin bot để dùng lệnh này!"
                    else:
                        # Lấy UID từ mention
                        mentioned_uids = extract_uids_from_mentions(msg_obj)
                        if not mentioned_uids:
                            response = "⚠️ Vui lòng tag (@) ít nhất một thành viên!\nVí dụ: bott mutestk @Tèo"
                        else:
                            responses = []
                            for uid in mentioned_uids:
                                res = set_mute_sticker_user(bot, thread_id, uid, True)
                                responses.append(res)
                            response = "\n".join(responses)
                
                elif act == 'unmutestk':
                    if thread_type != ThreadType.GROUP:
                        response = "⚠️ Lệnh này chỉ dùng trong nhóm!"
                    elif not check_admin_group(bot, thread_id) and not is_admin(author_id):
                        response = "⚠️ Bạn cần là quản trị viên nhóm hoặc admin bot để dùng lệnh này!"
                    else:
                        mentioned_uids = extract_uids_from_mentions(msg_obj)
                        if not mentioned_uids:
                            response = "⚠️ Vui lòng tag (@) ít nhất một thành viên!\nVí dụ: bott unmutestk @Tèo"
                        else:
                            responses = []
                            for uid in mentioned_uids:
                                res = set_mute_sticker_user(bot, thread_id, uid, False)
                                responses.append(res)
                            response = "\n".join(responses)                
                elif act == 'unblock':
                    if len(parts) < 3:
                        response = "⚠️ Cú pháp: bot unblock [UID1,UID2,...]"
                    else:
                        if thread_type != ThreadType.GROUP:
                            response = "⚠️ Lệnh này chỉ dùng trong nhóm!"
                        else:
                            uids = [uid.strip() for uid in parts[2].split(',') if uid.strip()]
                            response = unblock_users_from_group(bot, uids, thread_id) if uids else "⚠️ Không có UID hợp lệ!"
                elif act == 'kick':
                    if len(parts) < 3:
                        response = "⚠️ Cú pháp: bot kick [@user]"
                    else:
                        if thread_type != ThreadType.GROUP or not check_admin_group(bot, thread_id):
                            response = "⚠️ Lệnh này chỉ dùng trong nhóm với quyền phù hợp!"
                        else:
                            uids = extract_uids_from_mentions(msg_obj)
                            response = kick_users_from_group(bot, uids, thread_id)
                elif act == 'rule':
                    if len(parts) < 5:
                        response = "⚠️ Cú pháp: bot rule word [số lần] [số phút] hoặc bot rule spam [số tin nhắn] [số giây]"
                    else:
                        rule_type = parts[2].lower()
                        if rule_type not in ["word", "spam"]:
                            response = "⚠️ Loại quy tắc không hợp lệ! Sử dụng: bot rule word [số lần] [số phút] hoặc bot rule spam [số tin nhắn] [số giây]"
                        else:
                            try:
                                thresh, param = int(parts[3]), int(parts[4])
                            except ValueError:
                                response = "⚠️ Số lần/tin nhắn và số phút/giây phải là số nguyên!"
                            else:
                                if thread_type != ThreadType.GROUP:
                                    response = "⚠️ Lệnh này chỉ hoạt động trong nhóm!"
                                else:
                                    s = read_settings()
                                    s.setdefault("rules", {})
                                    if rule_type == "word":
                                        s["rules"]["word"] = {"threshold": thresh, "duration": param}
                                        write_settings(s)
                                        response = f"✅ Đã cập nhật quy tắc từ cấm: Vi phạm {thresh} lần sẽ bị mute {param} phút."
                                    elif rule_type == "spam":
                                        s["rules"]["spam"] = {"max_msgs": thresh, "time_win": param}
                                        write_settings(s)
                                        response = f"✅ Đã cập nhật quy tắc spam: Gửi quá {thresh} tin nhắn trong {param} giây sẽ bị kick và block."
                elif act == 'stats':
                    if thread_type != ThreadType.GROUP:
                        response = "⚠️ Lệnh này chỉ hoạt động trong nhóm!"
                    elif not check_admin_group(bot, thread_id) and not is_admin(author_id):
                        response = "⚠️ Bạn cần có quyền quản trị nhóm hoặc là admin bot để sử dụng lệnh này!"
                    else:
                        try:
                            s = read_settings()
                            violations = s.get("violations", {})
                            muted_users = s.get("muted_users", [])
                            group_name = bot.fetchGroupInfo(thread_id).gridInfoMap[thread_id].name

                            # Thống kê vi phạm
                            violation_stats = {
                                "profanity_count": 0,  # Từ cấm
                                "spam_count": 0,       # Spam
                                "sensitive_image_count": 0,  # Nội dung nhạy cảm
                                "muted_users_count": 0,      # Số người bị mute
                                "user_violations": {}        # Chi tiết vi phạm theo người dùng
                            }

                            # Thu thập dữ liệu vi phạm trong nhóm
                            for key, data in violations.items():
                                if key.startswith(f"{thread_id}_"):
                                    user_id = key.split("_")[1]
                                    user_name = get_user_name_by_id(bot, user_id)
                                    violation_stats["user_violations"][user_id] = {
                                        "name": user_name,
                                        "profanity_count": data.get("profanity_count", 0),
                                        "spam_count": data.get("spam_count", 0),
                                        "sensitive_image_count": data.get("sensitive_image_count", 0)
                                    }
                                    violation_stats["profanity_count"] += data.get("profanity_count", 0)
                                    violation_stats["spam_count"] += data.get("spam_count", 0)
                                    violation_stats["sensitive_image_count"] += data.get("sensitive_image_count", 0)

                            # Đếm số người bị mute trong nhóm
                            now = time.time()
                            for user in muted_users:
                                if user["thread_id"] == thread_id and user["muted_until"] > now:
                                    violation_stats["muted_users_count"] += 1

                            # Tạo phản hồi thống kê
                            responses = [
                                f"📊 THỐNG KÊ HÀNH VI VI PHẠM",
                                f"👥 Nhóm: {group_name} (ID: {thread_id})",
                                "════════════════════════"
                            ]

                            # Tổng quan vi phạm
                            responses.append("📈 Tổng quan vi phạm:")
                            responses.append(f"  🔍 Từ cấm: {violation_stats['profanity_count']} lần")
                            responses.append(f"  🚨 Spam: {violation_stats['spam_count']} lần")
                            responses.append(f"  🔞 Nội dung nhạy cảm: {violation_stats['sensitive_image_count']} lần")
                            responses.append(f"  🔇 Thành viên bị mute: {violation_stats['muted_users_count']} người")
                            responses.append("════════════════════════")

                            # Chi tiết theo thành viên (nếu có)
                            if violation_stats["user_violations"]:
                                responses.append("📋 Chi tiết vi phạm theo thành viên:")
                                for user_id, data in violation_stats["user_violations"].items():
                                    responses.append(f"  👤 {data['name']} (ID: {user_id}):")
                                    if data["profanity_count"] > 0:
                                        responses.append(f"    - Từ cấm: {data['profanity_count']} lần")
                                    if data["spam_count"] > 0:
                                        responses.append(f"    - Spam: {data['spam_count']} lần")
                                    if data["sensitive_image_count"] > 0:
                                        responses.append(f"    - Nội dung nhạy cảm: {data['sensitive_image_count']} lần")
                                responses.append("════════════════════════")

                            responses.append("✅ Hoàn tất thống kê!")
                            response = "\n".join(responses)
                        except Exception as e:
                            logging.error(f"Lỗi khi thống kê vi phạm: {e}")
                            response = f"⚠️ Lỗi khi thống kê vi phạm: {str(e)}"
                elif act == 'reset':
                    if not is_admin(author_id):
                        response = "Chỉ admin bot mới có quyền sử dụng lệnh này."
                    elif len(parts) < 3:
                        response = "Cú pháp: bot reset <id1> <id2> ... | bot reset hidden | bot reset all confirm"
                    else:
                        sub_cmd = parts[2].lower()

                        if sub_cmd == 'hidden':
                            response = reset_hidden_groups(bot)

                        elif sub_cmd == 'all':
                            confirm = ' '.join(parts[3:]).lower()
                            if confirm != 'confirm':
                                response = "DANGER ZONE\nXóa tất cả nhóm?\n→ bot reset all confirm"
                            else:
                                allowed = s.get("allowed_threads", [])
                                response = reset_group_config(bot, allowed)

                        else:
                            group_ids = parts[2:]
                            response = reset_group_config(bot, group_ids)                        
                elif act == 'groupban':
                    response = list_forbidden_groups(bot)
                elif act == 'skip':
                    if len(parts) < 3:
                        response = "⚠️ Cú pháp: bot skip add/del/list @user1 @user2 ... hoặc bot skip add/del id1 id2 ..."
                    else:
                        sub = parts[2].lower()
                        s = read_settings()
                        excluded_users = s.get("excluded_users", [])
                        if sub == 'list':
                            response = ("📋 Danh sách trắng:\n" +
                                        "\n".join(f"- {get_user_name_by_id(bot, uid)} (ID: {uid})" for uid in excluded_users)
                                       ) if excluded_users else "✅ Không có ai trong danh sách trắng"
                        elif sub in ['add', 'del']:
                            # Lấy danh sách UID từ mentions
                            uids_from_mentions = extract_uids_from_mentions(msg_obj)
                            # Lấy danh sách UID từ phần còn lại của lệnh (nếu có)
                            remaining_parts = parts[3:] if len(parts) > 3 else []
                            uids_from_input = []
                            for part in remaining_parts:
                                # Loại bỏ ký tự @ nếu có (trong trường hợp nhập @id)
                                clean_part = part.lstrip('@')
                                if clean_part.isdigit():  # Kiểm tra xem có phải là ID hợp lệ
                                    uids_from_input.append(clean_part)
                            
                            # Gộp danh sách UID từ mentions và input, loại bỏ trùng lặp
                            uids = list(set(uids_from_mentions + uids_from_input))
                            
                            if not uids:
                                response = "⚠️ Vui lòng cung cấp ít nhất một @user hoặc ID hợp lệ!"
                            else:
                                if sub == 'add':
                                    added_count = 0
                                    for uid in uids:
                                        if uid not in excluded_users:
                                            excluded_users.append(uid)
                                            added_count += 1
                                    s["excluded_users"] = excluded_users
                                    write_settings(s)
                                    response = f"✅ Đã thêm {added_count} người vào danh sách trắng"
                                elif sub == 'del':
                                    removed_count = 0
                                    for uid in uids:
                                        if uid in excluded_users:
                                            excluded_users.remove(uid)
                                            removed_count += 1
                                    s["excluded_users"] = excluded_users
                                    write_settings(s)
                                    response = f"✅ Đã xóa {removed_count} người khỏi danh sách trắng."
                        else:
                            response = f"⚠️️ Lệnh bot skip {sub} không được hỗ trợ."
                elif act == 'update':
                    if thread_type != ThreadType.GROUP:
                        response = "⚠️ Lệnh này chỉ dùng trong nhóm!"
                    else:
                        # Tách cài đặt và thread_ids
                        parts = ' '.join(parts[2:]).split('|')
                        settings = [s.strip() for s in parts[:-1] if s.strip()]
                        thread_ids = parts[-1].strip().split()
                        if not settings or not thread_ids:
                            response = "⚠️ Cú pháp: bot update <setting1> | <setting2> | ... | <thread_id1> <thread_id2> ..."
                        else:
                            responses = ["📋 KẾT QUẢ ÁP DỤNG CÀI ĐẶT"]
                            responses.append("════════════════════════")
                            for tid in thread_ids:
                                try:
                                    group = bot.fetchGroupInfo(tid).gridInfoMap[tid]
                                    group_name = group.name
                                    responses.append(f"👥 Nhóm: {group_name} (ID: {tid})")
                                    for setting in settings:
                                        set_parts = setting.split()
                                        cmd = set_parts[0].lower()
                                        status = set_parts[1].lower() if len(set_parts) > 1 else None
                                        if cmd == 'on' and not status:
                                            res = toggle_group(bot, tid, True)
                                        elif cmd == 'off' and not status:
                                            res = toggle_group(bot, tid, False)
                                        elif cmd == 'setup' and status in ['on', 'off']:
                                            res = setup_bot_on(bot, tid) if status == 'on' else setup_bot_off(bot, tid)
                                        elif cmd in ['link', 'image', 'video', 'sticker', 'gif', 'sex', 'file', 'voice', 'emoji', 'longmsg', 'dupe', 'tag', 'word', 'contact', 'phone', 'vehinh'] and status in ['on', 'off']:
                                            if cmd == 'link':
                                                res = set_ban_link(tid, status == 'on')
                                            elif cmd == 'word':
                                                res = set_word_ban(tid, status == 'on')
                                            elif cmd in ['longmsg', 'dupe', 'tag']:
                                                res = {'longmsg': set_longmsg_ban, 'dupe': set_duplicate_ban, 'tag': set_tag_ban}[cmd](tid, status == 'on')
                                            elif cmd == 'contact':
                                                res = set_contact_card_ban(tid, status == 'on')
                                            elif cmd == 'phone':
                                                res = set_phone_ban(tid, status == 'on')
                                            elif cmd == 'vehinh':
                                                res = set_vehinh_ban(tid, status == 'on')
                                            else:
                                                res = set_media_ban(tid, cmd, status == 'on')
                                        else:
                                            res = f"⚠️ Cài đặt '{setting}' không hợp lệ"
                                        responses.append(f"  {setting}: {res}")
                                    responses.append("════════════════════════")
                                except Exception as e:
                                    responses.append(f"⚠️ Lỗi với nhóm ID {tid}: {str(e)}")
                                    responses.append("════════════════════════")
                            response = "\n".join(responses) + "\n✅ Hoàn tất áp dụng cài đặt!"
                elif act == 'batch':
                    if thread_type != ThreadType.GROUP:
                        response = "⚠️ Lệnh này chỉ dùng trong nhóm!"
                    else:
                        # Tách các cài đặt
                        settings = [s.strip() for s in ' '.join(parts[2:]).split('|') if s.strip()]
                        if not settings:
                            response = "⚠️ Cú pháp: bot batch <setting1> | <setting2> | ..."
                        else:
                            responses = ["📋 KẾT QUẢ ÁP DỤNG CÀI ĐẶT", "════════════════════════"]
                            try:
                                group = bot.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
                                group_name = group.name
                                # Từ điển ánh xạ cài đặt với emoji
                                config_icons = {
                                    'on': '✅', 'off': '❌', 'setup': '⚙️', 'link': '🔗', 'image': '🖼️',
                                    'video': '🎥', 'sticker': '💬', 'gif': '🎞️', 'sex': '🔞', 'file': '📄',
                                    'voice': '🎤', 'emoji': '😀', 'longmsg': '🗨️', 'duplicate': '📑',
                                    'tag': '🏷️', 'word': '📜', 'contact': '📇', 'phone': '📱'
                                }
                                # Tách lệnh 'on' hoặc 'off' để xử lý trước
                                toggle_setting = None
                                other_settings = []
                                for setting in settings:
                                    if setting.lower() in ['on', 'off']:
                                        toggle_setting = setting
                                    else:
                                        other_settings.append(setting)
                                # Xử lý lệnh 'on' hoặc 'off' trước nếu có
                                if toggle_setting:
                                    cmd = toggle_setting.lower()
                                    res = toggle_group(bot, thread_id, cmd == 'on')
                                    responses.append(f"  {config_icons[cmd]} {res}")
                                    responses.append("════════════════════════")
                                # Xử lý các cài đặt còn lại theo thứ tự
                                for i, setting in enumerate(other_settings):
                                    set_parts = setting.split()
                                    cmd = set_parts[0].lower()
                                    status = set_parts[1].lower() if len(set_parts) > 1 else None
                                    icon = config_icons.get(cmd, '⚠️')
                                    # Xử lý lệnh
                                    if cmd == 'setup' and status in ['on', 'off']:
                                        res = setup_bot_on(bot, thread_id) if status == 'on' else setup_bot_off(bot, thread_id)
                                        # Format lại để khớp output
                                        res = "Cấu hình: 🟢 BẬT" if status == 'on' else "Cấu hình: 🔴 TẮT"
                                    elif cmd in ['link', 'image', 'video', 'sticker', 'gif', 'sex', 'file', 'voice', 'emoji', 'longmsg', 'duplicate', 'tag', 'word', 'contact', 'phone', 'vehinh'] and status in ['on', 'off']:
                                        if cmd == 'link':
                                            res = set_ban_link(thread_id, status == 'on')
                                        elif cmd == 'word':
                                            res = set_word_ban(thread_id, status == 'on')
                                        elif cmd in ['longmsg', 'duplicate', 'tag']:
                                            res = {'longmsg': set_longmsg_ban, 'duplicate': set_duplicate_ban, 'tag': set_tag_ban}[cmd](thread_id, status == 'on')
                                        elif cmd == 'contact':
                                            res = set_contact_card_ban(thread_id, status == 'on')
                                        elif cmd == 'phone':
                                            res = set_phone_ban(thread_id, status == 'on')
                                        elif cmd == 'vehinh':
                                            res = set_vehinh_ban(thread_id, status == 'on')
                                        else:
                                            res = set_media_ban(thread_id, cmd, status == 'on')
                                    else:
                                        res = f"Cài đặt '{setting}' không hợp lệ"
                                    # Sửa lỗi "dupe" và "img" bằng cách ánh xạ
                                    if cmd == 'dupe' and status in ['on', 'off']:
                                        res = set_duplicate_ban(thread_id, status == 'on')
                                        icon = config_icons.get('duplicate', '⚠️')
                                    elif cmd == 'img' and status in ['on', 'off']:
                                        res = set_media_ban(thread_id, 'image', status == 'on')
                                        icon = config_icons.get('image', '⚠️')
                                    # Thêm kết quả với định dạng
                                    indent = " " if cmd == 'setup' else "  "
                                    # Loại bỏ ⚠️ nếu res đã có nó
                                    if res.startswith('⚠️'):
                                        res = res[2:].strip()
                                    responses.append(f"{indent}{icon} {res}")
                                    # Thêm divider sau cài đặt đầu tiên nếu không có 'on' hoặc 'off'
                                    if i == 0 and not toggle_setting:
                                        responses.append("════════════════════════")
                                responses.append("════════════════════════")
                                responses.append("✅ Hoàn tất áp dụng cài đặt!")
                            except Exception as e:
                                responses.append(f"  ⚠️ Lỗi: {str(e)}")
                                responses.append("════════════════════════")
                                responses.append("✅ Hoàn tất áp dụng cài đặt!")
                            response = "\n".join(responses)
                elif act == 'welcome':
                    if not is_admin(author_id):
                        response = "❌ Chỉ admin bot mới có quyền sử dụng lệnh này."
                    else:
                        parts = ' '.join(parts[2:]).strip().split(maxsplit=1)
                        action = parts[0].lower() if parts else ""
                        param = parts[1] if len(parts) > 1 else ""

                        if action not in ["on", "off", "list"]:
                            response = f"⚠️ Cú pháp: bot welcome [on|off|list] <group_id hoặc tag nhóm>."
                        elif action == "list":
                            excluded_groups = list_excluded_groups()
                            if not excluded_groups:
                                response = "📋 Danh sách nhóm bị loại khỏi sự kiện chào mừng trống."
                            else:
                                response = "📋 Danh sách nhóm bị loại khỏi sự kiện chào mừng:\n" + "\n".join(
                                    [f"{i+1}. {grp['group_name']} (ID: {grp['group_id']})" for i, grp in enumerate(excluded_groups)]
                                )
                            send_reply_with_style(bot, response, msg_obj, thread_id, thread_type, ttl=120000)
                            return  # Thoát để tránh gửi response dưới dạng text thông thường
                        else:
                            group = fetch_group_info(param, msg_obj, bot)
                            if group is None:
                                response = f"⚠️ Cú pháp: bot welcome {action} <group_id hoặc tag nhóm>.\nKhông thể lấy thông tin nhóm."
                            else:
                                group_id, group_name = group
                                if action == "off":
                                    if add_excluded_group(group_id, group_name):
                                        response = f"❌ Đã tắt chế độ Welcome cho nhóm:\n👥 {group_name}\n🆔 {group_id}"
                                    else:
                                        response = f"⚠️ Nhóm: {group_name}\n🆔 {group_id}\n đã được tắt trước đó."
                                elif action == "on":
                                    if remove_excluded_group(group_id):
                                        response = f"✅ Đã bật chế độ Welcome cho nhóm:\n👥 {group_name}\n🆔 {group_id}"
                                    else:
                                        response = f"⚠️ Nhóm: {group_name}\n🆔 {group_id}\n đã được bật trước đó."
                                send_reply_with_style(bot, response, msg_obj, thread_id, thread_type, ttl=120000)
                                return  # Thoát để tránh gửi response dưới dạng text thông thường
                elif act == 'sos':
                    if thread_type != ThreadType.GROUP:
                        response = "⚠️ Lệnh này chỉ dùng trong nhóm!"
                    else:
                        if not is_admin(author_id):
                            error_msg = "• Bạn Không Có Quyền! Chỉ có admin mới có thể sử dụng lệnh này."
                            style_error = MultiMsgStyle(
                                [
                                    MessageStyle(
                                        offset=0,
                                        length=len(error_msg),
                                        style="color",
                                        color="#db342e",
                                        auto_format=False,
                                    ),
                                    MessageStyle(
                                        offset=0,
                                        length=len(error_msg),
                                        style="bold",
                                        size="16",
                                        auto_format=False,
                                    ),
                                ]
                            )
                            bot.replyMessage(Message(text=error_msg, style=style_error), msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=25000)
                            return  # Early return is fine since response is not used
                        try:
                            # Existing sos logic
                            current_status = group_chat_status.get(thread_id, 0)
                            new_status = 1 if current_status == 0 else 0
                            group_chat_status[thread_id] = new_status
                            bot.changeGroupSetting(thread_id, lockSendMsg=new_status)
                            action = "Đóng chat thành công!" if new_status == 1 else "Mở chat thành công!"
                            style_action = MultiMsgStyle(
                                [
                                    MessageStyle(
                                        offset=0,
                                        length=len(action),
                                        style="color",
                                        color="#db342e",
                                        auto_format=False,
                                    ),
                                    MessageStyle(
                                        offset=0,
                                        length=len(action),
                                        style="bold",
                                        size="16",
                                        auto_format=False,
                                    ),
                                ]
                            )
                            bot.replyMessage(Message(text=action, style=style_action), msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=25000)
                            return  # Early return after sending styled message
                        except Exception as e:
                            response = f"Lỗi khi thay đổi cài đặt nhóm: {str(e)}"
                            style_error = MultiMsgStyle(
                                [
                                    MessageStyle(
                                        offset=0,
                                        length=len(response),
                                        style="color",
                                        color="#db342e",
                                        auto_format=False,
                                    ),
                                    MessageStyle(
                                        offset=0,
                                        length=len(response),
                                        style="bold",
                                        size="16",
                                        auto_format=False,
                                    ),
                                ]
                            )
                            bot.replyMessage(Message(text=response, style=style_error), msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=25000)
                            return
                elif act == 'newlink':
                    if thread_type != ThreadType.GROUP:
                        send_message_with_style(bot, "🔴 Lệnh này chỉ có thể sử dụng trong nhóm!", thread_id, thread_type)
                        return
                    if not check_admin_group(bot, thread_id):
                        send_message_with_style(bot, "🔴 Bạn cần có quyền quản trị nhóm để sử dụng lệnh này!", thread_id, thread_type)
                        return
                    print(f"Nhận lệnh: {message}")
                    bot.sendReaction(msg_obj, "✅", thread_id, thread_type, reactionType=75)
                    try:
                        print(f"Đang tạo link mới cho nhóm {thread_id}")
                        result = bot.newlink(grid=thread_id)
                        print(f"Full API response: {result}")
                        if result.get("success"):
                            new_link = result.get("new_link")
                            response = f"🟢 Link nhóm mới đã được tạo: {new_link}" if new_link else "🟢 Link nhóm đã được tạo nhưng không nhận được URL mới. Vui lòng kiểm tra trong cài đặt nhóm!"
                        else:
                            error_code = result.get("error_code")
                            error_message = result.get("error_message", "Lỗi không xác định")
                            response = "🟢 Đã đổi link nhóm thành công! Vui lòng kiểm tra trong cài đặt nhóm để lấy link mới." if error_code == 1337 else f"🔴 Lỗi khi tạo link: {error_message} (Mã lỗi: {error_code})"
                    except ZaloAPIException as e:
                        print(f"Lỗi ZaloAPIException: {str(e)}")
                        response = f"🔴 Lỗi khi tạo link: {str(e)}"
                    except Exception as e:
                        print(f"Lỗi chung: {str(e)}")
                        response = f"🔴 Đã xảy ra lỗi: {str(e)}"
                    send_message_with_style(bot, response, thread_id, thread_type)
                    return
                elif act == 'dislink':
                    if thread_type != ThreadType.GROUP:
                        send_message_with_style(bot, "🔴 Lệnh này chỉ có thể sử dụng trong nhóm!", thread_id, thread_type)
                        return
                    if not check_admin_group(bot, thread_id):
                        send_message_with_style(bot, "🔴 Bạn cần có quyền quản trị nhóm để sử dụng lệnh này!", thread_id, thread_type)
                        return
                    print(f"Nhận lệnh: {message}")
                    bot.sendReaction(msg_obj, "✅", thread_id, thread_type, reactionType=75)
                    try:
                        print(f"Đang vô hiệu hóa link cho nhóm {thread_id}")
                        result = bot.dislink(grid=thread_id)
                        response = "🟢 Link nhóm đã được vô hiệu hóa thành công!" if result.get("success") else f"🔴 Lỗi khi vô hiệu hóa link: {result.get('error_message', 'Lỗi không xác định')} (Mã lỗi: {result.get('error_code')})"
                    except ZaloAPIException as e:
                        print(f"Lỗi ZaloAPIException: {str(e)}")
                        response = f"🔴 Lỗi khi vô hiệu hóa link: {str(e)}"
                    except Exception as e:
                        print(f"Lỗi chung: {str(e)}")
                        response = f"🔴 Đã xảy ra lỗi: {str(e)}"
                    send_message_with_style(bot, response, thread_id, thread_type)
                    return
                elif act == 'duyet':
                    if thread_type != ThreadType.GROUP:
                        response = "⚠️ Lệnh này chỉ dùng trong nhóm!"
                    elif not check_admin_group(bot, thread_id) and not is_admin(author_id):
                        response = "⚠️ Bạn cần có quyền quản trị nhóm hoặc là admin bot để sử dụng lệnh này!"
                    else:
                        if len(parts) < 3:
                            response = "⚠️ Cú pháp: bot duyet on/off/list/all"
                        else:
                            sub = parts[2].lower()
                            try:
                                group_info = bot.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
                                pending_members = group_info.pendingApprove.get('uids', [])
                                
                                if sub == 'list':
                                    if not pending_members:
                                        response = "✅ Hiện tại không có thành viên nào đang chờ duyệt."
                                    else:
                                        response = f"📋 Số thành viên đang chờ duyệt: {len(pending_members)} thành viên."
                                
                                elif sub == 'all':
                                    if not pending_members:
                                        response = "✅ Hiện tại không có thành viên nào đang chờ duyệt."
                                    else:
                                        approved_count = 0
                                        error_count = 0
                                        for member_id in pending_members:
                                            try:
                                                if hasattr(bot, 'handleGroupPending'):
                                                    bot.handleGroupPending(member_id, thread_id)
                                                    approved_count += 1
                                                time.sleep(3)  # Delay to avoid system errors
                                            except Exception as e:
                                                logging.error(f"Lỗi khi duyệt thành viên {member_id}: {e}")
                                                error_count += 1
                                        response = f"✅ Đã duyệt {approved_count} thành viên. "
                                        if error_count > 0:
                                            response += f"Có {error_count} lỗi xảy ra khi duyệt."
                                
                                elif sub in ['on', 'off']:
                                    new_value = 0 if sub == 'on' else 1  # on: disable joinAppr (auto-approve), off: enable joinAppr
                                    try:
                                        bot.changeGroupSetting(groupId=thread_id, joinAppr=new_value)
                                        response = f"✅ Đã {'bật' if sub == 'on' else 'tắt'} tính năng tự động duyệt thành viên mới."
                                    except Exception as e:
                                        response = f"⚠️ Lỗi khi thay đổi cài đặt: {str(e)}"
                                
                                else:
                                    response = "⚠️ Cú pháp: bot duyet on/off/list/all"
                            
                            except Exception as e:
                                logging.error(f"Lỗi khi xử lý lệnh duyetmem: {e}")
                                response = f"⚠️ Đã xảy ra lỗi khi xử lý lệnh duyetmem: {str(e)}" 
                elif act == 'vehinh':
                    if len(parts) < 3:
                        response = "⚠️ Cú pháp: bot vehinh on/off"
                    else:
                        toggle = parts[2].lower()
                        if toggle in ['on', 'off']:
                            status = (toggle == 'on')
                            response = set_vehinh_ban(thread_id, status)
                        else:
                            response = "⚠️ Cú pháp: bot vehinh on/off"                
                elif act == 'find':
                    if thread_type != ThreadType.GROUP:
                        response = "⚠️ Lệnh này chỉ hoạt động trong nhóm."
                    else:
                        parts = message.strip().split(" ", 2)
                        if len(parts) < 3 or not parts[2].strip():
                            response = "⚠️ Nhập tên thành viên cần tìm.\nVí dụ: bot finduser Tèo"
                        else:
                            search_term = parts[2].strip().lower()
                            members, error = get_group_members(bot, thread_id, thread_type, msg_obj)
                            if error:
                                response = error
                            else:
                                found_members = [
                                    member for member in members 
                                    if search_term == member['zaloName'].lower() or
                                    search_term in member['zaloName'].lower() or
                                    search_term in "".join(c[0] for c in member['zaloName'].split()).lower()
                                ]
                                if not found_members:
                                    response = f"🔎 Không tìm thấy thành viên nào có tên chứa '{search_term}'."
                                else:
                                    response = f"🔎 Danh sách thành viên '{search_term}' tìm thấy hoặc có tên gần giống:\n\n"
                                    for i, member in enumerate(found_members[:100], 1):
                                        response += f"{i}.\n- Tên: {member['zaloName']}, ID: {member['id']}\n\n"
                elif act == 'findtag':
                    if thread_type != ThreadType.GROUP:
                        response = "⚠️ Lệnh này chỉ hoạt động trong nhóm."
                    else:
                        if not is_admin(author_id):
                            response = "⚠️ Chỉ admin bot mới có thể sử dụng lệnh này."
                        else:
                            parts = message.strip().split(" ", 2)
                            if len(parts) < 3 or not parts[2].strip():
                                response = "⚠️ Nhập tên thành viên cần tag.\nVí dụ: bot findtag Nam"
                            else:
                                search_term = parts[2].strip().lower()
                                members, error = get_group_members(bot, thread_id, thread_type, msg_obj)
                                if error:
                                    response = error
                                else:
                                    found_members = [
                                        member for member in members 
                                        if search_term == member['zaloName'].lower() or
                                        search_term in member['zaloName'].lower() or
                                        search_term in "".join(c[0] for c in member['zaloName'].split()).lower()
                                    ]
                                    if not found_members:
                                        response = f"🔎 Không tìm thấy thành viên nào có tên chứa '{search_term}'."
                                    else:
                                        text = ""
                                        mentions = []
                                        offset = 0
                                        for member in found_members:
                                            user_id = str(member['id'])
                                            user_name = member['zaloName']
                                            text += f"{user_name} "
                                            mentions.append(Mention(uid=user_id, offset=offset, length=len(user_name), auto_format=False))
                                            offset += len(user_name) + 1
                                        bot.replyMessage(
                                            Message(text=text.strip(), mention=MultiMention(mentions)),
                                            msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=60000
                                        )
                                        return
                elif act == 'del':
                    if thread_type != ThreadType.GROUP:
                        response = "⚠️ Lệnh này chỉ hoạt động trong nhóm!"
                    elif not check_admin_group(bot, thread_id) and not is_admin(author_id):
                        response = "⚠️ Bạn cần có quyền quản trị nhóm hoặc là admin bot để sử dụng lệnh này!"
                    else:
                        if len(parts) < 3:
                            response = "⚠️ Cú pháp: bot del img/vd/sticker/link/gif/file/voice/emoji/contact/phone/msg/all"
                        else:
                            sub = parts[2].lower()
                            try:
                                # Lấy danh sách tin nhắn trong nhóm
                                group_data = bot.getRecentGroup(thread_id)
                                messages = group_data.groupMsgs if hasattr(group_data, 'groupMsgs') else []
                                deleted_count = 0
                                type_name = {
                                    'img': 'ảnh',
                                    'vd': 'video',
                                    'sticker': 'sticker',
                                    'link': 'link',
                                    'gif': 'GIF',
                                    'file': 'file',
                                    'voice': 'thoại',
                                    'emoji': 'emoji',
                                    'contact': 'danh thiếp',
                                    'phone': 'số điện thoại',
                                    'msg': 'văn bản',
                                    'all': 'tất cả',
                                    'vehinh': 'vẽ hình'
                                }
                                if sub == 'all':
                                    for msg in messages:
                                        try:
                                            msg_id = getattr(msg, 'msgId', getattr(msg, 'globalMsgId', None))
                                            owner_id = getattr(msg, 'uidFrom', getattr(msg, 'ownerId', None))
                                            cli_msg_id = getattr(msg, 'cliMsgId', None)
                                            bot.deleteGroupMsg(
                                                msgId=msg_id,
                                                ownerId=owner_id,
                                                clientMsgId=cli_msg_id,
                                                groupId=thread_id
                                            )
                                            deleted_count += 1
                                            time.sleep(0.5)  # Chờ 0.5 giây để tránh bị giới hạn API
                                        except Exception as e:
                                            logging.error(f"Lỗi khi xóa tin nhắn {msg_id}: {e}")
                                    response = f"✅ Đã xóa {deleted_count} tin nhắn trong nhóm."
                                elif sub in type_name:
                                    for msg in messages:
                                        try:
                                            should_delete = (
                                                (sub == 'img' and getattr(msg, 'msgType', '') == 'chat.photo') or
                                                (sub == 'vd' and getattr(msg, 'msgType', '') == 'chat.video') or
                                                (sub == 'sticker' and getattr(msg, 'msgType', '') == 'chat.sticker') or
                                                (sub == 'link' and is_url_in_message(msg)) or
                                                (sub == 'gif' and getattr(msg, 'msgType', '') == 'chat.gif') or
                                                (sub == 'file' and getattr(msg, 'msgType', '') == 'chat.file') or
                                                (sub == 'voice' and getattr(msg, 'msgType', '') == 'chat.voice') or
                                                (sub == 'emoji' and is_emoji_message(msg)) or
                                                (sub == 'contact' and getattr(msg, 'msgType', '') == 'chat.contact') or
                                                (sub == 'phone' and is_phone_number_message(msg)) or
                                                (sub == 'msg' and getattr(msg, 'msgType', '') == 'chat.msg') or
                                                (sub == 'vehinh' and getattr(msg, 'msgType', '') == 'chat.vehinh')
                                            )
                                            if should_delete:
                                                msg_id = getattr(msg, 'msgId', getattr(msg, 'globalMsgId', None))
                                                owner_id = getattr(msg, 'uidFrom', getattr(msg, 'ownerId', None))
                                                cli_msg_id = getattr(msg, 'cliMsgId', None)
                                                bot.deleteGroupMsg(
                                                    msgId=msg_id,
                                                    ownerId=owner_id,
                                                    clientMsgId=cli_msg_id,
                                                    groupId=thread_id
                                                )
                                                deleted_count += 1
                                                time.sleep(0.5)  # Chờ 0.5 giây để tránh bị giới hạn API
                                        except Exception as e:
                                            logging.error(f"Lỗi khi xóa tin nhắn {msg_id}: {e}")
                                    response = f"✅ Đã xóa {deleted_count} tin nhắn loại {type_name[sub]} trong nhóm."
                                else:
                                    response = "⚠️ Cú pháp: bot del img/vd/sticker/link/gif/file/voice/emoji/contact/phone/msg/all"
                            except Exception as e:
                                logging.error(f"Lỗi khi xử lý lệnh xóa tin nhắn: {e}")
                                response = f"⚠️ Lỗi khi xóa tin nhắn: {str(e)}"
                elif act == 'preset':
                    if not is_admin(author_id):
                        response = "❌ Chỉ admin bot mới có quyền sử dụng lệnh này."
                    else:
                        if len(parts) < 3:
                            response = "⚠️ Cú pháp: bot preset create <name> <setting1> | <setting2> | ... | bot preset apply <name> [<thread_id1> <thread_id2> ...] | bot preset delete <name> | bot preset list"
                        else:
                            sub = parts[2].lower()
                            if sub == 'create':
                                if len(parts) < 4:
                                    response = "⚠️ Cú pháp: bot preset create <name> <setting1> | <setting2> | ..."
                                else:
                                    preset_name = parts[3].strip()
                                    settings = [s.strip() for s in ' '.join(parts[4:]).split('|') if s.strip()]
                                    if not settings:
                                        response = "⚠️ Vui lòng cung cấp ít nhất một cài đặt!"
                                    else:
                                        s = read_settings()
                                        s.setdefault('presets', {})
                                        if preset_name in s['presets']:
                                            response = f"⚠️ Preset '{preset_name}' đã tồn tại!"
                                        else:
                                            # Validate settings
                                            valid_settings = []
                                            for setting in settings:
                                                set_parts = setting.split()
                                                if not set_parts:
                                                    continue
                                                cmd = set_parts[0].lower()
                                                status = set_parts[1].lower() if len(set_parts) > 1 else None
                                                if cmd in ['on', 'off'] and not status:
                                                    valid_settings.append(setting)
                                                elif cmd == 'setup' and status in ['on', 'off']:
                                                    valid_settings.append(setting)
                                                elif cmd in ['link', 'image', 'video', 'sticker', 'gif', 'sex', 'file', 'voice', 'emoji', 'longmsg', 'duplicate', 'tag', 'word', 'contact', 'phone', 'vehinh'] and status in ['on', 'off']:
                                                    valid_settings.append(setting)
                                            if not valid_settings:
                                                response = "⚠️ Không có cài đặt hợp lệ trong danh sách!"
                                            else:
                                                s['presets'][preset_name] = valid_settings
                                                write_settings(s)
                                                response = f"✅ Đã tạo preset '{preset_name}' với các cài đặt:\n" + "\n".join(f"- {setting}" for setting in valid_settings)
                            elif sub == 'apply':
                                if len(parts) < 4:
                                    response = "📝 Cú pháp: bot preset apply <name> [<thread_id1> <thread_id2> ...]"
                                else:
                                    preset_name = parts[3].strip()
                                    thread_ids = parts[4:] if len(parts) > 4 else [thread_id]
                                    s = read_settings()
                                    if preset_name not in s.get('presets', {}):
                                        response = f"⚠️ Preset '{preset_name}' không tồn tại!"
                                    else:
                                        responses = ["✅✅✅ ÁP DỤNG PRESET THÀNH CÔNG"]
                                        responses.append("════════════════════════")
                                        settings = s['presets'][preset_name]
                                        total_changes = 0

                                        for tid in thread_ids:
                                            try:
                                                group = bot.fetchGroupInfo(tid).gridInfoMap[tid]
                                                group_name = group.name
                                                responses.append(f"🏷️ Nhóm: {group_name}")
                                                responses.append(f"🆔 ID: {tid}")
                                                responses.append("──────────────────────────────")
                                                changes_in_group = 0

                                                for setting in settings:
                                                    set_parts = setting.split()
                                                    cmd = set_parts[0].lower()
                                                    status = set_parts[1].lower() if len(set_parts) > 1 else None
                                                    res = ""

                                                    # === XỬ LÝ CÁC LỆNH ===
                                                    if cmd == 'on' and not status:
                                                        res = toggle_group(bot, tid, True)
                                                    elif cmd == 'off' and not status:
                                                        res = toggle_group(bot, tid, False)
                                                    elif cmd == 'setup' and status in ['on', 'off']:
                                                        res = setup_bot_on(bot, tid) if status == 'on' else setup_bot_off(bot, tid)
                                                    elif cmd in ['link', 'image', 'video', 'sticker', 'gif', 'sex', 'file', 'voice', 'emoji', 'longmsg', 'duplicate', 'tag', 'word', 'contact', 'phone', 'vehinh'] and status in ['on', 'off']:
                                                        if cmd == 'link':
                                                            res = set_ban_link(tid, status == 'on')
                                                        elif cmd == 'word':
                                                            res = set_word_ban(tid, status == 'on')
                                                        elif cmd in ['longmsg', 'duplicate', 'tag']:
                                                            res = {'longmsg': set_longmsg_ban, 'duplicate': set_duplicate_ban, 'tag': set_tag_ban}[cmd](tid, status == 'on')
                                                        elif cmd == 'contact':
                                                            res = set_contact_card_ban(tid, status == 'on')
                                                        elif cmd == 'phone':
                                                            res = set_phone_ban(tid, status == 'on')
                                                        elif cmd == 'vehinh':
                                                            res = set_vehinh_ban(tid, status == 'on')
                                                        else:
                                                            res = set_media_ban(tid, cmd, status == 'on')
                                                    else:
                                                        res = "Cài đặt không hợp lệ"

                                                    # === CHỈ HIỂN THỊ NẾU CÓ THAY ĐỔI ===
                                                    if any(phrase in res for phrase in ["đã được bật", "đã được tắt", "Đã cập nhật", "Bot đã BẬT", "Bot đã TẮT", "Đã bật", "Đã tắt", "Đã cấm", "Đã cho phép"]):
                                                        if any(skip in res for skip in ["đã được bật trước đó", "đã được tắt trước đó", "đã được cấm trước đó", "đã được cho phép trước đó"]):
                                                            continue

                                                        # === GÁN ICON PHÙ HỢP ===
                                                        icon = ""
                                                        if "Bot đã BẬT" in res:
                                                            icon = "🤖 Bot"
                                                        elif "Bot đã TẮT" in res:
                                                            icon = "🤖 Bot"
                                                        elif "Đã cập nhật danh sách quản trị viên" in res or "setup on" in setting:
                                                            icon = "🛠️ Cấu hình"
                                                        elif cmd == 'link':
                                                            icon = "🔗 Liên kết"
                                                        elif cmd == 'image':
                                                            icon = "🖼️ Ảnh"
                                                        elif cmd == 'video':
                                                            icon = "🎥 Video"
                                                        elif cmd == 'sticker':
                                                            icon = "💟 Sticker"
                                                        elif cmd == 'gif':
                                                            icon = "🌀 GIF"
                                                        elif cmd == 'sex':
                                                            icon = "🔞 Nhạy cảm"
                                                        elif cmd == 'file':
                                                            icon = "📁 Tệp"
                                                        elif cmd == 'voice':
                                                            icon = "🎙️ Thoại"
                                                        elif cmd == 'emoji':
                                                            icon = "😄 Emoji"
                                                        elif cmd == 'longmsg':
                                                            icon = "🧾 Tin dài"
                                                        elif cmd == 'duplicate':
                                                            icon = "🔁 Trùng lặp"
                                                        elif cmd == 'tag':
                                                            icon = "🏷️ Tag"
                                                        elif cmd == 'word':
                                                            icon = "🚫 Từ cấm"
                                                        elif cmd == 'contact':
                                                            icon = "👤 Danh thiếp"
                                                        elif cmd == 'phone':
                                                            icon = "☎️ SĐT"
                                                        elif cmd == 'vehinh':
                                                            icon = "🎨 Vẽ hình"
                                                        else:
                                                            icon = cmd.upper()

                                                        # === ĐỊNH DẠNG KẾT QUẢ ===
                                                        if "bật" in res or "BẬT" in res:
                                                            action = "✅ Đã bật"
                                                        elif "tắt" in res or "TẮT" in res:
                                                            action = "❌ Đã tắt"
                                                        elif "cấm" in res:
                                                            action = "🚫 Đã cấm"
                                                        elif "cho phép" in res:
                                                            action = "✅ Đã mở"
                                                        else:
                                                            action = "⚙️ Đã cập nhật"

                                                        responses.append(f"{icon} → {action}")
                                                        changes_in_group += 1
                                                        total_changes += 1

                                                if changes_in_group == 0:
                                                    responses.append("ℹ️ Không có thay đổi nào.")

                                                responses.append("════════════════════════")
                                            except Exception as e:
                                                responses.append(f"❗ Lỗi nhóm ID {tid}: {str(e)}")
                                                responses.append("════════════════════════")

                                        responses.append(f"🎯 Hoàn tất! Tổng cộng {total_changes} thay đổi đã được áp dụng.")
                                        response = "\n".join(responses)

                            elif sub == 'delete':
                                if len(parts) < 4:
                                    response = "⚠️ Cú pháp: bot preset delete <name>"
                                else:
                                    preset_name = parts[3].strip()
                                    s = read_settings()
                                    if preset_name in s.get('presets', {}):
                                        del s['presets'][preset_name]
                                        write_settings(s)
                                        response = f"✅ Đã xóa preset '{preset_name}'!"
                                    else:
                                        response = f"⚠️ Preset '{preset_name}' không tồn tại!"
                            elif sub == 'list':
                                s = read_settings()
                                presets = s.get('presets', {})
                                if not presets:
                                    response = "📋 Danh sách preset trống."
                                else:
                                    responses = ["📋 DANH SÁCH PRESET"]
                                    responses.append("════════════════════════")
                                    for i, (name, settings) in enumerate(presets.items(), 1):
                                        responses.append(f"📌 Preset #{i}: {name}")
                                        responses.append("\n".join(f"- {setting}" for setting in settings))
                                        responses.append("════════════════════════")
                                    response = "\n".join(responses) + "\n✅ Hoàn tất hiển thị danh sách preset!"
                            else:
                                response = "⚠️ Cú pháp: bot preset create <name> <setting1> | <setting2> | ... | bot preset apply <name> [<thread_id1> <thread_id2> ...] | bot preset delete <name> | bot preset list"
                elif act == 'cleanlog':
                    if not is_admin(author_id):
                        response = "❌ Chỉ admin bot mới có quyền sử dụng lệnh này."
                    else:
                        if len(parts) < 3:
                            response = clean_message_log()
                        elif parts[2].isdigit():
                            response = clean_message_log(older_than_days=int(parts[2]))
                        else:
                            response = clean_message_log(thread_id=parts[2])
                    send_message_with_style(bot, response, thread_id, thread_type)
                    return 
                elif act == 'clearlog':
                    if not is_admin(author_id):
                        response = "❌ Chỉ admin bot mới có quyền sử dụng lệnh này."
                    else:
                        response = "⚠️ Lưu ý: Nên chạy 'bot backup create' trước khi xóa log.\n"
                        response += clear_message_log()
                    send_message_with_style(bot, response, thread_id, thread_type)
                    return    
                elif act == 'backup':
                    if len(parts) < 3:
                        response = "⚠️ Cú pháp: bot backup create/list/restore/delete <filename>"
                    else:
                        sub = parts[2].lower()
                        if sub == 'create':
                            if not is_admin(author_id):
                                response = "⚠️ Bạn cần là admin bot để sử dụng lệnh này!"
                            else:
                                response = create_backup()
                        elif sub == 'list':
                            response = list_backups()
                        elif sub == 'restore':
                            if not is_admin(author_id):
                                response = "⚠️ Bạn cần là admin bot để sử dụng lệnh này!"
                            elif len(parts) < 4:
                                response = "⚠️ Cú pháp: bot backup restore <filename>"
                            else:
                                backup_filename = parts[3]
                                response = restore_backup(backup_filename)
                        elif sub == 'delete':
                            if not is_admin(author_id):
                                response = "⚠️ Bạn cần là admin bot để sử dụng lệnh này!"
                            elif len(parts) < 4:
                                response = "⚠️ Cú pháp: bot backup delete <filename>"
                            else:
                                backup_filename = parts[3]
                                response = delete_backup(backup_filename)
                        else:
                            response = "⚠️ Cú pháp: bot backup create/list/restore/delete <filename>"  
                # Trong handle_bot_command
                elif act == 'autoduyet':
                    if thread_type != ThreadType.GROUP or not check_admin_group(bot, thread_id):
                        response = "❌ Bot chưa có quyền admin trong nhóm !"
                    else:
                        state = parts[2].lower() if len(parts) > 2 else ""
                        s = read_settings()
                        auto = s.get('auto_approve_join', {})

                        if state == 'on':
                            auto[thread_id] = True
                            action = "BẬT"
                        elif state == 'off':
                            auto[thread_id] = False
                            action = "TẮT"
                        else:
                            response = "⚠ Dùng: bot autoapprove on/off"
                            send_message_with_style(bot, response, thread_id, thread_type)
                            return

                        s['auto_approve_join'] = auto
                        write_settings(s)

                        group = bot.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
                        response = f"✅ Tự động duyệt yêu cầu tham gia: {action}\nNhóm: {group.name}"                            
                elif act == 'blacklist':
                    if len(parts) < 3:
                        response = "⚠️ Cú pháp: bot blacklist add/del/list [@user hoặc UID1,UID2,...]"
                    else:
                        sub = parts[2].lower()
                        if sub == 'list':
                            response = list_blacklist(bot)
                        elif sub in ['add', 'del']:
                            if thread_type != ThreadType.GROUP or not check_admin_group(bot, thread_id):
                                response = "⚠️ Lệnh này chỉ dùng trong nhóm với quyền phù hợp!"
                            else:
                                # Lấy UID từ mentions
                                uids_from_mentions = extract_uids_from_mentions(msg_obj)
                                # Lấy UID từ danh sách cách nhau bằng dấu phẩy
                                remaining_parts = parts[3:] if len(parts) > 3 else []
                                uids_from_input = []
                                for part in remaining_parts:
                                    # Tách danh sách UID nếu có dấu phẩy
                                    if ',' in part:
                                        uids_from_input.extend([uid.strip() for uid in part.split(',') if uid.strip().isdigit()])
                                    elif part.strip().isdigit():
                                        uids_from_input.append(part.strip())
                                # Gộp danh sách UID, loại bỏ trùng lặp
                                uids = list(set(uids_from_mentions + uids_from_input))
                                if not uids:
                                    response = "⚠️ Vui lòng tag ít nhất một @user hoặc cung cấp UID hợp lệ!"
                                else:
                                    if sub == 'add':
                                        response = add_to_blacklist(bot, uids)
                                    elif sub == 'del':
                                        response = remove_from_blacklist(bot, uids)
                        else:
                            response = f"⚠️ Lệnh bot blacklist {sub} không được hỗ trợ."      
                else:
                    response = f"❌ Lệnh [bot {act}] không được hỗ trợ."
            if response:
                MAX_MSG_LENGTH = 2000  # Giới hạn độ dài mỗi tin nhắn
                if len(response) <= MAX_MSG_LENGTH:
                    print(f"Sending response: {response[:100]}...")  # Log để debug
                    bot.replyMessage(Message(text=response), msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=25000)
                else:
                    # Chia nhỏ tin nhắn
                    lines = response.split('\n')
                    current_msg = ""
                    for line in lines:
                        if len(current_msg) + len(line) + 1 <= MAX_MSG_LENGTH:
                            current_msg += line + '\n'
                        else:
                            print(f"Sending chunk: {current_msg[:100]}...")  # Log để debug
                            bot.replyMessage(Message(text=current_msg), msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=25000)
                            current_msg = line + '\n'
                    if current_msg:
                        print(f"Sending final chunk: {current_msg[:100]}...")  # Log để debug
                        bot.replyMessage(Message(text=current_msg), msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=25000)
        except Exception as e:
            print(f"Error in send_bot_response: {e}")
            bot.replyMessage(Message(text="⚠️ Đã xảy ra lỗi"), msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=20000)
            time.sleep(1)
    Thread(target=send_bot_response).start()
    
# Trong bot_info2.py
def auto_approve_silent(bot, event_data, event_type):
    if event_type != GroupEventType.JOIN_REQUEST:
        return

    thread_id = event_data.get('groupId')
    if not thread_id:
        return

    s = read_settings()
    if not s.get('auto_approve_join', {}).get(thread_id, False):
        print(f"[AUTO APPROVE] TẮT cho nhóm {thread_id}")
        return

    print(f"\n{'='*60}")
    print(f"[JOIN.REQUEST] Phát hiện yêu cầu tham gia nhóm!")
    print(f"   Nhóm ID: {thread_id}")
    print(f"{'='*60}")

    try:
        group_info = bot.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
        pending_members = group_info.pendingApprove.get('uids', [])
        
        if not pending_members:
            print(f"[INFO] Không có ai đang chờ duyệt.")
            return

        print(f"[AUTO APPROVE] Phát hiện {len(pending_members)} yêu cầu:")
        for member_id in pending_members:
            print(f"   → Đang duyệt: {member_id}")
            try:
                if hasattr(bot, 'handleGroupPending'):
                    bot.handleGroupPending(member_id, thread_id)
                    print(f"   ĐÃ DUYỆT: {member_id}")
                    time.sleep(1)
            except Exception as e:
                print(f"   LỖI: {e}")

        print(f"[HOÀN TẤT] Đã duyệt {len(pending_members)} thành viên!\n")

    except Exception as e:
        print(f"[LỖI] fetchGroupInfo: {e}")


def get_mitaizl():
    return {'bott': handle_bot_command}