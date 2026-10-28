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
    QGroupBox, QLineEdit, QComboBox, QMessageBox, QApplication, QFileDialog,
    QDialogButtonBox
)
from qgis.PyQt.QtCore import Qt, QThread, pyqtSignal

from ..core.net_server import NetworkHelper, LanDropServer
from ..core.qr_native import generate_qr_matrix, render_qr_to_qpixmap
from ..core.adb_pusher import AdbPusher
from .icon_helper import get_icon, get_icon_path

ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter if hasattr(Qt, 'AlignmentFlag') else Qt.AlignCenter


class AdbInstallWorker(QThread):
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, mobile_src: str, serial: Optional[str]):
        super().__init__()
        self.mobile_src = mobile_src
        self.serial = serial

    def run(self):
        try:
            success, msg = AdbPusher.install_plugin(self.mobile_src, device_serial=self.serial)
            self.finished_signal.emit(success, msg)
        except Exception as e:
            self.finished_signal.emit(False, f"写入异常: {str(e)}")


class MobileInstallDialog(QDialog):
    def __init__(self, port: int, parent=None):
        super().__init__(parent)
        self.mobile_version = self._get_mobile_version()
        self.setWindowTitle(f"QField 手机助手安装 (移动端独立版本: v{self.mobile_version})")
        self.resize(660, 470)
        self.port = port
        self.current_ip = "127.0.0.1"

        # Determine IP
        lan_ips = NetworkHelper.get_all_lan_ips()
        if lan_ips:
            self.current_ip = lan_ips[0]['ip']

        self._init_ui()
        self._update_qr_and_urls()
        self._refresh_adb_devices()

    def _get_mobile_version(self) -> str:
        plugin_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        mobile_meta = os.path.join(plugin_root, "mobile", "metadata.txt")
        if os.path.exists(mobile_meta):
            try:
                import configparser
                cfg = configparser.ConfigParser()
                cfg.read(mobile_meta, encoding='utf-8')
                return cfg.get("general", "version", fallback="1.0.1")
            except Exception:
                pass
        return "1.0.1"

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # 1. Top IP Selector
        ip_row = QHBoxLayout()
        ip_row.addWidget(QLabel("当前电脑局域网 IP:"))
        self.ip_combo = QComboBox()
        self.ip_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        for item in NetworkHelper.get_all_lan_ips():
            self.ip_combo.addItem(item['label'], item['ip'])
        self.ip_combo.currentIndexChanged.connect(self._on_ip_changed)
        ip_row.addWidget(self.ip_combo, 1)
        main_layout.addLayout(ip_row)

        # 2. Middle Body: Two-Column Layout
        body_layout = QHBoxLayout()
        body_layout.setSpacing(12)

        # --- Left Column: Wireless QR & URL Direct Install (Primary) ---
        group_left = QGroupBox("通道一：局域网无线直装 (推荐)")
        left_layout = QVBoxLayout(group_left)
        left_layout.setSpacing(8)
        left_layout.setContentsMargins(12, 12, 12, 12)

        self.qr_label = QLabel()
        self.qr_label.setFixedSize(160, 160)
        self.qr_label.setAlignment(ALIGN_CENTER)
        self.qr_label.setStyleSheet("background-color: #FFFFFF; border: 1px solid palette(mid); border-radius: 4px;")
        left_layout.addWidget(self.qr_label, 0, ALIGN_CENTER)

        lbl_steps = QLabel(
            "<b>QField 扫码安装步骤：</b><br>"
            "1. 手机打开 QField ➔【设置】➔【插件】<br>"
            "2. 点击【从 URL 安装】右侧扫码图标扫描上方码<br>"
            "<i>（若使用手机自带浏览器扫码，将直接下载 ZIP 安装包）</i>"
        )
        lbl_steps.setWordWrap(True)
        f_s = lbl_steps.font()
        f_s.setPointSize(max(8, f_s.pointSize() - 1))
        lbl_steps.setFont(f_s)
        left_layout.addWidget(lbl_steps)

        left_layout.addSpacing(4)
        lbl_manual = QLabel("无相机设备或手动输入地址：")
        f_m = lbl_manual.font()
        f_m.setPointSize(max(8, f_m.pointSize() - 1))
        lbl_manual.setFont(f_m)
        left_layout.addWidget(lbl_manual)

        url_row = QHBoxLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setReadOnly(True)
        url_row.addWidget(self.url_edit, 1)

        btn_copy_url = QPushButton("复制")
        btn_copy_url.setIcon(get_icon("copy"))
        btn_copy_url.clicked.connect(self._copy_url)
        url_row.addWidget(btn_copy_url)
        left_layout.addLayout(url_row)

        body_layout.addWidget(group_left, 1)

        # --- Right Column: Hardware Direct Injection & Offline ZIP ---
        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        # Channel 2: Android ADB Direct Injection
        group_adb = QGroupBox("通道二：Android ADB 极速直接写入")
        adb_layout = QVBoxLayout(group_adb)
        adb_layout.setSpacing(8)
        adb_layout.setContentsMargins(12, 12, 12, 12)

        adb_desc = QLabel(
            "手机连接 USB 数据线或开启无线调试，电脑直接将插件写入 QField 沙盒内部（免扫码）："
        )
        adb_desc.setWordWrap(True)
        adb_layout.addWidget(adb_desc)

        dev_row = QHBoxLayout()
        self.dev_combo = QComboBox()
        self.dev_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        dev_row.addWidget(self.dev_combo, 1)

        btn_refresh_dev = QPushButton("刷新")
        btn_refresh_dev.setIcon(get_icon("refresh"))
        btn_refresh_dev.clicked.connect(self._refresh_adb_devices)
        dev_row.addWidget(btn_refresh_dev)
        adb_layout.addLayout(dev_row)

        self.btn_install_adb = QPushButton("⚡ 一键写入手机 QField 插件目录")
        self.btn_install_adb.setIcon(get_icon("zap"))
        self.btn_install_adb.setDefault(True)
        self.btn_install_adb.clicked.connect(self._install_via_adb)
        adb_layout.addWidget(self.btn_install_adb)
        right_col.addWidget(group_adb)

        # Channel 3: Offline Package Export
        group_offline = QGroupBox("通道三：离线安装包 (无局域网环境)")
        offline_layout = QVBoxLayout(group_offline)
        offline_layout.setSpacing(8)
        offline_layout.setContentsMargins(12, 12, 12, 12)

        offline_desc = QLabel(
            "导出独立 ZIP 安装包，可通过微信/QQ/数据线发送至手机："
        )
        offline_desc.setWordWrap(True)
        offline_layout.addWidget(offline_desc)

        btn_export = QPushButton("导出离线安装包 (ZIP)...")
        btn_export.setIcon(get_icon("download"))
        btn_export.clicked.connect(self._export_offline_zip)
        offline_layout.addWidget(btn_export)

        lbl_offline_tip = QLabel("手机接收后，在 QField【插件】➔【从压缩包安装】生效。")
        lbl_offline_tip.setWordWrap(True)
        f_off = lbl_offline_tip.font()
        f_off.setPointSize(max(8, f_off.pointSize() - 1))
        lbl_offline_tip.setFont(f_off)
        offline_layout.addWidget(lbl_offline_tip)

        right_col.addWidget(group_offline)
        right_col.addStretch()

        body_layout.addLayout(right_col, 1)
        main_layout.addLayout(body_layout, 1)

        # 3. Bottom Native Actions with QDialogButtonBox
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        self.button_box = QDialogButtonBox(QDialogButtonBox.Close)
        self.button_box.rejected.connect(self.close)
        bottom_row.addWidget(self.button_box)
        main_layout.addLayout(bottom_row)

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
        matrix = generate_qr_matrix(download_url, ecc='Q')
        icon_path = get_icon_path("MobileSetup")
        pixmap = render_qr_to_qpixmap(matrix, target_size=160, margin_px=6, icon_path=icon_path)
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
        self.btn_install_adb.setText("正在写入手机 (后台传输)...")

        self.adb_worker = AdbInstallWorker(mobile_src, serial)
        self.adb_worker.finished_signal.connect(self._on_install_finished)
        self.adb_worker.start()

    def _on_install_finished(self, success: bool, msg: str):
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
