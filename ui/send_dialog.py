# -*- coding: utf-8 -*-
"""
QField LAN Drop - Outbound Dispatch Dialog (投送至手机 - Drop Out)
Native QGIS Desktop UI style:
- Dedicated exclusively to packaging and dispatching projects to mobile devices
- Channels: QR Scan DeepLink / LocalSend Auto-push / Advanced ADB & QML
- Asynchronous Non-blocking Project Packaging Engine
"""

import os
import shutil
import tempfile
from typing import Optional, Dict, Any

from qgis.core import QgsProject
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QPushButton, QTabWidget, QProgressBar, QMessageBox, QDialogButtonBox,
    QStackedWidget, QWidget
)
from qgis.PyQt.QtCore import QTimer, Qt, QThread, pyqtSignal

from ..core.net_server import LanDropServer
from ..core.packager import ProjectPackager
from ..core.mdns_server import MdnsResponder

from .tab_qr import QrDropTab
from .tab_localsend import LocalSendTab
from .external_layers_dialog import ExternalLayersDialog
from .icon_helper import get_icon


class PackageWorker(QThread):
    progress_signal = pyqtSignal(int, int, str)    # (current_files, total_files, rel_path)
    finished_signal = pyqtSignal(bool, dict, str)  # (success, pkg_info, error_msg)

    def __init__(self, src_dir: str, dist_dir: str, zip_filename: str, project_name: str, external_layers: list):
        super().__init__()
        self.src_dir = src_dir
        self.dist_dir = dist_dir
        self.zip_filename = zip_filename
        self.project_name = project_name
        self.external_layers = external_layers
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            zip_path = os.path.join(self.dist_dir, self.zip_filename)

            def _prog(cur, tot, fn):
                if not self._cancelled:
                    self.progress_signal.emit(cur, tot, fn)

            file_count = ProjectPackager.compress_directory(
                src_dir=self.src_dir,
                zip_path=zip_path,
                progress_callback=_prog,
                is_cancelled=lambda: self._cancelled,
                root_folder_name=self.project_name
            )

            if self._cancelled:
                self.finished_signal.emit(False, {}, "工程打包已取消")
                return

            size_bytes = os.path.getsize(zip_path) if os.path.exists(zip_path) else 0
            pkg_info = {
                'dist_dir': self.dist_dir,
                'zip_path': zip_path,
                'zip_filename': self.zip_filename,
                'project_name': self.project_name,
                'size_bytes': size_bytes,
                'file_count': file_count,
                'external_layers': self.external_layers,
                'qfieldsync_used': False
            }
            self.finished_signal.emit(True, pkg_info, "")
        except Exception as e:
            self.finished_signal.emit(False, {}, str(e))


class QFieldSendDialog(QDialog):
    """Dedicated dialog for packaging and dispatching current QGIS project to phone."""

    def __init__(self, parent=None, initial_tab: int = 0):
        super().__init__(parent)
        self.initial_tab = initial_tab
        self.setWindowTitle("QField 局域网直传 - 投送至手机 (Drop Out)")
        self.resize(520, 380)
        self.setModal(False)
        self.setAttribute(Qt.WA_DeleteOnClose, False)

        self._cleaned_up = False
        self.is_ready = False
        self.server: Optional[LanDropServer] = None
        self.mdns: Optional[MdnsResponder] = None
        self.dist_dir: Optional[str] = None
        self.pkg_info: Dict[str, Any] = {}
        self.port = 8899
        self.pkg_worker: Optional[PackageWorker] = None
        self.tab_qr: Optional[QrDropTab] = None
        self.tab_localsend: Optional[LocalSendTab] = None

        # Verify project is saved
        project = QgsProject.instance()
        if not project.fileName():
            QMessageBox.warning(
                parent or self,
                "工程未保存",
                "当前 QGIS 工程尚未保存到本地磁盘！\n\n请先保存工程文件（.qgz 或 .qgs）后再进行局域网直传。"
            )
            QTimer.singleShot(0, self.close)
            return

        self.is_ready = True
        self._init_ui()
        self._start_packaging()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(9, 9, 9, 9)
        layout.setSpacing(8)

        # 1. Project Info Native GroupBox
        info_group = QGroupBox("当前工程与打包信息")
        info_layout = QHBoxLayout(info_group)
        info_layout.setContentsMargins(9, 8, 9, 8)

        self.meta_lbl = QLabel("正在分析工程依赖并准备打包...")
        info_layout.addWidget(self.meta_lbl)
        info_layout.addStretch()

        self.btn_warn = QPushButton("外部图层")
        self.btn_warn.setIcon(get_icon("alert-triangle"))
        self.btn_warn.setToolTip("查看位于工程目录外的图层")
        self.btn_warn.clicked.connect(self._show_external_layers)
        self.btn_warn.setVisible(False)
        info_layout.addWidget(self.btn_warn)

        self.btn_refresh = QPushButton("重新打包")
        self.btn_refresh.setIcon(get_icon("refresh"))
        self.btn_refresh.clicked.connect(self._repackage)
        self.btn_refresh.setEnabled(False)
        info_layout.addWidget(self.btn_refresh)

        layout.addWidget(info_group)

        # 2. Central Stacked Widget: Page 0 = Packaging Progress, Page 1 = Outbound Tabs
        self.stack = QStackedWidget()

        # Page 0: Packaging Status Page
        self.pack_page = QWidget()
        pack_layout = QVBoxLayout(self.pack_page)
        pack_layout.setContentsMargins(16, 24, 16, 24)
        pack_layout.setSpacing(12)
        pack_layout.setAlignment(Qt.AlignCenter)

        self.pack_status_lbl = QLabel("正在整理工程图层与依赖文件...")
        self.pack_status_lbl.setAlignment(Qt.AlignCenter)
        pack_font = self.pack_status_lbl.font()
        pack_font.setBold(True)
        self.pack_status_lbl.setFont(pack_font)
        pack_layout.addWidget(self.pack_status_lbl)

        self.pack_progress = QProgressBar()
        self.pack_progress.setRange(0, 0)  # Indeterminate initially
        self.pack_progress.setTextVisible(True)
        self.pack_progress.setFixedHeight(18)
        pack_layout.addWidget(self.pack_progress)

        self.pack_file_lbl = QLabel("正在准备数据压缩...")
        self.pack_file_lbl.setAlignment(Qt.AlignCenter)
        self.pack_file_lbl.setStyleSheet("color: palette(placeholder-text);")
        pack_layout.addWidget(self.pack_file_lbl)

        self.stack.addWidget(self.pack_page)

        # Page 1: Channels Tab Page
        self.tabs_page = QWidget()
        tabs_layout = QVBoxLayout(self.tabs_page)
        tabs_layout.setContentsMargins(0, 0, 0, 0)
        tabs_layout.setSpacing(0)

        self.tabs = QTabWidget()
        tabs_layout.addWidget(self.tabs)
        self.stack.addWidget(self.tabs_page)

        layout.addWidget(self.stack, 1)

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

        self.status_box = QLabel("正在初始化服务...")
        bottom_row.addWidget(self.status_box, 1)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Close)
        self.button_box.rejected.connect(self.close)
        bottom_row.addWidget(self.button_box)

        layout.addLayout(bottom_row)

    def _start_packaging(self):
        project = QgsProject.instance()
        if not project.fileName():
            return

        if project.isDirty():
            project.write()

        project_path = project.fileName()
        project_dir = os.path.normpath(os.path.dirname(project_path))
        project_name = project.baseName() or "qfield_project"

        # Safe main thread metadata pre-check
        external_layers = ProjectPackager.check_external_layers(project)
        dist_dir = tempfile.mkdtemp(prefix="qfield_drop_")
        zip_filename = f"{project_name}.zip"

        self.btn_refresh.setEnabled(False)
        self.meta_lbl.setText("正在打包工程中，请稍候...")
        self.pack_status_lbl.setText("正在整理工程图层与依赖文件...")
        self.pack_progress.setRange(0, 0)
        self.pack_file_lbl.setText("正在扫描工程目录...")
        self.status_box.setText("正在后台异步打包工程数据，主界面保持流畅响应...")
        self.stack.setCurrentIndex(0)

        self.pkg_worker = PackageWorker(project_dir, dist_dir, zip_filename, project_name, external_layers)
        self.pkg_worker.progress_signal.connect(self._on_pack_progress)
        self.pkg_worker.finished_signal.connect(self._on_pack_finished)
        self.pkg_worker.start()

    def _on_pack_progress(self, current: int, total: int, rel_path: str):
        if total > 0:
            self.pack_progress.setRange(0, total)
            self.pack_progress.setValue(current)
            pct = int((current / total) * 100)
            self.pack_status_lbl.setText(f"正在打包数据文件 ({current}/{total}) - {pct}%")
        self.pack_file_lbl.setText(f"压缩中: {rel_path}")

    def _on_pack_finished(self, success: bool, pkg_info: dict, err_msg: str):
        self.btn_refresh.setEnabled(True)

        if not success:
            self.pack_status_lbl.setText(f"打包失败: {err_msg}")
            self.status_box.setText("打包失败")
            if not self._cleaned_up:
                QMessageBox.critical(self, "打包失败", f"打包工程出现错误：\n{err_msg}")
            return

        self.pkg_info = pkg_info
        self.dist_dir = pkg_info['dist_dir']

        # Update Top Info Bar
        proj_name = self.pkg_info.get('project_name', '工程')
        size_bytes = self.pkg_info.get('size_bytes', 0)
        size_mb = size_bytes / (1024 * 1024)
        file_count = self.pkg_info.get('file_count', 0)
        self.meta_lbl.setText(
            f"工程名: <b>{proj_name}</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"压缩包大小: <b>{size_mb:.2f} MB</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"包含文件: <b>{file_count} 个</b>"
        )

        ext_count = len(self.pkg_info.get('external_layers', []))
        self.btn_warn.setText(f"{ext_count} 个外部图层")
        self.btn_warn.setVisible(ext_count > 0)

        # Start or update server
        is_first_init = (self.server is None)
        self._init_server()

        if is_first_init:
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

            if 0 <= self.initial_tab < self.tabs.count():
                self.tabs.setCurrentIndex(self.initial_tab)
                if self.initial_tab == 1 and hasattr(self, 'tab_localsend'):
                    self.tab_localsend.start_scan()

            self.tabs.currentChanged.connect(self._on_tab_changed)
        else:
            self.tab_qr.update_port_and_file(self.port, self.pkg_info['zip_filename'])
            self.tab_localsend.update_package(self.pkg_info['zip_path'], self.pkg_info['zip_filename'])

        # Switch to Tabs page
        self.stack.setCurrentIndex(1)
        self.status_box.setText(f"投送服务已就绪，正在监听局域网端口 :{self.port}")

    def _init_server(self):
        if not self.pkg_info:
            return

        if self.server and self.server.is_running:
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

    def _on_tab_changed(self, idx: int):
        if idx == 1 and hasattr(self, 'tab_localsend') and self.tab_localsend:
            if not getattr(self.tab_localsend, 'has_scanned', False):
                self.tab_localsend.start_scan()

    def _on_ip_changed(self, ip: str):
        if self.mdns:
            self.mdns.update_ip(ip)

    def _show_external_layers(self):
        layers = self.pkg_info.get('external_layers', [])
        dlg = ExternalLayersDialog(layers, self)
        if dlg.exec_() == QDialog.Accepted and dlg.new_pkg_info:
            if dlg.action_result == "temp_pack":
                self._apply_temp_package(dlg.new_pkg_info)
            elif dlg.action_result == "archived":
                self._repackage()

    def _apply_temp_package(self, pkg_info: dict):
        """Hot-swap active distribution payload with temporary self-contained package."""
        if self.dist_dir and os.path.exists(self.dist_dir) and self.dist_dir != pkg_info.get('dist_dir'):
            shutil.rmtree(self.dist_dir, ignore_errors=True)

        self.pkg_info = pkg_info
        self.dist_dir = pkg_info['dist_dir']

        if self.server:
            self.server.update_payload(self.dist_dir, pkg_info['zip_filename'])

        if hasattr(self, 'tab_qr') and self.tab_qr:
            self.tab_qr.update_port_and_file(self.port, pkg_info['zip_filename'])
        if hasattr(self, 'tab_localsend') and self.tab_localsend:
            self.tab_localsend.update_package(pkg_info['zip_path'], pkg_info['zip_filename'])

        if hasattr(self, 'meta_lbl') and self.meta_lbl:
            pname = self.pkg_info.get('project_name', '工程')
            smb = self.pkg_info.get('size_bytes', 0) / (1024 * 1024)
            fcnt = self.pkg_info.get('file_count', 0)
            self.meta_lbl.setText(
                f"工程名: <b>{pname}</b> &nbsp;&nbsp;|&nbsp;&nbsp; 压缩包大小: <b>{smb:.2f} MB</b> &nbsp;&nbsp;|&nbsp;&nbsp; 包含文件: <b>{fcnt} 个</b>"
            )

        if hasattr(self, 'btn_warn') and self.btn_warn:
            orig_cnt = pkg_info.get('original_external_count', len(layers_placeholder if 'layers_placeholder' in locals() else []))
            self.btn_warn.setText("外部图层已临时自包含打包")
            self.btn_warn.setIcon(get_icon("success"))
            self.btn_warn.setStyleSheet("QPushButton { color: #2e7d32; font-weight: bold; }")
            self.btn_warn.setToolTip("当前投送包已在临时沙箱中合并外部图层，手机端加载不红框，本地工程未受改动")

        self.status_box.setText("已完成外部图层临时自包含打包，分发载荷已就绪！")

    def _repackage(self):
        if self.server:
            self.server.stop()
            self.server = None

        if self.mdns:
            self.mdns.stop()
            self.mdns = None

        if self.dist_dir and os.path.exists(self.dist_dir):
            shutil.rmtree(self.dist_dir, ignore_errors=True)
            self.dist_dir = None

        self._start_packaging()

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

        if self.pkg_worker and self.pkg_worker.isRunning():
            try:
                self.pkg_worker.cancel()
                self.pkg_worker.wait(800)
            except Exception:
                pass
            self.pkg_worker = None

        try:
            if hasattr(self, 'tab_localsend') and self.tab_localsend:
                self.tab_localsend.stop()
        except (RuntimeError, AttributeError):
            pass

        try:
            if self.mdns:
                self.mdns.stop()
                self.mdns = None
        except (RuntimeError, AttributeError, OSError):
            pass

        try:
            if self.server:
                self.server.stop()
                self.server = None
        except (RuntimeError, AttributeError, OSError):
            pass

        try:
            if self.dist_dir and os.path.exists(self.dist_dir):
                shutil.rmtree(self.dist_dir, ignore_errors=True)
                self.dist_dir = None
        except (shutil.Error, OSError):
            pass

    def closeEvent(self, event):
        self._cleanup()
        event.accept()
        super().closeEvent(event)

    def reject(self):
        self._cleanup()
        super().reject()
