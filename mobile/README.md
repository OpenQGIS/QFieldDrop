# QFieldDrop Mobile (QField 局域网直传移动端助手)

[![QField Compatible](https://img.shields.io/badge/QField-2.0%2B%20%7C%203.0%2B-brightgreen)](https://qfield.org)
[![Platform](https://img.shields.io/badge/Platform-Android%20%7C%20iOS-blue)]()
[![License](https://img.shields.io/badge/License-GPLv3-green)]()

**QFieldDrop Mobile** 是配套桌面端 QGIS 插件 [QFieldDrop](https://github.com/OpenQGIS/QFieldDrop) 的移动端协同插件。

它直接运行在手机 **QField** 内部，彻底解决了 Android 11+ 沙盒文件隐藏导致普通浏览器无法回传文件的痛点。外业人员在手机 QField 中仅需一键，即可将当天的打点成果或整个项目秒级交还电脑。

---

## ✨ 核心特性

- 🚀 **QField 内部一键调起**：直接集成至 QField 顶部工具栏，外业作业途中随时一键直传。
- 📦 **双模式自由选择**：
  - **增量回传（推荐）**：自动识别修改过的矢量要素图层（`.gpkg` / `.shp`）及新增的现场照片附件（`DCIM/`），体积极小，秒级直达。
  - **整包工程回传**：打包当前工程目录下的所有配置文件及图层，全量回传电脑。
- 🔍 **智能电脑探测**：自动识别同一 Wi-Fi 或热点下的内业电脑（通过 mDNS `qgis-drop.local:8899` 或输入 IP）。
- 🛡️ **原生零依赖**：基于 Qt Quick / QML 原生构建，无需在移动端安装额外的 Python 运行环境或依赖库。

---

## 📲 安装方法

### 方式一：电脑端 QFieldDrop 一键导出（最推荐）
1. 在电脑端 QGIS 打开 `QFieldDrop` 面板，点击「导出移动端配套插件」。
2. 将导出的 `qfield_drop_mobile.zip` 发送到手机（通过微信/QQ/网盘/LocalSend）。
3. 在手机 QField 中点击右上角菜单 -> **插件 (Plugins)** -> **从压缩包安装 (Install from ZIP)**，选中该文件即可。

### 方式二：手动拷贝到沙盒目录
将本文件夹整体复制到手机 QField 插件目录下：
- **Android**: `/sdcard/Android/data/ch.opengis.qfield/files/plugins/qfield_drop/`
- 重启 QField 即可在顶部工具栏看到「回传电脑」图标。

---

## 🛠️ 目录结构

```
QFieldDrop-Mobile/
├── icon.svg          # 手机端工具栏矢量图标
├── metadata.txt      # QField 插件元数据清单
├── main.qml          # QField QML 主入口与交互弹窗
└── README.md         # 插件说明文档
```
