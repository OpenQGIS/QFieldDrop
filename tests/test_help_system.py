# -*- coding: utf-8 -*-
"""
Unit tests for the Help System:
- TOC structure & completeness
- Multi-language markdown resolution
- SVG diagram generation
- Diagram markup replacement
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from help.help_manager import HelpManager
from help.svg_builder import SvgDiagramBuilder
from help.html_builder import HtmlBuilder


class TestHelpSystem(unittest.TestCase):
    def setUp(self):
        self.mgr = HelpManager(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def test_toc_loading(self):
        chapters_zh = self.mgr.get_chapters("zh_CN")
        self.assertGreaterEqual(len(chapters_zh), 7)

        chapter_ids = [ch["id"] for ch in chapters_zh]
        self.assertIn("overview", chapter_ids)
        self.assertIn("mobile_setup", chapter_ids)
        self.assertIn("send_project", chapter_ids)
        self.assertIn("receive_results", chapter_ids)
        self.assertIn("network_guide", chapter_ids)
        self.assertIn("faq", chapter_ids)
        self.assertIn("appendix", chapter_ids)

    def test_markdown_loading_zh(self):
        for ch in self.mgr.get_chapters("zh_CN"):
            content = self.mgr.load_chapter_markdown(ch["id"], lang="zh_CN")
            self.assertTrue(len(content) > 50, f"Chapter {ch['id']} is too short")
            self.assertNotIn("404", content)
            self.assertNotIn("Not Found", content)

    def test_markdown_loading_en(self):
        for ch in self.mgr.get_chapters("en"):
            content = self.mgr.load_chapter_markdown(ch["id"], lang="en")
            self.assertTrue(len(content) > 50, f"Chapter {ch['id']} is too short")
            self.assertNotIn("404", content)
            self.assertNotIn("Not Found", content)

    def test_svg_diagram_generation(self):
        diagram_keys = [
            "ui_send_annotated",
            "ui_receive_annotated",
            "ui_mobile_annotated",
        ]
        for key in diagram_keys:
            svg_zh = SvgDiagramBuilder.get_diagram(key, lang="zh_CN")
            self.assertTrue(svg_zh.startswith("<svg"))
            self.assertTrue(svg_zh.endswith("</svg>"))
            self.assertIn("viewBox", svg_zh)

            svg_en = SvgDiagramBuilder.get_diagram(key, lang="en")
            self.assertTrue(svg_en.startswith("<svg"))
            self.assertTrue(svg_en.endswith("</svg>"))
            self.assertIn("viewBox", svg_en)

    def test_stylesheet_loading(self):
        css = self.mgr.get_stylesheet_content()
        self.assertIn("body", css)
        self.assertIn("font-family", css)

    def test_html_compilation(self):
        HtmlBuilder.compile_all(self.mgr.plugin_dir)
        html_dir = os.path.join(self.mgr.help_dir, "html")
        self.assertTrue(os.path.exists(os.path.join(html_dir, "index.html")))
        self.assertTrue(os.path.exists(os.path.join(html_dir, "zh_CN", "overview.html")))
        self.assertTrue(os.path.exists(os.path.join(html_dir, "en", "overview.html")))


if __name__ == "__main__":
    unittest.main()
