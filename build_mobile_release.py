# -*- coding: utf-8 -*-
r"""
QFieldDrop Mobile - 手机端伴侣插件官方发布打包脚本
依据 OpenQGIS 工程化规范，将手机端 QField QML 插件独立打包至：
E:\QGIS文章\OpenQGIS_Lab\OpenQGIS_QGISPlugins_LAB\QFieldDrop\QFieldDropMobile\
生成面向 GitHub Releases 与 QField 客户端的一键安装包与纯净镜像。
"""

import os
import sys
import shutil
import zipfile
import hashlib
import configparser

PLUGIN_ROOT = os.path.dirname(os.path.abspath(__file__))
MOBILE_SRC = os.path.join(PLUGIN_ROOT, "mobile")
TARGET_BASE = r"E:\QGIS文章\OpenQGIS_Lab\OpenQGIS_QGISPlugins_LAB\QFieldDrop"
MOBILE_DIST_DIR = os.path.join(TARGET_BASE, "QFieldDropMobile")
HISTORY_DIR = os.path.join(TARGET_BASE, "QFieldDrop_History")

# 严禁打入发布包的文件与目录
EXCLUDE_DIRS = {"__pycache__", ".git", ".idea", ".vscode"}
EXCLUDE_FILES = {"*.pyc", "*.pyo", ".DS_Store", "Thumbs.db"}


def get_version(src_dir: str) -> str:
    meta_path = os.path.join(src_dir, "metadata.txt")
    if not os.path.exists(meta_path):
        return "1.0.0"
    cfg = configparser.ConfigParser()
    cfg.read(meta_path, encoding="utf-8")
    return cfg.get("general", "version", fallback="1.0.0").strip()


def calculate_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def build_root_zip(src_dir: str, out_zip: str):
    """
    QField 官方【从压缩包安装 (Install from ZIP)】标准格式：
    metadata.txt、main.qml、icon.svg 位于 ZIP 顶级根目录。
    """
    os.makedirs(os.path.dirname(out_zip), exist_ok=True)
    with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(src_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for file in files:
                if any(file.endswith(ext.replace('*', '')) for ext in EXCLUDE_FILES):
                    continue
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, src_dir).replace(os.sep, "/")
                zf.write(full_path, rel_path)


def build_folder_zip(src_dir: str, out_zip: str, folder_name: str = "qfield_drop"):
    """
    包裹文件夹的标准格式 (用于手动解压至手机 plugins/qfield_drop/ 目录)
    """
    os.makedirs(os.path.dirname(out_zip), exist_ok=True)
    with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(src_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for file in files:
                if any(file.endswith(ext.replace('*', '')) for ext in EXCLUDE_FILES):
                    continue
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, src_dir).replace(os.sep, "/")
                arc_name = f"{folder_name}/{rel_path}"
                zf.write(full_path, arc_name)


def sync_clean_source(src_dir: str, target_dir: str):
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir, exist_ok=True)
    for root, dirs, files in os.walk(src_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for file in files:
            if any(file.endswith(ext.replace('*', '')) for ext in EXCLUDE_FILES):
                continue
            src_file = os.path.join(root, file)
            rel_path = os.path.relpath(src_file, src_dir)
            dst_file = os.path.join(target_dir, rel_path)
            os.makedirs(os.path.dirname(dst_file), exist_ok=True)
            shutil.copy2(src_file, dst_file)


def main():
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except (AttributeError, OSError):
            pass

    version = get_version(MOBILE_SRC)
    print(f"=== QFieldDrop Mobile 发布打包流水线 (v{version}) ===")

    os.makedirs(MOBILE_DIST_DIR, exist_ok=True)
    os.makedirs(HISTORY_DIR, exist_ok=True)

    # 1. 构建主发布包 (QField 原生 Install from ZIP 根目录格式)
    zip_ver_name = f"QFieldDropMobile_V-{version}.zip"
    zip_ver_path = os.path.join(MOBILE_DIST_DIR, zip_ver_name)
    build_root_zip(MOBILE_SRC, zip_ver_path)
    sha256_ver = calculate_sha256(zip_ver_path)
    print(f"✅ 生成标准安装包: {zip_ver_name} ({os.path.getsize(zip_ver_path)} bytes)")
    print(f"   SHA256: {sha256_ver}")

    # 2. 复制通用命名别名包 (方便直链引用)
    zip_alias_path = os.path.join(MOBILE_DIST_DIR, "qfield_drop_mobile.zip")
    shutil.copyfile(zip_ver_path, zip_alias_path)
    print(f"✅ 生成通用直链别名包: qfield_drop_mobile.zip")

    # 3. 构建带目录包裹的解压包 (方便手动解压缩至 Android 沙盒)
    zip_folder_name = f"QFieldDropMobile_folder_V-{version}.zip"
    zip_folder_path = os.path.join(MOBILE_DIST_DIR, zip_folder_name)
    build_folder_zip(MOBILE_SRC, zip_folder_path, folder_name="qfield_drop")
    print(f"✅ 生成沙盒解压专用包: {zip_folder_name}")

    # 4. 同步纯净源码镜像目录
    clean_src_mirror = os.path.join(MOBILE_DIST_DIR, "QFieldDropMobile")
    sync_clean_source(MOBILE_SRC, clean_src_mirror)
    print(f"✅ 纯净源码镜像已同步至: {clean_src_mirror}")

    # 5. 备份至历史版本归档库
    history_backup = os.path.join(HISTORY_DIR, zip_ver_name)
    shutil.copyfile(zip_ver_path, history_backup)
    print(f"✅ 历史版本归档备份至: {history_backup}")

    # 6. 生成面向 Release 发布的 README 说明文档
    readme_path = os.path.join(MOBILE_DIST_DIR, "README.md")
    readme_content = f"""# QFieldDrop Mobile 发布包 (Release Distribution)

本项目是配套桌面端 QGIS 插件 [QFieldDrop](https://github.com/OpenQGIS/QFieldDrop) 的移动端协同插件（运行于手机 QField 内部）。

---

## 📦 发布文件清单 (Release Assets)

| 文件名 | 类型 | 说明与适用场景 | SHA256 校验码 |
| :--- | :---: | :--- | :--- |
| **`{zip_ver_name}`** | **推荐** | QField 原生【从压缩包安装 (Install from ZIP)】标准格式，直接在 QField 中选中安装 | `{sha256_ver}` |
| **`qfield_drop_mobile.zip`** | 常用 | 通用直链安装包（与上面完全同构），适合静态托管与直链下载 | `{sha256_ver}` |
| **`{zip_folder_name}`** | 备用 | 内含 `qfield_drop/` 文件夹包裹，供直接解压至手机文件管理器沙盒目录使用 | `{calculate_sha256(zip_folder_path)}` |
| **`QFieldDropMobile/`** | 源码 | 未压缩的纯净源码镜像目录（自包含 `metadata.txt`, `main.qml`, `icon.svg`） | - |

---

## 📲 手机端 QField 安装指南

### 方式 A：QField 内部一键安装（最便捷）
1. 将下载的 **`{zip_ver_name}`** 发送到手机（通过微信、QQ、网盘、LocalSend 或 USB 传输）；
2. 在手机上启动 **QField**，点击左上角主菜单 $\\rightarrow$ **设置 (Settings)** $\\rightarrow$ **插件 (Plugins)**；
3. 点击右上角 **从压缩包安装 (Install from ZIP)**；
4. 在手机文件选择器中选中 `{zip_ver_name}`，确认安装并启用插件；
5. 返回 QField 主地图界面，顶部工具栏即可出现 **[回传电脑]** 动作按钮。

### 方式 B：局域网 URL 在线直装 (Install from URL)
1. 保持手机与内业电脑连接在同一 Wi-Fi 或热点下；
2. 电脑端 QGIS 保持 QFieldDrop 服务运行（默认端口 8899）；
3. 手机 QField 进入 **设置** $\\rightarrow$ **插件** $\\rightarrow$ **从 URL 安装**；
4. 输入 `http://<电脑IP>:8899/mobile.zip`，点击下载并启用。

### 方式 C：Android 存储沙盒手动解压部署
将 `{zip_folder_name}` 解压出来的 `qfield_drop` 文件夹整体复制到：
- 路径：`/sdcard/Android/data/ch.opengis.qfield/files/plugins/qfield_drop/`
- 重启 QField 即生效。

---

## 🌟 核心特性
- 🚀 **QField 工具栏集成**：直接嵌入 QField 顶部工具栏，外业作业途中随时一键交还数据。
- 📦 **增量与整包双模回传**：支持仅回传修改过的要素图层（`.gpkg`）和现场照片，也支持全工程整包回传。
- 🔍 **局域网 mDNS 自动发现**：自动发现内业电脑服务，无缝免配置。
"""
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)
    print(f"✅ 生成 Release 说明文档: {readme_path}")

    print("\n🎉 QFieldDrop Mobile 独立发布包打包完成！可直接用于 Release 释放。")


if __name__ == "__main__":
    main()
