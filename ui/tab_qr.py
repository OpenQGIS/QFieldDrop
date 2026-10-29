# -*- coding: utf-8 -*-
"""
QField LAN Drop - Tab: QR Camera Direct Wake-up (二维码直传)
Directly renders the DeepLink QR code (qfield://local?import=...) for native camera scanning.
Wakes up mobile QField automatically without manual file exploration.
Native QGIS Desktop UI style.
"""

from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QApplication, QMessageBox
)
from qgis.PyQt.QtCore import Qt

from ..core.qr_native import generate_qr_matrix, render_qr_to_qpixmap
from .icon_helper import get_icon, get_icon_path

ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter if hasattr(Qt, 'AlignmentFlag') else Qt.AlignCenter


class QrDropTab(QWidget):
    """Tab 1: Camera QR Direct Scan & QField DeepLink Wake-up."""

    def __init__(self, port: int, zip_filename: str, ip: str = "127.0.0.1", parent=None):
        super().__init__(parent)
        self.port = port
        self.zip_filename = zip_filename
        self.ip = ip
        self.current_http_url = ""
        self.current_deeplink_url = ""

        self._init_ui()
        self.update_port_and_file(port=self.port, zip_filename=self.zip_filename, ip=self.ip)

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(14)

        # Left Column: DeepLink QR Code
        self.qr_deeplink_lbl = QLabel()
        self.qr_deeplink_lbl.setFixedSize(145, 145)
        self.qr_deeplink_lbl.setAlignment(ALIGN_CENTER)
        self.qr_deeplink_lbl.setStyleSheet(
            "background-color: #FFFFFF; border: 1px solid palette(mid); border-radius: 4px;"
        )
        layout.addWidget(self.qr_deeplink_lbl, 0, Qt.AlignVCenter)

        # Right Column: Instructions & Action Button
        right_col = QVBoxLayout()
        right_col.setSpacing(8)
        right_col.setAlignment(Qt.AlignVCenter)

        lbl_desc = QLabel(
            "<div style='line-height: 145%;'>"
            "<b>手机系统相机直接扫码：</b><br>"
            "立即可自动唤醒手机 QField 并弹出工程导入确认，无需手动在文件管理器中查找。<br>"
            "<small style='color: #64748B;'>（外业极速导入首选推荐方式）</small>"
            "</div>"
        )
        lbl_desc.setWordWrap(True)
        right_col.addWidget(lbl_desc)

        btn_copy_dl = QPushButton("复制唤醒链接")
        btn_copy_dl.setIcon(get_icon("link"))
        btn_copy_dl.setToolTip("复制 qfield:// 深度唤醒链接，发至手机点击可直接唤醒 QField")
        btn_copy_dl.clicked.connect(self._copy_deeplink)
        right_col.addWidget(btn_copy_dl, 0, Qt.AlignLeft)

        lbl_tip = QLabel(
            "<small style='color: #94A3B8;'>ℹ️ 手机与电脑需连入同一 Wi-Fi 或热点。若相机不支持调起 App，可切换至【安装包下载】扫码。</small>"
        )
        lbl_tip.setWordWrap(True)
        right_col.addWidget(lbl_tip)

        layout.addLayout(right_col, 1)

    def set_ip(self, ip: str):
        self.ip = ip
        self._update_urls_and_qr()

    def update_port_and_file(self, port: int, zip_filename: str, ip: str = "127.0.0.1"):
        self.port = port
        self.zip_filename = zip_filename
        self.ip = ip
        self._update_urls_and_qr()

    def _update_urls_and_qr(self):
        self.current_http_url = f"http://{self.ip}:{self.port}/project.zip"
        self.current_deeplink_url = f"qfield://local?import={self.current_http_url}"

        m = generate_qr_matrix(self.current_deeplink_url, ecc='Q')
        pix = render_qr_to_qpixmap(m, target_size=140, margin_px=6, icon_path=get_icon_path("DropOut"))
        if pix:
            self.qr_deeplink_lbl.setPixmap(pix)

    def _copy_deeplink(self):
        QApplication.clipboard().setText(self.current_deeplink_url)
        QMessageBox.information(
            self, "复制成功",
            f"相机直接唤醒链接已复制至剪贴板：\n\n{self.current_deeplink_url}\n\n可直接通过聊天软件发送至手机。"
        )
