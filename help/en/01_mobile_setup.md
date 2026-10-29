# 📱 01. Mobile Companion Setup

First-time setup requires installing the companion plugin onto your mobile device once.

<div class="mockup-window">
  <div class="mockup-titlebar">
    <span class="mockup-dot red"></span><span class="mockup-dot yellow"></span><span class="mockup-dot green"></span>
    &nbsp;<b>QField Mobile Companion Setup</b>
  </div>
  <div style="padding: 8px 14px; background-color: #F8FAFC; border-bottom: 1px solid #E2E8F0;">
    <span class="mockup-tab-active">Method 1: QField QR Install</span>&nbsp;&nbsp;
    <span class="mockup-tab-inactive">Method 2: ADB Push</span>
  </div>
  <div class="mockup-body">
    <table width="100%" border="0" cellpadding="4" style="border: none;">
      <tr style="border: none; background: transparent;">
        <td width="130" align="center" valign="top" style="border: none; background-color: #F8FAFC; padding: 10px; border-radius: 6px;">
          <img src="../../assets/diagrams/qr_sample.svg" width="105" height="105" style="margin: 0 auto; display: block;" />
          <div style="margin-top: 6px;"><span class="step-badge blue">①</span><b>Scan QR</b></div>
        </td>
        <td valign="top" style="border: none; padding-left: 16px;">
          <p style="font-size: 13.5px; font-weight: bold; color: #0F172A; margin-bottom: 6px;">
            Install companion inside QField:
          </p>
          <p style="font-size: 13px; color: #334155; margin-bottom: 4px;">
            1. Open <b>QField</b> on phone ➔ tap top-left menu ➔ <b>【Settings】</b> ➔ <b>【Plugins】</b> ➔ <b>【Install from URL】</b>
          </p>
          <p style="font-size: 13px; color: #334155; margin-bottom: 10px;">
            2. Tap the <b>【📷 Camera Scanner】</b> icon on the right, point at the QR code to auto-install
          </p>
          <p style="font-size: 13px; font-weight: bold; color: #0F172A; margin-bottom: 4px;">
            <span class="step-badge green">②</span> Manual download URL for rugged devices:
          </p>
          <div style="background-color: #F1F5F9; border: 1px solid #CBD5E1; padding: 4px 8px; border-radius: 4px; font-family: monospace; font-size: 12.5px; color: #2563EB; margin-bottom: 10px;">
            http://192.168.43.120:8899/mobile.zip
          </div>
          <div>
            <span class="step-badge purple">③</span>
            <span style="background-color: #6366F1; color: #FFFFFF; font-weight: bold; padding: 5px 12px; border-radius: 4px; font-size: 12px; display: inline-block;">
              ⚡ USB / ADB One-Click Push
            </span>
          </div>
        </td>
      </tr>
    </table>
  </div>
  <div class="mockup-footer">
    <span class="step-badge blue">①</span> QField [Install from URL] Scan &nbsp;&nbsp;|&nbsp;&nbsp; 
    <span class="step-badge green">②</span> Manual Download URL &nbsp;&nbsp;|&nbsp;&nbsp; 
    <span class="step-badge purple">③</span> USB 1-Click ADB Push
  </div>
</div>

---

## 🛠️ Step-by-Step UI Guide

Click **`[ 📱 Mobile Setup ]`** on the toolbar to open the installer dialog:

### Badge ①: In-App QField QR Scanner (⭐ Recommended)
1. Open **QField** on your mobile phone;
2. Tap top-left menu ➔ **【Settings】** ➔ **【Plugins】** tab;
3. Tap **【Install from URL】**, then tap the **【📷 Camera Scanner】** icon;
4. Point at the QR code on your PC screen; QField will auto-install and enable it.

---

### Badge ②: Manual URL for Rugged Devices
For field devices without a rear camera:
* In QField's 【Install from URL】 box, type the address shown:
  ```plaintext
  http://192.168.43.120:8899/mobile.zip
  ```
* Tap OK to install.

---

### Badge ③: One-Click USB Cable Injection
If you have a USB cable connected:
1. Connect phone with **USB Debugging** enabled;
2. Click **"⚡ ADB Push"** on your PC;
3. The plugin silently writes into QField's private sandbox folder!

---

👉 Next: [📤 02. Send Project to Mobile (Drop Out)](chapter:send_project).
