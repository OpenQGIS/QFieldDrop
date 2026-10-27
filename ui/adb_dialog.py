# -*- coding: utf-8 -*-
"""
QField LAN Drop - Android ADB Wireless Push Dialog
Allows silent direct pushing of project files to Android QField sandbox
over USB or Wi-Fi ADB debugging.
Native QGIS Desktop UI style.
"""

import os
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QMessageBox, QTextEdit, QProgressBar, QGroupBox
)
from qgis.PyQt.QtCore import Qt, QThread, pyqtSignal

from ..core.adb_pusher import AdbPusher
from .icon_helper import get_icon


class AdbPushWorker(QThread):
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, src_dir: str, project_name: str, device_serial: str):
        super().__init__()
        self.src_dir = src_dir
        self.project_name = project_name
        self.device_serial = device_serial

    def run(self):
        success, msg = AdbPusher.push_project(self.src_dir, self.project_name, self.device_serial)
        self.finished_signal.emit(success, msg)


class AdbPushDialog(QDialog):
    def __init__(self, src_dir: str, project_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Android ADB 无线静默推送")
        self.resize(520, 380)
        self.src_dir = src_dir
        self.project_name = project_name
        self.worker = None

        self._init_ui()
        self._refresh_devices()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        info_lbl = QLabel(
            "<b>ADB 无线通道说明：</b><br>"
            "通过 Android 开发者无线调试功能，无需经过扫码与网络下载，直接将工程目录写入 QField 沙盒内部存储中。"
        )
        info_lbl.setWordWrap(True)
        layout.addWidget(info_lbl)

        # ADB Status check
        if not AdbPusher.is_adb_available():
            err_box = QLabel("未在系统环境变量 PATH 中检测到 adb 命令，请确保已安装 Android Platform Tools。")
            layout.addWidget(err_box)

        # Device Selection GroupBox
        group_dev = QGroupBox("设备连接")
        dev_box_layout = QVBoxLayout(group_dev)

        dev_layout = QHBoxLayout()
        dev_layout.addWidget(QLabel("已连接设备:"))
        self.dev_combo = QComboBox()
        self.dev_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        dev_layout.addWidget(self.dev_combo, 1)

        btn_refresh = QPushButton("刷新")
        btn_refresh.setIcon(get_icon("refresh"))
        btn_refresh.clicked.connect(self._refresh_devices)
        dev_layout.addWidget(btn_refresh)
        dev_box_layout.addLayout(dev_layout)

        # Connect Wireless
        conn_layout = QHBoxLayout()
        conn_layout.addWidget(QLabel("无线连接:"))
        self.ip_edit = QLineEdit()
        self.ip_edit.setPlaceholderText("手机IP:端口 (如 192.168.1.105:5555)")
        conn_layout.addWidget(self.ip_edit, 1)

        btn_conn = QPushButton("连接无线设备")
        btn_conn.setIcon(get_icon("radio"))
        btn_conn.clicked.connect(self._connect_wireless)
        conn_layout.addWidget(btn_conn)
        dev_box_layout.addLayout(conn_layout)

        layout.addWidget(group_dev)

        # Status / Log GroupBox
        group_log = QGroupBox("传输日志")
        log_layout = QVBoxLayout(group_log)
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setPlaceholderText("ADB 传输日志将显示在此处...")
        log_layout.addWidget(self.log_edit)
        layout.addWidget(group_log)

        # Bottom row
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()

        self.btn_push = QPushButton("一键推送至 QField 沙盒")
        self.btn_push.setIcon(get_icon("zap"))
        self.btn_push.setDefault(True)
        self.btn_push.clicked.connect(self._start_push)
        bottom_row.addWidget(self.btn_push)

        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.close)
        bottom_row.addWidget(btn_close)

        layout.addLayout(bottom_row)

    def _refresh_devices(self):
        self.dev_combo.clear()
        if not AdbPusher.is_adb_available():
            return
        devices = AdbPusher.list_devices()
        if not devices:
            self.dev_combo.addItem("未检测到已连接设备", "")
            self.btn_push.setEnabled(False)
        else:
            for serial, status in devices:
                self.dev_combo.addItem(f"{serial} ({status})", serial)
            self.btn_push.setEnabled(True)

    def _connect_wireless(self):
        addr = self.ip_edit.text().strip()
        if not addr:
            QMessageBox.warning(self, "提示", "请输入手机无线调试 IP 与端口！")
            return

        self.log_edit.append(f"正在尝试无线连接至 {addr} ...")
        success, msg = AdbPusher.connect_device(addr)
        self.log_edit.append(msg)
        if success:
            self._refresh_devices()

    def _start_push(self):
        serial = self.dev_combo.currentData()
        if not serial:
            QMessageBox.warning(self, "提示", "请选择有效的目标 Android 设备！")
            return

        self.btn_push.setEnabled(False)
        self.btn_push.setText("正在推送工程...")
        self.log_edit.append(f"开始推送工程目录到设备 [{serial}] ...")

        self.worker = AdbPushWorker(self.src_dir, self.project_name, serial)
        self.worker.finished_signal.connect(self._on_push_finished)
        self.worker.start()

    def _on_push_finished(self, success: bool, msg: str):
        self.btn_push.setEnabled(True)
        self.btn_push.setText("一键推送至 QField 沙盒")
        self.log_edit.append(msg)
        if success:
            QMessageBox.information(self, "推送成功", f"工程已成功推送到手机！\n{msg}\n可在 QField 中打开工程。")
        else:
            QMessageBox.warning(self, "推送未完成", f"推送遇到问题：\n{msg}")
