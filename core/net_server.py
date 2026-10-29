# -*- coding: utf-8 -*-
"""
Local Area Network (LAN) IP detection and controllable background HTTP server.
Provides thread-safe Qt signals for download monitoring and alias routing.
"""

import os
import re
import json
import time
import shutil
import socket
import zipfile
import datetime
import threading
import urllib.parse
from typing import Optional, List, Dict, Tuple
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from qgis.PyQt.QtCore import QObject, pyqtSignal


class NetworkHelper:
    @staticmethod
    def is_virtual_or_proxy(ip: str) -> bool:
        """Check if an IP address belongs to virtual machines or proxy/VPN (TUN/TAP)."""
        return (
            ip.startswith("28.")            # FlClash / Mihomo / Clash TUN default IP
            or ip.startswith("198.18.")     # Clash / FakeIP range
            or ip.startswith("198.19.")
            or ip.startswith("172.17.")     # Docker default bridge
            or ip.startswith("172.18.")
            or ip.startswith("192.168.56.") # VirtualBox Host-Only
        )

    @classmethod
    def classify_ip(cls, ip: str) -> str:
        """Classify IP for friendly display in dropdown."""
        if ip.startswith("192.168.43."):
            return "Android 手机热点"
        elif ip.startswith("172.20.10."):
            return "iOS / iPhone 热点"
        elif ip.startswith("192.168.56.") or ip.startswith("172.17.") or ip.startswith("172.18."):
            return "虚拟机网卡 (VM/Docker)"
        elif ip.startswith("28.") or ip.startswith("198.18.") or ip.startswith("198.19."):
            return "代理 / VPN 虚拟网卡 (Clash/TUN，不可连)"
        elif ip.startswith("192.168."):
            return "局域网 Wi-Fi / 有线"
        elif ip.startswith("10."):
            return "内网 / 企业 Wi-Fi"
        elif ip.startswith("172."):
            parts = ip.split('.')
            if len(parts) >= 2 and parts[1].isdigit() and 16 <= int(parts[1]) <= 31:
                return "局域网热点 / 内网"
            return "局域网地址"
        return "局域网 IPv4"

    @classmethod
    def get_all_local_ip_set(cls) -> set:
        """Returns all IPv4 addresses belonging to the local machine."""
        ips = {"127.0.0.1", "localhost", "28.0.0.1"}
        try:
            hostname = socket.gethostname()
            for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
                ips.add(info[4][0])
        except (socket.error, OSError):
            pass
        return ips

    @classmethod
    def get_all_lan_ips(cls):
        """
        Detect and rank all valid IPv4 LAN addresses.
        Returns a list of dicts: [{'ip': '192.168.1.100', 'label': '192.168.1.100 (局域网 Wi-Fi / 有线) [推荐出口]'}, ...]
        """
        ips = []
        primary_ip = None

        # 1. Probe primary outbound routing IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            # Connecting to a public IP doesn't actually send packets for UDP,
            # but causes the OS routing table to choose the outbound interface
            s.connect(('10.255.255.255', 1))
            primary_ip = s.getsockname()[0]
            s.close()
            if primary_ip and not primary_ip.startswith('127.') and not primary_ip.startswith('169.254.'):
                ips.append(primary_ip)
        except (socket.error, OSError):
            pass

        # 2. Enumerate host addresses via getaddrinfo
        try:
            hostname = socket.gethostname()
            for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
                ip = info[4][0]
                if not ip.startswith('127.') and not ip.startswith('169.254.') and ip not in ips:
                    ips.append(ip)
        except (socket.error, OSError):
            pass

        if not ips:
            ips = ['127.0.0.1']

        def is_private_ip(ip_str):
            if ip_str.startswith("192.168.") or ip_str.startswith("10."):
                return True
            if ip_str.startswith("172."):
                p = ip_str.split('.')
                if len(p) >= 2 and p[1].isdigit() and 16 <= int(p[1]) <= 31:
                    return True
            return False

        # Sort:
        # 1. Mobile Hotspots (192.168.43.x, 172.20.10.x)
        # 2. Private LAN Wi-Fi / Ethernet (192.168.x.x, 10.x.x.x, 172.16-31.x.x)
        # 3. Primary Outbound (if not private)
        # 4. Others
        # 5. Virtual / Proxies (198.18.x, 172.17.x, 192.168.56.x)
        def ip_sort_key(ip):
            if cls.is_virtual_or_proxy(ip):
                return 99
            if ip.startswith("192.168.43.") or ip.startswith("172.20.10."):
                return 0
            if is_private_ip(ip):
                return 1 if (ip == primary_ip and not cls.is_virtual_or_proxy(primary_ip)) else 2
            if ip == primary_ip and not cls.is_virtual_or_proxy(primary_ip):
                return 3
            return 5

        sorted_ips = sorted(ips, key=ip_sort_key)

        result = []
        best_ip = sorted_ips[0] if sorted_ips else None
        for ip in sorted_ips:
            desc = cls.classify_ip(ip)
            is_rec = (ip == best_ip and not cls.is_virtual_or_proxy(ip))
            is_def = (ip == primary_ip and not cls.is_virtual_or_proxy(ip))

            if is_rec:
                label = f"{ip} ★ 推荐"
                tooltip = f"{ip} ({desc}) ★ 推荐局域网优先使用"
            elif is_def:
                label = f"{ip} (默认)"
                tooltip = f"{ip} ({desc}) 系统默认出口"
            elif cls.is_virtual_or_proxy(ip):
                label = f"{ip} (虚拟网卡)"
                tooltip = f"{ip} ({desc}，手机通常不可直连)"
            else:
                label = ip
                tooltip = f"{ip} ({desc})"
            result.append({'ip': ip, 'label': label, 'tooltip': tooltip})

        return result


class DropServerSignals(QObject):
    client_connected = pyqtSignal(str)              # client_ip
    transfer_progress = pyqtSignal(str, int, int)   # client_ip, sent_bytes, total_bytes
    transfer_completed = pyqtSignal(str, str)       # client_ip, filename
    file_received = pyqtSignal(str, str, int)       # client_ip, saved_filepath, file_size
    server_started = pyqtSignal(int)                # port
    server_stopped = pyqtSignal()
    server_error = pyqtSignal(str)


_MOBILE_UPLOAD_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>QField 外业成果一键回传</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #F8FAFC; color: #0F172A; padding: 20px 16px; }
  .card { background: #FFFFFF; border-radius: 12px; padding: 20px 16px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 16px; }
  h1 { font-size: 19px; font-weight: 700; color: #0284C7; margin-bottom: 6px; }
  p.desc { font-size: 13px; color: #64748B; margin-bottom: 16px; line-height: 1.4; }
  .file-dropzone { border: 2px dashed #0284C7; background: #F0F9FF; border-radius: 10px; padding: 24px 12px; text-align: center; cursor: pointer; }
  .file-info { margin-top: 12px; padding: 10px; background: #F1F5F9; border-radius: 8px; font-size: 13px; display: none; }
  button { width: 100%; border: none; border-radius: 10px; padding: 14px; font-size: 15px; font-weight: bold; cursor: pointer; margin-top: 16px; }
  .btn-upload { background: #0284C7; color: white; display: none; }
  .progress-box { margin-top: 16px; display: none; }
  .progress-bar-bg { width: 100%; height: 10px; background: #E2E8F0; border-radius: 5px; overflow: hidden; }
  .progress-bar-fill { height: 100%; width: 0%; background: #10B981; transition: width 0.15s ease; }
  .status-text { font-size: 13px; margin-top: 6px; text-align: center; color: #475569; }
  .tip-box { background: #F0FDF4; border: 1px solid #86EFAC; border-radius: 10px; padding: 12px 14px; font-size: 12px; color: #166534; line-height: 1.5; margin-bottom: 14px; }
  .btn-wake { width: 100%; background: #16A34A; color: white; border: none; border-radius: 8px; padding: 10px 12px; font-size: 13px; font-weight: bold; cursor: pointer; margin-top: 6px; }
  .proj-badge { display: inline-block; background: #E0F2FE; color: #0369A1; font-weight: 600; padding: 3px 8px; border-radius: 6px; font-size: 12px; margin-bottom: 12px; }
</style>
</head>
<body>
<div class="card">
  <h1>📤 QField 外业成果回传</h1>
  <div id="projBadge" class="proj-badge" style="display:none;"></div>
  
  <div class="tip-box">
    <div style="font-weight:700; font-size:13px; margin-bottom:4px;">⚡ 推荐在 QField 伴侣中一键秒传 (绕过沙盒)</div>
    <div style="font-size:12px; opacity:0.9; margin-bottom:6px;">无需在此网页手动翻找 Android 沙盒文件，点击复制并直接唤醒 QField：</div>
    <button type="button" class="btn-wake" onclick="copyAndWakeQField()">📋 复制回传地址并唤醒 QField</button>
  </div>

  <p class="desc">请选择 QField 导出的工程压缩包 (.zip) 或现场照片，点击立即回传到电脑 QGIS。</p>
  
  <input type="file" id="fileInput" style="display:none;" />
  <div class="file-dropzone" onclick="document.getElementById('fileInput').click()">
    <div style="font-size:32px; margin-bottom:6px;">📁</div>
    <div style="font-weight:600; color:#0369A1;">点击选择工程压缩包或文件</div>
    <div style="font-size:12px; color:#94A3B8; margin-top:4px;">支持 .zip, .gpkg, 照片等</div>
  </div>

  <div id="fileInfo" class="file-info">
    📄 <span id="fileName"></span> (<span id="fileSize"></span>)
  </div>

  <button id="uploadBtn" class="btn-upload" onclick="startUpload()">🚀 立即回传至电脑</button>

  <div id="progressBox" class="progress-box">
    <div class="progress-bar-bg"><div id="progressFill" class="progress-bar-fill"></div></div>
    <div id="statusText" class="status-text">正在上传: 0%</div>
  </div>
</div>

<script>
let selectedFile = null;
const fileInput = document.getElementById('fileInput');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const uploadBtn = document.getElementById('uploadBtn');
const progressBox = document.getElementById('progressBox');
const progressFill = document.getElementById('progressFill');
const statusText = document.getElementById('statusText');

// Parse target project name from URL ?proj=xxx
const urlParams = new URLSearchParams(window.location.search);
const projName = urlParams.get('proj') || urlParams.get('project');
if (projName) {
  const badge = document.getElementById('projBadge');
  if (badge) {
    badge.innerText = '🎯 目标电脑工程: ' + projName;
    badge.style.display = 'inline-block';
  }
}

function copyAndWakeQField() {
  const curUrl = window.location.href;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(curUrl).then(() => {
      window.location.href = 'qfield://';
      setTimeout(() => {
        alert('✅ 回传地址已复制！\n请打开手机 QField，点击顶部回传图标即可全自动完成配对。');
      }, 500);
    }).catch(() => {
      fallbackCopy(curUrl);
    });
  } else {
    fallbackCopy(curUrl);
  }
}

function fallbackCopy(text) {
  const ta = document.createElement('textarea');
  ta.value = text;
  document.body.appendChild(ta);
  ta.select();
  document.execCommand('copy');
  document.body.removeChild(ta);
  window.location.href = 'qfield://';
  setTimeout(() => {
    alert('✅ 回传地址已复制！\n请打开手机 QField，点击顶部回传图标即可全自动完成配对。');
  }, 500);
}

fileInput.addEventListener('change', function() {
  if (this.files && this.files.length > 0) {
    selectedFile = this.files[0];
    fileName.innerText = selectedFile.name;
    const mb = (selectedFile.size / (1024 * 1024)).toFixed(2);
    fileSize.innerText = mb + ' MB';
    fileInfo.style.display = 'block';
    uploadBtn.style.display = 'block';
  }
});

function startUpload() {
  if (!selectedFile) return;
  uploadBtn.disabled = true;
  uploadBtn.style.opacity = '0.6';
  progressBox.style.display = 'block';

  const xhr = new XMLHttpRequest();
  const url = '/upload?filename=' + encodeURIComponent(selectedFile.name);
  xhr.open('POST', url, true);
  xhr.setRequestHeader('Content-Type', 'application/octet-stream');

  xhr.upload.onprogress = function(e) {
    if (e.lengthComputable) {
      const pct = Math.round((e.loaded / e.total) * 100);
      progressFill.style.width = pct + '%';
      const loadedMb = (e.loaded / (1024 * 1024)).toFixed(1);
      const totalMb = (e.total / (1024 * 1024)).toFixed(1);
      statusText.innerText = '正在上传: ' + loadedMb + ' / ' + totalMb + ' MB (' + pct + '%)';
    }
  };

  xhr.onload = function() {
    if (xhr.status === 200) {
      progressFill.style.width = '100%';
      statusText.innerHTML = '<b style="color:#059669;">✅ 上传成功！内业电脑 QGIS 已收到成果。</b>';
    } else {
      statusText.innerHTML = '<b style="color:#DC2626;">❌ 上传异常: HTTP ' + xhr.status + '</b>';
      uploadBtn.disabled = false;
      uploadBtn.style.opacity = '1';
    }
  };

  xhr.onerror = function() {
    statusText.innerHTML = '<b style="color:#DC2626;">❌ 网络连接失败，请检查是否处于同一 Wi-Fi。</b>';
    uploadBtn.disabled = false;
    uploadBtn.style.opacity = '1';
  };

  xhr.send(selectedFile);
}
</script>
</body>
</html>
"""


class LanDropServer:
    """
    Lightweight, controllable HTTP server for one-click ZIP distribution.
    Features:
    - Auto-scanning ports from 8899 to 8919
    - Alias routing: serves project file under /project.zip, /latest.zip, and its real filename
    - Streaming download in 64KB chunks with progress callbacks
    - Safe graceful shutdown and port release
    """

    def __init__(self, serve_dir: str, zip_filename: str, start_port: int = 8899, upload_dir: Optional[str] = None):
        self.serve_dir = serve_dir
        self.zip_filename = zip_filename
        self.target_filepath = os.path.join(serve_dir, zip_filename)
        self.upload_dir = upload_dir or os.path.join(serve_dir, "_qfield_return")
        os.makedirs(self.upload_dir, exist_ok=True)

        # Prepare mobile companion zip in serve_dir
        self.mobile_zip_path = os.path.join(serve_dir, "mobile.zip")
        self._prepare_mobile_zip()

        self.port = start_port
        self.httpd = None
        self.thread = None
        self.signals = DropServerSignals()
        self._is_running = False

    def _prepare_mobile_zip(self):
        """Pre-packages the mobile companion plugin into serve_dir/mobile.zip for offline download."""
        try:
            import zipfile
            plugin_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            mobile_src = os.path.join(plugin_root, "mobile")
            if not os.path.exists(mobile_src):
                mobile_src = os.path.join(os.path.dirname(plugin_root), "QFieldDrop-Mobile")

            if os.path.exists(mobile_src):
                with zipfile.ZipFile(self.mobile_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for root, dirs, files in os.walk(mobile_src):
                        for f in files:
                            full = os.path.join(root, f)
                            rel = os.path.relpath(full, mobile_src)
                            # QField expects metadata.txt and main.qml at the root of the plugin ZIP
                            zf.write(full, arcname=rel)
                # Also create plugin.zip alias
                alias = os.path.join(self.serve_dir, "plugin.zip")
                shutil.copyfile(self.mobile_zip_path, alias)
        except (shutil.Error, OSError):
            pass

    def update_payload(self, serve_dir: str, zip_filename: str):
        """Dynamically switch served archive without tearing down listening socket."""
        self.serve_dir = serve_dir
        self.zip_filename = zip_filename
        self.target_filepath = os.path.join(serve_dir, zip_filename)
        self.mobile_zip_path = os.path.join(serve_dir, "mobile.zip")
        self._prepare_mobile_zip()

    def start(self) -> int:
        parent_self = self

        class DropRequestHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=parent_self.serve_dir, **kwargs)

            def _send_zip_headers(self, file_size, download_name=None):
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                effective_name = download_name or parent_self.zip_filename or "project.zip"
                # RFC 2616 / RFC 6266: The fallback filename param MUST be pure Latin-1/ASCII.
                # In Python's http.server, headers are encoded strictly with 'latin-1'.
                # Any non-ASCII character (e.g. Chinese characters from \w in regex) causes
                # UnicodeEncodeError in send_header(), which immediately crashes the handler
                # thread and yields ERR_EMPTY_RESPONSE in browsers.
                base_name, ext = os.path.splitext(effective_name)
                ext = ext if ext else ".zip"
                safe_base = re.sub(r'[^a-zA-Z0-9_\-]', '_', base_name).strip('_')
                safe_ascii_name = f"{safe_base}{ext}" if safe_base else f"project{ext}"

                # RFC 5987 / RFC 6266: Use filename*=UTF-8''... for full Unicode support across modern browsers
                encoded_utf8_name = urllib.parse.quote(effective_name)
                self.send_header(
                    "Content-Disposition",
                    f'attachment; filename="{safe_ascii_name}"; filename*=UTF-8\'\'{encoded_utf8_name}'
                )
                self.send_header("Content-Length", str(file_size))
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, HEAD, POST, OPTIONS")
                self.end_headers()

            def do_OPTIONS(self):
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, HEAD, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Range")
                self.send_header("Content-Length", "0")
                self.end_headers()

            def do_HEAD(self):
                req_path = urllib.parse.unquote(self.path.split('?')[0]).lstrip('/')
                cur_fname = parent_self.zip_filename or "project.zip"
                valid_paths = {'', 'project.zip', 'latest.zip', cur_fname, urllib.parse.unquote(cur_fname)}
                valid_paths_lower = {p.lower() for p in valid_paths if p}
                if req_path in ('mobile.zip', 'plugin.zip', 'qfield_drop.zip'):
                    m_path = parent_self.mobile_zip_path
                    if os.path.exists(m_path):
                        self._send_zip_headers(os.path.getsize(m_path), download_name="qfield_drop.zip")
                        return
                if req_path in valid_paths or req_path.lower() in valid_paths_lower:
                    cur_target = parent_self.target_filepath
                    if not os.path.exists(cur_target):
                        self.send_error(404, "Project archive not found")
                        return
                    self._send_zip_headers(os.path.getsize(cur_target))
                else:
                    self.send_error(404, "Not Found")

            def do_GET(self):
                client_ip = self.client_address[0]
                req_path = urllib.parse.unquote(self.path.split('?')[0]).lstrip('/')

                # Route 1: Mobile companion plugin download
                if req_path in ('mobile.zip', 'plugin.zip', 'qfield_drop.zip'):
                    m_path = parent_self.mobile_zip_path
                    if not os.path.exists(m_path):
                        self.send_error(404, "Mobile plugin archive not found")
                        return
                    file_size = os.path.getsize(m_path)
                    self._send_zip_headers(file_size, download_name="qfield_drop.zip")
                    with open(m_path, 'rb') as f:
                        shutil.copyfileobj(f, self.wfile)
                    return

                # Route 2: Project payload download
                cur_fname = parent_self.zip_filename or "project.zip"
                valid_paths = {'', 'project.zip', 'latest.zip', cur_fname, urllib.parse.unquote(cur_fname)}
                valid_paths_lower = {p.lower() for p in valid_paths if p}

                if req_path in valid_paths or req_path.lower() in valid_paths_lower:
                    cur_target = parent_self.target_filepath
                    if not os.path.exists(cur_target):
                        self.send_error(404, "Project archive not found")
                        return

                    parent_self.signals.client_connected.emit(client_ip)
                    file_size = os.path.getsize(cur_target)
                    self._send_zip_headers(file_size)

                    # Stream file in 64KB chunks with throttled progress signals
                    sent = 0
                    chunk_size = 65536
                    last_pct = -1
                    last_emit_time = 0.0
                    try:
                        with open(cur_target, 'rb') as f:
                            while True:
                                chunk = f.read(chunk_size)
                                if not chunk:
                                    break
                                self.wfile.write(chunk)
                                sent += len(chunk)
                                now = time.monotonic()
                                pct = int((sent / file_size) * 100) if file_size > 0 else 100
                                if sent >= file_size or (pct != last_pct and (now - last_emit_time) >= 0.08):
                                    last_pct = pct
                                    last_emit_time = now
                                    parent_self.signals.transfer_progress.emit(client_ip, sent, file_size)
                        parent_self.signals.transfer_completed.emit(client_ip, cur_fname)
                    except (ConnectionResetError, BrokenPipeError):
                        # Client disconnected prematurely
                        pass
                    except Exception as e:
                        parent_self.signals.server_error.emit(f"传输异常: {str(e)}")
                elif req_path.startswith("upload") or req_path.startswith("return"):
                    html_bytes = _MOBILE_UPLOAD_HTML.encode('utf-8')
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(html_bytes)))
                    self.end_headers()
                    self.wfile.write(html_bytes)
                elif req_path == "ping":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"status":"ok","plugin":"QFieldDrop"}')
                else:
                    self.send_error(404, "Not Found")

            def do_POST(self):
                client_ip = self.client_address[0]
                req_path = urllib.parse.unquote(self.path.split('?')[0]).lstrip('/')

                if req_path.startswith("upload") or req_path.startswith("return"):
                    query_str = self.path.split('?')[1] if '?' in self.path else ''
                    params = urllib.parse.parse_qs(query_str)
                    raw_name = params.get('filename', ['field_result.zip'])[0]
                    safe_filename = os.path.basename(urllib.parse.unquote(raw_name)).strip()
                    if not safe_filename or safe_filename in ('.', '..'):
                        safe_filename = "field_result.zip"

                    try:
                        content_length = int(self.headers.get('Content-Length', 0))
                    except ValueError:
                        content_length = 0

                    max_upload_bytes = 4 * 1024 * 1024 * 1024  # 4 GB safety cap
                    if content_length <= 0 or content_length > max_upload_bytes:
                        self.send_error(400, "Invalid or empty payload size")
                        return

                    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
                    dest_dir = os.path.join(parent_self.upload_dir, f"回传_{ts}")
                    os.makedirs(dest_dir, exist_ok=True)
                    dest_path = os.path.join(dest_dir, safe_filename)

                    written = 0
                    remaining = content_length
                    try:
                        with open(dest_path, 'wb') as f:
                            while remaining > 0:
                                chunk_sz = min(65536, remaining)
                                chunk = self.rfile.read(chunk_sz)
                                if not chunk:
                                    break
                                f.write(chunk)
                                written += len(chunk)
                                remaining -= len(chunk)

                        if written < content_length:
                            try:
                                os.remove(dest_path)
                            except OSError:
                                pass
                            self.send_error(400, "Incomplete upload stream")
                            return

                        parent_self.signals.file_received.emit(client_ip, dest_path, written)

                        resp_body = json.dumps({"status": "ok", "filename": safe_filename, "size": written}).encode('utf-8')
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Content-Length", str(len(resp_body)))
                        self.end_headers()
                        self.wfile.write(resp_body)
                    except Exception as e:
                        try:
                            if os.path.exists(dest_path):
                                os.remove(dest_path)
                        except OSError:
                            pass
                        parent_self.signals.server_error.emit(f"接收文件异常: {str(e)}")
                        self.send_error(500, str(e))
                else:
                    self.send_error(404, "Not Found")

            def log_message(self, format, *args):
                # Suppress stdout logging to prevent polluting QGIS console
                pass

        import socketserver

        class _FastHTTPServer(ThreadingHTTPServer):
            allow_reuse_address = (os.name != 'nt')

            def server_bind(self):
                socketserver.TCPServer.server_bind(self)
                host, port = self.server_address[:2]
                self.server_name = host
                self.server_port = port

        # Try to bind ports starting from self.port
        bound = False
        for p in range(self.port, self.port + 20):
            try:
                self.httpd = _FastHTTPServer(('0.0.0.0', p), DropRequestHandler)
                self.httpd.daemon_threads = True
                self.port = p
                bound = True
                break
            except OSError:
                continue

        if not bound or not self.httpd:
            err = f"无法绑定端口 (8899-8919 均被占用)"
            self.signals.server_error.emit(err)
            raise RuntimeError(err)

        self._is_running = True
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        self.signals.server_started.emit(self.port)
        return self.port

    def _run_server(self):
        try:
            if self.httpd:
                self.httpd.serve_forever()
        except (socket.error, OSError):
            pass
        finally:
            self._is_running = False
            self.signals.server_stopped.emit()

    def stop(self):
        """Safely shuts down HTTP server and releases socket asynchronously."""
        httpd = self.httpd
        self.httpd = None
        self._is_running = False
        if httpd:
            def _shutdown():
                try:
                    httpd.shutdown()
                    httpd.server_close()
                except (socket.error, OSError):
                    pass
            threading.Thread(target=_shutdown, daemon=True).start()

    @property
    def is_running(self) -> bool:
        return self._is_running
