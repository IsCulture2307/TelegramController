import logging
import os

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
                             QLabel, QTextEdit, QLineEdit, QGridLayout, QListWidgetItem, QCheckBox)
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
        action_button_layout.setContentsMargins(5, 0, 0, 0)
        self.select_all_checkbox = QCheckBox("全选/全不选")
        self.select_all_checkbox.setStyleSheet("QCheckBox { font-weight: bold; color: #005a9e; padding: 2px; }")
        self.select_all_checkbox.stateChanged.connect(self.on_select_all_changed)
        action_button_layout.addWidget(self.select_all_checkbox, 0)

        get_groups_button = QPushButton("🔄 获取所有群组")
        get_groups_button.clicked.connect(self.on_get_groups_requested)
        action_button_layout.addWidget(get_groups_button, 1)

        remove_chat_button = QPushButton("🗑️ 移除已保存群")
        remove_chat_button.clicked.connect(self.remove_chat)
        action_button_layout.addWidget(remove_chat_button, 1)
        groups_grid.addLayout(action_button_layout, 2, 0, 1, 3)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
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
        save_config()
        self.callbacks['on_close']()
        super().closeEvent(event)

    def load_target_chats_to_listbox(self):
        self.group_data = []
        for cid_str, cname in self.account_config.get("target_chats", {}).items():
            self.group_data.append((int(cid_str), cname, "(已保存)"))
        self.update_listbox()
        self.update_selected_display()

    def update_selected_display(self):
        """根据当前的 account_config 更新右侧的已选择群组显示"""
        target_chats = self.account_config.get("target_chats", {})
        if self.selected_display:
            display_text = "\n".join(target_chats.values()) if target_chats else "尚未选择任何群组"
            self.selected_display.setText(display_text)

    def _update_select_all_checkbox_state(self):
        """一个私有的辅助函数，用于更新“全选”复选框的状态"""
        self.select_all_checkbox.stateChanged.disconnect()

        all_checked = True
        if self.list_widget.count() == 0:
            all_checked = False
        else:
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                widget = self.list_widget.itemWidget(item)
                if widget and not widget.findChild(QCheckBox).isChecked():
                    all_checked = False
                    break

        self.select_all_checkbox.setChecked(all_checked)
        self.select_all_checkbox.stateChanged.connect(self.on_select_all_changed)

    def on_select_all_changed(self, state):
        """当“全选/全不选”复选框状态改变时调用"""

        # 暂时断开单个复选框的信号连接，以防止雪崩式更新，提高性能
        # 这是一个重要的优化
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.stateChanged.disconnect()

        # 根据“全选”框的状态，设置列表中的每一个复选框
        is_checked = (state == Qt.CheckState.Checked.value)

        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(is_checked)

        # 更新底层的配置字典
        if is_checked:
            # 全选：将当前列表（包括搜索结果）中的所有群组添加到配置中
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                cid = item.data(Qt.ItemDataRole.UserRole)
                # 从 group_data 中找到名字
                name = next((n for item_id, n, t in self.group_data if item_id == cid), "未知")
                self.account_config["target_chats"][str(cid)] = name
        else:
            # 全不选：只清空当前可见的群组
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                cid = item.data(Qt.ItemDataRole.UserRole)
                if str(cid) in self.account_config["target_chats"]:
                    del self.account_config["target_chats"][str(cid)]

        # 重新连接所有信号
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                cid = item.data(Qt.ItemDataRole.UserRole)
                if checkbox:
                    checkbox.stateChanged.connect(
                        lambda s, c=cid, chk=checkbox: self.on_checkbox_changed(s, c, chk)
                    )
        self.update_selected_display()

    def update_listbox(self):
        self.list_widget.blockSignals(True)  # 开始操作前，阻止列表发出任何信号
        self.list_widget.clear()
        conf_ids = {int(k) for k in self.account_config.get("target_chats", {}).keys()}
        query = self.search_entry.text().lower().strip()
        display_data = [g for g in self.group_data if query in g[1].lower()] if query else self.group_data
        for cid, cname, tag in display_data:
            # 1. 创建一个 QListWidgetItem，它本身只是一个容器
            item = QListWidgetItem(self.list_widget)

            # 2. 创建一个自定义的 QWidget 作为 item 的内容
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(5, 5, 5, 5)  # 设置内边距

            # 3. 创建复选框
            checkbox = QCheckBox(f"{cname}")
            checkbox.setChecked(cid in conf_ids)
            # 使用 lambda 来捕获当前的 cid 和 checkbox 实例
            checkbox.stateChanged.connect(
                lambda state, c=cid, chk=checkbox: self.on_checkbox_changed(state, c, chk)
            )

            # 4. 创建一个标签来显示 ID 和 状态 (tag)
            info_label = QLabel(f"ID: {cid}  {tag}")
            info_label.setStyleSheet("color: #6c757d;")  # 用灰色显示，不那么显眼

            # 5. 将控件添加到布局中
            info_label.setMinimumWidth(220)

            info_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            layout.addWidget(checkbox)
            layout.addWidget(info_label)

            layout.setStretchFactor(checkbox, 1)
            layout.setStretchFactor(info_label, 0)

            widget.setLayout(layout)

            # 6. 设置 item 的大小提示，并把我们的 widget 放进去
            item.setSizeHint(widget.sizeHint())
            self.list_widget.setItemWidget(item, widget)

            # 7. (可选但推荐) 将 cid 存储在 item 的数据中，以备后用
            item.setData(Qt.ItemDataRole.UserRole, cid)
        # 在末尾更新“全选”框的状态
        if hasattr(self, 'select_all_checkbox'):
             self._update_select_all_checkbox_state()
        self.list_widget.blockSignals(False)

    def on_checkbox_changed(self, state, chat_id, checkbox):
        """当一个群组的复选框状态改变时调用"""
        chat_name = checkbox.text()  # 复选框的文本就是群组名

        if state == Qt.CheckState.Checked.value:
            # 如果被选中，就添加到配置中
            self.account_config["target_chats"][str(chat_id)] = chat_name
            logging.info(f"Added: {chat_id} - {chat_name}")
            new_tag = "(已保存)"
        else:
            # 如果被取消选中，就从配置中移除
            if str(chat_id) in self.account_config["target_chats"]:
                del self.account_config["target_chats"][str(chat_id)]
                logging.info(f"Removed: {chat_id}")
            new_tag = "(新发现)"
        # 1. 在 self.group_data 中找到匹配的项并更新其 tag
        for i, (cid, name, tag) in enumerate(self.group_data):
            if cid == chat_id:
                self.group_data[i] = (cid, name, new_tag)
                break  # 找到后即可退出循环

        # 2. 重新排序并刷新整个列表以显示状态变化
        self.group_data.sort(key=lambda x: (x[2] != "(已保存)", x[1]))
        self.update_listbox()
        # 实时更新右侧的已选择列表显示
        self.update_selected_display()

    def reset_search(self):
        self.search_entry.clear()
        self.update_listbox()

    def on_get_groups_requested(self):
        self.show_loading_message("🔄 正在获取群组列表")
        self.callbacks['get_groups']()

    def on_send_now_requested(self):
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

            # 更新UI中的 group_data，将新发送的群组标记为“(已保存)”
            ui_changed = False
            for i, (cid, name, tag) in enumerate(self.group_data):
                if cid in sent_ids and tag != "(已保存)":
                    self.group_data[i] = (cid, name, "(已保存)")
                    ui_changed = True

            # 更新 account_config["target_chats"]，将新发送的群组添加进去
            for sent_id in sent_ids:
                if str(sent_id) not in self.account_config["target_chats"]:
                    sent_name = next((n for item_id, n, t in self.group_data if item_id == sent_id), "未知群组")
                    self.account_config["target_chats"][str(sent_id)] = sent_name

            # 如果UI数据有变动，就重新排序和刷新列表
            if ui_changed:
                self.group_data.sort(key=lambda x: (x[2] != "(已保存)", x[1]))
                self.update_listbox()

            # 刷新右侧的显示
            self.update_selected_display()

            # 保存包含了所有已保存群组的完整配置
            save_config()
        else:
            ResultDialog.show_message(self, ResultDialog.ResultType.ERROR, "发送失败", message)

    def remove_chat(self):
        """新的逻辑：取消所有已勾选的群组，并正确更新UI状态"""

        if not self.account_config["target_chats"]:
            ResultDialog.show_message(self, ResultDialog.ResultType.WARNING, "提示", "当前没有勾选（即已保存）的群组可供移除。")
            return

        # 1. 获取所有需要被“移除”的群组ID
        ids_to_remove = set(int(k) for k in self.account_config["target_chats"].keys())

        # 2. 清空配置字典
        self.account_config["target_chats"].clear()

        # 3. 更新 self.group_data 中对应项的 tag
        for i, (cid, name, tag) in enumerate(self.group_data):
            if cid in ids_to_remove:
                self.group_data[i] = (cid, name, "(新发现)")

        # 4. 重新排序并刷新UI
        self.group_data.sort(key=lambda x: (x[2] != "(已保存)", x[1]))
        self.update_listbox()
        self.update_selected_display()

        # 5. 保存空的配置
        save_config()
        ResultDialog.show_message(self, ResultDialog.ResultType.SUCCESS, "操作成功", "所有已勾选的群组均已从“已保存”中移除。")

    def save_changes(self):
        self.account_config["message_text"] = self.msg_entry.toPlainText().strip()
        try:
            h, m = map(int, self.time_entry.text().strip().split(":"))
            if 0 <= h <= 23 and 0 <= m <= 59:
                self.account_config["send_hour"], self.account_config["send_minute"] = h, m
                save_config()
                self.callbacks['update_schedule'](self.session_name)
                ResultDialog.show_message(self, ResultDialog.ResultType.SUCCESS, "保存成功", "所有配置已保存，定时任务已更新")
            else:
                ResultDialog.show_message(self, ResultDialog.ResultType.ERROR, "错误", "时间格式不正确")
        except Exception as e:
            ResultDialog.show_message(self, ResultDialog.ResultType.ERROR, "错误", f"保存配置失败: {e}")

    def show_loading_message(self, text):
        self.loading_dialog.show_message(text)

    def hide_loading_message(self):
        self.loading_dialog.close_dialog()