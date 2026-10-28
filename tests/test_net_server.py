# -*- coding: utf-8 -*-
"""
单元测试：局域网 IP 分类与网络助手 (core/net_server.py)
"""

import pytest
pytest.importorskip("qgis")

from QFieldDrop.core.net_server import NetworkHelper


def test_classify_ip_hotspots():
    """验证 Android 与 iOS 热点网段的智能识别"""
    assert "Android 手机热点" in NetworkHelper.classify_ip("192.168.43.10")
    assert "iOS / iPhone 热点" in NetworkHelper.classify_ip("172.20.10.2")


def test_is_virtual_or_proxy():
    """验证代理网卡与虚拟机网段的智能判定"""
    assert NetworkHelper.is_virtual_or_proxy("198.18.0.1") is True
    assert NetworkHelper.is_virtual_or_proxy("192.168.1.100") is False
