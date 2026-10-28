# -*- coding: utf-8 -*-
"""
QField LAN Drop - Icon Component Canvas Builder
Scans all individual *.svg files in icons/ and rebuilds 0_icons_Component.svg
following the Inkscape multi-page standard.
"""

import os
import re
import xml.etree.ElementTree as ET

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR = os.path.join(PLUGIN_DIR, "icons")
OUT_SVG = os.path.join(ICONS_DIR, "0_icons_Component.svg")


def build_component_svg():
    if not os.path.exists(ICONS_DIR):
        print(f"Error: Directory not found: {ICONS_DIR}")
        return

    all_svgs = sorted([
        f for f in os.listdir(ICONS_DIR)
        if f.endswith(".svg") and f != "0_icons_Component.svg"
    ])

    # Separate small icons (usually 24x24) and large icons (e.g. 64x64)
    small_icons = []
    big_icons = []

    for name in all_svgs:
        stem = os.path.splitext(name)[0]
        fpath = os.path.join(ICONS_DIR, name)
        try:
            tree = ET.parse(fpath)
            root = tree.getroot()
            vb = root.attrib.get("viewBox", "0 0 24 24").split()
            w = float(vb[2]) if len(vb) == 4 else 24
            if w <= 32:
                small_icons.append((stem, fpath, root))
            else:
                big_icons.append((stem, fpath, root))
        except Exception:
            small_icons.append((stem, fpath, None))

    pages_xml = []
    groups_xml = []
    defs_xml = []

    # 1. Layout small icons (step = width + 10px = 34px)
    x_offset = 0
    step_small = 34

    for stem, fpath, root in small_icons:
        with open(fpath, "r", encoding="utf-8") as fp:
            text = fp.read()

        stroke = root.attrib.get('stroke', '#000000') if root is not None else '#000000'
        stroke_width = root.attrib.get('stroke-width', '2') if root is not None else '2'
        stroke_linecap = root.attrib.get('stroke-linecap', 'square') if root is not None else 'square'
        stroke_linejoin = root.attrib.get('stroke-linejoin', 'miter') if root is not None else 'miter'
        fill = root.attrib.get('fill', 'none') if root is not None else 'none'

        inner_lines = []
        for line in text.strip().splitlines():
            s = line.strip()
            if s.startswith('<svg') or s.startswith('</svg>') or s.startswith('<?xml'):
                continue
            inner_lines.append('      ' + s)
        inner_str = '\n'.join(inner_lines)

        pages_xml.append(f"""    <inkscape:page
       x="{x_offset}"
       y="0"
       width="24"
       height="24"
       id="page_{stem}"
       margin="0"
       bleed="0"
       inkscape:label="{stem}" />""")

        groups_xml.append(f"""    <!-- Page: {stem} (x={x_offset}) -->
    <g
       id="g_{stem}"
       inkscape:label="{stem}"
       transform="translate({x_offset}, 0)"
       fill="{fill}"
       stroke="{stroke}"
       stroke-width="{stroke_width}"
       stroke-linecap="{stroke_linecap}"
       stroke-linejoin="{stroke_linejoin}">
{inner_str}
    </g>""")
        x_offset += step_small

    # 2. Layout big icons (e.g. 64x64, step = 64 + 16 = 80px)
    if big_icons:
        x_offset = max(x_offset + 10, 622)
        step_big = 80

        # Custom gradient & filter defs for big icons
        defs_xml.append("""    <!-- Big icon gradients & filters -->
    <linearGradient id="mobile_grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#7C3AED;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#4F46E5;stop-opacity:1" />
    </linearGradient>
    <filter id="shadow_m" x="-10%" y="-10%" width="130%" height="130%">
      <feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#0F172A" flood-opacity="0.25" />
    </filter>
    <linearGradient id="receive_bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#059669;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#0D9488;stop-opacity:1" />
    </linearGradient>
    <filter id="shadow_receive" x="-10%" y="-10%" width="130%" height="130%">
      <feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#0F172A" flood-opacity="0.25" />
    </filter>
    <linearGradient id="send_bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0284C7;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#2563EB;stop-opacity:1" />
    </linearGradient>
    <filter id="shadow_send" x="-10%" y="-10%" width="130%" height="130%">
      <feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#0F172A" flood-opacity="0.25" />
    </filter>""")

        for stem, fpath, root in big_icons:
            pages_xml.append(f"""    <inkscape:page
       x="{x_offset}"
       y="0"
       width="64"
       height="64"
       id="page_{stem}"
       margin="0"
       bleed="0"
       inkscape:label="{stem}" />""")

            with open(fpath, "r", encoding="utf-8") as fp:
                text = fp.read()

            inner_lines = []
            in_defs = False
            for line in text.strip().splitlines():
                s = line.strip()
                if s.startswith('<svg') or s.startswith('</svg>') or s.startswith('<?xml'):
                    continue
                if '<defs>' in s:
                    in_defs = True
                    continue
                if '</defs>' in s:
                    in_defs = False
                    continue
                if in_defs:
                    continue
                if stem == 'icon_receive':
                    s = s.replace('url(#shadow)', 'url(#shadow_receive)')
                elif stem == 'icon_send':
                    s = s.replace('url(#shadow)', 'url(#shadow_send)')
                inner_lines.append('      ' + s)

            inner_str = '\n'.join(inner_lines)
            groups_xml.append(f"""    <!-- Page: {stem} (x={x_offset}) -->
    <g
       id="g_{stem}"
       inkscape:label="{stem}"
       transform="translate({x_offset}, 0)">
{inner_str}
    </g>""")
            x_offset += step_big

    pages_joined = "\n".join(pages_xml)
    defs_joined = "\n".join(defs_xml)
    groups_joined = "\n".join(groups_xml)

    full_svg = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!-- Created with Inkscape (http://www.inkscape.org/) -->

<svg
   width="24"
   height="24"
   viewBox="0 0 24 24"
   version="1.1"
   id="svg1"
   inkscape:version="1.4.4 (dcaf3e7, 2026-05-05)"
   sodipodi:docname="0_icons_Component.svg"
   inkscape:export-batch-name=""
   inkscape:export-batch-path="{ICONS_DIR}"
   xml:space="preserve"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns:xlink="http://www.w3.org/1999/xlink"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="true"
     inkscape:deskcolor="#d1d1d1"
     inkscape:document-units="px"
     inkscape:zoom="4"
     inkscape:cx="400"
     inkscape:cy="16"
     inkscape:window-width="1920"
     inkscape:window-height="1001"
     inkscape:window-x="-9"
     inkscape:window-y="41"
     inkscape:window-maximized="1"
     inkscape:current-layer="layer1">
{pages_joined}
  </sodipodi:namedview>
  <defs
     id="defs1">
{defs_joined}
  </defs>
  <g
     inkscape:label="Icons"
     inkscape:groupmode="layer"
     id="layer1">
{groups_joined}
  </g>
</svg>
"""
    with open(OUT_SVG, "w", encoding="utf-8") as fp:
        fp.write(full_svg)

    print(f"Build complete: generated {OUT_SVG} with {len(pages_xml)} icon pages!")


if __name__ == "__main__":
    build_component_svg()
