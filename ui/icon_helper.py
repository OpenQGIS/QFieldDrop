# -*- coding: utf-8 -*-
"""
QField LAN Drop - Icon Helper
Utility to load native QGIS theme icons and bundled Keyline SVG icons.
"""

import os
from qgis.core import QgsApplication
from qgis.PyQt.QtGui import QIcon

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ICONS_DIR = os.path.join(_BASE_DIR, "icons")
_MAIN_ICON_DIR = os.path.join(_BASE_DIR, "icon")

# Map standard action keys to native QGIS theme icons
_QGIS_THEME_ICONS = {
    "refresh": "mActionRefresh.svg",
    "folder": "mActionFileOpen.svg",
    "file": "mActionFileSave.svg",
    "save": "mActionFileSave.svg",
    "alert-triangle": "mIconWarning.svg",
    "warning": "mIconWarning.svg",
    "success": "mIconSuccess.svg",
    "info": "mIconInfo.svg",
    "settings": "mActionOptions.svg",
    "add": "mActionAdd.svg",
}


def get_icon(name: str) -> QIcon:
    """Load native QGIS theme QIcon or fallback to bundled SVG."""
    clean_name = name.lower().replace(".svg", "")

    # 1. Prefer native QGIS theme icon if mapped
    if clean_name in _QGIS_THEME_ICONS:
        qgis_icon = QgsApplication.getThemeIcon(_QGIS_THEME_ICONS[clean_name])
        if not qgis_icon.isNull():
            return qgis_icon

    # 2. Check bundled icons/
    svg_name = f"{name}.svg" if not name.endswith(".svg") else name
    p1 = os.path.join(_ICONS_DIR, svg_name)
    if os.path.exists(p1):
        return QIcon(p1)

    # 3. Check bundled icon/
    p2 = os.path.join(_MAIN_ICON_DIR, svg_name)
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
