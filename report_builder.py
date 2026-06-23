from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, Image as RLImage, PageBreak,
    KeepTogether,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from PIL import Image as PILImage
from io import BytesIO
import os
from datetime import datetime

PAGE_W, PAGE_H = A4
MARGIN = 50
USABLE_W = PAGE_W - 2 * MARGIN

SEVERITY_COLORS = {
    "Critical": colors.HexColor("#DC2626"),
    "High": colors.HexColor("#EA580C"),
    "Medium": colors.HexColor("#D97706"),
    "Low": colors.HexColor("#16A34A"),
}
SEVERITY_BG = {
    "Critical": colors.HexColor("#FEF2F2"),
    "High": colors.HexColor("#FFF7ED"),
    "Medium": colors.HexColor("#FFFBEB"),
    "Low": colors.HexColor("#F0FDF4"),
}
ACCENT = colors.HexColor("#1E3A5F")
DARK = colors.HexColor("#1E293B")
GRAY = colors.HexColor("#64748B")
BORDER = colors.HexColor("#CBD5E1")
LIGHT_BG = colors.HexColor("#F1F5F8")


def build_pdf_report(ddr_data: dict, images: list, output_path: str):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        rightMargin=MARGIN, leftMargin=MARGIN,
        topMargin=42, bottomMargin=45,
    )

    S = {
        "ct": ParagraphStyle("ct", fontSize=24, fontName="Helvetica-Bold", alignment=TA_CENTER, textColor=ACCENT, leading=30),
        "cs": ParagraphStyle("cs", fontSize=12, fontName="Helvetica", alignment=TA_CENTER, textColor=GRAY, leading=16),
        "sec": ParagraphStyle("sec", fontSize=14, fontName="Helvetica-Bold", textColor=ACCENT, leading=18, spaceBefore=16, spaceAfter=8),
        "h2": ParagraphStyle("h2", fontSize=11, fontName="Helvetica-Bold", textColor=DARK, leading=15, spaceBefore=8, spaceAfter=4),
        "body": ParagraphStyle("body", fontSize=9, fontName="Helvetica", textColor=DARK, leading=16, spaceAfter=0, alignment=TA_LEFT),
        "sm": ParagraphStyle("sm", fontSize=8.5, fontName="Helvetica", textColor=GRAY, leading=12, spaceAfter=4),
        "label": ParagraphStyle("lbl", fontSize=9, fontName="Helvetica-Bold", textColor=GRAY, leading=12),
        "note": ParagraphStyle("note", fontSize=8.5, fontName="Helvetica-Oblique", textColor=GRAY, leading=11),
        "bul": ParagraphStyle("bul", fontSize=9.5, fontName="Helvetica", textColor=DARK, leading=14, spaceAfter=4, leftIndent=14),
        "hdr": ParagraphStyle("hdr", fontSize=9, fontName="Helvetica-Bold", textColor=colors.white, leading=13),
    }

    def safe_str(val, default="Not Available"):
        return str(val) if val else default

    def find_image(ref):
        for img in images:
            if img.get("ref") == ref:
                return img
        return None

    def hr(thick=1.5):
        c = ACCENT if thick > 1 else BORDER
        return HRFlowable(width="100%", thickness=thick, color=c, spaceAfter=6, spaceBefore=1)

    def render_image(img_ref):
        if img_ref == "Not Available":
            return Paragraph("Image Not Available", S["note"])
        img_obj = find_image(img_ref)
        if not img_obj or not img_obj.get("data"):
            return Paragraph("Image Not Available", S["note"])
        try:
            pil = PILImage.open(BytesIO(img_obj["data"]))
            if pil.mode not in ("RGB", "L"):
                pil = pil.convert("RGB")
            iw, ih = pil.size
            max_w = USABLE_W * 0.9
            max_h = 120 * mm
            scale = min(max_w / iw, max_h / ih, 1.0)
            buf = BytesIO()
            pil.save(buf, format="PNG")
            buf.seek(0)
            img = RLImage(buf, width=iw * scale, height=ih * scale, hAlign='CENTER')
            return img
        except Exception as e:
            print("  [WARN] Image failed: %s - %s" % (img_ref, e))
            return Paragraph("[Image could not be rendered]", S["note"])

    def sev_box(level, text=None, width=60):
        c = SEVERITY_COLORS.get(level, GRAY)
        bg = SEVERITY_BG.get(level, LIGHT_BG)
        txt = text or level.upper()
        p = Paragraph(
            '<font color="%s"><b>%s</b></font>' % (c.hexval(), txt),
            ParagraphStyle("sb", fontSize=9, fontName="Helvetica-Bold", alignment=TA_CENTER, leading=12)
        )
        t = Table([[p]], colWidths=[width])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("BOX", (0, 0), (-1, -1), 1, c),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        return t

    def std_table(headers, rows, col_widths):
        data = [headers] + rows
        s = [
            ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTSIZE", (0, 1), (-1, -1), 8.5),
            ("TEXTCOLOR", (0, 1), (-1, -1), DARK),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("LEADING", (0, 0), (-1, -1), 16),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
        # Wrap string cells in Paragraph for proper text flow
        wrapped = []
        for r_idx, row in enumerate(data):
            style = S["hdr"] if r_idx == 0 else S["body"]
            wrapped.append([Paragraph(str(cell), style) if not isinstance(cell, Paragraph) else cell for cell in row])
        t = Table(wrapped, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle(s))
        return t

    story = []

    # ── COVER PAGE ──
    story.append(Spacer(1, 80))
    story.append(Paragraph("DETAILED DIAGNOSTIC REPORT", S["ct"]))
    story.append(Paragraph("DDR", S["cs"]))
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="40%", thickness=2.5, color=ACCENT, spaceAfter=20))
    story.append(Spacer(1, 10))

    info = [
        [Paragraph("<b>Report Title:</b>", S["label"]), Paragraph(safe_str(ddr_data.get("report_title", "Site Inspection")), S["body"])],
        [Paragraph("<b>Report Date:</b>", S["label"]), Paragraph(safe_str(ddr_data.get("report_date", datetime.now().strftime("%Y-%m-%d"))), S["body"])],
    ]
    it = Table(info, colWidths=[22 * mm, USABLE_W - 22 * mm])
    it.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(it)
    story.append(Spacer(1, 28))

    overall = ddr_data.get("severity_assessment", {}).get("overall", "N/A")
    sev_c = SEVERITY_COLORS.get(overall, GRAY)
    sev_bg = SEVERITY_BG.get(overall, LIGHT_BG)
    badge = Table(
        [[Paragraph('<font color="%s" size="14"><b>OVERALL SEVERITY: %s</b></font>' % (sev_c.hexval(), overall.upper()),
                    ParagraphStyle("bd", fontSize=14, fontName="Helvetica-Bold", alignment=TA_CENTER, leading=18))]],
        colWidths=[280])
    badge.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), sev_bg),
        ("BOX", (0, 0), (-1, -1), 2, sev_c),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ]))
    wrap = Table([[badge]], colWidths=[USABLE_W])
    wrap.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    story.append(wrap)
    story.append(Spacer(1, 30))
    story.append(HRFlowable(width="60%", thickness=0.5, color=BORDER, spaceAfter=10))
    story.append(Paragraph("<b>Prepared For:</b> Rachit Rahaman", S["sm"]))
    story.append(Paragraph("<b>Prepared By:</b> AI-Assisted Analysis System", S["sm"]))
    story.append(PageBreak())

    # ── SECTION 1 ──
    story.append(Paragraph("1. Property Issue Summary", S["sec"]))
    story.append(hr(2))
    story.append(Paragraph(safe_str(ddr_data.get("property_summary")), S["body"]))
    story.append(Spacer(1, 6))
    root_causes = ddr_data.get("root_causes", [])
    if root_causes:
        story.append(Paragraph("Key Issues Identified:", S["h2"]))
        rc_rows = [[str(i), safe_str(rc.get("issue")), safe_str(rc.get("cause"))] for i, rc in enumerate(root_causes, 1)]
        story.append(std_table(["#", "Issue", "Probable Cause"], rc_rows, [14, 60 * mm, 88 * mm]))

    # ── SECTION 2 ──
    story.append(Paragraph("2. Area-wise Observations", S["sec"]))
    story.append(hr(2))

    for idx, obs in enumerate(ddr_data.get("area_observations", []), 1):
        area = safe_str(obs.get("area", "Unknown Area"))
        observation = safe_str(obs.get("observation"))
        thermal = safe_str(obs.get("thermal_finding"))
        severity = safe_str(obs.get("severity", "Low"))
        sev_reason = safe_str(obs.get("severity_reason"))
        img_ref = safe_str(obs.get("image_ref", "Not Available"))

        story.append(Paragraph("<b>Observation %d:</b>  %s" % (idx, area), S["h2"]))
        story.append(hr(0.5))

        LABEL_W = 26 * mm
        obs_rows = [
            [Paragraph("<b>Finding:</b>", S["label"]), Paragraph(observation, S["body"])],
            [Paragraph("<b>Thermal:</b>", S["label"]), Paragraph(thermal, S["body"])],
            [sev_box(severity, width=60), Paragraph('<font color="%s"><b>Reasoning:</b></font> %s' % (GRAY.hexval(), sev_reason),
                                                ParagraphStyle("sr", fontSize=9, fontName="Helvetica", textColor=DARK, leading=16))],
        ]
        ot = Table(obs_rows, colWidths=[LABEL_W, USABLE_W - LABEL_W])
        ot.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(ot)

        story.append(Spacer(1, 8))
        story.append(render_image(img_ref))

        story.append(Spacer(1, 14))

    story.append(PageBreak())
    # ── SECTION 3 ──
    story.append(Paragraph("3. Probable Root Causes", S["sec"]))
    story.append(hr(2))
    if root_causes:
        rc_rows = [[str(i), safe_str(rc.get("issue")), safe_str(rc.get("cause"))] for i, rc in enumerate(root_causes, 1)]
        story.append(std_table(["#", "Issue", "Root Cause"], rc_rows, [14, 60 * mm, 88 * mm]))
    else:
        story.append(Paragraph("No root cause data available.", S["body"]))

    # ── SECTION 4 ──
    story.append(Paragraph("4. Severity Assessment", S["sec"]))
    story.append(hr(2))
    sa = ddr_data.get("severity_assessment", {})
    ov = safe_str(sa.get("overall"))
    reasoning = safe_str(sa.get("reasoning"))
    sr = [[sev_box(ov, "Overall: " + ov, width=65), Paragraph(reasoning, S["body"])]]
    st = Table(sr, colWidths=[28 * mm, USABLE_W - 28 * mm])
    st.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]))
    story.append(st)

    story.append(PageBreak())
    # ── SECTION 5 ──
    story.append(Paragraph("5. Recommended Actions", S["sec"]))
    story.append(hr(2))

    actions = ddr_data.get("recommended_actions", [])
    if actions:
        pbg = {"Immediate": colors.HexColor("#FEE2E2"), "Short-term": colors.HexColor("#FEF3C7"), "Long-term": colors.HexColor("#D1FAE5")}
        ptc = {"Immediate": colors.HexColor("#DC2626"), "Short-term": colors.HexColor("#D97706"), "Long-term": colors.HexColor("#16A34A")}
        ad = [["Priority", "Action"]]
        for act in actions:
            ad.append([safe_str(act.get("priority")), safe_str(act.get("action"))])
        stl = [
            ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("LEADING", (0, 0), (-1, -1), 16),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
        for i, act in enumerate(actions, 1):
            p = act.get("priority", "")
            stl.append(("BACKGROUND", (0, i), (-1, i), pbg.get(p, colors.white)))
            stl.append(("TEXTCOLOR", (0, i), (0, i), ptc.get(p, DARK)))
            stl.append(("FONTNAME", (0, i), (0, i), "Helvetica-Bold"))
        # Wrap strings in Paragraph for proper text flow in action column
        ad_wrapped = []
        for r_idx, r in enumerate(ad):
            if r_idx == 0:
                ad_wrapped.append([Paragraph(str(cell), S["hdr"]) if isinstance(cell, str) else cell for cell in r])
            else:
                ad_wrapped.append([
                    Paragraph(str(r[0]), ParagraphStyle("ap", fontSize=8.5, fontName="Helvetica-Bold", leading=12, textColor=ptc.get(r[0], DARK))),
                    Paragraph(str(r[1]), S["body"]),
                ])
        at = Table(ad_wrapped, colWidths=[42 * mm, 128 * mm], repeatRows=1)
        at.setStyle(TableStyle(stl))
        story.append(at)
    else:
        story.append(Paragraph("No recommended actions available.", S["body"]))

    # ── SECTION 6 ──
    story.append(Paragraph("6. Additional Notes", S["sec"]))
    story.append(hr(2))
    story.append(Paragraph(safe_str(ddr_data.get("additional_notes")), S["body"]))

    # ── SECTION 7 ──
    story.append(Paragraph("7. Missing or Unclear Information", S["sec"]))
    story.append(hr(2))
    missing = ddr_data.get("missing_or_unclear", [])
    if missing:
        for item in missing:
            story.append(Paragraph("-  %s" % item, S["bul"]))
    else:
        story.append(Paragraph("All key information was present in the documents.", S["body"]))

    doc.build(story)
    print("    [OK] PDF built: %s" % output_path)
