# 📥 03. 收工回传：手机至电脑 (Drop In)

外业调查收工后，在 QGIS 工具栏点击 **`[ 📥 接收 QField 成果 ]`**，窗口 **<0.1 秒秒级弹出**，进入待命监听状态。

<div class="mockup-window">
  <div class="mockup-titlebar">
    <span class="mockup-dot red"></span><span class="mockup-dot yellow"></span><span class="mockup-dot green"></span>
    &nbsp;<b>QField 局域网直传 - 接收外业成果 (Drop In)</b>
  </div>
  <div style="padding: 8px 14px; background-color: #F8FAFC; border-bottom: 1px solid #E2E8F0; font-size: 12px; color: #475569;">
    📁 关联工程: <b>Field_Survey_2026.qgz</b> &nbsp;|&nbsp; 存储目录: <span style="font-family: monospace; color: #2563EB;">.../_qfield_return/</span>
  </div>
  <div class="mockup-body">
    <!-- Top: QR Upload Channel -->
    <div style="border: 1px solid #CBD5E1; border-radius: 6px; background-color: #FFFFFF; padding: 10px; margin-bottom: 10px;">
      <table width="100%" border="0" cellpadding="4" style="border: none;">
        <tr style="border: none; background: transparent;">
          <td width="115" align="center" valign="middle" style="border: none;">
            <img src="../../assets/diagrams/qr_sample.svg" width="95" height="95" style="display: block; margin: 0 auto;" />
            <div style="margin-top: 4px;"><span class="step-badge blue">①</span><b>手机扫此码</b></div>
          </td>
          <td valign="top" style="border: none; padding-left: 10px;">
            <div style="margin-bottom: 6px;">
              <b>接收网卡：</b>
              <span class="mockup-input">192.168.43.120 (手机热点 / Wi-Fi) ▼</span>
            </div>
            <div style="font-size: 12.5px; color: #334155; line-height: 1.5; margin-bottom: 6px;">
              <b>手机扫码回传指引：</b><br>
              1. 手机自带相机扫描左侧二维码，打开轻量上传页面；<br>
              2. 勾选修改后的矢量图层或现场照片，点击【立即回传】。
            </div>
            <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 4px 6px; border-radius: 4px; font-family: monospace; font-size: 11px; color: #2563EB;">
              http://192.168.43.120:8899/upload &nbsp;
              <span class="qgis-btn">复制回传网址</span>
            </div>
          </td>
        </tr>
      </table>
    </div>

    <!-- Bottom: Received Archives Table -->
    <div style="border: 1px solid #CBD5E1; border-radius: 6px; background-color: #FFFFFF; padding: 10px;">
      <div style="font-size: 12px; font-weight: bold; color: #1E293B; margin-bottom: 8px;">
        <span class="step-badge green">②</span> <b>外业成果归档记录 (已自动隔离归档，安全不覆盖)</b>
      </div>
      <table width="100%" border="0" cellpadding="6" style="border-collapse: collapse; font-size: 11.5px; margin-bottom: 8px;">
        <tr style="background-color: #F1F5F9; border-bottom: 1px solid #CBD5E1; font-weight: bold; color: #475569;">
          <th align="left" style="padding: 5px 8px;">接收时间</th>
          <th align="left" style="padding: 5px 8px;">成果文件</th>
          <th align="center" style="padding: 5px 8px;">大小</th>
          <th align="left" style="padding: 5px 8px;">回传来源</th>
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
        <span class="qgis-btn-blue">载入至当前工程 (对比质检)</span>&nbsp;
        <span class="qgis-btn">打开所在目录</span>&nbsp;
        <span class="qgis-btn">解压成果包</span>
      </div>
    </div>
  </div>
  <div class="mockup-footer">
    <span class="step-badge blue">①</span> 手机相机扫码上传 &nbsp;&nbsp;|&nbsp;&nbsp; 
    <span class="step-badge green">②</span> 查看外业成果台账 &nbsp;&nbsp;|&nbsp;&nbsp; 
    <span class="step-badge purple">③</span> 一键载入地图画布进行质检验收
  </div>
</div>

---

## 🎯 界面三步操作指引

### 标注 ①：手机扫码回传成果
1. 手机自带相机扫描界面中央的二维码；
2. 手机浏览器将打开专属的轻量上传页面；
3. 点击 **【选择文件】**，勾选更新后的 `.gpkg` 矢量包、导出的 ZIP 或现场照片；
4. 点击 **「🚀 立即回传」**，电脑端立即自动接收并归档。

---

### 标注 ②：查看已接收成果台账
* 手机回传的文件会自动列入表格中；
* 包含文件名、大小、接收时间以及来源手机型号；
* 所有成果按时间戳安全存放在当前工程的 `_qfield_return/` 目录下，**绝不覆盖原始工程数据**。

---

### 标注 ③：一键载入 QGIS 对比质检
* 选中表格中的成果条目；
* 点击底部的 **「载入至当前工程」** 按钮；
* 图层将直接添加到当前 QGIS 地图画布上，立即进行内业质检验收！

---

👉 遇到网络连接问题？请看：[🌐 04. 外业野外组网攻略](chapter:network_guide)。
