# -*- coding: utf-8 -*-
"""
Lightweight Multicast DNS (mDNS / Bonjour) Responder for QGIS LAN Drop.
Broadcasts 'qgis-drop.local' on 224.0.0.251:5353.
Allows mobile devices to access http://qgis-drop.local:8899/project.zip
without needing to manually type or memorize fluctuating local IP addresses.
"""

import socket
import struct
import threading
from typing import Optional

MDNS_GROUP = "224.0.0.251"
MDNS_PORT = 5353


class MdnsResponder:
    def __init__(self, hostname: str = "qgis-drop.local", ip_address: str = "127.0.0.1"):
        self.hostname = hostname.rstrip('.').lower()
        self.ip_address = ip_address
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._sock: Optional[socket.socket] = None

    def start(self):
        if self._running or not self.ip_address or self.ip_address.startswith("127."):
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def update_ip(self, ip_address: str):
        self.ip_address = ip_address
        if not self._running and self.ip_address and not self.ip_address.startswith("127."):
            self.start()

    def stop(self):
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            except (socket.error, OSError):
                pass
            self._sock = None

    def _encode_domain(self, domain: str) -> bytes:
        parts = domain.split('.')
        res = b''
        for p in parts:
            b = p.encode('utf-8')
            res += bytes([len(b)]) + b
        return res + b'\x00'

    def _decode_domain(self, data: bytes, offset: int, depth: int = 0) -> tuple[str, int]:
        if depth > 10:
            return "", len(data)
        parts = []
        curr = offset
        data_len = len(data)
        while curr < data_len:
            length = data[curr]
            if length == 0:
                curr += 1
                break
            if (length & 0xC0) == 0xC0:
                if curr + 1 >= data_len:
                    return "", data_len
                ptr_offset = struct.unpack("!H", data[curr:curr+2])[0] & 0x3FFF
                if ptr_offset >= data_len or ptr_offset == offset:
                    return "", data_len
                sub_name, _ = self._decode_domain(data, ptr_offset, depth + 1)
                if sub_name:
                    parts.append(sub_name)
                curr += 2
                return ".".join(parts), curr
            curr += 1
            if curr + length > data_len:
                return "", data_len
            parts.append(data[curr:curr+length].decode('utf-8', errors='ignore'))
            curr += length
        return ".".join(parts), curr

    def _build_response(self, tx_id: int) -> bytes:
        # Standard DNS response header
        # Flags: QR=1 (response), AA=1 (authoritative) -> 0x8400
        header = struct.pack("!HHHHHH", tx_id, 0x8400, 0, 1, 0, 0)
        qname = self._encode_domain(self.hostname)
        # Type A (1), Class IN (1), TTL (120), RDLENGTH (4), RDATA (4 bytes IP)
        ip_bytes = socket.inet_aton(self.ip_address)
        record = qname + struct.pack("!HHIH", 1, 1 | 0x8000, 120, 4) + ip_bytes
        return header + record

    def _run(self):
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Bind to 5353
            try:
                self._sock.bind(('', MDNS_PORT))
                mreq = struct.pack("4sl", socket.inet_aton(MDNS_GROUP), socket.INADDR_ANY)
                self._sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            except Exception:
                # If 5353 is already bound exclusively, mDNS responder gracefully stops
                return

            self._sock.settimeout(2.0)

            while self._running:
                try:
                    data, addr = self._sock.recvfrom(2048)
                    if len(data) < 12:
                        continue
                    tx_id, flags, qdcount = struct.unpack("!HHH", data[:6])
                    is_query = (flags & 0x8000) == 0
                    if not is_query or qdcount < 1:
                        continue

                    # Parse query name
                    qname, _ = self._decode_domain(data, 12)
                    if qname.lower() == self.hostname:
                        resp = self._build_response(tx_id)
                        # Respond to mDNS multicast group
                        self._sock.sendto(resp, (MDNS_GROUP, MDNS_PORT))
                except (socket.timeout, struct.error, ValueError, IndexError, OSError):
                    continue
        except (socket.error, OSError):
            pass
        finally:
            if self._sock:
                try:
                    self._sock.close()
                except (socket.error, OSError):
                    pass
