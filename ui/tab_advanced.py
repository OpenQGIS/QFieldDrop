# -*- coding: utf-8 -*-
"""
QField LAN Drop - Tab: Advanced Outbound Channels
Native QGIS Desktop UI style:
1. Android ADB Wireless/USB direct sandbox push with dynamic adb.exe resolver.
2. mDNS (Bonjour) domain direct link with one-click copy and browser test.
3. QField Mobile Companion QML plugin exporter and instant ADB installer.
"""

import os
import zipfile
import webbrowser
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QMessageBox, QFileDialog, QComboBox,
    QProgressBar, QApplication
)
from qgis.PyQt.QtCore import Qt, QThread, pyqtSignal

from ..core.adb_pusher import AdbPusher
from .icon_helper import get_icon


class InTabAdbPushWorker(QThread):
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, src_dir: str, project_name: str, device_serial: str):
        super().__init__()
        self.src_dir = src_dir
        self.project_name = project_name
        self.device_serial = device_serial

    def run(self):
        success, msg = AdbPusher.push_project(self.src_dir, self.project_name, self.device_serial)
        self.finished_signal.emit(success, msg)


class AdvancedTab(QWidget):
    def __init__(self, get_project_dir_cb, get_project_name_cb, port: int, parent=None):
        super().__init__(parent)
        self.get_project_dir_cb = get_project_dir_cb
        self.get_project_name_cb = get_project_name_cb
        self.port = port
        self.worker = None

        self._init_ui()
        self._refresh_adb_status()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)

        # 1. Android ADB Push Native GroupBox
        adb_group = QGroupBox("Android ADB 调试直推")
        adb_layout = QVBoxLayout(adb_group)
        adb_layout.setSpacing(6)
        adb_layout.setContentsMargins(9, 8, 9, 8)

        adb_desc = QLabel(
            "针对通过 USB 数据线或已开启无线调试的 Android 手机，可直接穿透系统沙盒将工程写入 QField 存储目录。"
        )
        adb_desc.setWordWrap(True)
        adb_layout.addWidget(adb_desc)

        # ADB Tool Status Banner with Native QGIS Theme Icons
        self.adb_status_box = QHBoxLayout()
        self.adb_status_box.setSpacing(6)
        
        self.adb_icon_lbl = QLabel()
        self.adb_status_box.addWidget(self.adb_icon_lbl)

        self.adb_status_lbl = QLabel()
        self.adb_status_box.addWidget(self.adb_status_lbl, 1)

        self.btn_browse_adb = QPushButton("浏览...")
        self.btn_browse_adb.setIcon(get_icon("folder"))
        self.btn_browse_adb.setToolTip("选择本地已安装的 adb.exe 可执行文件")
        self.btn_browse_adb.clicked.connect(self._browse_custom_adb)
        self.adb_status_box.addWidget(self.btn_browse_adb)

        self.btn_dl_adb = QPushButton("下载 Platform Tools...")
        self.btn_dl_adb.setIcon(get_icon("download"))
        self.btn_dl_adb.setToolTip("在浏览器中打开 Google 官方 Android SDK Platform Tools 下载页面")
        self.btn_dl_adb.clicked.connect(self._open_adb_download_site)
        self.adb_status_box.addWidget(self.btn_dl_adb)

        adb_layout.addLayout(self.adb_status_box)

        # Connected Devices Selector Row
        dev_row = QHBoxLayout()
        dev_row.addWidget(QLabel("目标手机设备:"))
        self.dev_combo = QComboBox()
        self.dev_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        dev_row.addWidget(self.dev_combo, 1)

        self.btn_refresh_dev = QPushButton("刷新")
        self.btn_refresh_dev.setIcon(get_icon("refresh"))
        self.btn_refresh_dev.setToolTip("重新扫描已连接的 USB/无线 Android 设备")
        self.btn_refresh_dev.clicked.connect(self._refresh_adb_devices)
        dev_row.addWidget(self.btn_refresh_dev)
        adb_layout.addLayout(dev_row)

        # Wireless Connect Row
        conn_row = QHBoxLayout()
        conn_row.addWidget(QLabel("无线调试地址:"))
        self.ip_edit = QLineEdit()
        self.ip_edit.setPlaceholderText("手机IP:端口 (例如 192.168.1.105:5555)")
        self.ip_edit.returnPressed.connect(self._connect_wireless)
        conn_row.addWidget(self.ip_edit, 1)

        self.btn_conn = QPushButton("连接")
        self.btn_conn.setIcon(get_icon("radio"))
        self.btn_conn.setToolTip("通过 adb connect 连接局域网无线调试手机")
        self.btn_conn.clicked.connect(self._connect_wireless)
        conn_row.addWidget(self.btn_conn)
        adb_layout.addLayout(conn_row)

        # Action Button: Push to Sandbox
        btn_push_row = QHBoxLayout()
        btn_push_row.addStretch()

        self.btn_push = QPushButton("推送工程至 QField 沙盒")
        self.btn_push.setIcon(get_icon("zap"))
        self.btn_push.setDefault(True)
        self.btn_push.clicked.connect(self._start_adb_push)
        btn_push_row.addWidget(self.btn_push)
        adb_layout.addLayout(btn_push_row)

        layout.addWidget(adb_group)

        # 2. mDNS Service Native GroupBox
        mdns_group = QGroupBox("mDNS 局域网服务发现")
        mdns_layout = QVBoxLayout(mdns_group)
        mdns_layout.setSpacing(6)
        mdns_layout.setContentsMargins(9, 8, 9, 8)

        self.mdns_url = f"http://qgis-drop.local:{self.port}/project.zip"
        mdns_desc = QLabel(
            f"局域网 Multicast DNS 广播已在后台启动。支持 Bonjour/mDNS 的设备无需输入动态 IP，可直接访问固定域名：<br>"
            f"<code>{self.mdns_url}</code>"
        )
        mdns_desc.setWordWrap(True)
        mdns_layout.addWidget(mdns_desc)

        mdns_act_row = QHBoxLayout()
        btn_copy_mdns = QPushButton("复制直链")
        btn_copy_mdns.setIcon(get_icon("copy"))
        btn_copy_mdns.setToolTip("复制固定域名工程下载地址")
        btn_copy_mdns.clicked.connect(self._copy_mdns_url)
        mdns_act_row.addWidget(btn_copy_mdns)

        btn_test_browser = QPushButton("在默认浏览器中测试下载")
        btn_test_browser.setIcon(get_icon("globe"))
        btn_test_browser.setToolTip("在当前电脑浏览器中验证 mDNS 域名与下载服务是否正常")
        btn_test_browser.clicked.connect(self._open_in_browser)
        mdns_act_row.addWidget(btn_test_browser)
        mdns_act_row.addStretch()
        mdns_layout.addLayout(mdns_act_row)

        layout.addWidget(mdns_group)

        # 3. Mobile Companion QML Plugin Native GroupBox
        qml_group = QGroupBox("QField 移动端配套插件")
        qml_layout = QVBoxLayout(qml_group)
        qml_layout.setSpacing(6)
        qml_layout.setContentsMargins(9, 8, 9, 8)

        qml_desc = QLabel(
            "若手机自带相机限制跳转自定义 URL Scheme，可将配套 QML 插件导入手机 QField，"
            "在 QField 顶部工具栏直接输入电脑地址一键拉取工程或回传成果。"
        )
        qml_desc.setWordWrap(True)
        qml_layout.addWidget(qml_desc)

        btn_qml_row = QHBoxLayout()
        btn_export = QPushButton("导出配套插件 (ZIP)...")
        btn_export.setIcon(get_icon("download"))
        btn_export.setToolTip("将 QFieldDrop 手机端协同插件打包为 zip 压缩包导出")
        btn_export.clicked.connect(self._export_companion)
        btn_qml_row.addWidget(btn_export)

        self.btn_install_via_adb = QPushButton("通过 ADB 安装至手机")
        self.btn_install_via_adb.setIcon(get_icon("zap"))
        self.btn_install_via_adb.setToolTip("通过 ADB 直接将 QML 插件写入手机 QField 插件目录")
        self.btn_install_via_adb.clicked.connect(self._install_companion_via_adb)
        btn_qml_row.addWidget(self.btn_install_via_adb)
        btn_qml_row.addStretch()
        qml_layout.addLayout(btn_qml_row)

        layout.addWidget(qml_group)
        layout.addStretch()

    def update_port(self, port: int):
        self.port = port
        self.mdns_url = f"http://qgis-drop.local:{self.port}/project.zip"

    def _refresh_adb_status(self):
        adb_path = AdbPusher.get_adb_path()
        if adb_path:
            self.adb_icon_lbl.setPixmap(get_icon("success").pixmap(16, 16))
            self.adb_status_lbl.setText(f"ADB 命令行已就绪 ({adb_path})")
            self.btn_dl_adb.hide()
            self._refresh_adb_devices()
        else:
            self.adb_icon_lbl.setPixmap(get_icon("warning").pixmap(16, 16))
            self.adb_status_lbl.setText("未检测到 adb 命令行工具 (需安装 Platform Tools)")
            self.btn_dl_adb.show()
            self.dev_combo.clear()
            self.dev_combo.addItem("未检测到 adb (请指定路径或安装)", "")
            self.btn_push.setEnabled(False)
            self.btn_push.setToolTip("当前未检测到 adb 命令行工具，请先点击【浏览...】或【下载 Platform Tools...】进行配置。")
            self.btn_conn.setEnabled(False)
            self.btn_conn.setToolTip("需要 adb 工具支持方可执行无线连接。")
            self.btn_install_via_adb.setEnabled(False)
            self.btn_install_via_adb.setToolTip("需要 adb 工具支持方可写入手机。")

    def _browse_custom_adb(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择本地 adb.exe 命令行工具", "", "ADB Executable (adb.exe adb);;All Files (*)"
        )
        if path and os.path.isfile(path):
            AdbPusher.set_custom_adb_path(path)
            self._refresh_adb_status()
            QMessageBox.information(self, "配置成功", f"已成功指定 ADB 路径：\n{path}")

    def _open_adb_download_site(self):
        webbrowser.open("https://developer.android.com/tools/releases/platform-tools")

    def _refresh_adb_devices(self):
        self.dev_combo.clear()
        if not AdbPusher.is_adb_available():
            self.dev_combo.addItem("未检测到 adb (请指定路径或安装)", "")
            self.btn_push.setEnabled(False)
            self.btn_push.setToolTip("当前未检测到 adb 命令行工具，请先点击【浏览...】或【下载 Platform Tools...】进行配置。")
            self.btn_conn.setEnabled(False)
            self.btn_conn.setToolTip("需要 adb 工具支持方可执行无线连接。")
            self.btn_install_via_adb.setEnabled(False)
            self.btn_install_via_adb.setToolTip("需要 adb 工具支持方可写入手机。")
            return

        self.btn_conn.setEnabled(True)
        self.btn_conn.setToolTip("通过 adb connect 连接局域网无线调试手机")
        devices = AdbPusher.list_devices()
        if not devices:
            self.dev_combo.addItem("未连接任何 Android 设备", "")
            self.btn_push.setEnabled(False)
            self.btn_push.setToolTip("当前未检测到已连接的 Android 设备，请使用 USB 数据线或无线调试连接手机。")
            self.btn_install_via_adb.setEnabled(False)
            self.btn_install_via_adb.setToolTip("请先连接 Android 设备后再安装配套插件。")
        else:
            for serial, status in devices:
                self.dev_combo.addItem(f"{serial} ({status})", serial)
            self.btn_push.setEnabled(True)
            self.btn_push.setToolTip("穿透沙盒，直接将工程静默写入手机 QField 内部存储目录。")
            self.btn_install_via_adb.setEnabled(True)
            self.btn_install_via_adb.setToolTip("通过 ADB 直接将 QML 插件写入手机 QField 插件目录。")

    def _connect_wireless(self):
        addr = self.ip_edit.text().strip()
        if not addr:
            QMessageBox.warning(self, "提示", "请输入手机无线调试 IP 与端口 (如 192.168.1.105:5555)！")
            return

        self.btn_conn.setEnabled(False)
        self.btn_conn.setText("连接中...")
        QApplication.processEvents()

        try:
            success, msg = AdbPusher.connect_wireless(addr)
            if success:
                self._refresh_adb_devices()
                QMessageBox.information(self, "连接成功", f"成功连接至 Android 设备：\n{addr}\n\n{msg}")
            else:
                QMessageBox.warning(self, "连接失败", f"无线调试连接失败：\n{msg}\n\n请确认：手机已在【开发者选项】中开启【无线调试】。")
        finally:
            self.btn_conn.setEnabled(True)
            self.btn_conn.setText("连接")

    def _start_adb_push(self):
        serial = self.dev_combo.currentData()
        if not serial:
            QMessageBox.warning(self, "提示", "请选择已连接的目标 Android 设备！")
            return

        project_dir = self.get_project_dir_cb()
        project_name = self.get_project_name_cb()

        if not project_dir or not os.path.exists(project_dir):
            QMessageBox.warning(self, "提示", "当前工程未保存到本地，无法执行直推！")
            return

        self.btn_push.setEnabled(False)
        self.btn_push.setText("正在推送工程至沙盒...")
        QApplication.processEvents()

        self.worker = InTabAdbPushWorker(project_dir, project_name, serial)
        self.worker.finished_signal.connect(self._on_push_finished)
        self.worker.start()

    def _on_push_finished(self, success: bool, msg: str):
        self.btn_push.setEnabled(True)
        self.btn_push.setText("推送工程至 QField 沙盒")
        if success:
            QMessageBox.information(
                self, "推送成功",
                f"工程已成功写入手机 QField 内部存储！\n\n{msg}\n\n打开手机 QField 即可直接在主页打开工程开始作业。"
            )
        else:
            QMessageBox.warning(self, "推送未完成", f"推送遇到异常：\n{msg}")

    def _copy_mdns_url(self):
        QApplication.clipboard().setText(self.mdns_url)
        QMessageBox.information(self, "复制成功", f"固定域名直达链接已复制至剪贴板：\n{self.mdns_url}")

    def _open_in_browser(self):
        webbrowser.open(self.mdns_url)

    def _export_companion(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出 QField 手机端协同插件", "qfield_drop_mobile.zip", "Zip Archive (*.zip)"
        )
        if not file_path:
            return

        companion_dir = self._find_companion_source()
        if not companion_dir:
            QMessageBox.warning(self, "错误", "未找到配套移动端插件源文件！")
            return

        try:
            with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(companion_dir):
                    for f in files:
                        full = os.path.join(root, f)
                        rel = os.path.relpath(full, companion_dir)
                        zf.write(full, arcname=rel)
            QMessageBox.information(
                self, "导出成功",
                f"移动端配套插件已保存至：\n{file_path}\n\n将其发送至手机，在 QField 菜单 -> 插件 -> 从压缩包安装即可生效。"
            )
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出过程发生错误: {str(e)}")

    def _install_companion_via_adb(self):
        serial = self.dev_combo.currentData()
        if not serial:
            QMessageBox.warning(self, "提示", "请选择已连接的目标 Android 设备！")
            return

        companion_dir = self._find_companion_source()
        if not companion_dir:
            QMessageBox.warning(self, "错误", "未找到配套移动端插件源文件！")
            return

        self.btn_install_via_adb.setEnabled(False)
        self.btn_install_via_adb.setText("正在写入手机...")
        QApplication.processEvents()

        try:
            success, msg = AdbPusher.install_plugin(companion_dir, device_serial=serial)
            if success:
                QMessageBox.information(self, "写入成功", msg)
            else:
                QMessageBox.warning(self, "写入失败", msg)
        finally:
            self.btn_install_via_adb.setEnabled(True)
            self.btn_install_via_adb.setText("通过 ADB 安装至手机")

    def _find_companion_source(self):
        plugin_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidates = [
            os.path.join(os.path.dirname(plugin_root), "QFieldDrop-Mobile"),
            os.path.join(plugin_root, "companion", "qfield_drop"),
            os.path.join(plugin_root, "companion", "qfield_lan_pull")
        ]
        for cand in candidates:
            if os.path.exists(cand) and os.path.exists(os.path.join(cand, "metadata.txt")):
                return cand
        return None
