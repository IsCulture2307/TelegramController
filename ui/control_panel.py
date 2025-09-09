import os

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget,QPushButton,
                             QLabel, QTextEdit, QLineEdit, QGridLayout,QListWidgetItem)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from ui.widgets import ResultDialog, LoadingDialog
from utils.config import config, save_config

class ControlPanel(QWidget):
    def __init__(self, session_name, account_config, app_callbacks):
        super().__init__()
        self.session_name = session_name
        self.callbacks = app_callbacks

        self.account_config = account_config

        self.setWindowTitle(f"Telegram 群发控制器 - [{self.session_name}] 🚀")
        self.resize(config.get("window_width"), config.get("window_height"))

        self.group_data = []
        self.fetched_group_info = []
        self.loading_msg = None
        self.selected_display = None

        self.init_ui()
        self.load_target_chats_to_listbox()
        self.loading_dialog = LoadingDialog(self)

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
        if not ids: ResultDialog.show_message(self, ResultDialog.ResultType.WARNING, "警告", "请选择至少一个群组!"); return
        if not text: ResultDialog.show_message(self, ResultDialog.ResultType.WARNING, "警告", "消息内容不能为空！"); return
        self.show_loading_message("🚀 正在立即发送消息")
        self.callbacks['send_now'](ids, text)

    def handle_get_groups_result(self, groups, error):
        self.hide_loading_message()
        if error: ResultDialog.show_message(self, ResultDialog.ResultType.ERROR, "错误", error); return
        self.fetched_group_info = groups
        conf_ids = {int(k) for k in self.account_config.get("target_chats", {}).keys()}
        new_data = []
        for cid, cname in self.fetched_group_info:
            new_data.append((cid, cname, "(已保存)" if cid in conf_ids else "(新发现)"))
        self.group_data = sorted(new_data, key=lambda x: (x[2] != "(已保存)", x[1]))
        self.update_listbox()
        ResultDialog.show_message(self, ResultDialog.ResultType.SUCCESS, "获取成功", f"已获取 {len(self.fetched_group_info)} 个群组/频道")

    def handle_send_now_result(self, success, message, sent_ids):
        self.hide_loading_message()
        if success:
            ResultDialog.show_message(self, ResultDialog.ResultType.SUCCESS, "发送完成", message)

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
            ResultDialog.show_message(self, ResultDialog.ResultType.ERROR, "发送失败", message)

    def remove_chat(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items: ResultDialog.show_message(self, ResultDialog.ResultType.ERROR, "移除失败","请在列表中选择要移除的群组"); return
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
        ResultDialog.show_message(self, ResultDialog.ResultType.SUCCESS, "移除成功","已将选中的群组从“已保存”中移除")

    def save_changes(self):
        self.update_selected_from_list()
        self.account_config["message_text"] = self.msg_entry.toPlainText().strip()
        try:
            h, m = map(int, self.time_entry.text().strip().split(":"))
            if 0 <= h <= 23 and 0 <= m <= 59:
                self.account_config["send_hour"], self.account_config["send_minute"] = h, m
                save_config()
                self.callbacks['update_schedule'](self.session_name)
                ResultDialog.show_message(self, ResultDialog.ResultType.SUCCESS, "保存成功","所有配置已保存，定时任务已更新")
            else:
                ResultDialog.show_message(self, ResultDialog.ResultType.ERROR, "错误", "时间格式不正确")
        except Exception as e:
            ResultDialog.show_message(self, ResultDialog.ResultType.ERROR, "错误", f"保存配置失败: {e}")

    def show_loading_message(self, text):
        self.loading_dialog.show_message(text)

    def hide_loading_message(self):
        self.loading_dialog.close_dialog()