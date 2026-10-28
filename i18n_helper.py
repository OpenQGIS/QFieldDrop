# -*- coding: utf-8 -*-
"""
QField LAN Drop - 集中式多语言国际化 (i18n) 助手
- tr(): 优先命中 QTranslator (.qm)；未命中且当前环境为中文时，回退内置中文词典
- load_translator() / unload_translator(): QTranslator 生命周期管理（在插件主类中调用）
"""

import os
from qgis.PyQt.QtCore import QCoreApplication, QLocale, QTranslator
from qgis.core import QgsSettings

from .i18n_strings import _zh_translations

CONTEXT = "QFieldDrop"


def tr(text: str, disambiguation=None) -> str:
    """翻译静态英文源文本。严禁传入动态 f-string（动态内容请用 {0} 占位 + .format()）"""
    res = QCoreApplication.translate(CONTEXT, text, disambiguation)
    if res == text:
        locale_name = QgsSettings().value("locale/userLocale", QLocale.system().name())
        if locale_name and str(locale_name).lower().startswith("zh"):
            return _zh_translations.get(text, text)
    return res


def load_translator(plugin_dir: str):
    """按 QGIS 覆盖语言或系统语言加载 i18n/QFieldDrop_<locale>.qm；返回 translator 实例或 None"""
    override_flag = QgsSettings().value("locale/overrideFlag", False, type=bool)
    if override_flag:
        locale_name = QgsSettings().value("locale/userLocale", "")
    else:
        locale_name = QLocale.system().name()

    if not locale_name:
        locale_name = "en"

    # 标准化 locale 代码（例如 zh-hans -> zh_CN）
    locale_clean = str(locale_name).replace("-", "_").lower()
    if locale_clean in ("zh_cn", "zh_hans", "zh"):
        locale_clean = "zh_CN"
    elif locale_clean in ("zh_tw", "zh_hk", "zh_hant"):
        locale_clean = "zh_TW"

    qm_path = os.path.join(plugin_dir, "i18n", f"QFieldDrop_{locale_clean}.qm")
    if not os.path.exists(qm_path):
        short_code = locale_clean.split("_")[0]
        qm_path = os.path.join(plugin_dir, "i18n", f"QFieldDrop_{short_code}.qm")

    if os.path.exists(qm_path):
        translator = QTranslator()
        if translator.load(qm_path):
            QCoreApplication.installTranslator(translator)
            return translator
    return None


def unload_translator(translator):
    """卸载翻译器，防范生命周期外泄影响其他 QGIS 插件"""
    if translator is not None:
        try:
            QCoreApplication.removeTranslator(translator)
        except (AttributeError, RuntimeError):
            pass
    return None
