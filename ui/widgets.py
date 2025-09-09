import os
from enum import Enum

from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QDialog, QStyle)
from PyQt6.QtCore import Qt, QSize, QByteArray
from PyQt6.QtGui import QIcon, QRegion, QPainterPath, QPixmap

from utils.helpers import resource_path


class LoadingDialog(QDialog):
    """一个自定义的、无按钮的、纯文本的加载提示弹窗"""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setModal(True)  # 设置为模态对话框，阻止与其他窗口交互
        self.setStyleSheet("""
            QDialog {
                background-color: #f0f0f0;
                border: 1px solid #ababab;
                border-radius: 8px;
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

    def resizeEvent(self, event):
        """当窗口大小改变时，自动更新窗口的圆角遮罩"""
        super().resizeEvent(event)

        border_radius = 8  # 应与你的CSS值匹配

        # 创建一个 QPainterPath 对象来定义圆角矩形的形状
        path = QPainterPath()

        # 使用 path 是最精确可靠的方法
        path.addRoundedRect(0, 0, self.width(), self.height(), border_radius, border_radius)

        # 将这个 path 转换成一个 QRegion (区域)
        mask = QRegion(path.toFillPolygon().toPolygon())

        # 将这个区域设置为窗口的遮罩
        self.setMask(mask)


class ResultDialog(QDialog):
    """一个自定义的、带图标和按钮的、用于替代 QMessageBox 的结果提示弹窗。"""

    # 使用枚举来定义对话框的类型，让代码更清晰
    class ResultType(Enum):
        SUCCESS = 1
        ERROR = 2
        WARNING = 3

    def __init__(self, dialog_type: ResultType, title: str, message: str, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setModal(True)

        self.setMaximumWidth(320)

        # ---- 1. 样式和圆角遮罩 (与 LoadingDialog 完全相同) ----
        self.setStyleSheet("""
            QDialog {
                background-color: #f0f0f0;
                border: 2px solid #ababab; /* 边框可以稍粗一点更有质感 */
                border-radius: 8px;
            }
        """)
        self.border_radius = 8

        # ---- 2. 构建UI布局 ----
        # 整体垂直布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 20, 25, 15)
        main_layout.setSpacing(10)

        # 顶部区域：图标 + 标题 (水平布局)
        top_layout = QHBoxLayout()
        top_layout.setSpacing(15)

        # -- 图标 --
        icon_label = QLabel()
        style = self.style()
        icon_size = 32  # 图标大小

        if dialog_type == self.ResultType.SUCCESS:
            icon_path = resource_path(os.path.join("icons", "success.svg"))
            color_hex = "#5cb85c"
            fallback_icon = QStyle.StandardPixmap.SP_DialogApplyButton
        elif dialog_type == self.ResultType.ERROR:
            icon_path = resource_path(os.path.join("icons", "error.svg"))
            color_hex = "#d9534f"
            fallback_icon = style.standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical)
        else:  # WARNING
            icon_path = resource_path(os.path.join("icons", "warning.svg"))
            color_hex = "#f0ad4e"
            fallback_icon = QStyle.StandardPixmap.SP_MessageBoxWarning

        # 优先使用我们漂亮的SVG图标
        if os.path.exists(icon_path):
            try:
                # 读取SVG文件内容
                with open(icon_path, 'r', encoding='utf-8') as f:
                    svg_data = f.read()
                # 直接将颜色注入SVG数据
                colored_svg_data = svg_data.replace('stroke="currentColor"', f'stroke="{color_hex}"')

                # 从修改后的SVG数据加载图标
                icon_byte_array = QByteArray(colored_svg_data.encode('utf-8'))
                pixmap = QPixmap()
                pixmap.loadFromData(icon_byte_array)
                icon = QIcon(pixmap)
            except Exception:
                icon = style.standardIcon(fallback_icon)
        else:  # 如果SVG文件不存在，则回退到系统图标
            icon = style.standardIcon(fallback_icon)

        # 设置图标颜色
        icon_label.setStyleSheet(f"color: {color_hex};")
        # 渲染并设置pixmap
        pixmap = icon.pixmap(QSize(icon_size, icon_size))
        icon_label.setPixmap(pixmap)
        top_layout.addWidget(icon_label)

        # -- 标题 --
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        top_layout.addWidget(title_label, 1)  # 自动伸展

        main_layout.addLayout(top_layout)

        # -- 消息文本 --
        self.message_label = QLabel(message)
        self.message_label.setStyleSheet("font-size: 14px;")
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.message_label)

        # -- 确定按钮 --
        self.ok_button = QPushButton("确定")
        self.ok_button.setMinimumHeight(30)
        self.ok_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ok_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                background-color: #0275d8;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px 20px;
            }
            QPushButton:hover {
                background-color: #025aa5;
            }
            QPushButton:pressed {
                background-color: #014682;
            }
        """)
        self.ok_button.clicked.connect(self.accept)  # 点击按钮=关闭对话框

        # 让按钮靠右对齐
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        button_layout.addWidget(self.ok_button)
        button_layout.addStretch(1)
        main_layout.addLayout(button_layout)

    # ---- 3. 圆角遮罩方法 (与 LoadingDialog 完全相同) ----
    def resizeEvent(self, event):
        super().resizeEvent(event)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), self.border_radius, self.border_radius)
        mask = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(mask)

    # ---- 4. (推荐) 添加一个静态方法，让调用更简单！ ----
    @staticmethod
    def show_message(parent: QWidget | None, dialog_type: "ResultDialog.ResultType", title: str, message: str):
        """静态方法，用于像 QMessageBox一样方便地显示对话框"""
        dialog = ResultDialog(dialog_type, title, message, parent)
        dialog.adjustSize()
        # 将对话框居中于父窗口
        if parent:
            parent_rect = parent.geometry()
            dialog.move(parent_rect.center() - dialog.rect().center())
        else:
            screen_geometry = QApplication.primaryScreen().geometry()
            dialog.move(screen_geometry.center() - dialog.rect().center())

        return dialog.exec()
