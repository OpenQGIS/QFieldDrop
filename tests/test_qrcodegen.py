# -*- coding: utf-8 -*-
"""
单元测试：纯 Python 二维码矩阵生成算法
"""

import pytest
pytest.importorskip("qgis")

from QFieldDrop.core.qrcodegen import QrCode


def test_pure_python_qrcodegen():
    """验证 Nayuki 纯 Python 二维码核心编码功能 (零 Qt 依赖，任何环境均可通过)"""
    text = "https://qfield.org"
    qr = QrCode.encode_text(text, QrCode.Ecc.MEDIUM)
    assert qr.get_size() > 0
    # 模块矩阵读取
    module_val = qr.get_module(0, 0)
    assert isinstance(module_val, bool)


def test_qr_matrix_generation():
    """验证纯 Python 二维码引擎可正确将文本编码为二维布尔矩阵"""
    pytest.importorskip("qgis")
    from QFieldDrop.core.qr_native import generate_qr_matrix
    test_text = "qfield://cloud.qfield.org/open?url=http://192.168.1.100:8899/project.zip"
    matrix = generate_qr_matrix(test_text)
    
    assert isinstance(matrix, list)
    assert len(matrix) > 0
    # 二维码矩阵必为正方形
    size = len(matrix)
    assert len(matrix[0]) == size
    # 确认包含至少一个黑块与白块
    flat = [item for sublist in matrix for item in sublist]
    assert True in flat
    assert False in flat
