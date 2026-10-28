# -*- coding: utf-8 -*-
"""
QField LAN Drop - 自动化测试 pytest 夹具配置
"""

import os
import sys
import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_DIR = os.path.dirname(TESTS_DIR)
PLUGINS_ROOT = os.path.dirname(PLUGIN_DIR)

for p in (PLUGINS_ROOT, PLUGIN_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)


@pytest.fixture(scope="session", autouse=True)
def qgis_app():
    """初始化无头 QgsApplication 会话级夹具 (False 表示无 GUI 纯计算环境)"""
    try:
        from qgis.core import QgsApplication
        app = QgsApplication.instance()
        if app is None:
            app = QgsApplication([], False)
            app.initQgis()
            yield app
            app.exitQgis()
        else:
            yield app
    except (ImportError, RuntimeError):
        yield None
