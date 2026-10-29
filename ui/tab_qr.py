# -*- coding: utf-8 -*-
"""
QField LAN Drop - Tab 1: QR Code & Deep Link Direct Scan (Option B Sub-Tabs Architecture)
Features 3 dedicated sub-tabs:
1. Camera DeepLink (qfield://) auto-wakeup
2. Browser HTTP Download ZIP
3. Manual URL & Offline ZIP Package Export
Native QGIS Desktop UI style.
"""

import os
import urllib.parse
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QApplication, QGroupBox, QMessageBox,
    QTabWidget, QLineEdit, QFileDialog, QStackedWidget, QButtonGroup
)
from qgis.PyQt.QtCore import Qt, pyqtSignal

from ..core.net_server import NetworkHelper
from ..core.qr_native import generate_qr_matrix, render_qr_to_qpixmap
from .icon_helper import get_icon, get_icon_path

ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter if hasattr(Qt, 'AlignmentFlag') else Qt.AlignCenter


class QrDropTab(QWidget):
    ip_changed = pyqtSignal(str)

    def __init__(self, port: int, zip_filename: str, zip_path: str = "", parent=None):
        super().__init__(parent)
        self.port = port
        self.zip_filename = zip_filename
        self.zip_path = zip_path
        self.current_http_url = ""
        self.current_deeplink_url = ""

        self._init_ui()
        self._update_urls_and_qr()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(6, 6, 6, 6)

        # 1. Option B: Sub-Tabs on top for the 3 distinct wireless options
        self.sub_tabs = QTabWidget()

        # --- Sub-Tab 1: Camera DeepLink ---
        sub_deeplink = QWidget()
        dl_layout = QHBoxLayout(sub_deeplink)
        dl_layout.setContentsMargins(10, 8, 10, 8)
        dl_layout.setSpacing(14)

        self.qr_deeplink_lbl = QLabel()
        self.qr_deeplink_lbl.setFixedSize(150, 150)
        self.qr_deeplink_lbl.setAlignment(ALIGN_CENTER)
        self.qr_deeplink_lbl.setStyleSheet("background-color: #FFFFFF; border: 1px solid palette(mid); border-radius: 4px;")
        dl_layout.addWidget(self.qr_deeplink_lbl, 0, Qt.AlignVCenter)

        dl_right = QVBoxLayout()
        dl_right.setSpacing(8)
        dl_right.setAlignment(Qt.AlignVCenter)

        lbl_dl_desc = QLabel(
            "<div style='line-height: 145%;'>"
            "<b>手机系统相机直接扫码：</b><br>"
            "立即可自动唤醒手机 QField 并弹出工程导入确认，无需手动在文件管理器中查找。<br>"
            "<small style='color: #64748B;'>（外业极速导入首选推荐方式）</small>"
            "</div>"
        )
        lbl_dl_desc.setWordWrap(True)
        dl_right.addWidget(lbl_dl_desc)

        btn_copy_dl = QPushButton("复制唤醒链接")
        btn_copy_dl.setIcon(get_icon("link"))
        btn_copy_dl.setToolTip("复制 qfield:// 深度唤醒链接，发至手机点击可直接唤醒 QField")
        btn_copy_dl.clicked.connect(self._copy_deeplink)
        dl_right.addWidget(btn_copy_dl, 0, Qt.AlignLeft)

        dl_layout.addLayout(dl_right, 1)
        self.sub_tabs.addTab(sub_deeplink, get_icon("qr"), "相机直达唤醒 (推荐)")

        # --- Sub-Tab 2: Browser HTTP Download ZIP ---
        sub_http = QWidget()
        http_layout = QHBoxLayout(sub_http)
        http_layout.setContentsMargins(10, 8, 10, 8)
        http_layout.setSpacing(14)

        self.qr_http_lbl = QLabel()
        self.qr_http_lbl.setFixedSize(150, 150)
        self.qr_http_lbl.setAlignment(ALIGN_CENTER)
        self.qr_http_lbl.setStyleSheet("background-color: #FFFFFF; border: 1px solid palette(mid); border-radius: 4px;")
        http_layout.addWidget(self.qr_http_lbl, 0, Qt.AlignVCenter)

        http_right = QVBoxLayout()
        http_right.setSpacing(8)
        http_right.setAlignment(Qt.AlignVCenter)

        lbl_http_desc = QLabel(
            "<div style='line-height: 145%;'>"
            "<b>浏览器或微信扫码下载：</b><br>"
            "直接下载工程 ZIP 压缩包至手机本地存储。<br>"
            "<small style='color: #64748B;'>下载后在 QField 首页点击【➕】➔【从 ZIP 导入工程】即可打开。</small>"
            "</div>"
        )
        lbl_http_desc.setWordWrap(True)
        http_right.addWidget(lbl_http_desc)

        btn_copy_http = QPushButton("复制下载链接")
        btn_copy_http.setIcon(get_icon("link"))
        btn_copy_http.setToolTip("复制标准 HTTP 直链，可在手机浏览器中直接粘贴下载")
        btn_copy_http.clicked.connect(self._copy_http_url)
        http_right.addWidget(btn_copy_http, 0, Qt.AlignLeft)

        http_layout.addLayout(http_right, 1)
        self.sub_tabs.addTab(sub_http, get_icon("download"), "下载 ZIP 导入")

        # --- Sub-Tab 3: Manual URL & Offline Package ---
        sub_manual = QWidget()
        man_layout = QVBoxLayout(sub_manual)
        man_layout.setContentsMargins(12, 10, 12, 10)
        man_layout.setSpacing(8)

        man_desc = QLabel(
            "<div style='line-height: 140%;'>"
            "<b>备用渠道：手动输入网址或导出离线包</b><br>"
            "<small style='color: #64748B;'>适用于手机无相机扫码功能，或现场无局域网 Wi-Fi 的特殊场景。</small>"
            "</div>"
        )
        man_desc.setWordWrap(True)
        man_layout.addWidget(man_desc)

        url_row = QHBoxLayout()
        url_row.setSpacing(6)
        self.url_edit = QLineEdit()
        self.url_edit.setReadOnly(True)
        url_row.addWidget(self.url_edit, 1)

        btn_copy_manual = QPushButton("复制网址")
        btn_copy_manual.setIcon(get_icon("copy"))
        btn_copy_manual.clicked.connect(self._copy_http_url)
        url_row.addWidget(btn_copy_manual)
        man_layout.addLayout(url_row)

        self.lbl_simple_tip = QLabel()
        self.lbl_simple_tip.setWordWrap(True)
        self.lbl_simple_tip.setTextFormat(Qt.RichText)
        man_layout.addWidget(self.lbl_simple_tip)

        off_row = QHBoxLayout()
        btn_export = QPushButton("导出离线工程包 (ZIP)...")
        btn_export.setIcon(get_icon("download"))
        btn_export.setToolTip("将当前工程打包为独立 ZIP 文件，可通过微信、QQ 或 USB 发给手机")
        btn_export.clicked.connect(self._export_offline_zip)
        off_row.addWidget(btn_export, 0, Qt.AlignLeft)
        off_row.addStretch()
        man_layout.addLayout(off_row)

        man_layout.addStretch()

        self.sub_tabs.addTab(sub_manual, get_icon("link"), "手动网址 / 离线包")

        layout.addWidget(self.sub_tabs, 1)

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
        for idx, item in enumerate(NetworkHelper.get_all_lan_ips()):
            self.ip_combo.addItem(item['label'], item['ip'])
            self.ip_combo.setItemData(idx, item.get('tooltip', item['label']), Qt.ToolTipRole)
        if self.ip_combo.count() > 0:
            self.ip_combo.setToolTip(self.ip_combo.itemData(0, Qt.ToolTipRole))
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

    def get_selected_ip(self) -> str:
        ip = self.ip_combo.currentData()
        if not ip:
            ip = self.ip_combo.currentText().split(' ')[0]
        return ip or "127.0.0.1"

    def _on_ip_combo_changed(self):
        curr_idx = self.ip_combo.currentIndex()
        if curr_idx >= 0:
            tip = self.ip_combo.itemData(curr_idx, Qt.ToolTipRole)
            if tip:
                self.ip_combo.setToolTip(tip)
        ip = self.get_selected_ip()
        self.ip_changed.emit(ip)
        self._update_urls_and_qr()

    def update_port_and_file(self, port: int, zip_filename: str, zip_path: str = ""):
        self.port = port
        self.zip_filename = zip_filename
        if zip_path:
            self.zip_path = zip_path
        if hasattr(self, 'mdns_lbl'):
            self.mdns_lbl.setText(f"局域网通用域名: <code>http://qgis-drop.local:{self.port}/project.zip</code>")
        self._update_urls_and_qr()

    def _update_urls_and_qr(self):
        ip = self.get_selected_ip()
        # Use clean fixed route "project.zip" instead of percent-encoded Chinese characters.
        # This keeps the URL short, easy to type, and generates a cleaner low-density QR code.
        # The HTTP server sends RFC 6266 filename*=UTF-8'' header, so browsers automatically
        # save the file with the real Chinese project name (e.g. 工程测试.zip).
        self.current_http_url = f"http://{ip}:{self.port}/project.zip"
        self.current_deeplink_url = f"qfield://local?import={self.current_http_url}"

        if hasattr(self, 'url_edit'):
            self.url_edit.setText(self.current_http_url)
            self.url_edit.setCursorPosition(0)

        if hasattr(self, 'lbl_simple_tip'):
            self.lbl_simple_tip.setText(
                f"<small style='color: #64748B;'>💡 手动输入小技巧：手机浏览器直接输入 "
                f"<b style='color: palette(highlight);'>http://{ip}:{self.port}/</b> "
                f"也能直接下载，下载后文件名会自动恢复为工程原名。</small>"
            )

        # 1. Render Deeplink QR
        if hasattr(self, 'qr_deeplink_lbl'):
            m1 = generate_qr_matrix(self.current_deeplink_url, ecc='Q')
            pix1 = render_qr_to_qpixmap(m1, target_size=145, margin_px=6, icon_path=get_icon_path("DropOut"))
            if pix1:
                self.qr_deeplink_lbl.setPixmap(pix1)

        # 2. Render HTTP Download QR
        if hasattr(self, 'qr_http_lbl'):
            m2 = generate_qr_matrix(self.current_http_url, ecc='Q')
            pix2 = render_qr_to_qpixmap(m2, target_size=145, margin_px=6, icon_path=get_icon_path("DropOut"))
            if pix2:
                self.qr_http_lbl.setPixmap(pix2)

    def _copy_deeplink(self):
        QApplication.clipboard().setText(self.current_deeplink_url)
        QMessageBox.information(
            self, "复制成功",
            f"相机直接唤醒链接已复制至剪贴板：\n\n{self.current_deeplink_url}\n\n可直接通过聊天软件发送至手机。"
        )

    def _copy_http_url(self):
        QApplication.clipboard().setText(self.current_http_url)
        QMessageBox.information(
            self, "复制成功",
            f"标准下载链接已复制至剪贴板：\n\n{self.current_http_url}\n\n可在手机浏览器中直接粘贴下载。"
        )

    def _export_offline_zip(self):
        if not self.zip_path or not os.path.exists(self.zip_path):
            QMessageBox.warning(self, "提示", "工程压缩包尚未就绪，请等待打包完成或点击重新打包！")
            return
        dest_path, _ = QFileDialog.getSaveFileName(
            self, "导出离线工程压缩包", self.zip_filename or "project.zip", "Zip Archive (*.zip)"
        )
        if not dest_path:
            return
        try:
            import shutil
            shutil.copy2(self.zip_path, dest_path)
            QMessageBox.information(
                self, "导出成功",
                f"离线工程包已保存至：\n{dest_path}\n\n可直接发送至手机，在 QField【➕】➔【从 ZIP 导入工程】生效。"
            )
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出过程发生错误: {str(e)}")

    def _copy_firewall_cmd(self):
        cmd = f'netsh advfirewall firewall add rule name="QField LAN Drop" dir=in action=allow protocol=TCP localport={self.port}'
        QApplication.clipboard().setText(cmd)
        QMessageBox.information(
            self,
            "已复制防火墙规则",
            f"若手机因电脑防火墙拦截无法访问，请以管理员身份打开 PowerShell 运行以下命令：\n\n{cmd}\n\n已自动复制至剪贴板。"
        )
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
