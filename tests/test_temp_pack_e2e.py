# -*- coding: utf-8 -*-
"""
End-to-end verification of temporary self-contained packaging:
- Creates a real valid Shapefile outside project dir
- Runs ProjectPackager.package_with_external_layers_temp
- Inspects generated ZIP archive to verify files and XML datasource rewrites
"""

import os
import sys
import tempfile
import shutil
import zipfile

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGINS_ROOT = os.path.dirname(PLUGIN_DIR)
for p in (PLUGINS_ROOT, PLUGIN_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from qgis.core import (
    QgsApplication, QgsProject, QgsVectorLayer, QgsField,
    QgsCoordinateReferenceSystem, QgsVectorFileWriter, QgsWkbTypes
)
from qgis.PyQt.QtCore import QVariant
from QFieldDrop.core.packager import ProjectPackager

def test_temp_packaging_e2e():
    temp_root = tempfile.mkdtemp(prefix="qfield_e2e_")
    try:
        proj_dir = os.path.join(temp_root, "MyProject")
        ext_dir = os.path.join(temp_root, "ExternalData")
        os.makedirs(proj_dir, exist_ok=True)
        os.makedirs(ext_dir, exist_ok=True)

        # 1. Create a real valid external shapefile in ext_dir using QgsVectorFileWriter
        shp_path = os.path.join(ext_dir, "railway_line.shp")
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "ESRI Shapefile"
        options.fileEncoding = "UTF-8"

        mem_layer = QgsVectorLayer("Point?crs=epsg:4326", "temp", "memory")
        QgsVectorFileWriter.writeAsVectorFormatV3(
            mem_layer,
            shp_path,
            QgsProject.instance().transformContext(),
            options
        )

        layer = QgsVectorLayer(shp_path, "railway_line", "ogr")
        assert layer.isValid(), f"Layer created at {shp_path} is invalid!"

        # 2. Setup project
        proj_file = os.path.join(proj_dir, "test_network.qgz")
        project = QgsProject.instance()
        project.setFileName(proj_file)
        project.addMapLayer(layer)
        project.write()

        print("=== Checking External Layers Detection ===")
        ext_layers = ProjectPackager.check_external_layers(project)
        assert len(ext_layers) == 1, f"Expected 1 external layer, got: {len(ext_layers)}"
        print(f"  -> Detected external layer: {ext_layers[0]['name']} at {ext_layers[0]['path']}")
        assert len(ext_layers[0]['associated_files']) >= 3

        print("=== Running package_with_external_layers_temp ===")
        pkg_res = ProjectPackager.package_with_external_layers_temp(project)
        zip_path = pkg_res['zip_path']
        assert os.path.exists(zip_path), "ZIP file was not created!"
        print(f"  -> Successfully generated temporary zip: {zip_path} ({pkg_res['size_bytes']} bytes)")

        # 3. Inspect zip contents
        print("=== Inspecting ZIP Contents ===")
        with zipfile.ZipFile(zip_path, "r") as zf:
            namelist = [f.replace('\\', '/') for f in zf.namelist()]
            print("  -> Files inside zip:", namelist)
            assert "data/railway_line.shp" in namelist, "data/railway_line.shp missing in ZIP!"
            assert "data/railway_line.dbf" in namelist, "data/railway_line.dbf missing in ZIP!"

            # Extract the qgz to check rewritten datasource inside project XML
            qgz_in_zip = [f for f in namelist if f.endswith(".qgz")][0]
            extract_dir = os.path.join(temp_root, "inspect_qgz")
            zf.extract(qgz_in_zip, extract_dir)
            inner_qgz_path = os.path.join(extract_dir, qgz_in_zip)

            with zipfile.ZipFile(inner_qgz_path, "r") as izf:
                qgs_name = [f for f in izf.namelist() if f.endswith(".qgs")][0]
                with izf.open(qgs_name) as qf:
                    xml = qf.read().decode("utf-8")
                    assert "./data/railway_line.shp" in xml, "Datasource in project was not rewritten to ./data/railway_line.shp!"
                    print("  -> Datasource in project XML was perfectly rewritten to relative path './data/railway_line.shp'!")

        # 4. Verify local files are untouched
        assert os.path.exists(shp_path), "External file was removed from origin!"
        print("  -> Original external file still exists at origin.")

        # Check in project
        layer_source_now = layer.source()
        assert ext_dir.lower() in layer_source_now.lower(), "Live layer was altered!"
        print("  -> Live project layer source remains pointing to original external directory.")

        print("\n=== E2E TEMPORARY PACKAGING TEST PASSED COMPLETELY! ===")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

if __name__ == '__main__':
    qgs = QgsApplication([], False)
    qgs.initQgis()
    try:
        test_temp_packaging_e2e()
    finally:
        qgs.exitQgis()
