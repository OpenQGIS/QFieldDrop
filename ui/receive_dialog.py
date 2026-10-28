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
    QTabWidget
)
from qgis.PyQt.QtCore import Qt, pyqtSignal, QThread

from ..core.net_server import LanDropServer, NetworkHelper
from ..core.qr_native import generate_qr_matrix, render_qr_to_qpixmap
from ..core.adb_pusher import AdbPusher
from .icon_helper import get_icon, get_icon_path

ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter if hasattr(Qt, 'AlignmentFlag') else Qt.AlignCenter


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


class QFieldReceiveDialog(QDialog):
    """Dedicated dialog for receiving field survey updates from mobile devices."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("QField 成果接收 - 手机外业回传 (Drop In)")
        self.resize(540, 500)
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
        self._refresh_adb_devices()

    def _init_server(self):
        """Starts background server listening for /upload requests."""
        import tempfile
        dummy_dist = tempfile.gettempdir()
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
        info_layout = QHBoxLayout(info_group)
        info_layout.setContentsMargins(9, 8, 9, 8)

        lbl_dir = QLabel(f"关联工程: <b>{self.project_name}</b> &nbsp;&nbsp;|&nbsp;&nbsp; 存储目录: <code>{self.upload_dir}</code>")
        lbl_dir.setWordWrap(True)
        info_layout.addWidget(lbl_dir, 1)

        btn_open_root = QPushButton("打开归档目录")
        btn_open_root.setIcon(get_icon("folder"))
        btn_open_root.clicked.connect(self._open_return_root_folder)
        info_layout.addWidget(btn_open_root)

        layout.addWidget(info_group)

        # 2. Native QTabWidget for Inbound Channels
        self.tabs = QTabWidget()

        # Tab 1: Mobile Scan & QField LAN Return (Two-Column Layout)
        tab_web = QWidget()
        web_layout = QHBoxLayout(tab_web)
        web_layout.setContentsMargins(10, 10, 10, 10)
        web_layout.setSpacing(14)

        # Left Column: QR Code Image
        self.qr_label = QLabel()
        self.qr_label.setFixedSize(150, 150)
        self.qr_label.setAlignment(ALIGN_CENTER)
        self.qr_label.setStyleSheet("background-color: #FFFFFF; border: 1px solid palette(mid);")
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
        for item in NetworkHelper.get_all_lan_ips():
            self.ip_combo.addItem(item['label'], item['ip'])
        self.ip_combo.currentIndexChanged.connect(self._update_qr)
        ip_row.addWidget(self.ip_combo, 1)
        right_col.addLayout(ip_row)

        qr_tip = QLabel("手机相机直接扫码，在网页选择成果极速上传；或在手机 QField 中一键回传。")
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
        right_col.addWidget(btn_copy_upload)

        web_layout.addLayout(right_col, 1)
        self.tabs.addTab(tab_web, get_icon("qr"), "无线扫码 / QField 直传")

        # Tab 2: Android ADB Pull
        tab_adb = QWidget()
        adb_layout = QVBoxLayout(tab_adb)
        adb_layout.setContentsMargins(12, 10, 12, 10)
        adb_layout.setSpacing(8)

        adb_desc = QLabel(
            "通过 USB 或无线调试连接的 Android 手机，免打开网页，直接穿透系统沙盒将 QField 最新工程与照片拉回电脑："
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

        self.btn_browse_adb = QPushButton("浏览...")
        self.btn_browse_adb.setIcon(get_icon("folder"))
        self.btn_browse_adb.clicked.connect(self._browse_custom_adb)
        dev_row.addWidget(self.btn_browse_adb)
        adb_layout.addLayout(dev_row)

        self.btn_pull = QPushButton("拉取成果至本地")
        self.btn_pull.setIcon(get_icon("download"))
        self.btn_pull.setDefault(True)
        self.btn_pull.clicked.connect(self._do_adb_pull)
        adb_layout.addWidget(self.btn_pull)

        adb_layout.addStretch()
        self.tabs.addTab(tab_adb, get_icon("zap"), "Android ADB 拉取")

        layout.addWidget(self.tabs)

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
        rec_layout.addWidget(self.table)

        tbl_btn_row = QHBoxLayout()

        btn_load_qgis = QPushButton("载入至当前工程")
        btn_load_qgis.setIcon(get_icon("add"))
        btn_load_qgis.setDefault(True)
        btn_load_qgis.setToolTip("自动解析所选成果中的矢量或栅格图层并直接上图对比")
        btn_load_qgis.clicked.connect(self._load_selected_into_qgis)
        tbl_btn_row.addWidget(btn_load_qgis)

        btn_open_selected = QPushButton("打开所在目录")
        btn_open_selected.setIcon(get_icon("folder"))
        btn_open_selected.clicked.connect(self._open_selected_file_dir)
        tbl_btn_row.addWidget(btn_open_selected)

        btn_unzip_selected = QPushButton("解压成果包")
        btn_unzip_selected.setIcon(get_icon("archive"))
        btn_unzip_selected.clicked.connect(self._unzip_selected_file)
        tbl_btn_row.addWidget(btn_unzip_selected)

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

    def _get_selected_ip(self) -> str:
        ip = self.ip_combo.currentData()
        if not ip:
            ip = self.ip_combo.currentText().split(' ')[0]
        return ip or "127.0.0.1"

    def _update_qr(self):
        ip = self._get_selected_ip()
        self.current_upload_url = f"http://{ip}:{self.port}/upload"
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
        if not AdbPusher.is_adb_available():
            self.dev_combo.addItem("未检测到 adb (请点击右侧配置)", "")
            self.btn_pull.setEnabled(False)
            return

        devices = AdbPusher.list_devices()
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
