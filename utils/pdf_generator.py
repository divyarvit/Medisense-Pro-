"""
PDF Report Generator for MediSense Pro
Uses reportlab to generate professional clinical PDF reports.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, HRFlowable)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from datetime import datetime

# Brand colours
BLUE     = colors.HexColor("#1565c0")
BLUE_LT  = colors.HexColor("#e3f2fd")
GREEN    = colors.HexColor("#43a047")
GREEN_LT = colors.HexColor("#e8f5e9")
RED      = colors.HexColor("#e53935")
RED_LT   = colors.HexColor("#fce4ec")
ORANGE   = colors.HexColor("#fb8c00")
ORANGE_LT= colors.HexColor("#fff3e0")
GREY     = colors.HexColor("#555555")
LGREY    = colors.HexColor("#f8f9fa")
BLACK    = colors.black
WHITE    = colors.white


def _styles():
    s = getSampleStyleSheet()
    custom = {
        "Title":    ParagraphStyle("Title",    fontName="Helvetica-Bold",
                                   fontSize=20, textColor=WHITE,    leading=26,alignment=TA_CENTER),
        "SubTitle": ParagraphStyle("SubTitle", fontName="Helvetica",
                                   fontSize=11, textColor=WHITE,    leading=16,alignment=TA_CENTER),
        "SecHead":  ParagraphStyle("SecHead",  fontName="Helvetica-Bold",
                                   fontSize=13, textColor=BLUE,     leading=18,spaceBefore=10),
        "Body":     ParagraphStyle("Body",     fontName="Helvetica",
                                   fontSize=10, textColor=colors.HexColor("#333"),leading=15),
        "Small":    ParagraphStyle("Small",    fontName="Helvetica",
                                   fontSize=9,  textColor=GREY,     leading=13),
        "Bold":     ParagraphStyle("Bold",     fontName="Helvetica-Bold",
                                   fontSize=10, textColor=BLACK,    leading=15),
        "Bullet":   ParagraphStyle("Bullet",   fontName="Helvetica",
                                   fontSize=10, textColor=colors.HexColor("#333"),
                                   leading=15,  leftIndent=14, bulletIndent=4),
        "Warn":     ParagraphStyle("Warn",     fontName="Helvetica",
                                   fontSize=9,  textColor=RED,      leading=13, alignment=TA_CENTER),
    }
    return {**{k: s[k] for k in s.byName}, **custom}


def generate_report_pdf(module_name, patient_name, patient_info,
                         severity, severity_explanation,
                         conditions, confidence,
                         do_list, dont_list,
                         home_care, when_doctor,
                         summary="", extra_info=""):
    """
    Returns a BytesIO object containing the PDF.
    """
    buffer = BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=A4,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=1.5*cm, bottomMargin=2*cm)
    st     = _styles()
    story  = []
    now    = datetime.now().strftime("%d %B %Y, %I:%M %p")

    # ── Header Banner ──────────────────────────────────────────────────────
    header_data = [[
        Paragraph("🏥  MediSense Pro", st["Title"]),
        Paragraph(f"AI-Based Disease Diagnosis<br/>& Recommendation System", st["SubTitle"]),
    ]]
    header_tbl = Table(header_data, colWidths=[9*cm, 8*cm])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(-1,-1), BLUE),
        ("ROUNDEDCORNERS", (0,0), (-1,-1), [8]),
        ("TOPPADDING",  (0,0),(-1,-1), 14),
        ("BOTTOMPADDING",(0,0),(-1,-1), 14),
        ("LEFTPADDING", (0,0),(-1,-1), 12),
        ("RIGHTPADDING",(0,0),(-1,-1), 12),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 0.3*cm))

    # ── Patient Info Row ──────────────────────────────────────────────────
    info_data = [[
        Paragraph(f"<b>Patient:</b> {patient_name}", st["Body"]),
        Paragraph(f"<b>Module:</b> {module_name}", st["Body"]),
        Paragraph(f"<b>Date:</b> {now}", st["Small"]),
    ]]
    info_tbl = Table(info_data, colWidths=[6*cm, 6*cm, 5*cm])
    info_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(-1,-1), LGREY),
        ("BOX",         (0,0),(-1,-1), 0.5, colors.HexColor("#e0e0e0")),
        ("TOPPADDING",  (0,0),(-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("LEFTPADDING", (0,0),(-1,-1), 10),
    ]))
    story.append(info_tbl)

    if patient_info:
        story.append(Spacer(1, 0.15*cm))
        story.append(Paragraph(f"<b>Patient Details:</b> {patient_info}", st["Small"]))

    story.append(Spacer(1, 0.4*cm))

    # ── Section 1: Summary ────────────────────────────────────────────────
    story.append(Paragraph("📋  Section 1 — Clinical Summary", st["SecHead"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE))
    story.append(Spacer(1, 0.2*cm))

    if summary:
        sum_data = [[Paragraph(summary, st["Body"])]]
        sum_tbl  = Table(sum_data, colWidths=[17*cm])
        sum_tbl.setStyle(TableStyle([
            ("BACKGROUND",  (0,0),(-1,-1), BLUE_LT),
            ("LEFTPADDING", (0,0),(-1,-1), 12),
            ("RIGHTPADDING",(0,0),(-1,-1), 12),
            ("TOPPADDING",  (0,0),(-1,-1), 10),
            ("BOTTOMPADDING",(0,0),(-1,-1), 10),
            ("LINEAFTER",   (0,0),(0,-1), 4, BLUE),
        ]))
        story.append(sum_tbl)
        story.append(Spacer(1, 0.3*cm))

    # ── Section 2: Severity ───────────────────────────────────────────────
    story.append(Paragraph("🚨  Section 2 — Severity Assessment", st["SecHead"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE))
    story.append(Spacer(1, 0.2*cm))

    sev_color = {"Mild": GREEN, "Moderate": ORANGE, "Severe": RED}.get(severity, BLUE)
    sev_lt    = {"Mild": GREEN_LT,"Moderate": ORANGE_LT,"Severe": RED_LT}.get(severity, BLUE_LT)

    sev_data = [[
        Paragraph(f"<b>Severity Level: {severity}</b>", ParagraphStyle(
            "SevLabel", fontName="Helvetica-Bold", fontSize=14,
            textColor=sev_color, alignment=TA_CENTER)),
        Paragraph(severity_explanation, st["Body"]),
    ]]
    sev_tbl = Table(sev_data, colWidths=[4.5*cm, 12.5*cm])
    sev_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(0,0), sev_lt),
        ("BACKGROUND",  (1,0),(1,0), LGREY),
        ("BOX",         (0,0),(-1,-1), 1, sev_color),
        ("INNERGRID",   (0,0),(-1,-1), 0.5, sev_color),
        ("TOPPADDING",  (0,0),(-1,-1), 10),
        ("BOTTOMPADDING",(0,0),(-1,-1), 10),
        ("LEFTPADDING", (0,0),(-1,-1), 10),
        ("VALIGN",      (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(sev_tbl)
    story.append(Spacer(1, 0.3*cm))

    # ── Section 3: Confidence ─────────────────────────────────────────────
    story.append(Paragraph("📊  Section 3 — Assessment Confidence", st["SecHead"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE))
    story.append(Spacer(1, 0.2*cm))

    conf_label = "High" if confidence>=70 else ("Moderate" if confidence>=45 else "Low")
    conf_color = GREEN if confidence>=70 else (ORANGE if confidence>=45 else RED)

    conf_data = [[
        Paragraph(f"<b>Confidence: {confidence:.0f}% ({conf_label})</b>", st["Bold"]),
        Paragraph(f"Based on completeness and consistency of clinical data provided.", st["Small"]),
    ]]
    conf_tbl = Table(conf_data, colWidths=[6*cm, 11*cm])
    conf_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(-1,-1), LGREY),
        ("LEFTLINECOLOR",(0,0),(0,-1), conf_color),
        ("LEFTPADDING", (0,0),(-1,-1), 10),
        ("TOPPADDING",  (0,0),(-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
    ]))
    story.append(conf_tbl)
    story.append(Spacer(1, 0.3*cm))

    # ── Section 4: Differential Diagnosis ────────────────────────────────
    story.append(Paragraph("🔬  Section 4 — Differential Diagnosis", st["SecHead"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE))
    story.append(Spacer(1, 0.2*cm))

    dx_header = [
        Paragraph("<b>Rank</b>", st["Bold"]),
        Paragraph("<b>Condition</b>", st["Bold"]),
        Paragraph("<b>Probability</b>", st["Bold"]),
        Paragraph("<b>Description</b>", st["Bold"]),
        Paragraph("<b>ICD-10</b>", st["Bold"]),
    ]
    dx_rows = [dx_header]
    rank_labels = ["🥇 Most Likely","🥈 Second","🥉 Third"]
    for i, cond in enumerate(conditions[:3]):
        dx_rows.append([
            Paragraph(rank_labels[i] if i<3 else f"#{i+1}", st["Small"]),
            Paragraph(f"<b>{cond.get('condition','')}</b>", st["Bold"]),
            Paragraph(f"<b>{cond.get('probability',0):.1f}%</b>",
                      ParagraphStyle("PctStyle",fontName="Helvetica-Bold",fontSize=11,
                                     textColor=["#1565c0","#fb8c00","#9e9e9e"][i] if i<3 else BLACK,
                                     alignment=TA_CENTER)),
            Paragraph(cond.get('description',''), st["Small"]),
            Paragraph(cond.get('icd','—'), st["Small"]),
        ])

    dx_tbl = Table(dx_rows, colWidths=[2.5*cm, 4.5*cm, 2*cm, 6.5*cm, 1.5*cm])
    dx_style = [
        ("BACKGROUND",  (0,0),(-1,0), BLUE),
        ("TEXTCOLOR",   (0,0),(-1,0), WHITE),
        ("FONTNAME",    (0,0),(-1,0), "Helvetica-Bold"),
        ("TOPPADDING",  (0,0),(-1,-1), 7),
        ("BOTTOMPADDING",(0,0),(-1,-1), 7),
        ("LEFTPADDING", (0,0),(-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[LGREY, WHITE]),
        ("GRID",        (0,0),(-1,-1), 0.5, colors.HexColor("#e0e0e0")),
        ("VALIGN",      (0,0),(-1,-1), "MIDDLE"),
    ]
    dx_tbl.setStyle(TableStyle(dx_style))
    story.append(dx_tbl)
    story.append(Spacer(1, 0.3*cm))

    # ── Section 5: Do / Don't ─────────────────────────────────────────────
    story.append(Paragraph("✅  Section 5 — What To Do & What NOT To Do", st["SecHead"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE))
    story.append(Spacer(1, 0.2*cm))

    do_items   = [Paragraph(f"✔ {item}", st["Bullet"]) for item in do_list]
    dont_items = [Paragraph(f"✖ {item}", st["Bullet"]) for item in dont_list]

    do_col   = [Paragraph("<b>✅ DO These Things</b>", ParagraphStyle(
                    "DoHead",fontName="Helvetica-Bold",fontSize=11,textColor=GREEN))] + do_items
    dont_col = [Paragraph("<b>❌ DO NOT Do These</b>", ParagraphStyle(
                    "DontHead",fontName="Helvetica-Bold",fontSize=11,textColor=RED))] + dont_items

    max_len = max(len(do_col), len(dont_col))
    while len(do_col)   < max_len: do_col.append(Paragraph("", st["Body"]))
    while len(dont_col) < max_len: dont_col.append(Paragraph("", st["Body"]))

    dd_data = [[d, dn] for d, dn in zip(do_col, dont_col)]
    dd_tbl  = Table(dd_data, colWidths=[8.5*cm, 8.5*cm])
    dd_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(0,-1), GREEN_LT),
        ("BACKGROUND",  (1,0),(1,-1), RED_LT),
        ("TOPPADDING",  (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING", (0,0),(-1,-1), 10),
        ("RIGHTPADDING",(0,0),(-1,-1), 8),
        ("VALIGN",      (0,0),(-1,-1), "TOP"),
        ("GRID",        (0,0),(-1,-1), 0.5, colors.HexColor("#e0e0e0")),
    ]))
    story.append(dd_tbl)
    story.append(Spacer(1, 0.3*cm))

    # ── Section 6: Home Care ──────────────────────────────────────────────
    story.append(Paragraph("🏠  Section 6 — Home Care Instructions", st["SecHead"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE))
    story.append(Spacer(1, 0.2*cm))

    hc_items = [[Paragraph(f"🏠  {tip}", st["Bullet"])] for tip in home_care]
    if hc_items:
        hc_tbl = Table(hc_items, colWidths=[17*cm])
        hc_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), BLUE_LT),
            ("TOPPADDING",    (0,0),(-1,-1), 5),
            ("BOTTOMPADDING", (0,0),(-1,-1), 5),
            ("LEFTPADDING",   (0,0),(-1,-1), 12),
            ("ROWBACKGROUNDS",(0,0),(-1,-1), [BLUE_LT, WHITE]),
            ("GRID",          (0,0),(-1,-1), 0.3, colors.HexColor("#bbdefb")),
        ]))
        story.append(hc_tbl)
    story.append(Spacer(1, 0.3*cm))

    # ── Section 7: When to See Doctor ────────────────────────────────────
    story.append(Paragraph("🩺  Section 7 — When to Consult a Doctor", st["SecHead"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE))
    story.append(Spacer(1, 0.2*cm))

    for point in when_doctor:
        is_emerg = any(w in point.upper() for w in ["IMMEDIATELY","EMERGENCY","CALL 108","URGENT","NOW"])
        color_bg = RED_LT if is_emerg else ORANGE_LT
        prefix   = "🚨" if is_emerg else "🩺"
        wd_data  = [[Paragraph(f"{prefix}  {point}", st["Body"])]]
        wd_tbl   = Table(wd_data, colWidths=[17*cm])
        wd_tbl.setStyle(TableStyle([
            ("BACKGROUND",  (0,0),(-1,-1), color_bg),
            ("TOPPADDING",  (0,0),(-1,-1), 5),
            ("BOTTOMPADDING",(0,0),(-1,-1), 5),
            ("LEFTPADDING", (0,0),(-1,-1), 12),
        ]))
        story.append(wd_tbl)
        story.append(Spacer(1, 0.1*cm))

    story.append(Spacer(1, 0.4*cm))

    # ── Disclaimer ────────────────────────────────────────────────────────
    disc_data = [[Paragraph(
        "⚠️  MEDICAL DISCLAIMER: This clinical report is generated by an AI system "
        "for educational and informational purposes ONLY. It is NOT a substitute for "
        "professional medical advice, diagnosis, or treatment by a qualified licensed "
        "healthcare professional. Always consult your doctor. In emergencies, call 108.",
        st["Warn"]
    )]]
    disc_tbl = Table(disc_data, colWidths=[17*cm])
    disc_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(-1,-1), colors.HexColor("#fff8e1")),
        ("BOX",         (0,0),(-1,-1), 1, ORANGE),
        ("TOPPADDING",  (0,0),(-1,-1), 10),
        ("BOTTOMPADDING",(0,0),(-1,-1), 10),
        ("LEFTPADDING", (0,0),(-1,-1), 12),
        ("RIGHTPADDING",(0,0),(-1,-1), 12),
    ]))
    story.append(disc_tbl)

    # ── Footer ─────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.3*cm))
    footer_data = [[
        Paragraph("MediSense Pro v1.0", st["Small"]),
        Paragraph("VIT Capstone | SWE1904 | R.Divya 21MIS0261", st["Small"]),
        Paragraph(f"Generated: {now}", st["Small"]),
    ]]
    footer_tbl = Table(footer_data, colWidths=[5*cm, 8*cm, 4*cm])
    footer_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(-1,-1), colors.HexColor("#e8eaf6")),
        ("TOPPADDING",  (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING", (0,0),(-1,-1), 8),
        ("TEXTCOLOR",   (0,0),(-1,-1), GREY),
    ]))
    story.append(footer_tbl)

    doc.build(story)
    buffer.seek(0)
    return buffer
