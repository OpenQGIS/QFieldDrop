# -*- coding: utf-8 -*-
"""
QField LAN Drop - Outbound Dispatch Dialog (投送至手机 - Drop Out)
Native QGIS Desktop UI style:
- Dedicated exclusively to packaging and dispatching projects to mobile devices
- Channels: QR Scan DeepLink / LocalSend Auto-push / Advanced ADB & QML
"""

import os
import shutil
from typing import Optional

from qgis.core import QgsProject
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QPushButton, QTabWidget, QProgressBar, QMessageBox, QDialogButtonBox
)
from qgis.PyQt.QtCore import QTimer, Qt

from ..core.net_server import LanDropServer
from ..core.packager import ProjectPackager
from ..core.mdns_server import MdnsResponder

from .tab_qr import QrDropTab
from .tab_localsend import LocalSendTab
from .external_layers_dialog import ExternalLayersDialog
from .icon_helper import get_icon


class QFieldSendDialog(QDialog):
    """Dedicated dialog for packaging and dispatching current QGIS project to phone."""

    def __init__(self, parent=None, initial_tab: int = 0):
        super().__init__(parent)
        self.initial_tab = initial_tab
        self.setWindowTitle("QField 局域网直传 - 投送至手机 (Drop Out)")
        self.resize(560, 600)
        self.setModal(False)
        self.setAttribute(Qt.WA_DeleteOnClose, False)

        self._cleaned_up = False
        self.is_ready = False
        self.server: Optional[LanDropServer] = None
        self.mdns: Optional[MdnsResponder] = None
        self.dist_dir: Optional[str] = None
        self.pkg_info = {}
        self.port = 8899

        # Step 1: Check project and package
        project = QgsProject.instance()
        if not project.fileName():
            QMessageBox.warning(
                parent or self,
                "工程未保存",
                "当前 QGIS 工程尚未保存到本地磁盘！\n\n请先保存工程文件（.qgz 或 .qgs）后再进行局域网直传。"
            )
            QTimer.singleShot(0, self.close)
            return

        if not self._prepare_package():
            QTimer.singleShot(0, self.close)
            return

        # Step 2: Start background server & mDNS for downloading
        self._init_server()

        # Step 3: Build UI
        self._init_ui()

        # Step 4: Set initial active tab
        if 0 <= self.initial_tab < self.tabs.count():
            self.tabs.setCurrentIndex(self.initial_tab)
            if self.initial_tab == 1 and hasattr(self, 'tab_localsend'):
                self.tab_localsend.start_scan()

        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.is_ready = True

    def _on_tab_changed(self, idx: int):
        if idx == 1 and hasattr(self, 'tab_localsend') and self.tab_localsend:
            if not getattr(self.tab_localsend, 'has_scanned', False):
                self.tab_localsend.start_scan()

    def _prepare_package(self) -> bool:
        project = QgsProject.instance()
        if not project.fileName():
            return False

        try:
            self.pkg_info = ProjectPackager.package_project(project)
            self.dist_dir = self.pkg_info['dist_dir']
            return True
        except Exception as e:
            QMessageBox.critical(self, "打包失败", f"打包工程出现错误：\n{str(e)}")
            return False

    def _init_server(self):
        if not self.pkg_info:
            return

        zip_filename = self.pkg_info['zip_filename']
        project = QgsProject.instance()
        project_dir = os.path.dirname(project.fileName()) if project.fileName() else ""
        upload_dir = os.path.join(project_dir, "_qfield_return")
        self.server = LanDropServer(self.dist_dir, zip_filename, start_port=8899, upload_dir=upload_dir)
        self.port = self.server.start()

        self.server.signals.client_connected.connect(self._on_client_connected)
        self.server.signals.transfer_progress.connect(self._on_transfer_progress)
        self.server.signals.transfer_completed.connect(self._on_transfer_done)
        self.server.signals.server_error.connect(self._on_server_error)

        if self.mdns:
            self.mdns.stop()
        initial_ip = self.tab_qr.get_selected_ip() if hasattr(self, 'tab_qr') and self.tab_qr else "127.0.0.1"
        self.mdns = MdnsResponder("qgis-drop.local", initial_ip)
        self.mdns.start()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(9, 9, 9, 9)
        layout.setSpacing(8)

        # 1. Project Info Native GroupBox
        info_group = QGroupBox("当前工程与打包信息")
        info_layout = QHBoxLayout(info_group)
        info_layout.setContentsMargins(9, 8, 9, 8)

        proj_name = self.pkg_info.get('project_name', '工程')
        size_bytes = self.pkg_info.get('size_bytes', 0)
        size_mb = size_bytes / (1024 * 1024)
        file_count = self.pkg_info.get('file_count', 0)

        meta_text = f"工程名: <b>{proj_name}</b> &nbsp;&nbsp;|&nbsp;&nbsp; 压缩包大小: <b>{size_mb:.2f} MB</b> &nbsp;&nbsp;|&nbsp;&nbsp; 包含文件: <b>{file_count} 个</b>"
        self.meta_lbl = QLabel(meta_text)
        info_layout.addWidget(self.meta_lbl)
        info_layout.addStretch()

        ext_count = len(self.pkg_info.get('external_layers', []))
        self.btn_warn = QPushButton(f"{ext_count} 个外部图层")
        self.btn_warn.setIcon(get_icon("alert-triangle"))
        self.btn_warn.setToolTip("查看位于工程目录外的图层")
        self.btn_warn.clicked.connect(self._show_external_layers)
        self.btn_warn.setVisible(ext_count > 0)
        info_layout.addWidget(self.btn_warn)

        btn_refresh = QPushButton("重新打包")
        btn_refresh.setIcon(get_icon("refresh"))
        btn_refresh.clicked.connect(self._repackage)
        info_layout.addWidget(btn_refresh)

        layout.addWidget(info_group)

        # 2. Native QTabWidget for Outbound Channels
        self.tabs = QTabWidget()

        # Tab 0: QR Code Scan & DeepLink
        self.tab_qr = QrDropTab(self.port, self.pkg_info['zip_filename'], self)
        self.tab_qr.ip_changed.connect(self._on_ip_changed)
        self.tabs.addTab(self.tab_qr, get_icon("qr"), "扫码唤醒直传")

        if self.mdns:
            self.mdns.update_ip(self.tab_qr.get_selected_ip())

        # Tab 1: LocalSend Push
        self.tab_localsend = LocalSendTab(
            get_local_ip_cb=self.tab_qr.get_selected_ip,
            zip_path=self.pkg_info['zip_path'],
            zip_filename=self.pkg_info['zip_filename'],
            parent=self
        )
        self.tabs.addTab(self.tab_localsend, get_icon("radio"), "LocalSend 免扫码")


        layout.addWidget(self.tabs, 1)

        # 3. Global Download Progress Bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # 4. Bottom Native Bar: Status on Left + QDialogButtonBox on Right
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 4, 0, 0)

        self.status_icon = QLabel()
        self.status_icon.setPixmap(get_icon("info").pixmap(16, 16))
        bottom_row.addWidget(self.status_icon)

        self.status_box = QLabel(f"投送服务已就绪，正在监听局域网端口 :{self.port}")
        bottom_row.addWidget(self.status_box, 1)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Close)
        self.button_box.rejected.connect(self.close)
        bottom_row.addWidget(self.button_box)

        layout.addLayout(bottom_row)

    def _on_ip_changed(self, ip: str):
        if self.mdns:
            self.mdns.update_ip(ip)

    def _show_external_layers(self):
        layers = self.pkg_info.get('external_layers', [])
        dlg = ExternalLayersDialog(layers, self)
        dlg.exec_()

    def _repackage(self):
        if self.server:
            self.server.stop()

        if self.dist_dir and os.path.exists(self.dist_dir):
            shutil.rmtree(self.dist_dir, ignore_errors=True)

        if not self._prepare_package():
            return

        self._init_server()
        self.tab_qr.update_port_and_file(self.port, self.pkg_info['zip_filename'])
        self.tab_localsend.update_package(self.pkg_info['zip_path'], self.pkg_info['zip_filename'])

        if hasattr(self, 'meta_lbl') and self.meta_lbl:
            pname = self.pkg_info.get('project_name', '工程')
            smb = self.pkg_info.get('size_bytes', 0) / (1024 * 1024)
            fcnt = self.pkg_info.get('file_count', 0)
            self.meta_lbl.setText(
                f"工程名: <b>{pname}</b> &nbsp;&nbsp;|&nbsp;&nbsp; 压缩包大小: <b>{smb:.2f} MB</b> &nbsp;&nbsp;|&nbsp;&nbsp; 包含文件: <b>{fcnt} 个</b>"
            )

        if hasattr(self, 'btn_warn') and self.btn_warn:
            ext_count = len(self.pkg_info.get('external_layers', []))
            self.btn_warn.setText(f"{ext_count} 个外部图层")
            self.btn_warn.setVisible(ext_count > 0)

        self.status_box.setText("工程已重新打包，分发载荷已刷新！")

    def _on_client_connected(self, client_ip: str):
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.status_box.setText(f"手机 [{client_ip}] 已连接，正在投送工程包...")

    def _on_transfer_progress(self, client_ip: str, sent_bytes: int, total_bytes: int):
        if total_bytes > 0:
            pct = int((sent_bytes / total_bytes) * 100)
            self.progress_bar.setValue(pct)
            sent_mb = sent_bytes / (1024 * 1024)
            tot_mb = total_bytes / (1024 * 1024)
            self.status_box.setText(f"向 [{client_ip}] 发送数据: {sent_mb:.2f} MB / {tot_mb:.2f} MB ({pct}%)")

    def _on_transfer_done(self, client_ip: str, filename: str):
        self.progress_bar.setValue(100)
        self.status_box.setText(f"成功投送至手机 [{client_ip}]！手机 QField 正在载入。")

    def _on_server_error(self, err_msg: str):
        self.status_box.setText(f"服务异常: {err_msg}")

    def _cleanup(self):
        if getattr(self, '_cleaned_up', False):
            return
        self._cleaned_up = True

        try:
            if hasattr(self, 'tab_localsend') and self.tab_localsend:
                self.tab_localsend.stop()
        except Exception:
            pass

        try:
            if self.mdns:
                self.mdns.stop()
                self.mdns = None
        except Exception:
            pass

        try:
            if self.server:
                self.server.stop()
                self.server = None
        except Exception:
            pass

        try:
            if self.dist_dir and os.path.exists(self.dist_dir):
                shutil.rmtree(self.dist_dir, ignore_errors=True)
                self.dist_dir = None
        except Exception:
            pass

    def closeEvent(self, event):
        self._cleanup()
        event.accept()
        super().closeEvent(event)

    def reject(self):
        self._cleanup()
        super().reject()
