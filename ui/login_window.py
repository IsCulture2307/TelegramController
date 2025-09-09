import os
from glob import glob

from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QListWidget,
                             QPushButton, QLabel, QDialog)

from utils.helpers import app_path


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

        session_folder = app_path("session")
        self.accounts = [os.path.splitext(os.path.basename(f))[0] for f in glob(f"{session_folder}/*.session")]
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
