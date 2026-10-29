# 📱 01. 首次使用与手机端准备

首次使用时，只需在手机 QField 中安装一次离线伴侣插件。后续出工作业无需重复安装。

<div class="mockup-window">
  <div class="mockup-titlebar">
    <span class="mockup-dot red"></span><span class="mockup-dot yellow"></span><span class="mockup-dot green"></span>
    &nbsp;<b>QField 手机助手安装 (移动端独立伴侣)</b>
  </div>
  <div style="padding: 8px 14px; background-color: #F8FAFC; border-bottom: 1px solid #E2E8F0;">
    <span class="mockup-tab-active">方式一：QField 扫码直装</span>&nbsp;&nbsp;
    <span class="mockup-tab-inactive">方式二：ADB 数据线写入</span>
  </div>
  <div class="mockup-body">
    <table width="100%" border="0" cellpadding="4" style="border: none;">
      <tr style="border: none; background: transparent;">
        <td width="130" align="center" valign="top" style="border: none; background-color: #F8FAFC; padding: 10px; border-radius: 6px;">
          <img src="../../assets/diagrams/qr_sample.svg" width="105" height="105" style="margin: 0 auto; display: block;" />
          <div style="margin-top: 6px;"><span class="step-badge blue">①</span><b>扫此码</b></div>
        </td>
        <td valign="top" style="border: none; padding-left: 16px;">
          <p style="font-size: 13.5px; font-weight: bold; color: #0F172A; margin-bottom: 6px;">
            在手机 QField 内部安装伴侣插件：
          </p>
          <p style="font-size: 13px; color: #334155; margin-bottom: 4px;">
            1. 打开手机 <b>QField</b> ➔ 点击左上角菜单 ➔ <b>【设置】</b> ➔ <b>【插件】</b> ➔ <b>【从 URL 安装】</b>
          </p>
          <p style="font-size: 13px; color: #334155; margin-bottom: 10px;">
            2. 点击输入框右侧的 <b>【📷 扫一扫】</b> 相机图标，扫描左侧二维码即可自动安装
          </p>
          <p style="font-size: 13px; font-weight: bold; color: #0F172A; margin-bottom: 4px;">
            <span class="step-badge green">②</span> 无摄像头设备手动安装地址：
          </p>
          <div style="background-color: #F1F5F9; border: 1px solid #CBD5E1; padding: 4px 8px; border-radius: 4px; font-family: monospace; font-size: 12.5px; color: #2563EB; margin-bottom: 10px;">
            http://192.168.43.120:8899/mobile.zip
          </div>
          <div>
            <span class="step-badge purple">③</span>
            <span style="background-color: #6366F1; color: #FFFFFF; font-weight: bold; padding: 5px 12px; border-radius: 4px; font-size: 12px; display: inline-block;">
              ⚡ ADB 数据线一键写入手机
            </span>
          </div>
        </td>
      </tr>
    </table>
  </div>
  <div class="mockup-footer">
    <span class="step-badge blue">①</span> 打开 QField [从URL安装] 扫码 &nbsp;&nbsp;|&nbsp;&nbsp; 
    <span class="step-badge green">②</span> 手动填写本地地址 &nbsp;&nbsp;|&nbsp;&nbsp; 
    <span class="step-badge purple">③</span> 有线连接一键写入
  </div>
</div>

---

## 🛠️ 界面三步操作指引

点击 QGIS 工具栏的 **`[ 📱 手机助手 ]`** 图标打开安装窗口：

### 标注 ①：QField 内部扫码安装（⭐ 最推荐）
1. 手机打开 **QField** 软件；
2. 点击左上角主菜单 ➔ **【齿轮设置】** ➔ **【插件】** 选项卡；
3. 点击 **【从 URL 安装】**，再点击输入框右侧的 **【📷 扫一扫】** 相机图标；
4. 对准屏幕上的二维码扫描，QField 将自动下载安装并启用。

---

### 标注 ②：无相机设备手动输入地址
对于没有后置摄像头的定制手持终端：
* 在 QField 的【从 URL 安装】输入框中，直接填入界面中显示的网址：
  ```plaintext
  http://192.168.43.120:8899/mobile.zip
  ```
* 点击确定即可完成安装。

---

### 标注 ③：USB 数据线一键写入（零操作极速）
如果手头有 USB 数据线：
1. 手机连接电脑，开启 **【USB 调试】** 并允许授权；
2. 电脑端直接点击 **「⚡ ADB 数据线一键写入」**；
3. 插件自动穿透沙盒写入完成，手机端无需任何点击！

---

👉 手机配置完成后，立即开始出工投送：[📤 02. 出工投送：电脑至手机](chapter:send_project)。
