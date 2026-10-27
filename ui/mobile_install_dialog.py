# -*- coding: utf-8 -*-
"""
QField LAN Drop - Mobile Companion Plugin Installer Dialog
Provides 3 offline channels to install QFieldDrop Mobile:
1. Camera QR scan: direct HTTP URL for QField's internal "Install from URL" QR scanner or browser download
2. No camera URL input: In QField -> Plugins -> Install from URL -> http://<IP>:<PORT>/mobile.zip
3. Zero-touch ADB: Silent direct sandbox injection
Native QGIS Desktop UI style.
"""

import os
import shutil
import zipfile
import urllib.parse
from typing import Optional

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QLineEdit, QComboBox, QMessageBox, QApplication, QFileDialog
)
from qgis.PyQt.QtCore import Qt

from ..core.net_server import NetworkHelper, LanDropServer
from ..core.qr_native import generate_qr_matrix, render_qr_to_qpixmap
from ..core.adb_pusher import AdbPusher
from .icon_helper import get_icon

ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter if hasattr(Qt, 'AlignmentFlag') else Qt.AlignCenter


class MobileInstallDialog(QDialog):
    def __init__(self, port: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("QField 手机助手安装")
        self.resize(560, 640)
        self.port = port
        self.current_ip = "127.0.0.1"

        # Determine IP
        lan_ips = NetworkHelper.get_all_lan_ips()
        if lan_ips:
            self.current_ip = lan_ips[0]['ip']

        self._init_ui()
        self._update_qr_and_urls()
        self._refresh_adb_devices()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # 1. Top IP Selector
        ip_row = QHBoxLayout()
        ip_row.addWidget(QLabel("当前电脑局域网 IP:"))
        self.ip_combo = QComboBox()
        self.ip_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        for item in NetworkHelper.get_all_lan_ips():
            self.ip_combo.addItem(item['label'], item['ip'])
        self.ip_combo.currentIndexChanged.connect(self._on_ip_changed)
        ip_row.addWidget(self.ip_combo, 1)
        layout.addLayout(ip_row)

        # 2. Channel 1: QR Code
        group_qr = QGroupBox("通道一：扫码安装插件 (推荐)")
        qr_layout = QVBoxLayout(group_qr)
        qr_layout.setAlignment(ALIGN_CENTER)

        self.qr_label = QLabel()
        self.qr_label.setFixedSize(180, 180)
        self.qr_label.setAlignment(ALIGN_CENTER)
        self.qr_label.setStyleSheet("background-color: #FFFFFF; border: 1px solid #CCCCCC;")
        qr_layout.addWidget(self.qr_label, 0, ALIGN_CENTER)

        qr_tip = QLabel(
            "<b>最佳方式：</b>在手机 QField 中打开【设置】→【插件】→【从 URL 安装】，<br>"
            "点击输入框右侧的 <b>📷 扫码图标</b> 扫描此码，即可直接下载并激活！<br>"
            "<span style='color: #64748B; font-size: 11px;'>（注：若用手机浏览器扫码，则自动下载 ZIP 安装包，在 QField 中【从压缩包安装】）</span>"
        )
        qr_tip.setWordWrap(True)
        qr_tip.setAlignment(ALIGN_CENTER)
        qr_layout.addWidget(qr_tip)

        layout.addWidget(group_qr)

        # 3. Channel 2: QField URL Input (For devices without camera)
        group_url = QGroupBox("通道二：QField 内部输入 URL 安装 (无摄像头/三防平板)")
        url_layout = QVBoxLayout(group_url)

        url_desc = QLabel(
            "手机打开 QField，进入【设置】→【插件 (Plugins)】→【从 URL 安装 (Install from URL)】，输入："
        )
        url_desc.setWordWrap(True)
        url_layout.addWidget(url_desc)

        url_row = QHBoxLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setReadOnly(True)
        url_row.addWidget(self.url_edit, 1)

        btn_copy_url = QPushButton("复制链接")
        btn_copy_url.setIcon(get_icon("copy"))
        btn_copy_url.clicked.connect(self._copy_url)
        url_row.addWidget(btn_copy_url)
        url_layout.addLayout(url_row)

        layout.addWidget(group_url)

        # 4. Channel 3: Android ADB Direct Injection (Zero-touch)
        group_adb = QGroupBox("通道三：Android ADB 一键静默写入 (免扫码免输入)")
        adb_layout = QVBoxLayout(group_adb)

        adb_desc = QLabel(
            "手机连接 USB 数据线或开启无线调试，直接由电脑将插件写入 QField 沙盒内部："
        )
        adb_desc.setWordWrap(True)
        adb_layout.addWidget(adb_desc)

        dev_row = QHBoxLayout()
        self.dev_combo = QComboBox()
        self.dev_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        dev_row.addWidget(self.dev_combo, 1)

        btn_refresh_dev = QPushButton("刷新设备")
        btn_refresh_dev.setIcon(get_icon("refresh"))
        btn_refresh_dev.clicked.connect(self._refresh_adb_devices)
        dev_row.addWidget(btn_refresh_dev)

        self.btn_install_adb = QPushButton("一键写入手机 QField (ADB)")
        self.btn_install_adb.setIcon(get_icon("zap"))
        self.btn_install_adb.setDefault(True)
        self.btn_install_adb.clicked.connect(self._install_via_adb)
        dev_row.addWidget(self.btn_install_adb)
        adb_layout.addLayout(dev_row)

        layout.addWidget(group_adb)

        # 5. Bottom Actions
        bottom_row = QHBoxLayout()

        btn_export = QPushButton("导出离线安装包 (ZIP)")
        btn_export.setIcon(get_icon("download"))
        btn_export.clicked.connect(self._export_offline_zip)
        bottom_row.addWidget(btn_export)

        bottom_row.addStretch()

        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.close)
        bottom_row.addWidget(btn_close)

        layout.addLayout(bottom_row)

    def _on_ip_changed(self):
        data = self.ip_combo.currentData()
        if data:
            self.current_ip = data
        self._update_qr_and_urls()

    def _update_qr_and_urls(self):
        download_url = f"http://{self.current_ip}:{self.port}/mobile.zip"
        self.url_edit.setText(download_url)

        # Note: In QField, plugins are installed via clean HTTP URL!
        # Scanning from QField's "Install from URL" QR scanner directly parses this download URL.
        matrix = generate_qr_matrix(download_url, ecc='M')
        pixmap = render_qr_to_qpixmap(matrix, target_size=170, border_modules=2)
        if pixmap:
            self.qr_label.setPixmap(pixmap)

    def _copy_url(self):
        txt = self.url_edit.text()
        QApplication.clipboard().setText(txt)
        QMessageBox.information(
            self, "已复制",
            f"手机端插件安装地址已复制：\n{txt}\n\n在手机 QField【设置】→【插件】→【从 URL 安装】粘贴即可。"
        )

    def _refresh_adb_devices(self):
        self.dev_combo.clear()
        if not AdbPusher.is_adb_available():
            self.dev_combo.addItem("未检测到 adb (需安装 Platform Tools)", "")
            self.btn_install_adb.setEnabled(False)
            return

        devices = AdbPusher.list_devices()
        if not devices:
            self.dev_combo.addItem("未连接任何 Android 设备", "")
            self.btn_install_adb.setEnabled(False)
        else:
            for serial, status in devices:
                self.dev_combo.addItem(f"{serial} ({status})", serial)
            self.btn_install_adb.setEnabled(True)

    def _install_via_adb(self):
        serial = self.dev_combo.currentData()
        if not serial:
            QMessageBox.warning(self, "提示", "请选择已连接的 Android 设备！")
            return

        plugin_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        mobile_src = os.path.join(plugin_root, "mobile")
        if not os.path.exists(mobile_src):
            mobile_src = os.path.join(os.path.dirname(plugin_root), "QFieldDrop-Mobile")

        self.btn_install_adb.setEnabled(False)
        self.btn_install_adb.setText("正在写入手机...")
        QApplication.processEvents()

        success, msg = AdbPusher.install_plugin(mobile_src, device_serial=serial)

        self.btn_install_adb.setEnabled(True)
        self.btn_install_adb.setText("一键写入手机 QField (ADB)")

        if success:
            QMessageBox.information(self, "安装成功", msg)
        else:
            QMessageBox.warning(self, "安装失败", msg)

    def _export_offline_zip(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出 QField 手机端助手插件", "qfield_drop_mobile.zip", "Zip Archive (*.zip)"
        )
        if not file_path:
            return

        plugin_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        mobile_src = os.path.join(plugin_root, "mobile")
        if not os.path.exists(mobile_src):
            mobile_src = os.path.join(os.path.dirname(plugin_root), "QFieldDrop-Mobile")

        try:
            with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(mobile_src):
                    for f in files:
                        full = os.path.join(root, f)
                        rel = os.path.relpath(full, mobile_src)
                        # Put files at root of ZIP for QField plugin compatibility
                        zf.write(full, arcname=rel)
            QMessageBox.information(
                self, "导出成功",
                f"离线安装包已保存至：\n{file_path}\n\n可将其发送至手机，在 QField【插件】→【从压缩包安装】生效。"
            )
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出过程发生错误: {str(e)}")
