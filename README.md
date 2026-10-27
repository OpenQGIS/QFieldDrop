# QField LAN Drop (QField 局域网极速离线双向直传)

> 专为外业 GIS 打造的轻量级闭环工具：**一键快速打包分发（电脑 $\rightarrow$ 手机） + 一键外业成果回传（手机 $\rightarrow$ 电脑）**。  
> 告别重型云同步服务器与 MTP 数据线翻找沙盒文件的痛点，100% 局域网离线秒级直连。

---

## 🌟 工具栏成对按钮交互体系

插件在 QGIS 工具栏和菜单中并排挂载两个专属动作，完全契合出工与收工的时空心智：

```plaintext
QGIS 工具栏:  [ 📤 投送工程至 QField ]   [ 📥 接收 QField 成果 ]
```

| 按钮 | 触发动作 | 默认打开的界面 | 核心体验 |
| :--- | :--- | :--- | :--- |
| **📤 投送工程至 QField (Drop Out)** | 保存当前工程 $\rightarrow$ 静默过滤打包 $\rightarrow$ 启动分发服务 | 默认聚焦在 **「📱 扫码唤醒直传」** 面板 | 出工前一键打包，手机相机一扫即走 |
| **📥 接收 QField 成果 (Drop In)** | **跳过打包** $\rightarrow$ 启动接收监听服务 | 默认聚焦在 **「📥 外业成果回传」** 面板 | **< 0.1 秒秒级弹出**，专为收工回传设计 |

> **注**：无论点击哪个按钮打开窗口，窗口内部依然保留顶部 Tab 栏，用户依然可以自由切换查看或在需要时触发“重新打包”。

---

## 📂 多模块工程结构说明

各模块职责清晰，单文件保持在 40~350 行之间，有效避免上下文溢出与代码膨胀：

```plaintext
QFieldDrop/
├── __init__.py                  # 插件入口工厂函数 (classFactory)
├── metadata.txt                 # QGIS 插件元数据配置
├── icon_send.svg                # [📤 投送] 专属高清矢量图标
├── icon_receive.svg             # [📥 接收] 专属高清矢量图标
├── icon.svg                     # 基础总图标
├── plugin.py                    # 双按钮注册、菜单挂载与按需调度逻辑
├── README.md                    # 架构与使用指南
│
├── core/                        # 核心协议与后台服务层 (纯业务逻辑，无 GUI 依赖)
│   ├── __init__.py              # 统一对外导出接口
│   ├── packager.py              # 工程静默打包引擎 (临时文件过滤、外部图层预检、ZIP生成)
│   ├── net_server.py            # 多网卡/热点 IP 探测、后台 HTTP 流式下载与 /upload 移动端回传服务
│   ├── qr_native.py             # 零依赖 QR 矩阵生成与 QPixmap 内存高清渲染
│   ├── qrcodegen.py             # Nayuki 官方纯 Python 极简二维码算法核心 (MIT)
│   ├── localsend.py             # LocalSend v2 协议实现 (UDP 组播监听 + REST API 客户端)
│   ├── mdns_server.py           # mDNS 组播响应器 (qgis-drop.local 局域网域名广播)
│   └── adb_pusher.py            # Android ADB 无线/USB 静默推送与一键拉回 (Pull) 底层引擎
│
├── ui/                          # 界面表现层 (各标签页与子对话框独立拆解封装)
│   ├── __init__.py              # 统一导出 UI 对话框与面板
│   ├── share_dialog.py          # 主窗口框架控制器 (双模式初始化、服务生命周期、Tab 编排)
│   ├── tab_qr.py                # Tab 0: 扫码唤醒分发面板 (IP 切换、双码切换、放行命令)
│   ├── tab_localsend.py         # Tab 1: LocalSend 免扫码直推面板 (设备扫描、列表展示、推送进度)
│   ├── tab_return.py            # Tab 2: 外业成果回传面板 (网页扫码上传二维码、ADB 一键拉回、归档列表、一键解压)
│   ├── tab_advanced.py          # Tab 3: 高阶通道面板 (ADB 推送引导、mDNS 状态、伴侣插件导出)
│   ├── adb_dialog.py            # ADB 设备选择、无线连接与推送执行控制台
│   └── external_layers_dialog.py# 外部绝对路径图层预检详情弹窗
│
└── companion/                   # 配套移动端插件资产
    └── qfield_lan_pull/         # 移动端 QField QML 辅助拉取插件源码 (支持一键导出 ZIP)
        ├── metadata.txt
        ├── main.qml
        └── icon.svg
```

---

## 🚀 完整作业使用流程

### 1. 早上出工：快速下发（电脑 $\rightarrow$ 手机）
1. 在 QGIS 中点击工具栏 **「📤 投送工程至 QField」** 图标；
2. 插件自动保存修改、过滤临时文件并打包（默认停留在扫码直传面板）；
3. **方式 A**：手机自带相机扫描二维码，直接唤醒 QField 并自动导入工程；
4. **方式 B**：切换至「⚡ LocalSend 免扫码直推」，点击附近发现的手机设备一键推送。

### 2. 下午收工：成果回传（手机 $\rightarrow$ 电脑）
1. 在 QGIS 中点击工具栏 **「📥 接收 QField 成果」** 图标（**0.1 秒秒开，无需等待电脑重新打包**）；
2. **方式 A（手机扫码网页上传）**：
   - 手机自带相机/浏览器扫描回传二维码，自动打开内置的移动端回传网页；
   - 挑选 QField 导出的工程 `.zip`、更新后的 `.gpkg` 或现场照片，点击「🚀 立即回传至电脑」；
   - 电脑端 QGIS 弹出提醒，文件自动存储于当前工程的 `_qfield_return/<时间戳>/` 目录下。
3. **方式 B（Android ADB 一键拉取）**：
   - 电脑端直接点击「📥 一键拉回手机外业成果 (ADB)」按钮；
   - 自动穿透 Android 11+ 沙盒保护，将更新后的工程目录瞬间拉取到电脑。
