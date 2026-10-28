# -*- coding: utf-8 -*-
"""
LocalSend Protocol v2 Implementation for QGIS LAN Drop.
Supports:
1. Zero-config LAN device discovery via UDP Multicast (224.0.0.167:53317), LAN Subnet Broadcast, and concurrent Subnet HTTP scanning.
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
import concurrent.futures
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


def _get_opener():
    """Builds a dedicated opener that bypasses system/VPN proxies (Clash, etc.) for local LAN."""
    ctx = _get_ssl_context()
    https_handler = urllib.request.HTTPSHandler(context=ctx)
    proxy_handler = urllib.request.ProxyHandler({})  # Strictly disable system / VPN proxy for LAN
    return urllib.request.build_opener(proxy_handler, https_handler)


def _get_local_ip_set():
    """Returns all IPv4 addresses belonging to this computer (including loopback and virtual adapters)."""
    ips = {"127.0.0.1", "localhost", "28.0.0.1"}
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ips.add(info[4][0])
    except (socket.error, OSError):
        pass
    return ips


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
    """Discovers nearby LocalSend mobile/desktop clients via Multicast, Broadcast, and HTTP Subnet Probing."""
    def __init__(self, local_ip: str = "127.0.0.1"):
        self.local_ip = local_ip
        self.signals = DiscoverySignals()
        self.discovered_devices: Dict[str, LocalSendDevice] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._udp_sock: Optional[socket.socket] = None
        self._executor: Optional[concurrent.futures.ThreadPoolExecutor] = None

    @classmethod
    def fetch_device_info(cls, ip: str, port: int = LOCALSEND_PORT, timeout: float = 1.5) -> Optional[LocalSendDevice]:
        """Probes a device directly by IP and port via LocalSend REST API v2."""
        opener = _get_opener()
        reg_payload = json.dumps({
            "alias": "QGIS LAN Drop",
            "version": "2.1",
            "deviceModel": "Desktop",
            "deviceType": "desktop",
            "fingerprint": "qgis-lan-drop",
            "port": LOCALSEND_PORT,
            "protocol": "https",
            "download": False
        }).encode('utf-8')

        for proto in ("https", "http"):
            # 1. Official modern LocalSend register endpoint
            reg_url = f"{proto}://{ip}:{port}/api/localsend/v2/register"
            reg_req = urllib.request.Request(
                reg_url,
                data=reg_payload,
                headers={'Content-Type': 'application/json', 'User-Agent': 'LocalSend'}
            )
            try:
                with opener.open(reg_req, timeout=timeout) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode('utf-8'))
                        alias = data.get('alias', 'Unknown Device')
                        fp = data.get('fingerprint', '')
                        if alias == "QGIS LAN Drop" or fp.startswith("qgis-lan-drop"):
                            return None
                        return LocalSendDevice(
                            ip=ip,
                            port=port,
                            alias=alias,
                            device_model=data.get('deviceModel', ''),
                            device_type=data.get('deviceType', 'mobile'),
                            fingerprint=fp,
                            https=(proto == "https")
                        )
            except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
                pass

            # 2. Legacy fallback endpoint
            info_url = f"{proto}://{ip}:{port}/api/localsend/v2/info"
            info_req = urllib.request.Request(info_url, headers={'User-Agent': 'LocalSend'})
            try:
                with opener.open(info_req, timeout=timeout) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode('utf-8'))
                        alias = data.get('alias', 'Unknown Device')
                        fp = data.get('fingerprint', '')
                        if alias == "QGIS LAN Drop" or fp.startswith("qgis-lan-drop"):
                            return None
                        return LocalSendDevice(
                            ip=ip,
                            port=port,
                            alias=alias,
                            device_model=data.get('deviceModel', ''),
                            device_type=data.get('deviceType', 'mobile'),
                            fingerprint=fp,
                            https=(proto == "https")
                        )
            except Exception:
                continue
        return None

    def start_discovery(self, subnet_scan: bool = True):
        self._running = True
        self.discovered_devices.clear()
        self._thread = threading.Thread(target=self._run, args=(subnet_scan,), daemon=True)
        self._thread.start()

    def stop_discovery(self):
        self._running = False
        if self._executor:
            try:
                self._executor.shutdown(wait=False, cancel_futures=True)
            except (RuntimeError, OSError):
                pass
            self._executor = None
        if self._udp_sock:
            try:
                self._udp_sock.close()
            except (socket.error, OSError):
                pass
            self._udp_sock = None

    def _run(self, subnet_scan: bool):
        self.signals.status_updated.emit("正在监听 UDP 组播与广播...")

        # 1. Start UDP Multicast listener & announce in background
        udp_thread = threading.Thread(target=self._listen_and_announce_udp, daemon=True)
        udp_thread.start()

        # 2. Concurrently scan active LAN subnet via TCP/HTTP
        if subnet_scan and self.local_ip and not self.local_ip.startswith("127."):
            self.signals.status_updated.emit("正在并发扫描局域网网段设备...")
            self._scan_subnet()

        # Wait for UDP listener to complete
        udp_thread.join(timeout=3.5)
        if self._running:
            self.signals.discovery_finished.emit()

    def _listen_and_announce_udp(self):
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self._udp_sock = sock
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(0.5)

            # Bind to multicast port, fallback to any port if 53317 is occupied locally
            try:
                sock.bind(('', LOCALSEND_PORT))
            except Exception:
                try:
                    sock.bind(('', 0))
                except (socket.error, OSError):
                    pass

            # Configure Multicast Membership and Interface
            if self.local_ip and not self.local_ip.startswith("127."):
                try:
                    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(self.local_ip))
                except (socket.error, OSError):
                    pass
                try:
                    mreq = struct.pack("4s4s", socket.inet_aton(MULTICAST_GROUP), socket.inet_aton(self.local_ip))
                    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
                except Exception:
                    try:
                        mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_GROUP), socket.INADDR_ANY)
                        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
                    except (socket.error, OSError):
                        pass

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

            # Send announcement via Multicast and Subnet Broadcasts
            try:
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
                sock.sendto(query_payload, (MULTICAST_GROUP, LOCALSEND_PORT))
            except (socket.error, OSError):
                pass

            local_ips = _get_local_ip_set()
            if self.local_ip and "." in self.local_ip:
                try:
                    parts = self.local_ip.split('.')
                    bcast_ip = f"{parts[0]}.{parts[1]}.{parts[2]}.255"
                    sock.sendto(query_payload, (bcast_ip, LOCALSEND_PORT))
                    sock.sendto(query_payload, ("255.255.255.255", LOCALSEND_PORT))
                    # Also broadcast to neighboring /20 or common subnets if applicable
                    if parts[0] == "192" and parts[1] == "168":
                        if parts[2] != "0":
                            sock.sendto(query_payload, (f"{parts[0]}.{parts[1]}.0.255", LOCALSEND_PORT))
                        if parts[2] != "1":
                            sock.sendto(query_payload, (f"{parts[0]}.{parts[1]}.1.255", LOCALSEND_PORT))
                        sock.sendto(query_payload, (f"{parts[0]}.{parts[1]}.15.255", LOCALSEND_PORT))
                except (socket.error, OSError):
                    pass

            # Listen for responses for up to ~3.0 seconds
            for _ in range(6):
                if not self._running:
                    break
                try:
                    data, addr = sock.recvfrom(4096)
                    ip = addr[0]
                    # Strict self-filter: ignore loopbacks, virtual adapter IPs, and own host IPs
                    if (
                        ip == self.local_ip
                        or ip in local_ips
                        or ip.startswith("127.")
                        or ip.startswith("28.")
                        or ip.startswith("198.18.")
                    ):
                        continue

                    msg = json.loads(data.decode('utf-8', errors='ignore'))
                    alias = msg.get('alias', 'Unknown')
                    fp = msg.get('fingerprint', '')
                    # Ignore announcements originating from our own plugin
                    if alias == "QGIS LAN Drop" or fp.startswith("qgis-lan-drop"):
                        continue

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
        except (socket.error, OSError):
            pass
        finally:
            self._udp_sock = None
            if sock:
                try:
                    sock.close()
                except (socket.error, OSError):
                    pass

    def _scan_subnet(self):
        """Scans neighboring IPs in the same /24 subnet for LocalSend HTTP info endpoint concurrently."""
        parts = self.local_ip.split('.')
        if len(parts) != 4:
            return

        base_prefix = f"{parts[0]}.{parts[1]}.{parts[2]}."
        my_last = int(parts[3])

        # Prioritize IPs close to host IP and common mobile DHCP ranges
        prioritized = []
        for offset in range(1, 25):
            if my_last - offset >= 1:
                prioritized.append(my_last - offset)
            if my_last + offset <= 254:
                prioritized.append(my_last + offset)

        for special in [1, 2, 43, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110]:
            if special not in prioritized and special != my_last:
                prioritized.append(special)

        remaining = [i for i in range(1, 255) if i != my_last and i not in prioritized]
        all_indices = prioritized + remaining

        local_ips = _get_local_ip_set()
        def probe_index(idx):
            if not self._running:
                return
            target_ip = f"{base_prefix}{idx}"
            if target_ip in self.discovered_devices or target_ip in local_ips or target_ip == self.local_ip:
                return

            # Fast TCP port probe with short timeout to prevent blocking
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.25)
                res = s.connect_ex((target_ip, LOCALSEND_PORT))
                s.close()
                if res != 0 or not self._running:
                    return
            except Exception:
                return

            dev = self.fetch_device_info(target_ip, LOCALSEND_PORT, timeout=0.8)
            if dev and self._running and target_ip not in self.discovered_devices:
                self.discovered_devices[target_ip] = dev
                self.signals.device_found.emit(dev)

        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=32)
        try:
            futures = [self._executor.submit(probe_index, idx) for idx in all_indices]
            for f in concurrent.futures.as_completed(futures):
                if not self._running:
                    break
        finally:
            if self._executor:
                try:
                    self._executor.shutdown(wait=False, cancel_futures=True)
                except (RuntimeError, OSError):
                    pass
                self._executor = None


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

        opener = _get_opener()

        try:
            with opener.open(prepare_req, timeout=30) as resp:
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
                with opener.open(upload_req, timeout=120) as resp:
                    if resp.status == 200:
                        return True, f"已成功推送到 {device.alias}！"
                    return False, f"上传异常: HTTP {resp.status}"
        except InterruptedError:
            return False, "传输已取消"
        except Exception as e:
            return False, f"传输过程异常: {str(e)}"
