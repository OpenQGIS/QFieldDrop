# -*- coding: utf-8 -*-
"""
QField LAN Drop - Outbound Dispatch Dialog (投送至手机 - Drop Out) [Beta Release]
Focused purely on instant LAN QR scan & DeepLink wakeup transfer.
Zero-dependency, non-blocking asynchronous packaging.
"""

import os
import shutil
import tempfile
from typing import Optional, Dict, Any

from qgis.core import QgsProject
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QPushButton, QProgressBar, QMessageBox, QDialogButtonBox,
    QStackedWidget, QWidget, QApplication, QLineEdit, QComboBox
)
from qgis.PyQt.QtCore import QTimer, Qt, QThread, pyqtSignal

from ..core.net_server import LanDropServer, NetworkHelper
from ..core.packager import ProjectPackager
from ..core.mdns_server import MdnsResponder

from .tab_qr import QrDropTab
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
    """Dedicated dialog for packaging and dispatching current QGIS project to phone via QR Code."""

    def __init__(self, parent=None, initial_tab: int = 0):
        super().__init__(parent)
        self.initial_tab = initial_tab
        self.setWindowTitle("QField 局域网直传 - 投送至手机 (Drop Out)")
        self.resize(490, 410)
        self.setMinimumSize(450, 380)
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        self._cleaned_up = False
        self.is_ready = False
        self.server: Optional[LanDropServer] = None
        self.mdns: Optional[MdnsResponder] = None
        self.dist_dir: Optional[str] = None
        self.pkg_info: Dict[str, Any] = {}
        self.port = 8899
        self.pkg_worker: Optional[PackageWorker] = None
        self.tab_qr: Optional[QrDropTab] = None
        self.ip_combo: Optional[QComboBox] = None
        self.mdns_lbl: Optional[QLabel] = None

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

        self.project_name = project.baseName() or "qfield_project"
        self.is_ready = True
        self._init_ui()
        self._start_packaging()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        # 1. Project Info Native GroupBox
        info_group = QGroupBox("当前工程与打包信息")
        info_layout = QHBoxLayout(info_group)
        info_layout.setContentsMargins(8, 6, 8, 6)
        info_layout.setSpacing(6)

        lbl_pname = QLabel("工程名:")
        info_layout.addWidget(lbl_pname)

        self.project_name_edit = QLineEdit(self.project_name)
        self.project_name_edit.setToolTip("默认同步当前工程名，可自定义输入导出名称 (回车或点击【重新打包】生效)")
        self.project_name_edit.setMaximumWidth(140)
        self.project_name_edit.returnPressed.connect(self._repackage)
        info_layout.addWidget(self.project_name_edit)

        self.size_lbl = QLabel("大小: 计算中...")
        self.size_lbl.setStyleSheet("color: #475569;")
        info_layout.addWidget(self.size_lbl)

        info_layout.addStretch()

        self.btn_refresh = QPushButton("重新打包")
        self.btn_refresh.setIcon(get_icon("refresh"))
        self.btn_refresh.setToolTip("按当前名称与工程修改重新打包")
        self.btn_refresh.clicked.connect(self._repackage)
        self.btn_refresh.setEnabled(False)
        info_layout.addWidget(self.btn_refresh)

        root_layout.addWidget(info_group)

        # 2. Central Stacked Widget: Page 0 = Packaging Progress, Page 1 = Outbound QR Page
        self.stack = QStackedWidget()

        # Page 0: Packaging Status Page
        self.pack_page = QWidget()
        pack_layout = QVBoxLayout(self.pack_page)
        pack_layout.setContentsMargins(16, 24, 16, 24)
        pack_layout.setSpacing(12)
        pack_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.pack_status_lbl = QLabel("正在整理工程图层与依赖文件...")
        self.pack_status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pack_font = self.pack_status_lbl.font()
        pack_font.setBold(True)
        self.pack_status_lbl.setFont(pack_font)
        pack_layout.addWidget(self.pack_status_lbl)

        self.pack_progress = QProgressBar()
        self.pack_progress.setRange(0, 0)
        self.pack_progress.setTextVisible(True)
        self.pack_progress.setFixedHeight(18)
        pack_layout.addWidget(self.pack_progress)

        self.pack_file_lbl = QLabel("正在准备数据压缩...")
        self.pack_file_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pack_file_lbl.setStyleSheet("color: palette(placeholder-text);")
        pack_layout.addWidget(self.pack_file_lbl)

        self.stack.addWidget(self.pack_page)

        # Page 1: QR & Network Dispatch Page
        self.qr_page = QWidget()
        qr_page_layout = QVBoxLayout(self.qr_page)
        qr_page_layout.setContentsMargins(0, 0, 0, 0)
        qr_page_layout.setSpacing(8)

        # QR Dispatch Card Container
        self.qr_card_container = QVBoxLayout()
        self.qr_card_container.setContentsMargins(0, 0, 0, 0)
        qr_page_layout.addLayout(self.qr_card_container, 1)

        # Common LAN & Network Adapter Configuration GroupBox
        self.net_group = QGroupBox("局域网与网卡配置")
        net_layout = QVBoxLayout(self.net_group)
        net_layout.setSpacing(6)
        net_layout.setContentsMargins(10, 8, 10, 8)

        ip_row = QHBoxLayout()
        ip_row.addWidget(QLabel("投送网卡:"))
        self.ip_combo = QComboBox()
        self.ip_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        for idx, item in enumerate(NetworkHelper.get_all_lan_ips()):
            self.ip_combo.addItem(item['label'], item['ip'])
            self.ip_combo.setItemData(idx, item.get('tooltip', item['label']), Qt.ItemDataRole.ToolTipRole)
        if self.ip_combo.count() > 0:
            self.ip_combo.setToolTip(self.ip_combo.itemData(0, Qt.ItemDataRole.ToolTipRole))
        self.ip_combo.currentIndexChanged.connect(self._on_ip_combo_changed)
        ip_row.addWidget(self.ip_combo, 1)

        btn_firewall = QPushButton("防火墙配置")
        btn_firewall.setIcon(get_icon("shield"))
        btn_firewall.setToolTip("复制 Windows 高级防火墙端口放行命令")
        btn_firewall.clicked.connect(self._copy_firewall_cmd)
        ip_row.addWidget(btn_firewall)
        net_layout.addLayout(ip_row)

        self.mdns_lbl = QLabel(f"局域网通用地址: <code>http://qgis-drop.local:{self.port}/project.zip</code>")
        self.mdns_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        tip_f = self.mdns_lbl.font()
        tip_f.setPointSize(max(8, tip_f.pointSize() - 1))
        self.mdns_lbl.setFont(tip_f)
        net_layout.addWidget(self.mdns_lbl)

        qr_page_layout.addWidget(self.net_group)
        self.stack.addWidget(self.qr_page)

        root_layout.addWidget(self.stack, 1)

        # 3. Global Download Progress Bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()
        root_layout.addWidget(self.progress_bar)

        # 4. Bottom Native Bar: Status on Left + QDialogButtonBox on Right
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 4, 0, 0)

        self.status_icon = QLabel()
        self.status_icon.setPixmap(get_icon("info").pixmap(16, 16))
        bottom_row.addWidget(self.status_icon)

        self.status_box = QLabel("正在初始化服务...")
        bottom_row.addWidget(self.status_box, 1)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.rejected.connect(self.close)
        bottom_row.addWidget(self.button_box)

        root_layout.addLayout(bottom_row)

    def _start_packaging(self):
        project = QgsProject.instance()
        if not project.fileName():
            return

        if project.isDirty():
            project.write()

        project_path = project.fileName()
        project_dir = os.path.normpath(os.path.dirname(project_path))

        if hasattr(self, 'project_name_edit') and self.project_name_edit:
            txt = self.project_name_edit.text().strip()
            if txt:
                self.project_name = txt

        project_name = self.project_name
        external_layers = ProjectPackager.check_external_layers(project)
        dist_dir = tempfile.mkdtemp(prefix="qfield_drop_")
        zip_filename = f"{project_name}.zip"

        self.btn_refresh.setEnabled(False)
        if hasattr(self, 'size_lbl') and self.size_lbl:
            self.size_lbl.setText("大小: 计算中...")
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
        if getattr(self, '_cleaned_up', False):
            dist = pkg_info.get('dist_dir') if isinstance(pkg_info, dict) else None
            if dist and os.path.exists(dist):
                shutil.rmtree(dist, ignore_errors=True)
            return

        self.btn_refresh.setEnabled(True)

        if not success:
            self.pack_status_lbl.setText(f"打包失败: {err_msg}")
            self.status_box.setText("打包失败")
            if not self._cleaned_up:
                QMessageBox.critical(self, "打包失败", f"打包工程出现错误：\n{err_msg}")
            return

        self.pkg_info = pkg_info
        self.dist_dir = pkg_info['dist_dir']

        size_bytes = self.pkg_info.get('size_bytes', 0)
        size_mb = size_bytes / (1024 * 1024)
        if hasattr(self, 'size_lbl') and self.size_lbl:
            self.size_lbl.setText(f"大小: <b>{size_mb:.2f} MB</b>")

        self._init_server()

        current_ip = self._get_selected_ip()
        if self.tab_qr is None:
            self.tab_qr = QrDropTab(
                port=self.port,
                zip_filename=self.pkg_info['zip_filename'],
                ip=current_ip,
                parent=self
            )
            self.qr_card_container.addWidget(self.tab_qr)
        else:
            self.tab_qr.update_port_and_file(self.port, self.pkg_info['zip_filename'], ip=current_ip)

        if hasattr(self, 'mdns_lbl') and self.mdns_lbl:
            self.mdns_lbl.setText(f"局域网通用地址: <code>http://qgis-drop.local:{self.port}/project.zip</code>")

        self.stack.setCurrentIndex(1)
        self.status_box.setText(f"投送服务已就绪，正在监听局域网端口 :{self.port}")

    def _get_selected_ip(self) -> str:
        if hasattr(self, 'ip_combo') and self.ip_combo:
            ip = self.ip_combo.currentData()
            if not ip:
                ip = self.ip_combo.currentText().split(' ')[0]
            return ip or "127.0.0.1"
        return "127.0.0.1"

    def _on_ip_combo_changed(self):
        curr_idx = self.ip_combo.currentIndex()
        if curr_idx >= 0:
            tip = self.ip_combo.itemData(curr_idx, Qt.ItemDataRole.ToolTipRole)
            if tip:
                self.ip_combo.setToolTip(tip)
        ip = self._get_selected_ip()
        if self.mdns:
            self.mdns.update_ip(ip)
        if hasattr(self, 'tab_qr') and self.tab_qr:
            self.tab_qr.set_ip(ip)

    def _copy_firewall_cmd(self):
        cmd = f'netsh advfirewall firewall add rule name="QField LAN Drop" dir=in action=allow protocol=TCP localport={self.port}'
        QApplication.clipboard().setText(cmd)
        QMessageBox.information(
            self,
            "已复制防火墙规则",
            f"若手机因电脑防火墙拦截无法访问，请以管理员身份打开 PowerShell 运行以下命令：\n\n{cmd}\n\n已自动复制至剪贴板。"
        )

    def _init_server(self):
        if not self.pkg_info:
            return

        zip_filename = self.pkg_info['zip_filename']
        if self.server and self.server.is_running:
            self.server.update_payload(self.dist_dir, zip_filename)
            return
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
        initial_ip = self._get_selected_ip()
        self.mdns = MdnsResponder("qgis-drop.local", initial_ip)
        self.mdns.start()

    def _repackage(self):
        if self.pkg_worker and self.pkg_worker.isRunning():
            self.pkg_worker.cancel()
            self.pkg_worker.wait(1500)
        self._start_packaging()

    def _on_client_connected(self, client_ip: str, user_agent: str):
        ua_summary = user_agent[:32] if user_agent else "Mobile Device"
        self.status_box.setText(f"已连接: {client_ip} ({ua_summary})")
        self.progress_bar.show()
        self.progress_bar.setValue(0)

    def _on_transfer_progress(self, sent_bytes: int, total_bytes: int):
        if total_bytes > 0:
            pct = int((sent_bytes / total_bytes) * 100)
            self.progress_bar.setValue(pct)
            self.status_box.setText(f"正在发送至手机: {pct}% ({sent_bytes // 1024}/{total_bytes // 1024} KB)")

    def _on_transfer_done(self, client_ip: str, success: bool, msg: str):
        self.progress_bar.hide()
        if success:
            self.status_box.setText("🎉 投送成功！手机端已唤醒 QField 导入工程。")
            QMessageBox.information(
                self, "投送成功",
                f"工程已成功投送至手机 ({client_ip})！\n\n手机端 QField 正在自动解压并打开工程。"
            )
        else:
            self.status_box.setText(f"发送中断: {msg}")

    def _on_server_error(self, err_msg: str):
        self.status_box.setText(f"服务异常: {err_msg}")

    def closeEvent(self, event):
        self._cleanup()
        super().closeEvent(event)

    def _cleanup(self):
        self._cleaned_up = True
        if self.pkg_worker and self.pkg_worker.isRunning():
            self.pkg_worker.cancel()
            self.pkg_worker.wait(1500)
        if self.server:
            self.server.stop()
            self.server = None
        if self.mdns:
            self.mdns.stop()
            self.mdns = None
        if self.dist_dir and os.path.exists(self.dist_dir):
            shutil.rmtree(self.dist_dir, ignore_errors=True)
            self.dist_dir = None
