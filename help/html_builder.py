# -*- coding: utf-8 -*-
"""
QField LAN Drop - Zero-dependency Markdown to HTML Site Generator
Compiles Markdown chapters into standalone, beautifully-styled HTML files
that can be opened locally in Chrome, Edge, Safari or inside QGIS QTextBrowser.
"""

import html
import os
import re
from typing import Dict, List, Optional


class HtmlBuilder:
    """Compiles Markdown docs and TOC into standalone HTML pages."""

    @classmethod
    def markdown_to_html(cls, md_text: str) -> str:
        """Converts Markdown text to clean HTML without external dependencies."""
        lines = md_text.splitlines()
        html_lines = []
        in_code_block = False
        code_block_lines = []
        code_lang = ""
        in_table = False
        table_rows = []
        in_list = False
        list_type = "ul"

        def _format_inline(text: str) -> str:
            # Inline code: `code`
            text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
            # Bold: **bold**
            text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
            # Italic: *italic*
            text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
            # Images: ![alt](url)
            text = re.sub(r"!\[(.*?)\]\((.*?)\)", r'<img src="\2" alt="\1" class="doc-img" />', text)
            # Internal Chapter Links: [text](chapter:id) -> [text](id.html)
            text = re.sub(r"\[(.*?)\]\(chapter:([a-zA-Z0-9_-]+)\)", r'<a href="\2.html" class="chapter-link">\1</a>', text)
            # External Links: [text](url)
            text = re.sub(r"\[(.*?)\]\((.*?)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
            return text

        def _flush_list():
            nonlocal in_list, list_type
            if in_list:
                html_lines.append(f"</{list_type}>")
                in_list = False

        def _flush_table():
            nonlocal in_table, table_rows
            if in_table and table_rows:
                html_lines.append('<div class="table-container"><table>')
                # Header row
                if len(table_rows) >= 1:
                    html_lines.append("<thead><tr>")
                    for cell in table_rows[0]:
                        html_lines.append(f"<th>{_format_inline(cell)}</th>")
                    html_lines.append("</tr></thead>")
                # Body rows
                if len(table_rows) >= 2:
                    html_lines.append("<tbody>")
                    # Row 1 is divider (|:---|), so skip if it matches
                    start_idx = 1
                    if len(table_rows) > 1 and all(set(c.strip()).issubset({'-', ':', '|', ' '}) for c in table_rows[1]):
                        start_idx = 2
                    for r in table_rows[start_idx:]:
                        html_lines.append("<tr>")
                        for cell in r:
                            html_lines.append(f"<td>{_format_inline(cell)}</td>")
                        html_lines.append("</tr>")
                    html_lines.append("</tbody>")
                html_lines.append("</table></div>")
                in_table = False
                table_rows = []

        for line in lines:
            stripped = line.strip()

            # 1. Code blocks ```
            if stripped.startswith("```"):
                if in_code_block:
                    in_code_block = False
                    code_content = html.escape("\n".join(code_block_lines))
                    html_lines.append(f'<pre><code class="language-{code_lang}">{code_content}</code></pre>')
                    code_block_lines = []
                    code_lang = ""
                else:
                    _flush_list()
                    _flush_table()
                    in_code_block = True
                    code_lang = stripped[3:].strip()
                continue

            if in_code_block:
                code_block_lines.append(line)
                continue

            # 2. Tables (| col | col |)
            if stripped.startswith("|") and stripped.endswith("|"):
                _flush_list()
                in_table = True
                cells = [c.strip() for c in stripped.strip("|").split("|")]
                table_rows.append(cells)
                continue
            else:
                _flush_table()

            # 3. Horizontal Rule ---
            if stripped in ("---", "***", "___"):
                _flush_list()
                html_lines.append("<hr />")
                continue

            # 4. Headings #, ##, ###
            if stripped.startswith("#"):
                _flush_list()
                m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
                if m:
                    level = len(m.group(1))
                    text = _format_inline(m.group(2))
                    html_lines.append(f"<h{level}>{text}</h{level}>")
                    continue

            # 5. Blockquotes & Alerts (> [!NOTE], > [!TIP], > [!WARNING])
            if stripped.startswith(">"):
                _flush_list()
                quote_text = stripped[1:].strip()
                callout_class = "blockquote-info"
                if quote_text.startswith("[!NOTE]"):
                    callout_class = "blockquote-note"
                    quote_text = quote_text[7:].strip()
                elif quote_text.startswith("[!TIP]"):
                    callout_class = "blockquote-tip"
                    quote_text = quote_text[6:].strip()
                elif quote_text.startswith("[!WARNING]"):
                    callout_class = "blockquote-warning"
                    quote_text = quote_text[10:].strip()

                formatted_quote = _format_inline(quote_text)
                html_lines.append(f'<blockquote class="{callout_class}"><p>{formatted_quote}</p></blockquote>')
                continue

            # 6. Unordered Lists (*, -)
            if re.match(r"^[\*\-]\s+(.*)$", stripped):
                item_text = re.sub(r"^[\*\-]\s+", "", stripped)
                if not in_list or list_type != "ul":
                    _flush_list()
                    in_list = True
                    list_type = "ul"
                    html_lines.append("<ul>")
                html_lines.append(f"<li>{_format_inline(item_text)}</li>")
                continue

            # 7. Ordered Lists (1., 2.)
            m_num = re.match(r"^\d+\.\s+(.*)$", stripped)
            if m_num:
                item_text = m_num.group(1)
                if not in_list or list_type != "ol":
                    _flush_list()
                    in_list = True
                    list_type = "ol"
                    html_lines.append("<ol>")
                html_lines.append(f"<li>{_format_inline(item_text)}</li>")
                continue

            # 8. Empty line
            if stripped == "":
                _flush_list()
                continue

            # 8.5 Direct HTML pass-through
            if stripped.startswith("<") and (stripped.endswith(">") or "</" in stripped or "/>" in stripped):
                _flush_list()
                html_lines.append(stripped)
                continue

            # 9. Paragraph
            _flush_list()
            html_lines.append(f"<p>{_format_inline(stripped)}</p>")

        _flush_list()
        _flush_table()

        return "\n".join(html_lines)

    @classmethod
    def build_standalone_page(
        cls,
        title: str,
        body_html: str,
        chapters: List[Dict[str, str]],
        current_ch_id: str,
        lang: str = "zh_CN",
        asset_prefix: str = "../assets"
    ) -> str:
        """Wraps chapter HTML in a modern full-featured documentation website shell."""
        is_zh = lang.startswith("zh")

        # Sidebar navigation items
        sidebar_items = []
        curr_index = 0
        for idx, ch in enumerate(chapters):
            ch_id = ch["id"]
            ch_title = ch["title"]
            ch_file = f"{ch_id}.html"
            active_cls = " active" if ch_id == current_ch_id else ""
            if ch_id == current_ch_id:
                curr_index = idx
            sidebar_items.append(
                f'<a href="{ch_file}" class="nav-item{active_cls}">'
                f'<span class="nav-icon">📖</span><span class="nav-label">{html.escape(ch_title)}</span>'
                f'</a>'
            )
        sidebar_html = "\n".join(sidebar_items)

        # Prev / Next navigation
        prev_link = ""
        next_link = ""
        if curr_index > 0:
            prev_ch = chapters[curr_index - 1]
            prev_text = "◀ 上一章: " + prev_ch["title"] if is_zh else "◀ Prev: " + prev_ch["title"]
            prev_link = f'<a href="{prev_ch["id"]}.html" class="pager-btn prev">{html.escape(prev_text)}</a>'
        if curr_index < len(chapters) - 1:
            next_ch = chapters[curr_index + 1]
            next_text = next_ch["title"] + " ▶" if is_zh else next_ch["title"] + " ▶"
            next_link = f'<a href="{next_ch["id"]}.html" class="pager-btn next">{html.escape(next_text)}</a>'

        if is_zh:
            lang_bar_html = f"""<div class="lang-segmented">
        <span class="lang-tab active">🇨🇳 简体中文</span>
        <a href="../en/{current_ch_id}.html" class="lang-tab link">🌐 English</a>
      </div>"""
        else:
            lang_bar_html = f"""<div class="lang-segmented">
        <span class="lang-tab active">🌐 English</span>
        <a href="../zh_CN/{current_ch_id}.html" class="lang-tab link">🇨🇳 简体中文</a>
      </div>"""

        return f"""<!DOCTYPE html>
<html lang="{'zh-CN' if is_zh else 'en'}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(title)} - QField LAN Drop</title>
  <style>
    :root {{
      --primary: #2563EB;
      --primary-hover: #1D4ED8;
      --qgis-green: #589632;
      --bg-main: #FFFFFF;
      --bg-sidebar: #F8FAFC;
      --border-color: #E2E8F0;
      --text-main: #1E293B;
      --text-muted: #64748B;
      --code-bg: #F1F5F9;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
      color: var(--text-main);
      background: var(--bg-main);
      display: flex;
      min-height: 100vh;
      line-height: 1.65;
    }}
    /* Sidebar */
    .sidebar {{
      width: 280px;
      background: var(--bg-sidebar);
      border-right: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;
      position: fixed;
      top: 0;
      bottom: 0;
      left: 0;
      overflow-y: auto;
      z-index: 10;
    }}
    .sidebar-header {{
      padding: 18px 16px;
      border-bottom: 1px solid var(--border-color);
      font-weight: bold;
      font-size: 15px;
      color: #0F172A;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .sidebar-nav {{
      padding: 10px 8px;
      display: flex;
      flex-direction: column;
      gap: 3px;
      flex: 1;
    }}
    .nav-item {{
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 9px 12px;
      color: var(--text-main);
      text-decoration: none;
      border-radius: 6px;
      font-size: 13.5px;
      transition: background 0.15s;
    }}
    .nav-item:hover {{ background: #E2E8F0; }}
    .nav-item.active {{
      background: var(--primary);
      color: #FFFFFF;
      font-weight: 600;
    }}
    /* Main Content */
    .content-wrapper {{
      margin-left: 280px;
      flex: 1;
      display: flex;
      flex-direction: column;
      max-width: 960px;
      padding: 32px 48px;
    }}
    .top-toolbar {{
      display: flex;
      justify-content: flex-end;
      align-items: center;
      margin-bottom: 24px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border-color);
    }}
    .lang-segmented {{
      display: inline-flex;
      align-items: center;
      background: #F1F5F9;
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 3px;
      gap: 3px;
    }}
    .lang-tab {{
      font-size: 12.5px;
      padding: 4px 12px;
      border-radius: 4px;
      text-decoration: none;
      display: inline-block;
    }}
    .lang-tab.active {{
      background: #FFFFFF;
      color: var(--primary);
      font-weight: bold;
      box-shadow: 0 1px 2px rgba(0,0,0,0.06);
    }}
    .lang-tab.link {{
      color: var(--text-muted);
      transition: all 0.15s;
    }}
    .lang-tab.link:hover {{
      color: var(--text-main);
      background: #E2E8F0;
    }}
    /* Typography */
    h1 {{ font-size: 26px; font-weight: 700; margin-bottom: 18px; color: #0F172A; border-bottom: 2px solid var(--border-color); padding-bottom: 10px; }}
    h2 {{ font-size: 19px; font-weight: 600; margin-top: 32px; margin-bottom: 14px; color: #0F172A; border-bottom: 1px solid #F1F5F9; padding-bottom: 6px; }}
    h3 {{ font-size: 16px; font-weight: 600; margin-top: 24px; margin-bottom: 10px; color: #334155; }}
    p {{ margin-bottom: 14px; font-size: 14.5px; color: #334155; }}
    ul, ol {{ margin-left: 24px; margin-bottom: 16px; font-size: 14.5px; }}
    li {{ margin-bottom: 6px; }}
    hr {{ border: 0; border-top: 1px solid var(--border-color); margin: 28px 0; }}
    /* Callouts */
    blockquote {{
      margin: 18px 0;
      padding: 12px 16px;
      border-left: 4px solid var(--primary);
      background: #EFF6FF;
      border-radius: 0 8px 8px 0;
      font-size: 14px;
    }}
    blockquote.blockquote-tip {{ border-left-color: #10B981; background: #ECFDF5; color: #065F46; }}
    blockquote.blockquote-warning {{ border-left-color: #F59E0B; background: #FEF3C7; color: #92400E; }}
    /* Code */
    code {{ font-family: "JetBrains Mono", Consolas, monospace; background: var(--code-bg); color: #BE185D; padding: 2px 6px; border-radius: 4px; font-size: 13px; }}
    pre {{ background: #0F172A; color: #F8FAFC; padding: 14px 18px; border-radius: 8px; overflow-x: auto; margin: 16px 0; }}
    pre code {{ background: transparent; color: inherit; padding: 0; }}
    /* Tables */
    .table-container {{ overflow-x: auto; margin: 20px 0; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border: 1px solid var(--border-color); padding: 10px 14px; text-align: left; }}
    th {{ background: #F8FAFC; font-weight: 600; }}
    tr:nth-child(even) {{ background: #FBFCFD; }}
    /* Images */
    .doc-img {{ max-width: 100%; height: auto; display: block; margin: 20px auto; border-radius: 8px; }}
    /* Pager */
    .pager {{ display: flex; justify-content: space-between; margin-top: 48px; padding-top: 20px; border-top: 1px solid var(--border-color); }}
    .pager-btn {{ text-decoration: none; padding: 8px 16px; border: 1px solid var(--border-color); border-radius: 6px; font-size: 13.5px; color: var(--text-main); font-weight: 500; transition: all 0.15s; }}
    .pager-btn:hover {{ border-color: var(--primary); color: var(--primary); }}
    @media (max-width: 768px) {{
      .sidebar {{ display: none; }}
      .content-wrapper {{ margin-left: 0; padding: 20px; }}
    }}
  </style>
</head>
<body>
  <aside class="sidebar">
    <div class="sidebar-header">
      <span>🚀</span>
      <span>QField LAN Drop</span>
    </div>
    <nav class="sidebar-nav">
      {sidebar_html}
    </nav>
  </aside>
  <main class="content-wrapper">
    <div class="top-toolbar">
      {lang_bar_html}
    </div>
    <article class="doc-body">
      {body_html}
    </article>
    <div class="pager">
      <div>{prev_link}</div>
      <div>{next_link}</div>
    </div>
  </main>
</body>
</html>"""

    @classmethod
    def compile_all(cls, plugin_dir: str):
        """Compiles all markdown chapters into html/zh_CN/ and html/en/."""
        from .help_manager import HelpManager

        mgr = HelpManager(plugin_dir)
        html_base = os.path.join(mgr.help_dir, "html")
        os.makedirs(html_base, exist_ok=True)

        for lang in ("zh_CN", "en"):
            lang_dir = os.path.join(html_base, lang)
            os.makedirs(lang_dir, exist_ok=True)
            chapters = mgr.get_chapters(lang=lang)

            for ch in chapters:
                ch_id = ch["id"]
                raw_md = mgr.load_chapter_markdown(ch_id, lang=lang)

                # Fix image paths for HTML: convert absolute SVG paths or diagram links
                # to relative path ../../assets/diagrams/...
                diagram_rel = f"../../assets/diagrams/{ch_id}_{'zh' if lang.startswith('zh') else 'en'}.svg"

                def _fix_img(match):
                    alt = match.group(1)
                    src = match.group(2)
                    filename = os.path.basename(src)
                    return f"![{alt}](../../assets/diagrams/{filename})"

                clean_md = re.sub(r"!\[(.*?)\]\((.*?\.svg)\)", _fix_img, raw_md)

                body_html = cls.markdown_to_html(clean_md)
                page_html = cls.build_standalone_page(
                    title=ch["title"],
                    body_html=body_html,
                    chapters=chapters,
                    current_ch_id=ch_id,
                    lang=lang,
                    asset_prefix="../../assets"
                )

                out_path = os.path.join(lang_dir, f"{ch_id}.html")
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(page_html)

        # Generate index.html redirector
        index_html = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>QField LAN Drop Docs</title>
  <script>
    var lang = (navigator.language || navigator.userLanguage || '').toLowerCase();
    if (lang.indexOf('zh') !== -1) {
      window.location.replace('zh_CN/overview.html');
    } else {
      window.location.replace('en/overview.html');
    }
  </script>
</head>
<body>
  <p>Redirecting to <a href="zh_CN/overview.html">Chinese Docs</a> or <a href="en/overview.html">English Docs</a>...</p>
</body>
</html>"""
        with open(os.path.join(html_base, "index.html"), "w", encoding="utf-8") as f:
            f.write(index_html)
