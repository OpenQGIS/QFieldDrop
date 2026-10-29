# 📥 03. Receive Results from Field (Drop In)

Upon returning from field surveying, click **`[ 📥 Drop In (Receive from QField) ]`** on the toolbar to open the receiver in **< 0.1s**.

<div class="mockup-window">
  <div class="mockup-titlebar">
    <span class="mockup-dot red"></span><span class="mockup-dot yellow"></span><span class="mockup-dot green"></span>
    &nbsp;<b>QField LAN Drop - Receive Field Results (Drop In)</b>
  </div>
  <div style="padding: 8px 14px; background-color: #F8FAFC; border-bottom: 1px solid #E2E8F0; font-size: 12px; color: #475569;">
    📁 Project: <b>Field_Survey_2026.qgz</b> &nbsp;|&nbsp; Archive Dir: <span style="font-family: monospace; color: #2563EB;">.../_qfield_return/</span>
  </div>
  <div class="mockup-body">
    <!-- Top: QR Upload Channel -->
    <div style="border: 1px solid #CBD5E1; border-radius: 6px; background-color: #FFFFFF; padding: 10px; margin-bottom: 10px;">
      <table width="100%" border="0" cellpadding="4" style="border: none;">
        <tr style="border: none; background: transparent;">
          <td width="115" align="center" valign="middle" style="border: none;">
            <img src="../../assets/diagrams/qr_sample.svg" width="95" height="95" style="display: block; margin: 0 auto;" />
            <div style="margin-top: 4px;"><span class="step-badge blue">①</span><b>Scan QR</b></div>
          </td>
          <td valign="top" style="border: none; padding-left: 10px;">
            <div style="margin-bottom: 6px;">
              <b>Receiver Network:</b>
              <span class="mockup-input">192.168.43.120 (Hotspot / Wi-Fi) ▼</span>
            </div>
            <div style="font-size: 12.5px; color: #334155; line-height: 1.5; margin-bottom: 6px;">
              <b>Mobile Return Instructions:</b><br>
              1. Scan the QR code with your mobile camera to open the lightweight uploader;<br>
              2. Select updated vector layers or survey photos, then tap [Send to PC].
            </div>
            <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 4px 6px; border-radius: 4px; font-family: monospace; font-size: 11px; color: #2563EB;">
              http://192.168.43.120:8899/upload &nbsp;
              <span class="qgis-btn">Copy Upload URL</span>
            </div>
          </td>
        </tr>
      </table>
    </div>

    <!-- Bottom: Received Archives Table -->
    <div style="border: 1px solid #CBD5E1; border-radius: 6px; background-color: #FFFFFF; padding: 10px;">
      <div style="font-size: 12px; font-weight: bold; color: #1E293B; margin-bottom: 8px;">
        <span class="step-badge green">②</span> <b>Received Field Survey Records (Isolated & Safe, Won't Overwrite)</b>
      </div>
      <table width="100%" border="0" cellpadding="6" style="border-collapse: collapse; font-size: 11.5px; margin-bottom: 8px;">
        <tr style="background-color: #F1F5F9; border-bottom: 1px solid #CBD5E1; font-weight: bold; color: #475569;">
          <th align="left" style="padding: 5px 8px;">Received Time</th>
          <th align="left" style="padding: 5px 8px;">Filename</th>
          <th align="center" style="padding: 5px 8px;">Size</th>
          <th align="left" style="padding: 5px 8px;">Source Device</th>
        </tr>
        <tr style="background-color: #EFF6FF; border-bottom: 1px solid #E2E8F0;">
          <td style="padding: 6px 8px; color: #1E40AF; font-weight: bold;">17:42:08</td>
          <td style="padding: 6px 8px; font-family: monospace; color: #1E40AF; font-weight: bold;">survey_return_20261029.gpkg</td>
          <td align="center" style="padding: 6px 8px; color: #1E40AF;">34.2 MB</td>
          <td style="padding: 6px 8px; color: #1E40AF;">Xiaomi 13 (192.168.43.55)</td>
        </tr>
        <tr style="background-color: #FFFFFF; border-bottom: 1px solid #E2E8F0;">
          <td style="padding: 6px 8px; color: #64748B;">17:35:14</td>
          <td style="padding: 6px 8px; font-family: monospace; color: #334155;">photos_site_north.zip</td>
          <td align="center" style="padding: 6px 8px; color: #64748B;">18.6 MB</td>
          <td style="padding: 6px 8px; color: #64748B;">Honor 90 (192.168.43.82)</td>
        </tr>
      </table>
      <div>
        <span class="step-badge purple">③</span>
        <span class="qgis-btn-blue">Load into QGIS Canvas (QA / Inspect)</span>&nbsp;
        <span class="qgis-btn">Open Folder</span>&nbsp;
        <span class="qgis-btn">Extract Zip</span>
      </div>
    </div>
  </div>
  <div class="mockup-footer">
    <span class="step-badge blue">①</span> Scan QR with phone to upload &nbsp;&nbsp;|&nbsp;&nbsp; 
    <span class="step-badge green">②</span> View received return ledger &nbsp;&nbsp;|&nbsp;&nbsp; 
    <span class="step-badge purple">③</span> Load into QGIS map canvas for QA inspection
  </div>
</div>

---

## 🎯 Step-by-Step UI Guide

### Badge ①: Scan QR to Upload from Phone
1. Scan the screen QR code with your phone's native camera;
2. A lightweight upload web page opens in your mobile browser;
3. Tap **【Select Files】** to pick modified `.gpkg` layers, ZIP files, or field photos;
4. Tap **「🚀 Send to PC」**; files transfer immediately to your PC.

---

### Badge ②: Review Received Results Ledger
* Received files are automatically listed in the table;
* Displays filename, size, timestamp, and client device name;
* Stored safely under `_qfield_return/` without overwriting master project data.

---

### Badge ③: Load into QGIS Canvas for QA
* Select a record in the ledger;
* Click **"Load into QGIS"**;
* The layer loads directly onto the QGIS map canvas for instant inspection!

---

👉 Connectivity issues? Read: [🌐 04. Field Networking Guide](chapter:network_guide).
