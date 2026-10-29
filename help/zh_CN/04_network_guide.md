# 🌐 04. 外业野外组网攻略

在外业作业中，“连接不上电脑”90% 是因为**网络拓扑或网段选择不正确**。本章详细解析 4 种典型工况的最佳连接姿势。

<table width="100%" border="0" cellpadding="8" style="border-collapse: separate; border-spacing: 8px; margin: 12px 0;">
  <tr>
    <td width="50%" valign="top" style="border: 1.5px solid #3B82F6; border-radius: 8px; background-color: #EFF6FF; padding: 12px;">
      <div style="font-size: 13.5px; font-weight: bold; color: #1E40AF; margin-bottom: 6px;">
        ⭐ 方案 A：手机热点 ➔ 电脑连接（野外最推荐）
      </div>
      <div style="font-size: 12.5px; color: #1E3A8A; line-height: 1.6;">
        📱 手机开启便携热点 (网关通常为 192.168.43.1)<br>
        💻 电脑 Wi-Fi 搜索并连入手机热点<br>
        ⚡ <b>即使深山无手机信号，局域网千兆通道依然畅通无阻！</b>
      </div>
    </td>
    <td width="50%" valign="top" style="border: 1.5px solid #CBD5E1; border-radius: 8px; background-color: #F8FAFC; padding: 12px;">
      <div style="font-size: 13.5px; font-weight: bold; color: #0F172A; margin-bottom: 6px;">
        方案 B：电脑热点 ➔ 手机连接
      </div>
      <div style="font-size: 12.5px; color: #334155; line-height: 1.6;">
        💻 电脑设置中开启 Windows 移动热点<br>
        📱 手机 Wi-Fi 连入电脑 (网段通常为 192.168.137.1)<br>
        🚙 适合固定在车载上的内业工控机或笔记本
      </div>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top" style="border: 1.5px solid #CBD5E1; border-radius: 8px; background-color: #F8FAFC; padding: 12px;">
      <div style="font-size: 13.5px; font-weight: bold; color: #0F172A; margin-bottom: 6px;">
        方案 C：营地/办公室同局域网
      </div>
      <div style="font-size: 12.5px; color: #334155; line-height: 1.6;">
        🏠 电脑与手机连接同一个 Wi-Fi 路由器<br>
        🌐 选择分配给电脑的局域网 IP (192.168.1.x)<br>
        ⚠️ 若酒店/企业开启了 AP 隔离，请立即换用方案 A
      </div>
    </td>
    <td width="50%" valign="top" style="border: 1.5px solid #CBD5E1; border-radius: 8px; background-color: #F8FAFC; padding: 12px;">
      <div style="font-size: 13.5px; font-weight: bold; color: #0F172A; margin-bottom: 6px;">
        方案 D：纯 USB 数据线 (涉密/强干扰)
      </div>
      <div style="font-size: 12.5px; color: #334155; line-height: 1.6;">
        🔌 手机开启开发者选项中的【USB 调试】<br>
        ⚡ 电脑端点击 ADB 模式一键推送或拉取<br>
        🔒 物理级断开无线网络，100% 离线涉密安全
      </div>
    </td>
  </tr>
</table>

---

## 🏕️ 4 大典型工况实战方案

### 方案 A：手机开热点 ➔ 电脑连接手机（⭐ 野外最推荐！）

在荒郊野外、没有任何公共 Wi-Fi 设施时，这是最健壮、最推荐的方案：

1. **第一步**：外业人员打开手机上的 **【便携式个人热点】**；
2. **第二步**：内业笔记本电脑打开 Wi-Fi，搜索并连接到手机的热点；
3. **第三步**：在 QGIS 插件界面的「网络接口 (IP)」下拉框中，系统会自动列出当前热点网段（例如 `192.168.43.x`）；
4. **原理与优势**：
   * 手机此时充当了局域网的“主路由器与网关”；
   * 哪怕外业现场完全没有运营商 4G/5G 信号，手机与电脑之间依然建立了一条**高速千兆局域网通道**；
   * 手机访问自身网关速度极快，丢包率几乎为 0。

---

### 方案 B：笔记本电脑开热点 ➔ 手机连接电脑

如果现场有固定在车载上的内业工控机或笔记本：

1. 笔记本在 Windows 设置中开启 **【移动热点】**；
2. 手机打开 Wi-Fi，连接到笔记本发出的热点名称；
3. 在插件界面的网络选择下拉框中，选择 Windows 移动热点虚拟适配器对应的 IP（通常为 `192.168.137.1`）。

---

### 方案 C：驻地/项目部局域网（同一路由器）

当在项目部营地、会议室或办公室时：

1. 确保电脑和手机都连接在同一个 Wi-Fi 名称下；
2. 在插件下拉框中选择路由器分配给电脑的局域网 IP（例如 `192.168.1.105` 或 `10.0.0.x`）。

> [!WARNING]
> 部分企业内部或酒店 Wi-Fi 启用了 **【AP 隔离 / 访客网络保护 (Client Isolation)】**，这会导致连接同一 Wi-Fi 的两台设备无法互相通信。如遇此情况，请立即切换至 **方案 A（手机开热点）**！

---

### 方案 D：涉密项目 / 强干扰完全断网（纯 USB 线缆）

在保密基地、地下矿山或强电磁干扰环境下：

1. 手机开启开发者模式下的 **USB 调试**；
2. 用 USB 数据线连上电脑；
3. 投送与接收全程使用 ADB 模式，**物理级断开所有无线连接**，100% 离线安全。

---

## 🔌 多网卡筛选技巧

现代电脑上往往安装了虚拟机（VMware / VirtualBox）、Docker、WSL 或 VPN 客户端，这些软件会生成很多虚拟网卡（例如 `192.168.199.1`、`10.244.x.x`）。

* 插件已内置**智能网络检测引擎**，会自动置顶推荐真实的物理 Wi-Fi 与以太网卡；
* 如果扫码打不开，请检查下拉框是否误选了 VPN 虚拟网卡，手动切回 `192.168.x.x` 即可。

---

👉 遇到具体报错？请查看：[🛠️ 05. 常见问题与排错急救箱](chapter:faq)。
