# 📤 02. Send Project to Mobile (Drop Out)

Click **`[ 📤 Drop Out (Send to QField) ]`** on the toolbar to auto-package and dispatch the current project.

<div class="mockup-window">
  <div class="mockup-titlebar">
    <span class="mockup-dot red"></span><span class="mockup-dot yellow"></span><span class="mockup-dot green"></span>
    &nbsp;<b>QField LAN Drop - Send to Mobile (Drop Out)</b>
  </div>
  <div style="padding: 10px 14px; background-color: #F8FAFC; border-bottom: 1px solid #E2E8F0;">
    <span class="step-badge blue">①</span> <b>Network Adapter / IP:</b>
    <span class="mockup-input">192.168.43.120 (Hotspot / Wi-Fi) ▼</span>&nbsp;
    <span class="qgis-btn">Refresh</span>
  </div>
  <div class="mockup-body">
    <table width="100%" border="0" cellpadding="4" style="border: none;">
      <tr style="border: none; background: transparent;">
        <!-- Left: QR Code Box -->
        <td width="60%" valign="top" style="border: none; padding-right: 14px;">
          <div style="margin-bottom: 8px;">
            <span class="mockup-tab-active">📱 QR Direct</span>&nbsp;
            <span class="mockup-tab-inactive">⚡ LocalSend</span>&nbsp;
            <span class="mockup-tab-inactive">📦 Package Download</span>&nbsp;
            <span class="mockup-tab-inactive">🔌 USB Wired</span>
          </div>
          <table width="100%" border="0" cellpadding="6" style="border: 1px solid #CBD5E1; border-radius: 6px; background-color: #FFFFFF;">
            <tr style="border: none; background: transparent;">
              <td width="115" align="center" valign="middle" style="border: none;">
                <img src="../../assets/diagrams/qr_sample.svg" width="95" height="95" style="display: block; margin: 0 auto;" />
                <div style="margin-top: 4px;"><span class="step-badge red">②</span><b>Scan QR</b></div>
              </td>
              <td valign="top" style="border: none; padding-left: 8px;">
                <div style="font-size: 12.5px; font-weight: bold; color: #0F172A; margin-bottom: 6px;">
                  Scan with mobile camera to wake up QField and import project
                </div>
                <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 4px 6px; border-radius: 4px; font-family: monospace; font-size: 11px; color: #2563EB; margin-bottom: 8px;">
                  qfield://open?url=http://192.168.43.120...
                </div>
                <div>
                  <span class="qgis-btn-blue">Copy Link</span>&nbsp;
                  <span class="qgis-btn">Repack</span>
                </div>
              </td>
            </tr>
          </table>
        </td>
        <!-- Right: Treemap Box -->
        <td width="40%" valign="top" style="border: 1px solid #CBD5E1; border-radius: 6px; background-color: #F8FAFC; padding: 8px;">
          <div style="font-size: 12px; font-weight: bold; color: #1E293B; margin-bottom: 6px;">
            <span class="step-badge green">③</span> <b>📊 Layer Storage Treemap</b>
          </div>
          <table width="100%" border="0" cellpadding="4" style="border-collapse: separate; border-spacing: 2px;">
            <tr style="border: none;">
              <td colspan="2" style="background-color: #3B82F6; color: #FFF; font-weight: bold; font-size: 11px; text-align: center; padding: 8px; border-radius: 4px;">
                DOM.tif (128 MB Raster)
              </td>
            </tr>
            <tr style="border: none;">
              <td width="55%" style="background-color: #10B981; color: #FFF; font-weight: bold; font-size: 10px; text-align: center; padding: 6px; border-radius: 4px;">
                survey.gpkg (34 MB)
              </td>
              <td width="45%" style="background-color: #F59E0B; color: #FFF; font-weight: bold; font-size: 10px; text-align: center; padding: 6px; border-radius: 4px;">
                base.qml
              </td>
            </tr>
            <tr style="border: none;">
              <td colspan="2" style="background-color: #8B5CF6; color: #FFF; font-weight: bold; font-size: 11px; text-align: center; padding: 6px; border-radius: 4px;">
                Project.qgz (12 MB Project)
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </div>
  <div class="mockup-footer">
    <span class="step-badge blue">①</span> Select shared network IP &nbsp;&nbsp;|&nbsp;&nbsp; 
    <span class="step-badge red">②</span> Scan QR code with mobile camera &nbsp;&nbsp;|&nbsp;&nbsp; 
    <span class="step-badge green">③</span> Inspect layer storage breakdown
  </div>
</div>

---

## 🎯 Step-by-Step UI Guide

### Badge ①: Verify Network IP
* Select the network shared between your PC and phone:
  * **In the Field**: Choose the phone hotspot subnet (usually `192.168.43.x`);
  * **In the Office**: Choose the Wi-Fi router subnet (e.g. `192.168.1.x`).

---

### Badge ②: Scan QR Code with Phone
1. Open your phone's native camera, browser, or QR scanner;
2. Scan the QR code displayed in the center of the screen;
3. Once downloaded, **QField automatically launches, unzips, and opens the project**.

> [!TIP]
> You can also switch to **"⚡ LocalSend"** for auto device discovery, use **"📦 Package Download"** to export offline ZIP files, or switch to **"🔌 USB Wired"** to inject directly over cable!

---

### Badge ③: Treemap Storage Inspection (Optional)
* The color treemap on the right visualizes layer sizes in your project folder;
* Spot oversized basemaps before dispatching to save mobile storage space.

---

👉 Field survey finished? Read: [📥 03. Receive Results from Field (Drop In)](chapter:receive_results).
