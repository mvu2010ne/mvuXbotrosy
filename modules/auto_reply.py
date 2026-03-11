from zlapi.models import Message, ThreadType, Mention
import time
from datetime import datetime
import logging
from modules.friend import is_friend, get_user_name, load_sent_requests, save_sent_requests

logger = logging.getLogger("Bot")

def apply_default_style(text):
    import random
    COLORS = ["#db342e", "#15a85f", "#f27806", "#f7b503"]
    base_length = len(text)
    adjusted_length = base_length + 100
    from zlapi.models import MultiMsgStyle, MessageStyle
    return MultiMsgStyle([
        MessageStyle(offset=0, length=adjusted_length, style="color", color=random.choice(COLORS), auto_format=False),
        MessageStyle(offset=0, length=adjusted_length, style="font", size="16", auto_format=False),
    ])

def handle_bot_mention(client, message_object, author_id, dname_value, message, thread_id, thread_type, now_str):
    if not hasattr(message_object, 'mentions') or not message_object.mentions:
        return False

    for mention in message_object.mentions:
        if mention.uid != client.uid:
            continue

        tag_exceeded = client.check_tag_spam(author_id)
        if client.mention_enabled and not tag_exceeded:
            mention_text = f"Xin chào  @{dname_value}  ! Cảm ơn bạn đã tag \nNếu có vấn đề cần hỗ trợ \nVui lòng bấm vào đây nhắn tin cho chủ của tôi : "
            mention_obj = Mention(
                uid=author_id,
                length=len(f"@{dname_value} "),
                offset=9
            )
            try:
                client.replyMessage(
                    Message(
                        text=mention_text,
                        style=apply_default_style(mention_text),
                        mention=mention_obj
                    ),
                    message_object,
                    thread_id,
                    thread_type,
                    ttl=180000
                )
                logger.info(f"Bot đã trả lời khi được tag bởi {author_id} trong {thread_id}")
                time.sleep(0.3)
                target_user_id = "3299675674241805615"
                try:
                    qr_data = client.getQrUser(target_user_id)
                    qr_url = qr_data.get(str(target_user_id), "") if qr_data else None
                    if qr_url:
                        client.sendBusinessCard(
                            userId=target_user_id,
                            qrCodeUrl=qr_url,
                            thread_id=thread_id,
                            thread_type=thread_type,
                            phone="Cung cấp mod Liên quân",
                            ttl=300000
                        )
                        logger.info(f"Đã gửi danh thiếp của {target_user_id} tới nhóm {thread_id}")
                    else:
                        client.sendMessage(
                            Message(text="Không thể lấy mã QR của chủ bot.", style=apply_default_style("Không thể lấy mã QR của chủ bot.")),
                            thread_id,
                            thread_type,
                            ttl=60000
                        )
                        logger.info(f"Không thể lấy mã QR của {target_user_id}")
                except Exception as e:
                    logger.error(f"Lỗi khi gửi danh thiếp của {target_user_id}: {e}")
                    client.sendMessage(
                        Message(text=f"Lỗi lấy mã QR của chủ bot.", style=apply_default_style(f"Lỗi lấy mã QR của chủ bot.")),
                        thread_id,
                        thread_type,
                        ttl=60000
                    )
            except Exception as e:
                logger.error(f"Lỗi khi gửi tin nhắn trả lời: {e}")

        target_author_id = "3299675674241805615"
        group_name = "Không xác định"
        if thread_type == ThreadType.GROUP:
            try:
                group_info = client.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
                group_name = group_info.name
            except Exception as e:
                logger.error(f"Lỗi khi lấy thông tin nhóm: {e}")
            group_info = f"🏠 Tên nhóm: {group_name}\n🏠 ID nhóm: {thread_id}"
        else:
            group_info = "Tin nhắn riêng"

        notify_text = (
            f"📢 Bot đã được tag!\n"
            f"══════════════════════════\n"
            f"👤 Tên người tag: {dname_value}\n"
            f"🆔 ID người gửi: {author_id}\n"
            f"💬 Nội dung: {message}\n"
            f"{group_info}\n"
            f"🕒 Thời gian: {now_str}"
        )
        try:
            client.sendMessage(
                Message(text=notify_text),
                target_author_id,
                ThreadType.USER
            )
            logger.info(f"Đã gửi thông báo tới {target_author_id}")
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo tới {target_author_id}: {e}")

        try:
            user_info = client.fetchUserInfo(author_id).changed_profiles.get(author_id)
            if not user_info:
                client.sendMessage(
                    Message(text="Không thể lấy thông tin người dùng."),
                    target_author_id,
                    ThreadType.USER
                )
                logger.info(f"Không thể lấy thông tin người tag {author_id}")
            else:
                dob = user_info.dob
                if dob and isinstance(dob, int):
                    dob = datetime.fromtimestamp(dob).strftime("%d/%m/%Y")
                else:
                    dob = "Không công khai"
                phone = dob
                qr_data = client.getQrUser(author_id)
                qr_url = qr_data.get(str(author_id), "") if qr_data else None
                if not qr_url:
                    client.sendMessage(
                        Message(text="Người dùng này không có mã QR."),
                        target_author_id,
                        ThreadType.USER,
                        ttl=60000
                    )
                    logger.info(f"Người tag {author_id} không có mã QR")
                else:
                    client.sendBusinessCard(
                        userId=author_id,
                        qrCodeUrl=qr_url,
                        thread_id=target_author_id,
                        thread_type=ThreadType.USER,
                        phone=phone
                    )
                    logger.info(f"Đã gửi danh thiếp của {author_id} tới {target_author_id}")
        except Exception as e:
            logger.error(f"Lỗi khi lấy hoặc gửi danh thiếp của {author_id}: {e}")
            client.sendMessage(
                Message(text=f"Lỗi lấy mã QR của người dùng {author_id}."),
                target_author_id,
                ThreadType.USER
            )

        return True
    return False

def handle_private_message(client, message_object, author_id, message, thread_id, thread_type, now_str):
    if thread_type != ThreadType.USER:
        return

    if message_object.msgType == 'chat.photo':
        if not client.check_message_spam(author_id):
            reply_text = "📷 Cảm ơn bạn đã gửi ảnh! Vui lòng gửi tin nhắn văn bản để được hỗ trợ thêm hoặc liên hệ chủ bot qua danh thiếp."
            client.sendMessage(
                Message(text=reply_text, style=apply_default_style(reply_text)),
                thread_id,
                thread_type
            )
            target_user_id = "3299675674241805615"
            try:
                qr_data = client.getQrUser(target_user_id)
                qr_url = qr_data.get(str(target_user_id), "") if qr_data else None
                if qr_url:
                    client.sendBusinessCard(
                        userId=target_user_id,
                        qrCodeUrl=qr_url,
                        thread_id=thread_id,
                        thread_type=thread_type,
                        phone="Cung cấp mod Liên quân"
                    )
                else:
                    client.sendMessage(
                        Message(text="Không thể lấy mã QR của chủ bot.", style=apply_default_style("Không thể lấy mã QR của chủ bot.")),
                        thread_id,
                        thread_type
                    )
            except Exception as e:
                client.sendMessage(
                    Message(text=f"Lỗi lấy mã QR của chủ bot: {e}.", style=apply_default_style(f"Lỗi lấy mã QR của chủ bot: {e}.")),
                        thread_id,
                        thread_type
                    )

        target_admin_id = "3299675674241805615"
        try:
            sender_info = client.fetchUserInfo(author_id).changed_profiles.get(str(author_id))
            photo_url = message_object.content.get('href', 'Không có link ảnh')
            sender_name = sender_info.displayName if sender_info and hasattr(sender_info, 'displayName') else "Không xác định"
            notify_text = (
                f"📩 Tin nhắn riêng mới (Ảnh)!\n"
                f"══════════════════════════\n"
                f"👤 Tên: {sender_name}\n"
                f"🆔 ID: {author_id}\n"
                f"🖼️ Link ảnh: {photo_url}\n"
                f"🕒 Thời gian: {now_str}"
            )
            client.sendMessage(
                Message(text=notify_text),
                target_admin_id,
                ThreadType.USER
            )
            try:
                qr_data = client.getQrUser(author_id)
                qr_url = qr_data.get(str(author_id), "") if qr_data else None
                if qr_url:
                    client.sendBusinessCard(
                        userId=author_id,
                        qrCodeUrl=qr_url,
                        thread_id=target_admin_id,
                        thread_type=ThreadType.USER,
                        phone="Không công khai"
                    )
                else:
                    client.sendMessage(
                        Message(text="Người dùng này không có mã QR.", style=apply_default_style("Người dùng này không có mã QR.")),
                        target_admin_id,
                        ThreadType.USER
                    )
            except Exception as e:
                client.sendMessage(
                    Message(text=f"Lỗi lấy mã QR của người dùng {author_id}: {e}.", style=apply_default_style(f"Lỗi lấy mã QR của người dùng {author_id}: {e}.")),
                    target_admin_id,
                    ThreadType.USER
                )
        except Exception as e:
            client.sendMessage(
                Message(text=f"Lỗi khi xử lý tin nhắn ảnh từ {author_id}: {e}.", style=apply_default_style(f"Lỗi khi xử lý tin nhắn ảnh từ {author_id}: {e}.")),
                target_admin_id,
                ThreadType.USER
            )
        return

    user_msg = message.strip().lower()
    skip_auto_reply_keywords = [
        "vdtt", "2c", "5c", "@all", "acclq", "alo", "amlich", "api", "atk", "stklag", "stop",
        "atknamegr", "atkstk", "attack", "autolink", "autosend_on", "ban", "banggia",
        "addbgroup", "delbgroup", "listbgroup", "bantho", "addban", "delban", "listban",
        "bc", "menubc", "bcua", "bclichsu", "block", "unblock", "boi", "booba", "bot",
        "bott", "calc", "canva", "cap", "card", "cmd", "cmdl", "cos18", "cover", "csplay",
        "welcome", "deptrai", "dhbc", "tl", "dhbcstop", "dhbc2", "tl2", "dhbcstop2", "dich",
        "dinhgiasdt", "ngaunhien", "doan", "doc", "down", "duyetmem", "fb", "`", "gai1",
        "gai2", "gay", "gen", "getidbylink", "getlink", "getvoice", "girl", "gr", "grid",
        "group", "haha", "help", "hentai", "hotclip", "i4", "i5", "imgur", "jav", "join",
        "kb", "kiss", "lamnetanh", "leave", "lea", "listfriends", "listgroups", "listmembers",
        "love", "addgroup", "delgroup", "listgroup", "maqr", "media", "menu", "menu1",
        "menu2", "menu3", "menu4", "menu5", "menu9", "menuad", "mlem", "day", "mya", "net",
        "onMessage", "nhai", "note", "nude", "otaku", "phatnguoi", "phongthuy", "pin",
        "play_on", "play_off", "pollwar", "qr", "qrcode", "random", "renamecmd", "rm",
        "sory", "rs", "scanqr", "scantext", "scl", "scllist", "scload", "sendtoall",
        "sendanh", "sendids", "sendl", "sendl2", "sendlink", "sendnhom", "sendstk",
        "senduser", "sexy", "sharecode", "sms", "sos", "spamsms", "spamtodo", "stk",
        "stkmoi", "stktn", "sys", "tagall", "tagallmem", "tagmem", "stkk2", "tdgr",
        "teach", "text", "thinh", "thoitiet", "tiktokinfo", "time", "todogr", "todouser",
        "tt", "ttinfo", "tx", "menutx", "txiu", "soi", "xemphientruoc", "dsnohu",
        "dudoan", "lichsu", "tygia", "uid", "unlock", "vd18", "vd19", "vdgai", "vdtt",
        "vdx", "viewcode", "voice", "vt", "tlvt", "vtstop", "warpoll", "wiki", "xoa",
        "xxxhub", "yt", "up", "zl"
    ]

    target_admin_id = "3299675674241805615"
    try:
        sender_info = client.fetchUserInfo(author_id).changed_profiles.get(str(author_id))
        if sender_info:
            sender_name = sender_info.displayName if hasattr(sender_info, 'displayName') else "Không xác định"
            notify_text = (
                f"📩 Tin nhắn riêng mới!\n"
                f"══════════════════════════\n"
                f"👤 Tên: {sender_name}\n"
                f"🆔 ID: {author_id}\n"
                f"💬 Nội dung: {message}\n"
                f"🕒 Thời gian: {now_str}"
            )
            client.sendMessage(
                Message(text=notify_text),
                target_admin_id,
                ThreadType.USER
            )
            try:
                qr_data = client.getQrUser(author_id)
                qr_url = qr_data.get(str(author_id), "") if qr_data else None
                if qr_url:
                    client.sendBusinessCard(
                        userId=author_id,
                        qrCodeUrl=qr_url,
                        thread_id=target_admin_id,
                        thread_type=ThreadType.USER,
                        phone="Không công khai"
                    )
                else:
                    client.sendMessage(
                        Message(text="Người dùng này không có mã QR.", style=apply_default_style("Người dùng này không có mã QR.")),
                        target_admin_id,
                        ThreadType.USER
                    )
            except Exception as e:
                client.sendMessage(
                    Message(text=f"Lỗi lấy mã QR của người dùng {author_id}: {e}.", style=apply_default_style(f"Lỗi lấy mã QR của người dùng {author_id}: {e}.")),
                    target_admin_id,
                    ThreadType.USER
                )
        else:
            client.sendMessage(
                Message(text=f"Không thể lấy thông tin người dùng {author_id}.", style=apply_default_style(f"Không thể lấy thông tin người dùng {author_id}.")),
                target_admin_id,
                ThreadType.USER
            )
    except Exception:
        pass
        
    if not is_friend(client, author_id):
        sent_requests = load_sent_requests()
        if author_id not in sent_requests:
            try:
                friend_request_message = f"Xin chào {get_user_name(client, author_id)}! Cảm ơn bạn đã nhắn tin."
                api_response = client.sendFriendRequest(userId=author_id, msg=friend_request_message)
                sent_requests[author_id] = datetime.now().isoformat()
                save_sent_requests(sent_requests)
                logger.info(f"Đã gửi lời mời kết bạn tới {author_id}")
                print(f"✔️ Đã gửi lời mời kết bạn tới {get_user_name(client, author_id)} ({author_id})")
                print(f"📡 Kết quả API: {api_response}")
            except Exception as e:
                logger.error(f"Lỗi khi gửi lời mời kết bạn tới {author_id}: {e}")
                print(f"❌ Không thể gửi lời mời kết bạn tới {get_user_name(client, author_id)} ({author_id}): {e}")
                print(f"📡 Kết quả API: Lỗi - {e}")
            time.sleep(1.0)
    else:
        print(f"👥 {get_user_name(client, author_id)} ({author_id}) đã là bạn bè.")    

    if user_msg == "1":
        if not client.check_message_spam(author_id):
            reply_text = "📞 Vui lòng bấm vào danh thiếp ở trên để liên hệ chủ bot "
            client.sendMessage(
                Message(text=reply_text, style=apply_default_style(reply_text)),
                thread_id,
                thread_type
            )
    elif user_msg == "2":
        if not client.check_message_spam(author_id):
            reply_text = "📞 Vui lòng bấm vào danh thiếp ở trên để liên hệ chủ bot"
            client.sendMessage(
                Message(text=reply_text, style=apply_default_style(reply_text)),
                thread_id,
                thread_type
            )
    elif user_msg == "3":
        if not client.check_message_spam(author_id):
            reply_text = "ℹ️ Nhập lệnh menu để xem menu chính, từ menu chính nhập tiếp lệnh để xem menu con \n 💡 Soạn help + tên lệnh để xem mô tả lệnh và cách sử dụng "
            client.sendMessage(
                Message(text=reply_text, style=apply_default_style(reply_text)),
                thread_id,
                thread_type
            )
    elif user_msg == "4":
        if not client.check_message_spam(author_id):
            reply_text = "📞 Nếu có ý kiến khác vui lòng liên hệ chủ bot để hợp tác, danh thiếp ở trên "
            client.sendMessage(
                Message(text=reply_text, style=apply_default_style(reply_text)),
                thread_id,
                thread_type
            )
    elif user_msg in skip_auto_reply_keywords:
        pass
    else:
        if not client.check_message_spam(author_id):
            auto_reply = (
                "🌸 **BOT Minh Vũ Shinn Cte - PHẢN HỒI TỰ ĐỘNG** 🌸\n"
                "═════════════════════════════\n"
                "👋 Chào bạn! Tôi là bot hỗ trợ tự động.\n"
                "📌 Vui lòng chọn một trong các tùy chọn sau:\n"
                "  1️⃣ Xin slot\n"
                "  2️⃣ Mua map\n"
                "  3️⃣ Hướng dẫn sử dụng bot\n"
                "  4️⃣ Yêu cầu khác hoặc hợp tác\n"
                "─────────────────────────────\n"
                "💬 Nhập số từ 1-4 để tiếp tục.\n"
                "📇 Danh thiếp chủ bot sẽ được gửi kèm để hỗ trợ!"
            )
            client.sendMessage(
                Message(text=auto_reply, style=apply_default_style(auto_reply)),
                author_id,
                ThreadType.USER
            )
            target_user_id = "3299675674241805615"
            user_info_response = client.fetchUserInfo(target_user_id)
            user_info = user_info_response.changed_profiles.get(str(target_user_id))
            phone_text = "Cung cấp mod Liên quân"
            if not user_info:
                client.sendMessage(
                    Message(text="Không thể lấy thông tin người dùng.", style=apply_default_style("Không thể lấy thông tin người dùng.")),
                    thread_id,
                    thread_type
                )
            else:
                try:
                    qr_data = client.getQrUser(target_user_id)
                    qr_url = qr_data.get(str(target_user_id), "") if qr_data else None
                    if qr_url:
                        client.sendBusinessCard(
                            userId=target_user_id,
                            qrCodeUrl=qr_url,
                            thread_id=thread_id,
                            thread_type=thread_type,
                            phone=phone_text
                        )
                    else:
                        client.sendMessage(
                            Message(text="Người dùng này không có mã QR.", style=apply_default_style("Người dùng này không có mã QR.")),
                            thread_id,
                            thread_type
                        )
                except Exception:
                    client.sendMessage(
                        Message(text=f"Lỗi lấy mã QR của người dùng {target_user_id}.", style=apply_default_style(f"Lỗi lấy mã QR của người dùng {target_user_id}.")),
                        thread_id,
                        thread_type
                    )
def get_mitaizl():
    return {
        'autorep': None
    }