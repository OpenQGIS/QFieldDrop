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

from ..core.net_server import NetworkHelper
from ..core.qr_native import generate_qr_matrix, render_qr_to_qpixmap
from .icon_helper import get_icon

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
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # 1. Main Centerpiece: Clean QR Code Card
        qr_group = QGroupBox("手机扫码快速导入工程")
        qr_layout = QVBoxLayout(qr_group)
        qr_layout.setAlignment(ALIGN_CENTER)
        qr_layout.setContentsMargins(12, 12, 12, 12)

        self.qr_label = QLabel()
        self.qr_label.setFixedSize(220, 220)
        self.qr_label.setAlignment(ALIGN_CENTER)
        # High contrast white background for camera scanning
        self.qr_label.setStyleSheet("background-color: #FFFFFF; border: 1px solid #CCCCCC;")
        qr_layout.addWidget(self.qr_label, 0, ALIGN_CENTER)

        # Mode Selection Radio Buttons directly under QR
        mode_box = QHBoxLayout()
        mode_box.setAlignment(ALIGN_CENTER)
        self.btn_group = QButtonGroup(self)

        self.rb_http = QRadioButton("QField 内部扫码 / 浏览器 (推荐)")
        self.rb_http.setChecked(True)
        self.rb_http.setToolTip("标准 HTTP 地址：在 QField【从 URL 导入】点击扫码小图标，或手机浏览器扫码下载")

        self.rb_deeplink = QRadioButton("系统相机直达 (qfield://)")
        self.rb_deeplink.setToolTip("使用 qfield:// 协议：手机自带相机扫码直接唤醒 QField 应用")

        self.btn_group.addButton(self.rb_http)
        self.btn_group.addButton(self.rb_deeplink)
        self.rb_http.toggled.connect(self._update_urls_and_qr)
        self.rb_deeplink.toggled.connect(self._update_urls_and_qr)

        mode_box.addWidget(self.rb_http)
        mode_box.addSpacing(16)
        mode_box.addWidget(self.rb_deeplink)
        qr_layout.addLayout(mode_box)

        self.scan_tip = QLabel("提示：打开 QField ➔【从 URL 导入工程】➔ 点击输入框右侧 📷 扫码图标扫描")
        self.scan_tip.setAlignment(ALIGN_CENTER)
        self.scan_tip.setStyleSheet("color: #475569; font-size: 11px; margin-top: 4px;")
        qr_layout.addWidget(self.scan_tip)

        layout.addWidget(qr_group)

        # 2. Quick Action Bar
        act_row = QHBoxLayout()
        act_row.setAlignment(ALIGN_CENTER)

        btn_copy_link = QPushButton("复制直达链接")
        btn_copy_link.setIcon(get_icon("link"))
        btn_copy_link.clicked.connect(self._copy_link_auto)
        act_row.addWidget(btn_copy_link)

        self.btn_toggle_adv = QPushButton("▼ 高级网络选项")
        self.btn_toggle_adv.setCheckable(True)
        self.btn_toggle_adv.setChecked(False)
        self.btn_toggle_adv.toggled.connect(self._toggle_advanced)
        act_row.addWidget(self.btn_toggle_adv)

        layout.addLayout(act_row)

        # 3. Progressive Disclosure: Advanced Settings Box (Hidden by default)
        self.adv_group = QGroupBox("高级网络设置")
        adv_layout = QVBoxLayout(self.adv_group)

        # IP Selector Row
        ip_row = QHBoxLayout()
        ip_row.addWidget(QLabel("选择投送 IP:"))
        self.ip_combo = QComboBox()
        self.ip_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        for item in NetworkHelper.get_all_lan_ips():
            self.ip_combo.addItem(item['label'], item['ip'])
        self.ip_combo.currentIndexChanged.connect(self._on_ip_combo_changed)
        ip_row.addWidget(self.ip_combo, 1)

        btn_firewall = QPushButton("防火墙放行命令")
        btn_firewall.setIcon(get_icon("shield"))
        btn_firewall.clicked.connect(self._copy_firewall_cmd)
        ip_row.addWidget(btn_firewall)
        adv_layout.addLayout(ip_row)

        self.mdns_lbl = QLabel(f"局域网通用域名: <code>http://qgis-drop.local:{self.port}/project.zip</code>")
        adv_layout.addWidget(self.mdns_lbl)

        self.adv_group.hide()
        layout.addWidget(self.adv_group)

        layout.addStretch()

    def _toggle_advanced(self, checked: bool):
        self.adv_group.setVisible(checked)
        self.btn_toggle_adv.setText("▲ 收起高级选项" if checked else "▼ 高级网络选项")

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
        self.current_http_url = f"http://{ip}:{self.port}/project.zip"
        # Properly percent-encode the parameter for deep link
        encoded_import = urllib.parse.quote(self.current_http_url, safe='')
        self.current_deeplink_url = f"qfield://local?import={encoded_import}"

        if self.rb_http.isChecked():
            target = self.current_http_url
            if hasattr(self, 'scan_tip'):
                self.scan_tip.setText("提示：在 QField ➔【从 URL 导入工程】点击输入框右侧 📷 扫码图标扫描")
        else:
            target = self.current_deeplink_url
            if hasattr(self, 'scan_tip'):
                self.scan_tip.setText("提示：使用手机自带相机扫码，直接唤醒 QField 应用进行导入")

        matrix = generate_qr_matrix(target, ecc='M')
        pixmap = render_qr_to_qpixmap(matrix, target_size=210, border_modules=2)
        if pixmap:
            self.qr_label.setPixmap(pixmap)

    def _copy_link_auto(self):
        target = self.current_http_url if self.rb_http.isChecked() else self.current_deeplink_url
        QApplication.clipboard().setText(target)
        QMessageBox.information(
            self,
            "链接已复制",
            f"直达链接已复制至剪贴板：\n{target}\n\n在 QField【从 URL 导入工程】中粘贴或发送至手机浏览器打开。"
        )

    def _copy_firewall_cmd(self):
        cmd = f'netsh advfirewall firewall add rule name="QFieldDrop" dir=in action=allow protocol=TCP localport={self.port}'
        QApplication.clipboard().setText(cmd)
        QMessageBox.information(
            self,
            "Windows 防火墙放行命令",
            f"若手机无法连接电脑，请以管理员身份打开 PowerShell 运行以下已复制的命令：\n\n{cmd}"
        )
