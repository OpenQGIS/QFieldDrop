# -*- coding: utf-8 -*-
"""
QField Project Packaging Engine.
Supports:
1. Fast Direct Packaging (Mode A): saves dirty project, validates paths, packages project & data while filtering temp files.
2. QFieldSync integration (Mode B): calls QFieldSync's OfflineConverter if available.
3. External Layer Pre-check: inspects all layers and identifies data sources outside project folder.
"""

import os
import re
import shutil
import sqlite3
import tempfile
import zipfile
from typing import Dict, List, Any, Optional

from qgis.core import QgsProject, QgsMapLayer


EXCLUDED_EXTENSIONS = {
    '.qgs~', '.qgz~', '.wal', '.shm', '-wal', '-shm', '-journal',
    '.tmp', '.pyc', '.bak', '.log'
}

EXCLUDED_DIR_NAMES = {
    '.git', '.svn', '.hg', '__pycache__', '_qfield_dist', '.qfield_drop',
    '_qfield_return', '.idea', '.vscode', '.sync'
}

EXCLUDED_FILE_NAMES = {
    '.ds_store', 'thumbs.db', 'desktop.ini'
}


class ProjectPackager:
    @staticmethod
    def extract_filepath_from_source(source: str) -> Optional[str]:
        """Extract clean file path on disk from layer source string."""
        if not source:
            return None
        # Check SQLite / SpatiaLite dbname='...'
        m = re.search(r"dbname=['\"]([^'\"]+)['\"]", source)
        if m:
            path = m.group(1)
            if os.path.exists(path):
                return os.path.normpath(path)
        # Strip sublayer / query parameters (e.g., path.gpkg|layername=xxx)
        clean_path = source.split('|')[0].strip('"\'')
        if os.path.exists(clean_path):
            return os.path.normpath(clean_path)
        return None

    @classmethod
    def check_external_layers(cls, project: QgsProject) -> List[Dict[str, Any]]:
        """
        Inspect all layers in the project to check if any data files
        are located outside the project directory.
        """
        project_path = project.fileName()
        if not project_path:
            return []

        project_dir = os.path.normpath(os.path.dirname(project_path))
        external_layers = []

        for layer_id, layer in project.mapLayers().items():
            if not layer.isValid():
                continue

            provider = layer.providerType()
            # Skip memory, online tiles, database servers
            if provider in ('memory', 'wms', 'wfs', 'arcgismapserver', 'arcgisfeatureserver', 'vectortile'):
                continue

            # Skip remote database connections (PostgreSQL, Oracle, Hana, etc.)
            source = layer.source()
            if 'host=' in source and 'dbname=' in source and 'user=' in source:
                continue

            file_path = cls.extract_filepath_from_source(source)
            if not file_path:
                continue

            # Check if file is inside project_dir
            try:
                common = os.path.commonpath([project_dir, file_path])
                is_inside = (common.lower() == project_dir.lower())
            except ValueError:
                # Different drive letters on Windows (e.g. C: and D:)
                is_inside = False

            if not is_inside:
                file_size = os.path.getsize(file_path) if os.path.isfile(file_path) else 0
                external_layers.append({
                    'id': layer_id,
                    'name': layer.name(),
                    'provider': provider,
                    'path': file_path,
                    'size': file_size
                })

        return external_layers

    @staticmethod
    def _flush_sqlite_wal(directory: str):
        """
        Best-effort WAL checkpoint on .gpkg / .sqlite databases inside directory
        so pending WAL transactions are merged into the main database file before archiving.
        """
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED_DIR_NAMES and not d.startswith('.')]
            for f in files:
                if f.lower().endswith(('.gpkg', '.sqlite', '.db')):
                    db_path = os.path.join(root, f)
                    if os.path.exists(db_path + "-wal"):
                        try:
                            conn = sqlite3.connect(db_path, timeout=1.0)
                            conn.execute("PRAGMA wal_checkpoint(PASSIVE);")
                            conn.close()
                        except Exception:
                            pass

    @classmethod
    def package_project(cls, project: Optional[QgsProject] = None, use_qfieldsync_if_available: bool = False) -> Dict[str, Any]:
        """
        Package the current QGIS project into a standalone .zip payload.
        Returns a dictionary containing package metadata:
        {
            'dist_dir': temp_dir,
            'zip_path': path_to_zip,
            'zip_filename': filename,
            'project_name': name,
            'size_bytes': size,
            'file_count': count,
            'external_layers': [...]
        }
        """
        if project is None:
            project = QgsProject.instance()

        project_path = project.fileName()
        if not project_path or not os.path.exists(project_path):
            raise ValueError("当前工程尚未保存到本地磁盘，请先保存工程后再进行投送！")

        # Save dirty changes
        if project.isDirty():
            project.write()

        project_dir = os.path.normpath(os.path.dirname(project_path))
        project_name = project.baseName() or "qfield_project"

        # Check external layers
        external_layers = cls.check_external_layers(project)

        # Create isolated temp distribution directory
        dist_dir = tempfile.mkdtemp(prefix="qfield_drop_")
        zip_filename = f"{project_name}.zip"
        zip_path = os.path.join(dist_dir, zip_filename)

        # Check if QFieldSync is available and explicitly requested
        qfieldsync_used = False
        if use_qfieldsync_if_available:
            try:
                import qgis.utils
                qfs = qgis.utils.plugins.get('qfieldsync')
                if qfs and hasattr(qfs, 'core') and hasattr(qfs.core, 'OfflineConverter'):
                    export_dir = os.path.join(dist_dir, "export_tmp")
                    os.makedirs(export_dir, exist_ok=True)
                    converter = qfs.core.OfflineConverter(project, export_dir)
                    converter.convert()
                    project_dir = export_dir
                    qfieldsync_used = True
            except Exception:
                qfieldsync_used = False

        src_dir = project_dir

        # Flush SQLite/GeoPackage WAL files into main database files before archiving
        cls._flush_sqlite_wal(src_dir)

        # Build ZIP archive cleanly excluding unwanted files
        file_count = 0
        with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for root, dirs, files in os.walk(src_dir):
                # Filter directories in-place
                dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED_DIR_NAMES and not d.startswith('.')]

                for f in files:
                    f_lower = f.lower()
                    if f_lower in EXCLUDED_FILE_NAMES:
                        continue
                    if any(f_lower.endswith(ext) for ext in EXCLUDED_EXTENSIONS):
                        continue

                    full_path = os.path.join(root, f)
                    # Don't pack the zip inside itself if accidentally in src_dir
                    if os.path.abspath(full_path) == os.path.abspath(zip_path):
                        continue

                    rel_path = os.path.relpath(full_path, src_dir)
                    zf.write(full_path, arcname=rel_path)
                    file_count += 1

        size_bytes = os.path.getsize(zip_path)

        return {
            'dist_dir': dist_dir,
            'zip_path': zip_path,
            'zip_filename': zip_filename,
            'project_name': project_name,
            'size_bytes': size_bytes,
            'file_count': file_count,
            'external_layers': external_layers,
            'qfieldsync_used': qfieldsync_used
        }
