# -*- coding: utf-8 -*-
"""
LocalSend Protocol v2 Implementation for QGIS LAN Drop.
Supports:
1. Zero-config LAN device discovery via UDP Multicast (224.0.0.167:53317) & Subnet HTTP scanning.
2. Direct push of QGIS project .zip to phone LocalSend app without scanning QR codes.
3. 100% pure Python standard library (socket, json, urllib, ssl) - zero pip dependencies.
"""

import os
import json
import time
import uuid
import socket
import ssl
import struct
import threading
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Callable, Tuple
from qgis.PyQt.QtCore import QObject, pyqtSignal

MULTICAST_GROUP = "224.0.0.167"
LOCALSEND_PORT = 53317


def _get_ssl_context():
    """Create unverified SSL context to accept LocalSend's self-signed certificates."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


class LocalSendDevice:
    def __init__(
        self,
        ip: str,
        port: int = LOCALSEND_PORT,
        alias: str = "Unknown Device",
        device_model: str = "Phone",
        device_type: str = "mobile",
        fingerprint: str = "",
        https: bool = True
    ):
        self.ip = ip
        self.port = port
        self.alias = alias
        self.device_model = device_model
        self.device_type = device_type
        self.fingerprint = fingerprint
        self.https = https

    @property
    def display_name(self) -> str:
        model_str = f" ({self.device_model})" if self.device_model else ""
        return f"{self.alias}{model_str} [{self.ip}]"

    def to_dict(self):
        return {
            'ip': self.ip,
            'port': self.port,
            'alias': self.alias,
            'device_model': self.device_model,
            'device_type': self.device_type,
            'https': self.https
        }


class DiscoverySignals(QObject):
    device_found = pyqtSignal(object)  # LocalSendDevice
    discovery_finished = pyqtSignal()
    status_updated = pyqtSignal(str)


class LocalSendDiscovery:
    """Discovers nearby LocalSend mobile/desktop clients."""
    def __init__(self, local_ip: str = "127.0.0.1"):
        self.local_ip = local_ip
        self.signals = DiscoverySignals()
        self.discovered_devices: Dict[str, LocalSendDevice] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._udp_sock: Optional[socket.socket] = None

    def start_discovery(self, subnet_scan: bool = True):
        self._running = True
        self.discovered_devices.clear()
        self._thread = threading.Thread(target=self._run, args=(subnet_scan,), daemon=True)
        self._thread.start()

    def stop_discovery(self):
        self._running = False
        if self._udp_sock:
            try:
                self._udp_sock.close()
            except Exception:
                pass
            self._udp_sock = None

    def _run(self, subnet_scan: bool):
        self.signals.status_updated.emit("正在监听 UDP 组播广播...")

        # 1. Start UDP Multicast listener & announce
        udp_thread = threading.Thread(target=self._listen_and_announce_udp, daemon=True)
        udp_thread.start()

        # 2. Optionally scan active LAN subnet
        if subnet_scan and self.local_ip and not self.local_ip.startswith("127."):
            self.signals.status_updated.emit("正在扫描局域网网段设备...")
            self._scan_subnet()

        # Wait for UDP listener to complete its discovery window
        udp_thread.join(timeout=3.5)
        if self._running:
            self.signals.discovery_finished.emit()

    def _listen_and_announce_udp(self):
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self._udp_sock = sock
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(0.5)

            # Bind to multicast port
            try:
                sock.bind(('', LOCALSEND_PORT))
                mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_GROUP), socket.INADDR_ANY)
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            except Exception:
                # Port might be occupied by local LocalSend client; use arbitrary port to broadcast query
                pass

            # Send announcement query
            query_payload = json.dumps({
                "alias": "QGIS LAN Drop",
                "version": "2.1",
                "deviceModel": "Desktop",
                "deviceType": "desktop",
                "fingerprint": "qgis-lan-drop-" + str(uuid.uuid4())[:8],
                "port": LOCALSEND_PORT,
                "protocol": "https",
                "download": False,
                "announce": True
            }).encode('utf-8')

            try:
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
                sock.sendto(query_payload, (MULTICAST_GROUP, LOCALSEND_PORT))
            except Exception:
                pass

            # Listen for responses for up to ~2.5 seconds (5 * 0.5s)
            for _ in range(5):
                if not self._running:
                    break
                try:
                    data, addr = sock.recvfrom(4096)
                    ip = addr[0]
                    if ip == self.local_ip or ip.startswith("127."):
                        continue
                    msg = json.loads(data.decode('utf-8', errors='ignore'))
                    alias = msg.get('alias', 'Unknown')
                    model = msg.get('deviceModel', '')
                    dtype = msg.get('deviceType', 'mobile')
                    port = msg.get('port', LOCALSEND_PORT)
                    https = msg.get('protocol', 'https').lower() == 'https'

                    dev = LocalSendDevice(ip, port, alias, model, dtype, https=https)
                    if ip not in self.discovered_devices:
                        self.discovered_devices[ip] = dev
                        self.signals.device_found.emit(dev)
                except socket.timeout:
                    continue
                except Exception:
                    if not self._running:
                        break
                    continue
        except Exception:
            pass
        finally:
            self._udp_sock = None
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass

    def _scan_subnet(self):
        """Scans neighboring IPs in the same /24 subnet for LocalSend HTTP info endpoint."""
        parts = self.local_ip.split('.')
        if len(parts) != 4:
            return

        base_prefix = f"{parts[0]}.{parts[1]}.{parts[2]}."
        my_last = int(parts[3])

        # Prioritize IPs close to host IP (such as gateway and recent devices)
        scan_indices = []
        for offset in range(1, 20):
            if my_last - offset >= 1:
                scan_indices.append(my_last - offset)
            if my_last + offset <= 254:
                scan_indices.append(my_last + offset)

        # Include common mobile gateway / DHCP assigns (1, 2, 100, 101, 102...)
        for special in [1, 2, 43, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110]:
            if special not in scan_indices and special != my_last:
                scan_indices.append(special)

        def probe_ip(ip):
            if not self._running or ip in self.discovered_devices:
                return
            for proto in ("https", "http"):
                url = f"{proto}://{ip}:{LOCALSEND_PORT}/api/localsend/v2/info"
                req = urllib.request.Request(url, headers={'User-Agent': 'QGIS-LAN-Drop'})
                try:
                    with urllib.request.urlopen(req, timeout=0.35, context=_get_ssl_context()) as resp:
                        if resp.status == 200:
                            data = json.loads(resp.read().decode('utf-8'))
                            alias = data.get('alias', 'Unknown')
                            model = data.get('deviceModel', '')
                            dtype = data.get('deviceType', 'mobile')
                            dev = LocalSendDevice(ip, LOCALSEND_PORT, alias, model, dtype, https=(proto == "https"))
                            if ip not in self.discovered_devices:
                                self.discovered_devices[ip] = dev
                                self.signals.device_found.emit(dev)
                            break
                except Exception:
                    continue

        threads = []
        for idx in scan_indices[:35]:
            ip = f"{base_prefix}{idx}"
            t = threading.Thread(target=probe_ip, args=(ip,), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=0.6)


class LocalSendClient:
    """Sends files to a target LocalSend client via REST API v2."""

    @classmethod
    def push_file(
        cls,
        device: LocalSendDevice,
        file_path: str,
        display_filename: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None,
        _use_https: Optional[bool] = None
    ) -> Tuple[bool, str]:
        if not os.path.exists(file_path):
            return False, "待推送的文件不存在"

        use_https = device.https if _use_https is None else _use_https
        file_size = os.path.getsize(file_path)
        filename = display_filename or os.path.basename(file_path)
        file_id = str(uuid.uuid4())
        session_fingerprint = "qgis-" + str(uuid.uuid4())[:8]
        protocol = "https" if use_https else "http"
        base_url = f"{protocol}://{device.ip}:{device.port}/api/localsend/v2"

        # Step 1: POST /prepare-upload
        prepare_payload = {
            "info": {
                "alias": "QGIS Desktop",
                "version": "2.1",
                "deviceModel": "Desktop",
                "deviceType": "desktop",
                "fingerprint": session_fingerprint,
                "download": False
            },
            "files": {
                file_id: {
                    "id": file_id,
                    "fileName": filename,
                    "size": file_size,
                    "fileType": "application/zip"
                }
            }
        }

        prepare_req = urllib.request.Request(
            f"{base_url}/prepare-upload",
            data=json.dumps(prepare_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        try:
            with urllib.request.urlopen(prepare_req, timeout=30, context=_get_ssl_context()) as resp:
                if resp.status != 200:
                    return False, f"手机端拒绝接收 (HTTP {resp.status})"
                resp_data = json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 403:
                return False, "用户在手机端拒绝了接收请求"
            return False, f"初始化传输失败: HTTP {e.code}"
        except Exception as e:
            # If HTTPS failed on initial attempt, try HTTP fallback once
            if use_https and _use_https is None:
                return cls.push_file(
                    device, file_path, display_filename,
                    progress_callback=progress_callback,
                    is_cancelled=is_cancelled,
                    _use_https=False
                )
            return False, f"连接手机失败: {str(e)}"

        session_id = resp_data.get('sessionId')
        file_token = resp_data.get('files', {}).get(file_id)

        if not session_id or not file_token:
            return False, "协议握手异常：未获取到会话凭证"

        # Step 2: POST /upload
        upload_url = f"{base_url}/upload?sessionId={session_id}&fileId={file_id}&token={file_token}"

        class ProgressReader:
            def __init__(self, fp, total, cb, cancel_cb):
                self.fp = fp
                self.total = total
                self.cb = cb
                self.cancel_cb = cancel_cb
                self.sent = 0
                self.last_pct = -1
                self.last_emit_time = 0.0

            def read(self, size=-1):
                if self.cancel_cb and self.cancel_cb():
                    raise InterruptedError("传输已取消")
                chunk = self.fp.read(size)
                if chunk:
                    self.sent += len(chunk)
                    if self.cb:
                        now = time.monotonic()
                        pct = int((self.sent / self.total) * 100) if self.total > 0 else 100
                        if self.sent >= self.total or (pct != self.last_pct and (now - self.last_emit_time) >= 0.08):
                            self.last_pct = pct
                            self.last_emit_time = now
                            self.cb(self.sent, self.total)
                return chunk

        try:
            with open(file_path, 'rb') as f:
                reader = ProgressReader(f, file_size, progress_callback, is_cancelled)
                upload_req = urllib.request.Request(
                    upload_url,
                    data=reader,
                    headers={
                        'Content-Type': 'application/octet-stream',
                        'Content-Length': str(file_size)
                    },
                    method='POST'
                )
                with urllib.request.urlopen(upload_req, timeout=120, context=_get_ssl_context()) as resp:
                    if resp.status == 200:
                        return True, f"已成功推送到 {device.alias}！"
                    return False, f"上传异常: HTTP {resp.status}"
        except InterruptedError:
            return False, "传输已取消"
        except Exception as e:
            return False, f"传输过程异常: {str(e)}"
