# QField LAN Drop (QField 局域网极速离线双向直传)

<p align="left">
  <img src="https://img.shields.io/badge/status-pending%20approval-orange?style=flat&logo=clockify&logoColor=white" alt="Status: Pending Approval">
  <img src="https://img.shields.io/badge/QGIS-3.0%2B-blue?style=flat&logo=qgis&logoColor=white" alt="QGIS 3.0+">
  <img src="https://img.shields.io/badge/QField-2.0%2B%20%7C%203.0%2B-brightgreen?style=flat&logo=android&logoColor=white" alt="QField 2.0+ | 3.0+">
  <img src="https://img.shields.io/badge/license-AGPL--3.0-blue?style=flat" alt="AGPL-3.0 License">
</p>

> ⏳ **项目状态说明 (Project Status)**：  
> - **QGIS Plugin 状态**：`Under Review / In Active Development`（本插件处于持续活跃迭代开发中，**v1.0.1 纯净正式包与手机端伴侣插件已就绪**）。  
> - **QGIS Version 兼容范围**：`≥ 3.0`（实测覆盖 QGIS 3.0 ~ 3.40 LTR，并已通过 Qt6 / QGIS 4.x Scoped Enum 兼容桥接）。  
> 
> 在官方插件库正式审核上线前，用户可直接前往 [Releases 页面](https://github.com/OpenQGIS/QFieldDrop/releases) 下载最新 ZIP 安装包，在 QGIS 菜单栏选择 **【插件】➔【管理并安装插件】➔【从 ZIP 文件安装】** 即插即用。

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

## 🧬 双线独立版本架构体系 (Dual-Track Independent Versioning)

本项目确立并严格践行 **「桌面端与移动端双轨独立版本演进架构」**：

| 维度对比 | 🖥️ 桌面端 QGIS 插件 (Track A) | 📱 移动端 QField 伴侣 (Track B) |
| :--- | :--- | :--- |
| **独立版本号** | **1.1.1** (当前最新) | **1.0.1** (当前最新) |
| **元数据源** | ./metadata.txt | ./mobile/metadata.txt |
| **宿主环境** | QGIS Desktop (PyQt5 / PyQt6) | QField Mobile (QML / QtQuick / JavaScript) |
| **版本迭代节奏**| **敏捷高频**（异步防假死重构、局域网协议迭代） | **克制稳健**（现场外业稳定性优先，免除频繁重复安装） |
| **分发包制品** | QFieldDrop_V-1.1.3.zip (官方纯净包) | QFieldDropMobile_V-1.0.3.zip (直装与沙盒包) |

> 💡 **架构解耦原则**：桌面端的性能调优、跨版本垫片升级或多线程重构**严禁无谓抬升手机端版本号**；两端生命周期完全解耦，构建流水线（uild_clean_release.py）自动独立解析版本并打包。

---

## 📂 多模块工程结构说明

各模块职责清晰，单文件保持在 40~350 行之间，有效避免上下文溢出与代码膨胀。关于开发、推送、打包与 Releases 资产的完整四维归类，请详阅 [PROJECT_STRUCTURE.md](file:///c:/Users/tesla/AppData/Roaming/QGIS/QGIS3/profiles/ForTest/python/plugins/QFieldDrop/PROJECT_STRUCTURE.md)。

```plaintext
QFieldDrop/
├── __init__.py                  # 插件入口工厂函数 (classFactory)
├── plugin.py                    # 动作注册、菜单挂载与按需调度逻辑
├── metadata.txt                 # QGIS 插件元数据配置 (索引 icon/QFieldDrop_logo.svg)
├── i18n_strings.py              # 多语言静态字典与保底机制
├── i18n_helper.py               # 多语言加载与动态切换辅助
├── README.md                    # 架构与使用指南
├── LICENSE                      # GNU AGPL v3.0 开源许可证
├── CHANGELOG.md                 # 语义化双语更新日志
├── PROJECT_STRUCTURE.md         # 工程结构与资产四维归类详案
├── DISTRIBUTION_GUIDE.md        # 官方插件发布规范与分发指引
├── build_clean_release.py       # 桌面端+移动端双轨纯净发布包构建脚本
├── build_mobile_release.py      # 移动端 QField 插件独立构建与校验脚本
│
├── core/                        # 核心协议与后台服务层 (纯业务逻辑，无 GUI 依赖)
│   ├── __init__.py              # 统一对外导出接口
│   ├── packager.py              # 工程静默打包引擎 (临时文件过滤、外部图层预检、ZIP生成)
│   ├── net_server.py            # 多网卡探测、HTTP 流式下载与移动端回传服务
│   ├── qr_native.py             # 零依赖 QR 矩阵生成与 QPixmap 内存高清渲染
│   ├── qrcodegen.py             # Nayuki 纯 Python 极简二维码算法核心 (MIT)
│   ├── localsend.py             # LocalSend v2 协议实现 (UDP 组播探测 + REST 传输)
│   ├── mdns_server.py           # mDNS 组播响应器 (局域网域名广播)
│   ├── adb_pusher.py            # Android ADB 静默推送与拉回引擎
│   └── compat.py                # 跨版本与跨平台兼容层
│
├── ui/                          # 界面表现层 (独立对话框与分发面板)
│   ├── __init__.py              # 统一导出 UI 对话框与面板
│   ├── send_dialog.py           # [📤 投送] 对话框主控制器
│   ├── receive_dialog.py        # [📥 接收] 对话框主控制器 (<0.1s 秒开)
│   ├── mobile_install_dialog.py # [📱 助手安装] 移动端伴侣多通道部署窗口
│   ├── tab_qr.py                # Tab: 扫码唤醒分发面板
│   ├── tab_localsend.py         # Tab: LocalSend 免扫码直推面板
│   ├── tab_return.py            # Tab: 外业成果回传面板
│   └── icon_helper.py           # 原生矢量与状态感知图标辅助引擎
│
├── icon/                        # 顶层入口图标 (含官方 Logo 与动作图标)
│   ├── QFieldDrop_logo.svg      # 官方标准插件 Logo
│   ├── icon_send.svg            # 投送工程动作图标
│   ├── icon_receive.svg         # 接收成果动作图标
│   └── icon_mobile.svg          # 手机端助手动作图标
│
├── icons/                       # 运行时高清操作图标集 (21 个矢量图标)
├── mobile/                      # 手机端 QField 独立伴侣插件源码 (main.qml, metadata.txt, icon.svg)
├── i18n/                        # 多语言源码与编译文件 (*.ts, *.qm, build_i18n.py)
├── tests/                       # 自动化回归测试套件
└── testdata/                    # 测试样本工程与数据
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

---

## 🗺️ 路线图与规划 (Roadmap)

本项目当前处于 **v1.1.0 迭代周期**，正在推进 **移动热点自愈** 与 **外业成果差异变动比对**。

```mermaid
gantt
    title QField LAN Drop 研发路线一览
    dateFormat  YYYY-MM-DD
    axisFormat  %m/%d
    todayMarker stroke-width:2px,stroke:#2563EB,opacity:0.8

    section v1.0.1 稳定版 (已发布)
    双动作解耦与LocalSend协议支持   :done,    t1, 2026-10-27, 2026-10-28
    v1.0.1 协议增强版发布          :milestone, m1, 2026-10-28, 0d

    section v1.1.0 当前迭代 (进行中)
    移动热点自愈与多网卡智能优选   :active,  t2, 2026-10-28, 2026-11-04
    外业回传差异比对与成果台账     :active,  t3, 2026-10-29, 2026-11-08
    v1.1.0 发布                   :milestone, m2, 2026-11-13, 0d
```

👉 查看详细开发排期、特性矩阵与任务清单：[详细路线图 (ROADMAP.md)](ROADMAP.md)

---

## 📄 开源许可 (License)

本项目采用 **GNU Affero General Public License v3.0 (AGPL-3.0-or-later)** 超强传染开源协议发布。任何基于本项目的修改、衍生分发或云端网络服务部署，均须以相同 AGPL-3.0 协议公开完整源代码。详情请参阅 [LICENSE](LICENSE) 文件。

