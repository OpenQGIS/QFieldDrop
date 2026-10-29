# -*- coding: utf-8 -*-
"""
QField LAN Drop - Interface UI Mockup & Step-by-Step Annotated SVG Generator
Directly renders simulated plugin UI windows with ① ② ③ callout badges.
100% full English & Chinese localization for all internal controls.
"""

import os
from typing import Dict, List, Optional


class SvgDiagramBuilder:
    """Generates high-fidelity UI window mockups with step-by-step annotations."""

    @staticmethod
    def _xml_escape(text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    @classmethod
    def get_diagram(cls, name: str, lang: str = "zh_CN", output_dir: Optional[str] = None) -> str:
        is_zh = str(lang).lower().startswith("zh")
        generator = getattr(cls, f"_build_{name}", None)
        if not generator:
            return ""

        svg_content = generator(is_zh=is_zh)

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            filename = f"{name}_{'zh' if is_zh else 'en'}.svg"
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(svg_content)
            return filepath

        return svg_content

    @classmethod
    def _wrap_svg(cls, width: int, height: int, content: str, is_zh: bool = True) -> str:
        target_w = 620
        target_h = int(height * target_w / width)
        font_family = "Microsoft YaHei" if is_zh else "Segoe UI"
        return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{target_w}" height="{target_h}" shape-rendering="geometricPrecision" text-rendering="geometricPrecision" style="max-width:100%; height:auto; display:block; margin: 12px auto; font-family: '{font_family}', sans-serif;">
  <defs>
    <filter id="win-shadow" x="-3%" y="-2%" width="106%" height="108%" filterUnits="userSpaceOnUse">
      <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#0F172A" flood-opacity="0.12"/>
    </filter>
  </defs>
  {content}
</svg>"""

    @classmethod
    def _render_badge(cls, x: int, y: int, num: str, color: str = "#EF4444") -> str:
        return f"""
    <g transform="translate({x}, {y})">
      <circle cx="0" cy="0" r="13" fill="{color}" stroke="#FFFFFF" stroke-width="2.5" />
      <text x="0" y="0.5" font-size="13" font-weight="900" fill="#FFFFFF" text-anchor="middle" dominant-baseline="central">{num}</text>
    </g>"""

    # -------------------------------------------------------------------------
    # UI 1: 投送工程窗口 (SendDialog) 实机标注
    # -------------------------------------------------------------------------
    @classmethod
    def _build_ui_send_annotated(cls, is_zh: bool) -> str:
        win_title = "QField 局域网直传 - 投送至手机 (Drop Out)" if is_zh else "QField LAN Drop - Outbound Dispatch (Drop Out)"
        ip_label = "选择分发网卡 / IP：" if is_zh else "Select Network IP:"
        ip_val = "192.168.43.120 (手机热点 / Wi-Fi)" if is_zh else "192.168.43.120 (Hotspot / Wi-Fi)"
        btn_refresh = "刷新" if is_zh else "Refresh"
        tab_qr = "📱 扫码唤醒直传" if is_zh else "📱 QR Code Wake-up"
        tab_ls = "⚡ LocalSend 直推" if is_zh else "⚡ LocalSend Push"
        qr_hint = "手机自带相机扫码，直接唤醒 QField 并自动导入" if is_zh else "Scan with phone camera to wake QField & import"
        btn_copy = "复制链接" if is_zh else "Copy URL"
        btn_repack = "重新打包" if is_zh else "Repackage"
        drawer_title = "📊 图层存储分析" if is_zh else "📊 Layer Storage Analysis"
        status_txt = "工程打包成功：共 174 MB · 局域网服务运行中" if is_zh else "Packaged successfully: 174 MB · LAN service running"
        b1_txt = "① 选择当前连接的网络 IP" if is_zh else "① Select Active Network IP"
        b2_txt = "② 手机相机扫描此二维码" if is_zh else "② Scan QR with Phone Camera"
        b3_txt = "③ 右侧透视大文件与底图" if is_zh else "③ Inspect Large Layer Sizes"

        content = f"""
  <g filter="url(#win-shadow)" transform="translate(15, 10)">
    <!-- Window Frame -->
    <rect width="730" height="390" rx="10" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1.5" />
    <rect width="730" height="34" rx="10" fill="#F1F5F9" />
    <rect y="20" width="730" height="14" fill="#F1F5F9" />
    <circle cx="16" cy="17" r="4.5" fill="#EF4444" />
    <circle cx="30" cy="17" r="4.5" fill="#F59E0B" />
    <circle cx="44" cy="17" r="4.5" fill="#10B981" />
    <text x="65" y="18" font-size="12" font-weight="600" fill="#334155" dominant-baseline="central">{cls._xml_escape(win_title)}</text>

    <!-- 1. Network IP Selector Box -->
    <g transform="translate(20, 50)">
      <rect width="450" height="48" rx="6" fill="#F8FAFC" stroke="#E2E8F0" stroke-width="1.2"/>
      <text x="14" y="24" font-size="12" font-weight="bold" fill="#1E293B" dominant-baseline="central">{cls._xml_escape(ip_label)}</text>
      <rect x="135" y="10" width="235" height="28" rx="4" fill="#FFFFFF" stroke="#94A3B8" stroke-width="1.2"/>
      <text x="145" y="24" font-size="11.5" fill="#0F172A" dominant-baseline="central">{cls._xml_escape(ip_val)}</text>
      <path d="M 355 22 L 361 28 L 367 22" fill="#64748B"/>
      <rect x="380" y="10" width="60" height="28" rx="4" fill="#E2E8F0"/>
      <text x="410" y="24" font-size="11" fill="#475569" text-anchor="middle" dominant-baseline="central">{cls._xml_escape(btn_refresh)}</text>
    </g>

    <!-- 2. Tabs & QR Code Main Box -->
    <g transform="translate(20, 110)">
      <rect width="130" height="28" rx="4" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1"/>
      <text x="65" y="14" font-size="11.5" font-weight="bold" fill="#2563EB" text-anchor="middle" dominant-baseline="central">{cls._xml_escape(tab_qr)}</text>
      <rect x="135" y="0" width="130" height="28" rx="4" fill="#F1F5F9" stroke="#E2E8F0"/>
      <text x="200" y="14" font-size="11.5" fill="#64748B" text-anchor="middle" dominant-baseline="central">{cls._xml_escape(tab_ls)}</text>

      <rect y="27" width="450" height="205" rx="6" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1"/>
      
      <!-- QR Frame -->
      <rect x="25" y="45" width="130" height="130" rx="6" fill="#F8FAFC" stroke="#E2E8F0" stroke-width="1.5"/>
      <rect x="37" y="57" width="30" height="30" fill="#0F172A"/>
      <rect x="42" y="62" width="20" height="20" fill="#F8FAFC"/>
      <rect x="47" y="67" width="10" height="10" fill="#0F172A"/>

      <rect x="113" y="57" width="30" height="30" fill="#0F172A"/>
      <rect x="118" y="62" width="20" height="20" fill="#F8FAFC"/>
      <rect x="123" y="67" width="10" height="10" fill="#0F172A"/>

      <rect x="37" y="133" width="30" height="30" fill="#0F172A"/>
      <rect x="42" y="138" width="20" height="20" fill="#F8FAFC"/>
      <rect x="47" y="143" width="10" height="10" fill="#0F172A"/>

      <rect x="75" y="75" width="28" height="28" rx="4" fill="#589632"/>
      <polygon points="89,82 82,95 96,95" fill="#FFF"/>

      <!-- QR Details -->
      <text x="175" y="65" font-size="12" font-weight="bold" fill="#0F172A">{cls._xml_escape(qr_hint)}</text>
      <rect x="175" y="80" width="250" height="26" rx="4" fill="#F1F5F9" stroke="#E2E8F0"/>
      <text x="185" y="93" font-size="10.5" fill="#3B82F6" dominant-baseline="central">qfield://open?url=http://192.168.43.120...</text>
      
      <rect x="175" y="120" width="115" height="32" rx="4" fill="#2563EB"/>
      <text x="232" y="136" font-size="12" font-weight="bold" fill="#FFF" text-anchor="middle" dominant-baseline="central">{cls._xml_escape(btn_copy)}</text>

      <rect x="300" y="120" width="115" height="32" rx="4" fill="#FFFFFF" stroke="#94A3B8"/>
      <text x="357" y="136" font-size="12" fill="#334155" text-anchor="middle" dominant-baseline="central">{cls._xml_escape(btn_repack)}</text>
    </g>

    <!-- RIGHT DRAWER: Treemap Analysis -->
    <g transform="translate(485, 45)">
      <rect width="225" height="270" rx="6" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.2"/>
      <rect width="225" height="30" rx="6" fill="#E2E8F0"/>
      <text x="14" y="16" font-size="11.5" font-weight="bold" fill="#1E293B" dominant-baseline="central">{cls._xml_escape(drawer_title)}</text>
      
      <g transform="translate(10, 40)">
        <rect width="120" height="130" fill="#3B82F6" opacity="0.85" rx="3" stroke="#FFF"/>
        <text x="60" y="60" font-size="10" font-weight="bold" fill="#FFF" text-anchor="middle">DOM.tif</text>
        <text x="60" y="75" font-size="9" fill="#E0F2FE" text-anchor="middle">128 MB</text>

        <rect x="125" width="80" height="75" fill="#10B981" opacity="0.85" rx="3" stroke="#FFF"/>
        <text x="165" y="35" font-size="9.5" font-weight="bold" fill="#FFF" text-anchor="middle">survey.gpkg</text>
        <text x="165" y="48" font-size="8.5" fill="#DCFCE7" text-anchor="middle">34 MB</text>

        <rect x="125" y="80" width="80" height="50" fill="#F59E0B" opacity="0.85" rx="3" stroke="#FFF"/>
        <text x="165" y="105" font-size="9" fill="#FFF" text-anchor="middle">base.qml</text>

        <rect y="135" width="205" height="75" fill="#8B5CF6" opacity="0.85" rx="3" stroke="#FFF"/>
        <text x="102" y="172" font-size="10.5" font-weight="bold" fill="#FFF" text-anchor="middle">Project.qgz (12 MB)</text>
      </g>
    </g>

    <!-- Bottom Status Bar -->
    <rect x="1" y="350" width="728" height="38" rx="0 0 10 10" fill="#F8FAFC" stroke="#E2E8F0"/>
    <circle cx="25" cy="369" r="4.5" fill="#10B981"/>
    <text x="38" y="369" font-size="11.5" fill="#475569" dominant-baseline="central">{cls._xml_escape(status_txt)}</text>
  </g>

  <!-- Badges -->
  {cls._render_badge(x=155, y=48, num="1", color="#2563EB")}
  {cls._render_badge(x=115, y=210, num="2", color="#EF4444")}
  {cls._render_badge(x=500, y=45, num="3", color="#10B981")}

  <!-- Bottom Annotation Explanations -->
  <g transform="translate(40, 420)">
    <rect width="680" height="36" rx="6" fill="#F1F5F9" stroke="#E2E8F0"/>
    <text x="20" y="18" font-size="12" font-weight="bold" fill="#2563EB" dominant-baseline="central">{cls._xml_escape(b1_txt)}</text>
    <text x="245" y="18" font-size="12" font-weight="bold" fill="#DC2626" dominant-baseline="central">{cls._xml_escape(b2_txt)}</text>
    <text x="470" y="18" font-size="12" font-weight="bold" fill="#16A34A" dominant-baseline="central">{cls._xml_escape(b3_txt)}</text>
  </g>
"""
        return cls._wrap_svg(760, 470, content, is_zh=is_zh)

    # -------------------------------------------------------------------------
    # UI 2: 接收成果窗口 (ReceiveDialog) 实机标注
    # -------------------------------------------------------------------------
    @classmethod
    def _build_ui_receive_annotated(cls, is_zh: bool) -> str:
        win_title = "QField 成果接收 - 手机外业回传 (Drop In)" if is_zh else "QField Inbound Return (Drop In)"
        tbl_title = "已接收的外业成果台账记录" if is_zh else "Received Survey Packages Ledger"
        btn_load = "载入至当前工程" if is_zh else "Load into QGIS"
        btn_open = "打开所在目录" if is_zh else "Open Folder"
        banner_title = "手机扫码极速回传外业成果" if is_zh else "Scan QR to Upload Field Survey Data"
        banner_desc = "手机相机或浏览器扫码，直接打开网页选择 GPKG 矢量包或现场照片上传" if is_zh else "Scan with phone camera or browser to select GPKG or photos"
        btn_copy_url = "复制回传网址" if is_zh else "Copy Return URL"
        col_fn = "文件名" if is_zh else "Filename"
        col_sz = "大小" if is_zh else "Size"
        col_tm = "接收时间" if is_zh else "Time"
        col_dev = "来源设备" if is_zh else "Device"
        b1_txt = "① 手机扫码打开上传页" if is_zh else "① Scan QR for Upload Web"
        b2_txt = "② 成果自动进入台账记录" if is_zh else "② Results Listed in Table"
        b3_txt = "③ 一键载入地图对比质检" if is_zh else "③ Load to Canvas for QA"

        content = f"""
  <g filter="url(#win-shadow)" transform="translate(15, 10)">
    <!-- Frame -->
    <rect width="730" height="380" rx="10" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1.5" />
    <rect width="730" height="34" rx="10" fill="#F1F5F9" />
    <rect y="20" width="730" height="14" fill="#F1F5F9" />
    <circle cx="16" cy="17" r="4.5" fill="#EF4444" />
    <circle cx="30" cy="17" r="4.5" fill="#F59E0B" />
    <circle cx="44" cy="17" r="4.5" fill="#10B981" />
    <text x="65" y="18" font-size="12" font-weight="600" fill="#334155" dominant-baseline="central">{cls._xml_escape(win_title)}</text>

    <!-- Top Web Scanner Section -->
    <g transform="translate(20, 50)">
      <rect width="690" height="135" rx="6" fill="#F8FAFC" stroke="#E2E8F0" stroke-width="1"/>
      
      <rect x="20" y="15" width="105" height="105" rx="6" fill="#FFFFFF" stroke="#CBD5E1"/>
      <rect x="30" y="25" width="24" height="24" fill="#0F172A"/>
      <rect x="90" y="25" width="24" height="24" fill="#0F172A"/>
      <rect x="30" y="85" width="24" height="24" fill="#0F172A"/>
      <rect x="62" y="57" width="22" height="22" rx="3" fill="#2563EB"/>
      <polygon points="73,63 67,73 79,73" fill="#FFF"/>

      <text x="145" y="32" font-size="13" font-weight="bold" fill="#0F172A">{cls._xml_escape(banner_title)}</text>
      <text x="145" y="54" font-size="11.5" fill="#64748B">{cls._xml_escape(banner_desc)}</text>
      
      <rect x="145" y="70" width="320" height="26" rx="4" fill="#FFFFFF" stroke="#CBD5E1"/>
      <text x="155" y="83" font-size="11" fill="#2563EB" dominant-baseline="central">http://192.168.43.120:8899/return</text>

      <rect x="480" y="70" width="110" height="26" rx="4" fill="#E2E8F0"/>
      <text x="535" y="83" font-size="11" fill="#334155" text-anchor="middle" dominant-baseline="central">{cls._xml_escape(btn_copy_url)}</text>
    </g>

    <!-- Bottom Records Table -->
    <g transform="translate(20, 200)">
      <text x="5" y="12" font-size="12" font-weight="bold" fill="#1E293B">{cls._xml_escape(tbl_title)}</text>
      <rect y="22" width="690" height="26" fill="#F1F5F9" stroke="#E2E8F0"/>
      <text x="15" y="35" font-size="11" font-weight="bold" fill="#475569" dominant-baseline="central">{cls._xml_escape(col_fn)}</text>
      <text x="260" y="35" font-size="11" font-weight="bold" fill="#475569" dominant-baseline="central">{cls._xml_escape(col_sz)}</text>
      <text x="360" y="35" font-size="11" font-weight="bold" fill="#475569" dominant-baseline="central">{cls._xml_escape(col_tm)}</text>
      <text x="520" y="35" font-size="11" font-weight="bold" fill="#475569" dominant-baseline="central">{cls._xml_escape(col_dev)}</text>

      <!-- Row 1 -->
      <rect y="48" width="690" height="28" fill="#EFF6FF" stroke="#BFDBFE"/>
      <text x="15" y="62" font-size="11.5" font-weight="bold" fill="#1D4ED8" dominant-baseline="central">📄 field_survey_20261028.gpkg</text>
      <text x="260" y="62" font-size="11" fill="#1E293B" dominant-baseline="central">14.8 MB</text>
      <text x="360" y="62" font-size="11" fill="#475569" dominant-baseline="central">17:42:05</text>
      <text x="520" y="62" font-size="11" fill="#10B981" font-weight="bold" dominant-baseline="central">Redmi Note 12</text>

      <g transform="translate(0, 88)">
        <rect width="135" height="32" rx="4" fill="#589632"/>
        <text x="67" y="16" font-size="12" font-weight="bold" fill="#FFF" text-anchor="middle" dominant-baseline="central">{cls._xml_escape(btn_load)}</text>

        <rect x="145" width="115" height="32" rx="4" fill="#FFFFFF" stroke="#94A3B8"/>
        <text x="202" y="16" font-size="12" fill="#334155" text-anchor="middle" dominant-baseline="central">{cls._xml_escape(btn_open)}</text>
      </g>
    </g>
  </g>

  <!-- Badges -->
  {cls._render_badge(x=80, y=95, num="1", color="#2563EB")}
  {cls._render_badge(x=380, y=240, num="2", color="#F59E0B")}
  {cls._render_badge(x=100, y=320, num="3", color="#16A34A")}

  <!-- Bottom Annotation Explanations -->
  <g transform="translate(40, 410)">
    <rect width="680" height="36" rx="6" fill="#F1F5F9" stroke="#E2E8F0"/>
    <text x="20" y="18" font-size="12" font-weight="bold" fill="#2563EB" dominant-baseline="central">{cls._xml_escape(b1_txt)}</text>
    <text x="245" y="18" font-size="12" font-weight="bold" fill="#D97706" dominant-baseline="central">{cls._xml_escape(b2_txt)}</text>
    <text x="470" y="18" font-size="12" font-weight="bold" fill="#16A34A" dominant-baseline="central">{cls._xml_escape(b3_txt)}</text>
  </g>
"""
        return cls._wrap_svg(760, 460, content, is_zh=is_zh)

    # -------------------------------------------------------------------------
    # UI 3: 手机助手安装窗口 (MobileInstallDialog) 实机标注
    # -------------------------------------------------------------------------
    @classmethod
    def _build_ui_mobile_annotated(cls, is_zh: bool) -> str:
        win_title = "QField 手机助手安装 (移动端独立伴侣)" if is_zh else "QField Mobile Companion Setup"
        tab1_title = "方式一：QField 扫码直装" if is_zh else "Method 1: QField QR Install"
        tab2_title = "方式二：ADB 数据线写入" if is_zh else "Method 2: ADB Push"
        
        step1_h = "在 QField 内部安装伴侣插件：" if is_zh else "Install companion inside QField:"
        step1_d1 = "1. 手机打开 QField ➔ 设置 ➔【插件】➔【从 URL 安装】" if is_zh else "1. Open QField ➔ Settings ➔ [Plugins] ➔ [Install from URL]"
        step1_d2 = "2. 点击输入框右侧的【📷 扫一扫】图标，扫描左侧二维码" if is_zh else "2. Tap [📷 Camera Scanner] icon, scan the QR code"
        step2_h = "无摄像头设备手动安装地址：" if is_zh else "Manual download URL for rugged devices:"
        btn_adb_txt = "⚡ ADB 数据线一键写入" if is_zh else "⚡ USB / ADB One-Click Push"

        b1_txt = "① 打开 QField [从URL安装] 扫码" if is_zh else "① QField [Install from URL] Scan"
        b2_txt = "② 手动填写显示的本地网址" if is_zh else "② Or Enter Download URL"
        b3_txt = "③ 有线连接点击一键写入" if is_zh else "③ Or USB 1-Click ADB Push"

        content = f"""
  <g filter="url(#win-shadow)" transform="translate(20, 10)">
    <rect width="720" height="340" rx="10" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1.5" />
    <rect width="720" height="34" rx="10" fill="#F1F5F9" />
    <rect y="20" width="720" height="14" fill="#F1F5F9" />
    <circle cx="16" cy="17" r="4.5" fill="#EF4444" />
    <circle cx="30" cy="17" r="4.5" fill="#F59E0B" />
    <circle cx="44" cy="17" r="4.5" fill="#10B981" />
    <text x="65" y="18" font-size="12" font-weight="600" fill="#334155" dominant-baseline="central">{cls._xml_escape(win_title)}</text>

    <!-- Tab Buttons -->
    <g transform="translate(20, 50)">
      <rect width="180" height="30" rx="4" fill="#FFFFFF" stroke="#CBD5E1"/>
      <text x="90" y="15" font-size="12" font-weight="bold" fill="#2563EB" text-anchor="middle" dominant-baseline="central">{cls._xml_escape(tab1_title)}</text>
      
      <rect x="190" width="180" height="30" rx="4" fill="#F1F5F9" stroke="#E2E8F0"/>
      <text x="280" y="15" font-size="12" fill="#64748B" text-anchor="middle" dominant-baseline="central">{cls._xml_escape(tab2_title)}</text>

      <!-- Tab Content Area -->
      <rect y="29" width="680" height="235" rx="6" fill="#FFFFFF" stroke="#CBD5E1"/>
      
      <!-- Left QR Box -->
      <rect x="25" y="45" width="135" height="135" rx="6" fill="#F8FAFC" stroke="#E2E8F0"/>
      <rect x="40" y="60" width="26" height="26" fill="#0F172A"/>
      <rect x="115" y="60" width="26" height="26" fill="#0F172A"/>
      <rect x="40" y="135" width="26" height="26" fill="#0F172A"/>
      <rect x="75" y="95" width="24" height="24" rx="4" fill="#0284C7"/>
      <text x="87" y="108" font-size="13" font-weight="bold" fill="#FFF" text-anchor="middle" dominant-baseline="central">Q</text>

      <!-- Right Steps -->
      <g transform="translate(180, 45)">
        <text y="15" font-size="13" font-weight="bold" fill="#0F172A">{cls._xml_escape(step1_h)}</text>
        <text y="40" font-size="12" fill="#475569">{cls._xml_escape(step1_d1)}</text>
        <text y="65" font-size="12" fill="#475569">{cls._xml_escape(step1_d2)}</text>
        
        <!-- URL Fallback -->
        <text y="105" font-size="12" font-weight="bold" fill="#0F172A">{cls._xml_escape(step2_h)}</text>
        <rect y="115" width="460" height="28" rx="4" fill="#F1F5F9" stroke="#CBD5E1"/>
        <text x="12" y="129" font-size="11.5" fill="#3B82F6" dominant-baseline="central">http://192.168.43.120:8899/mobile.zip</text>

        <rect y="160" width="220" height="32" rx="4" fill="#6366F1"/>
        <text x="110" y="176" font-size="12" font-weight="bold" fill="#FFF" text-anchor="middle" dominant-baseline="central">{cls._xml_escape(btn_adb_txt)}</text>
      </g>
    </g>
  </g>

  <!-- Badges -->
  {cls._render_badge(x=115, y=145, num="1", color="#2563EB")}
  {cls._render_badge(x=420, y=210, num="2", color="#0284C7")}
  {cls._render_badge(x=380, y=270, num="3", color="#6366F1")}

  <!-- Explanations -->
  <g transform="translate(40, 370)">
    <rect width="680" height="36" rx="6" fill="#F1F5F9" stroke="#E2E8F0"/>
    <text x="20" y="18" font-size="12" font-weight="bold" fill="#2563EB" dominant-baseline="central">{cls._xml_escape(b1_txt)}</text>
    <text x="245" y="18" font-size="12" font-weight="bold" fill="#0284C7" dominant-baseline="central">{cls._xml_escape(b2_txt)}</text>
    <text x="470" y="18" font-size="12" font-weight="bold" fill="#4F46E5" dominant-baseline="central">{cls._xml_escape(b3_txt)}</text>
  </g>
"""
        return cls._wrap_svg(760, 420, content, is_zh=is_zh)
