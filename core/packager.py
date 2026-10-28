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
from typing import Dict, List, Any, Optional, Callable

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
    def split_qgis_source(source_path: str):
        """Separate file path and query parameters (like |layername=... or ?subset=...)."""
        if not source_path:
            return "", ""
        parts = source_path.split('|', 1)
        phys_path = parts[0]
        q_params = '|' + parts[1] if len(parts) == 2 else ""

        if '?' in phys_path:
            sub_parts = phys_path.split('?', 1)
            phys_path = sub_parts[0]
            q_params = '?' + sub_parts[1] + q_params

        return phys_path.replace('\\', '/'), q_params

    @staticmethod
    def resolve_physical_path(path: str) -> str:
        """Resolve virtual VSI archive paths (/vsizip/, /vsitar/, etc.) to real disk file."""
        if not path:
            return ""
        norm_p = path.replace('\\', '/')
        for prefix in ['/vsizip/', '/vsitar/', '/vsigzip/', '/vsiz/', '/vsicurl/']:
            if norm_p.startswith(prefix):
                norm_p = norm_p[len(prefix):]
                break
        for archive_ext in ['.zip/', '.tar/', '.tar.gz/', '.tgz/', '.gz/']:
            idx = norm_p.lower().find(archive_ext)
            if idx != -1:
                norm_p = norm_p[:idx + len(archive_ext) - 1]
        return os.path.normpath(norm_p)

    @classmethod
    def get_associated_files(cls, file_path: str) -> List[str]:
        """Collect all associated sidecar files for ESRI Shapefile or rasters."""
        phys_path, _ = cls.split_qgis_source(file_path)
        actual_path = cls.resolve_physical_path(phys_path)
        if not actual_path or not os.path.exists(actual_path):
            return []

        if actual_path.lower().endswith(('.zip', '.tar', '.gz', '.tgz', '.tar.gz')):
            return [actual_path]

        dir_name = os.path.dirname(actual_path)
        file_name = os.path.basename(actual_path)

        shp_extensions = [
            '.shp.xml', '.shp', '.dbf', '.shx', '.prj', '.cpg', '.qpj',
            '.sbn', '.sbx', '.qml', '.qmd', '.qix', '.cst'
        ]

        try:
            files_in_dir = os.listdir(dir_name or '.')
        except OSError:
            return [actual_path]

        actual_file_name = file_name
        for f in files_in_dir:
            if f.lower() == file_name.lower():
                actual_file_name = f
                break

        actual_file_name_lower = actual_file_name.lower()
        matched_ext = None
        for ext in shp_extensions:
            if actual_file_name_lower.endswith(ext):
                matched_ext = ext
                break

        if matched_ext is not None:
            base_prefix = actual_file_name[:-len(matched_ext)]
            target_exts = shp_extensions
        else:
            if actual_file_name_lower.endswith('.aux.xml'):
                base_prefix = actual_file_name[:-8]
                _, main_ext = os.path.splitext(base_prefix)
            else:
                base_prefix, main_ext = os.path.splitext(actual_file_name)

            target_exts = [
                main_ext.lower(),
                (main_ext + '.aux.xml').lower(),
                (main_ext + '.ovr').lower(),
                '.tfw', '.wld', '.prj', '.xml', '.qml', '.qmd'
            ]
            if len(main_ext) >= 4:
                w_char = 'W' if main_ext[-1].isupper() else 'w'
                world_ext = main_ext[0] + main_ext[1] + main_ext[-1] + w_char
                if world_ext.lower() not in target_exts:
                    target_exts.append(world_ext.lower())

        matching_files = [f for f in files_in_dir if f.startswith(base_prefix)]
        ext_to_file = {}
        for f in matching_files:
            ext_part = f[len(base_prefix):].lower()
            if ext_part not in ext_to_file:
                ext_to_file[ext_part] = []
            ext_to_file[ext_part].append(f)

        seen = set()
        associated = []
        for ext in target_exts:
            if ext in ext_to_file:
                for f in ext_to_file[ext]:
                    full_path = os.path.join(dir_name, f)
                    if os.path.isfile(full_path):
                        norm_p = os.path.normcase(os.path.abspath(full_path))
                        if norm_p not in seen:
                            seen.add(norm_p)
                            associated.append(full_path)

        if not associated and os.path.exists(actual_path):
            associated = [actual_path]
        return associated

    @classmethod
    def extract_filepath_from_source(cls, source: str) -> Optional[str]:
        """Extract clean file path on disk from layer source string."""
        if not source:
            return None
        # Check SQLite / SpatiaLite dbname='...'
        m = re.search(r"dbname=['\"]([^'\"]+)['\"]", source)
        if m:
            path = m.group(1)
            actual = cls.resolve_physical_path(path)
            if actual and os.path.exists(actual):
                return os.path.normpath(actual)

        phys_path, _ = cls.split_qgis_source(source)
        actual = cls.resolve_physical_path(phys_path)
        if actual and os.path.exists(actual):
            return os.path.normpath(actual)
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
                associated = cls.get_associated_files(file_path)
                file_size = sum(os.path.getsize(f) for f in associated if os.path.isfile(f))
                external_layers.append({
                    'id': layer_id,
                    'name': layer.name(),
                    'provider': provider,
                    'path': file_path,
                    'size': file_size,
                    'associated_files': associated
                })

        return external_layers

    @classmethod
    def get_layers_size_distribution(cls, project: Optional[QgsProject] = None) -> List[Dict[str, Any]]:
        """
        Calculate disk size and percentage weight for all local file layers.
        Follows SuperLayer's deduplication architecture:
        - When multiple layers share the same physical dataset, total size is divided
          equally between referencing layers for treemap layout (reference_count).
        - Tracks whether layers reside outside the project directory.
        """
        if project is None:
            project = QgsProject.instance()

        project_path = project.fileName()
        project_dir = os.path.normpath(os.path.dirname(project_path)) if project_path else ""

        datasets = {}
        for layer_id, layer in project.mapLayers().items():
            if not layer.isValid():
                continue

            provider = layer.providerType()
            if provider in ('memory', 'wms', 'wfs', 'arcgismapserver', 'arcgisfeatureserver', 'vectortile'):
                continue

            source = layer.source()
            if 'host=' in source and 'dbname=' in source and 'user=' in source:
                continue

            phys_path = cls.extract_filepath_from_source(source)
            if not phys_path or not os.path.exists(phys_path):
                continue

            associated = cls.get_associated_files(phys_path)
            total_size = sum(os.path.getsize(f) for f in associated if os.path.isfile(f))

            # Deduplication key based on normalized canonical realpath
            dataset_key = os.path.normcase(os.path.realpath(phys_path))

            is_external = False
            if project_dir:
                try:
                    common = os.path.commonpath([project_dir, phys_path])
                    is_external = (common.lower() != project_dir.lower())
                except ValueError:
                    is_external = True

            if dataset_key not in datasets:
                datasets[dataset_key] = {
                    'path': phys_path,
                    'size': total_size,
                    'associated_files': associated,
                    'is_external': is_external,
                    'layers': []
                }
            datasets[dataset_key]['layers'].append(layer)

        nodes = []
        for dataset in datasets.values():
            ref_count = len(dataset['layers'])
            layer_names = [l.name() for l in dataset['layers']]
            layer_ids = [l.id() for l in dataset['layers']]
            primary_layer = dataset['layers'][0] if dataset['layers'] else None

            # Single shape for physical dataset, combining layer names
            display_name = ", ".join(layer_names)

            nodes.append({
                'layer': primary_layer,
                'id': primary_layer.id() if primary_layer else "",
                'layers': dataset['layers'],
                'layer_names': layer_names,
                'layer_ids': layer_ids,
                'name': display_name,
                'provider': primary_layer.providerType() if primary_layer else "",
                'path': dataset['path'],
                'size': dataset['size'],              # True physical size on disk
                'physical_size': dataset['size'],
                'reference_count': ref_count,         # Sharing count
                'is_external': dataset['is_external'],
                'associated_files': dataset['associated_files']
            })

        nodes.sort(key=lambda x: x['size'], reverse=True)
        return nodes

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
                        except (sqlite3.Error, OSError):
                            pass

    @classmethod
    def compress_directory(
        cls,
        src_dir: str,
        zip_path: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None,
        root_folder_name: Optional[str] = None
    ) -> int:
        """
        Thread-safe file compression helper. Compresses src_dir into zip_path,
        filtering temp files and reporting progress.
        If root_folder_name is provided, wraps all files inside a top-level project folder.
        Returns the number of files packed.
        """
        cls._flush_sqlite_wal(src_dir)

        # 1. Collect files to pack
        files_to_pack = []
        for root, dirs, files in os.walk(src_dir):
            dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED_DIR_NAMES and not d.startswith('.')]
            for f in files:
                f_lower = f.lower()
                if f_lower in EXCLUDED_FILE_NAMES:
                    continue
                if any(f_lower.endswith(ext) for ext in EXCLUDED_EXTENSIONS):
                    continue

                full_path = os.path.join(root, f)
                if os.path.abspath(full_path) == os.path.abspath(zip_path):
                    continue

                rel_path = os.path.relpath(full_path, src_dir)
                arc_name = os.path.join(root_folder_name, rel_path) if root_folder_name else rel_path
                files_to_pack.append((full_path, arc_name))

        total_files = len(files_to_pack)
        file_count = 0

        # 2. Compress files with progress notification
        with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for idx, (full_path, arc_name) in enumerate(files_to_pack):
                if is_cancelled and is_cancelled():
                    zf.close()
                    try:
                        if os.path.exists(zip_path):
                            os.remove(zip_path)
                    except OSError:
                        pass
                    raise InterruptedError("工程打包已被用户取消")

                zf.write(full_path, arcname=arc_name)
                file_count += 1
                if progress_callback:
                    progress_callback(file_count, total_files, arc_name)

        return file_count

    @classmethod
    def package_project(
        cls,
        project: Optional[QgsProject] = None,
        use_qfieldsync_if_available: bool = False,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Dict[str, Any]:
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

        file_count = cls.compress_directory(
            src_dir=src_dir,
            zip_path=zip_path,
            progress_callback=progress_callback,
            is_cancelled=is_cancelled,
            root_folder_name=project_name
        )

        size_bytes = os.path.getsize(zip_path) if os.path.exists(zip_path) else 0

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

    @classmethod
    def package_with_external_layers_temp(
        cls,
        project: Optional[QgsProject] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Dict[str, Any]:
        """
        Temporary Self-contained Packaging (Option B):
        Creates an isolated sandbox in system temp, copies external data files into ./data/,
        rewrites the cloned project XML datasources to relative paths, and compresses into
        a standalone zip payload for immediate mobile dispatch.
        The user's local disk project and original data files remain 100% untouched.
        """
        if project is None:
            project = QgsProject.instance()

        project_path = project.fileName()
        if not project_path or not os.path.exists(project_path):
            raise ValueError("当前工程尚未保存到本地磁盘，请先保存工程后再进行投送！")

        if project.isDirty():
            project.write()

        project_dir = os.path.normpath(os.path.dirname(project_path))
        project_name = project.baseName() or "qfield_project"

        # 1. Create sandbox workspace
        sandbox_dir = tempfile.mkdtemp(prefix="qfield_sbx_")
        sbx_data_dir = os.path.join(sandbox_dir, "data")
        os.makedirs(sbx_data_dir, exist_ok=True)

        try:
            # 2. Mirror project directory into sandbox (excluding temp files)
            for root, dirs, files in os.walk(project_dir):
                dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED_DIR_NAMES and not d.startswith('.')]
                for f in files:
                    f_lower = f.lower()
                    if f_lower in EXCLUDED_FILE_NAMES or any(f_lower.endswith(ext) for ext in EXCLUDED_EXTENSIONS):
                        continue
                    src_file = os.path.join(root, f)
                    rel_p = os.path.relpath(src_file, project_dir)
                    dest_file = os.path.join(sandbox_dir, rel_p)
                    os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                    shutil.copy2(src_file, dest_file)

            # 3. Collect external layers and copy associated files to sandbox/data/
            external_layers = cls.check_external_layers(project)
            copied_files = set()
            path_replacements = []  # list of (pattern, replacement)

            for item in external_layers:
                phys_path = item.get('path', '')
                if not phys_path or not os.path.exists(phys_path):
                    continue

                associated = cls.get_associated_files(phys_path)
                for fpath in associated:
                    norm_k = os.path.normcase(os.path.abspath(fpath))
                    if norm_k not in copied_files:
                        dest_path = os.path.join(sbx_data_dir, os.path.basename(fpath))
                        shutil.copy2(fpath, dest_path)
                        copied_files.add(norm_k)

                base_name = os.path.basename(phys_path)
                new_rel = f"./data/{base_name}"

                candidates = [
                    phys_path.replace('\\', '/'),
                    phys_path.replace('/', '\\'),
                ]

                # Check if it was serialized as relative path from project_dir
                try:
                    rel_to_proj = os.path.relpath(phys_path, project_dir)
                    candidates.append(rel_to_proj.replace('\\', '/'))
                    candidates.append(rel_to_proj.replace('/', '\\'))
                except ValueError:
                    pass

                # Also grab raw source from layer
                layer_obj = project.mapLayer(item.get('id', ''))
                if layer_obj:
                    raw_p, _ = cls.split_qgis_source(layer_obj.source())
                    if raw_p:
                        candidates.append(raw_p.replace('\\', '/'))
                        candidates.append(raw_p.replace('/', '\\'))

                for cand in candidates:
                    if cand and (cand, new_rel) not in path_replacements:
                        path_replacements.append((cand, new_rel))

            # 4. Rewrite sandbox project datasource references
            sbx_proj_file = os.path.join(sandbox_dir, os.path.basename(project_path))
            if os.path.exists(sbx_proj_file) and path_replacements:
                if sbx_proj_file.lower().endswith('.qgz'):
                    qgz_tmp = tempfile.mkdtemp(prefix="qgz_extract_")
                    try:
                        with zipfile.ZipFile(sbx_proj_file, 'r') as zf_in:
                            zf_in.extractall(qgz_tmp)

                        for root, _, files in os.walk(qgz_tmp):
                            for f in files:
                                if f.lower().endswith('.qgs'):
                                    qgs_file = os.path.join(root, f)
                                    with open(qgs_file, 'r', encoding='utf-8', errors='ignore') as qf:
                                        content = qf.read()
                                    for old_p, new_p in path_replacements:
                                        content = content.replace(old_p, new_p)
                                    with open(qgs_file, 'w', encoding='utf-8') as qf:
                                        qf.write(content)

                        with zipfile.ZipFile(sbx_proj_file, 'w', compression=zipfile.ZIP_DEFLATED) as zf_out:
                            for root, _, files in os.walk(qgz_tmp):
                                for f in files:
                                    full_p = os.path.join(root, f)
                                    zf_out.write(full_p, arcname=os.path.relpath(full_p, qgz_tmp))
                    finally:
                        shutil.rmtree(qgz_tmp, ignore_errors=True)

                elif sbx_proj_file.lower().endswith('.qgs'):
                    with open(sbx_proj_file, 'r', encoding='utf-8', errors='ignore') as qf:
                        content = qf.read()
                    for old_p, new_p in path_replacements:
                        content = content.replace(old_p, new_p)
                    with open(sbx_proj_file, 'w', encoding='utf-8') as qf:
                        qf.write(content)

            # 5. Compress the sandbox directory into final distribution package
            dist_dir = tempfile.mkdtemp(prefix="qfield_drop_")
            zip_filename = f"{project_name}.zip"
            zip_path = os.path.join(dist_dir, zip_filename)

            file_count = cls.compress_directory(
                src_dir=sandbox_dir,
                zip_path=zip_path,
                progress_callback=progress_callback,
                is_cancelled=is_cancelled,
                root_folder_name=project_name
            )

            size_bytes = os.path.getsize(zip_path) if os.path.exists(zip_path) else 0

            return {
                'dist_dir': dist_dir,
                'zip_path': zip_path,
                'zip_filename': zip_filename,
                'project_name': project_name,
                'size_bytes': size_bytes,
                'file_count': file_count,
                'external_layers': [],
                'is_temp_package': True,
                'original_external_count': len(external_layers)
            }
        finally:
            shutil.rmtree(sandbox_dir, ignore_errors=True)

    @classmethod
    def archive_external_layers_to_project(
        cls,
        project: Optional[QgsProject] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Dict[str, Any]:
        """
        Permanent Archive to Current Project (Option A):
        Copies external layer data files into a 'data/' subfolder inside current project dir,
        re-points QGIS live map layers to the new relative datasource, saves current project,
        and repackages cleanly.
        """
        if project is None:
            project = QgsProject.instance()

        project_path = project.fileName()
        if not project_path or not os.path.exists(project_path):
            raise ValueError("当前工程尚未保存到本地磁盘，请先保存工程后再进行归档！")

        project_dir = os.path.normpath(os.path.dirname(project_path))
        target_data_dir = os.path.join(project_dir, "data")
        os.makedirs(target_data_dir, exist_ok=True)

        external_layers = cls.check_external_layers(project)
        copied_files = set()

        for item in external_layers:
            layer_id = item.get('id', '')
            layer = project.mapLayer(layer_id)
            if not layer or not layer.isValid():
                continue

            source = layer.source()
            phys_path, query_params = cls.split_qgis_source(source)
            if not phys_path or not os.path.exists(phys_path):
                continue

            associated = cls.get_associated_files(phys_path)
            for fpath in associated:
                norm_k = os.path.normcase(os.path.abspath(fpath))
                if norm_k not in copied_files:
                    dest_path = os.path.join(target_data_dir, os.path.basename(fpath))
                    shutil.copy2(fpath, dest_path)
                    copied_files.add(norm_k)

            # Update live layer data source
            new_phys = os.path.join(target_data_dir, os.path.basename(phys_path))
            new_source = new_phys + query_params
            dp = layer.dataProvider()
            provider_name = dp.name() if dp is not None else layer.providerType()
            layer.setDataSource(new_source, layer.name(), provider_name)

        # Ensure project saves relative paths
        try:
            from qgis.core import Qgis
            if hasattr(Qgis, 'FilePathType') and hasattr(project, 'setFilePathStorage'):
                project.setFilePathStorage(Qgis.FilePathType.Relative)
        except Exception:
            pass

        project.write()

        # Repackage project with newly archived data
        return cls.package_project(
            project=project,
            progress_callback=progress_callback,
            is_cancelled=is_cancelled
        )
