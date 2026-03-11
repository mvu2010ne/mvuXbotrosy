import difflib
import json
from zlapi.models import Message

_enabled_groups = {}

def load_enabled_groups():
    global _enabled_groups
    try:
        with open('enabled_groups.json', 'r') as f:
            _enabled_groups = json.load(f)
    except FileNotFoundError:
        _enabled_groups = {}
    except json.JSONDecodeError:
        _enabled_groups = {}

def save_enabled_groups():
    try:
        with open('enabled_groups.json', 'w') as f:
            json.dump(_enabled_groups, f)
    except Exception:
        pass

load_enabled_groups()

def handle_huongdan(message, PREFIX, send_func, thread_id, thread_type, author_id, logger):
    global _enabled_groups
    
    # Nếu PREFIX trống, bỏ qua hoàn toàn để giảm tải
    if not PREFIX:
        return False

    msg_lower = message.strip().lower()

    if PREFIX and msg_lower == PREFIX:
        text = f"Bạn muốn biết tôi có những lệnh gì ❓\nℹ️ Vui lòng sử dụng {PREFIX}menu để xem danh sách lệnh."
        send_func(Message(text=text), thread_id, thread_type, ttl=60000)
        return True

    if msg_lower.startswith(f"{PREFIX}huongdan"):
        parts = msg_lower.split()
        if len(parts) == 1:
            text = f"ℹ️ Sử dụng: {PREFIX}huongdan on/off/list\n" \
                   f"- on: Bật gợi ý lệnh sai cho nhóm này\n" \
                   f"- off: Tắt gợi ý lệnh sai cho nhóm này\n" \
                   f"- list: Xem danh sách nhóm đã bật gợi ý"
        elif parts[1] == "on":
            previous_state = _enabled_groups.get(thread_id)
            if previous_state is True:
                text = f"⚠️ Gợi ý lệnh sai đã được bật trước đó cho nhóm {thread_id}."
            else:
                _enabled_groups[thread_id] = True
                save_enabled_groups()
                text = f"✅ Đã bật tính năng gợi ý lệnh sai cho nhóm {thread_id}."
        elif parts[1] == "off":
            previous_state = _enabled_groups.get(thread_id)
            if previous_state is False:
                text = f"⚠️ Gợi ý lệnh sai đã được tắt trước đó cho nhóm {thread_id}."
            else:
                _enabled_groups.pop(thread_id, None)
                save_enabled_groups()
                text = f"🛑 Đã tắt tính năng gợi ý lệnh sai cho nhóm {thread_id}."
        elif parts[1] == "list":
            enabled_list = [tid for tid, enabled in _enabled_groups.items() if enabled]
            if enabled_list:
                text = "📋 Danh sách nhóm đã bật gợi ý lệnh sai:\n" + "\n".join(f"- {tid}" for tid in enabled_list)
            else:
                text = "📪 Hiện không có nhóm nào bật gợi ý lệnh sai."
        else:
            text = f"⚠️ Sai cú pháp! Sử dụng {PREFIX}huongdan on/off/list."

        send_func(Message(text=text), thread_id, thread_type, ttl=60000)
        return True

    if thread_id in _enabled_groups and _enabled_groups[thread_id]:
        if PREFIX and msg_lower.startswith(PREFIX):
            command_input = msg_lower[len(PREFIX):].split()[0] if msg_lower[len(PREFIX):].strip() else ""
            available_commands = [
                "menu", "help", "code.search", "tree.cmdmap", "admin", "antispam", "nct", "scl", "ttchon",
                "bott.reply", "bott.pm", "menu.media", "menu.game", "menu.user", "menu.group", "menu.bot",
                "menu.send", "menu.stk", "menu.search", "menu.spam", "menu.code", "menu.tag", "menu.file",
                "menu.use", "menu.cmd", "menu.checklink", "menu.ms", "menu.img", "menu.fun", "menu.auto",
                "group", "bott", "casio", "dich", "note", "bst", "addbst", "neko", "gai", "haha", "jp",
                "mlem", "otaku", "pongif", "gainhay", "vd18", "vdgai", "vdx", "bcua", "txiu", "taixiu",
                "soi", "dhbc", "dhbc2", "random", "vtv", "ngaunhien", "nt", "cotuong", "bc", "tx",
                "user.createtime", "user.i4", "user.idcard", "user.qr", "user.report", "user.uid",
                "group.i4", "group.id", "group.find", "group.getid", "group.getlink", "group.getmultilink",
                "group.member", "group.addmember", "group.finduser", "group.findtag", "group.linkfind",
                "group.linktag", "group.msg", "group.accept", "group.pending", "group.banuser",
                "group.unlock", "group.unbanuser", "group.blocked", "group.avatar", "group.stat",
                "group.delmsg", "group.sos", "group.creat", "group.del", "group.cancel", "bot.accept",
                "bot.addfriend", "bot.cancelrequest", "bot.block", "bot.unblock", "bot.friendlist",
                "bot.grouplist", "bot.join", "bot.leave", "bot.leaveid", "bot.setprefix", "bot.delprefix",
                "bot.reset", "bot.rename", "bot.info", "bot.update", "bot.updateavatar", "bot.net",
                "bot.sys", "bot.rs", "bot.inviteall", "bot.keygroup", "bot.teach", "bot.undo",
                "send.all", "send.grouplink", "send.idlist", "auto.link", "send.link", "send.sms",
                "send.user", "send.code", "send.pic", "send.stk", "call", "createlink", "delstk",
                "getstk", "showstk", "stk", "acclq", "fbinfo", "githubi4", "tt", "ttinfo", "wiki",
                "ytb", "pin", "gg", "amlich", "lich", "time", "thoitiet", "web.ss", "web.html",
                "dinhgiasdt", "phongthuy", "phatnguoi", "tygia", "spam.call", "spam.sms", "spam.hiden",
                "spam.grouplink", "spam.stk", "spam.multistk", "spam.stkgif", "spam.poll", "spam.rename",
                "spam.tag", "spam.todogroup", "spam.todouser", "src", "srcreply", "code.admincheck",
                "code.desc", "code.search", "code.share", "code.view", "code.cmdmap", "code.projectmap",
                "tag.all", "tag.allmsg", "tag.mem", "up.catbox", "up.catbox2", "up.imgur", "up.tmp",
                "up.json", "dl", "dl2", "checklink", "getlink", "getlinktt", "ttdownloader", "up.foder",
                "vid2webp", "checklink.addgroup", "checklink.delgroup", "checklink.listgroup",
                "checklink.start", "checklink.stop", "checklink.now", "ms.scl", "ms.nct", "play.on",
                "play.off", "scload", "read", "voice", "getaudio", "create.bankcard", "canva", "cover",
                "thathinh", "art", "bantho", "text2color", "qr", "qrcode", "scanqr", "img.enhance",
                "up", "scantext", "bot", "chat", "chat.clear", "gemin", "gemin.clear", "deptra",
                "gay", "love", "tarot", "banggia", "day", "mya", "auto.sendon", "auto.sendv2",
                "autoimg", "auto.stk", "group.dsthanhvien", "group.duyetmem", "group.duyettv",
                "group.lockgroup", "group.msg", "group.name", "group.note", "group.poll", "group.post",
                "group.sos", "group.theme", "group.active", "group.avatar", "group.demote", "group.info",
                "group.listmembers", "group.owner", "group.promote", "group.rename", "bot.setup",
                "bot.ad", "bot.rules", "bot.rule.word", "bot.rule.spam", "bot.update", "bot.welcome",
                "bot.undo", "bot.mute", "bot.kick", "bot.block", "bot.word", "bot.link", "bot.img",
                "bot.video", "bot.sticker", "bot.gif", "bot.file", "bot.voice", "bot.emoji",
                "bot.longmsg", "bot.dupe", "bot.tag", "bot.asex", "bot.all", "bot.skip", "bot.banlist",
                "bot.groupban", "cmd", "cmd.mng", "cmd.rename", "cmd.sync", "2c", "5c", "@all", "alo", "api", "autolink", "autosend", "quangcao", "autosend_on", "autosend_on2",
                "autostk", "on_start", "on_start_image", "autorep", "menubc", "bclichsu", "bcbatdau", "bot.i4",
                "bot.prefix", "delbst", "fix", "group.find.user", "huongdan", "img_enhance", "addbgroup", "delbgroup",
                "listbgroup", "addban", "delban", "listban", "addgroup", "delgroup", "listgroup", "getstk1", "xemstk1",
                "xoastk1", "stk1", "menu9", "menu.Shinn", "ntstop", "default", "Minh Vũ", "stop", "spamtodo", "text",
                "dl.tt", "truyen", "message", "txiu.soi", "txiu.xemphientruoc", "txiu.dsnohu", "txiu.dudoan",
                "txiu.lichsu", "txiu.on", "txiu.rsjackpot", "txiu.setjackpot", "user.creattime", "bot.report", "vt",
                "vtstop", "canvas", "xoanen", "tl", "dhbcstop", "tl2", "dhbcstop2", "xito", "doan", "fr", "gaitt",
                "delete", "gemini", "welcome", "dlmedia", "code.search/", "rs"
            ]

            command_descriptions = {
                "menu": "Hiển thị danh sách lệnh hiện có",
                "help": "Xem hướng dẫn chi tiết cho một lệnh",
                "code.search": "Tìm kiếm mã nguồn cục bộ",
                "tree.cmdmap": "Hiển thị cây lệnh",
                "admin": "Quản lý cài đặt admin",
                "antispam": "Bật/tắt chế độ chống spam",
                "nct": "Tìm kiếm bài hát trên nct",
                "scl": "Tìm kiếm bài hát trên soundcloud",
                "ttchon": "Chọn video tiktok",
                "bott.reply": "Bật/tắt trả lời khi được tag",
                "bott.pm": "Bật/tắt trả lời tin nhắn riêng",
                "menu.media": "Menu xem ảnh và video",
                "menu.game": "Menu trò chơi",
                "menu.user": "Menu thông tin người dùng",
                "menu.group": "Menu quản lý nhóm",
                "menu.bot": "Menu quản lý bot",
                "menu.send": "Menu quản lý gửi tin nhắn",
                "menu.stk": "Menu quản lý sticker",
                "menu.search": "Menu tìm kiếm",
                "menu.spam": "Menu công cụ spam",
                "menu.code": "Menu quản lý mã nguồn",
                "menu.tag": "Menu gắn thẻ người dùng",
                "menu.file": "Menu quản lý file",
                "menu.use": "Menu quản lý quyền sử dụng bot",
                "menu.cmd": "Menu quản lý lệnh",
                "menu.checklink": "Menu kiểm soát liên kết",
                "menu.ms": "Menu âm thanh và nhạc",
                "menu.img": "Menu tạo hình ảnh",
                "menu.fun": "Menu giải trí và trò chuyện",
                "menu.auto": "Menu tự động gửi",
                "group": "Quản lý thông tin nhóm",
                "bott": "Cài đặt và tùy chỉnh bot",
                "casio": "Máy tính casio",
                "dich": "Dịch ngôn ngữ",
                "note": "Ghi chú và chia sẻ",
                "bst": "Ảnh từ bộ sưu tập (json)",
                "addbst": "Thêm ảnh vào bộ sưu tập",
                "neko": "Ảnh neko",
                "gai": "Ảnh gái xinh (girl1.txt)",
                "haha": "Ảnh meme (haha.txt)",
                "jp": "Ảnh idol nhật (jav.txt)",
                "mlem": "Ảnh mông (mlem.txt)",
                "otaku": "Ảnh anime (otaku.txt)",
                "pongif": "Porn gif (otaku.txt)",
                "gainhay": "Video gái nhảy (json)",
                "vd18": "Video 18+ (vd18.txt)",
                "vdgai": "Video từ json github",
                "vdx": "Video người lớn (vdx.txt)",
                "bcua": "Chơi trò bầu cua vui nhộn",
                "txiu": "Chơi tài xỉu với kết quả ngẫu nhiên",
                "taixiu": "Chơi tài xỉu (phiên bản khác)",
                "soi": "Soi cầu dự đoán kết quả tài xỉu",
                "dhbc": "Chơi đuổi hình bắt chữ với 1 ảnh",
                "dhbc2": "Chơi đuổi hình bắt chữ với 2 ảnh",
                "random": "Trò chơi ngẫu nhiên đầy bất ngờ",
                "vtv": "Tham gia vua tiếng việt giải đố",
                "ngaunhien": "Random kết quả ngẫu nhiên",
                "nt": "Tham gia trò chơi nối từ",
                "cotuong": "Chơi cờ tướng",
                "bc": "Xem menu chi tiết của trò bầu cua",
                "tx": "Xem menu chi tiết của trò tài xỉu",
                "user.createtime": "Kiểm tra thời gian tạo tài khoản",
                "user.i4": "Lấy thông tin người dùng zalo",
                "user.idcard": "Lấy id card người dùng zalo",
                "user.qr": "Lấy mã qr zalo của người dùng",
                "user.report": "Báo cáo người dùng",
                "user.uid": "Lấy uid người dùng",
                "group.i4": "Xem thông tin nhóm zalo",
                "group.id": "Lấy id nhóm",
                "group.find": "Tìm thông tin nhóm zalo qua id nhóm",
                "group.getid": "Lấy id nhóm zalo từ link",
                "group.getlink": "Lấy link mời của nhóm zalo",
                "group.getmultilink": "Lấy link mời nhiều nhóm qua id nhóm",
                "group.member": "Xem danh sách thành viên",
                "group.addmember": "Xem danh sách thành viên (bản cũ)",
                "group.finduser": "Tìm thành viên theo tên",
                "group.findtag": "Gắn thẻ thành viên theo tên hoặc id",
                "group.linkfind": "Tìm thành viên thông qua link nhóm",
                "group.linktag": "Gắn thẻ thành viên theo tên hoặc id qua link nhóm",
                "group.msg": "Xem cuộc trò chuyện nhóm",
                "group.accept": "Duyệt/xem thành viên chờ tham gia",
                "group.pending": "Xem danh sách thành viên chờ duyệt chi tiết",
                "group.banuser": "Xóa và chặn thành viên khỏi nhóm",
                "group.unlock": "Mở khóa nhóm",
                "group.unbanuser": "Gỡ cấm thành viên",
                "group.blocked": "Xem danh sách thành viên bị khóa",
                "group.avatar": "Thay đổi avatar nhóm zalo bằng link ảnh",
                "group.stat": "Thống kê nhóm zalo theo trưởng nhóm",
                "group.delmsg": "Xóa 50 tin nhắn gần nhất trong nhóm",
                "group.sos": "Khóa nhóm khẩn cấp",
                "group.creat": "Tạo nhóm mới",
                "group.del": "Giải tán nhóm",
                "group.cancel": "Hủy giải tán nhóm",
                "bot.accept": "Chấp nhận kết bạn một người dùng",
                "bot.addfriend": "Gửi lời mời kết bạn tới tất cả thành viên trong nhóm",
                "bot.cancelrequest": "Hủy tiến trình kết bạn",
                "bot.block": "Chặn một người dùng trong trò chuyện cá nhân",
                "bot.unblock": "Gỡ chặn người dùng",
                "bot.friendlist": "Xem danh sách bạn bè của bot",
                "bot.grouplist": "Xem danh sách tất cả nhóm tham gia",
                "bot.join": "Tham gia nhiều nhóm thông qua link nhóm",
                "bot.leave": "Rời nhóm hiện tại",
                "bot.leaveid": "Rời nhóm theo id nhóm",
                "bot.setprefix": "Thay đổi tiền tố lệnh",
                "bot.delprefix": "Xóa tiền tố lệnh",
                "bot.reset": "Đặt lại cấu hình prefix về mặc định",
                "bot.rename": "Đổi tên hiển thị của bot",
                "bot.info": "Xem thông tin chi tiết của bot",
                "bot.update": "Cập nhật thông tin hiển thị của bot",
                "bot.updateavatar": "Đổi avatar bot",
                "bot.net": "Kiểm tra tốc độ mạng thiết bị",
                "bot.sys": "Xem thông tin phần cứng của bot",
                "bot.rs": "Khởi động lại để làm mới hệ thống",
                "bot.inviteall": "Mời tất cả bạn bè vào nhóm",
                "bot.keygroup": "Lấy danh sách link mời của các nhóm zalo mà bot đang là phó nhóm",
                "bot.teach": "Dạy bot trả lời",
                "bot.undo": "Thu hồi tin nhắn trong nhóm",
                "send.all": "Gửi tin nhắn tới tất cả nhóm zalo",
                "send.grouplink": "Gửi tin nhắn qua link nhóm",
                "send.idlist": "Gửi tin nhắn theo danh sách id nhóm",
                "auto.link": "Tự động gửi danh sách link",
                "send.link": "Gửi link đã tạo tới các nhóm",
                "send.sms": "Gửi tin nhắn trực tiếp cho 1 người",
                "send.user": "Gửi nhiều tin nhắn cho 1 người",
                "send.code": "Gửi file code cho người được tag",
                "send.pic": "Gửi ảnh bằng link ảnh",
                "send.stk": "Gửi sticker cú đấm vào nhóm",
                "call": "Gọi điện tới số điện thoại hoặc zalo",
                "createlink": "Tạo link mời tham gia tùy chỉnh",
                "delstk": "Xóa sticker đã lưu",
                "getstk": "Tạo sticker từ ảnh/video",
                "showstk": "Xem danh sách sticker",
                "stk": "Gửi sticker đã lưu",
                "acclq": "Lấy tài khoản liên quân miễn phí",
                "fbinfo": "Lấy thông tin facebook",
                "githubi4": "Thông tin github",
                "tt": "Tìm/tải video tiktok",
                "ttinfo": "Chi tiết video tiktok",
                "wiki": "Tra cứu wikipedia",
                "ytb": "Tìm/tải video youtube",
                "pin": "Tìm ảnh pinterest",
                "gg": "Tìm kiếm trên google",
                "amlich": "Xem âm lịch theo ngày",
                "lich": "Xem lịch hôm nay",
                "time": "Xem giờ hiện tại",
                "thoitiet": "Xem dự báo thời tiết",
                "web.ss": "Chụp màn hình web từ link",
                "web.html": "Lấy mã html từ web",
                "dinhgiasdt": "Định giá số điện thoại",
                "phongthuy": "Tra phong thủy số điện thoại",
                "phatnguoi": "Tra cứu phạt nguội xe",
                "tygia": "Tra tỷ giá ngoại tệ",
                "spam.call": "Gọi liên tục tới số zalo",
                "spam.sms": "Gửi nhiều cuộc gọi & tin nhắn đến số điện thoại",
                "spam.hiden": "Spam ẩn",
                "spam.g^{[}link": "Gửi tin nhắn nhiều lần qua link nhóm",
                "spam.stk": "Gửi nhiều sticker liên tục",
                "spam.multistk": "Gửi sticker gây lag liên tục",
                "spam.stkgif": "Gửi sticker gif gây lag nhóm",
                "spam.poll": "Tạo khảo sát spam liên tục",
                "spam.rename": "Đổi tên nhóm liên tục",
                "spam.tag": "Gắn thẻ + spam chửi trong nhóm",
                "spam.todogroup": "Gửi spam todo vào nhóm",
                "spam.todouser": "Gửi spam todo tới người dùng",
                "src": "Xem dữ liệu gốc của tin nhắn người dùng",
                "srcreply": "Xem dữ liệu gốc của tin nhắn được trả lời",
                "code.admincheck": "Xem quyền của tất cả file python trong /modules",
                "code.desc": "Xem mô tả của tất cả file python trong /modules",
                "code.share": "Chia sẻ mã nguồn dưới dạng file và link",
                "code.view": "Xem mã nguồn của một lệnh cụ thể trong /modules",
                "code.cmdmap": "Bản đồ ánh xạ lệnh",
                "code.projectmap": "Bản đồ ánh xạ dự án",
                "tag.all": "Gắn thẻ tất cả thành viên trong nhóm",
                "tag.allmsg": "Gắn thẻ tất cả kèm nội dung tùy chỉnh",
                "tag.mem": "Gắn thẻ một thành viên cụ thể",
                "up.catbox": "Tải file lên catbox",
                "up.catbox2": "Tải file lên catbox lấy link",
                "up.imgur": "Tải ảnh lên imgur",
                "up.tmp": "Tải file lên tmpfile",
                "up.json": "Lưu link ảnh vào json",
                "dl": "Tải file từ link bất kỳ",
                "dl2": "Tải file từ link bất kỳ (phiên bản khác)",
                "checklink": "Kiểm tra trạng thái link",
                "getlink": "Chuyển ảnh/video thành link",
                "getlinktt": "Lấy link video tiktok từ id hoặc url",
                "ttdownloader": "Tải video tiktok và lưu vào gainhay",
                "up.foder": "Upload toàn bộ thư mục lên catbox",
                "vid2webp": "Chuyển video sang webp",
                "checklink.addgroup": "Thêm nhóm vào danh sách kiểm tra link",
                "checklink.delgroup": "Xóa nhóm khỏi danh sách kiểm tra link",
                "checklink.listgroup": "Xem danh sách nhóm kiểm tra link",
                "checklink.start": "Bắt đầu kiểm tra link",
                "checklink.stop": "Dừng kiểm tra link",
                "checklink.now": "Kiểm tra link ngay",
                "ms.scl": "Nghe nhạc soundcloud",
                "ms.nct": "Nghe nhạc nct",
                "play.on": "Bật danh sách nhạc",
                "play.off": "Tắt danh sách nhạc",
                "scload": "Tải nhạc soundcloud",
                "read": "Đọc tin nhắn bằng giọng ai",
                "voice": "Chuyển văn bản thành giọng nói",
                "getaudio": "Tải audio từ link",
                "create.bankcard": "Tạo thẻ chuyển khoản tùy chỉnh",
                "canva": "Tạo thông báo tùy chỉnh",
                "cover": "Thiết kế ảnh bìa mạng xã hội",
                "thathinh": "Tạo ảnh thả thính",
                "art": "Tạo ảnh nghệ thuật từ văn bản",
                "bantho": "Tạo ảnh bàn thờ troll",
                "text2color": "Tạo chữ màu tùy chỉnh",
                "qr": "Tạo mã qr nâng cao",
                "qrcode": "Tạo mã qr cơ bản",
                "scanqr": "Quét mã qr",
                "img.enhance": "Tăng độ nét ảnh",
                "up": "Cải thiện chất lượng ảnh bằng ai",
                "scantext": "Trích xuất văn bản từ ảnh",
                "bot": "Trò chuyện với bot ai",
                "chat": "Chat với gpt-4",
                "chat.clear": "Hủy luồng trò chuyện hiện tại với gpt-4",
                "gemin": "Trò chuyện với gemini",
                "gemin.clear": "Hủy luồng trò chuyện hiện tại với gemini",
                "deptra": "Đánh giá độ đẹp trai",
                "gay": "Đo độ 'gay' vui",
                "love": "Bói tình duyên",
                "tarot": "Xem bói tarot hàng ngày",
                "banggia": "Xem bảng giá dịch vụ bot",
                "day": "Dạy bot nội bộ",
                "mya": "Dạy bot nội bộ",
                "auto.sendon": "Tự động gửi tin nhắn theo lịch",
                "auto.sendv2": "Tự động gửi link theo lịch",
                "autoimg": "Tự động gửi ảnh theo lịch",
                "auto.stk": "Tự động gửi sticker theo lịch",
                "group.dsthanhvien": "Xem danh sách thành viên",
                "group.duyetmem": "Phê duyệt thành viên mới",
                "group.duyettv": "Chỉ cho phép thêm thành viên",
                "group.lockgroup": "Khóa/mở toàn bộ nhóm",
                "group.msg": "Lịch sử tin nhắn nhóm",
                "group.name": "Thay đổi tên nhóm",
                "group.note": "Ghi chú cho admin",
                "group.poll": "Tạo khảo sát",
                "group.post": "Tạo bài viết",
                "group.sos": "Gửi tin nhắn khẩn cấp",
                "group.theme": "Thay đổi chủ đề nhóm",
                "group.active": "Xem trạng thái cài đặt",
                "group.avatar": "Đổi ảnh đại diện nhóm",
                "group.demote": "Hạ cấp admin",
                "group.info": "Xem thông tin nhóm",
                "group.listmembers": "Xem danh sách thành viên",
                "group.owner": "Chuyển quyền sở hữu nhóm",
                "group.promote": "Nâng cấp admin",
                "group.rename": "Đổi tên nhóm",
                "bot.setup": "Cài quyền quản trị",
                "bot.ad": "Thêm/xóa/xem admin",
                "bot.rules": "Xem nội quy nhóm",
                "bot.rule.word": "Cập nhật từ cấm",
                "bot.rule.spam": "Cập nhật quy tắc chống spam",
                "bot.update": "Cập nhật cài đặt",
                "bot.welcome": "Chế độ chào mừng",
                "bot.undo": "Chế độ hoàn tác",
                "bot.mute": "Quản lý khóa thành viên",
                "bot.kick": "Xóa thành viên",
                "bot.block": "Quản lý chặn thành viên",
                "bot.word": "Quản lý từ cấm",
                "bot.link": "Cấm/cho phép link",
                "bot.img": "Cấm/cho phép ảnh",
                "bot.video": "Cấm/cho phép video",
                "bot.sticker": "Cấm/cho phép sticker",
                "bot.gif": "Cấm/cho phép gif",
                "bot.file": "Cấm/cho phép file",
                "bot.voice": "Cấm/cho phép voice",
                "bot.emoji": "Cấm/cho phép emoji",
                "bot.longmsg": "Cấm/cho phép tin nhắn dài",
                "bot.dupe": "Cấm/cho phép tin nhắn trùng",
                "bot.tag": "Cấm/cho phép tag",
                "bot.asex": "Cấm/cho phép nội dung 18+",
                "bot.all": "Bật/tắt tất cả lệnh",
                "bot.skip": "Quản lý bỏ qua",
                "bot.banlist": "Xem lệnh cấm hiện tại",
                "bot.groupban": "Xem nhóm bật lệnh cấm",
                "cmd": "Đóng/mở một hoặc nhiều lệnh",
                "cmd.mng": "Quản lý các lệnh trong hệ thống bot",
                "cmd.rename": "Đổi tên một lệnh cụ thể trong /modules",
                "cmd.sync": "So sánh tên lệnh đăng ký với tên tệp trong thư mục 'modules'",
                "2c": "Chơi trò chơi 2 chữ cái",
                "5c": "Chơi trò chơi 5 chữ cái",
                "@all": "Gắn thẻ tất cả thành viên trong nhóm",
                "alo": "Gửi tin nhắn chào hỏi",
                "api": "Kiểm tra trạng thái API bot",
                "autolink": "Tự động gửi link theo lịch trình",
                "autosend": "Tự động gửi tin nhắn ngẫu nhiên",
                "quangcao": "Gửi tin nhắn quảng cáo tới nhóm",
                "autosend_on": "Bật chế độ tự động gửi tin nhắn",
                "autosend_on2": "Bật chế độ tự động gửi tin nhắn (phiên bản 2)",
                "autostk": "Tự động gửi sticker theo lịch trình",
                "on_start": "Khởi động tính năng tự động khi bot chạy",
                "on_start_image": "Khởi động gửi ảnh tự động khi bot chạy",
                "autorep": "Tự động trả lời tin nhắn",
                "menubc": "Hiển thị menu trò chơi bầu cua",
                "bclichsu": "Xem lịch sử chơi bầu cua",
                "bcbatdau": "Bắt đầu trò chơi bầu cua",
                "bot.i4": "Xem thông tin bot trên Zalo",
                "bot.prefix": "Xem tiền tố lệnh hiện tại",
                "delbst": "Xóa ảnh khỏi bộ sưu tập",
                "fix": "Sửa lỗi hệ thống bot",
                "group.find.user": "Tìm thành viên nhóm theo tên",
                "huongdan": "Xem hướng dẫn sử dụng bot",
                "img_enhance": "Tăng độ nét ảnh bằng AI",
                "addbgroup": "Thêm nhóm vào danh sách chặn",
                "delbgroup": "Xóa nhóm khỏi danh sách chặn",
                "listbgroup": "Xem danh sách nhóm bị chặn",
                "addban": "Thêm người dùng vào danh sách cấm",
                "delban": "Xóa người dùng khỏi danh sách cấm",
                "listban": "Xem danh sách người dùng bị cấm",
                "addgroup": "Thêm nhóm vào danh sách quản lý",
                "delgroup": "Xóa nhóm khỏi danh sách quản lý",
                "listgroup": "Xem danh sách nhóm quản lý",
                "getstk1": "Tạo sticker mới (phiên bản 1)",
                "xemstk1": "Xem danh sách sticker (phiên bản 1)",
                "xoastk1": "Xóa sticker (phiên bản 1)",
                "stk1": "Gửi sticker (phiên bản 1)",
                "menu9": "Hiển thị danh sách lệnh chi tiết",
                "menu.Shinn": "Hiển thị menu lệnh của Shinn",
                "ntstop": "Dừng trò chơi nối từ",
                "default": "Đặt lại cài đặt bot về mặc định",
                "Minh Vũ": "Hiển thị thông tin bot Minh Vũ Shinn Cte",
                "stop": "Dừng tất cả tính năng tự động",
                "spamtodo": "Gửi spam công việc (todo)",
                "text": "Tạo văn bản tùy chỉnh",
                "dl.tt": "Tải video TikTok",
                "truyen": "Đọc truyện ngắn ngẫu nhiên",
                "message": "Gửi tin nhắn tùy chỉnh",
                "txiu.soi": "Soi cầu dự đoán tài xỉu",
                "txiu.xemphientruoc": "Xem phiên tài xỉu trước",
                "txiu.dsnohu": "Xem danh sách nổ hũ tài xỉu",
                "txiu.dudoan": "Dự đoán kết quả tài xỉu",
                "txiu.lichsu": "Xem lịch sử chơi tài xỉu",
                "txiu.on": "Bật trò chơi tài xỉu",
                "txiu.rsjackpot": "Đặt lại jackpot tài xỉu",
                "txiu.setjackpot": "Cài đặt jackpot tài xỉu",
                "user.creattime": "Kiểm tra thời gian tạo tài khoản Zalo",
                "bot.report": "Báo cáo sự cố bot",
                "vt": "Chơi trò vua tiếng Việt",
                "vtstop": "Dừng trò vua tiếng Việt",
                "canvas": "Tạo thiết kế đồ họa tùy chỉnh",
                "xoanen": "Tạo ảnh nền ngẫu nhiên",
                "tl": "Trả lời câu hỏi đuổi hình bắt chữ",
                "dhbcstop": "Dừng trò đuổi hình bắt chữ",
                "tl2": "Trả lời câu hỏi đuổi hình bắt chữ (phiên bản 2)",
                "dhbcstop2": "Dừng trò đuổi hình bắt chữ (phiên bản 2)",
                "xito": "Chơi trò xì tố",
                "doan": "Chơi trò đoán số",
                "fr": "Gửi lời mời kết bạn",
                "gaitt": "Tải ảnh gái từ TikTok",
                "delete": "Xóa tin nhắn bot",
                "gemini": "Trò chuyện với AI Gemini",
                "welcome": "Cài đặt tin nhắn chào mừng",
                "dlmedia": "Tải media từ link",
                "code.search/": "Tìm kiếm mã nguồn (phiên bản đặc biệt)",
                "rs": "Khởi động lại bot"
            }

            if command_input and command_input not in available_commands:
                closest_matches = difflib.get_close_matches(command_input, available_commands, n=10, cutoff=0.6)  # Lấy tối đa 3 lệnh gần giống
                if closest_matches:
                    closest_commands = [f"➜ {PREFIX}{cmd} - {command_descriptions.get(cmd, 'Không có mô tả')}" for cmd in closest_matches]
                    response_text = (
                        f"❌ Lệnh {PREFIX}{command_input} không tồn tại.\n"
                        f"Có phải bạn đang muốn tìm ❓\n"
                        + "\n".join(closest_commands) + "\n"
                        f"Gõ {PREFIX}help <lệnh> để biết thêm chi tiết."
                    )
                    send_func(Message(text=response_text), thread_id, thread_type, ttl=60000)
                    return True

    return False

def get_mitaizl():
    return {
        'huongdan': handle_huongdan
    }