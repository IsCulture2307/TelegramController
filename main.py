import asyncio
import os
import re
import sys
import logging
from datetime import datetime

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QInputDialog, QLineEdit, QStyle
from telethon import TelegramClient, errors

from core.telegram import send_message_to_chats, get_group_ids_and_names
from core.scheduler import initialize_scheduler, shutdown_scheduler, update_or_create_schedule
from ui.control_panel import ControlPanel
from ui.login_window import LoginWindow
from ui.widgets import LoadingDialog, ResultDialog
from utils.config import config,load_config, API_ID, API_HASH, DEFAULT_ACCOUNT_CONFIG
from utils.helpers import resource_path, app_path

# ==== 配置日志 ====
log_folder = app_path("log")
if not os.path.exists(log_folder):
    os.makedirs(log_folder)
current_date = datetime.now().strftime("%Y-%m-%d")
log_filename = f"telegram_controller_{current_date}.log"
log_file = os.path.join(log_folder, log_filename)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
    force=True
)

class App:
    def __init__(self, loop):
        self.loop = loop
        self.current_panel = None
        self.scheduler = initialize_scheduler(self.loop)

    async def start(self):
        load_config()
        while True:
            login_result = self.show_login_window()
            if not login_result:
                logging.info("用户关闭登录窗口，退出应用")
                break
            if login_result == '__add_new__':
                await self.add_new_account_flow()
                continue
            session_name = login_result
            await self.run_control_panel(session_name)
            logging.info(f"账号 '{session_name}' 已退出返回账号选择菜单")

        shutdown_scheduler()
        QApplication.instance().quit()

    def show_login_window(self):
        dialog = LoginWindow()
        return dialog.selected_session if dialog.exec() else None

    async def add_new_account_flow(self):
        """
        一个完整的、基于 PyQt 弹窗的异步登录流程，并确保只在成功时保存 session
        """
        session_name, ok = QInputDialog.getText(None, "第1步：设置别名", "请输入一个账号别名 (只能用英文和数字):")
        if not ok or not session_name: return
        session_name = session_name.strip()
        if not re.match("^[a-zA-Z0-9_]+$", session_name): ResultDialog.show_message(None, ResultDialog.ResultType.ERROR, "错误", "别名不合法"); return
        if os.path.exists(f"session/{session_name}.session"): ResultDialog.show_message(None, ResultDialog.ResultType.ERROR, "错误", "该别名已存在"); return

        phone, ok = QInputDialog.getText(None, f"第2步：输入手机号 ({session_name})", "请输入手机号码(+869121037658):")
        if not ok or not phone: return
        session_folder = app_path("session")
        os.makedirs(session_folder, exist_ok=True)
        session_file = os.path.join(session_folder, f"{session_name}.session")
        client = TelegramClient(session_file, API_ID, API_HASH)
        login_success = False

        loading_dialog = LoadingDialog()
        try:
            await client.connect()
            if not await client.is_user_authorized():
                loading_dialog.show_message("正在请求Telegram发送验证码...")
                sent_code = await client.send_code_request(phone)
                loading_dialog.close_dialog()

                code, ok = QInputDialog.getText(None, f"第3步：输入验证码 ({session_name})", f"已向 {phone} 发送验证码，请输入:")
                if not ok or not code:
                    raise InterruptedError("用户取消了输入验证码")  # 主动抛出异常以进入 finally

                try:
                    loading_dialog.show_message("正在验证Telegram验证码...")
                    await client.sign_in(phone, code, phone_code_hash=sent_code.phone_code_hash)
                    loading_dialog.close_dialog()
                except errors.SessionPasswordNeededError:
                    password, ok = QInputDialog.getText(None, f"第4步：输入两步验证密码 ({session_name})", "此账号已启用两步验证，请输入密码:", QLineEdit.EchoMode.Password)
                    if not ok or not password:
                        raise InterruptedError("用户取消了输入密码")

                    loading_dialog.show_message("正在验证两步验证密码...")
                    await client.sign_in(password=password)
                    loading_dialog.close_dialog()

            # **关键修复 2：只有在所有步骤都完成后，才标记为成功**
            login_success = True
            ResultDialog.show_message(None, ResultDialog.ResultType.SUCCESS, "成功", f"账号 '{session_name}' 登录成功！\n\n请在您的Telegram设备上确认本人操作")

        except InterruptedError as e:
            loading_dialog.close_dialog()
            logging.warning(f"❌ 登录被用户取消: {e}")
            # 用户取消，不需要弹窗报错，静默处理
        except Exception as e:
            loading_dialog.close_dialog()
            logging.error(f"❌ 登录流程失败: {e}")
            ResultDialog.show_message(None, ResultDialog.ResultType.ERROR, "验证失败", f"登录流程失败: {e}")

        finally:
            if client.is_connected():
                await client.disconnect()

            if not login_success and os.path.exists(session_file):
                try:
                    os.remove(session_file)
                    logging.info(f"🔥 已删除不完整的 session 文件: {session_file}")
                except OSError as e:
                    logging.error(f"❌ 删除不完整的 session 文件失败: {e}")

    async def run_control_panel(self, session_name):
        try:
            closed_future = self.loop.create_future()
            callbacks = {
                'on_close'       : lambda: not closed_future.done() and closed_future.set_result(True),
                'get_groups'     : lambda: self.loop.create_task(self.get_groups_task(session_name)),
                'send_now'       : lambda ids, text: self.loop.create_task(self.send_now_task(session_name, ids, text)),
                'update_schedule': lambda s_name: self.loop.create_task(update_or_create_schedule(s_name))
            }

            if session_name not in config["accounts"]:
                config["accounts"][session_name] = DEFAULT_ACCOUNT_CONFIG.copy()
                # 把这个账号的专属配置提取出来
            account_config_for_panel = config["accounts"][session_name]

            logging.info("即将创建 ControlPanel 实例...")
            self.current_panel = ControlPanel(session_name, account_config_for_panel, callbacks)
            logging.info("ControlPanel 实例创建成功！")
            await update_or_create_schedule(session_name)
            self.current_panel.show()
            await closed_future

        except Exception as e:
            logging.error(f"创建ControlPanel时发生致命错误: {e}, 错误类型: {type(e).__name__}", exc_info=True)
            ResultDialog.show_message(None, ResultDialog.ResultType.ERROR, "严重错误", f"无法加载主控制面板，请检查日志文件获取详细信息。\n\n错误: {e}")

    async def get_groups_task(self, session_name):
        groups, error = await get_group_ids_and_names(session_name)
        if self.current_panel:
            self.current_panel.handle_get_groups_result(groups, error)

    async def send_now_task(self, session_name, ids, text):
        chat_id_map = {int(k): v for k, v in self.current_panel.account_config["target_chats"].items()}
        success, message, sent_ids = await send_message_to_chats(session_name, ids, text, chat_id_map)
        if self.current_panel:
            self.current_panel.handle_send_now_result(success, message, sent_ids)

# ==== 7. 程序入口 (最终稳定版) ====
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # vvvv---- 新增应用图标设置 ----vvvv
    app_icon_path = resource_path(os.path.join("icons", "app_icon.svg"))
    if os.path.exists(app_icon_path):
        app.setWindowIcon(QIcon(app_icon_path))
    else:
        # 如果找不到自定义图标，使用一个系统默认图标
        style = app.style()
        icon = style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        app.setWindowIcon(icon)
    # ^^^^---- 新增应用图标设置 ----^^^^

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)


    def update_asyncio():
        loop.run_until_complete(asyncio.sleep(0.01))


    timer = QTimer()
    timer.setInterval(20)
    timer.timeout.connect(update_asyncio)
    timer.start()

    main_app = App(loop)

    print("程序启动，正在加载登录窗口")
    main_task = loop.create_task(main_app.start())

    sys.exit(app.exec())