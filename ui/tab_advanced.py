# -*- coding: utf-8 -*-
"""
QField LAN Drop - Tab 3: Advanced Channels
Houses Android ADB wireless direct sandbox push, mDNS status, and QField QML companion plugin exporter.
Native QGIS Desktop UI style.
"""

import os
import zipfile
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QMessageBox, QFileDialog
)

from .adb_dialog import AdbPushDialog
from .icon_helper import get_icon


class AdvancedTab(QWidget):
    def __init__(self, get_project_dir_cb, get_project_name_cb, port: int, parent=None):
        super().__init__(parent)
        self.get_project_dir_cb = get_project_dir_cb
        self.get_project_name_cb = get_project_name_cb
        self.port = port

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(8, 8, 8, 8)

        # 1. Android ADB GroupBox
        adb_group = QGroupBox("Android ADB 无线直推")
        adb_layout = QVBoxLayout(adb_group)

        adb_desc = QLabel(
            "针对已开启【开发者无线调试】的 Android 手机，无需经过任何扫码或文件传输 App，"
            "直接由电脑端写入 QField 沙盒内部存储中。"
        )
        adb_desc.setWordWrap(True)
        adb_layout.addWidget(adb_desc)

        btn_adb_row = QHBoxLayout()
        btn_open_adb = QPushButton("打开 ADB 无线推送控制面板")
        btn_open_adb.setIcon(get_icon("zap"))
        btn_open_adb.clicked.connect(self._open_adb)
        btn_adb_row.addWidget(btn_open_adb)
        btn_adb_row.addStretch()
        adb_layout.addLayout(btn_adb_row)

        layout.addWidget(adb_group)

        # 2. mDNS Service GroupBox
        mdns_group = QGroupBox("mDNS (Bonjour) 局域网服务发现")
        mdns_layout = QVBoxLayout(mdns_group)

        mdns_desc = QLabel(
            f"后台已自动启用 Multicast DNS 广播。同一 Wi-Fi 下支持 mDNS 的移动设备可直接访问固定域名：<br>"
            f"<code>http://qgis-drop.local:{self.port}/project.zip</code><br>"
            f"无需记电脑当前分配的 IP 变动。"
        )
        mdns_desc.setWordWrap(True)
        mdns_layout.addWidget(mdns_desc)

        layout.addWidget(mdns_group)

        # 3. Mobile Companion QML Plugin GroupBox
        qml_group = QGroupBox("QField 移动端配套插件 (QML)")
        qml_layout = QVBoxLayout(qml_group)

        qml_desc = QLabel(
            "若手机自带相机限制跳转自定义 URL Scheme，可将配套 QML 插件导入手机 QField，"
            "在 QField 顶部工具栏直接输入电脑地址一键拉取工程。"
        )
        qml_desc.setWordWrap(True)
        qml_layout.addWidget(qml_desc)

        btn_qml_row = QHBoxLayout()
        btn_export = QPushButton("导出移动端配套插件 (qfield_drop_mobile.zip)")
        btn_export.setIcon(get_icon("download"))
        btn_export.clicked.connect(self._export_companion)
        btn_qml_row.addWidget(btn_export)
        btn_qml_row.addStretch()
        qml_layout.addLayout(btn_qml_row)

        layout.addWidget(qml_group)

        layout.addStretch()

    def _open_adb(self):
        project_dir = self.get_project_dir_cb()
        project_name = self.get_project_name_cb()
        dlg = AdbPushDialog(project_dir, project_name, self)
        dlg.exec_()

    def _export_companion(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出 QField 手机端协同插件", "qfield_drop_mobile.zip", "Zip Archive (*.zip)"
        )
        if not file_path:
            return

        plugin_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Check QFieldDrop-Mobile first, then bundled companion
        candidates = [
            os.path.join(os.path.dirname(plugin_root), "QFieldDrop-Mobile"),
            os.path.join(plugin_root, "companion", "qfield_drop"),
            os.path.join(plugin_root, "companion", "qfield_lan_pull")
        ]
        companion_dir = None
        for cand in candidates:
            if os.path.exists(cand) and os.path.exists(os.path.join(cand, "metadata.txt")):
                companion_dir = cand
                break

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
