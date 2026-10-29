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
    QDialogButtonBox, QTabWidget, QWidget
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


class AdbDetectWorker(QThread):
    finished_signal = pyqtSignal(bool, list)

    def run(self):
        try:
            avail = AdbPusher.is_adb_available()
            devices = AdbPusher.list_devices() if avail else []
            self.finished_signal.emit(avail, devices)
        except Exception:
            self.finished_signal.emit(False, [])


class MobileInstallDialog(QDialog):
    def __init__(self, port: int, parent=None):
        super().__init__(parent)
        self.mobile_version = self._get_mobile_version()
        self.setWindowTitle(f"QField 手机助手安装 (移动端独立版本: v{self.mobile_version})")
        self.resize(520, 310)
        self.port = port
        self.current_ip = "127.0.0.1"

        # Determine IP once
        self.lan_ips = NetworkHelper.get_all_lan_ips()
        if self.lan_ips:
            self.current_ip = self.lan_ips[0]['ip']

        self._init_ui()
        self._update_qr_and_urls()

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

        qr_group = QGroupBox("QField 伴侣插件扫码安装")
        qr_layout = QVBoxLayout(qr_group)
        qr_layout.setSpacing(8)
        qr_layout.setContentsMargins(12, 10, 12, 10)

        # 1. IP Selection Row (Compact)
        ip_row = QHBoxLayout()
        ip_row.addWidget(QLabel("投送网卡:"))
        self.ip_combo = QComboBox()
        self.ip_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        for idx, item in enumerate(self.lan_ips):
            self.ip_combo.addItem(item['label'], item['ip'])
            self.ip_combo.setItemData(idx, item.get('tooltip', item['label']), Qt.ToolTipRole)
        if self.ip_combo.count() > 0:
            self.ip_combo.setToolTip(self.ip_combo.itemData(0, Qt.ToolTipRole))
        self.ip_combo.currentIndexChanged.connect(self._on_ip_changed)
        ip_row.addWidget(self.ip_combo)
        ip_row.addStretch()
        qr_layout.addLayout(ip_row)

        # 2. Main Middle: QR on left, Guide & URL & Offline Export on right
        mid_row = QHBoxLayout()
        mid_row.setSpacing(14)

        self.qr_label = QLabel()
        self.qr_label.setFixedSize(160, 160)
        self.qr_label.setAlignment(ALIGN_CENTER)
        self.qr_label.setStyleSheet("background-color: #FFFFFF; border: 1px solid palette(mid); border-radius: 6px;")
        mid_row.addWidget(self.qr_label, 0, Qt.AlignTop)

        right_col = QVBoxLayout()
        right_col.setSpacing(6)

        lbl_steps = QLabel(
            "<div style='line-height: 140%;'>"
            "<b>QField 扫码极速安装：</b><br>"
            "1. 打开手机 QField ➔【设置】➔【插件】<br>"
            "2. 点击【从 URL 安装】右侧扫码图标扫描左侧码<br>"
            "<small style='color: #64748B;'>（亦可用手机自带浏览器扫码直接下载 ZIP）</small>"
            "</div>"
        )
        lbl_steps.setWordWrap(True)
        right_col.addWidget(lbl_steps)

        right_col.addSpacing(2)
        lbl_manual = QLabel("<small style='color: #64748B;'>手动安装网址：</small>")
        right_col.addWidget(lbl_manual)

        url_row = QHBoxLayout()
        url_row.setSpacing(6)
        self.url_edit = QLineEdit()
        self.url_edit.setReadOnly(True)
        url_row.addWidget(self.url_edit, 1)

        btn_copy_url = QPushButton("复制网址")
        btn_copy_url.setIcon(get_icon("copy"))
        btn_copy_url.setToolTip("复制插件安装网址并发送至手机")
        btn_copy_url.clicked.connect(self._copy_url)
        url_row.addWidget(btn_copy_url)
        right_col.addLayout(url_row)

        right_col.addSpacing(4)
        btn_export = QPushButton("导出离线包 (ZIP)...")
        btn_export.setIcon(get_icon("download"))
        btn_export.setToolTip("无局域网环境时，可导出独立 ZIP 发送至手机安装")
        btn_export.clicked.connect(self._export_offline_zip)
        right_col.addWidget(btn_export, 0, Qt.AlignLeft)

        mid_row.addLayout(right_col, 1)
        qr_layout.addLayout(mid_row)
        main_layout.addWidget(qr_group, 1)

        # 3. Bottom Native Actions with QDialogButtonBox (Localized "关闭")
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        self.button_box = QDialogButtonBox()
        btn_close = self.button_box.addButton("关闭", QDialogButtonBox.RejectRole)
        btn_close.clicked.connect(self.close)
        bottom_row.addWidget(self.button_box)
        main_layout.addLayout(bottom_row)

    def _on_ip_changed(self):
        curr_idx = self.ip_combo.currentIndex()
        if curr_idx >= 0:
            tip = self.ip_combo.itemData(curr_idx, Qt.ToolTipRole)
            if tip:
                self.ip_combo.setToolTip(tip)
        data = self.ip_combo.currentData()
        if data:
            self.current_ip = data
        self._update_qr_and_urls()

    def _update_qr_and_urls(self):
        download_url = f"http://{self.current_ip}:{self.port}/mobile.zip"
        self.url_edit.setText(download_url)
        self.url_edit.setCursorPosition(0)

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

    def _cleanup(self):
        if getattr(self, '_cleaned_up', False):
            return
        self._cleaned_up = True

        worker = getattr(self, '_adb_detect_worker', None)
        if worker:
            try:
                worker.finished_signal.disconnect()
            except (TypeError, RuntimeError):
                pass
            if worker.isRunning():
                worker.wait(400)
            self._adb_detect_worker = None

        a_worker = getattr(self, 'adb_worker', None)
        if a_worker:
            try:
                a_worker.finished_signal.disconnect()
            except (TypeError, RuntimeError):
                pass
            if a_worker.isRunning():
                a_worker.wait(400)
            self.adb_worker = None

    def closeEvent(self, event):
        self._cleanup()
        event.accept()
        super().closeEvent(event)

    def reject(self):
        self._cleanup()
        super().reject()

    def __del__(self):
        try:
            self._cleanup()
        except Exception:
            pass
