# -*- coding: utf-8 -*-
"""
QField LAN Drop - 官方规范纯净发布包与归档构建脚本
依据：《0-QGIS插件通用开发架构与工程化全流程指南.md》第四章 Step 5
1. 自动解析 metadata.txt 获取当前桌面端与移动端版本号
2. 绝对剔除 tests/, testdata/, 0_*.svg, ROADMAP.md 等非运行时开发杂质
3. 严格构建顶级目录名为 QFieldDrop/ 的纯净桌面端 ZIP 发布包 (使用 POSIX / 路径)
4. 严格构建移动端 QField 插件 ZIP 发布包：
   - QFieldDropMobile_V-X.Y.Z.zip (根目录直装包)
   - qfield_drop_mobile.zip (通用直链安装包)
   - QFieldDropMobile_folder_V-X.Y.Z.zip (含 qfield_drop/ 文件夹包裹，供沙盒手动解压)
5. 计算 SHA256 并更新 QFieldDropMobile/README.md
6. 执行发布前合规断言深度扫描
7. 双轨归档至 QFieldDrop-4QGIS/、QFieldDropMobile/ 与 QFieldDrop_History/ 并同步纯净源码
"""

import os
import sys
import re
import fnmatch
import hashlib
import zipfile
import shutil
import configparser

HERE = os.path.dirname(os.path.abspath(__file__))
TOP_FOLDER_NAME = "QFieldDrop"

# 严禁打入官方分发包的黑名单目录
EXCLUDE_DIRS = {
    "tests", "test", "testdata", "dev", "scratch", "tools",
    "__pycache__", ".git", ".github", ".vscode", ".idea", "dist",
    "icons_Component", ".pytest_cache"
}

# 严禁打入官方分发包的黑名单文件通配符
EXCLUDE_FILE_PATTERNS = [
    "0_*.svg", "*.pyc", "*.pyo", "*.pyd.tmp",
    "ROADMAP.md", "DISTRIBUTION_GUIDE.md", "PROJECT_STRUCTURE.md",
    "*.gpkg-shm", "*.gpkg-wal", "*.db", "keys.json",
    ".gitignore", ".bandit", ".flake8", "*.log",
    "build_clean_release.py", "build_icons_component.py", "build_mobile_release.py",
    "*.ts", "build_i18n.py"
]


def get_version(source_dir: str) -> str:
    """从 metadata.txt 读取语义化版本号"""
    meta_path = os.path.join(source_dir, "metadata.txt")
    if not os.path.exists(meta_path):
        raise FileNotFoundError(f"metadata.txt not found in {source_dir}")
    cfg = configparser.ConfigParser()
    cfg.read(meta_path, encoding="utf-8")
    return cfg.get("general", "version").strip()


def calc_sha256(filepath: str) -> str:
    """计算文件的 SHA-256 校验哈希值"""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def build_clean_release_zip(source_dir: str, output_zip_path: str, top_folder_name: str):
    """构建 100% 符合 QGIS 官方审核规范的纯净桌面发布 ZIP 包"""
    os.makedirs(os.path.dirname(output_zip_path), exist_ok=True)

    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for file in files:
                if any(fnmatch.fnmatch(file, pattern) for pattern in EXCLUDE_FILE_PATTERNS):
                    continue

                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, source_dir)
                archive_name = f"{top_folder_name}/{rel_path}".replace(os.sep, "/")
                zf.write(full_path, archive_name)


def build_mobile_release_zip(mobile_dir: str, output_zip_path: str, wrap_folder: str = ""):
    """构建 QField 移动端插件发布包（支持根目录直装模式与文件夹包裹模式）"""
    os.makedirs(os.path.dirname(output_zip_path), exist_ok=True)

    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(mobile_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for file in files:
                if any(fnmatch.fnmatch(file, pattern) for pattern in EXCLUDE_FILE_PATTERNS):
                    continue
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, mobile_dir)
                if wrap_folder:
                    archive_name = f"{wrap_folder}/{rel_path}".replace(os.sep, "/")
                else:
                    archive_name = rel_path.replace(os.sep, "/")
                zf.write(full_path, archive_name)


def verify_zip_integrity(zip_path: str, top_folder_name: str):
    """深度扫描检查生成的桌面端 ZIP，确保 0 违规条目且路径全部为正斜杠"""
    with zipfile.ZipFile(zip_path, 'r') as zf:
        namelist = zf.namelist()
        for name in namelist:
            assert "\\" not in name, f"❌ 发现非法 Windows 反斜杠: {name}"
            assert name.startswith(f"{top_folder_name}/"), f"❌ 根目录不合规: {name}"
            parts = name.split("/")
            assert not any(p in EXCLUDE_DIRS for p in parts), f"❌ 发现泄露的排除目录: {name}"
            filename = parts[-1]
            if filename:
                assert not any(fnmatch.fnmatch(filename, pat) for pat in EXCLUDE_FILE_PATTERNS), (
                    f"❌ 发现泄露的排除文件: {name}"
                )
    print(f"✅ 桌面端 ZIP 合规性扫描通过：共包含 {len(namelist)} 个纯净资源文件")


def verify_mobile_zip_integrity(zip_path: str, wrap_folder: str = ""):
    """深度扫描检查生成的移动端 ZIP，确保必要文件存在且无非法路径"""
    with zipfile.ZipFile(zip_path, 'r') as zf:
        namelist = zf.namelist()
        prefix = f"{wrap_folder}/" if wrap_folder else ""
        assert f"{prefix}metadata.txt" in namelist, f"❌ 移动端插件缺少 {prefix}metadata.txt"
        assert f"{prefix}main.qml" in namelist, f"❌ 移动端插件缺少 {prefix}main.qml"
        assert f"{prefix}icon.svg" in namelist, f"❌ 移动端插件缺少 {prefix}icon.svg"
        for name in namelist:
            assert "\\" not in name, f"❌ 发现非法 Windows 反斜杠: {name}"
            parts = name.split("/")
            assert not any(p in EXCLUDE_DIRS for p in parts), f"❌ 发现泄露的排除目录: {name}"
    print(f"✅ 移动端 ZIP ({os.path.basename(zip_path)}) 扫描通过：共包含 {len(namelist)} 个纯净资源文件")


def sync_clean_source(source_dir: str, target_dir: str):
    """同步输出纯净源码镜像目录"""
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir, exist_ok=True)

    for root, dirs, files in os.walk(source_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for file in files:
            if any(fnmatch.fnmatch(file, pattern) for pattern in EXCLUDE_FILE_PATTERNS):
                continue
            src_file = os.path.join(root, file)
            rel_path = os.path.relpath(src_file, source_dir)
            dst_file = os.path.join(target_dir, rel_path)
            os.makedirs(os.path.dirname(dst_file), exist_ok=True)
            shutil.copy2(src_file, dst_file)
    print(f"✅ 纯净源码镜像已同步至: {target_dir}")


def update_mobile_readme_hashes(readme_path: str, hashes: dict):
    """更新移动端发布目录 README.md 中的 SHA256 校验码"""
    if not os.path.exists(readme_path):
        return
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    for filename, sha in hashes.items():
        # 匹配对应表格行的 SHA256 并替换
        pattern = rf"(\*\*{re.escape(filename)}\*\*.*?\| `)[a-f0-9]{{64}}(`)"
        content = re.sub(pattern, rf"\g<1>{sha}\g<2>", content)

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ 移动端 README.md SHA256 校验码表已更新")


def main():
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except (AttributeError, OSError):
            pass

    desktop_version = get_version(HERE)
    mobile_dir = os.path.join(HERE, "mobile")
    mobile_version = get_version(mobile_dir)

    print(f"=== QFieldDrop 发布打包流水线 ===")
    print(f"  桌面端 QGIS 插件版本: v{desktop_version}")
    print(f"  移动端 QField 助手版本: v{mobile_version}")

    # 目标路径设定
    lab_base = r"E:\QGIS文章\OpenQGIS_Lab\OpenQGIS_QGISPlugins_LAB\QFieldDrop"
    rel_4qgis_dir = os.path.join(lab_base, "QFieldDrop-4QGIS")
    rel_mobile_dir = os.path.join(lab_base, "QFieldDropMobile")
    history_dir = os.path.join(lab_base, "QFieldDrop_History")

    os.makedirs(rel_4qgis_dir, exist_ok=True)
    os.makedirs(rel_mobile_dir, exist_ok=True)
    os.makedirs(history_dir, exist_ok=True)

    # ---------------- 1. 移动端 QField 插件打包 ----------------
    print("\n--- 正在构建移动端 QField 插件 ---")
    mobile_zip_filename = f"QFieldDropMobile_V-{mobile_version}.zip"
    mobile_folder_zip_filename = f"QFieldDropMobile_folder_V-{mobile_version}.zip"

    mobile_target_zip = os.path.join(rel_mobile_dir, mobile_zip_filename)
    mobile_latest_zip = os.path.join(rel_mobile_dir, "qfield_drop_mobile.zip")
    mobile_folder_zip = os.path.join(rel_mobile_dir, mobile_folder_zip_filename)

    # 1.1 构建根目录直装包
    build_mobile_release_zip(mobile_dir, mobile_target_zip, wrap_folder="")
    verify_mobile_zip_integrity(mobile_target_zip, wrap_folder="")
    print(f"✅ 移动端直装包生成: {mobile_target_zip} ({os.path.getsize(mobile_target_zip)} bytes)")

    # 1.2 复制为通用直链包
    shutil.copy2(mobile_target_zip, mobile_latest_zip)

    # 1.3 构建文件夹包裹包 (qfield_drop/)
    build_mobile_release_zip(mobile_dir, mobile_folder_zip, wrap_folder="qfield_drop")
    verify_mobile_zip_integrity(mobile_folder_zip, wrap_folder="qfield_drop")
    print(f"✅ 移动端沙盒包裹包生成: {mobile_folder_zip} ({os.path.getsize(mobile_folder_zip)} bytes)")

    # 1.4 备份到历史归档库
    shutil.copy2(mobile_target_zip, os.path.join(history_dir, mobile_zip_filename))
    shutil.copy2(mobile_folder_zip, os.path.join(history_dir, mobile_folder_zip_filename))
    print(f"✅ 移动端版本归档备份完成")

    # 1.5 同步移动端纯净源码镜像
    clean_mobile_src_dir = os.path.join(rel_mobile_dir, "QFieldDropMobile")
    sync_clean_source(mobile_dir, clean_mobile_src_dir)

    # 1.6 计算校验码并刷新移动端 README.md
    hashes = {
        f"`{mobile_zip_filename}`": calc_sha256(mobile_target_zip),
        "`qfield_drop_mobile.zip`": calc_sha256(mobile_latest_zip),
        f"`{mobile_folder_zip_filename}`": calc_sha256(mobile_folder_zip),
    }
    update_mobile_readme_hashes(os.path.join(rel_mobile_dir, "README.md"), hashes)

    # ---------------- 2. 桌面端 QGIS 插件打包 ----------------
    print("\n--- 正在构建桌面端 QGIS 插件 (已内置更新后的移动端组件) ---")
    desktop_zip_filename = f"QFieldDrop_V-{desktop_version}.zip"
    desktop_target_zip = os.path.join(rel_4qgis_dir, desktop_zip_filename)
    desktop_history_zip = os.path.join(history_dir, desktop_zip_filename)

    build_clean_release_zip(HERE, desktop_target_zip, TOP_FOLDER_NAME)
    print(f"✅ 桌面端发布包生成成功: {desktop_target_zip} ({os.path.getsize(desktop_target_zip)} bytes)")
    verify_zip_integrity(desktop_target_zip, TOP_FOLDER_NAME)

    # 备份至历史归档
    shutil.copy2(desktop_target_zip, desktop_history_zip)
    print(f"✅ 桌面端归档备份至: {desktop_history_zip}")

    # 同步桌面端纯净源码镜像
    clean_desktop_src_dir = os.path.join(rel_4qgis_dir, TOP_FOLDER_NAME)
    sync_clean_source(HERE, clean_desktop_src_dir)

    print("\n🎉 发布流水线执行完成！桌面端与移动端纯净包及源码镜像已全部就绪。")


if __name__ == "__main__":
    main()
