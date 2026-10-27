# -*- coding: utf-8 -*-
"""
QField LAN Drop - Tab 2: LocalSend Zero-Scan Auto-Discovery & Push
Discovers devices via UDP multicast (224.0.0.167:53317) & pushes ZIP directly via REST API.
Native QGIS Desktop UI style.
"""

from typing import Dict, Optional
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QProgressBar, QMessageBox, QGroupBox
)
from qgis.PyQt.QtCore import Qt, QThread, pyqtSignal

from ..core.localsend import LocalSendDiscovery, LocalSendClient, LocalSendDevice
from .icon_helper import get_icon


class PushWorker(QThread):
    progress_signal = pyqtSignal(int, int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, device: LocalSendDevice, file_path: str, filename: str):
        super().__init__()
        self.device = device
        self.file_path = file_path
        self.filename = filename
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        def cb(sent, total):
            if not self._cancelled:
                self.progress_signal.emit(sent, total)

        success, msg = LocalSendClient.push_file(
            self.device,
            self.file_path,
            self.filename,
            progress_callback=cb,
            is_cancelled=lambda: self._cancelled
        )
        if not self._cancelled:
            self.finished_signal.emit(success, msg)


class LocalSendTab(QWidget):
    def __init__(self, get_local_ip_cb, zip_path: str, zip_filename: str, parent=None):
        super().__init__(parent)
        self.get_local_ip_cb = get_local_ip_cb
        self.zip_path = zip_path
        self.zip_filename = zip_filename
        self.discovery: Optional[LocalSendDiscovery] = None
        self.discovered_devices: Dict[str, LocalSendDevice] = {}
        self.push_worker: Optional[PushWorker] = None

        self._init_ui()
        self.start_scan()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(8, 8, 8, 8)

        # 1. Info Label (Native, no web alert container)
        info_lbl = QLabel(
            "<b>免扫码直推说明：</b>手机端安装并打开 <b>LocalSend</b> App，与电脑处于同一局域网下，"
            "下方将自动列出可用的移动设备。在列表中选择设备后点击发送，手机端确认即可接收。"
        )
        info_lbl.setWordWrap(True)
        layout.addWidget(info_lbl)

        # 2. Devices GroupBox
        group = QGroupBox("在线设备列表")
        group_layout = QVBoxLayout(group)

        # Controls & List Header
        header_row = QHBoxLayout()
        header_row.addWidget(QLabel("选择目标手机设备:"))
        header_row.addStretch()

        self.btn_refresh = QPushButton("重新扫描")
        self.btn_refresh.setIcon(get_icon("search"))
        self.btn_refresh.clicked.connect(self.start_scan)
        header_row.addWidget(self.btn_refresh)
        group_layout.addLayout(header_row)

        # Device List Widget (Native QListWidget)
        self.device_list = QListWidget()
        self.device_list.setAlternatingRowColors(True)
        self.device_list.itemSelectionChanged.connect(self._on_device_selected)
        group_layout.addWidget(self.device_list)

        # Scan Status
        self.status_lbl = QLabel("正在搜索局域网设备...")
        group_layout.addWidget(self.status_lbl)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.hide()
        group_layout.addWidget(self.progress_bar)

        # Send Button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_send = QPushButton("推送到选中手机 (免扫码)")
        self.btn_send.setIcon(get_icon("send"))
        self.btn_send.setEnabled(False)
        self.btn_send.setDefault(True)
        self.btn_send.clicked.connect(self._send_to_device)
        btn_row.addWidget(self.btn_send)
        group_layout.addLayout(btn_row)

        layout.addWidget(group)

    def update_package(self, zip_path: str, zip_filename: str):
        self.zip_path = zip_path
        self.zip_filename = zip_filename

    def start_scan(self):
        if self.discovery:
            self.discovery.stop_discovery()

        self.device_list.clear()
        self.discovered_devices.clear()
        self.btn_send.setEnabled(False)
        self.btn_refresh.setEnabled(False)
        self.status_lbl.setText("正在监听 UDP 组播 (224.0.0.167:53317)...")

        local_ip = self.get_local_ip_cb()
        self.discovery = LocalSendDiscovery(local_ip)
        self.discovery.signals.device_found.connect(self._on_device_found)
        self.discovery.signals.discovery_finished.connect(self._on_scan_finished)
        self.discovery.signals.status_updated.connect(self.status_lbl.setText)
        self.discovery.start_discovery(subnet_scan=False)

    def _on_device_found(self, device: LocalSendDevice):
        ip = device.ip
        if ip in self.discovered_devices:
            return
        self.discovered_devices[ip] = device

        icon_obj = get_icon("smartphone") if device.device_type == "mobile" else get_icon("laptop")
        item = QListWidgetItem(icon_obj, device.display_name)
        item.setData(Qt.UserRole, ip)
        self.device_list.addItem(item)
        if self.device_list.count() == 1:
            self.device_list.setCurrentRow(0)

    def _on_scan_finished(self):
        self.btn_refresh.setEnabled(True)
        count = len(self.discovered_devices)
        if count == 0:
            self.status_lbl.setText("未发现在线设备。请确认手机已打开 LocalSend 且处于同一网络。")
        else:
            self.status_lbl.setText(f"扫描完毕，共发现 {count} 台局域网设备。")

    def _on_device_selected(self):
        has_sel = len(self.device_list.selectedItems()) > 0
        self.btn_send.setEnabled(has_sel)

    def _send_to_device(self):
        selected_items = self.device_list.selectedItems()
        if not selected_items:
            return

        ip = selected_items[0].data(Qt.UserRole)
        device = self.discovered_devices.get(ip)
        if not device:
            return

        self.btn_send.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.status_lbl.setText(f"正在向 {device.alias} 发起传输请求，请在手机端确认接收...")

        self.push_worker = PushWorker(device, self.zip_path, self.zip_filename)
        self.push_worker.progress_signal.connect(self._on_push_progress)
        self.push_worker.finished_signal.connect(self._on_push_finished)
        self.push_worker.start()

    def _on_push_progress(self, sent: int, total: int):
        if total > 0:
            pct = int((sent / total) * 100)
            self.progress_bar.setValue(pct)
            sent_mb = sent / (1024 * 1024)
            tot_mb = total / (1024 * 1024)
            self.status_lbl.setText(f"正在推送: {sent_mb:.2f} MB / {tot_mb:.2f} MB ({pct}%)")

    def _on_push_finished(self, success: bool, msg: str):
        self.btn_send.setEnabled(True)
        if success:
            self.progress_bar.setValue(100)
            self.status_lbl.setText(f"推送成功：{msg}")
            QMessageBox.information(self, "推送成功", f"{msg}\n\n请在手机端使用 QField 打开该工程包。")
        else:
            self.status_lbl.setText(f"推送失败：{msg}")
            QMessageBox.warning(self, "推送未完成", msg)

    def stop(self):
        if self.discovery:
            self.discovery.stop_discovery()
            self.discovery = None
        if self.push_worker and self.push_worker.isRunning():
            self.push_worker.cancel()
            try:
                self.push_worker.progress_signal.disconnect()
                self.push_worker.finished_signal.disconnect()
            except Exception:
                pass
            self.push_worker.wait(500)
