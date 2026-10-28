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
    QStackedWidget, QWidget, QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QApplication, QLineEdit
)
from qgis.PyQt.QtCore import QTimer, Qt, QThread, pyqtSignal

from ..core.net_server import LanDropServer
from ..core.packager import ProjectPackager
from ..core.mdns_server import MdnsResponder

from .tab_qr import QrDropTab
from .tab_localsend import LocalSendTab
from .treemap_widget import TreeMapWidget, format_size
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
        self.drawer: Optional[QFrame] = None
        self.treemap: Optional[TreeMapWidget] = None
        self.ext_table: Optional[QTableWidget] = None
        self.drawer_warn_pill: Optional[QLabel] = None

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
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(8)

        # === 1. Left Primary Work Area ===
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # 1. Project Info Native GroupBox (从左往右: 工程名输入框 -> 大小 -> 重新打包 -> 查看详细)
        info_group = QGroupBox("当前工程与打包信息")
        info_layout = QHBoxLayout(info_group)
        info_layout.setContentsMargins(8, 6, 8, 6)
        info_layout.setSpacing(6)

        # 1. 工程名 (默认同步工程名，支持用户自定义输入)
        lbl_pname = QLabel("工程名:")
        info_layout.addWidget(lbl_pname)

        self.project_name_edit = QLineEdit(self.project_name)
        self.project_name_edit.setToolTip("默认同步当前工程名，可自定义输入导出名称 (回车或点击【重新打包】生效)")
        self.project_name_edit.setMaximumWidth(125)
        self.project_name_edit.returnPressed.connect(self._repackage)
        info_layout.addWidget(self.project_name_edit)

        # 2. 大小 (不显示文件数量)
        self.size_lbl = QLabel("大小: 计算中...")
        self.size_lbl.setStyleSheet("color: #475569;")
        info_layout.addWidget(self.size_lbl)

        info_layout.addStretch()

        # 3. 重新打包
        self.btn_refresh = QPushButton("重新打包")
        self.btn_refresh.setIcon(get_icon("refresh"))
        self.btn_refresh.setToolTip("按当前名称与工程修改重新打包")
        self.btn_refresh.clicked.connect(self._repackage)
        self.btn_refresh.setEnabled(False)
        info_layout.addWidget(self.btn_refresh)

        # 4. 查看详细 (原收起外部，向右展开树图与外部诊断)
        self.btn_toggle_drawer = QPushButton("查看详细 ▶")
        self.btn_toggle_drawer.setIcon(get_icon("chart"))
        self.btn_toggle_drawer.setToolTip("向右展开查看图层体积占比树图与外部图层诊断")
        self.btn_toggle_drawer.clicked.connect(lambda: self._toggle_drawer(None))
        info_layout.addWidget(self.btn_toggle_drawer)

        left_layout.addWidget(info_group)

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

        left_layout.addWidget(self.stack, 1)

        # 3. Global Download Progress Bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()
        left_layout.addWidget(self.progress_bar)

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

        left_layout.addLayout(bottom_row)
        root_layout.addWidget(left_widget, 1)

        # === 2. Right Side Collapsible Inspector Drawer ===
        self._init_drawer_ui(root_layout)

    def _init_drawer_ui(self, parent_layout: QHBoxLayout):
        self.drawer = QFrame()
        self.drawer.setFixedWidth(420)
        self.drawer.setStyleSheet(
            "QFrame#inspectorDrawer { border-left: 1px solid palette(mid); background: palette(window); }"
        )
        self.drawer.setObjectName("inspectorDrawer")
        drawer_layout = QVBoxLayout(self.drawer)
        drawer_layout.setContentsMargins(8, 2, 2, 2)
        drawer_layout.setSpacing(6)

        # 1. Header
        header_row = QHBoxLayout()
        header_row.setContentsMargins(2, 2, 2, 2)

        lbl_title = QLabel("<b>📊 图层存储分析</b>")
        header_row.addWidget(lbl_title)

        self.drawer_warn_pill = QLabel()
        self.drawer_warn_pill.setStyleSheet("color: #D97706; font-size: 11px;")
        self.drawer_warn_pill.setVisible(False)
        header_row.addWidget(self.drawer_warn_pill)
        header_row.addStretch()

        btn_close_drawer = QPushButton("✕")
        btn_close_drawer.setFixedSize(22, 22)
        btn_close_drawer.setToolTip("收起侧边栏")
        btn_close_drawer.setStyleSheet(
            "QPushButton { border: none; font-size: 13px; color: #64748B; }"
            "QPushButton:hover { color: #0F172A; font-weight: bold; }"
        )
        btn_close_drawer.clicked.connect(lambda: self._toggle_drawer(False))
        header_row.addWidget(btn_close_drawer)

        drawer_layout.addLayout(header_row)

        # 2. Tabs: Treemap vs Details Table
        self.drawer_tabs = QTabWidget()

        # Tab 0: Treemap
        self.treemap = TreeMapWidget(self)
        self.drawer_tabs.addTab(self.treemap, get_icon("chart"), "体积树图")

        # Tab 1: External Layers Table
        ext_widget = QWidget()
        ext_layout = QVBoxLayout(ext_widget)
        ext_layout.setContentsMargins(4, 4, 4, 4)

        self.ext_table = QTableWidget(0, 3)
        self.ext_table.setHorizontalHeaderLabels(["图层名称", "大小", "磁盘路径"])
        self.ext_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.ext_table.setAlternatingRowColors(True)
        stretch_mode = QHeaderView.Stretch if hasattr(QHeaderView, 'Stretch') else QHeaderView.ResizeMode.Stretch
        self.ext_table.horizontalHeader().setSectionResizeMode(2, stretch_mode)
        ext_layout.addWidget(self.ext_table)
        self.drawer_tabs.addTab(ext_widget, get_icon("list"), "外部清单 (0)")

        drawer_layout.addWidget(self.drawer_tabs, 1)

        # 3. Legend / Guidance
        legend_lbl = QLabel(
            "<small style='color: #64748B;'><font color='#F59E0B'>● 橙点</font>工程外 ｜ 悬停色块查看详情</small>"
        )
        drawer_layout.addWidget(legend_lbl)

        # 4. Actions Row inside drawer
        act_row = QHBoxLayout()
        act_row.setSpacing(6)

        self.btn_drawer_archive = QPushButton("📁 一键归档")
        self.btn_drawer_archive.setIcon(get_icon("folder"))
        self.btn_drawer_archive.setToolTip("将外部图层物理复制到本工程 data/ 目录并自动更新相对路径")
        self.btn_drawer_archive.clicked.connect(self._on_drawer_archive)
        act_row.addWidget(self.btn_drawer_archive)

        self.btn_drawer_temp = QPushButton("⚡ 临时沙箱打包")
        self.btn_drawer_temp.setIcon(get_icon("send"))
        self.btn_drawer_temp.setToolTip("在后台临时沙箱中自动收集外部图层并打包，不改动电脑本地工程")
        self.btn_drawer_temp.clicked.connect(self._on_drawer_temp_pack)
        act_row.addWidget(self.btn_drawer_temp)

        drawer_layout.addLayout(act_row)

        self.drawer.setVisible(False)
        parent_layout.addWidget(self.drawer)

    def _start_packaging(self):
        project = QgsProject.instance()
        if not project.fileName():
            return

        if project.isDirty():
            project.write()

        project_path = project.fileName()
        project_dir = os.path.normpath(os.path.dirname(project_path))

        # Read custom project name from input edit if available
        if hasattr(self, 'project_name_edit') and self.project_name_edit:
            txt = self.project_name_edit.text().strip()
            if txt:
                self.project_name = txt
        project_name = self.project_name

        # Safe main thread metadata pre-check
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
        self.btn_refresh.setEnabled(True)

        if not success:
            self.pack_status_lbl.setText(f"打包失败: {err_msg}")
            self.status_box.setText("打包失败")
            if not self._cleaned_up:
                QMessageBox.critical(self, "打包失败", f"打包工程出现错误：\n{err_msg}")
            return

        self.pkg_info = pkg_info
        self.dist_dir = pkg_info['dist_dir']

        # Update Top Info Bar: 只显示 大小，不显示包含文件数
        size_bytes = self.pkg_info.get('size_bytes', 0)
        size_mb = size_bytes / (1024 * 1024)
        if hasattr(self, 'size_lbl') and self.size_lbl:
            self.size_lbl.setText(f"大小: <b>{size_mb:.2f} MB</b>")

        ext_count = len(self.pkg_info.get('external_layers', []))
        if ext_count > 0:
            self.btn_toggle_drawer.setText(f"查看详细 ({ext_count}) ▶")
            self.btn_toggle_drawer.setStyleSheet("QPushButton { font-weight: bold; color: #D97706; }")
            self.btn_toggle_drawer.setToolTip(f"检测到 {ext_count} 个外部图层，点击向右展开查看体积树图与一键归档")
        else:
            self.btn_toggle_drawer.setText("查看详细 ▶")
            self.btn_toggle_drawer.setStyleSheet("")
            self.btn_toggle_drawer.setToolTip("向右展开查看图层体积占比树图")

        self._refresh_drawer_data()
        # 默认始终保持紧凑折叠小窗口，仅在用户点击时才展开
        self._toggle_drawer(False)

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

    def _toggle_drawer(self, visible: Optional[bool] = None):
        if not self.drawer:
            return
        if visible is None:
            visible = not self.drawer.isVisible()

        self.drawer.setVisible(visible)
        ext_count = len(self.pkg_info.get('external_layers', []))

        if visible:
            self.drawer.setVisible(True)
            self.btn_toggle_drawer.setText("收起详细 ◀")
            self._refresh_drawer_data()
            self.setMinimumWidth(940)
            self.resize(940, max(self.height(), 400))
        else:
            self.drawer.setVisible(False)
            btn_txt = f"查看详细 ({ext_count}) ▶" if ext_count > 0 else "查看详细 ▶"
            self.btn_toggle_drawer.setText(btn_txt)
            self.setMinimumWidth(520)
            target_h = max(self.height(), 400)
            self.setMaximumWidth(530)
            self.adjustSize()
            self.setMaximumWidth(16777215)
            self.resize(520, target_h)

    def _refresh_drawer_data(self):
        project = QgsProject.instance()
        # 1. Update Treemap data
        if self.treemap:
            layers_dist = ProjectPackager.get_layers_size_distribution(project)
            self.treemap.set_data(layers_dist)

        # 2. Update External layers list and micro warning pill
        ext_layers = self.pkg_info.get('external_layers', [])
        ext_count = len(ext_layers)

        if self.drawer_warn_pill:
            if ext_count > 0:
                self.drawer_warn_pill.setText(f"⚠️ {ext_count} 个外部图层")
                self.drawer_warn_pill.setToolTip("数据源位于工程目录之外，手机端可能无法加载。推荐点击下方按钮一键处理。")
                self.drawer_warn_pill.setVisible(True)
            else:
                self.drawer_warn_pill.setVisible(False)

        if self.ext_table:
            self.ext_table.setRowCount(ext_count)
            for row, item in enumerate(ext_layers):
                self.ext_table.setItem(row, 0, QTableWidgetItem(item.get('name', '')))
                sz = item.get('size', 0)
                self.ext_table.setItem(row, 1, QTableWidgetItem(format_size(sz)))
                self.ext_table.setItem(row, 2, QTableWidgetItem(item.get('path', '')))

        if hasattr(self, 'drawer_tabs') and self.drawer_tabs:
            self.drawer_tabs.setTabText(1, f"外部清单 ({ext_count})")

    def _on_drawer_archive(self):
        project = QgsProject.instance()
        ext_layers = self.pkg_info.get('external_layers', [])
        if not ext_layers:
            QMessageBox.information(self, "提示", "当前工程所有图层均已位于工程目录内，无需归档。")
            return

        ret = QMessageBox.question(
            self,
            "确认归档到工程",
            f"检测到 {len(ext_layers)} 个外部图层。\n\n"
            "该操作将自动执行：\n"
            "1. 在工程目录下创建 'data' 文件夹；\n"
            "2. 将外部文件物理复制至该文件夹；\n"
            "3. 将工程图层路径更新为相对路径并保存。\n\n"
            "是否立即执行归档？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if ret != QMessageBox.Yes:
            return

        self.btn_drawer_archive.setEnabled(False)
        self.btn_drawer_archive.setText("归档中...")
        QApplication.processEvents()

        try:
            ProjectPackager.archive_external_layers_to_project(project)
            QMessageBox.information(
                self,
                "归档成功",
                "外部图层已成功整理并归档到工程的 data/ 目录下！\n工程已自动转为绿色便携工程，即将重新打包。"
            )
            self._repackage()
        except Exception as e:
            QMessageBox.critical(self, "归档失败", f"归档外部图层时出错：\n{str(e)}")
        finally:
            self.btn_drawer_archive.setEnabled(True)
            self.btn_drawer_archive.setText("📁 一键归档")

    def _on_drawer_temp_pack(self):
        project = QgsProject.instance()
        ext_layers = self.pkg_info.get('external_layers', [])
        if not ext_layers:
            QMessageBox.information(self, "提示", "当前工程所有图层均在工程目录下，无需临时沙箱收集。")
            return

        self.btn_drawer_temp.setEnabled(False)
        self.btn_drawer_temp.setText("沙箱打包中...")
        QApplication.processEvents()

        try:
            new_pkg = ProjectPackager.package_with_external_layers_temp(project)
            self._apply_temp_package(new_pkg)
            QMessageBox.information(
                self,
                "沙箱打包就绪",
                "已在临时沙箱中将外部图层全量打包！\n\n"
                "本地工程保持原样，左侧二维码与推送通道已自动更新为自包含完整包，手机端可正常加载。"
            )
            self._refresh_drawer_data()
        except Exception as e:
            QMessageBox.critical(self, "临时打包失败", f"处理外部图层打包时出错：\n{str(e)}")
        finally:
            self.btn_drawer_temp.setEnabled(True)
            self.btn_drawer_temp.setText("⚡ 临时沙箱打包")

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

        if hasattr(self, 'size_lbl') and self.size_lbl:
            smb = self.pkg_info.get('size_bytes', 0) / (1024 * 1024)
            self.size_lbl.setText(f"大小: <b>{smb:.2f} MB</b>")

        if hasattr(self, 'btn_warn') and self.btn_warn:
            orig_cnt = pkg_info.get('original_external_count', len(layers_placeholder if 'layers_placeholder' in locals() else []))
            self.btn_warn.setText("外部图层已临时自包含打包")
            self.btn_warn.setIcon(get_icon("success"))
            self.btn_warn.setStyleSheet("QPushButton { color: #2e7d32; font-weight: bold; }")
            self.btn_warn.setToolTip("当前投送包已在临时沙箱中合并外部图层，手机端加载不红框，本地工程未受改动")

        self.status_box.setText("已完成外部图层临时自包含打包，分发载荷已就绪！")

    def _repackage(self):
        if hasattr(self, 'project_name_edit') and self.project_name_edit:
            txt = self.project_name_edit.text().strip()
            if txt:
                self.project_name = txt

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
