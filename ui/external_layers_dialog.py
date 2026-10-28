# -*- coding: utf-8 -*-
"""
QField LAN Drop - External Layers Inspection Dialog
Warns users if project layers reference files outside the project root directory.
Native QGIS Desktop UI style.
"""

from typing import List, Dict, Any
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QDialogButtonBox
)
from .icon_helper import get_icon


class ExternalLayersDialog(QDialog):
    """Sub-dialog to inspect layers whose data sources reside outside project directory."""
    def __init__(self, external_layers: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("外部图层数据源详情")
        self.resize(600, 340)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        info_lbl = QLabel(
            "<b>提示：</b>以下图层的数据源位于当前工程目录之外。<br>"
            "打包下发到手机 QField 后，由于手机端文件路径不同，这些图层可能无法加载（显示红框或丢失）。<br>"
            "<b>建议：</b>将这些文件复制或移动到工程所在文件夹（或其子文件夹）内，并在 QGIS 中重新保存后再投送。"
        )
        info_lbl.setWordWrap(True)
        layout.addWidget(info_lbl)

        group = QGroupBox("外部图层列表")
        group_layout = QVBoxLayout(group)

        table = QTableWidget(len(external_layers), 3)
        table.setHorizontalHeaderLabels(["图层名称", "数据格式", "磁盘原始路径"])
        table.setAlternatingRowColors(True)
        stretch_mode = QHeaderView.Stretch if hasattr(QHeaderView, 'Stretch') else QHeaderView.ResizeMode.Stretch
        table.horizontalHeader().setSectionResizeMode(2, stretch_mode)

        for row, item in enumerate(external_layers):
            table.setItem(row, 0, QTableWidgetItem(item.get('name', '')))
            table.setItem(row, 1, QTableWidgetItem(item.get('provider', '')))
            table.setItem(row, 2, QTableWidgetItem(item.get('path', '')))

        group_layout.addWidget(table)
        layout.addWidget(group)

        btn_box = QHBoxLayout()
        btn_box.setContentsMargins(0, 4, 0, 0)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        btn_box.addStretch()
        btn_box.addWidget(button_box)
        layout.addLayout(btn_box)
