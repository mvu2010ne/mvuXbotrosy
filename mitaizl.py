from zlapi.models import Message
import os
import importlib
from config import PREFIX

# ANSI color codes
RESET = '\033[0m'
BOLD = '\033[1m'
GREEN = '\033[92m'
RED = '\033[91m'
CYAN = '\033[96m'
YELLOW = '\033[93m'

class CommandHandler:
    def __init__(self, client):
        self.client = client
        self.mitaizl = self.load_mitaizl()
        self.auto_mitaizl = self.load_auto_mitaizl()

    def load_mitaizl(self):
        mitaizl = {}
        modules_path = 'modules'
        success_count = 0
        failed_count = 0
        success_mitaizl = []
        failed_mitaizl = []

        for filename in os.listdir(modules_path):
            if filename.endswith('.py') and filename != '__init__.py':
                module_name = filename[:-3]
                try:
                    module = importlib.import_module(f'{modules_path}.{module_name}')
                    if hasattr(module, 'get_mitaizl'):
                        mitaizl.update(module.get_mitaizl())
                        success_count += 1
                        success_mitaizl.append(module_name)
                    else:
                        raise ImportError(f"Module {module_name} không có hàm get_mitaizl")
                except Exception as e:
                    print(f"{BOLD}{RED}✖ Tải module thất bại: {module_name} | Lỗi: {e}{RESET}")
                    failed_count += 1
                    failed_mitaizl.append(module_name)

        # Beautified output for commands
        self._print_load_summary(
            prefix=PREFIX,
            command_type="Lệnh",
            success_count=success_count,
            success_list=success_mitaizl,
            failed_count=failed_count,
            failed_list=failed_mitaizl
        )

        return mitaizl

    def load_auto_mitaizl(self):
        """Tải các lệnh không cần tiền tố từ 'modules/auto'."""
        auto_mitaizl = {}
        auto_modules_path = 'modules.auto'
        success_count = 0
        failed_count = 0
        success_auto_mitaizl = []
        failed_auto_mitaizl = []

        try:
            for filename in os.listdir('modules/auto'):
                if filename.endswith('.py') and filename != '__init__.py':
                    module_name = filename[:-3]
                    try:
                        module = importlib.import_module(f'{auto_modules_path}.{module_name}')
                        if hasattr(module, 'get_mitaizl'):
                            auto_mitaizl.update(module.get_mitaizl())
                            success_count += 1
                            success_auto_mitaizl.append(module_name)
                        else:
                            raise ImportError(f"Module {module_name} không có hàm get_mitaizl")
                    except Exception as e:
                        print(f"{BOLD}{RED}✖ Tải module tự động thất bại: {module_name} | Lỗi: {e}{RESET}")
                        failed_count += 1
                        failed_auto_mitaizl.append(module_name)
        except FileNotFoundError:
            print(f"{BOLD}{YELLOW}⚠ Không tìm thấy thư mục 'modules/auto'. Bỏ qua các lệnh tự động.{RESET}")

        # Beautified output for auto commands
        self._print_load_summary(
            prefix=None,
            command_type="Lệnh Tự Động",
            success_count=success_count,
            success_list=success_auto_mitaizl,
            failed_count=failed_count,
            failed_list=failed_auto_mitaizl
        )

        return auto_mitaizl

    def _print_load_summary(self, prefix, command_type, success_count, success_list, failed_count, failed_list):
        """Phương thức hỗ trợ để in tóm tắt tải lệnh với định dạng đẹp mắt."""
        # Định nghĩa các ký tự Unicode cho khung
        TOP_LEFT = "╔"
        TOP_RIGHT = "╗"
        BOTTOM_LEFT = "╚"
        BOTTOM_RIGHT = "╝"
        HORIZONTAL = "═"
        VERTICAL = "║"
        WIDTH = 40  # Chiều rộng khung

        # Tiêu đề
        title = f" Tóm Tắt Tải {command_type} "
        title_line = f"{BOLD}{CYAN}{TOP_LEFT}{HORIZONTAL * 2}{title.center(WIDTH - 6, HORIZONTAL)}{HORIZONTAL * 2}{TOP_RIGHT}{RESET}"
        print(f"\n{title_line}")

        # In thông tin tiền tố nếu có
        if prefix:
            print(f"{BOLD}{CYAN}{VERTICAL} Tiền tố: {GREEN}{prefix}{RESET}{CYAN}{' ' * (WIDTH - 12 - len(prefix))}{VERTICAL}{RESET}")

        # In thông tin lệnh tải thành công
        if success_count > 0:
            success_text = f"✔ Tải thành công {success_count} {command_type.lower()}"
            print(f"{BOLD}{CYAN}{VERTICAL} {GREEN}{success_text}{RESET}{CYAN}{' ' * (WIDTH - 5 - len(success_text))}{VERTICAL}{RESET}")
            success_modules = ', '.join(success_list)
            print(f"{BOLD}{CYAN}{VERTICAL}   {success_modules}{' ' * (WIDTH - 5 - len(success_modules))}{VERTICAL}{RESET}")
        else:
            no_success_text = f"⚠ Không có {command_type.lower()} nào được tải"
            print(f"{BOLD}{CYAN}{VERTICAL} {YELLOW}{no_success_text}{RESET}{CYAN}{' ' * (WIDTH - 5 - len(no_success_text))}{VERTICAL}{RESET}")

        # In thông tin lệnh tải thất bại
        if failed_count > 0:
            failed_text = f"✖ Tải thất bại {failed_count} {command_type.lower()}"
            print(f"{BOLD}{CYAN}{VERTICAL} {RED}{failed_text}{RESET}{CYAN}{' ' * (WIDTH - 5 - len(failed_text))}{VERTICAL}{RESET}")
            failed_modules = ', '.join(failed_list)
            print(f"{BOLD}{CYAN}{VERTICAL}   {failed_modules}{' ' * (WIDTH - 5 - len(failed_modules))}{VERTICAL}{RESET}")

        # Đóng khung
        bottom_line = f"{BOLD}{CYAN}{BOTTOM_LEFT}{HORIZONTAL * (WIDTH - 2)}{BOTTOM_RIGHT}{RESET}"
        print(f"{bottom_line}\n")

    def handle_command(self, message, author_id, message_object, thread_id, thread_type):
        # Xử lý các lệnh không cần tiền tố
        auto_command_handler = self.auto_mitaizl.get(message.lower())
        if auto_command_handler:
            auto_command_handler(message, message_object, thread_id, thread_type, author_id, self.client)
            return
        
        if not message.startswith(PREFIX):
            return

        # Xử lý các lệnh có tiền tố
        command_name = message[len(PREFIX):].split(' ')[0].lower()
        command_handler = self.mitaizl.get(command_name)

        if command_handler:
            command_handler(message, message_object, thread_id, thread_type, author_id, self.client)
        else:
            self.client.sendMessage(
                f"Lệnh '{command_name}' không tồn tại. Sử dụng {PREFIX}menu để xem danh sách lệnh khả dụng.",
                thread_id,
                thread_type
            )