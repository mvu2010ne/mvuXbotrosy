#!/bin/bash
cd /mnt/c/tets/bottngan-main/ngan

# File log của bot
LOG_FILE="bot.log"
# File log của script
SCRIPT_LOG="monitor.log"
# Thời gian tối đa không có log mới (phút)
MAX_INACTIVE_MINUTES=2
# Đường dẫn đến Python
PYTHON="python3"
# Lệnh chạy bot
BOT_COMMAND="$PYTHON main.py"

# Hàm ghi log cho script
log_message() {
    echo "[$(date)] $1" >> "$SCRIPT_LOG"
}

# Hàm kiểm tra bot có treo không
check_bot() {
    if [ -f "$LOG_FILE" ]; then
        # Kiểm tra thời gian sửa đổi file log
        if [ $(find "$LOG_FILE" -mmin +$MAX_INACTIVE_MINUTES | wc -l) -gt 0 ]; then
            log_message "Bot treo (log không cập nhật trong $MAX_INACTIVE_MINUTES phút). Khởi động lại..."
            return 1
        fi
    else
        log_message "File log $LOG_FILE không tồn tại. Khởi động bot..."
        return 1
    fi
    return 0
}

while true; do
    # Reset file bot.log trước khi chạy bot
    > "$LOG_FILE"
    log_message "Đã reset file $LOG_FILE"

    # Chạy bot trong nền và ghi log
    $BOT_COMMAND >> "$LOG_FILE" 2>&1 &
    BOT_PID=$!
    log_message "Bot started with PID $BOT_PID"

    # Giám sát bot
    while kill -0 $BOT_PID 2>/dev/null; do
        if ! check_bot; then
            log_message "Killing hung bot (PID $BOT_PID)"
            kill $BOT_PID
            wait $BOT_PID 2>/dev/null
            break
        fi
        sleep 30  # Kiểm tra mỗi 30 giây
    done

    log_message "Bot stopped or crashed. Restarting in 5 seconds"
    sleep 5
done
