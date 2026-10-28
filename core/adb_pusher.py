# -*- coding: utf-8 -*-
"""
Optional Android ADB Wireless / USB Silent Push Engine.
Pushes unzipped project folder directly into QField's sandbox storage:
/sdcard/Android/data/ch.opengis.qfield/files/QField/<project_name>/
"""

import os
import shlex
import shutil
import tempfile
import subprocess
from typing import List, Tuple, Optional
from qgis.PyQt.QtCore import QSettings

from .packager import (
    EXCLUDED_DIR_NAMES,
    EXCLUDED_FILE_NAMES,
    EXCLUDED_EXTENSIONS,
    ProjectPackager
)


class AdbPusher:
    TARGET_QFIELD_PATH = "/sdcard/Android/data/ch.opengis.qfield/files/QField"
    FALLBACK_QFIELD_PATH = "/sdcard/QField"

    @classmethod
    def get_adb_path(cls) -> Optional[str]:
        """Resolves the executable path of adb, checking custom settings, PATH, and common Windows SDK paths."""
        try:
            settings = QSettings("QFieldDrop", "ADB")
            custom_path = settings.value("custom_adb_path", "")
            if custom_path and os.path.isfile(custom_path):
                return custom_path
        except (TypeError, RuntimeError, AttributeError):
            pass

        # Check system PATH
        which_path = shutil.which("adb")
        if which_path:
            return which_path

        # Check common Windows locations
        if os.name == 'nt':
            candidates = [
                os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
                os.path.expandvars(r"%ProgramFiles%\Android\android-sdk\platform-tools\adb.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Android\android-sdk\platform-tools\adb.exe"),
                os.path.expandvars(r"C:\platform-tools\adb.exe"),
                os.path.expandvars(r"D:\platform-tools\adb.exe"),
                os.path.expandvars(r"C:\adb\adb.exe"),
                os.path.expandvars(r"D:\adb\adb.exe"),
                os.path.expandvars(r"%ProgramFiles%\leidian\ldplayer9\adb.exe"),
                os.path.expandvars(r"D:\leidian\ldplayer9\adb.exe"),
                os.path.expandvars(r"C:\leidian\ldplayer9\adb.exe"),
            ]
            for c in candidates:
                if os.path.isfile(c):
                    return c

        return None

    @classmethod
    def set_custom_adb_path(cls, path: str):
        settings = QSettings("QFieldDrop", "ADB")
        settings.setValue("custom_adb_path", path)

    @classmethod
    def is_adb_available(cls) -> bool:
        """Check if adb executable is found in system PATH or custom/common paths."""
        return cls.get_adb_path() is not None

    @classmethod
    def list_devices(cls) -> List[Tuple[str, str]]:
        """
        List connected ADB devices (both USB and wireless).
        Returns list of (serial, status), e.g. [('192.168.1.105:5555', 'device')]
        """
        adb_bin = cls.get_adb_path()
        if not adb_bin:
            return []

        try:
            res = subprocess.run(
                [adb_bin, "devices"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            devices = []
            lines = res.stdout.strip().splitlines()
            for line in lines[1:]:  # skip 'List of devices attached'
                parts = line.strip().split()
                if len(parts) >= 2:
                    devices.append((parts[0], parts[1]))
            return devices
        except Exception:
            return []

    @classmethod
    def connect_wireless(cls, ip_port: str) -> Tuple[bool, str]:
        """Connect to Android device over Wi-Fi (e.g. 192.168.1.105:5555)."""
        adb_bin = cls.get_adb_path()
        if not adb_bin:
            return False, "系统中未检测到 adb 命令，请先配置或安装 Android Platform Tools。"

        try:
            res = subprocess.run(
                [adb_bin, "connect", ip_port],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=8,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            out = res.stdout.strip()
            if "connected to" in out.lower() or "already connected" in out.lower():
                return True, out
            return False, out or res.stderr.strip()
        except Exception as e:
            return False, str(e)

    @classmethod
    def connect_device(cls, ip_port: str) -> Tuple[bool, str]:
        """Alias for connect_wireless."""
        return cls.connect_wireless(ip_port)

    @staticmethod
    def _stage_clean_project_dir(src_dir: str) -> str:
        """
        Copies only clean project files (excluding _qfield_return, .git, temp/WAL files)
        into an isolated staging folder for ADB push.
        """
        ProjectPackager._flush_sqlite_wal(src_dir)
        stage_dir = tempfile.mkdtemp(prefix="qfield_adb_stage_")
        for root, dirs, files in os.walk(src_dir):
            dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED_DIR_NAMES and not d.startswith('.')]
            rel_root = os.path.relpath(root, src_dir)
            dest_root = stage_dir if rel_root == '.' else os.path.join(stage_dir, rel_root)
            os.makedirs(dest_root, exist_ok=True)
            for f in files:
                f_lower = f.lower()
                if f_lower in EXCLUDED_FILE_NAMES:
                    continue
                if any(f_lower.endswith(ext) for ext in EXCLUDED_EXTENSIONS):
                    continue
                shutil.copy2(os.path.join(root, f), os.path.join(dest_root, f))
        return stage_dir

    @classmethod
    def push_project(
        cls,
        src_dir: str,
        project_name: str,
        device_serial: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Pushes filtered project directory to QField sandbox.
        """
        adb_bin = cls.get_adb_path()
        if not adb_bin:
            return False, "系统中未检测到 adb 命令行工具。"

        base_cmd = [adb_bin]
        if device_serial:
            base_cmd.extend(["-s", device_serial])

        remote_target = f"{cls.TARGET_QFIELD_PATH}/{project_name}"
        quoted_remote = shlex.quote(remote_target)
        stage_dir = None

        try:
            stage_dir = cls._stage_clean_project_dir(src_dir)

            # 1. Create target directory safely
            mkdir_cmd = base_cmd + ["shell", f"mkdir -p {quoted_remote}"]
            subprocess.run(
                mkdir_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            # 2. Push clean staged folder contents
            push_cmd = base_cmd + ["push", stage_dir.rstrip('\\/') + "/.", remote_target]
            res = subprocess.run(
                push_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=120,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            if res.returncode == 0:
                return True, f"成功推送至 QField 沙盒：{remote_target}"
            return False, res.stderr or res.stdout
        except Exception as e:
            return False, str(e)
        finally:
            if stage_dir and os.path.exists(stage_dir):
                shutil.rmtree(stage_dir, ignore_errors=True)

    @classmethod
    def pull_project(
        cls,
        project_name: str,
        local_dest_dir: str,
        device_serial: Optional[str] = None
    ) -> Tuple[bool, str, str]:
        """
        Pulls updated field project from Android QField sandbox to local directory.
        Returns: (success, message, saved_path)
        """
        adb_bin = cls.get_adb_path()
        if not adb_bin:
            return False, "系统中未检测到 adb 命令，请确保已安装或配置 Android Platform Tools。", ""

        base_cmd = [adb_bin]
        if device_serial:
            base_cmd.extend(["-s", device_serial])

        os.makedirs(local_dest_dir, exist_ok=True)

        candidate_remotes = [
            f"{cls.TARGET_QFIELD_PATH}/{project_name}",
            f"{cls.FALLBACK_QFIELD_PATH}/{project_name}",
            f"/sdcard/Android/data/ch.opengis.qfield/files/Exported Projects/{project_name}.zip",
            f"/sdcard/QField/Exported Projects/{project_name}.zip"
        ]

        found_remote = None
        for rpath in candidate_remotes:
            quoted_rpath = shlex.quote(rpath)
            chk = base_cmd + ["shell", f"[ -e {quoted_rpath} ] && echo FOUND"]
            try:
                res = subprocess.run(
                    chk, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                if "FOUND" in res.stdout:
                    found_remote = rpath
                    break
            except Exception:
                continue

        if not found_remote:
            found_remote = candidate_remotes[0]

        target_local = os.path.join(local_dest_dir, project_name)
        pull_cmd = base_cmd + ["pull", found_remote, target_local]

        try:
            res = subprocess.run(
                pull_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=180,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            if res.returncode == 0 and os.path.exists(target_local):
                return True, f"成功拉取外业成果：{target_local}", target_local
            err = res.stderr.strip() or res.stdout.strip()
            return False, f"拉取失败: {err}", ""
        except Exception as e:
            return False, str(e), ""

    @classmethod
    def install_plugin(
        cls,
        plugin_src_dir: str,
        device_serial: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Installs QField companion plugin directly into QField's sandbox plugins folder.
        """
        adb_bin = cls.get_adb_path()
        if not adb_bin:
            return False, "系统中未检测到 adb 命令，请确保已安装 Android Platform Tools。"

        if not os.path.exists(plugin_src_dir):
            return False, f"未找到插件源文件夹：{plugin_src_dir}"

        base_cmd = [adb_bin]
        if device_serial:
            base_cmd.extend(["-s", device_serial])

        remote_target = "/sdcard/Android/data/ch.opengis.qfield/files/plugins/qfield_drop"

        mkdir_cmd = base_cmd + ["shell", f"mkdir -p {shlex.quote(remote_target)}"]
        try:
            subprocess.run(
                mkdir_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=10, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
        except (subprocess.SubprocessError, OSError, TimeoutError):
            pass

        push_cmd = base_cmd + ["push", f"{plugin_src_dir}/.", remote_target]
        try:
            res = subprocess.run(
                push_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            if res.returncode == 0:
                return True, f"成功将助手插件写入手机 QField！\n路径: {remote_target}\n在手机中启动 QField 即可看到顶部【回传电脑】图标。"
            err = res.stderr.strip() or res.stdout.strip()
            return False, f"写入手机失败: {err}"
        except Exception as e:
            return False, f"ADB 传输异常: {str(e)}"
