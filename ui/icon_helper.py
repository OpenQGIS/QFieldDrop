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
    """Load bundled SVG icon from icons/ first, fallback to icon/ or QGIS theme."""
    svg_name = f"{name}.svg" if not name.endswith(".svg") else name
    clean_name = name.lower().replace(".svg", "")

    # 1. 优先读取用户升级的 icons/ 目录
    p1 = os.path.join(_ICONS_DIR, svg_name)
    if os.path.exists(p1):
        icon = QIcon(p1)
        if not icon.isNull():
            return icon

    # 2. 其次读取 bundled icon/ 目录
    p2 = os.path.join(_MAIN_ICON_DIR, svg_name)
    if os.path.exists(p2):
        icon = QIcon(p2)
        if not icon.isNull():
            return icon

    # 3. 降级回退到 QGIS 原生主题图标
    if clean_name in _QGIS_THEME_ICONS:
        qgis_icon = QgsApplication.getThemeIcon(_QGIS_THEME_ICONS[clean_name])
        if not qgis_icon.isNull():
            return qgis_icon

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
