# -*- coding: utf-8 -*-
"""
QField LAN Drop - Tab: LocalSend Zero-Scan Auto-Discovery & Push
Discovers devices via UDP multicast (224.0.0.167:53317), Subnet Broadcast, and TCP /24 Subnet Probing.
Supports manual phone IP direct connect fallback for strict AP-isolated routers.
Native QGIS Desktop UI style.
"""

from typing import Dict, Optional
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QProgressBar, QMessageBox, QGroupBox,
    QLineEdit, QApplication
)
from qgis.PyQt.QtCore import Qt, QThread, pyqtSignal, QSettings

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
        self.settings = QSettings("QFieldDrop", "LocalSend")

        self._init_ui()
        self.start_scan()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(8, 8, 8, 8)

        # 1. Info Label
        info_lbl = QLabel(
            "<b>免扫码直推说明：</b>手机端打开 <b>LocalSend</b> App 并保持在前台，与电脑处于同一局域网下，"
            "下方将自动扫描在线手机。选择设备后点击发送即可免扫码秒传。"
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

        # Device List Widget
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

        # 3. Manual IP Direct Connect Box (Fail-Safe for AP-Isolated Wi-Fi)
        manual_group = QGroupBox("手机 IP 手动直连 (若路由器阻断了自动扫描)")
        manual_layout = QHBoxLayout(manual_group)
        manual_layout.setContentsMargins(8, 8, 8, 8)

        manual_layout.addWidget(QLabel("手机端 LocalSend 显示的 IP:"))
        self.manual_ip_edit = QLineEdit()
        saved_ip = self.settings.value("last_phone_ip", "")
        if saved_ip:
            self.manual_ip_edit.setText(saved_ip)
        else:
            local_ip = self.get_local_ip_cb()
            if local_ip and "." in local_ip:
                prefix = local_ip.rsplit('.', 1)[0] + "."
                self.manual_ip_edit.setText(prefix)
            self.manual_ip_edit.setPlaceholderText("例如 192.168.1.105")

        self.manual_ip_edit.returnPressed.connect(self._connect_manual_ip)
        manual_layout.addWidget(self.manual_ip_edit, 1)

        self.btn_manual_connect = QPushButton("连接并添加")
        self.btn_manual_connect.setIcon(get_icon("link"))
        self.btn_manual_connect.clicked.connect(self._connect_manual_ip)
        manual_layout.addWidget(self.btn_manual_connect)

        layout.addWidget(manual_group)

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
        self.status_lbl.setText("正在并发扫描局域网 LocalSend 设备 (UDP组播 + 网段探测)...")

        local_ip = self.get_local_ip_cb()
        self.discovery = LocalSendDiscovery(local_ip)
        self.discovery.signals.device_found.connect(self._on_device_found)
        self.discovery.signals.discovery_finished.connect(self._on_scan_finished)
        self.discovery.signals.status_updated.connect(self.status_lbl.setText)
        # Enable full concurrent subnet scanning alongside UDP multicast
        self.discovery.start_discovery(subnet_scan=True)

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
            self.status_lbl.setText("未搜到在线设备。若路由器开启了 AP 隔离，可在下方直接输入手机 IP 直连。")
        else:
            self.status_lbl.setText(f"扫描完毕，共发现 {count} 台局域网设备。")

    def _on_device_selected(self):
        has_sel = len(self.device_list.selectedItems()) > 0
        self.btn_send.setEnabled(has_sel)

    def _connect_manual_ip(self):
        ip = self.manual_ip_edit.text().strip()
        if not ip:
            QMessageBox.warning(self, "提示", "请输入手机端 LocalSend 显示的 IP 地址！")
            return

        port = 53317
        if ":" in ip:
            parts = ip.split(":")
            ip = parts[0].strip()
            try:
                port = int(parts[1].strip())
            except ValueError:
                port = 53317

        self.btn_manual_connect.setEnabled(False)
        self.btn_manual_connect.setText("连接中...")
        QApplication.processEvents()

        try:
            device = LocalSendDiscovery.fetch_device_info(ip, port=port, timeout=2.5)
            if device:
                self.settings.setValue("last_phone_ip", ip)
                self._on_device_found(device)
                # Select the manually added device
                for i in range(self.device_list.count()):
                    item = self.device_list.item(i)
                    if item.data(Qt.UserRole) == ip:
                        self.device_list.setCurrentItem(item)
                        break
                self.status_lbl.setText(f"成功直连手机设备：{device.alias} ({device.device_model})")
                QMessageBox.information(
                    self, "连接成功",
                    f"已成功识别目标设备：\n\n设备名: {device.alias}\n型号: {device.device_model}\nIP: {device.ip}:{device.port}\n\n已自动选中该设备，点击【推送到选中手机】即可开始直传！"
                )
            else:
                QMessageBox.warning(
                    self, "连接未响应",
                    f"无法连接到目标设备 ({ip}:{port})。\n\n排查建议：\n"
                    "1. 请确认手机已打开 LocalSend App 且处于前台（未锁屏）；\n"
                    "2. 确认手机与电脑连接的是同一个 Wi-Fi 或手机热点；\n"
                    "3. 检查手机端 LocalSend 界面首页显示的 IP 是否与输入一致。"
                )
        finally:
            self.btn_manual_connect.setEnabled(True)
            self.btn_manual_connect.setText("连接并添加")

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
            self.status_lbl.setText(f"推送未完成：{msg}")
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
