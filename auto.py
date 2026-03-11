import subprocess
import re
import os
import sys
import time

def credit():
    """Developer: Minh Vũ"""

# ================= RUN BOT =================
def run_bot(cmd):
    print(f"\n[DEBUG] Khởi chạy: {cmd}")
    return subprocess.Popen(cmd, shell=True)

def run_command(cmd):
    result = subprocess.run(
        cmd,
        shell=True,
        text=True,
        capture_output=True
    )
    return result.stdout, result.stderr, result.returncode

# ================= PACKAGE MAP =================
def get_real_package_name(module):
    package_map = {
        'Crypto': ('pycryptodome', []),
        'zlib': ('', ['zlib']),  
        'brotli': ('brotli', []),
        'cv2': ('opencv-python', ['libopencv']),
        'PIL': ('Pillow', ['libjpeg-turbo', 'libpng', 'freetype']),
        'zbar': ('pyzbar', ['zbar']),
        'pyzbar': ('pyzbar', ['zbar']),
        'imageio': ('imageio', []),
        'bs4': ('beautifulsoup4', []),
        'lxml': ('lxml', ['libxml2', 'libxslt']),
        'html5lib': ('html5lib', []),
        'requests_html': ('requests-html', ['libxml2']),
        'selenium': ('selenium', []),
        'seleniumwire': ('seleniumWire', []),
        'undetected_chromedriver': ('undetected-chromedriver', []),
        'yaml': ('PyYAML', []),
        'ujson': ('ujson', []),
        'orjson': ('orjson', []),
        'numpy': ('numpy', []),
        'pandas': ('pandas', ['numpy']),
        'matplotlib': ('matplotlib', ['freetype', 'libpng']),
        'seaborn': ('seaborn', ['numpy', 'pandas', 'matplotlib']),
        'sklearn': ('scikit-learn', []),
        'scipy': ('scipy', ['numpy']),
        'torch': ('torch', []),  
        'tensorflow': ('tensorflow', []),  
        'xgboost': ('xgboost', []),
        'transformers': ('transformers', []),
        'datasets': ('datasets', []),
        'requests': ('requests', []),
        'httpx': ('httpx', []),
        'aiohttp': ('aiohttp', []),
        'openpyxl': ('openpyxl', []),
        'xlrd': ('xlrd', []),
        'xlwt': ('xlwt', []),
        'python_docx': ('python-docx', []),
        'docx': ('python-docx', []),
        'pdfplumber': ('pdfplumber', ['poppler']),
        'PyPDF2': ('PyPDF2', []),
        'rich': ('rich', []),
        'termcolor': ('termcolor', []),
        'colorama': ('colorama', []),
        'tqdm': ('tqdm', []),
        'pyfiglet': ('pyfiglet', []),
        'flask': ('Flask', []),
        'fastapi': ('fastapi', ['uvicorn']),
        'uvicorn': ('uvicorn', []),
        'socketio': ('python-socketio', []),
        'websocket': ('websocket-client', []),
        'pyshorteners': ('pyshorteners', []),
        'pyperclip': ('pyperclip', ['xclip']),
        'fake_useragent': ('fake-useragent', []),
        'webdriver_manager': ('webdriver-manager', []),
        'qrcode': ('qrcode', []),
        'googlesearch': ('googlesearch-python', []),
        'speedtest': ('speedtest-cli', []),
        'whois': ('python-whois', []),
        'dns': ('dnspython', []),
        'tabulate': ('tabulate', []),
        'pytz': ('pytz', []),
        'schedule': ('schedule', []),
        'loguru': ('loguru', []),
        'ffmpeg': ('ffmpeg', []),
        'asyncio': ('', []),  
        'threading': ('', []),  
        'sqlalchemy': ('SQLAlchemy', []),
        'psycopg2': ('psycopg2-binary', ['libpq']),
        'pymysql': ('PyMySQL', []),
        'sqlite3': ('', []),  
        'django': ('Django', []),
        'jinja2': ('Jinja2', []),
        'werkzeug': ('Werkzeug', []),
        'gunicorn': ('gunicorn', []),
        'celery': ('celery', ['redis']),
        'redis': ('redis', ['redis-server']),
        'pika': ('pika', []),
        'boto3': ('boto3', []),
        'botocore': ('botocore', []),
        's3fs': ('s3fs', []),
        'paramiko': ('paramiko', ['libffi']),
        'cryptography': ('cryptography', ['openssl']),
        'pyOpenSSL': ('pyOpenSSL', ['openssl']),
        'pyjwt': ('PyJWT', []),
        'oauthlib': ('oauthlib', []),
        'requests_oauthlib': ('requests-oauthlib', []),
        'pyarrow': ('pyarrow', []),
        'dask': ('dask', []),
        'numba': ('numba', []),
        'cupy': ('cupy', []),  
        'pytorch_lightning': ('pytorch-lightning', []),
        'keras': ('keras', []),
        'onnx': ('onnx', []),
        'onnxruntime': ('onnxruntime', []),
        'spacy': ('spacy', []),
        'nltk': ('nltk', []),
        'gensim': ('gensim', []),
        'textblob': ('textblob', []),
        'plotly': ('plotly', []),
        'bokeh': ('bokeh', []),
        'holoviews': ('holoviews', []),
        'streamlit': ('streamlit', []),
        'dash': ('dash', []),
        'pydantic': ('pydantic', []),
        'sqlparse': ('sqlparse', []),
        'pytest': ('pytest', []),
        'unittest': ('', []),  
        'mock': ('', []),  
        'coverage': ('coverage', []),
        'flake8': ('flake8', []),
        'black': ('black', []),
        'isort': ('isort', []),
        'mypy': ('mypy', []),
        'pylint': ('pylint', []),
        'pyautogui': ('PyAutoGUI', []),
        'keyboard': ('keyboard', []),
        'mouse': ('mouse', []),
        'pywin32': ('pywin32', []),  
        'pyinstaller': ('PyInstaller', []),
        'cx_Freeze': ('cx-Freeze', []),
        'py2exe': ('py2exe', []),  
        'click': ('click', []),
        'typer': ('typer', []),
        'argparse': ('', []),  
        'configparser': ('', []),  
        'pathlib': ('', []),  
        'pendulum': ('pendulum', []),
        'arrow': ('arrow', []),
        'dateutil': ('python-dateutil', []),
        'psutil': ('psutil', []),
        'shutil': ('', []),  
        'os': ('', []),  
        'sys': ('', []),  
        'json': ('', []),  
        'pickle': ('', []),  
        'csv': ('', []),  
        'logging': ('', []),  
        'argparse': ('', []),  
        'random': ('', []),  
        'math': ('', []),  
        'datetime': ('', []),  
        're': ('', []),  
        'urllib': ('', []),  
        'http': ('', []),  
        'socket': ('', []),  
        'multiprocessing': ('', []),  
        'concurrent': ('', []),  
        'queue': ('', []),  
        'time': ('', []),  
        'secrets': ('', []),  
        'hashlib': ('', []),  
        'base64': ('', []),  
        'uuid': ('', []),  
        'itertools': ('', []),  
        'collections': ('', []),  
        'functools': ('', []),  
        'operator': ('', []),  
        'statistics': ('', []),  
        'decimal': ('', []),  
        'fractions': ('', []),  
        'heapq': ('', []),  
        'bisect': ('', []),  
        'array': ('', []),  
    }
    return package_map.get(module, (module, []))

# ================= INSTALL =================
def install_system_packages(pkgs):
    for pkg in pkgs:
        print(f"[PKG] Cài thư viện hệ thống: {pkg}")
        subprocess.run(f"yes | pkg install {pkg}", shell=True)

def install_pip_package(pkg):
    if not pkg:
        return
    print(f"[PIP] Cài thư viện Python: {pkg}")
    subprocess.run(f"pip install {pkg}", shell=True)

# ================= ERROR PARSE =================
def find_missing_module(stderr):
    match = re.search(r"No module named ['\"](.*?)['\"]", stderr)
    return match.group(1) if match else None

# ================= NORMALIZE CMD =================
def normalize_command(cmd):
    if cmd.endswith(".py") and not cmd.startswith("python"):
        return f"python {cmd}"
    return cmd

# ================= MAIN =================
def main():
    print("📥 Nhập file cần chạy (VD: main.py):")
    user_cmd = input("MinhVu!Localhost# ").strip()

    if not user_cmd:
        print("❌ Không nhập lệnh.")
        return

    cmd = normalize_command(user_cmd)

    for _ in range(30):
        process = run_bot(cmd)
        time.sleep(2)

        # ===== BOT CHẾT SỚM =====
        if process.poll() is not None:
            print("⚠️ Bot dừng sớm, kiểm tra lỗi...")

            stdout, stderr, code = run_command(cmd)
            print(stdout)
            print(stderr)

            missing = find_missing_module(stderr)
            if not missing:
                print("❌ Lỗi không phải do thiếu thư viện.")
                break

            print(f"📦 Thiếu module: {missing}")

            pip_pkg, sys_pkgs = get_real_package_name(missing)

            # 1️⃣ CÀI PKG TRƯỚC
            if sys_pkgs:
                install_system_packages(sys_pkgs)

            # 2️⃣ CÀI PIP
            install_pip_package(pip_pkg)

            print("🔁 Cài xong → chạy lại bot...\n")
            time.sleep(1)
            continue

        # ===== BOT CHẠY THẬT =====
        print("✅ Bot đang chạy THẬT (giống python main.py)")
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\n⛔ Dừng bot.")
            process.terminate()
        return

    print("⚠️ Quá số lần thử.")

# ================= ENTRY =================
if __name__ == "__main__":
    main()