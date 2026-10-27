# -*- coding: utf-8 -*-
"""
QField LAN Drop - Tab: Return / Upload Back (外业成果回传)
Supports:
1. Mobile Web Scan & Upload: QR code pointing to http://<IP>:<PORT>/upload
2. Android ADB Wireless One-Click Pull: pulls modified project sandbox directly to PC
3. Return Package History & Actions: list of received packages, one-click open folder, extract, and inspect
Native QGIS Desktop UI style.
"""

import os
import shutil
import zipfile
import subprocess
from datetime import datetime
from typing import Optional, List, Dict, Any

from qgis.core import QgsProject
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QApplication, QComboBox, QFileDialog
)
from qgis.PyQt.QtCore import Qt, pyqtSignal

from ..core.qr_native import generate_qr_matrix, render_qr_to_qpixmap
from ..core.adb_pusher import AdbPusher
from .icon_helper import get_icon

ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter if hasattr(Qt, 'AlignmentFlag') else Qt.AlignCenter


class ReturnTab(QWidget):
    file_received_signal = pyqtSignal(str, str, int)

    def __init__(
        self,
        get_local_ip_cb,
        port: int,
        project_dir: str,
        project_name: str,
        parent=None
    ):
        super().__init__(parent)
        self.get_local_ip_cb = get_local_ip_cb
        self.port = port
        self.project_dir = project_dir
        self.project_name = project_name
        self.current_upload_url = ""
        self.received_records: List[Dict[str, Any]] = []

        self._init_ui()
        self._update_qr()
        self._refresh_adb_devices()
        self._scan_existing_returns()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(8, 8, 8, 8)

        # 1. Info Note (Native label)
        info_lbl = QLabel(
            "<b>外业成果回传说明：</b>外业采集打点或拍照完毕后，可通过手机扫码网页上传或 ADB 一键拉取，"
            "将成果无痛交回电脑，自动归档并随时载入比对。"
        )
        info_lbl.setWordWrap(True)
        layout.addWidget(info_lbl)

        # 2. Dual Channel Box (Two QGroupBoxes side by side)
        channels_box = QHBoxLayout()

        # Left Channel: Web Scan Return GroupBox
        group_web = QGroupBox("通道一：手机扫码网页回传")
        web_layout = QVBoxLayout(group_web)
        web_layout.setAlignment(ALIGN_CENTER)

        self.qr_label = QLabel()
        self.qr_label.setFixedSize(170, 170)
        self.qr_label.setAlignment(ALIGN_CENTER)
        self.qr_label.setStyleSheet("background-color: #FFFFFF; border: 1px solid #CCCCCC;")
        web_layout.addWidget(self.qr_label, 0, ALIGN_CENTER)

        qr_tip = QLabel("手机相机或浏览器扫码，在移动端直接挑选 ZIP 包或现场照片上传。")
        qr_tip.setWordWrap(True)
        qr_tip.setAlignment(ALIGN_CENTER)
        web_layout.addWidget(qr_tip)

        btn_copy_upload = QPushButton("复制回传网页链接")
        btn_copy_upload.setIcon(get_icon("copy"))
        btn_copy_upload.clicked.connect(self._copy_upload_url)
        web_layout.addWidget(btn_copy_upload)

        channels_box.addWidget(group_web, 1)

        # Right Channel: Android ADB Pull GroupBox
        group_adb = QGroupBox("通道二：Android ADB 一键拉取")
        adb_layout = QVBoxLayout(group_adb)

        adb_desc = QLabel(
            "针对已开启无线调试的手机，可直接穿透 Android 沙盒限制，"
            "瞬间拉取手机端更新后的整个工程及多媒体附件照片。"
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

        self.btn_pull = QPushButton("一键拉回手机外业成果 (ADB)")
        self.btn_pull.setIcon(get_icon("zap"))
        self.btn_pull.setDefault(True)
        self.btn_pull.clicked.connect(self._do_adb_pull)
        adb_layout.addWidget(self.btn_pull)

        adb_layout.addStretch()
        channels_box.addWidget(group_adb, 1)

        layout.addLayout(channels_box)

        # 3. Received Records GroupBox
        group_records = QGroupBox("本工程已收到的外业成果归档")
        rec_layout = QVBoxLayout(group_records)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["时间", "文件名", "大小", "来源"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        stretch_mode = QHeaderView.Stretch if hasattr(QHeaderView, 'Stretch') else QHeaderView.ResizeMode.Stretch
        self.table.horizontalHeader().setSectionResizeMode(1, stretch_mode)
        self.table.setFixedHeight(120)
        rec_layout.addWidget(self.table)

        # Action button row under table
        tbl_btn_row = QHBoxLayout()

        btn_open_selected = QPushButton("查看所选文件所在目录")
        btn_open_selected.setIcon(get_icon("folder"))
        btn_open_selected.clicked.connect(self._open_selected_file_dir)
        tbl_btn_row.addWidget(btn_open_selected)

        btn_unzip_selected = QPushButton("解压所选压缩包")
        btn_unzip_selected.setIcon(get_icon("archive"))
        btn_unzip_selected.clicked.connect(self._unzip_selected_file)
        tbl_btn_row.addWidget(btn_unzip_selected)

        tbl_btn_row.addStretch()

        btn_open_folder = QPushButton("打开回传归档总目录")
        btn_open_folder.setIcon(get_icon("folder"))
        btn_open_folder.clicked.connect(self._open_return_root_folder)
        tbl_btn_row.addWidget(btn_open_folder)

        rec_layout.addLayout(tbl_btn_row)
        layout.addWidget(group_records)

    def update_ip_and_port(self, port: int):
        self.port = port
        self._update_qr()

    def _update_qr(self):
        ip = self.get_local_ip_cb()
        self.current_upload_url = f"http://{ip}:{self.port}/upload"
        matrix = generate_qr_matrix(self.current_upload_url, ecc='M')
        pixmap = render_qr_to_qpixmap(matrix, target_size=160, border_modules=2)
        if pixmap:
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
            self.dev_combo.addItem("未检测到 adb (需安装 Platform Tools)", "")
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

    def _do_adb_pull(self):
        serial = self.dev_combo.currentData()
        if not serial:
            QMessageBox.warning(self, "提示", "请选择已连接的 Android 设备！")
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_dir = os.path.join(self.project_dir, "_qfield_return", f"ADB拉取_{ts}")
        os.makedirs(dest_dir, exist_ok=True)

        self.btn_pull.setEnabled(False)
        self.btn_pull.setText("正在从手机拉取中...")
        QApplication.processEvents()

        success, msg, saved_path = AdbPusher.pull_project(
            self.project_name, dest_dir, device_serial=serial
        )

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

    def on_file_received(self, client_ip: str, saved_path: str, file_size: int):
        """Called when a file is uploaded through the web portal."""
        self.add_received_record(f"网页({client_ip})", saved_path, file_size)

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
            'time': ts,
            'name': filename,
            'size': size_str,
            'source': source,
            'path': file_path
        })
        self.table.selectRow(row)

    def _scan_existing_returns(self):
        return_root = os.path.join(self.project_dir, "_qfield_return")
        if not os.path.exists(return_root):
            return

        for root, dirs, files in os.walk(return_root):
            for f in files:
                fpath = os.path.join(root, f)
                try:
                    sz = os.path.getsize(fpath)
                    mtime = datetime.fromtimestamp(os.path.getmtime(fpath)).strftime("%m-%d %H:%M")
                    size_str = f"{sz / (1024*1024):.2f} MB" if sz >= 1024*1024 else f"{sz / 1024:.1f} KB"

                    row = self.table.rowCount()
                    self.table.insertRow(row)
                    self.table.setItem(row, 0, QTableWidgetItem(mtime))
                    self.table.setItem(row, 1, QTableWidgetItem(f))
                    self.table.setItem(row, 2, QTableWidgetItem(size_str))
                    self.table.setItem(row, 3, QTableWidgetItem("历史归档"))

                    self.received_records.append({
                        'time': mtime,
                        'name': f,
                        'size': size_str,
                        'source': '历史归档',
                        'path': fpath
                    })
                except Exception:
                    pass

    def _open_return_root_folder(self):
        return_root = os.path.join(self.project_dir, "_qfield_return")
        os.makedirs(return_root, exist_ok=True)
        self._open_path_in_explorer(return_root)

    def _open_selected_file_dir(self):
        row = self.table.currentRow()
        if 0 <= row < len(self.received_records):
            p = self.received_records[row]['path']
            parent_dir = os.path.dirname(p)
            self._open_path_in_explorer(parent_dir)
        else:
            QMessageBox.information(self, "提示", "请先在上方列表中选中一项记录。")

    def _unzip_selected_file(self):
        row = self.table.currentRow()
        if not (0 <= row < len(self.received_records)):
            QMessageBox.information(self, "提示", "请先在列表中选中一个 ZIP 压缩包。")
            return

        p = self.received_records[row]['path']
        if not p.lower().endswith('.zip'):
            QMessageBox.warning(self, "提示", "所选文件不是 .zip 格式。")
            return

        dest = os.path.join(os.path.dirname(p), "unzipped_" + os.path.splitext(os.path.basename(p))[0])
        try:
            with zipfile.ZipFile(p, 'r') as zf:
                zf.extractall(dest)
            reply = QMessageBox.information(
                self, "解压成功", f"成果压缩包已成功解压至：\n{dest}\n\n是否打开解压后的文件夹？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self._open_path_in_explorer(dest)
        except Exception as e:
            QMessageBox.critical(self, "解压失败", f"解压过程发生异常: {str(e)}")

    def _get_path_size(self, path: str) -> int:
        if os.path.isfile(path):
            return os.path.getsize(path)
        total = 0
        for root, dirs, files in os.walk(path):
            for f in files:
                fp = os.path.join(root, f)
                total += os.path.getsize(fp)
        return total

    def _open_path_in_explorer(self, path: str):
        if os.path.exists(path):
            try:
                if os.name == 'nt':
                    os.startfile(path)
                elif os.name == 'posix':
                    subprocess.run(['open', path])
            except Exception:
                pass
