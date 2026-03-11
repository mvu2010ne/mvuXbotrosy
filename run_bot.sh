#!/bin/bash
cd /mnt/c/tets/bottngan-main/ngan
while true; do
    python3 main.py
    echo "Bot crashed with exit code $?. Restarting..." >&2
    sleep 5  # Đợi 5 giây trước khi khởi động lại
done
