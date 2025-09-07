import asyncio
import json
import os
import re
import sys
import logging
from glob import glob

# 导入 PyQt6
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
                             QPushButton, QLabel, QTextEdit, QLineEdit, QGridLayout,
                             QTabWidget, QDialog, QListWidgetItem,
                             QMessageBox, QInputDialog, QStyle)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon

# 导入 Telethon 和 APScheduler
from telethon import TelegramClient, errors
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ==== 1. 配置日志 ====
log_folder = "log"
if not os.path.exists(log_folder):
    os.makedirs(log_folder)
log_file = os.path.join(log_folder, "telegram_controller.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

# ==== 2. 全局常量和配置 ====
API_ID = 17349
API_HASH = "344583e45741c457fe1862106095a5eb"
CONFIG_FILE = "config.json"
DEFAULT_ACCOUNT_CONFIG = {"target_chats": {}, "message_text": "这是自动群发的消息 ✅", "send_hour": 12, "send_minute": 23}
DEFAULT_CONFIG = {"accounts": {}, "window_width": 750, "window_height": 700}
config = {}


# ==== 3. 读写配置 ====
def load_config():
    global config
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = f.read().strip()
                config = {**DEFAULT_CONFIG, **json.loads(data)} if data else DEFAULT_CONFIG
        except Exception as e:
            config = DEFAULT_CONFIG
            logging.error(f"❌ 加载 config.json 时发生错误: {e}")
    else:
        config = DEFAULT_CONFIG
    logging.info("✅ config.json 已加载")


def save_config():
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        logging.info("✅ 配置已保存")
    except Exception as e:
        logging.error(f"❌ 保存配置时发生错误: {e}")


# ==== 4. 核心异步功能 ====
async def send_message_to_chats(session_name, chat_ids, message_text):
    session_file = os.path.join("session", f"{session_name}.session")
    client = TelegramClient(session_file, API_ID, API_HASH)
    sent_ids = []  # 用于记录成功发送的ID
    try:
        await client.start()
        for chat_id in chat_ids:
            try:
                await client.send_message(chat_id, message_text)
                logging.info(f"✅ ({session_name}) 已发送到 {chat_id}")
                sent_ids.append(chat_id)  # 记录成功
            except Exception as e:
                logging.error(f"❌ ({session_name}) 发送到 {chat_id} 失败: {e}")
        # **关键修改：返回成功发送的 ID 列表**
        return True, "发送成功", sent_ids
    except Exception as e:
        logging.error(f"❌ ({session_name}) Telegram 客户端操作失败: {e}")
        return False, f"Telegram 客户端操作失败: {e}", []
    finally:
        if client.is_connected():
            await client.disconnect()


async def get_group_ids_and_names(session_name):
    session_file = os.path.join("session", f"{session_name}.session")
    client = TelegramClient(session_file, API_ID, API_HASH)
    try:
        await client.start()
        dialogs = await client.get_dialogs()
        group_data = [(d.id, d.title) for d in dialogs if d.is_group or d.is_channel]
        logging.info(f"✅ ({session_name}) 成功获取 {len(group_data)} 个群组/频道")
        return group_data, None
    except errors.SessionPasswordNeededError:
        error_msg = f"账号 '{session_name}' 需要两步验证密码"
        logging.error(f"❌ {error_msg}")
        return None, error_msg
    except Exception as e:
        error_msg = f"获取群组列表失败: {e}"
        logging.error(f"❌ ({session_name}) {error_msg}")
        return None, error_msg
    finally:
        if client.is_connected():
            await client.disconnect()


# ==== 5. GUI 窗口类 ====
class LoginWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择或添加 Telegram 账号")
        self.setMinimumSize(350, 300)
        self.selected_session = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("请选择一个已保存的账号:"))
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        button_layout = QHBoxLayout()
        self.login_button = QPushButton("✅ 登录选中账号")
        self.add_button = QPushButton("➕ 添加新账号")
        button_layout.addWidget(self.login_button)
        button_layout.addWidget(self.add_button)
        layout.addLayout(button_layout)

        self.login_button.clicked.connect(self.on_login)
        self.add_button.clicked.connect(self.on_add)
        self.list_widget.itemDoubleClicked.connect(self.on_login)

        self.accounts = [os.path.splitext(os.path.basename(f))[0] for f in glob("session/*.session")]
        if not self.accounts:
            self.list_widget.addItem("未检测到任何账号")
            self.list_widget.setEnabled(False)
            self.login_button.setEnabled(False)
        else:
            self.list_widget.addItems(self.accounts)

    def on_login(self):
        current_item = self.list_widget.currentItem()
        if current_item:
            self.selected_session = current_item.text()
            self.accept()

    def on_add(self):
        # **关键修复：在接受前先隐藏自己**
        self.hide()
        self.selected_session = "__add_new__"
        self.accept()


class LoadingDialog(QDialog):
    """一个自定义的、无按钮的、纯文本的加载提示弹窗"""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setModal(True)  # 设置为模态对话框，阻止与其他窗口交互
        self.setStyleSheet("""
            QDialog {
                background-color: #f0f0f0;
                border: 1px solid #ababab;
                border-radius: 5px;
            }
        """)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)

        self.label = QLabel("正在处理，请稍候...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("font-size: 14px;")

        self.layout.addWidget(self.label)

    def show_message(self, message):
        """显示加载窗口并设置文本"""
        self.label.setText(message)
        # 调整窗口大小以适应文本
        self.adjustSize()
        self.show()
        QApplication.processEvents()

    def close_dialog(self):
        """关闭加载窗口"""
        self.close()
        QApplication.processEvents()

class ControlPanel(QWidget):
    def __init__(self, session_name, app_callbacks):
        super().__init__()
        self.session_name = session_name
        self.callbacks = app_callbacks

        if session_name not in config["accounts"]:
            config["accounts"][session_name] = DEFAULT_ACCOUNT_CONFIG.copy()
        self.account_config = config["accounts"][session_name]

        self.setWindowTitle(f"Telegram 群发控制器 - [{self.session_name}] 🚀")
        self.resize(config.get("window_width"), config.get("window_height"))

        self.group_data = []
        self.fetched_group_info = []
        self.loading_msg = None
        self.selected_display = None

        self.init_ui()
        self.load_target_chats_to_listbox()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        groups_grid = QGridLayout()
        groups_grid.setContentsMargins(0, 0, 0, 0)
        groups_label = QLabel("📋 群组/频道")
        if os.path.exists("groups.png"):
            groups_label.setIcon(QIcon("groups.png"))
        groups_grid.addWidget(groups_label, 0, 0, 1, 3)
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("按群聊名称搜索")
        self.search_entry.returnPressed.connect(self.update_listbox)
        groups_grid.addWidget(self.search_entry, 1, 0)
        search_button = QPushButton("🔍 搜索")
        search_button.clicked.connect(self.update_listbox)
        groups_grid.addWidget(search_button, 1, 1)
        reset_button = QPushButton("🔄 重置")
        reset_button.clicked.connect(self.reset_search)
        groups_grid.addWidget(reset_button, 1, 2)
        groups_grid.setColumnStretch(0, 1)
        action_button_layout = QHBoxLayout()
        get_groups_button = QPushButton("🔄 获取所有群组")
        get_groups_button.clicked.connect(self.on_get_groups_requested)
        action_button_layout.addWidget(get_groups_button)
        remove_chat_button = QPushButton("🗑️ 移除已保存群")
        remove_chat_button.clicked.connect(self.remove_chat)
        action_button_layout.addWidget(remove_chat_button)
        groups_grid.addLayout(action_button_layout, 2, 0, 1, 3)
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.list_widget.itemSelectionChanged.connect(self.update_selected_from_list)
        groups_grid.addWidget(self.list_widget, 3, 0, 1, 3)
        main_layout.addLayout(groups_grid)
        bottom_layout = QGridLayout()
        msg_label = QLabel("💬 群发消息")
        self.msg_entry = QTextEdit(self.account_config.get("message_text", ""))
        bottom_layout.addWidget(msg_label, 0, 0)
        bottom_layout.addWidget(self.msg_entry, 1, 0)
        schedule_label = QLabel("⚙️ 定时发送")
        if os.path.exists("schedule.png"):
            schedule_label.setIcon(QIcon("schedule.png"))
        bottom_layout.addWidget(schedule_label, 0, 1)
        bottom_layout.setAlignment(schedule_label, Qt.AlignmentFlag.AlignTop)
        settings_container = QWidget()
        settings_layout = QVBoxLayout(settings_container)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(10)
        self.selected_display = QTextEdit()
        self.selected_display.setReadOnly(True)
        self.selected_display.setStyleSheet("background-color: #f0f0f0;")
        settings_layout.addWidget(self.selected_display)
        time_layout = QGridLayout()
        time_layout.addWidget(QLabel("24小时格式(HH:MM):"), 0, 0)
        self.time_entry = QLineEdit(f"{self.account_config.get('send_hour', 10):02d}:{self.account_config.get('send_minute', 0):02d}")
        self.time_entry.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_layout.addWidget(self.time_entry, 0, 1)
        save_button = QPushButton("💾 保存配置")
        save_button.clicked.connect(self.save_changes)
        time_layout.addWidget(save_button, 1, 0, 1, 2)
        settings_layout.addLayout(time_layout)
        settings_layout.setStretch(0, 1)
        bottom_layout.addWidget(settings_container, 1, 1)
        bottom_layout.setColumnStretch(0, 2)
        bottom_layout.setColumnStretch(1, 1)
        main_layout.addLayout(bottom_layout)
        send_now_button = QPushButton("🚀 立即发送")
        send_now_button.setStyleSheet("font-size: 16px; font-weight: bold; padding: 5px;")
        send_now_button.clicked.connect(self.on_send_now_requested)
        main_layout.addWidget(send_now_button)

    def closeEvent(self, event):
        self.update_selected_from_list()
        save_config()
        self.callbacks['on_close']()
        super().closeEvent(event)

    def load_target_chats_to_listbox(self):
        self.group_data = []
        for cid_str, cname in self.account_config.get("target_chats", {}).items():
            self.group_data.append((int(cid_str), cname, "(已保存)"))
        self.update_listbox()
        self.update_selected_from_list()

    def update_listbox(self):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        conf_ids = {int(k) for k in self.account_config.get("target_chats", {}).keys()}
        query = self.search_entry.text().lower().strip()
        display_data = [g for g in self.group_data if query in g[1].lower()] if query else self.group_data
        for cid, cname, tag in display_data:
            item = QListWidgetItem(f"{cid:<15} {cname:<20} {tag}")
            item.setData(Qt.ItemDataRole.UserRole, cid)
            self.list_widget.addItem(item)
            if cid in conf_ids:
                item.setSelected(True)
        self.list_widget.blockSignals(False)

    def reset_search(self):
        self.search_entry.clear()
        self.update_listbox()

    def update_selected_from_list(self):
        target_chats = {}
        for item in self.list_widget.selectedItems():
            cid = item.data(Qt.ItemDataRole.UserRole)
            name = next((n for item_id, n, t in self.group_data if item_id == cid), "未知")
            target_chats[str(cid)] = name
        self.account_config["target_chats"] = target_chats
        if self.selected_display:
            display_text = "\n".join(target_chats.values()) if target_chats else "尚未选择任何群组"
            self.selected_display.setText(display_text)

    def on_get_groups_requested(self):
        self.show_loading_message("🔄 正在获取群组列表")
        self.callbacks['get_groups']()

    def on_send_now_requested(self):
        self.update_selected_from_list()
        ids = [int(k) for k in self.account_config["target_chats"].keys()]
        text = self.msg_entry.toPlainText().strip()
        if not ids: QMessageBox.warning(self, "警告", "请选择至少一个群组!"); return
        if not text: QMessageBox.warning(self, "警告", "消息内容不能为空！"); return
        self.show_loading_message("🚀 正在立即发送消息")
        self.callbacks['send_now'](ids, text)

    def handle_get_groups_result(self, groups, error):
        self.hide_loading_message()
        if error: QMessageBox.critical(self, "错误", error); return
        self.fetched_group_info = groups
        conf_ids = {int(k) for k in self.account_config.get("target_chats", {}).keys()}
        new_data = []
        for cid, cname in self.fetched_group_info:
            new_data.append((cid, cname, "(已保存)" if cid in conf_ids else "(新发现)"))
        self.group_data = sorted(new_data, key=lambda x: (x[2] != "(已保存)", x[1]))
        self.update_listbox()
        QMessageBox.information(self, "完成", f"已获取 {len(self.fetched_group_info)} 个群组/频道")

    def handle_send_now_result(self, success, message, sent_ids):
        self.hide_loading_message()
        if success:
            QMessageBox.information(self, "发送完成", message)

            new_target_chats = {}

            for i, (cid, name, tag) in enumerate(self.group_data):
                if cid in sent_ids:
                    if tag != "(已保存)":
                        self.group_data[i] = (cid, name, "(已保存)")
                    new_target_chats[str(cid)] = name

            self.account_config["target_chats"] = new_target_chats
            self.group_data.sort(key=lambda x: (x[2] != "(已保存)", x[1]))
            self.update_listbox()
            self.update_selected_from_list()
            save_config()
        else:
            QMessageBox.critical(self, "发送失败", message)

    def remove_chat(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items: QMessageBox.warning(self, "警告", "请在列表中选择要移除的群组"); return
        ids_to_remove = {item.data(Qt.ItemDataRole.UserRole) for item in selected_items}
        for cid in ids_to_remove:
            self.account_config["target_chats"].pop(str(cid), None)
        updated_group_data = []
        for cid, name, tag in self.group_data:
            if cid in ids_to_remove:
                original_name = next((n for fetched_id, n in self.fetched_group_info if fetched_id == cid), None)
                if original_name:
                    updated_group_data.append((cid, original_name, "(新发现)"))
            else:
                updated_group_data.append((cid, name, tag))
        self.group_data = sorted(updated_group_data, key=lambda x: (x[2] != "(已保存)", x[1]))
        self.update_listbox()
        self.update_selected_from_list()
        save_config()
        QMessageBox.information(self, "成功", "已将选中的群组从“已保存”中移除")

    def save_changes(self):
        self.update_selected_from_list()
        self.account_config["message_text"] = self.msg_entry.toPlainText().strip()
        try:
            h, m = map(int, self.time_entry.text().strip().split(":"))
            if 0 <= h <= 23 and 0 <= m <= 59:
                self.account_config["send_hour"], self.account_config["send_minute"] = h, m
                save_config()
                self.callbacks['update_schedule'](self.session_name)
                QMessageBox.information(self, "成功", "所有配置已保存，定时任务已更新")
            else:
                QMessageBox.critical(self, "错误", "时间格式不正确")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败: {e}")

    def show_loading_message(self, text):
        if not self.loading_msg:
            self.loading_msg = QMessageBox(self)
            self.loading_msg.setWindowTitle("请稍候")
            self.loading_msg.setStandardButtons(QMessageBox.StandardButton.NoButton)
        self.loading_msg.setText(text)
        self.loading_msg.show()
        QApplication.processEvents()

    def hide_loading_message(self):
        if self.loading_msg:
            self.loading_msg.hide()


# ==== 6. 主应用类，管理流程 ====
class App:
    def __init__(self, loop):
        self.loop = loop
        self.current_panel = None
        self.scheduler = AsyncIOScheduler(event_loop=self.loop)
        self.scheduler.start()
        logging.info("🕒 后台定时任务调度器已启动")

    async def start(self):
        load_config()
        while True:
            session_name = self.show_login_window()
            if not session_name: break
            if session_name == '__add_new__':
                await self.add_new_account_flow()
                continue
            await self.run_control_panel(session_name)
            logging.info(f"账号 '{session_name}' 已退出返回账号选择菜单")

        self.scheduler.shutdown()
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
        if not re.match("^[a-zA-Z0-9_]+$", session_name): QMessageBox.critical(None, "错误", "别名不合法"); return
        if os.path.exists(f"session/{session_name}.session"): QMessageBox.critical(None, "错误", "该别名已存在"); return

        phone, ok = QInputDialog.getText(None, f"第2步：输入手机号 ({session_name})", "请输入手机号码(+869121037658):")
        if not ok or not phone: return
        os.makedirs("session", exist_ok=True)

        session_file = os.path.join("session", f"{session_name}.session")
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
            QMessageBox.information(None, "成功", f"账号 '{session_name}' 登录成功！\n\n请在您的Telegram设备上确认本人操作")

        except InterruptedError as e:
            loading_dialog.close_dialog()
            logging.warning(f"❌ 登录被用户取消: {e}")
            # 用户取消，不需要弹窗报错，静默处理
        except Exception as e:
            loading_dialog.close_dialog()
            logging.error(f"❌ 登录流程失败: {e}")
            QMessageBox.critical(None, "验证失败", f"登录流程失败: {e}")

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
        closed_future = self.loop.create_future()
        callbacks = {
            'on_close'       : lambda: not closed_future.done() and closed_future.set_result(True),
            'get_groups'     : lambda: self.loop.create_task(self.get_groups_task(session_name)),
            'send_now'       : lambda ids, text: self.loop.create_task(self.send_now_task(session_name, ids, text)),
            'update_schedule': lambda s_name: self.loop.create_task(self.update_schedule_task(s_name))
        }
        self.current_panel = ControlPanel(session_name, callbacks)
        await self.update_schedule_task(session_name)
        self.current_panel.show()
        await closed_future

    async def get_groups_task(self, session_name):
        groups, error = await get_group_ids_and_names(session_name)
        if self.current_panel:
            self.current_panel.handle_get_groups_result(groups, error)

    async def send_now_task(self, session_name, ids, text):
        success, message, sent_ids = await send_message_to_chats(session_name, ids, text)
        if self.current_panel:
            self.current_panel.handle_send_now_result(success, message, sent_ids)

    async def update_schedule_task(self, session_name):
        account_config = config["accounts"].get(session_name, DEFAULT_ACCOUNT_CONFIG)
        target_ids = [int(k) for k in account_config.get("target_chats", {}).keys()]
        job_id = f"daily_send_{session_name}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        if target_ids:
            async def scheduled_send_wrapper():
                await send_message_to_chats(session_name, target_ids, account_config["message_text"])

            self.scheduler.add_job(
                scheduled_send_wrapper, "cron",
                hour=account_config["send_hour"],
                minute=account_config["send_minute"],
                id=job_id
            )
            logging.info(f"🕒 ({session_name}) 定时任务已更新为 {account_config['send_hour']}:{account_config['send_minute']:02d}")
        else:
            logging.info(f"🕒 ({session_name}) 没有发送目标，定时任务未设置")


# ==== 7. 程序入口 (最终稳定版) ====
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    style = app.style()
    icon = style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
    app.setWindowIcon(icon)

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