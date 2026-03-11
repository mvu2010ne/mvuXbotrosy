import time
import random
import requests
from zlapi.models import Message, ThreadType
from datetime import datetime, timedelta
import pytz
import threading

time_messages = {
    "07:00": "𝙍𝙊𝙎𝙔 𝘼𝙍𝙀𝙉𝘼 𝙎𝙃𝙊𝙋\n𝙈𝙪𝙖 𝙝𝙖𝙘𝙠 𝙢𝙖𝙥 𝙤̛̉ 𝙙𝙖̂𝙮\nBán box zalo\nBox 1️⃣: Leo rank Tlt\nzalo.me/g/olpwed729\nBox 2️⃣: Reg Đi Bot\nzalo.me/g/bjnwqv874\nBox 3️⃣: Reg Bot 5 Game\nzalo.me/g/oiqhul568\nBox 4️⃣: Box Leo Rank\nzalo.me/g/ochyyh448\nBox 5️⃣: TLT- Nor 5-5\nzalo.me/g/lzygxi684\nBox 6️⃣Leo rank\nzalo.me/g/qlhssk809\nBox 7️⃣ : Leo CT-CTG\nzalo.me/g/xvtszw104\nBox 8️⃣: Hạ Rank Cấp Tốc\nzalo.me/g/sjrbqa638\nBox 9️⃣ Leo rank\nzalo.me/g/cmbmjz408\nBox: 🔟 Leo hạ rank\nzalo.me/g/vtgpfr533\nBox 1️⃣1️⃣: Hạ Rank\nzalo.me/g/dmgtoc729\nBox 1️⃣2️⃣: Hạ Rank \nzalo.me/g/tlxiin969 \nBox 1️⃣3️⃣: Cầm Đèn Leo Rank \nzalo.me/g/spaqlb267\nBox 1️⃣4️⃣: Hạ Rank \nzalo.me/g/byuqks230 \nBox 1️⃣5️⃣ : Hạ rank 24/7 \nzalo.me/g/khjrna643\nBox 1️⃣6️⃣: Nghiện Liên Quân \nzalo.me/g/zfziaz213\nBox 1️⃣7️⃣: Hạ Rank \nzalo.me/g/smibnr474\nBox 1️⃣8️⃣: Tlt 3 vs 3 \nzalo.me/g/tyldqj123\nBox 1️⃣9️⃣ : Leo Rank \nzalo.me/g/lulmlw377 \nBox 2️⃣0️⃣ Hạ rank \nzalo.me/g/ysdgtu142\nBox 2️⃣1️⃣: Keo rank \nzalo.me/g/lalvob031\nBox 2️⃣2️⃣: Leo rank \nzalo.me/g/crgyqw748\nBox 2️⃣3️⃣: Hạ Rank \nzalo.me/g/lnuarr372",
    "09:34": "𝙍𝙊𝙎𝙔 𝘼𝙍𝙀𝙉𝘼 𝙎𝙃𝙊𝙋\n𝙈𝙪𝙖 𝙝𝙖𝙘𝙠 𝙢𝙖𝙥 𝙤̛̉ 𝙙𝙖̂𝙮\nBán box zalo\nBox 1️⃣: Leo rank Tlt\nzalo.me/g/olpwed729\nBox 2️⃣: Reg Đi Bot\nzalo.me/g/bjnwqv874\nBox 3️⃣: Reg Bot 5 Game\nzalo.me/g/oiqhul568\nBox 4️⃣: Box Leo Rank\nzalo.me/g/ochyyh448\nBox 5️⃣: TLT- Nor 5-5\nzalo.me/g/lzygxi684\nBox 6️⃣Leo rank\nzalo.me/g/qlhssk809\nBox 7️⃣ : Leo CT-CTG\nzalo.me/g/xvtszw104\nBox 8️⃣: Hạ Rank Cấp Tốc\nzalo.me/g/sjrbqa638\nBox 9️⃣ Leo rank\nzalo.me/g/cmbmjz408\nBox: 🔟 Leo hạ rank\nzalo.me/g/vtgpfr533\nBox 1️⃣1️⃣: Hạ Rank\nzalo.me/g/dmgtoc729\nBox 1️⃣2️⃣: Hạ Rank \nzalo.me/g/tlxiin969 \nBox 1️⃣3️⃣: Cầm Đèn Leo Rank \nzalo.me/g/spaqlb267\nBox 1️⃣4️⃣: Hạ Rank \nzalo.me/g/byuqks230 \nBox 1️⃣5️⃣ : Hạ rank 24/7 \nzalo.me/g/khjrna643\nBox 1️⃣6️⃣: Nghiện Liên Quân \nzalo.me/g/zfziaz213\nBox 1️⃣7️⃣: Hạ Rank \nzalo.me/g/smibnr474\nBox 1️⃣8️⃣: Tlt 3 vs 3 \nzalo.me/g/tyldqj123\nBox 1️⃣9️⃣ : Leo Rank \nzalo.me/g/lulmlw377 \nBox 2️⃣0️⃣ Hạ rank \nzalo.me/g/ysdgtu142\nBox 2️⃣1️⃣: Keo rank \nzalo.me/g/lalvob031\nBox 2️⃣2️⃣: Leo rank \nzalo.me/g/crgyqw748\nBox 2️⃣3️⃣: Hạ Rank \nzalo.me/g/lnuarr372",
    "11:00": "𝙍𝙊𝙎𝙔 𝘼𝙍𝙀𝙉𝘼 𝙎𝙃𝙊𝙋\n𝙈𝙪𝙖 𝙝𝙖𝙘𝙠 𝙢𝙖𝙥 𝙤̛̉ 𝙙𝙖̂𝙮\nBán box zalo\nBox 1️⃣: Leo rank Tlt\nzalo.me/g/olpwed729\nBox 2️⃣: Reg Đi Bot\nzalo.me/g/bjnwqv874\nBox 3️⃣: Reg Bot 5 Game\nzalo.me/g/oiqhul568\nBox 4️⃣: Box Leo Rank\nzalo.me/g/ochyyh448\nBox 5️⃣: TLT- Nor 5-5\nzalo.me/g/lzygxi684\nBox 6️⃣Leo rank\nzalo.me/g/qlhssk809\nBox 7️⃣ : Leo CT-CTG\nzalo.me/g/xvtszw104\nBox 8️⃣: Hạ Rank Cấp Tốc\nzalo.me/g/sjrbqa638\nBox 9️⃣ Leo rank\nzalo.me/g/cmbmjz408\nBox: 🔟 Leo hạ rank\nzalo.me/g/vtgpfr533\nBox 1️⃣1️⃣: Hạ Rank\nzalo.me/g/dmgtoc729\nBox 1️⃣2️⃣: Hạ Rank \nzalo.me/g/tlxiin969 \nBox 1️⃣3️⃣: Cầm Đèn Leo Rank \nzalo.me/g/spaqlb267\nBox 1️⃣4️⃣: Hạ Rank \nzalo.me/g/byuqks230 \nBox 1️⃣5️⃣ : Hạ rank 24/7 \nzalo.me/g/khjrna643\nBox 1️⃣6️⃣: Nghiện Liên Quân \nzalo.me/g/zfziaz213\nBox 1️⃣7️⃣: Hạ Rank \nzalo.me/g/smibnr474\nBox 1️⃣8️⃣: Tlt 3 vs 3 \nzalo.me/g/tyldqj123\nBox 1️⃣9️⃣ : Leo Rank \nzalo.me/g/lulmlw377 \nBox 2️⃣0️⃣ Hạ rank \nzalo.me/g/ysdgtu142\nBox 2️⃣1️⃣: Keo rank \nzalo.me/g/lalvob031\nBox 2️⃣2️⃣: Leo rank \nzalo.me/g/crgyqw748\nBox 2️⃣3️⃣: Hạ Rank \nzalo.me/g/lnuarr372",
    "13:00": "𝙍𝙊𝙎𝙔 𝘼𝙍𝙀𝙉𝘼 𝙎𝙃𝙊𝙋\n𝙈𝙪𝙖 𝙝𝙖𝙘𝙠 𝙢𝙖𝙥 𝙤̛̉ 𝙙𝙖̂𝙮\nBán box zalo\nBox 1️⃣: Leo rank Tlt\nzalo.me/g/olpwed729\nBox 2️⃣: Reg Đi Bot\nzalo.me/g/bjnwqv874\nBox 3️⃣: Reg Bot 5 Game\nzalo.me/g/oiqhul568\nBox 4️⃣: Box Leo Rank\nzalo.me/g/ochyyh448\nBox 5️⃣: TLT- Nor 5-5\nzalo.me/g/lzygxi684\nBox 6️⃣Leo rank\nzalo.me/g/qlhssk809\nBox 7️⃣ : Leo CT-CTG\nzalo.me/g/xvtszw104\nBox 8️⃣: Hạ Rank Cấp Tốc\nzalo.me/g/sjrbqa638\nBox 9️⃣ Leo rank\nzalo.me/g/cmbmjz408\nBox: 🔟 Leo hạ rank\nzalo.me/g/vtgpfr533\nBox 1️⃣1️⃣: Hạ Rank\nzalo.me/g/dmgtoc729\nBox 1️⃣2️⃣: Hạ Rank \nzalo.me/g/tlxiin969 \nBox 1️⃣3️⃣: Cầm Đèn Leo Rank \nzalo.me/g/spaqlb267\nBox 1️⃣4️⃣: Hạ Rank \nzalo.me/g/byuqks230 \nBox 1️⃣5️⃣ : Hạ rank 24/7 \nzalo.me/g/khjrna643\nBox 1️⃣6️⃣: Nghiện Liên Quân \nzalo.me/g/zfziaz213\nBox 1️⃣7️⃣: Hạ Rank \nzalo.me/g/smibnr474\nBox 1️⃣8️⃣: Tlt 3 vs 3 \nzalo.me/g/tyldqj123\nBox 1️⃣9️⃣ : Leo Rank \nzalo.me/g/lulmlw377 \nBox 2️⃣0️⃣ Hạ rank \nzalo.me/g/ysdgtu142\nBox 2️⃣1️⃣: Keo rank \nzalo.me/g/lalvob031\nBox 2️⃣2️⃣: Leo rank \nzalo.me/g/crgyqw748\nBox 2️⃣3️⃣: Hạ Rank \nzalo.me/g/lnuarr372",
    "15:00": "𝙍𝙊𝙎𝙔 𝘼𝙍𝙀𝙉𝘼 𝙎𝙃𝙊𝙋\n𝙈𝙪𝙖 𝙝𝙖𝙘𝙠 𝙢𝙖𝙥 𝙤̛̉ 𝙙𝙖̂𝙮\nBán box zalo\nBox 1️⃣: Leo rank Tlt\nzalo.me/g/olpwed729\nBox 2️⃣: Reg Đi Bot\nzalo.me/g/bjnwqv874\nBox 3️⃣: Reg Bot 5 Game\nzalo.me/g/oiqhul568\nBox 4️⃣: Box Leo Rank\nzalo.me/g/ochyyh448\nBox 5️⃣: TLT- Nor 5-5\nzalo.me/g/lzygxi684\nBox 6️⃣Leo rank\nzalo.me/g/qlhssk809\nBox 7️⃣ : Leo CT-CTG\nzalo.me/g/xvtszw104\nBox 8️⃣: Hạ Rank Cấp Tốc\nzalo.me/g/sjrbqa638\nBox 9️⃣ Leo rank\nzalo.me/g/cmbmjz408\nBox: 🔟 Leo hạ rank\nzalo.me/g/vtgpfr533\nBox 1️⃣1️⃣: Hạ Rank\nzalo.me/g/dmgtoc729\nBox 1️⃣2️⃣: Hạ Rank \nzalo.me/g/tlxiin969 \nBox 1️⃣3️⃣: Cầm Đèn Leo Rank \nzalo.me/g/spaqlb267\nBox 1️⃣4️⃣: Hạ Rank \nzalo.me/g/byuqks230 \nBox 1️⃣5️⃣ : Hạ rank 24/7 \nzalo.me/g/khjrna643\nBox 1️⃣6️⃣: Nghiện Liên Quân \nzalo.me/g/zfziaz213\nBox 1️⃣7️⃣: Hạ Rank \nzalo.me/g/smibnr474\nBox 1️⃣8️⃣: Tlt 3 vs 3 \nzalo.me/g/tyldqj123\nBox 1️⃣9️⃣ : Leo Rank \nzalo.me/g/lulmlw377 \nBox 2️⃣0️⃣ Hạ rank \nzalo.me/g/ysdgtu142\nBox 2️⃣1️⃣: Keo rank \nzalo.me/g/lalvob031\nBox 2️⃣2️⃣: Leo rank \nzalo.me/g/crgyqw748\nBox 2️⃣3️⃣: Hạ Rank \nzalo.me/g/lnuarr372",
    "17:00": "𝙍𝙊𝙎𝙔 𝘼𝙍𝙀𝙉𝘼 𝙎𝙃𝙊𝙋\n𝙈𝙪𝙖 𝙝𝙖𝙘𝙠 𝙢𝙖𝙥 𝙤̛̉ 𝙙𝙖̂𝙮\nBán box zalo\nBox 1️⃣: Leo rank Tlt\nzalo.me/g/olpwed729\nBox 2️⃣: Reg Đi Bot\nzalo.me/g/bjnwqv874\nBox 3️⃣: Reg Bot 5 Game\nzalo.me/g/oiqhul568\nBox 4️⃣: Box Leo Rank\nzalo.me/g/ochyyh448\nBox 5️⃣: TLT- Nor 5-5\nzalo.me/g/lzygxi684\nBox 6️⃣Leo rank\nzalo.me/g/qlhssk809\nBox 7️⃣ : Leo CT-CTG\nzalo.me/g/xvtszw104\nBox 8️⃣: Hạ Rank Cấp Tốc\nzalo.me/g/sjrbqa638\nBox 9️⃣ Leo rank\nzalo.me/g/cmbmjz408\nBox: 🔟 Leo hạ rank\nzalo.me/g/vtgpfr533\nBox 1️⃣1️⃣: Hạ Rank\nzalo.me/g/dmgtoc729\nBox 1️⃣2️⃣: Hạ Rank \nzalo.me/g/tlxiin969 \nBox 1️⃣3️⃣: Cầm Đèn Leo Rank \nzalo.me/g/spaqlb267\nBox 1️⃣4️⃣: Hạ Rank \nzalo.me/g/byuqks230 \nBox 1️⃣5️⃣ : Hạ rank 24/7 \nzalo.me/g/khjrna643\nBox 1️⃣6️⃣: Nghiện Liên Quân \nzalo.me/g/zfziaz213\nBox 1️⃣7️⃣: Hạ Rank \nzalo.me/g/smibnr474\nBox 1️⃣8️⃣: Tlt 3 vs 3 \nzalo.me/g/tyldqj123\nBox 1️⃣9️⃣ : Leo Rank \nzalo.me/g/lulmlw377 \nBox 2️⃣0️⃣ Hạ rank \nzalo.me/g/ysdgtu142\nBox 2️⃣1️⃣: Keo rank \nzalo.me/g/lalvob031\nBox 2️⃣2️⃣: Leo rank \nzalo.me/g/crgyqw748\nBox 2️⃣3️⃣: Hạ Rank \nzalo.me/g/lnuarr372",
    "19:00": "𝙍𝙊𝙎𝙔 𝘼𝙍𝙀𝙉𝘼 𝙎𝙃𝙊𝙋\n𝙈𝙪𝙖 𝙝𝙖𝙘𝙠 𝙢𝙖𝙥 𝙤̛̉ 𝙙𝙖̂𝙮\nBán box zalo\nBox 1️⃣: Leo rank Tlt\nzalo.me/g/olpwed729\nBox 2️⃣: Reg Đi Bot\nzalo.me/g/bjnwqv874\nBox 3️⃣: Reg Bot 5 Game\nzalo.me/g/oiqhul568\nBox 4️⃣: Box Leo Rank\nzalo.me/g/ochyyh448\nBox 5️⃣: TLT- Nor 5-5\nzalo.me/g/lzygxi684\nBox 6️⃣Leo rank\nzalo.me/g/qlhssk809\nBox 7️⃣ : Leo CT-CTG\nzalo.me/g/xvtszw104\nBox 8️⃣: Hạ Rank Cấp Tốc\nzalo.me/g/sjrbqa638\nBox 9️⃣ Leo rank\nzalo.me/g/cmbmjz408\nBox: 🔟 Leo hạ rank\nzalo.me/g/vtgpfr533\nBox 1️⃣1️⃣: Hạ Rank\nzalo.me/g/dmgtoc729\nBox 1️⃣2️⃣: Hạ Rank \nzalo.me/g/tlxiin969 \nBox 1️⃣3️⃣: Cầm Đèn Leo Rank \nzalo.me/g/spaqlb267\nBox 1️⃣4️⃣: Hạ Rank \nzalo.me/g/byuqks230 \nBox 1️⃣5️⃣ : Hạ rank 24/7 \nzalo.me/g/khjrna643\nBox 1️⃣6️⃣: Nghiện Liên Quân \nzalo.me/g/zfziaz213\nBox 1️⃣7️⃣: Hạ Rank \nzalo.me/g/smibnr474\nBox 1️⃣8️⃣: Tlt 3 vs 3 \nzalo.me/g/tyldqj123\nBox 1️⃣9️⃣ : Leo Rank \nzalo.me/g/lulmlw377 \nBox 2️⃣0️⃣ Hạ rank \nzalo.me/g/ysdgtu142\nBox 2️⃣1️⃣: Keo rank \nzalo.me/g/lalvob031\nBox 2️⃣2️⃣: Leo rank \nzalo.me/g/crgyqw748\nBox 2️⃣3️⃣: Hạ Rank \nzalo.me/g/lnuarr372",
    "21:00": "𝙍𝙊𝙎𝙔 𝘼𝙍𝙀𝙉𝘼 𝙎𝙃𝙊𝙋\n𝙈𝙪𝙖 𝙝𝙖𝙘𝙠 𝙢𝙖𝙥 𝙤̛̉ 𝙙𝙖̂𝙮\nBán box zalo\nBox 1️⃣: Leo rank Tlt\nzalo.me/g/olpwed729\nBox 2️⃣: Reg Đi Bot\nzalo.me/g/bjnwqv874\nBox 3️⃣: Reg Bot 5 Game\nzalo.me/g/oiqhul568\nBox 4️⃣: Box Leo Rank\nzalo.me/g/ochyyh448\nBox 5️⃣: TLT- Nor 5-5\nzalo.me/g/lzygxi684\nBox 6️⃣Leo rank\nzalo.me/g/qlhssk809\nBox 7️⃣ : Leo CT-CTG\nzalo.me/g/xvtszw104\nBox 8️⃣: Hạ Rank Cấp Tốc\nzalo.me/g/sjrbqa638\nBox 9️⃣ Leo rank\nzalo.me/g/cmbmjz408\nBox: 🔟 Leo hạ rank\nzalo.me/g/vtgpfr533\nBox 1️⃣1️⃣: Hạ Rank\nzalo.me/g/dmgtoc729\nBox 1️⃣2️⃣: Hạ Rank \nzalo.me/g/tlxiin969 \nBox 1️⃣3️⃣: Cầm Đèn Leo Rank \nzalo.me/g/spaqlb267\nBox 1️⃣4️⃣: Hạ Rank \nzalo.me/g/byuqks230 \nBox 1️⃣5️⃣ : Hạ rank 24/7 \nzalo.me/g/khjrna643\nBox 1️⃣6️⃣: Nghiện Liên Quân \nzalo.me/g/zfziaz213\nBox 1️⃣7️⃣: Hạ Rank \nzalo.me/g/smibnr474\nBox 1️⃣8️⃣: Tlt 3 vs 3 \nzalo.me/g/tyldqj123\nBox 1️⃣9️⃣ : Leo Rank \nzalo.me/g/lulmlw377 \nBox 2️⃣0️⃣ Hạ rank \nzalo.me/g/ysdgtu142\nBox 2️⃣1️⃣: Keo rank \nzalo.me/g/lalvob031\nBox 2️⃣2️⃣: Leo rank \nzalo.me/g/crgyqw748\nBox 2️⃣3️⃣: Hạ Rank \nzalo.me/g/lnuarr372",
    "23:00": "𝙍𝙊𝙎𝙔 𝘼𝙍𝙀𝙉𝘼 𝙎𝙃𝙊𝙋\n𝙈𝙪𝙖 𝙝𝙖𝙘𝙠 𝙢𝙖𝙥 𝙤̛̉ 𝙙𝙖̂𝙮\nBán box zalo\nBox 1️⃣: Leo rank Tlt\nzalo.me/g/olpwed729\nBox 2️⃣: Reg Đi Bot\nzalo.me/g/bjnwqv874\nBox 3️⃣: Reg Bot 5 Game\nzalo.me/g/oiqhul568\nBox 4️⃣: Box Leo Rank\nzalo.me/g/ochyyh448\nBox 5️⃣: TLT- Nor 5-5\nzalo.me/g/lzygxi684\nBox 6️⃣Leo rank\nzalo.me/g/qlhssk809\nBox 7️⃣ : Leo CT-CTG\nzalo.me/g/xvtszw104\nBox 8️⃣: Hạ Rank Cấp Tốc\nzalo.me/g/sjrbqa638\nBox 9️⃣ Leo rank\nzalo.me/g/cmbmjz408\nBox: 🔟 Leo hạ rank\nzalo.me/g/vtgpfr533\nBox 1️⃣1️⃣: Hạ Rank\nzalo.me/g/dmgtoc729\nBox 1️⃣2️⃣: Hạ Rank \nzalo.me/g/tlxiin969 \nBox 1️⃣3️⃣: Cầm Đèn Leo Rank \nzalo.me/g/spaqlb267\nBox 1️⃣4️⃣: Hạ Rank \nzalo.me/g/byuqks230 \nBox 1️⃣5️⃣ : Hạ rank 24/7 \nzalo.me/g/khjrna643\nBox 1️⃣6️⃣: Nghiện Liên Quân \nzalo.me/g/zfziaz213\nBox 1️⃣7️⃣: Hạ Rank \nzalo.me/g/smibnr474\nBox 1️⃣8️⃣: Tlt 3 vs 3 \nzalo.me/g/tyldqj123\nBox 1️⃣9️⃣ : Leo Rank \nzalo.me/g/lulmlw377 \nBox 2️⃣0️⃣ Hạ rank \nzalo.me/g/ysdgtu142\nBox 2️⃣1️⃣: Keo rank \nzalo.me/g/lalvob031\nBox 2️⃣2️⃣: Leo rank \nzalo.me/g/crgyqw748\nBox 2️⃣3️⃣: Hạ Rank \nzalo.me/g/lnuarr372"
}

vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')

def start_auto(client):
    try:
        listvd = "https://raw.githubusercontent.com/nguyenductai206/list/refs/heads/main/listvideo.json"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }
        
        response = requests.get(listvd, headers=headers)
        response.raise_for_status()
        urls = response.json()
        video_url = random.choice(urls)

        thumbnail_url = "https://i.imgur.com/As0K5cN.jpeg"
        duration = '1000'

    except Exception as e:
        print(f"Error fetching video list: {e}")
        return

    all_group = client.fetchAllGroups()
    allowed_thread_ids = [gid for gid in all_group.gridVerMap.keys() if gid != '9034032228046851908']

    last_sent_time = None

    while True:
        now = datetime.now(vn_tz)
        current_time_str = now.strftime("%H:%M")
        
        if current_time_str in time_messages and (last_sent_time is None or now - last_sent_time >= timedelta(minutes=1)):
            message = time_messages[current_time_str]
            for thread_id in allowed_thread_ids:
                gui = Message(text=f"[Rải link tự động\n{current_time_str} ]\n> {message}")
                try:
                    client.sendRemoteVideo(
                        video_url, 
                        thumbnail_url,
                        duration=duration,
                        message=gui,
                        thread_id=thread_id,
                        thread_type=ThreadType.GROUP,
                        width=1080,
                        height=1920
                    )
                    time.sleep(0.3)
                except Exception as e:
                    print(f"Error sending message to {thread_id}: {e}")
            last_sent_time = now
        
        time.sleep(30)

def handle_autosend_start(message, message_object, thread_id, thread_type, author_id, client):
    # Khởi chạy auto trong luồng riêng
    threading.Thread(target=start_auto, args=(client,), daemon=True).start()
    response_message = Message(text="Đã bật tính năng tự động rải link theo thời gian đã định ✅🚀")
    client.replyMessage(response_message, message_object, thread_id, thread_type)

def get_mitaizl():
    return {
        'tudonggui': handle_autosend_start
    }