# 🌐 04. Field Networking Guide

In field surveys, 90% of connection failures are due to **mismatched network subnets or topology**. This chapter details the best connection setups for 4 typical field environments.

<table width="100%" border="0" cellpadding="8" style="border-collapse: separate; border-spacing: 8px; margin: 12px 0;">
  <tr>
    <td width="50%" valign="top" style="border: 1.5px solid #3B82F6; border-radius: 8px; background-color: #EFF6FF; padding: 12px;">
      <div style="font-size: 13.5px; font-weight: bold; color: #1E40AF; margin-bottom: 6px;">
        ⭐ Option A: Mobile Hotspot ➔ PC Connects (Field Recommended)
      </div>
      <div style="font-size: 12.5px; color: #1E3A8A; line-height: 1.6;">
        📱 Turn on Personal Hotspot on phone (gateway usually 192.168.43.1)<br>
        💻 Connect PC Wi-Fi to phone's hotspot<br>
        ⚡ <b>Zero cell reception needed! High-speed Gigabit LAN connection works everywhere.</b>
      </div>
    </td>
    <td width="50%" valign="top" style="border: 1.5px solid #CBD5E1; border-radius: 8px; background-color: #F8FAFC; padding: 12px;">
      <div style="font-size: 13.5px; font-weight: bold; color: #0F172A; margin-bottom: 6px;">
        Option B: PC Hotspot ➔ Mobile Connects
      </div>
      <div style="font-size: 12.5px; color: #334155; line-height: 1.6;">
        💻 Turn on Windows Mobile Hotspot on PC<br>
        📱 Connect phone Wi-Fi to PC (usually 192.168.137.1)<br>
        🚙 Ideal for fixed in-vehicle field computers or laptops
      </div>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top" style="border: 1.5px solid #CBD5E1; border-radius: 8px; background-color: #F8FAFC; padding: 12px;">
      <div style="font-size: 13.5px; font-weight: bold; color: #0F172A; margin-bottom: 6px;">
        Option C: Basecamp / Office Shared Wi-Fi
      </div>
      <div style="font-size: 12.5px; color: #334155; line-height: 1.6;">
        🏠 Connect both PC and mobile to the same Wi-Fi router<br>
        🌐 Select PC's LAN IP assigned by router (192.168.1.x)<br>
        ⚠️ If AP isolation is enabled by hotel/enterprise, switch to Option A
      </div>
    </td>
    <td width="50%" valign="top" style="border: 1.5px solid #CBD5E1; border-radius: 8px; background-color: #F8FAFC; padding: 12px;">
      <div style="font-size: 13.5px; font-weight: bold; color: #0F172A; margin-bottom: 6px;">
        Option D: Pure USB Cable (High Security / Interference)
      </div>
      <div style="font-size: 12.5px; color: #334155; line-height: 1.6;">
        🔌 Enable USB Debugging in Android Developer Options<br>
        ⚡ Use ADB mode for 1-click push and pull<br>
        🔒 Physically disconnects all wireless networks for 100% offline security
      </div>
    </td>
  </tr>
</table>

---

## 🏕️ 4 Typical Field Networking Scenarios

### Option A: Mobile Hotspot ➔ PC Connects (⭐ Highly Recommended!)

In remote areas without public Wi-Fi, this is the most reliable setup:

1. **Step 1**: Enable **【Personal Hotspot】** on your mobile phone;
2. **Step 2**: Open PC Wi-Fi, connect to the phone's hotspot;
3. **Step 3**: In QGIS, select the hotspot IP from the network dropdown (e.g. `192.168.43.x`);
4. **Why it works**:
   * The phone acts as the local router and gateway;
   * Even with zero cellular carrier signal in deep valleys, the local LAN runs at full speed;
   * Mobile access to its own gateway has practically 0% packet loss.

---

### Option B: PC Hotspot ➔ Mobile Connects

If you have a laptop or industrial PC mounted in a survey vehicle:

1. Enable **【Mobile Hotspot】** in Windows Settings;
2. Connect mobile phone Wi-Fi to the laptop's hotspot SSID;
3. Select the hotspot adapter IP (usually `192.168.137.1`) in the plugin dropdown.

---

### Option C: Shared Basecamp / Office Wi-Fi

When working in basecamp, hotel rooms, or office spaces:

1. Ensure PC and phone are connected to the same Wi-Fi router;
2. Select the PC's router-assigned LAN IP (e.g. `192.168.1.105` or `10.0.0.x`).

> [!WARNING]
> Some enterprise or hotel networks enforce **【AP Isolation / Client Isolation】**, blocking direct peer-to-peer communication. If scan fails, switch immediately to **Option A (Mobile Hotspot)**!

---

### Option D: Air-Gapped / High-Security Survey (Pure USB Cable)

For classified projects, underground mines, or high electromagnetic interference:

1. Enable **USB Debugging** on your Android device;
2. Connect the phone via USB cable;
3. Use ADB mode for both dispatch and return — **physically disconnecting all wireless radios** for complete security.

---

## 🔌 Multi-Adapter Selection Tips

Modern PCs often run virtualization tools (VMware, VirtualBox), Docker, WSL, or VPN clients that create virtual network adapters (e.g. `192.168.199.1`, `10.244.x.x`).

* The plugin includes an **intelligent network adapter ranking engine** that prioritizes real physical Wi-Fi and Ethernet adapters;
* If the QR code does not open on your phone, verify you have not selected a VPN adapter and switch back to `192.168.x.x`.

---

👉 Facing specific errors? Check: [🛠️ 05. Frequently Asked Questions](chapter:faq).
