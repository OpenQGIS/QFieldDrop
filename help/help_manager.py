# -*- coding: utf-8 -*-
"""
QField LAN Drop - Help Document Manager
Handles TOC loading, multi-language markdown resolution, fallback mechanics,
dynamic SVG diagram injection, and link transformations for QTextBrowser.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional

try:
    from qgis.core import QgsSettings
    from qgis.PyQt.QtCore import QLocale
except ImportError:
    QgsSettings = None
    QLocale = None

from .svg_builder import SvgDiagramBuilder


class HelpManager:
    """Core manager for in-app help documentation and localized content."""

    def __init__(self, plugin_dir: Optional[str] = None):
        if not plugin_dir:
            plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.plugin_dir = os.path.abspath(plugin_dir)
        self.help_dir = os.path.join(self.plugin_dir, "help")
        self.assets_dir = os.path.join(self.help_dir, "assets")
        self.diagrams_dir = os.path.join(self.assets_dir, "diagrams")
        self.toc_path = os.path.join(self.help_dir, "toc.json")
        self._toc: List[Dict[str, Any]] = []
        self._load_toc()

    def _load_toc(self):
        """Loads table of contents from toc.json."""
        if os.path.exists(self.toc_path):
            try:
                with open(self.toc_path, "r", encoding="utf-8") as f:
                    self._toc = json.load(f)
            except Exception:
                self._toc = []
        else:
            self._toc = []

    def get_current_language(self) -> str:
        """Determines current locale from QGIS settings or system."""
        locale_name = ""
        if QgsSettings is not None:
            try:
                override_flag = QgsSettings().value("locale/overrideFlag", False, type=bool)
                if override_flag:
                    locale_name = QgsSettings().value("locale/userLocale", "")
            except Exception:
                pass

        if not locale_name and QLocale is not None:
            try:
                locale_name = QLocale.system().name()
            except Exception:
                pass

        if not locale_name:
            import locale
            try:
                locale_name = locale.getdefaultlocale()[0] or "zh_CN"
            except Exception:
                locale_name = "zh_CN"

        locale_clean = str(locale_name).replace("-", "_").lower()
        if locale_clean in ("zh_cn", "zh_hans", "zh"):
            return "zh_CN"
        elif locale_clean in ("zh_tw", "zh_hk", "zh_hant"):
            return "zh_TW"
        return "en"

    def get_chapters(self, lang: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Returns list of chapters with localized titles:
        [{"id": "overview", "title": "...", "icon": "...", "file": "..."}]
        """
        if not lang:
            lang = self.get_current_language()
        is_zh = lang.startswith("zh")

        chapters = []
        for item in self._toc:
            ch_id = item.get("id", "")
            icon = item.get("icon", "file.svg")
            file_name = item.get("file", "")
            title_dict = item.get("title", {})

            if is_zh:
                title = title_dict.get("zh_CN", title_dict.get("en", ch_id))
            else:
                title = title_dict.get("en", title_dict.get("zh_CN", ch_id))

            chapters.append({
                "id": ch_id,
                "title": title,
                "icon": icon,
                "file": file_name,
            })
        return chapters

    def get_chapter_by_id(self, ch_id: str) -> Optional[Dict[str, Any]]:
        for ch in self._toc:
            if ch.get("id") == ch_id:
                return ch
        return None

    def load_chapter_markdown(self, ch_id: str, lang: Optional[str] = None) -> str:
        """
        Loads markdown content for a chapter with language fallback:
        1. help/<lang>/<file>
        2. help/en/<file>
        3. help/zh_CN/<file>
        """
        if not lang:
            lang = self.get_current_language()

        ch = self.get_chapter_by_id(ch_id)
        if not ch:
            return f"# 404\n\nChapter `{ch_id}` not found."

        file_name = ch.get("file", "")
        lang_dir_name = "zh_CN" if lang.startswith("zh") else "en"

        target_path = os.path.join(self.help_dir, lang_dir_name, file_name)
        if not os.path.exists(target_path):
            # Fallback 1: English
            fallback_en = os.path.join(self.help_dir, "en", file_name)
            if os.path.exists(fallback_en):
                target_path = fallback_en
            else:
                # Fallback 2: Chinese
                fallback_zh = os.path.join(self.help_dir, "zh_CN", file_name)
                if os.path.exists(fallback_zh):
                    target_path = fallback_zh

        if not os.path.exists(target_path):
            return f"# Content Pending\n\nFile `{file_name}` is not yet available."

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return f"# Error\n\nFailed to read file: {e}"

        # Resolve dynamic diagrams: ![label](diagram://name)
        content = self._resolve_diagrams(content, lang=lang)
        return content

    def _resolve_diagrams(self, markdown_text: str, lang: str) -> str:
        """
        Replaces ![title](diagram://<diagram_name>) with an exported local SVG path.
        """
        pattern = re.compile(r"!\[(.*?)\]\(diagram://([a-zA-Z0-9_-]+)\)")

        def _repl(match):
            alt_text = match.group(1)
            diagram_name = match.group(2)
            svg_path = SvgDiagramBuilder.get_diagram(
                name=diagram_name, lang=lang, output_dir=self.diagrams_dir
            )
            if svg_path and os.path.exists(svg_path):
                # Format as standard markdown image link with forward slashes for Qt
                clean_path = svg_path.replace("\\", "/")
                return f"![{alt_text}]({clean_path})"
            return f"*(Diagram: {diagram_name})*"

        return pattern.sub(_repl, markdown_text)

    def get_stylesheet_content(self) -> str:
        """Reads help.css content."""
        css_path = os.path.join(self.assets_dir, "help.css")
        if os.path.exists(css_path):
            try:
                with open(css_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                pass
        return ""
