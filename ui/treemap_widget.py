# -*- coding: utf-8 -*-
"""
QField LAN Drop - Layer Storage Treemap Widget (图层存储树状矩形树图)
Adapted and inspired by SuperLayer's treemap engine:
- Squarified treemap layout algorithm (Bruls et al.)
- Reference-count based size normalization (prevents double-counting shared datasets)
- Highlights external layers visually with warning accents
- Interactive hover tooltips showing allocation, physical size and sharing status
"""

import os
from typing import List, Dict, Any, Optional

from qgis.PyQt.QtCore import Qt, QRectF, pyqtSignal as Signal, QPoint
from qgis.PyQt.QtWidgets import QWidget, QToolTip
from qgis.PyQt.QtGui import QPainter, QColor, QFont, QPen, QBrush

# Color palettes mapped by format - Soft, elegant Morandi/Tailwind tones
FORMAT_COLORS = {
    "shp": QColor("#5E8E76"),          # 柔和鼠尾草绿
    "gpkg": QColor("#787195"),         # 典雅莫兰迪灰紫 (淡雅克制，护眼不刺眼)
    "tif": QColor("#5B8C9E"),          # 雾霾青灰蓝
    "tiff": QColor("#5B8C9E"),
    "gdb": QColor("#B58652"),          # 暖赭焦糖黄
    "sqlite": QColor("#63728F"),        # 灰靛蓝
    "spatialite": QColor("#63728F"),
    "geojson": QColor("#A46C7E"),       # 干枯玫瑰豆沙
    "kml": QColor("#5A8C84"),           # 灰青色
    "kmz": QColor("#5A8C84"),
    "other": QColor("#7E8B94"),         # 中性石板灰
}


def format_size(size_in_bytes: float) -> str:
    """Formats bytes into human readable string."""
    if size_in_bytes <= 0:
        return "0 B"
    val = float(size_in_bytes)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if val < 1024.0:
            return f"{val:.2f} {unit}"
        val /= 1024.0
    return f"{val:.2f} TB"


class TreeMapNode:
    """Single layer rectangle node in the squarified treemap."""
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.name = data.get('name', '图层')
        self.layer_names: List[str] = data.get('layer_names', [self.name])
        self.layer_id = data.get('id', '')
        self.path = data.get('path', '')
        self.provider = data.get('provider', '')
        self.size = float(data.get('size', 0))
        self.physical_size = float(data.get('physical_size', self.size))
        self.reference_count = int(data.get('reference_count', 1))
        self.is_external = bool(data.get('is_external', False))
        self.rect = QRectF()

    def get_color(self) -> QColor:
        _, ext = os.path.splitext(self.path.lower())
        ext_clean = ext.lstrip('.')
        if ext_clean in FORMAT_COLORS:
            base_col = FORMAT_COLORS[ext_clean]
        else:
            base_col = FORMAT_COLORS.get(self.provider.lower(), FORMAT_COLORS["other"])
        return base_col


class TreeMapWidget(QWidget):
    """Squarified treemap widget visualizing layer size proportion."""
    nodeClicked = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumHeight(180)
        self.nodes: List[TreeMapNode] = []
        self.hovered_node: Optional[TreeMapNode] = None
        self.total_size: float = 0.0

        self.font_title = QFont()
        self.font_title.setPointSize(9)
        self.font_title.setBold(True)

        self.font_sub = QFont()
        self.font_sub.setPointSize(8)

    def set_data(self, layer_distributions: List[Dict[str, Any]]):
        """Populate widget with layer size distribution nodes."""
        self.nodes = [TreeMapNode(d) for d in layer_distributions if d.get('size', 0) > 0]
        self.total_size = sum(n.size for n in self.nodes)
        self.nodes.sort(key=lambda n: n.size, reverse=True)
        self.update_layout()
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_layout()

    def update_layout(self):
        """Compute squarified rectangles for all nodes within widget rect."""
        w = self.width() - 8
        h = self.height() - 8
        if w <= 10 or h <= 10 or not self.nodes or self.total_size <= 0:
            for n in self.nodes:
                n.rect = QRectF()
            return

        available_rect = QRectF(4, 4, w, h)
        self._squarify(self.nodes[:], [], available_rect, self.total_size)

    def _squarify(self, children: List[TreeMapNode], row: List[TreeMapNode], rect: QRectF, total_size: float):
        if not children:
            if row:
                self._layout_row(row, rect, total_size)
            return

        child = children[0]
        row_with_child = row + [child]

        if not row or self._worst_aspect_ratio(row, rect, total_size) >= self._worst_aspect_ratio(row_with_child, rect, total_size):
            self._squarify(children[1:], row_with_child, rect, total_size)
        else:
            new_rect = self._layout_row(row, rect, total_size)
            remaining_size = total_size - sum(n.size for n in row)
            self._squarify(children, [], new_rect, remaining_size)

    def _worst_aspect_ratio(self, row: List[TreeMapNode], rect: QRectF, total_size: float) -> float:
        if not row or total_size <= 0:
            return float('inf')

        is_wide = rect.width() >= rect.height()
        length = rect.width() if is_wide else rect.height()
        if length <= 0:
            return float('inf')

        row_size = sum(n.size for n in row)
        row_fraction = row_size / total_size
        extent = (rect.height() if is_wide else rect.width()) * row_fraction
        if extent <= 0:
            return float('inf')

        worst = 0.0
        for n in row:
            item_fraction = n.size / row_size if row_size > 0 else 0
            item_length = length * item_fraction
            if item_length <= 0:
                continue
            ratio = max(extent / item_length, item_length / extent)
            if ratio > worst:
                worst = ratio
        return worst

    def _layout_row(self, row: List[TreeMapNode], rect: QRectF, total_size: float) -> QRectF:
        if not row or total_size <= 0:
            return rect

        is_wide = rect.width() >= rect.height()
        length = rect.width() if is_wide else rect.height()
        row_size = sum(n.size for n in row)
        row_fraction = row_size / total_size

        if is_wide:
            extent = rect.height() * row_fraction
            x = rect.x()
            for n in row:
                item_fraction = n.size / row_size if row_size > 0 else 0
                item_width = length * item_fraction
                n.rect = QRectF(x, rect.y(), max(1.0, item_width), max(1.0, extent))
                x += item_width
            return QRectF(rect.x(), rect.y() + extent, rect.width(), max(0.0, rect.height() - extent))
        else:
            extent = rect.width() * row_fraction
            y = rect.y()
            for n in row:
                item_fraction = n.size / row_size if row_size > 0 else 0
                item_height = length * item_fraction
                n.rect = QRectF(rect.x(), y, max(1.0, extent), max(1.0, item_height))
                y += item_height
            return QRectF(rect.x() + extent, rect.y(), max(0.0, rect.width() - extent), rect.height())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if not self.nodes or self.total_size <= 0:
            painter.setPen(QColor(140, 140, 140))
            painter.drawText(self.rect(), Qt.AlignCenter, "未检测到磁盘图层数据源或图层大小为 0")
            return

        for node in self.nodes:
            r = node.rect
            if r.width() <= 1 or r.height() <= 1:
                continue

            # Node background color
            base_color = node.get_color()
            is_hover = (node == self.hovered_node)

            draw_col = base_color.lighter(115) if is_hover else base_color
            painter.setBrush(QBrush(draw_col))

            # Border styling
            if is_hover:
                pen = QPen(QColor(255, 255, 255), 2.0)
            elif node.is_external:
                pen = QPen(QColor(245, 158, 11, 210), 1.2)  # Soft amber border for external
            else:
                pen = QPen(QColor(255, 255, 255, 140), 1.0)
            painter.setPen(pen)

            # Draw cell
            painter.drawRoundedRect(r.adjusted(1, 1, -1, -1), 3.0, 3.0)

            # Draw external indicator dot in upper-right corner
            if node.is_external and r.width() > 24 and r.height() > 20:
                painter.setBrush(QBrush(QColor(245, 158, 11)))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(QPoint(int(r.right() - 8), int(r.top() + 8)), 3.5, 3.5)

            # Render text if cell is large enough
            if r.width() >= 45 and r.height() >= 26:
                painter.setPen(QColor(255, 255, 255))
                painter.setFont(self.font_title)

                pct = (node.size / self.total_size * 100.0) if self.total_size > 0 else 0
                size_str = f"{format_size(node.size)} ({pct:.1f}%)"

                avail_w = int(r.width() - 8)
                fm_t = painter.fontMetrics()
                line_h = fm_t.height()

                # Multi-layer shared dataset layout (when height permits)
                if node.reference_count > 1 and r.height() >= 56:
                    y_curr = r.y() + 4
                    painter.setFont(self.font_title)
                    max_name_lines = max(1, int((r.height() - 24) / (line_h + 1)))
                    drawn_count = 0
                    for lname in node.layer_names[:max_name_lines]:
                        elided = fm_t.elidedText(f"• {lname}", Qt.ElideRight, avail_w)
                        painter.drawText(QRectF(r.x() + 4, y_curr, avail_w, line_h), Qt.AlignLeft | Qt.AlignTop, elided)
                        y_curr += line_h + 1
                        drawn_count += 1

                    if drawn_count < len(node.layer_names):
                        rem_count = len(node.layer_names) - drawn_count
                        painter.setFont(self.font_sub)
                        painter.drawText(QRectF(r.x() + 4, y_curr, avail_w, line_h), Qt.AlignLeft | Qt.AlignTop, f"...等 {len(node.layer_names)} 个共用图层")
                        y_curr += line_h

                    # Subtitle size & count tag
                    painter.setFont(self.font_sub)
                    fm_s = painter.fontMetrics()
                    text_rect_sub = QRectF(r.x() + 4, max(y_curr, r.bottom() - fm_s.height() - 4), avail_w, fm_s.height())
                    painter.drawText(text_rect_sub, Qt.AlignLeft | Qt.AlignTop, f"{size_str} · 共用")
                else:
                    # Single layer or compact cell
                    elided_name = fm_t.elidedText(node.name, Qt.ElideRight, avail_w)
                    text_rect_name = QRectF(r.x() + 4, r.y() + 3, avail_w, line_h)
                    painter.drawText(text_rect_name, Qt.AlignLeft | Qt.AlignTop, elided_name)

                    # Subtitle line
                    if r.height() >= 44:
                        painter.setFont(self.font_sub)
                        fm_s = painter.fontMetrics()
                        text_rect_sub = QRectF(r.x() + 4, text_rect_name.bottom() + 1, avail_w, fm_s.height())
                        sub_text = size_str
                        if node.reference_count > 1:
                            sub_text += f" · {node.reference_count}图层共用"
                        painter.drawText(text_rect_sub, Qt.AlignLeft | Qt.AlignTop, sub_text)

    def mouseMoveEvent(self, event):
        pos = event.pos()
        matched = None
        for node in self.nodes:
            if node.rect.contains(pos.x(), pos.y()):
                matched = node
                break

        if matched != self.hovered_node:
            self.hovered_node = matched
            self.update()

            if matched:
                pct = (matched.size / self.total_size * 100.0) if self.total_size > 0 else 0
                tip_lines = []
                if matched.reference_count > 1:
                    fname = os.path.basename(matched.path)
                    tip_lines.append(f"<b>📁 物理数据源: {fname}</b>")
                    tip_lines.append(f"<b>🔗 共用该文件的图层 ({matched.reference_count} 个)：</b>")
                    for lname in matched.layer_names:
                        tip_lines.append(f"&nbsp;&nbsp;• <b>{lname}</b>")
                else:
                    tip_lines.append(f"<b>图层名称: {matched.name}</b>")

                tip_lines.append(f"物理大小: <b>{format_size(matched.size)}</b> (体积占比: <b>{pct:.1f}%</b>)")
                tip_lines.append(f"数据格式: {matched.provider.upper()}")

                if matched.is_external:
                    tip_lines.append(f"<font color='#ff9800'><b>● 外部数据源 (位于工程目录外)</b></font>")
                else:
                    tip_lines.append(f"<font color='#4caf50'>✓ 工程内部数据源</font>")

                tip_lines.append(f"磁盘路径: {matched.path}")
                QToolTip.showText(event.globalPos(), "<br>".join(tip_lines), self)
            else:
                QToolTip.hideText()

    def leaveEvent(self, event):
        if self.hovered_node is not None:
            self.hovered_node = None
            self.update()
        QToolTip.hideText()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.hovered_node:
            self.nodeClicked.emit(self.hovered_node.data)
