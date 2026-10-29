# -*- coding: utf-8 -*-
"""
QField LAN Drop - Inbound Return Dialog (接收外业成果 - Drop In)
Native QGIS Desktop UI style:
- Dedicated exclusively to receiving field survey updates from mobile devices
- Channels: Mobile Camera Web Scan & Stream Upload / Android ADB Instant Pull
- Zero packaging overhead: Opens instantly without zipping project
"""

import os
import sys
import platform
import shutil
import zipfile
import subprocess
from datetime import datetime
from typing import Optional, List, Dict, Any

from qgis.core import QgsProject, QgsVectorLayer, QgsRasterLayer
from qgis.PyQt.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QApplication, QComboBox, QFileDialog, QDialogButtonBox,
    QTabWidget, QMenu, QAction, QSizePolicy
)
from qgis.PyQt.QtGui import QKeySequence
from qgis.PyQt.QtWidgets import QShortcut
from qgis.PyQt.QtCore import Qt, pyqtSignal, QThread

from ..core.net_server import LanDropServer, NetworkHelper
from ..core.qr_native import generate_qr_matrix, render_qr_to_qpixmap
from ..core.adb_pusher import AdbPusher
from .icon_helper import get_icon, get_icon_path

ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter if hasattr(Qt, 'AlignmentFlag') else Qt.AlignCenter


class ElidedLabel(QLabel):
    """A QLabel that automatically elides middle text when overflowing its layout width."""
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._full_text = text
        self.setToolTip(text)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setWordWrap(False)

    def setText(self, text):
        self._full_text = text
        self.setToolTip(text)
        self._update_elided()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elided()

    def showEvent(self, event):
        super().showEvent(event)
        self._update_elided()

    def _update_elided(self):
        if not self._full_text:
            super().setText("")
            return
        metrics = self.fontMetrics()
        avail_w = max(10, self.width() - 4)
        elided = metrics.elidedText(self._full_text, Qt.ElideMiddle, avail_w)
        super().setText(elided)


class AdbPullWorker(QThread):
    finished_signal = pyqtSignal(bool, str, str, str)  # (success, msg, saved_path, dest_dir)

    def __init__(self, project_name: str, dest_dir: str, serial: str):
        super().__init__()
        self.project_name = project_name
        self.dest_dir = dest_dir
        self.serial = serial

    def run(self):
        try:
            success, msg, saved_path = AdbPusher.pull_project(
                self.project_name, self.dest_dir, device_serial=self.serial
            )
            self.finished_signal.emit(success, msg, saved_path, self.dest_dir)
        except Exception as e:
            self.finished_signal.emit(False, str(e), "", self.dest_dir)


class UnzipWorker(QThread):
    finished_signal = pyqtSignal(bool, str, str, str)  # (success, msg, extract_dir, action_tag)

    def __init__(self, zip_path: str, extract_dir: str, action_tag: str = ""):
        super().__init__()
        self.zip_path = zip_path
        self.extract_dir = extract_dir
        self.action_tag = action_tag

    def run(self):
        try:
            with zipfile.ZipFile(self.zip_path, 'r') as zf:
                zf.extractall(self.extract_dir)
            self.finished_signal.emit(True, "", self.extract_dir, self.action_tag)
        except Exception as e:
            self.finished_signal.emit(False, str(e), self.extract_dir, self.action_tag)


class AdbDetectWorker(QThread):
    finished_signal = pyqtSignal(bool, list)  # (adb_available, devices_list)

    def run(self):
        try:
            avail = AdbPusher.is_adb_available()
            devices = AdbPusher.list_devices() if avail else []
            self.finished_signal.emit(avail, devices)
        except Exception:
            self.finished_signal.emit(False, [])


class QFieldReceiveDialog(QDialog):
    """Dedicated dialog for receiving field survey updates from mobile devices."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("QField 成果接收 - 手机外业回传 (Drop In)")
        self.resize(480, 500)
        self.setModal(False)
        self.setAttribute(Qt.WA_DeleteOnClose, False)

        self._cleaned_up = False
        self.server: Optional[LanDropServer] = None
        self.port = 8899
        self.received_records: List[Dict[str, Any]] = []

        # Determine target return directory
        project = QgsProject.instance()
        self.project_name = project.baseName() or "qfield_project"
        if project.fileName():
            proj_dir = os.path.dirname(project.fileName())
            self.upload_dir = os.path.join(proj_dir, "_qfield_return")
        else:
            self.upload_dir = os.path.join(os.path.expanduser("~"), "QField_Return")

        os.makedirs(self.upload_dir, exist_ok=True)

        # 1. Start lightweight HTTP receiver server
        self._init_server()

        # 2. Build UI
        self._init_ui()

        # 3. Scan existing files in upload directory
        self._scan_existing_returns()

    def _init_server(self):
        """Starts background server listening for /upload requests."""
        import tempfile
        dummy_dist = os.path.join(tempfile.gettempdir(), "qfield_drop_recv_srv")
        os.makedirs(dummy_dist, exist_ok=True)
        self.server = LanDropServer(
            serve_dir=dummy_dist,
            zip_filename="dummy.zip",
            start_port=8899,
            upload_dir=self.upload_dir
        )
        self.port = self.server.start()
        self.server.signals.file_received.connect(self._on_file_received)
        self.server.signals.server_error.connect(self._on_server_error)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 1. Top Info Box: Project & Return Storage
        info_group = QGroupBox("成果归档配置")
        info_layout = QVBoxLayout(info_group)
        info_layout.setContentsMargins(10, 8, 10, 8)
        info_layout.setSpacing(4)

        # Row 1: Project Name
        lbl_proj = QLabel(f"关联工程: <b>{self.project_name}</b>")
        info_layout.addWidget(lbl_proj)

        # Row 2: Storage Path (Elided) + Open Button on right
        path_row = QHBoxLayout()
        path_row.setSpacing(8)

        lbl_path = ElidedLabel(f"存储目录: {self.upload_dir}")
        lbl_path.setStyleSheet("color: #475569;")
        path_row.addWidget(lbl_path, 1)

        btn_open_root = QPushButton("打开")
        btn_open_root.setIcon(get_icon("folder"))
        btn_open_root.setToolTip(f"在系统文件管理器中打开归档目录：\n{self.upload_dir}")
        btn_open_root.clicked.connect(self._open_return_root_folder)
        path_row.addWidget(btn_open_root)

        info_layout.addLayout(path_row)

        layout.addWidget(info_group)

        # 2. Main QR Inbound Return Card
        qr_group = QGroupBox("手机扫码回传")
        web_layout = QHBoxLayout(qr_group)
        web_layout.setContentsMargins(10, 10, 10, 10)
        web_layout.setSpacing(14)

        # Left Column: QR Code Image
        self.qr_label = QLabel()
        self.qr_label.setFixedSize(145, 145)
        self.qr_label.setAlignment(ALIGN_CENTER)
        self.qr_label.setStyleSheet("background-color: #FFFFFF; border: 1px solid palette(mid); border-radius: 4px;")
        web_layout.addWidget(self.qr_label, 0, Qt.AlignVCenter)

        # Right Column: Network selector + Tip + URL + Copy Button
        right_col = QVBoxLayout()
        right_col.setSpacing(6)
        right_col.setAlignment(Qt.AlignVCenter)

        # IP Selection Row
        ip_row = QHBoxLayout()
        ip_row.addWidget(QLabel("接收网卡:"))
        self.ip_combo = QComboBox()
        self.ip_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        for idx, item in enumerate(NetworkHelper.get_all_lan_ips()):
            self.ip_combo.addItem(item['label'], item['ip'])
            self.ip_combo.setItemData(idx, item.get('tooltip', item['label']), Qt.ToolTipRole)
        if self.ip_combo.count() > 0:
            self.ip_combo.setToolTip(self.ip_combo.itemData(0, Qt.ToolTipRole))
        self.ip_combo.currentIndexChanged.connect(self._on_ip_combo_changed)
        ip_row.addWidget(self.ip_combo, 1)
        right_col.addLayout(ip_row)

        qr_tip = QLabel(
            "<b>扫码回传指引:</b><br>"
            "① 手机自带相机/微信扫左侧二维码打开轻量回传页；<br>"
            "② 勾选修改后的矢量图层或现场照片，点击【立即回传】；<br>"
            "③ 电脑自动接收归档至下方列表，安全不覆盖原始工程。"
        )
        qr_tip.setWordWrap(True)
        tip_f = qr_tip.font()
        tip_f.setPointSize(max(8, tip_f.pointSize() - 1))
        qr_tip.setFont(tip_f)
        right_col.addWidget(qr_tip)

        self.url_label = QLabel()
        url_f = self.url_label.font()
        url_f.setPointSize(max(8, url_f.pointSize() - 1))
        self.url_label.setFont(url_f)
        right_col.addWidget(self.url_label)

        btn_copy_upload = QPushButton("复制回传网址")
        btn_copy_upload.setIcon(get_icon("copy"))
        btn_copy_upload.clicked.connect(self._copy_upload_url)
        right_col.addWidget(btn_copy_upload, 0, Qt.AlignLeft)

        web_layout.addLayout(right_col, 1)
        layout.addWidget(qr_group)

        # 3. Received Archives Table & Management
        group_records = QGroupBox("外业成果归档记录")
        rec_layout = QVBoxLayout(group_records)
        rec_layout.setContentsMargins(9, 8, 9, 8)
        rec_layout.setSpacing(6)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["时间", "成果文件", "大小", "回传来源"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        stretch_mode = QHeaderView.Stretch if hasattr(QHeaderView, 'Stretch') else QHeaderView.ResizeMode.Stretch
        self.table.horizontalHeader().setSectionResizeMode(1, stretch_mode)
        self.table.setFixedHeight(140)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        QShortcut(QKeySequence.Delete, self.table, self._delete_selected_record)
        rec_layout.addWidget(self.table)

        tbl_btn_row = QHBoxLayout()

        self.btn_load = QPushButton("载入至当前工程")
        self.btn_load.setIcon(get_icon("add"))
        self.btn_load.setDefault(True)
        self.btn_load.setToolTip("自动解析所选成果中的矢量或栅格图层并直接上图对比")
        self.btn_load.clicked.connect(self._load_selected_into_qgis)
        tbl_btn_row.addWidget(self.btn_load)

        btn_open_selected = QPushButton("打开所在目录")
        btn_open_selected.setIcon(get_icon("folder"))
        btn_open_selected.clicked.connect(self._open_selected_file_dir)
        tbl_btn_row.addWidget(btn_open_selected)

        self.btn_unzip = QPushButton("解压成果包")
        self.btn_unzip.setIcon(get_icon("archive"))
        self.btn_unzip.clicked.connect(self._unzip_selected_file)
        tbl_btn_row.addWidget(self.btn_unzip)

        btn_delete_selected = QPushButton("删除归档")
        btn_delete_selected.setIcon(get_icon("trash") if get_icon("trash") else get_icon("alert-triangle"))
        btn_delete_selected.setToolTip("从本地磁盘彻底删除此成果归档 (Del)")
        btn_delete_selected.clicked.connect(self._delete_selected_record)
        tbl_btn_row.addWidget(btn_delete_selected)

        tbl_btn_row.addStretch()

        rec_layout.addLayout(tbl_btn_row)
        layout.addWidget(group_records)

        # 4. Bottom Native Bar: Status & Close
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 4, 0, 0)
        self.status_icon = QLabel()
        self.status_icon.setPixmap(get_icon("info").pixmap(16, 16))
        bottom_row.addWidget(self.status_icon)

        self.status_box = QLabel(f"成果接收服务已就绪，正在监听局域网端口 :{self.port}")
        bottom_row.addWidget(self.status_box, 1)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Close)
        self.button_box.rejected.connect(self.close)
        bottom_row.addWidget(self.button_box)

        layout.addLayout(bottom_row)

        self._update_qr()

    def _on_ip_combo_changed(self):
        curr_idx = self.ip_combo.currentIndex()
        if curr_idx >= 0:
            tip = self.ip_combo.itemData(curr_idx, Qt.ToolTipRole)
            if tip:
                self.ip_combo.setToolTip(tip)
        self._update_qr()

    def _get_selected_ip(self) -> str:
        ip = self.ip_combo.currentData()
        if not ip:
            ip = self.ip_combo.currentText().split(' ')[0]
        return ip or "127.0.0.1"

    def _update_qr(self):
        import urllib.parse
        ip = self._get_selected_ip()
        proj_q = urllib.parse.quote(self.project_name) if self.project_name else ""
        query_suffix = f"?proj={proj_q}" if proj_q else ""
        self.current_upload_url = f"http://{ip}:{self.port}/upload{query_suffix}"
        if hasattr(self, 'url_label'):
            self.url_label.setText(self.current_upload_url)
        matrix = generate_qr_matrix(self.current_upload_url, ecc='Q')
        icon_path = get_icon_path("DropIn")
        pixmap = render_qr_to_qpixmap(matrix, target_size=140, margin_px=6, icon_path=icon_path)
        if pixmap and hasattr(self, 'qr_label'):
            self.qr_label.setPixmap(pixmap)

    def _copy_upload_url(self):
        QApplication.clipboard().setText(self.current_upload_url)
        QMessageBox.information(
            self,
            "复制成功",
            f"回传网址已复制至剪贴板：\n{self.current_upload_url}\n\n可在手机自带浏览器中直接打开进行上传。"
        )

    def _refresh_adb_devices(self):
        self.dev_combo.clear()
        self.dev_combo.addItem("正在检测 Android 设备...", "")
        self.btn_pull.setEnabled(False)
        self._adb_detect_worker = AdbDetectWorker()
        self._adb_detect_worker.finished_signal.connect(self._on_adb_detected)
        self._adb_detect_worker.start()

    def _on_adb_detected(self, avail: bool, devices: list):
        if getattr(self, '_cleaned_up', False):
            return
        self.dev_combo.clear()
        if not avail:
            self.dev_combo.addItem("未检测到 adb (请点击右侧配置)", "")
            self.btn_pull.setEnabled(False)
            return

        if not devices:
            self.dev_combo.addItem("未连接任何 Android 设备", "")
            self.btn_pull.setEnabled(False)
        else:
            for serial, status in devices:
                self.dev_combo.addItem(f"{serial} ({status})", serial)
            self.btn_pull.setEnabled(True)

    def _browse_custom_adb(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择本地 adb.exe 命令行工具", "", "ADB Executable (adb.exe adb);;All Files (*)"
        )
        if path and os.path.isfile(path):
            AdbPusher.set_custom_adb_path(path)
            self._refresh_adb_devices()
            QMessageBox.information(self, "配置成功", f"已成功指定 ADB 路径：\n{path}")

    def _do_adb_pull(self):
        serial = self.dev_combo.currentData()
        if not serial:
            QMessageBox.warning(self, "提示", "请选择已连接的 Android 设备！")
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_dir = os.path.join(self.upload_dir, f"ADB拉取_{ts}")
        os.makedirs(dest_dir, exist_ok=True)

        self.btn_pull.setEnabled(False)
        self.btn_pull.setText("正在从手机拉取中 (后台运行)...")

        self.adb_worker = AdbPullWorker(self.project_name, dest_dir, serial)
        self.adb_worker.finished_signal.connect(self._on_adb_pull_finished)
        self.adb_worker.start()

    def _on_adb_pull_finished(self, success: bool, msg: str, saved_path: str, dest_dir: str):
        self.btn_pull.setEnabled(True)
        self.btn_pull.setText("一键拉回手机外业成果 (ADB)")

        if success:
            file_size = self._get_path_size(saved_path)
            self.add_received_record("ADB无线", saved_path, file_size)
            reply = QMessageBox.information(
                self,
                "拉取成功",
                f"成功从手机拉回外业更新成果！\n\n保存路径:\n{saved_path}\n\n是否立即打开成果所在文件夹？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self._open_path_in_explorer(dest_dir)
        else:
            QMessageBox.warning(self, "拉取失败", f"未能从手机拉回成果:\n{msg}")

    def _on_file_received(self, client_ip: str, saved_path: str, file_size: int):
        fname = os.path.basename(saved_path)
        sz_mb = file_size / (1024 * 1024)
        self.add_received_record(f"手机直传({client_ip})", saved_path, file_size)
        self.status_box.setText(f"收到手机 [{client_ip}] 上传的成果: {fname} ({sz_mb:.2f} MB)")
        QMessageBox.information(
            self,
            "收到外业成果",
            f"成功接收来自手机 [{client_ip}] 的成果！\n\n"
            f"文件名: {fname}\n"
            f"大小: {sz_mb:.2f} MB\n"
            f"存储位置: {saved_path}\n\n"
            "已归档存入工程的 _qfield_return 目录中。"
        )

    def _on_server_error(self, err_msg: str):
        self.status_box.setText(f"服务异常: {err_msg}")

    def add_received_record(self, source: str, file_path: str, file_size: int):
        filename = os.path.basename(file_path)
        ts = datetime.now().strftime("%H:%M:%S")
        size_str = f"{file_size / (1024 * 1024):.2f} MB" if file_size >= 1024*1024 else f"{file_size / 1024:.1f} KB"

        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(ts))
        self.table.setItem(row, 1, QTableWidgetItem(filename))
        self.table.setItem(row, 2, QTableWidgetItem(size_str))
        self.table.setItem(row, 3, QTableWidgetItem(source))

        self.received_records.append({
            'source': source,
            'path': file_path,
            'filename': filename,
            'size': file_size,
            'time': ts
        })
        self.table.selectRow(row)

    def _scan_existing_returns(self):
        if not os.path.exists(self.upload_dir):
            return

        for item in sorted(os.listdir(self.upload_dir)):
            full_path = os.path.join(self.upload_dir, item)
            if item.startswith('.'):
                continue
            sz = self._get_path_size(full_path)
            src = "历史归档"
            mtime = datetime.fromtimestamp(os.path.getmtime(full_path)).strftime("%m-%d %H:%M")

            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(mtime))
            self.table.setItem(row, 1, QTableWidgetItem(item))
            sz_str = f"{sz / (1024 * 1024):.2f} MB" if sz >= 1024*1024 else f"{sz / 1024:.1f} KB"
            self.table.setItem(row, 2, QTableWidgetItem(sz_str))
            self.table.setItem(row, 3, QTableWidgetItem(src))

            self.received_records.append({
                'source': src,
                'path': full_path,
                'filename': item,
                'size': sz,
                'time': mtime
            })

    def _get_selected_record(self) -> Optional[Dict[str, Any]]:
        row = self.table.currentRow()
        if 0 <= row < len(self.received_records):
            return self.received_records[row]
        return None

    def _load_selected_into_qgis(self):
        rec = self._get_selected_record()
        if not rec:
            QMessageBox.warning(self, "提示", "请先在上方列表中选中一项成果记录！")
            return

        file_path = rec['path']
        if not os.path.exists(file_path):
            QMessageBox.critical(self, "错误", f"成果文件已被移动或删除：\n{file_path}")
            return

        # If it's a zip archive, extract in background worker first
        if file_path.lower().endswith(".zip"):
            extract_dir = os.path.join(os.path.dirname(file_path), f"extracted_{os.path.splitext(rec['filename'])[0]}")
            if not os.path.exists(extract_dir):
                self.btn_load.setEnabled(False)
                self.btn_load.setText("正在解压中...")
                self.unzip_worker = UnzipWorker(file_path, extract_dir, action_tag="load")
                self.unzip_worker.finished_signal.connect(self._on_unzip_finished)
                self.unzip_worker.start()
                return
            target_files = self._find_geodata_files(extract_dir)
        elif os.path.isdir(file_path):
            target_files = self._find_geodata_files(file_path)
        else:
            target_files = [file_path]

        self._do_add_layers_to_qgis(target_files)

    def _unzip_selected_file(self):
        rec = self._get_selected_record()
        if not rec:
            QMessageBox.warning(self, "提示", "请先在上方列表中选中一项成果记录！")
            return

        file_path = rec['path']
        if not file_path.lower().endswith(".zip"):
            QMessageBox.information(self, "提示", "所选文件不是 ZIP 压缩包，无需解压。")
            return

        extract_dir = os.path.join(os.path.dirname(file_path), f"extracted_{os.path.splitext(rec['filename'])[0]}")
        self.btn_unzip.setEnabled(False)
        self.btn_unzip.setText("正在解压...")

        self.unzip_worker = UnzipWorker(file_path, extract_dir, action_tag="open")
        self.unzip_worker.finished_signal.connect(self._on_unzip_finished)
        self.unzip_worker.start()

    def _on_unzip_finished(self, success: bool, msg: str, extract_dir: str, action_tag: str):
        self.btn_load.setEnabled(True)
        self.btn_load.setText("载入到当前工程")
        self.btn_unzip.setEnabled(True)
        self.btn_unzip.setText("解压成果包")

        if not success:
            QMessageBox.critical(self, "解压错误", f"解压过程发生异常：\n{msg}")
            return

        if action_tag == "open":
            QMessageBox.information(self, "解压成功", f"成果包已解压到：\n{extract_dir}")
            self._open_path_in_explorer(extract_dir)
        elif action_tag == "load":
            target_files = self._find_geodata_files(extract_dir)
            self._do_add_layers_to_qgis(target_files)

    def _do_add_layers_to_qgis(self, target_files: List[str]):
        if not target_files:
            QMessageBox.information(self, "未发现图层", "在所选成果中未检索到支持的地理数据图层 (.gpkg, .shp, .tif 等)。")
            return

        loaded_count = 0
        project = QgsProject.instance()
        for f in target_files:
            base_name = os.path.basename(f)
            layer_name = f"[外业回传] {os.path.splitext(base_name)[0]}"
            if f.lower().endswith(('.gpkg', '.shp', '.geojson', '.kml', '.gdb')):
                vlayer = QgsVectorLayer(f, layer_name, "ogr")
                if vlayer.isValid():
                    project.addMapLayer(vlayer)
                    loaded_count += 1
            elif f.lower().endswith(('.tif', '.tiff', '.img', '.jpg', '.png')):
                rlayer = QgsRasterLayer(f, layer_name)
                if rlayer.isValid():
                    project.addMapLayer(rlayer)
                    loaded_count += 1

        if loaded_count > 0:
            QMessageBox.information(
                self,
                "载入完成",
                f"成功将 {loaded_count} 个外业成果图层追加到当前 QGIS 画布中！\n可在图层面板中查看比对。"
            )
        else:
            QMessageBox.warning(self, "载入失败", "所选文件无法被 QGIS 正常加载。")

    def _open_selected_file_dir(self):
        rec = self._get_selected_record()
        if not rec:
            QMessageBox.warning(self, "提示", "请先在列表中选中一项记录！")
            return
        target_dir = os.path.dirname(rec['path']) if os.path.isfile(rec['path']) else rec['path']
        self._open_path_in_explorer(target_dir)

    def _open_return_root_folder(self):
        self._open_path_in_explorer(self.upload_dir)

    def _open_path_in_explorer(self, path: str):
        if not os.path.exists(path):
            return
        try:
            if os.name == 'nt':
                os.startfile(path)
            elif sys.platform == 'darwin' or platform.system() == 'Darwin':
                subprocess.Popen(['open', path])
            else:
                subprocess.Popen(['xdg-open', path])
        except (subprocess.SubprocessError, OSError):
            pass

    def _find_geodata_files(self, root_dir: str) -> List[str]:
        geo_exts = ('.gpkg', '.shp', '.tif', '.tiff', '.geojson')
        found = []
        for root, _, files in os.walk(root_dir):
            for f in files:
                if f.lower().endswith(geo_exts):
                    found.append(os.path.join(root, f))
        return found

    def _show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
        row = item.row()
        self.table.selectRow(row)
        rec = self._get_selected_record()
        if not rec:
            return

        menu = QMenu(self)
        act_load = menu.addAction(get_icon("add"), "载入至当前工程 (上图比对)")
        act_open = menu.addAction(get_icon("folder"), "在资源管理器中定位")
        act_unzip = menu.addAction(get_icon("archive"), "解压成果包")
        menu.addSeparator()
        act_del = menu.addAction(get_icon("trash") or get_icon("alert-triangle"), "删除此归档 (Del)")

        action = menu.exec_(self.table.viewport().mapToGlobal(pos))
        if action == act_load:
            self._load_selected_into_qgis()
        elif action == act_open:
            self._open_selected_file_dir()
        elif action == act_unzip:
            self._unzip_selected_file()
        elif action == act_del:
            self._delete_selected_record()

    def _delete_selected_record(self):
        rec = self._get_selected_record()
        if not rec:
            return

        fname = rec.get('filename', '')
        fpath = rec.get('path', '')

        reply = QMessageBox.question(
            self,
            "确认删除归档",
            f"确定要永久删除以下成果归档吗？\n\n"
            f"📄 文件名: {fname}\n"
            f"📁 路径: {fpath}\n\n"
            f"⚠️ 警告：该操作将直接从本地磁盘中彻底物理删除此成果，无法恢复！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            if os.path.isfile(fpath):
                os.remove(fpath)
            elif os.path.isdir(fpath):
                shutil.rmtree(fpath)

            row = self.table.currentRow()
            if 0 <= row < self.table.rowCount():
                self.table.removeRow(row)
            if rec in self.received_records:
                self.received_records.remove(rec)

            self.status_box.setText(f"已成功删除外业归档：{fname}")
        except Exception as e:
            QMessageBox.critical(self, "删除失败", f"删除归档时发生错误：\n{str(e)}")

    def _get_path_size(self, path: str) -> int:
        if os.path.isfile(path):
            return os.path.getsize(path)
        total = 0
        for root, _, files in os.walk(path):
            for f in files:
                fp = os.path.join(root, f)
                if os.path.exists(fp):
                    total += os.path.getsize(fp)
        return total

    def _cleanup(self):
        if getattr(self, '_cleaned_up', False):
            return
        self._cleaned_up = True

        # Safely detach and wait for background workers to prevent Qt fatal C++ abort:
        # "QThread: Destroyed while thread is still running"
        worker = getattr(self, '_adb_detect_worker', None)
        if worker:
            try:
                worker.finished_signal.disconnect()
            except (TypeError, RuntimeError):
                pass
            if worker.isRunning():
                worker.wait(400)
            self._adb_detect_worker = None

        e_worker = getattr(self, 'extract_worker', None)
        if e_worker:
            try:
                e_worker.finished_signal.disconnect()
            except (TypeError, RuntimeError):
                pass
            if e_worker.isRunning():
                e_worker.wait(400)
            self.extract_worker = None

        a_worker = getattr(self, 'adb_worker', None)
        if a_worker:
            try:
                a_worker.finished_signal.disconnect()
            except (TypeError, RuntimeError):
                pass
            if a_worker.isRunning():
                a_worker.wait(400)
            self.adb_worker = None

        if self.server:
            try:
                self.server.stop()
            except (RuntimeError, AttributeError, OSError):
                pass
            self.server = None

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
