# 🛠️ 05. Troubleshooting & FAQ

This chapter addresses the most common field issues and troubleshooting solutions.

---

## ❓ 1. Phone scan displays "Cannot reach page" or "Connection Timed Out"?

**Troubleshooting Steps**:
1. **Verify Local Subnet**: Has the phone fallen back to mobile cellular 4G/5G? Temporarily disable mobile data on your phone so all traffic routes through the local Wi-Fi / hotspot;
2. **Windows Defender Firewall (Most Common)**:
   * When QGIS first starts a local network service, Windows Defender Firewall may prompt for permissions. If cancelled or ignored, inbound traffic from phones is silently blocked;
   * **Fix**: Open Windows Control Panel ➔【System and Security】➔【Windows Defender Firewall】➔【Allow an app or feature through firewall】. Find `qgis-bin.exe` or `python.exe` and check the **【Private】** network box;
3. **Router Client Isolation**: If on hotel or enterprise Wi-Fi, the router may isolate wireless clients. Switch to **Phone Hotspot Mode**.

---

## ❓ 2. Camera scans and downloads ZIP, but does not auto-open QField?

**Cause & Solution**:
* Certain Android distributions (e.g. Xiaomi HyperOS, Huawei HarmonyOS, Samsung OneUI) restrict browsers from directly triggering third-party app DeepLinks;
* **Solutions**:
  * **Option A**: Open **QField**, tap 【Open Local Project】, and select the downloaded ZIP file;
  * **Option B**: Use QField's internal companion scanner, which has elevated sandboxed extraction permissions.

---

## ❓ 3. USB mode reports "No Android device detected"?

**Checklist**:
1. **Data Cable Quality**: Many low-cost charging cables lack the internal D+/D- data lines ("charging only"). Always use a certified data-capable USB cable;
2. **Developer Options & USB Debugging**:
   * Settings ➔ About Phone ➔ Tap "Build Number" 7 times to enable developer mode;
   * Open Developer Options and enable "USB Debugging";
3. **RSA Computer Fingerprint Authorization**:
   * Unlock your phone screen upon connecting the cable;
   * When the **"Allow USB Debugging?"** popup appears, check **【Always allow from this computer】** and tap OK.

---

## ❓ 4. Why does packaging report "External layers detected"?

**Explanation**:
* The QGIS project references raster or vector layers stored outside the project folder (e.g. `D:\GIS_Data\DEM.tif`);
* Packaging only compresses the active project folder. The phone will show a "Missing Layer" warning because the external path does not exist on Android.

**Recommendation**:
* Store all required `.gpkg` and `.tif` files inside the project directory;
* In QGIS menu: 【Project】➔【Project Properties】➔【General】, set layer storage paths to **【Relative】**.

---

## ❓ 5. Server alerts "Port 8080 already in use"?

* The plugin includes an **auto-healing adaptive port mechanism**;
* If port 8080 is occupied, it automatically scans `8081`, `8082`, etc., until an open port is found, updating the QR code URL dynamically.

---

👉 Next: [💡 06. Appendix & Advanced Tips](chapter:appendix).
