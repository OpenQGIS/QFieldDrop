# -*- coding: utf-8 -*-
"""
QField LAN Drop - Tab 1: QR Code & Deep Link Direct Scan
Generates QField deep link (qfield://) and standard HTTP QR codes with IP switching.
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
        layout.setContentsMargins(8, 8, 8, 8)

        # 1. Network IP Selector GroupBox
        net_group = QGroupBox("局域网 IP 设置")
        net_layout = QHBoxLayout(net_group)
        net_lbl = QLabel("本机直传 IP:")
        net_layout.addWidget(net_lbl)

        self.ip_combo = QComboBox()
        self.ip_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        lan_ips = NetworkHelper.get_all_lan_ips()
        for item in lan_ips:
            self.ip_combo.addItem(item['label'], item['ip'])

        self.ip_combo.currentIndexChanged.connect(self._on_ip_combo_changed)
        net_layout.addWidget(self.ip_combo, 1)

        btn_firewall = QPushButton("防火墙放行命令")
        btn_firewall.setIcon(get_icon("shield"))
        btn_firewall.clicked.connect(self._copy_firewall_cmd)
        net_layout.addWidget(btn_firewall)

        layout.addWidget(net_group)

        # 2. QR Code GroupBox
        qr_group = QGroupBox("手机扫码快速投送")
        qr_layout = QVBoxLayout(qr_group)
        qr_layout.setAlignment(ALIGN_CENTER)

        # QR Code Display
        self.qr_label = QLabel()
        self.qr_label.setFixedSize(220, 220)
        self.qr_label.setAlignment(ALIGN_CENTER)
        # Note: QR code must be on white background for scanner contrast
        self.qr_label.setStyleSheet("background-color: #FFFFFF; border: 1px solid #CCCCCC;")
        qr_layout.addWidget(self.qr_label, 0, ALIGN_CENTER)

        # Mode Selection Radio buttons
        mode_row = QHBoxLayout()
        mode_row.setAlignment(ALIGN_CENTER)
        self.btn_group = QButtonGroup(self)

        self.rb_deeplink = QRadioButton("QField 唤醒码 (系统相机直接打开)")
        self.rb_deeplink.setChecked(True)
        self.rb_deeplink.setToolTip("使用 qfield:// 协议，手机相机扫码即可唤起 QField 导入工程")

        self.rb_http = QRadioButton("标准下载码 (浏览器/通用下载)")
        self.rb_http.setToolTip("标准 HTTP 地址，可用于手机浏览器扫码下载或手动输入")

        self.btn_group.addButton(self.rb_deeplink)
        self.btn_group.addButton(self.rb_http)
        self.rb_deeplink.toggled.connect(self._update_urls_and_qr)

        mode_row.addWidget(self.rb_deeplink)
        mode_row.addSpacing(20)
        mode_row.addWidget(self.rb_http)
        qr_layout.addLayout(mode_row)

        layout.addWidget(qr_group)

        # 3. Domain and Link Actions
        action_group = QGroupBox("直达链接与域名")
        action_layout = QVBoxLayout(action_group)

        domain_row = QHBoxLayout()
        self.mdns_lbl = QLabel(f"局域网通用域名: <code>http://qgis-drop.local:{self.port}/project.zip</code>")
        domain_row.addWidget(self.mdns_lbl)
        domain_row.addStretch()

        btn_copy_mdns = QPushButton("复制域名")
        btn_copy_mdns.setIcon(get_icon("copy"))
        btn_copy_mdns.clicked.connect(lambda: QApplication.clipboard().setText(f"http://qgis-drop.local:{self.port}/project.zip"))
        domain_row.addWidget(btn_copy_mdns)
        action_layout.addLayout(domain_row)

        links_row = QHBoxLayout()
        btn_copy_link = QPushButton("复制 HTTP 链接")
        btn_copy_link.setIcon(get_icon("link"))
        btn_copy_link.clicked.connect(self._copy_http_url)
        links_row.addWidget(btn_copy_link)

        btn_copy_deep = QPushButton("复制 QField 协议链接")
        btn_copy_deep.setIcon(get_icon("link"))
        btn_copy_deep.clicked.connect(self._copy_deeplink_url)
        links_row.addWidget(btn_copy_deep)

        action_layout.addLayout(links_row)
        layout.addWidget(action_group)

        layout.addStretch()

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
        encoded_import = urllib.parse.quote(self.current_http_url, safe=':/')
        self.current_deeplink_url = f"qfield://local?import={encoded_import}"

        target = self.current_deeplink_url if self.rb_deeplink.isChecked() else self.current_http_url

        matrix = generate_qr_matrix(target, ecc='M')
        pixmap = render_qr_to_qpixmap(matrix, target_size=210, border_modules=2)
        if pixmap:
            self.qr_label.setPixmap(pixmap)

    def _copy_http_url(self):
        QApplication.clipboard().setText(self.current_http_url)
        QMessageBox.information(
            self,
            "复制成功",
            f"HTTP 直链已复制到剪贴板：\n{self.current_http_url}\n\n可在手机浏览器中粘贴直接下载。"
        )

    def _copy_deeplink_url(self):
        QApplication.clipboard().setText(self.current_deeplink_url)
        QMessageBox.information(
            self,
            "复制成功",
            f"QField 专属协议链接已复制：\n{self.current_deeplink_url}\n\n可通过微信/钉钉/备忘录发送至手机点击直达。"
        )

    def _copy_firewall_cmd(self):
        cmd = f'netsh advfirewall firewall add rule name="QFieldDrop" dir=in action=allow protocol=TCP localport={self.port}'
        QApplication.clipboard().setText(cmd)
        QMessageBox.information(
            self,
            "Windows 防火墙放行命令",
            f"若手机无法连接电脑，请以管理员身份打开 PowerShell 运行以下已复制的命令：\n\n{cmd}"
        )
