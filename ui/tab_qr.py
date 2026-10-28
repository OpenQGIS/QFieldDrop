# -*- coding: utf-8 -*-
"""
QField LAN Drop - Tab 1: QR Code & Deep Link Direct Scan (Simplified)
Generates QField deep link (qfield://) QR code with progressive disclosure of advanced settings.
Native QGIS Desktop UI style.
"""

import urllib.parse
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QRadioButton, QPushButton, QApplication, QGroupBox, QButtonGroup, QMessageBox
)
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.gui import QgsCollapsibleGroupBox

from ..core.net_server import NetworkHelper
from ..core.qr_native import generate_qr_matrix, render_qr_to_qpixmap
from .icon_helper import get_icon, get_icon_path

ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter if hasattr(Qt, 'AlignmentFlag') else Qt.AlignCenter


class QrDropTab(QWidget):
    ip_changed = pyqtSignal(str)

    def __init__(self, port: int, zip_filename: str, parent=None):
        super().__init__(parent)
        self.port = port
        self.zip_filename = zip_filename
        self.current_http_url = ""
        self.current_deeplink_url = ""

        self._init_ui()
        self._update_urls_and_qr()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)

        # 1. Main QR Code GroupBox (Two-Column Layout)
        qr_group = QGroupBox("手机扫码快速导入工程")
        qr_layout = QHBoxLayout(qr_group)
        qr_layout.setContentsMargins(10, 10, 10, 10)
        qr_layout.setSpacing(14)

        # Left Column: QR Code (compact, tight quiet zone)
        self.qr_label = QLabel()
        self.qr_label.setFixedSize(160, 160)
        self.qr_label.setAlignment(ALIGN_CENTER)
        self.qr_label.setStyleSheet("background-color: #FFFFFF; border: 1px solid palette(mid); border-radius: 4px;")
        qr_layout.addWidget(self.qr_label, 0, Qt.AlignVCenter)

        # Right Column: Mode options + Instructions + Actions
        right_col = QVBoxLayout()
        right_col.setSpacing(8)
        right_col.setAlignment(Qt.AlignVCenter)

        self.btn_group = QButtonGroup(self)
        self.rb_deeplink = QRadioButton("系统相机直达唤醒 (推荐)")
        self.rb_deeplink.setChecked(True)
        self.rb_deeplink.setToolTip("手机自带系统相机直接扫码，自动唤醒 QField 并弹出工程导入对话框")

        self.rb_http = QRadioButton("扫码下载 ZIP 导入 (备用)")
        self.rb_http.setToolTip("手机自带相机或浏览器扫码极速下载 ZIP，在 QField 点【➕】选择【从 ZIP 导入工程】")

        self.btn_group.addButton(self.rb_deeplink)
        self.btn_group.addButton(self.rb_http)
        self.rb_deeplink.toggled.connect(self._update_urls_and_qr)
        self.rb_http.toggled.connect(self._update_urls_and_qr)

        right_col.addWidget(self.rb_deeplink)
        right_col.addWidget(self.rb_http)

        self.scan_tip = QLabel("提示：使用手机自带相机扫码，直接唤醒 QField 并弹出导入确认")
        self.scan_tip.setWordWrap(True)
        tip_font = self.scan_tip.font()
        tip_font.setPointSize(max(8, tip_font.pointSize() - 1))
        self.scan_tip.setFont(tip_font)
        right_col.addWidget(self.scan_tip)

        act_row = QHBoxLayout()
        act_row.setSpacing(8)

        btn_copy_link = QPushButton("复制链接")
        btn_copy_link.setIcon(get_icon("link"))
        btn_copy_link.clicked.connect(self._copy_link_auto)
        act_row.addWidget(btn_copy_link)

        btn_browser = QPushButton("测试下载")
        btn_browser.setIcon(get_icon("globe"))
        btn_browser.setToolTip("在默认浏览器中测试下载此工程包")
        btn_browser.clicked.connect(self._open_in_browser)
        act_row.addWidget(btn_browser)

        right_col.addLayout(act_row)
        qr_layout.addLayout(right_col, 1)

        layout.addWidget(qr_group)

        # 2. Network Adapter & LAN Configuration GroupBox
        net_group = QGroupBox("局域网与网卡配置")
        net_layout = QVBoxLayout(net_group)
        net_layout.setSpacing(6)
        net_layout.setContentsMargins(10, 8, 10, 8)

        # IP Selector Row
        ip_row = QHBoxLayout()
        ip_row.addWidget(QLabel("投送网卡:"))
        self.ip_combo = QComboBox()
        self.ip_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        for item in NetworkHelper.get_all_lan_ips():
            self.ip_combo.addItem(item['label'], item['ip'])
        self.ip_combo.currentIndexChanged.connect(self._on_ip_combo_changed)
        ip_row.addWidget(self.ip_combo, 1)

        btn_firewall = QPushButton("防火墙配置")
        btn_firewall.setIcon(get_icon("shield"))
        btn_firewall.setToolTip("复制 Windows 高级防火墙端口放行命令")
        btn_firewall.clicked.connect(self._copy_firewall_cmd)
        ip_row.addWidget(btn_firewall)
        net_layout.addLayout(ip_row)

        self.mdns_lbl = QLabel(f"局域网通用地址: <code>http://qgis-drop.local:{self.port}/project.zip</code>")
        self.mdns_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        tip_f = self.mdns_lbl.font()
        tip_f.setPointSize(max(8, tip_f.pointSize() - 1))
        self.mdns_lbl.setFont(tip_f)
        net_layout.addWidget(self.mdns_lbl)

        layout.addWidget(net_group)

    def _open_in_browser(self):
        import webbrowser
        if self.current_http_url:
            webbrowser.open(self.current_http_url)

    def get_selected_ip(self) -> str:
        ip = self.ip_combo.currentData()
        if not ip:
            ip = self.ip_combo.currentText().split(' ')[0]
        return ip or "127.0.0.1"

    def _on_ip_combo_changed(self):
        ip = self.get_selected_ip()
        self.ip_changed.emit(ip)
        self._update_urls_and_qr()

    def update_port_and_file(self, port: int, zip_filename: str):
        self.port = port
        self.zip_filename = zip_filename
        if hasattr(self, 'mdns_lbl'):
            self.mdns_lbl.setText(f"局域网通用域名: <code>http://qgis-drop.local:{self.port}/project.zip</code>")
        self._update_urls_and_qr()

    def _update_urls_and_qr(self):
        ip = self.get_selected_ip()
        filename = self.zip_filename or "project.zip"
        encoded_filename = urllib.parse.quote(filename)
        self.current_http_url = f"http://{ip}:{self.port}/{encoded_filename}"

        # Official QField Deep Link specification:
        # qfield://local?import={url}
        self.current_deeplink_url = f"qfield://local?import={self.current_http_url}"

        use_deeplink = self.rb_deeplink.isChecked()
        active_url = self.current_deeplink_url if use_deeplink else self.current_http_url

        if use_deeplink:
            self.scan_tip.setText("提示：使用手机自带相机扫码，直接唤醒 QField 并弹出导入确认")
        else:
            self.scan_tip.setText("提示：扫码下载 ZIP 压缩包 ➔ 打开 QField ➔ 点击右下角【➕】➔ 选择【从 ZIP 导入工程】")

        matrix = generate_qr_matrix(active_url, ecc='Q')
        icon_path = get_icon_path("DropOut")
        pixmap = render_qr_to_qpixmap(matrix, target_size=160, margin_px=6, icon_path=icon_path)
        if pixmap:
            self.qr_label.setPixmap(pixmap)

    def _copy_link_auto(self):
        url = self.current_deeplink_url if self.rb_deeplink.isChecked() else self.current_http_url
        QApplication.clipboard().setText(url)
        name = "相机直接唤醒链接 (qfield://)" if self.rb_deeplink.isChecked() else "标准下载链接 (HTTP)"
        QMessageBox.information(
            self,
            "复制成功",
            f"{name} 已复制至剪贴板：\n\n{url}\n\n可直接通过聊天软件发送至手机。"
        )

    def _copy_firewall_cmd(self):
        cmd = f'netsh advfirewall firewall add rule name="QField LAN Drop" dir=in action=allow protocol=TCP localport={self.port}'
        QApplication.clipboard().setText(cmd)
        QMessageBox.information(
            self,
            "已复制防火墙规则",
            f"若手机因电脑防火墙拦截无法访问，请以管理员身份打开 PowerShell 运行以下命令：\n\n{cmd}\n\n已自动复制至剪贴板。"
        )
