#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LiveCanvas Deterministic OpenXML (PresentationML) to Graph AST Compiler
Requires: pip install python-pptx lxml
Usage:    python src/python/main.py [input_deck.pptx output_ast.json]
"""

import sys
import json
import math
import base64
import colorsys
from pathlib import Path
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from lxml import etree

# OpenXML Namespace Dictionary
NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}

EMU_PER_PX = 9525.0  # 914,400 EMU/inch / 96 CSS px/inch


def emu_to_px(val) -> float:
    if val is None:
        return 0.0
    return round(float(val) / EMU_PER_PX, 2)


def rot_to_deg(val) -> float:
    if val is None:
        return 0.0
    return round(float(val) / 60000.0, 2)


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    hex_str = hex_str.lstrip("#")
    return tuple(int(hex_str[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: float, g: float, b: float) -> str:
    return "#{:02X}{:02X}{:02X}".format(
        max(0, min(255, int(round(r)))),
        max(0, min(255, int(round(g)))),
        max(0, min(255, int(round(b)))),
    )


class ThemeAndCascadeResolver:
    """ppt/theme/theme1.xml ve slideMaster clrMap verilerini çözerek gerçek HEX/RGBA üretir."""

    def __init__(self, prs: Presentation):
        self.theme_colors = {
            "dk1": "000000",
            "lt1": "FFFFFF",
            "dk2": "1F497D",
            "lt2": "EEECE1",
            "accent1": "4F81BD",
            "accent2": "C0504D",
            "accent3": "9BBB59",
            "accent4": "8064A2",
            "accent5": "4BACC6",
            "accent6": "F79646",
            "hlink": "0000FF",
            "folHlink": "800080",
        }
        self.color_map = {
            "bg1": "lt1",
            "tx1": "dk1",
            "bg2": "lt2",
            "tx2": "dk2",
            "accent1": "accent1",
            "accent2": "accent2",
            "accent3": "accent3",
            "accent4": "accent4",
            "accent5": "accent5",
            "accent6": "accent6",
            "hlink": "hlink",
            "folHlink": "folHlink",
        }
        self.major_font = "Calibri"
        self.minor_font = "Calibri"
        self.bg_fill_styles: list[str] = []
        self._parse_master_and_theme(prs)

    def _parse_master_and_theme(self, prs: Presentation):
        try:
            master = prs.slide_master
            master_elem = master.element

            # 1. Color Map (clrMap) çözümlemesi
            clr_map_elem = master_elem.find("p:clrMap", NS)
            if clr_map_elem is not None:
                for k, v in clr_map_elem.attrib.items():
                    self.color_map[k] = v

            # 2. Theme XML part'ına erişim
            for rel in master.part.rels.values():
                if "theme" in rel.reltype:
                    theme_xml = etree.fromstring(rel.target_part.blob)
                    clr_scheme = theme_xml.find(".//a:clrScheme", NS)
                    if clr_scheme is not None:
                        for slot in self.theme_colors.keys():
                            slot_elem = clr_scheme.find(f"a:{slot}", NS)
                            if slot_elem is not None:
                                srgb = slot_elem.find("a:srgbClr", NS)
                                sys_clr = slot_elem.find("a:sysClr", NS)
                                if srgb is not None and "val" in srgb.attrib:
                                    self.theme_colors[slot] = srgb.get("val")
                                elif sys_clr is not None and "lastClr" in sys_clr.attrib:
                                    self.theme_colors[slot] = sys_clr.get("lastClr")

                    font_scheme = theme_xml.find(".//a:fontScheme", NS)
                    if font_scheme is not None:
                        mj_latin = font_scheme.find("a:majorFont/a:latin", NS)
                        mn_latin = font_scheme.find("a:minorFont/a:latin", NS)
                        if mj_latin is not None and mj_latin.get("typeface"):
                            self.major_font = mj_latin.get("typeface")
                        if mn_latin is not None and mn_latin.get("typeface"):
                            self.minor_font = mn_latin.get("typeface")

                    bg_fill_lst = theme_xml.find(".//a:fmtScheme/a:bgFillStyleLst", NS)
                    if bg_fill_lst is not None:
                        for fill_elem in bg_fill_lst:
                            tag = etree.QName(fill_elem).localname
                            if tag == "solidFill":
                                clr = self.resolve_color_element(fill_elem)
                                self.bg_fill_styles.append(clr or "#FFFFFF")
                            elif tag == "gradFill":
                                stops = fill_elem.findall("a:gsLst/a:gs", NS)
                                if stops:
                                    first_clr = self.resolve_color_element(stops[0]) or "#FFFFFF"
                                    last_clr = self.resolve_color_element(stops[-1]) or first_clr
                                    self.bg_fill_styles.append(f"linear-gradient(135deg, {first_clr}, {last_clr})")
                                else:
                                    self.bg_fill_styles.append("#FFFFFF")
                            else:
                                self.bg_fill_styles.append("#FFFFFF")
                    break
        except Exception:
            pass

    def resolve_bg_ref(self, bg_ref) -> str | None:
        if bg_ref is None:
            return None
        idx_str = bg_ref.get("idx", "0")
        try:
            idx = int(idx_str)
        except ValueError:
            idx = 0
        if idx >= 1001:
            style_idx = idx - 1001
            if 0 <= style_idx < len(self.bg_fill_styles):
                return self.bg_fill_styles[style_idx]
        return self.resolve_color_element(bg_ref)

    def resolve_font_family(self, typeface: str | None) -> str:
        if not typeface:
            return self.minor_font
        if typeface.startswith("+mj"):
            return self.major_font
        if typeface.startswith("+mn"):
            return self.minor_font
        return typeface

    def resolve_color_element(self, parent_elem) -> str | None:
        """<a:solidFill>, <a:ln>, <a:rPr> veya <a:fillRef> içindeki rengi ve modifikasyonları çözer."""
        if parent_elem is None:
            return None

        srgb = parent_elem.find("a:srgbClr", NS)
        scheme = parent_elem.find("a:schemeClr", NS)
        sys_clr = parent_elem.find("a:sysClr", NS)
        prst_clr = parent_elem.find("a:prstClr", NS)

        color_node = None
        base_hex = None

        if srgb is not None:
            color_node = srgb
            base_hex = srgb.get("val", "000000")
        elif scheme is not None:
            color_node = scheme
            scheme_val = scheme.get("val", "dk1")
            mapped_key = self.color_map.get(scheme_val, scheme_val)
            base_hex = self.theme_colors.get(mapped_key, "000000")
        elif sys_clr is not None:
            color_node = sys_clr
            base_hex = sys_clr.get("lastClr", "000000")
        elif prst_clr is not None:
            color_node = prst_clr
            prst_map = {
                "black": "000000", "white": "FFFFFF", "red": "FF0000",
                "green": "00FF00", "blue": "0000FF", "yellow": "FFFF00",
                "gray": "808080", "ltGray": "D3D3D3", "dkGray": "A9A9A9"
            }
            base_hex = prst_map.get(prst_clr.get("val", ""), "000000")

        if not base_hex or color_node is None:
            return None

        return self._apply_color_transforms(base_hex, color_node)

    def _apply_color_transforms(self, base_hex: str, color_node) -> str:
        r, g, b = hex_to_rgb(base_hex)
        # RGB [0..1]
        rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
        h, l, s = colorsys.rgb_to_hls(rf, gf, bf)

        for child in color_node:
            tag = etree.QName(child).localname
            val = float(child.get("val", "100000")) / 100000.0

            if tag == "lumMod":
                l = l * val
            elif tag == "lumOff":
                l = l + val
            elif tag == "satMod":
                s = s * val
            elif tag == "satOff":
                s = s + val

        l = max(0.0, min(1.0, l))
        s = max(0.0, min(1.0, s))
        rf, gf, bf = colorsys.hls_to_rgb(h, l, s)
        r_out, g_out, b_out = rf * 255.0, gf * 255.0, bf * 255.0

        for child in color_node:
            tag = etree.QName(child).localname
            val = float(child.get("val", "100000")) / 100000.0
            if tag == "tint":
                r_out = r_out + (255.0 - r_out) * val
                g_out = g_out + (255.0 - g_out) * val
                b_out = b_out + (255.0 - b_out) * val
            elif tag == "shade":
                r_out = r_out * val
                g_out = g_out * val
                b_out = b_out * val

        alpha_elem = color_node.find("a:alpha", NS)
        if alpha_elem is not None:
            alpha = round(float(alpha_elem.get("val", "100000")) / 100000.0, 3)
            return f"rgba({int(round(r_out))}, {int(round(g_out))}, {int(round(b_out))}, {alpha})"

        return rgb_to_hex(r_out, g_out, b_out)


class PresentationMLCompiler:
    def __init__(self, pptx_path: str):
        self.prs = Presentation(pptx_path)
        self.theme = ThemeAndCascadeResolver(self.prs)
        self.slide_width = emu_to_px(self.prs.slide_width)
        self.slide_height = emu_to_px(self.prs.slide_height)
        self._virtual_anchor_counter = 100000

    def compile(self) -> dict:
        deck_ast = {
            "version": "1.0.0",
            "presentation": {
                "slideWidth": self.slide_width,
                "slideHeight": self.slide_height,
                "unit": "px",
                "defaultFonts": {
                    "major": self.theme.major_font,
                    "minor": self.theme.minor_font,
                },
            },
            "slides": [],
        }

        for idx, slide in enumerate(self.prs.slides):
            deck_ast["slides"].append(self._compile_slide(slide, idx + 1))

        return deck_ast

    def _compile_slide(self, slide, slide_num: int) -> dict:
        nodes = []
        edges = []
        z_counter = [1]

        bg_color = self._extract_slide_background(slide)

        for shape in slide.shapes:
            self._process_shape(shape, slide, nodes, edges, 0.0, 0.0, 1.0, 1.0, z_counter)

        return {
            "slideNumber": slide_num,
            "id": f"slide-{slide_num}",
            "background": {"color": bg_color},
            "nodes": nodes,
            "edges": edges,
        }

    def _extract_slide_background(self, slide) -> str:
        # Slide -> SlideLayout -> SlideMaster sırasıyla arka plan rengini arar
        for container in [slide, slide.slide_layout, slide.slide_layout.slide_master]:
            if container is None:
                continue
            bg_pr = container.element.find(".//p:bg/p:bgPr", NS)
            if bg_pr is not None:
                solid = bg_pr.find("a:solidFill", NS)
                if solid is not None:
                    clr = self.theme.resolve_color_element(solid)
                    if clr:
                        return clr
                grad = bg_pr.find("a:gradFill", NS)
                if grad is not None:
                    stops = grad.findall("a:gsLst/a:gs", NS)
                    if stops:
                        first_clr = self.theme.resolve_color_element(stops[0]) or "#FFFFFF"
                        last_clr = self.theme.resolve_color_element(stops[-1]) or first_clr
                        return f"linear-gradient(135deg, {first_clr}, {last_clr})"
            bg_ref = container.element.find(".//p:bg/p:bgRef", NS)
            if bg_ref is not None:
                clr = self.theme.resolve_bg_ref(bg_ref)
                if clr:
                    return clr

        # Full-bleed arka plan şekli kontrolü (örn. (0,0) konumunda tüm slaytı kaplayan şekil)
        if len(slide.shapes) > 0:
            first_sp = slide.shapes[0]
            try:
                xfrm = first_sp.element.find(".//p:spPr/a:xfrm", NS)
                if xfrm is not None:
                    off = xfrm.find("a:off", NS)
                    ext = xfrm.find("a:ext", NS)
                    if off is not None and ext is not None:
                        x = int(off.get("x", 0))
                        y = int(off.get("y", 0))
                        w = int(ext.get("cx", 0))
                        h = int(ext.get("cy", 0))
                        slide_w_emu = int(self.prs.slide_width)
                        slide_h_emu = int(self.prs.slide_height)
                        if x == 0 and y == 0 and w >= int(slide_w_emu * 0.95) and h >= int(slide_h_emu * 0.95):
                            sp_pr = first_sp.element.find("p:spPr", NS)
                            if sp_pr is not None:
                                solid = sp_pr.find("a:solidFill", NS)
                                if solid is not None:
                                    clr = self.theme.resolve_color_element(solid)
                                    if clr:
                                        return clr
                                grad = sp_pr.find("a:gradFill", NS)
                                if grad is not None:
                                    stops = grad.findall("a:gsLst/a:gs", NS)
                                    if stops:
                                        first_clr = self.theme.resolve_color_element(stops[0]) or "#FFFFFF"
                                        last_clr = self.theme.resolve_color_element(stops[-1]) or first_clr
                                        return f"linear-gradient(135deg, {first_clr}, {last_clr})"
            except Exception:
                pass

        return "#" + self.theme.theme_colors.get("lt1", "FFFFFF")

    def _process_shape(self, shape, slide, nodes: list, edges: list,
                       parent_x: float, parent_y: float, scale_x: float, scale_y: float,
                       z_counter: list):
        local_tag = etree.QName(shape.element).localname

        # 1. Grup Şekli (<p:grpSp>)
        if local_tag == "grpSp" or shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            self._compile_group(shape, slide, nodes, edges, parent_x, parent_y, scale_x, scale_y, z_counter)
            return

        # 2. Bağlantı Oku / Çizgisi (<p:cxnSp>)
        if local_tag == "cxnSp":
            self._compile_connector(shape, nodes, edges, parent_x, parent_y, scale_x, scale_y, z_counter)
            return

        # 3. Tablo (<p:graphicFrame> içinde <a:tbl>)
        if getattr(shape, "has_table", False):
            tbl_node = self._compile_table(shape, slide, parent_x, parent_y, scale_x, scale_y, z_counter[0])
            z_counter[0] += 1
            if tbl_node:
                nodes.append(tbl_node)
            return

        # 4. Resim (<p:pic>)
        if local_tag == "pic" or shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
            pic_node = self._compile_picture(shape, slide, parent_x, parent_y, scale_x, scale_y, z_counter[0])
            z_counter[0] += 1
            if pic_node:
                nodes.append(pic_node)
            return

        # 5. Standart Şekil / Metin Kutusu (<p:sp>)
        node = self._compile_standard_shape(shape, slide, parent_x, parent_y, scale_x, scale_y, z_counter[0])
        z_counter[0] += 1
        if node:
            nodes.append(node)

    def _resolve_geometry(self, shape, slide, parent_x: float, parent_y: float, scale_x: float, scale_y: float):
        """Şeklin koordinatlarını okur; placeholder ise Layout veya Master'dan miras alır."""
        sp_elem = shape.element
        xfrm = sp_elem.find(".//p:spPr/a:xfrm", NS)
        if xfrm is None:
            xfrm = sp_elem.find(".//p:xfrm", NS)

        # Placeholder miras kontrolü
        if (xfrm is None or xfrm.find("a:off", NS) is None) and shape.is_placeholder:
            inherited_xfrm = self._find_inherited_xfrm(sp_elem, slide)
            if inherited_xfrm is not None:
                xfrm = inherited_xfrm

        off_x, off_y, ext_cx, ext_cy = None, None, None, None
        rot = 0
        flip_h = False
        flip_v = False

        if xfrm is not None:
            off = xfrm.find("a:off", NS)
            ext = xfrm.find("a:ext", NS)
            if off is not None:
                off_x = int(off.get("x", 0))
                off_y = int(off.get("y", 0))
            if ext is not None:
                ext_cx = int(ext.get("cx", 0))
                ext_cy = int(ext.get("cy", 0))
            rot = int(xfrm.get("rot", 0))
            flip_h = xfrm.get("flipH", "0") in ("1", "true")
            flip_v = xfrm.get("flipV", "0") in ("1", "true")

        # python-pptx yüksek seviye fallback
        if off_x is None and shape.left is not None:
            off_x = int(shape.left)
            off_y = int(shape.top)
            ext_cx = int(shape.width)
            ext_cy = int(shape.height)

        if off_x is None or ext_cx is None:
            return None

        raw_x = parent_x + scale_x * emu_to_px(off_x)
        raw_y = parent_y + scale_y * emu_to_px(off_y)
        raw_w = scale_x * emu_to_px(ext_cx)
        raw_h = scale_y * emu_to_px(ext_cy)

        # A flipped group is represented by a negative effective scale. Keep
        # the canvas box positive and carry the flip into the node geometry.
        if raw_w < 0:
            raw_x += raw_w
            raw_w = -raw_w
            flip_h = not flip_h
        if raw_h < 0:
            raw_y += raw_h
            raw_h = -raw_h
            flip_v = not flip_v

        return {
            "x": round(raw_x, 2),
            "y": round(raw_y, 2),
            "width": max(round(raw_w, 2), 1.0),
            "height": max(round(raw_h, 2), 1.0),
            "rotation": rot_to_deg(rot),
            "flipH": flip_h,
            "flipV": flip_v,
        }

    def _find_inherited_xfrm(self, sp_elem, slide):
        ph = sp_elem.find(".//p:nvPr/p:ph", NS)
        if ph is None:
            return None
        ph_type = ph.get("type")
        ph_idx = ph.get("idx")

        for container in [slide.slide_layout, slide.slide_layout.slide_master]:
            if container is None:
                continue
            for cand in container.element.findall(".//p:sp", NS):
                cand_ph = cand.find(".//p:nvPr/p:ph", NS)
                if cand_ph is None:
                    continue
                if (ph_idx and cand_ph.get("idx") == ph_idx) or (ph_type and cand_ph.get("type") == ph_type):
                    cand_xfrm = cand.find(".//p:spPr/a:xfrm", NS)
                    if cand_xfrm is not None and cand_xfrm.find("a:off", NS) is not None:
                        return cand_xfrm
        return None

    def _compile_standard_shape(self, shape, slide, parent_x: float, parent_y: float,
                                scale_x: float, scale_y: float, z_index: int) -> dict | None:
        geom = self._resolve_geometry(shape, slide, parent_x, parent_y, scale_x, scale_y)
        if not geom:
            return None

        sp_elem = shape.element
        sp_pr = sp_elem.find("p:spPr", NS)
        sp_style = sp_elem.find("p:style", NS)

        # Şekil Geometrisi (rect, roundRect, ellipse, diamond, arc vb.)
        prst_geom = "rect"
        corner_radius_px = 0.0
        arc_params = None
        if sp_pr is not None:
            prst_elem = sp_pr.find("a:prstGeom", NS)
            if prst_elem is not None:
                prst_geom = prst_elem.get("prst", "rect")
                if prst_geom == "roundRect":
                    gd = prst_elem.find("a:avLst/a:gd[@name='adj']", NS)
                    adj_val = 16667.0
                    if gd is not None and "fmla" in gd.attrib:
                        parts = gd.get("fmla").split()
                        if len(parts) == 2 and parts[0] == "val":
                            adj_val = float(parts[1])
                    corner_radius_px = round(min(geom["width"], geom["height"]) * (adj_val / 100000.0), 2)
                elif prst_geom == "arc":
                    adj1_val = 16200000.0
                    adj2_val = 0.0
                    gd1 = prst_elem.find("a:avLst/a:gd[@name='adj1']", NS)
                    gd2 = prst_elem.find("a:avLst/a:gd[@name='adj2']", NS)
                    if gd1 is not None and "fmla" in gd1.attrib:
                        parts = gd1.get("fmla").split()
                        if len(parts) == 2 and parts[0] == "val":
                            adj1_val = float(parts[1])
                    if gd2 is not None and "fmla" in gd2.attrib:
                        parts = gd2.get("fmla").split()
                        if len(parts) == 2 and parts[0] == "val":
                            adj2_val = float(parts[1])
                    arc_params = {
                        "startAngle": round(adj1_val / 60000.0, 2),
                        "endAngle": round(adj2_val / 60000.0, 2),
                    }

        # Arka Plan Dolgusu (Fill)
        bg_color = "transparent"
        if sp_pr is not None:
            if sp_pr.find("a:noFill", NS) is not None:
                bg_color = "transparent"
            elif sp_pr.find("a:solidFill", NS) is not None:
                resolved = self.theme.resolve_color_element(sp_pr.find("a:solidFill", NS))
                if resolved:
                    bg_color = resolved
            elif sp_pr.find("a:gradFill", NS) is not None:
                stops = sp_pr.findall("a:gradFill/a:gsLst/a:gs", NS)
                if stops:
                    first_clr = self.theme.resolve_color_element(stops[0]) or "#FFFFFF"
                    last_clr = self.theme.resolve_color_element(stops[-1]) or first_clr
                    bg_color = f"linear-gradient(135deg, {first_clr}, {last_clr})"
            elif sp_style is not None:
                fill_ref = sp_style.find("a:fillRef", NS)
                if fill_ref is not None and fill_ref.get("idx", "0") != "0":
                    resolved = self.theme.resolve_color_element(fill_ref)
                    if resolved:
                        bg_color = resolved

        # Kenarlık (Stroke / Border)
        border_color = "transparent"
        border_width = 0.0
        border_style = "solid"
        arrow_start = "none"
        arrow_end = "none"
        ln_elem = sp_pr.find("a:ln", NS) if sp_pr is not None else None

        if ln_elem is not None and ln_elem.find("a:noFill", NS) is None:
            w_emu = ln_elem.get("w")
            border_width = max(1.0, emu_to_px(w_emu)) if w_emu else 1.0
            solid_ln = ln_elem.find("a:solidFill", NS)
            if solid_ln is not None:
                border_color = self.theme.resolve_color_element(solid_ln) or "transparent"
            dash_elem = ln_elem.find("a:prstDash", NS)
            if dash_elem is not None:
                d_val = dash_elem.get("val", "solid")
                if "dot" in d_val.lower():
                    border_style = "dotted"
                elif "dash" in d_val.lower():
                    border_style = "dashed"

            head_end = ln_elem.find("a:headEnd", NS)
            tail_end = ln_elem.find("a:tailEnd", NS)
            if head_end is not None and head_end.get("type", "none") != "none":
                arrow_start = head_end.get("type")
            if tail_end is not None and tail_end.get("type", "none") != "none":
                arrow_end = tail_end.get("type")
        elif (ln_elem is None or ln_elem.find("a:noFill", NS) is None) and sp_style is not None:
            ln_ref = sp_style.find("a:lnRef", NS)
            if ln_ref is not None and ln_ref.get("idx", "0") != "0":
                resolved = self.theme.resolve_color_element(ln_ref)
                if resolved:
                    border_color = resolved
                    border_width = 1.0

        # Gölge Çıkarımı (a:outerShdw in a:effectLst)
        box_shadow = None
        if sp_pr is not None:
            outer_shdw = sp_pr.find("a:effectLst/a:outerShdw", NS)
            if outer_shdw is not None:
                blur_emu = float(outer_shdw.get("blurRad", 0))
                dist_emu = float(outer_shdw.get("dist", 0))
                dir_rot = float(outer_shdw.get("dir", 0))
                blur_px = emu_to_px(blur_emu)
                dist_px = emu_to_px(dist_emu)
                dir_deg = rot_to_deg(dir_rot)
                dx = round(dist_px * math.cos(math.radians(dir_deg)), 2)
                dy = round(dist_px * math.sin(math.radians(dir_deg)), 2)
                clr = self.theme.resolve_color_element(outer_shdw) or "rgba(0, 0, 0, 0.35)"
                box_shadow = f"{dx}px {dy}px {blur_px}px {clr}"

        # Text Body & Padding (Insets)
        padding = {"top": 4.8, "right": 9.6, "bottom": 4.8, "left": 9.6}
        vertical_align = "top"
        word_wrap = True
        paragraphs = []

        tx_body = sp_elem.find("p:txBody", NS)
        if tx_body is not None:
            body_pr = tx_body.find("a:bodyPr", NS)
            if body_pr is not None:
                if "lIns" in body_pr.attrib:
                    padding["left"] = emu_to_px(body_pr.get("lIns"))
                if "rIns" in body_pr.attrib:
                    padding["right"] = emu_to_px(body_pr.get("rIns"))
                if "tIns" in body_pr.attrib:
                    padding["top"] = emu_to_px(body_pr.get("tIns"))
                if "bIns" in body_pr.attrib:
                    padding["bottom"] = emu_to_px(body_pr.get("bIns"))

                anchor = body_pr.get("anchor", "t")
                if anchor == "ctr":
                    vertical_align = "center"
                elif anchor == "b":
                    vertical_align = "bottom"

                if body_pr.get("wrap") == "none":
                    word_wrap = False

            paragraphs = self._extract_paragraphs(shape, slide, sp_style)

        if prst_geom in ("line", "arc") or arc_params is not None or geom["width"] <= 1.5 or geom["height"] <= 1.5:
            if not paragraphs or all(not p.get("runs") or all(not r.get("text", "").strip() for r in p["runs"]) for p in paragraphs):
                padding = {"top": 0.0, "right": 0.0, "bottom": 0.0, "left": 0.0}

        style_dict = {
            "background": bg_color,
            "borderColor": border_color,
            "borderWidth": border_width,
            "borderStyle": border_style,
            "borderRadius": corner_radius_px,
            "verticalAlign": vertical_align,
            "wordWrap": word_wrap,
            "padding": padding,
        }
        if box_shadow:
            style_dict["boxShadow"] = box_shadow
        if arrow_start != "none":
            style_dict["arrowStart"] = arrow_start
        if arrow_end != "none":
            style_dict["arrowEnd"] = arrow_end

        node_dict = {
            "id": str(shape.shape_id),
            "name": shape.name or f"shape-{shape.shape_id}",
            "type": "shapeNode",
            "zIndex": z_index,
            "shapePreset": prst_geom,
            "geometry": geom,
            "style": style_dict,
            "textBody": paragraphs,
            "ports": self._default_ports(),
        }
        if arrow_start != "none":
            node_dict["arrowStart"] = arrow_start
        if arrow_end != "none":
            node_dict["arrowEnd"] = arrow_end
        if arc_params is not None:
            node_dict["arcParams"] = arc_params

        return node_dict

    def _extract_paragraphs(self, shape, slide, sp_style) -> list:
        paragraphs_out = []
        if not shape.has_text_frame:
            return paragraphs_out

        # Varsayılan metin rengi ve font ailesi
        default_font_color = "#" + self.theme.theme_colors.get("dk1", "000000")
        default_font_family = self.theme.minor_font

        # 1. Shape Style fontRef kontrolü
        if sp_style is not None:
            font_ref = sp_style.find("a:fontRef", NS)
            if font_ref is not None:
                resolved = self.theme.resolve_color_element(font_ref)
                if resolved:
                    default_font_color = resolved
                idx = font_ref.get("idx", "")
                if idx in ("major", "+mj", "+mj-lt"):
                    default_font_family = self.theme.major_font
                elif idx in ("minor", "+mn", "+mn-lt"):
                    default_font_family = self.theme.minor_font

        # 2. Placeholder tipi kontrolü (title -> major_font, body -> minor_font)
        if shape.is_placeholder:
            ph = shape.element.find(".//p:nvPr/p:ph", NS)
            ph_type = ph.get("type", "body") if ph is not None else "body"
            if ph_type in ("title", "ctrTitle"):
                default_font_family = self.theme.major_font
            elif ph_type in ("body", "subTitle"):
                default_font_family = self.theme.minor_font

        # 3. Shape txBody list style varsayılanı (lstStyle/lvl1pPr/defRPr)
        lst_def_rpr = shape.element.find(".//p:txBody/a:lstStyle/a:lvl1pPr/a:defRPr", NS)
        if lst_def_rpr is not None:
            latin = lst_def_rpr.find("a:latin", NS)
            ea = lst_def_rpr.find("a:ea", NS)
            cs = lst_def_rpr.find("a:cs", NS)
            if latin is not None and "typeface" in latin.attrib:
                default_font_family = self.theme.resolve_font_family(latin.get("typeface"))
            elif ea is not None and "typeface" in ea.attrib:
                default_font_family = self.theme.resolve_font_family(ea.get("typeface"))
            elif cs is not None and "typeface" in cs.attrib:
                default_font_family = self.theme.resolve_font_family(cs.get("typeface"))

        default_pt = self._resolve_default_font_pt(shape)

        for p in shape.text_frame.paragraphs:
            p_elem = p._p
            p_pr = p_elem.find("a:pPr", NS)

            align = "left"
            level = p.level or 0
            bullet_char = None
            space_before_px = 0.0
            space_after_px = 0.0

            if p_pr is not None:
                algn_val = p_pr.get("algn", "l")
                align_map = {"l": "left", "ctr": "center", "r": "right", "just": "justify"}
                align = align_map.get(algn_val, "left")

                if p_pr.find("a:buNone", NS) is None:
                    bu_char_elem = p_pr.find("a:buChar", NS)
                    bu_auto_elem = p_pr.find("a:buAutoNum", NS)
                    if bu_char_elem is not None:
                        bullet_char = bu_char_elem.get("char", "•")
                    elif bu_auto_elem is not None:
                        bullet_char = "•"

                spc_bef = p_pr.find("a:spcBef/a:spcPts", NS)
                if spc_bef is not None and "val" in spc_bef.attrib:
                    space_before_px = round((float(spc_bef.get("val")) / 100.0) * (96.0 / 72.0), 2)

                spc_aft = p_pr.find("a:spcAft/a:spcPts", NS)
                if spc_aft is not None and "val" in spc_aft.attrib:
                    space_after_px = round((float(spc_aft.get("val")) / 100.0) * (96.0 / 72.0), 2)

            runs_out = []
            for child in p_elem:
                tag = etree.QName(child).localname
                if tag == "r":
                    r_pr = child.find("a:rPr", NS)
                    t_elem = child.find("a:t", NS)
                    text_val = t_elem.text if (t_elem is not None and t_elem.text) else ""
                    runs_out.append(self._parse_run(text_val, r_pr, p_pr, default_pt, default_font_color, default_font_family))
                elif tag == "br":
                    runs_out.append({
                        "text": "\n",
                        "fontFamily": default_font_family,
                        "fontSize": round(default_pt * (96.0 / 72.0), 2),
                        "color": default_font_color,
                        "bold": False,
                        "italic": False,
                        "underline": False,
                        "strikethrough": False,
                    })
                elif tag == "fld":
                    r_pr = child.find("a:rPr", NS)
                    t_elem = child.find("a:t", NS)
                    text_val = t_elem.text if (t_elem is not None and t_elem.text) else ""
                    runs_out.append(self._parse_run(text_val, r_pr, p_pr, default_pt, default_font_color, default_font_family))

            paragraphs_out.append({
                "align": align,
                "level": level,
                "bullet": bullet_char,
                "spaceBefore": space_before_px,
                "spaceAfter": space_after_px,
                "runs": runs_out,
            })

        return paragraphs_out

    def _resolve_default_font_pt(self, shape) -> float:
        if shape.is_placeholder:
            ph = shape.element.find(".//p:nvPr/p:ph", NS)
            ph_type = ph.get("type", "body") if ph is not None else "body"
            if ph_type in ("title", "ctrTitle"):
                return 36.0
            if ph_type == "subTitle":
                return 22.0
            return 20.0
        return 18.0

    def _parse_run(self, text: str, r_pr, p_pr, default_pt: float, default_color: str,
                   default_font_family: str = None) -> dict:
        font_family = default_font_family or self.theme.minor_font
        font_pt = default_pt
        color = default_color
        bold = False
        italic = False
        underline = False
        strikethrough = False

        # Paragraf varsayılan run özellikleri (defRPr)
        def_rpr = p_pr.find("a:defRPr", NS) if p_pr is not None else None
        for prop_node in [def_rpr, r_pr]:
            if prop_node is None:
                continue
            if "sz" in prop_node.attrib:
                font_pt = float(prop_node.get("sz")) / 100.0
            if "b" in prop_node.attrib:
                bold = prop_node.get("b") in ("1", "true")
            if "i" in prop_node.attrib:
                italic = prop_node.get("i") in ("1", "true")
            if "u" in prop_node.attrib and prop_node.get("u") != "none":
                underline = True
            strike_attr = prop_node.get("strike")
            if strike_attr in ("sngStrike", "dblStrike"):
                strikethrough = True
            elif strike_attr == "noStrike":
                strikethrough = False

            latin = prop_node.find("a:latin", NS)
            ea = prop_node.find("a:ea", NS)
            cs = prop_node.find("a:cs", NS)
            if latin is not None and "typeface" in latin.attrib:
                font_family = self.theme.resolve_font_family(latin.get("typeface"))
            elif ea is not None and "typeface" in ea.attrib:
                font_family = self.theme.resolve_font_family(ea.get("typeface"))
            elif cs is not None and "typeface" in cs.attrib:
                font_family = self.theme.resolve_font_family(cs.get("typeface"))

            solid_fill = prop_node.find("a:solidFill", NS)
            if solid_fill is not None:
                resolved_c = self.theme.resolve_color_element(solid_fill)
                if resolved_c:
                    color = resolved_c

        return {
            "text": text,
            "fontFamily": font_family,
            "fontSize": round(font_pt * (96.0 / 72.0), 2),
            "color": color,
            "bold": bold,
            "italic": italic,
            "underline": underline,
            "strikethrough": strikethrough,
        }

    def _compile_picture(self, shape, slide, parent_x: float, parent_y: float,
                         scale_x: float, scale_y: float, z_index: int) -> dict | None:
        geom = self._resolve_geometry(shape, slide, parent_x, parent_y, scale_x, scale_y)
        if not geom:
            return None

        data_uri = ""
        try:
            blob = shape.image.blob
            content_type = shape.image.content_type or "image/png"
            b64_str = base64.b64encode(blob).decode("ascii")
            data_uri = f"data:{content_type};base64,{b64_str}"
        except Exception:
            return None

        return {
            "id": str(shape.shape_id),
            "name": shape.name or f"image-{shape.shape_id}",
            "type": "imageNode",
            "zIndex": z_index,
            "geometry": geom,
            "imageDataUri": data_uri,
            "ports": self._default_ports(),
        }

    def _compile_table(self, shape, slide, parent_x: float, parent_y: float,
                       scale_x: float, scale_y: float, z_index: int) -> dict | None:
        geom = self._resolve_geometry(shape, slide, parent_x, parent_y, scale_x, scale_y)
        if not geom:
            return None

        table = shape.table
        col_widths = [round(scale_x * emu_to_px(col.width), 2) for col in table.columns]
        rows_data = []

        for row in table.rows:
            row_height = round(scale_y * emu_to_px(row.height), 2)
            cells_data = []
            for cell in row.cells:
                tc_pr = cell._tc.find("a:tcPr", NS)
                cell_bg = "#FFFFFF"
                if tc_pr is not None:
                    solid = tc_pr.find("a:solidFill", NS)
                    if solid is not None:
                        cell_bg = self.theme.resolve_color_element(solid) or "#FFFFFF"

                cell_text = cell.text_frame.text if cell.text_frame else ""
                cell_font_family = self.theme.minor_font
                cell_font_size = 13.0
                cell_color = "#000000"
                cell_bold = False

                if cell.text_frame and cell.text_frame.paragraphs:
                    p0 = cell.text_frame.paragraphs[0]
                    if p0.runs:
                        r0 = p0.runs[0]
                        r_pr = r0._r.find("a:rPr", NS) if hasattr(r0, "_r") else None
                        if r_pr is not None:
                            latin = r_pr.find("a:latin", NS)
                            ea = r_pr.find("a:ea", NS)
                            cs = r_pr.find("a:cs", NS)
                            if latin is not None and "typeface" in latin.attrib:
                                cell_font_family = self.theme.resolve_font_family(latin.get("typeface"))
                            elif ea is not None and "typeface" in ea.attrib:
                                cell_font_family = self.theme.resolve_font_family(ea.get("typeface"))
                            elif cs is not None and "typeface" in cs.attrib:
                                cell_font_family = self.theme.resolve_font_family(cs.get("typeface"))
                            if "sz" in r_pr.attrib:
                                cell_font_size = round((float(r_pr.get("sz")) / 100.0) * (96.0 / 72.0), 2)
                            if "b" in r_pr.attrib:
                                cell_bold = r_pr.get("b") in ("1", "true")
                            solid = r_pr.find("a:solidFill", NS)
                            if solid is not None:
                                c = self.theme.resolve_color_element(solid)
                                if c:
                                    cell_color = c

                cells_data.append({
                    "text": cell_text,
                    "backgroundColor": cell_bg,
                    "fontFamily": cell_font_family,
                    "fontSize": cell_font_size,
                    "color": cell_color,
                    "bold": cell_bold,
                })
            rows_data.append({
                "height": row_height,
                "cells": cells_data,
            })

        return {
            "id": str(shape.shape_id),
            "name": shape.name or f"table-{shape.shape_id}",
            "type": "tableNode",
            "zIndex": z_index,
            "geometry": geom,
            "table": {
                "columnWidths": col_widths,
                "rows": rows_data,
            },
            "ports": self._default_ports(),
        }

    def _compile_connector(self, shape, nodes: list, edges: list,
                           parent_x: float, parent_y: float, scale_x: float, scale_y: float,
                           z_counter: list):
        sp_elem = shape.element
        st_cxn = sp_elem.find(".//p:nvCxnSpPr/p:cNvCxnSpPr/a:stCxn", NS)
        end_cxn = sp_elem.find(".//p:nvCxnSpPr/p:cNvCxnSpPr/a:endCxn", NS)

        geom = self._resolve_geometry(shape, None, parent_x, parent_y, scale_x, scale_y)
        if not geom:
            return

        # Başlangıç ve Bitiş koordinatlarının flipH ve flipV'ye göre hesabı (serbest uçlar için)
        x1 = geom["x"] + geom["width"] if geom["flipH"] else geom["x"]
        y1 = geom["y"] + geom["height"] if geom["flipV"] else geom["y"]
        x2 = geom["x"] if geom["flipH"] else geom["x"] + geom["width"]
        y2 = geom["y"] if geom["flipV"] else geom["y"] + geom["height"]

        if st_cxn is not None and "id" in st_cxn.attrib:
            source_id = str(st_cxn.get("id"))
            source_idx = int(st_cxn.get("idx", "0")) % 4
            source_handle = f"port-{source_idx}-src"
        else:
            self._virtual_anchor_counter += 1
            source_id = f"virtual-anchor-{self._virtual_anchor_counter}"
            source_handle = "port-0-src"
            nodes.append(self._create_virtual_anchor(source_id, x1, y1, z_counter[0]))
            z_counter[0] += 1

        if end_cxn is not None and "id" in end_cxn.attrib:
            target_id = str(end_cxn.get("id"))
            target_idx = int(end_cxn.get("idx", "0")) % 4
            target_handle = f"port-{target_idx}-tgt"
        else:
            self._virtual_anchor_counter += 1
            target_id = f"virtual-anchor-{self._virtual_anchor_counter}"
            target_handle = "port-0-tgt"
            nodes.append(self._create_virtual_anchor(target_id, x2, y2, z_counter[0]))
            z_counter[0] += 1

        # Connector Routing Tipi (straight, smoothstep, bezier)
        prst_elem = sp_elem.find(".//p:spPr/a:prstGeom", NS)
        prst_val = prst_elem.get("prst", "line") if prst_elem is not None else "line"
        edge_type = "straight"
        if "bent" in prst_val.lower():
            edge_type = "smoothstep"
        elif "curved" in prst_val.lower():
            edge_type = "bezier"

        # Çizgi Rengi, Kalınlığı ve Ok Uçları (headEnd / tailEnd)
        stroke_color = "#" + self.theme.theme_colors.get("dk1", "000000")
        stroke_width = 2.0
        stroke_dash = None
        arrow_start = "none"
        arrow_end = "none"

        ln_elem = sp_elem.find(".//p:spPr/a:ln", NS)
        sp_style = sp_elem.find("p:style", NS)

        if sp_style is not None:
            ln_ref = sp_style.find("a:lnRef", NS)
            if ln_ref is not None:
                c = self.theme.resolve_color_element(ln_ref)
                if c:
                    stroke_color = c

        if ln_elem is not None:
            if "w" in ln_elem.attrib:
                stroke_width = max(1.5, emu_to_px(ln_elem.get("w")))
            solid_ln = ln_elem.find("a:solidFill", NS)
            if solid_ln is not None:
                c = self.theme.resolve_color_element(solid_ln)
                if c:
                    stroke_color = c

            dash_elem = ln_elem.find("a:prstDash", NS)
            if dash_elem is not None:
                d_val = dash_elem.get("val", "solid")
                if "dot" in d_val.lower():
                    stroke_dash = "3 3"
                elif "dash" in d_val.lower():
                    stroke_dash = "6 4"

            head_end = ln_elem.find("a:headEnd", NS)
            tail_end = ln_elem.find("a:tailEnd", NS)
            if head_end is not None and head_end.get("type", "none") != "none":
                arrow_start = head_end.get("type")
            if tail_end is not None and tail_end.get("type", "none") != "none":
                arrow_end = tail_end.get("type")

        edges.append({
            "id": f"edge-{shape.shape_id}",
            "type": edge_type,
            "sourceNodeId": source_id,
            "targetNodeId": target_id,
            "sourceHandleId": source_handle,
            "targetHandleId": target_handle,
            "style": {
                "strokeColor": stroke_color,
                "strokeWidth": stroke_width,
                "strokeDashArray": stroke_dash,
                "arrowStart": arrow_start,
                "arrowEnd": arrow_end,
            },
        })

    def _create_virtual_anchor(self, node_id: str, x: float, y: float, z_index: int) -> dict:
        return {
            "id": node_id,
            "name": node_id,
            "type": "anchorNode",
            "zIndex": z_index,
            "geometry": {
                "x": round(x, 2),
                "y": round(y, 2),
                "width": 1.0,
                "height": 1.0,
                "rotation": 0.0,
                "flipH": False,
                "flipV": False,
            },
            "ports": [{"id": "port-0", "idx": 0, "xPercent": 0.5, "yPercent": 0.5}],
        }

    def _compile_group(self, group_shape, slide, nodes: list, edges: list,
                       parent_x: float, parent_y: float, parent_sx: float, parent_sy: float,
                       z_counter: list):
        grp_elem = group_shape.element
        grp_xfrm = grp_elem.find("p:grpSpPr/a:xfrm", NS)
        if grp_xfrm is None:
            return

        off = grp_xfrm.find("a:off", NS)
        ext = grp_xfrm.find("a:ext", NS)
        ch_off = grp_xfrm.find("a:chOff", NS)
        ch_ext = grp_xfrm.find("a:chExt", NS)

        if None in (off, ext, ch_off, ch_ext):
            return

        ch_cx = float(ch_ext.get("cx", "1")) or 1.0
        ch_cy = float(ch_ext.get("cy", "1")) or 1.0
        scale_x = float(ext.get("cx", "1")) / ch_cx
        scale_y = float(ext.get("cy", "1")) / ch_cy
        group_flip_h = grp_xfrm.get("flipH", "0") in ("1", "true")
        group_flip_v = grp_xfrm.get("flipV", "0") in ("1", "true")

        off_x_px = emu_to_px(int(off.get("x", 0)))
        off_y_px = emu_to_px(int(off.get("y", 0)))
        ch_off_x_px = emu_to_px(int(ch_off.get("x", 0)))
        ch_off_y_px = emu_to_px(int(ch_off.get("y", 0)))

        eff_sx = parent_sx * scale_x
        eff_sy = parent_sy * scale_y

        if group_flip_h:
            eff_sx = -eff_sx
            base_x = parent_x + parent_sx * (off_x_px + emu_to_px(int(ext.get("cx", 0)))) - eff_sx * ch_off_x_px
        else:
            base_x = parent_x + parent_sx * off_x_px - eff_sx * ch_off_x_px
        if group_flip_v:
            eff_sy = -eff_sy
            base_y = parent_y + parent_sy * (off_y_px + emu_to_px(int(ext.get("cy", 0)))) - eff_sy * ch_off_y_px
        else:
            base_y = parent_y + parent_sy * off_y_px - eff_sy * ch_off_y_px

        for child_shape in group_shape.shapes:
            self._process_shape(child_shape, slide, nodes, edges, base_x, base_y, eff_sx, eff_sy, z_counter)

    @staticmethod
    def _default_ports() -> list:
        return [
            {"id": "port-0", "idx": 0, "xPercent": 0.5, "yPercent": 0.0},  # Top
            {"id": "port-1", "idx": 1, "xPercent": 0.0, "yPercent": 0.5},  # Left
            {"id": "port-2", "idx": 2, "xPercent": 0.5, "yPercent": 1.0},  # Bottom
            {"id": "port-3", "idx": 3, "xPercent": 1.0, "yPercent": 0.5},  # Right
        ]


def main():
    if len(sys.argv) not in (1, 3):
        print(
            "Kullanım: python src/python/main.py "
            "[<girdi.pptx> <cikti_ast.json>]"
        )
        sys.exit(1)

    if len(sys.argv) == 3:
        input_files = [(Path(sys.argv[1]), Path(sys.argv[2]))]
    else:
        input_dir = Path("data/input")
        input_files = [
            (input_pptx, Path("data/output") / f"{input_pptx.stem}.json")
            for input_pptx in sorted(input_dir.glob("*.pptx"))
            if not input_pptx.name.startswith("~$")
        ]
        if not input_files:
            print(f"Hata: '{input_dir}' içinde .pptx dosyası bulunamadı.")
            sys.exit(1)

    for input_pptx, output_json in input_files:
        if not input_pptx.exists():
            print(f"Hata: '{input_pptx}' dosyası bulunamadı.")
            sys.exit(1)

        compiler = PresentationMLCompiler(str(input_pptx))
        ast_data = compiler.compile()
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(
            json.dumps(ast_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            f"Tamamlandı: {len(ast_data['slides'])} slayt başarıyla "
            f"'{output_json}' dosyasına derlendi."
        )


if __name__ == "__main__":
    main()