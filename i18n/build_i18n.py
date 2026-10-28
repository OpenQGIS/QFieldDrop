# -*- coding: utf-8 -*-
"""
QField LAN Drop - 翻译文件构建与编译工具
从 i18n_strings._zh_translations 自动生成：
  - i18n/QFieldDrop_zh_CN.ts
  - i18n/QFieldDrop_zh_CN.qm
  - i18n/QFieldDrop_zh_TW.ts
  - i18n/QFieldDrop_zh_TW.qm
纯 Python 实现 ELF Hash 算法与 Qt QM 二进制封装，零外部 Qt 工具依赖。
"""

import os
import struct
import sys
import xml.etree.ElementTree as ET  # nosec B405

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(HERE)
sys.path.insert(0, PLUGIN_ROOT)

from i18n_strings import _zh_translations  # noqa: E402

CONTEXT = "QFieldDrop"


def build_ts(lang: str, translations_dict: dict) -> str:
    """生成标准 Qt XML 格式翻译源文件 (.ts)"""
    ts_path = os.path.join(HERE, f"QFieldDrop_{lang}.ts")
    root = ET.Element("TS", {"version": "2.1", "language": lang, "sourcelanguage": "en"})
    ctx = ET.SubElement(root, "context")
    ET.SubElement(ctx, "name").text = CONTEXT
    for src in sorted(translations_dict):
        msg = ET.SubElement(ctx, "message")
        ET.SubElement(msg, "source").text = src
        ET.SubElement(msg, "translation").text = translations_dict[src]
    try:
        ET.indent(root)
    except AttributeError:
        pass
    ET.ElementTree(root).write(ts_path, encoding="utf-8", xml_declaration=True)
    return ts_path


def _elf_hash(data: bytes) -> int:
    """Qt 内部使用的 ELF Hash 散列算法"""
    h = 0
    for byte in data:
        h = (h << 4) + byte
        g = h & 0xF0000000
        if g:
            h ^= g >> 24
        h &= ~g & 0xFFFFFFFF
    return h & 0xFFFFFFFF


def build_qm(lang: str, translations_dict: dict) -> str:
    """编译生成标准 Qt 二进制翻译文件 (.qm)"""
    msg_block = bytearray()
    hash_entries = []
    ctx_bytes = CONTEXT.encode("utf-8")

    for src in sorted(translations_dict):
        translation = translations_dict[src]
        offset = len(msg_block)

        trans_bytes = translation.encode("utf-16-be")
        msg_block.append(0x03)
        msg_block.extend(struct.pack(">I", len(trans_bytes)))
        msg_block.extend(trans_bytes)

        msg_block.append(0x07)
        msg_block.extend(struct.pack(">I", len(ctx_bytes)))
        msg_block.extend(ctx_bytes)

        src_bytes = src.encode("utf-8")
        msg_block.append(0x06)
        msg_block.extend(struct.pack(">I", len(src_bytes)))
        msg_block.extend(src_bytes)

        msg_block.append(0x01)
        hash_entries.append((_elf_hash(src_bytes), offset))

    hash_block = bytearray()
    for h, offset in sorted(hash_entries):
        hash_block.extend(struct.pack(">I", h))
        hash_block.extend(struct.pack(">I", offset))

    qm = bytearray(bytes.fromhex("3cb86418caef9c95cd211cbf60a1bddd"))
    qm.append(0x42)
    qm.extend(struct.pack(">I", len(hash_block)))
    qm.extend(hash_block)
    qm.append(0x69)
    qm.extend(struct.pack(">I", len(msg_block)))
    qm.extend(msg_block)

    qm_path = os.path.join(HERE, f"QFieldDrop_{lang}.qm")
    with open(qm_path, "wb") as f:
        f.write(qm)
    return qm_path


def main():
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except (AttributeError, OSError):
            pass
    os.makedirs(HERE, exist_ok=True)
    # 1. 编译简体中文 (zh_CN)
    ts_cn = build_ts("zh_CN", _zh_translations)
    qm_cn = build_qm("zh_CN", _zh_translations)
    print(f"[OK] [zh_CN] TS -> {ts_cn}")
    print(f"[OK] [zh_CN] QM -> {qm_cn} ({os.path.getsize(qm_cn)} bytes, {len(_zh_translations)} entries)")

    # 2. 编译繁体中文 (zh_TW)
    # 简繁对照替换表 (针对高频核心词汇)
    tw_map = {
        "投送": "投送",
        "局域网": "區域網路",
        "直传": "直傳",
        "工程": "專案",
        "成果": "成果",
        "手机": "手機",
        "助手": "助手",
        "扫码": "掃碼",
        "唤醒": "喚醒",
        "接收": "接收",
        "回传": "回傳",
        "网卡": "網卡",
        "图层": "圖層",
        "外部": "外部",
        "详情": "詳情",
        "设备": "設備",
        "列表": "列表",
        "目录": "目錄",
        "解压": "解壓",
        "链接": "連結",
        "复制": "複製",
        "刷新": "重新整理",
        "保存": "儲存",
        "设置": "設定",
        "提示": "提示",
        "错误": "錯誤",
        "警告": "警告",
        "确定": "確定",
        "取消": "取消",
        "关闭": "關閉",
    }
    _tw_translations = {}
    for k, v in _zh_translations.items():
        val = v
        for s_word, t_word in tw_map.items():
            val = val.replace(s_word, t_word)
        _tw_translations[k] = val

    ts_tw = build_ts("zh_TW", _tw_translations)
    qm_tw = build_qm("zh_TW", _tw_translations)
    print(f"[OK] [zh_TW] TS -> {ts_tw}")
    print(f"[OK] [zh_TW] QM -> {qm_tw} ({os.path.getsize(qm_tw)} bytes, {len(_tw_translations)} entries)")


if __name__ == "__main__":
    main()
