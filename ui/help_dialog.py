# -*- coding: utf-8 -*-
"""
QField LAN Drop - In-App Help Center Dialog (内置离线图文帮助中心)
Features:
- Left-right split layout with chapter tree and fast search
- Multi-language switching (zh_CN / en) on the fly
- Responsive QTextBrowser rendering Markdown and declarative SVGs
- Deep-link navigation: chapter:xxx, anchor links, and external web URLs
- Context-sensitive jumping (e.g. HelpDialog.show_help(section_id="send_project"))
"""

import os
from typing import Optional

from qgis.PyQt.QtCore import Qt, QUrl
from qgis.PyQt.QtGui import QDesktopServices, QIcon, QFont
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QWidget, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QTextBrowser, QPushButton,
    QComboBox, QFrame, QApplication
)

from ..help.help_manager import HelpManager
from .icon_helper import get_icon, get_icon_path


class HelpDialog(QDialog):
    _instance: Optional["HelpDialog"] = None

    def __init__(self, parent=None, initial_section: str = "overview", lang: Optional[str] = None):
        super().__init__(parent)
        self.help_mgr = HelpManager()
        self.current_lang = lang or self.help_mgr.get_current_language()
        self.initial_section = initial_section
        self._chapters = []

        self.setWindowTitle(self._tr("QField LAN Drop - 使用手册与帮助中心", "QField LAN Drop - User Manual & Help Center"))
        self.resize(980, 680)
        self.setMinimumSize(800, 540)

        # Set window icon
        icon = get_icon("icon_help")
        if icon.isNull():
            icon = get_icon("help-circle")
        if not icon.isNull():
            self.setWindowIcon(icon)

        self._init_ui()
        self._populate_chapters()
        self.navigate_to_chapter(self.initial_section)

    def _tr(self, zh: str, en: str) -> str:
        return zh if self.current_lang.startswith("zh") else en

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        # Main Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal if hasattr(Qt, "Orientation") else Qt.Horizontal)

        # ---------------- Left Navigation Pane ----------------
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 6, 0)
        left_layout.setSpacing(8)

        # Search box
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(self._tr("🔍 搜索章节...", "🔍 Search chapters..."))
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._filter_chapters)
        left_layout.addWidget(self.search_edit)

        # Chapter list
        self.chapter_list = QListWidget()
        self.chapter_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection if hasattr(QListWidget, "SelectionMode") else QListWidget.SingleSelection)
        self.chapter_list.currentRowChanged.connect(self._on_chapter_selected)
        self.chapter_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                background-color: #F8FAFC;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px 10px;
                border-radius: 4px;
                margin-bottom: 2px;
                font-size: 13px;
                color: #1E293B;
            }
            QListWidget::item:hover {
                background-color: #E2E8F0;
            }
            QListWidget::item:selected {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: bold;
            }
        """)
        left_layout.addWidget(self.chapter_list)

        # Left bottom: Open in Browser
        self.btn_browser = QPushButton(self._tr("↗ 在默认浏览器中查看", "↗ View in Browser"))
        self.btn_browser.setStyleSheet("padding: 5px 10px; font-size: 12px; color: #475569;")
        self.btn_browser.clicked.connect(self._open_in_browser)
        left_layout.addWidget(self.btn_browser)

        left_widget.setMinimumWidth(210)
        left_widget.setMaximumWidth(260)
        splitter.addWidget(left_widget)

        # ---------------- Right Content Pane ----------------
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(6, 0, 0, 0)
        right_layout.setSpacing(8)

        # Top Bar
        top_bar = QHBoxLayout()
        self.lbl_title = QLabel()
        self.lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        top_bar.addWidget(self.lbl_title)
        top_bar.addStretch()

        # Language Selector
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("🇨🇳 简体中文", "zh_CN")
        self.lang_combo.addItem("🌐 English", "en")
        idx = 0 if self.current_lang.startswith("zh") else 1
        self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        top_bar.addWidget(self.lang_combo)

        right_layout.addLayout(top_bar)

        # Content Browser
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(False)
        self.text_browser.anchorClicked.connect(self._handle_link_clicked)
        default_font = QFont("Microsoft YaHei" if self.current_lang.startswith("zh") else "Segoe UI", 10)
        self.text_browser.setFont(default_font)
        self.text_browser.setStyleSheet("""
            QTextBrowser {
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                background-color: #FFFFFF;
                padding: 12px;
            }
        """)
        right_layout.addWidget(self.text_browser)

        # Bottom Bar: Prev / Next / Close
        bottom_bar = QHBoxLayout()
        self.btn_prev = QPushButton(self._tr("◀ 上一章", "◀ Previous"))
        self.btn_prev.clicked.connect(self._go_prev_chapter)
        bottom_bar.addWidget(self.btn_prev)

        self.btn_next = QPushButton(self._tr("下一章 ▶", "Next ▶"))
        self.btn_next.clicked.connect(self._go_next_chapter)
        bottom_bar.addWidget(self.btn_next)

        bottom_bar.addStretch()

        self.btn_close = QPushButton(self._tr("关闭 (Esc)", "Close (Esc)"))
        self.btn_close.clicked.connect(self.accept)
        bottom_bar.addWidget(self.btn_close)

        right_layout.addLayout(bottom_bar)
        splitter.addWidget(right_widget)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        root_layout.addWidget(splitter)

    def _populate_chapters(self):
        """Loads and lists chapters from HelpManager."""
        self.chapter_list.blockSignals(True)
        self.chapter_list.clear()
        self._chapters = self.help_mgr.get_chapters(lang=self.current_lang)

        for ch in self._chapters:
            item = QListWidgetItem(ch["title"])
            item.setData(Qt.ItemDataRole.UserRole if hasattr(Qt, "ItemDataRole") else Qt.UserRole, ch["id"])

            # Attach icon
            icon_name = ch.get("icon", "file.svg").replace(".svg", "")
            icon = get_icon(icon_name)
            if not icon.isNull():
                item.setIcon(icon)

            self.chapter_list.addItem(item)

        self.chapter_list.blockSignals(False)

    def navigate_to_chapter(self, section_id: str):
        """Selects and displays the specified chapter ID."""
        for row in range(self.chapter_list.count()):
            item = self.chapter_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole if hasattr(Qt, "ItemDataRole") else Qt.UserRole) == section_id:
                self.chapter_list.setCurrentRow(row)
                return

        if self.chapter_list.count() > 0:
            self.chapter_list.setCurrentRow(0)

    def _on_chapter_selected(self, row: int):
        if row < 0 or row >= len(self._chapters):
            return

        ch = self._chapters[row]
        ch_id = ch["id"]
        ch_title = ch["title"]
        self.lbl_title.setText(ch_title)

        # Load content
        markdown_text = self.help_mgr.load_chapter_markdown(ch_id=ch_id, lang=self.current_lang)
        css_style = self.help_mgr.get_stylesheet_content()

        # Normalize relative asset paths to absolute file paths for QTextBrowser
        assets_dir_url = self.help_mgr.assets_dir.replace("\\", "/")
        markdown_text = markdown_text.replace("../../assets", assets_dir_url)

        # Render markdown in QTextBrowser with stylesheet and base URL applied
        if hasattr(self.text_browser.document(), "setBaseUrl"):
            base_url = QUrl.fromLocalFile(os.path.join(self.help_mgr.assets_dir) + os.sep)
            self.text_browser.document().setBaseUrl(base_url)

        if css_style:
            self.text_browser.document().setDefaultStyleSheet(css_style)

        if hasattr(self.text_browser, "setMarkdown"):
            # Qt 5.14+ native Markdown support
            self.text_browser.setMarkdown(markdown_text)
        else:
            # Fallback simple text
            self.text_browser.setPlainText(markdown_text)

        # Update Prev/Next buttons
        self.btn_prev.setEnabled(row > 0)
        self.btn_next.setEnabled(row < len(self._chapters) - 1)

    def _handle_link_clicked(self, url: QUrl):
        """Dispatches internal and external links."""
        url_str = url.toString()
        if url_str.startswith("chapter:"):
            target_id = url_str.split(":", 1)[1]
            self.navigate_to_chapter(target_id)
        elif url_str.startswith("http://") or url_str.startswith("https://"):
            QDesktopServices.openUrl(url)
        elif url_str.startswith("#"):
            self.text_browser.scrollToAnchor(url_str[1:])
        else:
            # Default open
            QDesktopServices.openUrl(url)

    def _on_language_changed(self, index: int):
        self.current_lang = self.lang_combo.itemData(index)
        current_row = self.chapter_list.currentRow()
        current_id = self._chapters[current_row]["id"] if (0 <= current_row < len(self._chapters)) else "overview"

        # Update UI text
        self.setWindowTitle(self._tr("QField LAN Drop - 使用手册与帮助中心", "QField LAN Drop - User Manual & Help Center"))
        self.search_edit.setPlaceholderText(self._tr("🔍 搜索章节...", "🔍 Search chapters..."))
        self.btn_browser.setText(self._tr("↗ 在默认浏览器中查看", "↗ View in Browser"))
        self.btn_prev.setText(self._tr("◀ 上一章", "◀ Previous"))
        self.btn_next.setText(self._tr("下一章 ▶", "Next ▶"))
        self.btn_close.setText(self._tr("关闭 (Esc)", "Close (Esc)"))

        self._populate_chapters()
        self.navigate_to_chapter(current_id)

    def _filter_chapters(self, query: str):
        query = query.strip().lower()
        for row in range(self.chapter_list.count()):
            item = self.chapter_list.item(row)
            item.setHidden(query != "" and query not in item.text().lower())

    def _go_prev_chapter(self):
        row = self.chapter_list.currentRow()
        if row > 0:
            self.chapter_list.setCurrentRow(row - 1)

    def _go_next_chapter(self):
        row = self.chapter_list.currentRow()
        if row < self.chapter_list.count() - 1:
            self.chapter_list.setCurrentRow(row + 1)

    def _open_in_browser(self):
        """Opens current chapter as full HTML documentation website in system default browser."""
        current_row = self.chapter_list.currentRow()
        if 0 <= current_row < len(self._chapters):
            ch = self._chapters[current_row]
            ch_id = ch["id"]
            lang_dir = "zh_CN" if self.current_lang.startswith("zh") else "en"
            html_path = os.path.join(self.help_mgr.help_dir, "html", lang_dir, f"{ch_id}.html")
            if not os.path.exists(html_path):
                try:
                    from ..help.html_builder import HtmlBuilder
                    HtmlBuilder.compile_all(self.help_mgr.plugin_dir)
                except Exception:
                    pass

            if os.path.exists(html_path):
                QDesktopServices.openUrl(QUrl.fromLocalFile(html_path))
                return

        # Fallback to index.html
        index_path = os.path.join(self.help_mgr.help_dir, "html", "index.html")
        if os.path.exists(index_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(index_path))

    @classmethod
    def show_help(cls, parent=None, section_id: str = "overview", lang: Optional[str] = None):
        """Global launcher method with singleton reuse."""
        if cls._instance is None or not cls._instance.isVisible():
            cls._instance = HelpDialog(parent=parent, initial_section=section_id, lang=lang)
            cls._instance.show()
        else:
            cls._instance.navigate_to_chapter(section_id)
            cls._instance.raise_()
            cls._instance.activateWindow()
        return cls._instance
