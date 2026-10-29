# 📤 02. 出工投送：电脑至手机 (Drop Out)

在 QGIS 工具栏直接点击 **`[ 📤 投送工程至 QField ]`** 按钮，系统自动保存并打包当前工程。

<div class="mockup-window">
  <div class="mockup-titlebar">
    <span class="mockup-dot red"></span><span class="mockup-dot yellow"></span><span class="mockup-dot green"></span>
    &nbsp;<b>QField 局域网直传 - 投送至手机 (Drop Out)</b>
  </div>
  <div style="padding: 10px 14px; background-color: #F8FAFC; border-bottom: 1px solid #E2E8F0;">
    <span class="step-badge blue">①</span> <b>选择分发网卡 / IP：</b>
    <span class="mockup-input">192.168.43.120 (手机热点 / Wi-Fi) ▼</span>&nbsp;
    <span class="qgis-btn">刷新</span>
  </div>
  <div class="mockup-body">
    <table width="100%" border="0" cellpadding="4" style="border: none;">
      <tr style="border: none; background: transparent;">
        <!-- Left: QR Code Box -->
        <td width="60%" valign="top" style="border: none; padding-right: 14px;">
          <div style="margin-bottom: 8px;">
            <span class="mockup-tab-active">📱 二维码直传</span>&nbsp;
            <span class="mockup-tab-inactive">⚡ LocalSend 导入</span>&nbsp;
            <span class="mockup-tab-inactive">📦 安装包下载</span>&nbsp;
            <span class="mockup-tab-inactive">🔌 有线传输</span>
          </div>
          <table width="100%" border="0" cellpadding="6" style="border: 1px solid #CBD5E1; border-radius: 6px; background-color: #FFFFFF;">
            <tr style="border: none; background: transparent;">
              <td width="115" align="center" valign="middle" style="border: none;">
                <img src="../../assets/diagrams/qr_sample.svg" width="95" height="95" style="display: block; margin: 0 auto;" />
                <div style="margin-top: 4px;"><span class="step-badge red">②</span><b>扫此码</b></div>
              </td>
              <td valign="top" style="border: none; padding-left: 8px;">
                <div style="font-size: 12.5px; font-weight: bold; color: #0F172A; margin-bottom: 6px;">
                  手机自带相机扫码，直接唤醒 QField 并自动导入
                </div>
                <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 4px 6px; border-radius: 4px; font-family: monospace; font-size: 11px; color: #2563EB; margin-bottom: 8px;">
                  qfield://open?url=http://192.168.43.120...
                </div>
                <div>
                  <span class="qgis-btn-blue">复制链接</span>&nbsp;
                  <span class="qgis-btn">重新打包</span>
                </div>
              </td>
            </tr>
          </table>
        </td>
        <!-- Right: Treemap Box -->
        <td width="40%" valign="top" style="border: 1px solid #CBD5E1; border-radius: 6px; background-color: #F8FAFC; padding: 8px;">
          <div style="font-size: 12px; font-weight: bold; color: #1E293B; margin-bottom: 6px;">
            <span class="step-badge green">③</span> <b>📊 图层存储分析</b>
          </div>
          <table width="100%" border="0" cellpadding="4" style="border-collapse: separate; border-spacing: 2px;">
            <tr style="border: none;">
              <td colspan="2" style="background-color: #3B82F6; color: #FFF; font-weight: bold; font-size: 11px; text-align: center; padding: 8px; border-radius: 4px;">
                DOM.tif (128 MB 遥感影像)
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
                Project.qgz (12 MB 工程配置)
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </div>
  <div class="mockup-footer">
    <span class="step-badge blue">①</span> 选择共用网络 IP &nbsp;&nbsp;|&nbsp;&nbsp; 
    <span class="step-badge red">②</span> 相机扫描屏幕二维码 &nbsp;&nbsp;|&nbsp;&nbsp; 
    <span class="step-badge green">③</span> 透视检查图层体积占比
  </div>
</div>

---

## 🎯 界面三步操作指引

### 标注 ①：确认网络 IP
* 点击下拉框，选择当前电脑与手机共用的网络：
  * **野外推荐**：选择手机热点分配的 IP（通常为 `192.168.43.x`）；
  * **办公室内**：选择 Wi-Fi 路由器分配的 IP（如 `192.168.1.x`）。

---

### 标注 ②：手机相机扫码即走
1. 打开手机系统自带相机、微信或扫一扫；
2. 对准屏幕中央的高清二维码扫描；
3. 手机下载完成后，**自动唤醒 QField 并静默解压到工程列表**，立即可以开始外业调查！

> [!TIP]
> 也可以切换到 **「⚡ LocalSend 导入」** 自动发现附近设备，或通过 **「📦 安装包下载」** 导出 ZIP 离线包，涉密/无网环境更可切至 **「🔌 有线传输」** 一键通过 USB 写入手机！

---

### 标注 ③：查看图层存储透视（可选）
* 右侧展开的彩色矩树图直观展示了工程内各图层的空间占用；
* 可以在出工前快速检查是否有误放入的几百兆超大底图，避免占满手机存储空间。

---

👉 现场调查完毕收工？请看：[📥 03. 收工回传：手机至电脑](chapter:receive_results)。
