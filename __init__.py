# -*- coding: utf-8 -*-
"""
QField LAN Drop - QGIS Plugin classFactory entry
"""


def classFactory(iface):
    """Factory function loaded by QGIS plugin manager."""
    from .plugin import QFieldDropPlugin
    return QFieldDropPlugin(iface)
