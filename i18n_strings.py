# -*- coding: utf-8 -*-
"""
QField LAN Drop - 集中式多语言英汉翻译字典 (Fallback 保底库)
包含所有界面英文字符串对应的简体中文翻译。
"""

_zh_translations = {
    # 插件入口与菜单动作
    "QFieldDrop": "QFieldDrop",
    "QFieldDrop_Dev": "QFieldDrop_Dev",
    "QField LAN Drop": "QFieldDrop",
    "Drop Out (Send to QField)": "投送工程至 QField (Drop Out)",
    "Drop In (Receive from QField)": "接收 QField 成果 (Drop In)",
    "Install QField Mobile Companion": "安装 QField 手机助手 (Mobile Setup)",
    "Help & User Manual": "使用手册与帮助中心 (Help)",
    "Save, package and transfer current project to QField via QR/LocalSend/ADB": "一键保存、打包并投送当前工程至外业手机 QField (扫码唤醒 / LocalSend / ADB)",
    "Start receiving service and retrieve field updates via Web/ADB": "一键开启成果接收服务，从手机回传外业成果 (网页扫码 / ADB拉取，无需重新打包)",
    "Install companion QML plugin onto mobile QField": "为手机 QField 安装配套助手插件 (扫码安装 / QField URL / ADB写入 / 离线ZIP)",
    "Open in-app help center and troubleshooting guide": "打开内置离线图文使用手册与故障排查指南",
    "Help": "帮助",
    "User Manual": "使用手册",

    # 对话框标题
    "QField LAN Drop - Outbound Dispatch (Drop Out)": "QField 局域网直传 - 投送至手机 (Drop Out)",
    "QField LAN Drop - Inbound Return (Drop In)": "QField 成果接收 - 手机外业回传 (Drop In)",
    "QField Mobile Companion Setup": "QField 手机助手安装",
    "External Layer Data Sources Detail": "外部图层数据源详情",
    "ADB Device & Push Management": "ADB 设备管理与推送",

    # 选项卡标题
    "📱 QR Code Wake-up": "📱 扫码唤醒直传",
    "⚡ LocalSend Auto-push": "⚡ LocalSend 免扫码直推",
    "📥 Field Return & Archive": "📥 外业成果回传",
    "🛠️ Advanced / ADB Channel": "🛠️ 高阶通道 (ADB / 伴侣插件)",

    # 扫码面板与分发
    "Scan with mobile camera to wake QField and import project": "手机自带相机扫描二维码，直接唤醒 QField 并导入工程",
    "Select Network Card / IP:": "选择分发网卡 / IP：",
    "Project Packaging:": "工程打包状态：",
    "Deep Link QR Code": "深度链接二维码 (推荐)",
    "HTTP Download QR Code": "浏览器下载二维码",
    "Firewall Rule Command": "防火墙放行命令",
    "Copy Link": "复制链接",
    "Refresh Network": "刷新网卡",
    "Repackage Project": "重新打包工程",
    "Project successfully packaged: {0} ({1} MB)": "工程打包成功：{0} ({1} MB)",
    "External absolute path layers detected: {0} layers": "检测到外部绝对路径图层：共 {0} 个",
    "View External Layers": "查看外部图层",

    # LocalSend 面板
    "Searching for devices on local network...": "正在扫描局域网内的设备...",
    "Discovered Devices:": "发现的设备：",
    "Push Project to Selected Device": "推送工程至所选设备",
    "Refresh Device List": "刷新设备列表",
    "Device Name": "设备名称",
    "Device IP": "设备 IP",
    "Device OS / Type": "系统 / 类型",
    "Pushing: {0}%": "正在推送：{0}%",
    "Push completed successfully!": "工程推送成功！",
    "Push failed: {0}": "推送失败：{0}",

    # 回传面板
    "Mobile Upload URL:": "手机回传网页地址：",
    "Scan QR code with mobile browser to upload files directly": "手机浏览器扫描二维码，直接打开网页上传外业成果",
    "Received Field Packages:": "已接收的外业成果记录：",
    "Open Return Directory": "打开回传归档目录",
    "Unpack Selected Package": "一键解压并打开",
    "Load Layers into QGIS": "载入图层至当前工程",
    "Pull via ADB": "一键拉回手机外业成果 (ADB)",
    "Filename": "文件名",
    "Size": "大小",
    "Receive Time": "接收时间",
    "Client IP": "来源 IP",
    "Status": "状态",
    "No package selected!": "请先在上方列表中选中一项成果记录！",
    "Package file has been moved or deleted:": "成果文件已被移动或删除：",

    # 手机助手面板
    "Companion QML Plugin Installation": "配套 QML 插件安装方式",
    "Method 1: Scan QR to Install": "方式一：手机扫码安装",
    "Method 2: One-Click Push via ADB": "方式二：ADB 一键免线/有线写入手机",
    "Method 3: Export Offline ZIP": "方式三：导出离线安装包 (ZIP)",
    "Export Companion ZIP": "导出伴侣插件 ZIP",
    "ADB Push to Phone": "一键写入手机 QField (ADB)",
    "Detected ADB Devices:": "检测到的 ADB 设备：",
    "No Android device detected! Please connect via USB or Wi-Fi.": "未检测到 Android 设备！请通过 USB 数据线或无线调试连接手机。",
    "Companion plugin installed successfully!": "配套伴侣插件已成功写入手机 QField！",
    "Installation failed: {0}": "安装失败：{0}",

    # 提示与通用状态
    "Project Unsaved": "工程未保存",
    "Current QGIS project is not saved yet! Please save before dropping.": "当前 QGIS 工程尚未保存到本地磁盘！\n\n请先保存工程文件（.qgz 或 .qgs）后再进行局域网直传。",
    "Operation Succeeded": "操作成功",
    "Operation Failed": "操作失败",
    "Warning": "警告",
    "Information": "提示",
    "Error": "错误",
    "Close": "关闭",
    "Cancel": "取消",
    "OK": "确定",
    "Copy": "复制",
    "Copied to clipboard!": "已复制到剪贴板！",
}
