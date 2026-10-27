# -*- coding: utf-8 -*-
"""
Optional Android ADB Wireless / USB Silent Push Engine.
Pushes unzipped project folder directly into QField's sandbox storage:
/sdcard/Android/data/ch.opengis.qfield/files/QField/<project_name>/
"""

import os
import shutil
import subprocess
from typing import List, Tuple, Optional


class AdbPusher:
    TARGET_QFIELD_PATH = "/sdcard/Android/data/ch.opengis.qfield/files/QField"
    FALLBACK_QFIELD_PATH = "/sdcard/QField"

    @staticmethod
    def is_adb_available() -> bool:
        """Check if adb executable is found in system PATH."""
        return shutil.which("adb") is not None

    @classmethod
    def list_devices(cls) -> List[Tuple[str, str]]:
        """
        List connected ADB devices (both USB and wireless).
        Returns list of (serial, status), e.g. [('192.168.1.105:5555', 'device')]
        """
        if not cls.is_adb_available():
            return []

        try:
            res = subprocess.run(
                ["adb", "devices"],
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
        if not cls.is_adb_available():
            return False, "系统中未检测到 adb 命令，请先安装 Android Platform Tools。"

        try:
            res = subprocess.run(
                ["adb", "connect", ip_port],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=8,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            out = res.stdout.strip()
            if "connected to" in out.lower():
                return True, out
            return False, out or res.stderr.strip()
        except Exception as e:
            return False, str(e)

    @classmethod
    def push_project(
        cls,
        src_dir: str,
        project_name: str,
        device_serial: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Pushes directory to QField sandbox.
        """
        if not cls.is_adb_available():
            return False, "系统中未安装 adb。"

        base_cmd = ["adb"]
        if device_serial:
            base_cmd.extend(["-s", device_serial])

        remote_target = f"{cls.TARGET_QFIELD_PATH}/{project_name}"

        try:
            # 1. Create target directory
            mkdir_cmd = base_cmd + ["shell", "mkdir", "-p", remote_target]
            subprocess.run(
                mkdir_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            # 2. Push folder contents
            push_cmd = base_cmd + ["push", src_dir.rstrip('\\/') + "/.", remote_target]
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
        if not cls.is_adb_available():
            return False, "系统中未检测到 adb 命令，请确保已安装 Android Platform Tools。", ""

        base_cmd = ["adb"]
        if device_serial:
            base_cmd.extend(["-s", device_serial])

        os.makedirs(local_dest_dir, exist_ok=True)

        # Potential paths inside Android
        candidate_remotes = [
            f"{cls.TARGET_QFIELD_PATH}/{project_name}",
            f"{cls.FALLBACK_QFIELD_PATH}/{project_name}",
            f"/sdcard/Android/data/ch.opengis.qfield/files/Exported Projects/{project_name}.zip",
            f"/sdcard/QField/Exported Projects/{project_name}.zip"
        ]

        # Check which remote path exists
        found_remote = None
        for rpath in candidate_remotes:
            chk = base_cmd + ["shell", f"[ -e '{rpath}' ] && echo 'FOUND'"]
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
            # Fall back to primary target path
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

