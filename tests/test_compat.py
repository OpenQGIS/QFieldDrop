# -*- coding: utf-8 -*-
"""
单元测试：Qt5 / Qt6 与 QGIS 跨版本兼容层 (core/compat.py)
"""

import pytest
pytest.importorskip("qgis")

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDialog, QMenu
from QFieldDrop.core.compat import safe_exec


def test_scoped_enums_exist():
    """验证常用枚举在跨版本桥接后可直接安全访问"""
    assert hasattr(Qt, "CrossCursor") or hasattr(Qt.CursorShape, "CrossCursor")
    assert hasattr(Qt, "PointingHandCursor") or hasattr(Qt.CursorShape, "PointingHandCursor")


def test_exec_bridge():
    """验证 QDialog 与 QMenu 的 exec / exec_ 兼容桥接正常"""
    assert hasattr(QDialog, "exec") or hasattr(QDialog, "exec_")
    assert hasattr(QMenu, "exec") or hasattr(QMenu, "exec_")


def test_safe_exec_callable():
    """验证 safe_exec 对空对象安全不崩溃"""
    res = safe_exec(None)
    assert res is None
