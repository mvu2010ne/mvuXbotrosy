# Sử dụng môi trường Python nhẹ
FROM python:3.10-slim

# Đặt thư mục làm việc là /app
WORKDIR /app

# Copy file requirements.txt vào container
COPY requirements.txt requirements.txt

# Cài đặt các thư viện trong requirements.txt (và cache lại)
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code trong project vào container
COPY . .

# Chạy bot Zalo khi container khởi động
CMD ["python", "main.py"]
