import os
import requests
from zlapi.models import Message
import random
from PIL import Image

# Thư mục lưu trữ tạm
THU_MUC_CACHE = 'modules/cache'
os.makedirs(THU_MUC_CACHE, exist_ok=True)

# Danh sách các header để xoay vòng
DANH_SACH_HEADER = [
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'},
    {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15'},
    {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0'},
]

# Biến đếm để xoay vòng header
chi_so_header = 0

# Hàm lấy header tiếp theo
def lay_header_tiep_theo():
    global chi_so_header
    header = DANH_SACH_HEADER[chi_so_header]
    chi_so_header = (chi_so_header + 1) % len(DANH_SACH_HEADER)  # Xoay vòng header
    print(f"Đã chọn header: {header}")
    return header

# Hàm lấy kích thước ảnh
def lay_kich_thuoc_anh(duong_dan_anh):
    try:
        with Image.open(duong_dan_anh) as img:
            width, height = img.size
            print(f"Kích thước ảnh: {width}x{height}")
            return width, height
    except Exception as e:
        print(f"Lỗi khi lấy kích thước ảnh: {str(e)}")
        return None, None

# Hàm gọi API để tạo ảnh bìa V1
def lay_anh_bia_v1(ten, uid, dia_chi, email, subname, sdt, mau_sac):
    # URL API với các tham số
    url = f"https://api-dowig.onrender.com/fbcover/v1?name={ten}&uid={uid}&address={dia_chi}&email={email}&subname={subname}&sdt={sdt}&color={mau_sac}"
    print(f"Gọi API với URL: {url}")

    try:
        # Lấy header xoay vòng
        header = lay_header_tiep_theo()
        phan_hoi = requests.get(url, headers=header)
        
        # Kiểm tra trạng thái phản hồi
        print(f"Trạng thái API: {phan_hoi.status_code}")
        if phan_hoi.status_code == 200:
            # Lưu ảnh vào thư mục tạm
            duong_dan_anh = os.path.join(THU_MUC_CACHE, "canvasv1.png")
            with open(duong_dan_anh, 'wb') as tep:
                tep.write(phan_hoi.content)
            print(f"Đã lưu ảnh vào: {duong_dan_anh}")
            return duong_dan_anh
        else:
            print(f"Lỗi API: Mã trạng thái {phan_hoi.status_code}")
            return None
    except Exception as e:
        print(f"Lỗi khi gọi API: {str(e)}")
        return None

# Hàm xử lý lệnh *canvasv1 và gửi ảnh
def xu_ly_lenh_canvasv1(noi_dung_tin_nhan, doi_tuong_tin_nhan, thread_id, thread_type, author_id, client):
    print(f"Nhận lệnh: {noi_dung_tin_nhan}")
    
    # Kiểm tra xem lệnh có bắt đầu bằng *canvasv1 không
    if not noi_dung_tin_nhan.lower().startswith('canvasv1'):
        thong_bao_loi = Message(text="❌ Lệnh không hợp lệ. Vui lòng sử dụng *canvasv1.")
        client.replyMessage(thong_bao_loi, doi_tuong_tin_nhan, thread_id, thread_type, ttl=60000)
        print("Lỗi: Lệnh không bắt đầu bằng *canvasv1")
        return

    # Tách tham số sau *canvasv1
    tham_so = noi_dung_tin_nhan[9:].strip()  # Bỏ *canvasv1 (9 ký tự)
    noi_dung = tham_so.split('|')

    # Kiểm tra xem có đủ tham số không
    if len(noi_dung) < 6:
        thong_bao_loi = Message(text="❌ Vui lòng nhập đầy đủ: tên|UID|địa chỉ|email|subname|số điện thoại|[màu sắc].")
        client.replyMessage(thong_bao_loi, doi_tuong_tin_nhan, thread_id, thread_type, ttl=60000)
        print("Lỗi: Thi thiếu tham số")
        return

    # Lấy các tham số từ lệnh
    try:
        ten = noi_dung[0].strip()
        uid = noi_dung[1].strip()
        dia_chi = noi_dung[2].strip()
        email = noi_dung[3].strip()
        subname = noi_dung[4].strip()
        sdt = noi_dung[5].strip()
        mau_sac = noi_dung[6].strip() if len(noi_dung) > 6 else "pink"  # Mặc định màu hồng
        print(f"Tham số: tên={ten}, uid={uid}, địa chỉ={dia_chi}, email={email}, subname={subname}, sdt={sdt}, màu sắc={mau_sac}")
    except Exception as e:
        thong_bao_loi = Message(text="❌ Dữ liệu không hợp lệ. Vui lòng kiểm tra lại định dạng lệnh.")
        client.replyMessage(thong_bao_loi, doi_tuong_tin_nhan, thread_id, thread_type, ttl=60000)
        print(f"Lỗi xử lý tham số: {str(e)}")
        return

    # Gửi thông báo đang xử lý
    thong_bao_dang_tai = Message(text="✨ Đang tạo ảnh bìa... Vui lòng đợi một chút.")
    client.replyMessage(thong_bao_dang_tai, doi_tuong_tin_nhan, thread_id, thread_type, ttl=60000)
    print("Đã gửi thông báo đang tải")

    # Gọi API để lấy ảnh bìa
    duong_dan_anh = lay_anh_bia_v1(ten, uid, dia_chi, email, subname, sdt, mau_sac)

    if duong_dan_anh:
        # Lấy kích thước ảnh
        width, height = lay_kich_thuoc_anh(duong_dan_anh)
        kich_thuoc = f" (kích thước: {width}x{height} pixels)" if width and height else ""

        # Gửi ảnh bìa cho người dùng với kích thước
        thong_bao_thanh_cong = Message(text=f"✨ Đã tạo ảnh bìa thành công! Hãy lưu ảnh để xem full kích cỡ{kich_thuoc}:")
        try:
            client.sendLocalImage(
                imagePath=duong_dan_anh,
                message=thong_bao_thanh_cong,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width if width else 851,  # Mặc định 851 nếu không lấy được
                height=height if height else 315,  # Mặc định 315 nếu không lấy được
                ttl=300000
            )
            print("Đã gửi ảnh bìa thành công với kích thước")
        except Exception as e:
            thong_bao_loi = Message(text="❌ Lỗi khi gửi ảnh bìa. Vui lòng thử lại.")
            client.replyMessage(thong_bao_loi, doi_tuong_tin_nhan, thread_id, thread_type, ttl=60000)
            print(f"Lỗi khi gửi ảnh: {str(e)}")
            return

        # Xóa ảnh tạm sau khi gửi
        try:
            os.remove(duong_dan_anh)
            print(f"Đã xóa ảnh tạm: {duong_dan_anh}")
        except Exception as e:
            print(f"Lỗi khi xóa ảnh tạm: {str(e)}")
    else:
        thong_bao_loi = Message(text="❌ Đã xảy ra lỗi khi tạo ảnh bìa. Vui lòng thử lại.")
        client.replyMessage(thong_bao_loi, doi_tuong_tin_nhan, thread_id, thread_type, ttl=60000)
        print("Lỗi: Không thể tạo ảnh bìa")

# Đăng ký lệnh
def get_mitaizl():
    return {
        'canvasv1': xu_ly_lenh_canvasv1,
    }