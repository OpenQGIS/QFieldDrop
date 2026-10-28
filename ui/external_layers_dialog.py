# -*- coding: utf-8 -*-
"""
QField LAN Drop - External Layers Inspection & Storage Treemap Dialog
- Dual-view: Squarified Layer Size Treemap + External Layers Detailed Table
- Two-Action Pipeline:
  1. Priority Option: Temporary Self-contained Packaging (Option B, leaves disk untouched)
  2. Permanent Option: Archive into project's data/ folder (Option A, portabilize project)
- Native QGIS Desktop UI style.
"""

from typing import List, Dict, Any, Optional

from qgis.core import QgsProject
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QTabWidget, QMessageBox, QApplication
)
from qgis.PyQt.QtCore import Qt

from .icon_helper import get_icon
from .treemap_widget import TreeMapWidget, format_size
from ..core.packager import ProjectPackager


class ExternalLayersDialog(QDialog):
    """Dialog to inspect layer sizes via treemap and resolve external layer paths."""

    def __init__(self, external_layers: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("图层存储分析与外部数据源处理")
        self.resize(700, 480)

        self.external_layers = external_layers
        self.project = QgsProject.instance()
        self.action_result: Optional[str] = None
        self.new_pkg_info: Optional[Dict[str, Any]] = None

        # Fetch full project layer size distribution
        self.layers_distribution = ProjectPackager.get_layers_size_distribution(self.project)

        layout = QVBoxLayout(self)
        layout.setSpacing(9)
        layout.setContentsMargins(10, 10, 10, 10)

        # 1. Top Notice Banner (精简、克制、直击要点)
        ext_count = len(self.external_layers)
        self.notice_frame = QFrame()
        self.notice_frame.setStyleSheet(
            "QFrame { background-color: #FFFBEB; border: 1px solid #FDE68A; border-radius: 4px; padding: 5px 8px; }"
        )
        notice_layout = QHBoxLayout(self.notice_frame)
        notice_layout.setContentsMargins(4, 2, 4, 2)
        notice_layout.setSpacing(6)

        warn_lbl = QLabel(
            f"<font color='#B45309'><b>⚠️ 检测到 {ext_count} 个图层位于工程目录之外</b></font>"
            f"<span style='color: #78350F;'>，直接下发到手机可能无法加载。推荐使用右下方<b>【临时打包发送】</b>。</span>"
        )
        warn_lbl.setWordWrap(True)
        notice_layout.addWidget(warn_lbl)
        layout.addWidget(self.notice_frame)

        # 2. Main Tab Widget (Treemap + Table)
        self.tabs = QTabWidget()

        # Tab 0: Treemap (树状百分比图)
        self.treemap = TreeMapWidget(self)
        self.treemap.set_data(self.layers_distribution)
        self.tabs.addTab(self.treemap, get_icon("chart"), "图层体积占比树图 (Treemap)")

        # Tab 1: Detailed External Layers Table
        table_container = QGroupBox("工程外部图层明细")
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(6, 6, 6, 6)

        self.table = QTableWidget(len(self.external_layers), 4)
        self.table.setHorizontalHeaderLabels(["图层名称", "格式", "文件大小", "磁盘原始路径"])
        self.table.setAlternatingRowColors(True)
        stretch_mode = QHeaderView.Stretch if hasattr(QHeaderView, 'Stretch') else QHeaderView.ResizeMode.Stretch
        self.table.horizontalHeader().setSectionResizeMode(3, stretch_mode)

        for row, item in enumerate(self.external_layers):
            self.table.setItem(row, 0, QTableWidgetItem(item.get('name', '')))
            self.table.setItem(row, 1, QTableWidgetItem(item.get('provider', '').upper()))
            sz = item.get('size', 0)
            self.table.setItem(row, 2, QTableWidgetItem(format_size(sz)))
            self.table.setItem(row, 3, QTableWidgetItem(item.get('path', '')))

        table_layout.addWidget(self.table)
        self.tabs.addTab(table_container, get_icon("list"), f"外部图层清单 ({ext_count})")

        layout.addWidget(self.tabs, 1)

        # 3. Legend / Guidance Bar (极简一行式)
        guide_layout = QHBoxLayout()
        guide_layout.setContentsMargins(2, 0, 2, 0)
        legend_lbl = QLabel(
            "<small style='color: #64748B;'><font color='#F59E0B'>● 橙点标记</font>为外部数据源 ｜ 悬停色块可查看图层与路径详情</small>"
        )
        guide_layout.addWidget(legend_lbl)
        guide_layout.addStretch()
        layout.addLayout(guide_layout)

        # 4. Action Buttons Bar
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 4, 0, 0)
        btn_layout.setSpacing(8)

        # Close button on left
        self.btn_close = QPushButton("仅查看并关闭")
        self.btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_close)

        btn_layout.addStretch()

        # Secondary Action: Permanent Archive to Project data/
        self.btn_archive = QPushButton("📁 一键归档到工程")
        self.btn_archive.setIcon(get_icon("folder"))
        self.btn_archive.setToolTip("将外部图层物理复制到当前工程的 data/ 目录，并将本地工程修改为相对路径后保存")
        self.btn_archive.clicked.connect(self._on_archive_to_project)
        btn_layout.addWidget(self.btn_archive)

        # Primary Action: Temporary Self-contained Package (Priority)
        self.btn_temp_pack = QPushButton("⚡ 临时打包发送 (推荐)")
        self.btn_temp_pack.setIcon(get_icon("send"))
        self.btn_temp_pack.setDefault(True)
        self.btn_temp_pack.setStyleSheet(
            "QPushButton { background-color: #2563EB; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px; border: none; }"
            "QPushButton:hover { background-color: #1D4ED8; }"
            "QPushButton:pressed { background-color: #1E40AF; }"
        )
        self.btn_temp_pack.setToolTip("在后台临时沙箱中收集外部图层并重写相对路径，直接打包发送到手机，本地原始工程保持原样")
        self.btn_temp_pack.clicked.connect(self._on_temp_package)
        btn_layout.addWidget(self.btn_temp_pack)

        layout.addLayout(btn_layout)

    def _set_working_state(self, is_working: bool, text: str = ""):
        self.btn_close.setEnabled(not is_working)
        self.btn_archive.setEnabled(not is_working)
        self.btn_temp_pack.setEnabled(not is_working)
        if text:
            self.btn_temp_pack.setText(text)
        QApplication.processEvents()

    def _on_temp_package(self):
        """Execute Priority Option B: Temporary Self-contained Sandbox Packaging."""
        self._set_working_state(True, "正在临时收集外部图层并打包...")
        try:
            self.new_pkg_info = ProjectPackager.package_with_external_layers_temp(self.project)
            self.action_result = "temp_pack"
            self.accept()
        except Exception as e:
            self._set_working_state(False, "⚡ 临时打包发送 (推荐)")
            QMessageBox.critical(self, "临时打包失败", f"处理外部图层打包时出错：\n{str(e)}")

    def _on_archive_to_project(self):
        """Execute Option A: Permanent Archive into Project's data/ folder."""
        ret = QMessageBox.question(
            self,
            "确认归档",
            "该操作将执行以下步骤：\n"
            "1. 在当前工程目录下创建 'data' 文件夹；\n"
            "2. 将外部图层文件（含 Shapefile 伴随文件）复制到该文件夹；\n"
            "3. 将当前打开工程的图层数据源自动更新为相对路径并保存工程。\n\n"
            "确定要永久归档到当前工程中吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if ret != QMessageBox.Yes:
            return

        self._set_working_state(True, "正在复制文件并重写工程路径...")
        try:
            self.new_pkg_info = ProjectPackager.archive_external_layers_to_project(self.project)
            self.action_result = "archived"
            QMessageBox.information(
                self,
                "归档成功",
                "外部图层已成功整理并归档到工程的 data/ 目录下！\n工程已自动保存为自包含工程。"
            )
            self.accept()
        except Exception as e:
            self._set_working_state(False, "📁 一键归档到当前工程")
            QMessageBox.critical(self, "归档失败", f"归档外部图层时出错：\n{str(e)}")
