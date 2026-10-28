# -*- coding: utf-8 -*-
"""
Verification script for Treemap and Packaging Engine enhancements.
Run using QGIS Python environment.
"""

import os
import sys
import tempfile
import shutil

# Ensure plugins dir is on path
PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGINS_ROOT = os.path.dirname(PLUGIN_DIR)
for p in (PLUGINS_ROOT, PLUGIN_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from qgis.core import QgsApplication, QgsProject, QgsVectorLayer
from QFieldDrop.core.packager import ProjectPackager
from QFieldDrop.ui.treemap_widget import TreeMapWidget, format_size, TreeMapNode

def run_tests():
    print("=== 1. Testing split_qgis_source & resolve_physical_path ===")
    src1 = r"F:\data\test.gpkg|layername=roads"
    phys, query = ProjectPackager.split_qgis_source(src1)
    assert phys == "F:/data/test.gpkg", f"Unexpected phys: {phys}"
    assert query == "|layername=roads", f"Unexpected query: {query}"

    vsi_src = "/vsizip/C:/archives/data.zip/subfolder/my_layer.shp"
    resolved = ProjectPackager.resolve_physical_path(vsi_src)
    assert "data.zip" in resolved, f"Unexpected resolved: {resolved}"
    print("  -> Passed!")

    print("=== 2. Testing format_size ===")
    assert format_size(0) == "0 B"
    assert "KB" in format_size(2048)
    assert "MB" in format_size(1024 * 1024 * 5)
    print("  -> Passed!")

    print("=== 3. Testing Shapefile Associated Files Collection ===")
    tmp_dir = tempfile.mkdtemp()
    try:
        shp_file = os.path.join(tmp_dir, "test_boundary.shp")
        shx_file = os.path.join(tmp_dir, "test_boundary.shx")
        dbf_file = os.path.join(tmp_dir, "test_boundary.dbf")
        prj_file = os.path.join(tmp_dir, "test_boundary.prj")
        for f in (shp_file, shx_file, dbf_file, prj_file):
            with open(f, 'w') as fp:
                fp.write("dummy")

        associated = ProjectPackager.get_associated_files(shp_file)
        assert len(associated) == 4, f"Expected 4 files, got: {associated}"
        print("  -> Passed! Collected all 4 sidecar files.")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print("=== 4. Testing Treemap Squarify & Equal Weighting for Same Dataset ===")
    # Simulate two layers sharing the same physical file (SuperLayer rule)
    mock_distributions = [
        {
            'id': 'layer_1',
            'name': '管线_A',
            'provider': 'ogr',
            'path': 'D:/test/network.gpkg',
            'size': 50.0,            # 100MB divided by 2
            'physical_size': 100.0,
            'reference_count': 2,
            'is_external': True
        },
        {
            'id': 'layer_2',
            'name': '管线_B',
            'provider': 'ogr',
            'path': 'D:/test/network.gpkg',
            'size': 50.0,            # 100MB divided by 2
            'physical_size': 100.0,
            'reference_count': 2,
            'is_external': True
        },
        {
            'id': 'layer_3',
            'name': '航拍正射影像',
            'provider': 'gdal',
            'path': 'D:/test/ortho.tif',
            'size': 200.0,
            'physical_size': 200.0,
            'reference_count': 1,
            'is_external': False
        }
    ]

    widget = TreeMapWidget()
    widget.resize(600, 400)
    widget.set_data(mock_distributions)

    assert len(widget.nodes) == 3
    assert widget.total_size == 300.0, f"Expected total 300.0, got: {widget.total_size}"

    # Verify rects are computed without overlapping zero dimensions
    for node in widget.nodes:
        assert node.rect.width() > 10, f"Node width too small: {node.rect.width()}"
        assert node.rect.height() > 10, f"Node height too small: {node.rect.height()}"
    print("  -> Passed! Treemap squarified rects layout successfully generated.")

    print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    qgs = QgsApplication([], False)
    qgs.initQgis()
    try:
        run_tests()
    finally:
        qgs.exitQgis()
