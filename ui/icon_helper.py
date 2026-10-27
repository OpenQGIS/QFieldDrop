# -*- coding: utf-8 -*-
"""
QField LAN Drop - Icon Helper
Utility to load sharp Keyline SVG icons from the icons/ and icon/ directories.
"""

import os
from qgis.PyQt.QtGui import QIcon

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ICONS_DIR = os.path.join(_BASE_DIR, "icons")
_MAIN_ICON_DIR = os.path.join(_BASE_DIR, "icon")


def get_icon(name: str) -> QIcon:
    """Load QIcon from icons/ or icon/ directory."""
    if not name.endswith(".svg"):
        name += ".svg"

    # Check icons/ first
    p1 = os.path.join(_ICONS_DIR, name)
    if os.path.exists(p1):
        return QIcon(p1)

    # Check icon/
    p2 = os.path.join(_MAIN_ICON_DIR, name)
    if os.path.exists(p2):
        return QIcon(p2)

    return QIcon()


def get_icon_path(name: str) -> str:
    """Returns absolute path to an SVG icon."""
    if not name.endswith(".svg"):
        name += ".svg"

    p1 = os.path.join(_ICONS_DIR, name)
    if os.path.exists(p1):
        return p1

    p2 = os.path.join(_MAIN_ICON_DIR, name)
    if os.path.exists(p2):
        return p2

    return ""
