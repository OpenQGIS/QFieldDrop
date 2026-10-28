# -*- coding: utf-8 -*-
"""
单元测试：工程打包与路径提取引擎 (core/packager.py)
"""

import pytest
pytest.importorskip("qgis")

from QFieldDrop.core.packager import (
    ProjectPackager, EXCLUDED_EXTENSIONS, EXCLUDED_DIR_NAMES, EXCLUDED_FILE_NAMES
)


def test_excluded_extensions_and_dirs():
    """验证临时与缓存过滤黑名单完备性"""
    assert ".tmp" in EXCLUDED_EXTENSIONS
    assert ".qgs~" in EXCLUDED_EXTENSIONS
    assert "_qfield_return" in EXCLUDED_DIR_NAMES
    assert ".git" in EXCLUDED_DIR_NAMES
    assert "thumbs.db" in EXCLUDED_FILE_NAMES


def test_extract_filepath_from_source_empty():
    """验证空数据源处理安全返回 None"""
    assert ProjectPackager.extract_filepath_from_source("") is None
    assert ProjectPackager.extract_filepath_from_source(None) is None
