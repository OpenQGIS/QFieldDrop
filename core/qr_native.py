# -*- coding: utf-8 -*-
"""
Zero-dependency QR Code generation module.
Supports system 'qrcode' / 'segno' if installed, otherwise uses embedded pure-Python 'qrcodegen'.
Renders matrix directly to QImage / QPixmap compatible with Qt5 and Qt6.
"""

import os
from typing import List, Optional
from qgis.PyQt.QtGui import QImage, QColor, QPainter, QPixmap, QPen
from qgis.PyQt.QtCore import Qt, QRect, QRectF

# Qt5 / Qt6 Format_RGB32 compatibility
if hasattr(QImage, 'Format_RGB32'):
    _FMT_RGB32 = QImage.Format_RGB32
elif hasattr(QImage, 'Format') and hasattr(QImage.Format, 'Format_RGB32'):
    _FMT_RGB32 = QImage.Format.Format_RGB32
else:
    _FMT_RGB32 = 4  # Standard Qt enum value for Format_RGB32


def generate_qr_matrix(text: str, ecc: str = 'M') -> List[List[bool]]:
    """
    Generate a 2D boolean matrix where True represents a dark module,
    and False represents a light module.
    """
    if not text:
        return []

    # 1. Try external qrcode library if available
    try:
        import qrcode
        import qrcode.constants
        ecc_map = {
            'L': qrcode.constants.ERROR_CORRECT_L,
            'M': qrcode.constants.ERROR_CORRECT_M,
            'Q': qrcode.constants.ERROR_CORRECT_Q,
            'H': qrcode.constants.ERROR_CORRECT_H,
        }
        qr = qrcode.QRCode(
            version=None,
            error_correction=ecc_map.get(ecc.upper(), qrcode.constants.ERROR_CORRECT_M),
            box_size=1,
            border=0
        )
        qr.add_data(text)
        qr.make(fit=True)
        return qr.get_matrix()
    except ImportError:
        pass

    # 2. Use embedded pure-Python qrcodegen
    from .qrcodegen import QrCode
    ecc_map = {
        'L': QrCode.Ecc.LOW,
        'M': QrCode.Ecc.MEDIUM,
        'Q': QrCode.Ecc.QUARTILE,
        'H': QrCode.Ecc.HIGH
    }
    ecc_level = ecc_map.get(ecc.upper(), QrCode.Ecc.MEDIUM)
    qr = QrCode.encode_text(text, ecc_level)
    size = qr.get_size()
    matrix = []
    for y in range(size):
        row = [qr.get_module(x, y) for x in range(size)]
        matrix.append(row)
    return matrix


def render_qr_to_qimage(
    matrix: List[List[bool]],
    target_size: int = 160,
    border_modules: int = 1,
    margin_px: Optional[int] = None,
    icon_path: Optional[str] = None
) -> Optional[QImage]:
    """
    Renders the QR matrix to an exact target_size x target_size QImage with a compact,
    clean quiet zone border and optional center logo badge.
    """
    if not matrix or not matrix[0]:
        return None

    matrix_size = len(matrix)
    if margin_px is None:
        # Default tight quiet zone: 6-8px
        margin = max(6, int(round(target_size * 0.045)))
    else:
        margin = max(2, margin_px)

    available = max(10, target_size - 2 * margin)
    mod_size = available / matrix_size

    image = QImage(target_size, target_size, _FMT_RGB32)
    image.fill(QColor(255, 255, 255))

    painter = QPainter(image)
    try:
        painter.setPen(Qt.NoPen if hasattr(Qt, 'NoPen') else Qt.PenStyle.NoPen)
        painter.setBrush(QColor(18, 20, 24))  # Premium dark slate / black

        # 1. Draw QR code modules
        for r in range(matrix_size):
            y0 = int(round(margin + r * mod_size))
            y1 = int(round(margin + (r + 1) * mod_size))
            h = y1 - y0
            for c in range(matrix_size):
                if matrix[r][c]:
                    x0 = int(round(margin + c * mod_size))
                    x1 = int(round(margin + (c + 1) * mod_size))
                    w = x1 - x0
                    painter.drawRect(x0, y0, w, h)

        # 2. Draw optional center logo badge
        if icon_path and os.path.exists(icon_path):
            painter.setRenderHint(QPainter.Antialiasing, True)
            badge_size = max(26, int(round(target_size * 0.22)))
            cx = target_size / 2.0
            cy = target_size / 2.0
            bx = cx - badge_size / 2.0
            by = cy - badge_size / 2.0

            # White rounded card background with subtle clean border
            painter.setPen(QPen(QColor(220, 224, 230), 1))
            painter.setBrush(QColor(255, 255, 255))
            radius = max(3.0, badge_size * 0.16)
            painter.drawRoundedRect(QRectF(bx, by, badge_size, badge_size), radius, radius)

            # Render SVG icon inside badge with neat inner padding & strict clipping
            try:
                from qgis.PyQt.QtSvg import QSvgRenderer
                renderer = QSvgRenderer(icon_path)
                if renderer.isValid():
                    pad = max(2.5, badge_size * 0.10)
                    icon_rect = QRectF(bx + pad, by + pad, badge_size - 2 * pad, badge_size - 2 * pad)
                    painter.save()
                    painter.setClipRect(icon_rect)
                    renderer.render(painter, icon_rect)
                    painter.restore()
            except (ImportError, RuntimeError, AttributeError):
                pass
    finally:
        painter.end()

    return image


def render_qr_to_qpixmap(
    matrix: List[List[bool]],
    target_size: int = 160,
    border_modules: int = 1,
    margin_px: Optional[int] = None,
    icon_path: Optional[str] = None
) -> Optional[QPixmap]:
    """
    Convenience method returning a QPixmap ready for QLabel.setPixmap().
    Supports optional center logo SVG via icon_path.
    """
    img = render_qr_to_qimage(matrix, target_size, border_modules, margin_px, icon_path)
    if img:
        return QPixmap.fromImage(img)
    return None
