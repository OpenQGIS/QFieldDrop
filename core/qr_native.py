# -*- coding: utf-8 -*-
"""
Zero-dependency QR Code generation module.
Supports system 'qrcode' / 'segno' if installed, otherwise uses embedded pure-Python 'qrcodegen'.
Renders matrix directly to QImage / QPixmap compatible with Qt5 and Qt6.
"""

from typing import List, Optional
from qgis.PyQt.QtGui import QImage, QColor, QPainter, QPixmap
from qgis.PyQt.QtCore import Qt, QRect

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


def render_qr_to_qimage(matrix: List[List[bool]], target_size: int = 240, border_modules: int = 3) -> Optional[QImage]:
    """
    Renders the QR matrix to a high-resolution QImage with white quiet zone border.
    Uses target_size to compute integer scaling factor for crisp, sharp rendering.
    """
    if not matrix or not matrix[0]:
        return None

    matrix_size = len(matrix)
    total_modules = matrix_size + 2 * border_modules

    # Calculate optimal pixel scale
    scale = max(1, target_size // total_modules)
    pixel_size = total_modules * scale

    image = QImage(pixel_size, pixel_size, _FMT_RGB32)
    image.fill(QColor(255, 255, 255))

    painter = QPainter(image)
    try:
        painter.setPen(Qt.NoPen if hasattr(Qt, 'NoPen') else Qt.PenStyle.NoPen)
        painter.setBrush(QColor(18, 20, 24))  # Premium dark slate / black

        for r in range(matrix_size):
            for c in range(matrix_size):
                if matrix[r][c]:
                    x = (c + border_modules) * scale
                    y = (r + border_modules) * scale
                    painter.drawRect(x, y, scale, scale)
    finally:
        painter.end()

    return image


def render_qr_to_qpixmap(matrix: List[List[bool]], target_size: int = 240, border_modules: int = 3) -> Optional[QPixmap]:
    """
    Convenience method returning a QPixmap ready for QLabel.setPixmap().
    """
    img = render_qr_to_qimage(matrix, target_size, border_modules)
    if img:
        return QPixmap.fromImage(img)
    return None
