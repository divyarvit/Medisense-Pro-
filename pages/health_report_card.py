"""
Feature 3: Weekly / Monthly Health Report Card
Auto-generates a summary PDF of all health activity.
Like a school report card — but for your health.
"""
import streamlit as st
from utils.database import get_conn
from datetime import datetime, timedelta
import io

def get_period_reports(user_id, days=7):
    conn = get_conn(); c = conn.cursor()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    c.execute("""SELECT module,severity,diagnosis,confidence,created_at,numeric_value
                 FROM reports WHERE user_id=? AND created_at >= ?
                 ORDER BY created_at DESC""", (user_id, since))
    rows = c.fetchall(); conn.close(); return rows

def get_all_reports(user_id):
    conn = get_conn(); c = conn.cursor()
    c.execute("""SELECT module,severity,diagnosis,confidence,created_at,numeric_value
                 FROM reports WHERE user_id=?
                 ORDER BY created_at DESC""", (user_id,))
    rows = c.fetchall(); conn.close(); return rows

def _compute_grade(reports):
    if not reports: return "N/A", "#888"
    sev_map = {"Mild":1,"Moderate":2,"Severe":3}
    avg = sum(sev_map.get(r[1],1) for r in reports) / len(reports)
    if avg <= 1.2: return "A — Excellent", "#43a047"
    if avg <= 1.8: return "B — Good",      "#66bb6a"
    if avg <= 2.2: return "C — Moderate",  "#fb8c00"
    return "D — Needs Attention", "#e53935"

def _trend_vs_prev(curr_reports, prev_reports):
    if not curr_reports or not prev_reports: return "—", "#888"
    sev_map = {"Mild":1,"Moderate":2,"Severe":3}
    curr_avg = sum(sev_map.get(r[1],1) for r in curr_reports)/len(curr_reports)
    prev_avg = sum(sev_map.get(r[1],1) for r in prev_reports)/len(prev_reports)
    diff = curr_avg - prev_avg
    if diff < -0.3: return "📉 Improving vs previous period",  "#43a047"
    if diff >  0.3: return "📈 Worsening vs previous period",   "#e53935"
    return "➡️ Stable vs previous period", "#fb8c00"

def _generate_pdf(user_id, period_label, reports, grade, grade_color, tips, uname, period_days):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                         Table, TableStyle, HRFlowable)
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
                                  leftMargin=2*cm, rightMargin=2*cm,
                                  topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story  = []

        BLUE  = colors.HexColor("#1565c0")
        GREEN = colors.HexColor(grade_color if grade_color.startswith("#") else "#43a047")
        LIGHT = colors.HexColor("#e3f2fd")
        GRAY  = colors.HexColor("#666666")

        H1 = ParagraphStyle("H1", parent=styles["Normal"], fontSize=20,
                              fontName="Helvetica-Bold", textColor=BLUE,
                              alignment=TA_CENTER, spaceAfter=4)
        H2 = ParagraphStyle("H2", parent=styles["Normal"], fontSize=13,
                              fontName="Helvetica-Bold", textColor=BLUE, spaceAfter=4)
        BODY = ParagraphStyle("BODY", parent=styles["Normal"], fontSize=10,
                                textColor=colors.HexColor("#333"), spaceAfter=3)
        SMALL = ParagraphStyle("SMALL", parent=styles["Normal"], fontSize=8,
                                 textColor=GRAY, spaceAfter=2)
        CTR = ParagraphStyle("CTR", parent=styles["Normal"], fontSize=10,
                               alignment=TA_CENTER, spaceAfter=2)

        # Header
        story += [
            Paragraph("MediSense Pro", H1),
            Paragraph(f"Health Report Card — {period_label}", ParagraphStyle(
                "sub", parent=styles["Normal"], fontSize=13,
                textColor=GRAY, alignment=TA_CENTER, spaceAfter=2)),
            Paragraph(f"Patient: {uname}  ·  Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}",
                       ParagraphStyle("meta", parent=styles["Normal"], fontSize=9,
                                       textColor=GRAY, alignment=TA_CENTER)),
            HRFlowable(width="100%", thickness=2, color=BLUE, spaceAfter=12),
        ]

        # Overall Grade
        grade_tbl = Table([[Paragraph("OVERALL HEALTH GRADE", SMALL),
                             Paragraph(grade, ParagraphStyle("G", parent=styles["Normal"],
                                 fontSize=16, fontName="Helvetica-Bold",
                                 textColor=colors.HexColor(grade_color),
                                 alignment=TA_CENTER))]],
                           colWidths=[8*cm, 8*cm])
        grade_tbl.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(0,0), LIGHT),
            ("BACKGROUND",(1,0),(1,0), colors.HexColor(grade_color+"22")),
            ("BOX",(0,0),(-1,-1), 1, BLUE),
            ("INNERGRID",(0,0),(-1,-1), 0.5, colors.white),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),10),
            ("BOTTOMPADDING",(0,0),(-1,-1),10),
        ]))
        story += [grade_tbl, Spacer(1,14)]

        # Summary stats
        total   = len(reports)
        severe  = sum(1 for r in reports if r[1]=="Severe")
        mod     = sum(1 for r in reports if r[1]=="Moderate")
        mild    = sum(1 for r in reports if r[1]=="Mild")
        modules = list(set(r[0] for r in reports))

        stats_data = [
            ["Total Assessments", "Severe Alerts", "Moderate", "Mild / Clear"],
            [str(total), str(severe), str(mod), str(mild)],
        ]
        stats_tbl = Table(stats_data, colWidths=[4*cm]*4)
        stats_tbl.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0), BLUE),
            ("TEXTCOLOR",(0,0),(-1,0), colors.white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
            ("FONTSIZE",(0,0),(-1,-1),10),
            ("ALIGN",(0,0),(-1,-1),"CENTER"),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),8),
            ("BOTTOMPADDING",(0,0),(-1,-1),8),
            ("BACKGROUND",(1,1),(1,1), colors.HexColor("#ffebee")),
            ("BOX",(0,0),(-1,-1),1,BLUE),
            ("INNERGRID",(0,0),(-1,-1),0.5,colors.HexColor("#e0e0e0")),
        ]))
        story += [Paragraph("Period Summary", H2), stats_tbl, Spacer(1,12)]

        # Detailed reports table
        story.append(Paragraph("Assessments This Period", H2))
        tbl_data = [["Date","Module","Diagnosis","Severity","Confidence"]]
        for r in reports[:15]:
            module, severity, diagnosis, conf, ts, nv = r
            try: ts_fmt = datetime.strptime(ts,"%Y-%m-%d %H:%M").strftime("%d %b")
            except: ts_fmt = ts[:10]
            tbl_data.append([ts_fmt, module[:18], diagnosis[:28], severity, f"{conf:.0f}%"])

        rep_tbl = Table(tbl_data, colWidths=[2*cm, 4*cm, 6*cm, 2.5*cm, 2*cm])
        ts_style = [
            ("BACKGROUND",(0,0),(-1,0), BLUE),
            ("TEXTCOLOR",(0,0),(-1,0), colors.white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
            ("FONTSIZE",(0,0),(-1,-1),8),
            ("ALIGN",(0,0),(-1,-1),"CENTER"),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),5),
            ("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, colors.HexColor("#f5f5f5")]),
            ("BOX",(0,0),(-1,-1),1,BLUE),
            ("INNERGRID",(0,0),(-1,-1),0.3,colors.HexColor("#e0e0e0")),
        ]
        for i,r in enumerate(reports[:15],start=1):
            sev = r[1]
            if sev=="Severe":   ts_style.append(("BACKGROUND",(3,i),(3,i),colors.HexColor("#ffebee")))
            elif sev=="Moderate":ts_style.append(("BACKGROUND",(3,i),(3,i),colors.HexColor("#fff3e0")))
            else:               ts_style.append(("BACKGROUND",(3,i),(3,i),colors.HexColor("#e8f5e9")))
        rep_tbl.setStyle(TableStyle(ts_style))
        story += [rep_tbl, Spacer(1,14)]

        # Health tips
        story.append(Paragraph("Personalised Health Tips for Next Period", H2))
        for tip in tips:
            story.append(Paragraph(f"✔ {tip}", BODY))
        story.append(Spacer(1,14))

        # Disclaimer
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e0e0e0")))
        story.append(Paragraph(
            "⚠ This report is generated by MediSense Pro AI and is for informational purposes only. "
            "It is not a medical certificate or clinical diagnosis. Always consult a qualified doctor.",
            ParagraphStyle("disc", parent=styles["Normal"], fontSize=7, textColor=GRAY)))
        story.append(Paragraph("MediSense Pro · SWE1904 · VIT · R.Divya 21MIS0261",
                                 ParagraphStyle("ft", parent=styles["Normal"], fontSize=7,
                                                 textColor=GRAY, alignment=TA_CENTER)))

        doc.build(story)
        buf.seek(0)
        return buf.read()
    except Exception as e:
        return None

def show():
    uid   = st.session_state.user_id
    uname = st.session_state.get("full_name","Patient")

    st.markdown("""<div class="main-header">
        <h1>📊 Health Report Card</h1>
        <p>Your personalised weekly/monthly health summary — download as PDF to show your doctor</p>
    </div>""", unsafe_allow_html=True)

    st.markdown("""<div style="background:#e8f5e9;border-left:5px solid #43a047;
        border-radius:10px;padding:12px 18px;font-size:14px;margin-bottom:16px">
        📋 <b>What is this?</b> Like a school report card — but for your health.
        Every week or month, MediSense auto-summarises all your tests, assigns a health grade,
        shows your trend vs last period, and gives personalised tips. Download as PDF to share
        with your doctor at your next visit.
    </div>""", unsafe_allow_html=True)

    # Period selector
    c1, c2 = st.columns([2,3])
    with c1:
        period = st.selectbox("📅 Report Period",
                               ["Last 7 Days","Last 14 Days","Last 30 Days","All Time"])
    period_map = {"Last 7 Days":7,"Last 14 Days":14,"Last 30 Days":30,"All Time":3650}
    days = period_map[period]

    curr_reports = get_period_reports(uid, days)
    prev_reports = get_period_reports(uid, days*2)
    prev_reports = [r for r in prev_reports if r not in curr_reports]
    all_reports  = get_all_reports(uid)

    if not curr_reports:
        st.info(f"No health assessments in the {period.lower()}. Run some tests first!")
        return

    grade, grade_color = _compute_grade(curr_reports)
    trend_txt, trend_col = _trend_vs_prev(curr_reports, prev_reports)

    # ── HEADER CARDS ─────────────────────────────────────────────────────
    sev_cnt = {"Severe":0,"Moderate":0,"Mild":0}
    for r in curr_reports:
        sev_cnt[r[1]] = sev_cnt.get(r[1],0)+1

    c1,c2,c3,c4,c5 = st.columns(5)
    for col, label, val, color in [
        (c1, "📋 Tests Done",      len(curr_reports),        "#1565c0"),
        (c2, "🏆 Health Grade",    grade.split("—")[0].strip(),"#6a1b9a"),
        (c3, "🔴 Severe Alerts",   sev_cnt["Severe"],         "#e53935"),
        (c4, "🟡 Moderate",        sev_cnt["Moderate"],       "#fb8c00"),
        (c5, "🟢 Mild / Clear",    sev_cnt["Mild"],           "#43a047"),
    ]:
        with col:
            st.markdown(f"""<div style="background:white;border-radius:12px;padding:16px;
                text-align:center;box-shadow:0 2px 10px rgba(0,0,0,0.08);
                border-top:4px solid {color}">
                <h2 style="color:{color};margin:4px 0">{val}</h2>
                <p style="margin:0;color:#666;font-size:11px">{label}</p>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── GRADE CARD ────────────────────────────────────────────────────────
    st.markdown(f"""<div style="background:linear-gradient(135deg,{grade_color},{grade_color}cc);
        color:white;border-radius:18px;padding:24px 32px;margin:12px 0;
        display:flex;justify-content:space-between;align-items:center">
        <div>
            <h2 style="margin:0;font-size:1.1em;opacity:0.9">OVERALL HEALTH GRADE</h2>
            <h1 style="margin:8px 0 0;font-size:2.2em">{grade}</h1>
            <p style="margin:6px 0 0;opacity:0.85;font-size:14px">
                Based on {len(curr_reports)} assessments · {period}
            </p>
        </div>
        <div style="font-size:5em;opacity:0.3">🏆</div>
    </div>""", unsafe_allow_html=True)

    # Trend vs last period
    st.markdown(f"""<div style="background:{trend_col}15;border-left:5px solid {trend_col};
        border-radius:10px;padding:12px 18px;font-size:14px;margin:8px 0">
        {trend_txt}
        {f" · Based on {len(prev_reports)} reports in previous period" if prev_reports else ""}
    </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── MODULE BREAKDOWN ──────────────────────────────────────────────────
    st.markdown("### 📊 Module-by-Module Breakdown")
    modules = {}
    for r in curr_reports:
        m = r[0]
        if m not in modules: modules[m]= []
        modules[m].append(r)

    mc = st.columns(min(len(modules),3))
    for i,(mod, reps) in enumerate(modules.items()):
        g, gc = _compute_grade(reps)
        last_sev = reps[0][1]
        sc = {"Severe":"#e53935","Moderate":"#fb8c00","Mild":"#43a047"}.get(last_sev,"#888")
        with mc[i % 3]:
            st.markdown(f"""<div style="background:white;border-radius:12px;padding:14px;
                border-left:5px solid {sc};box-shadow:0 2px 8px rgba(0,0,0,0.07);margin-bottom:8px">
                <b style="font-size:13px">{mod}</b><br>
                <span style="font-size:11px;color:#888">{len(reps)} test(s)</span>
                <span style="float:right;background:{sc};color:white;padding:1px 8px;
                    border-radius:10px;font-size:11px">{last_sev}</span><br>
                <span style="font-size:12px;color:{gc}">Grade: {g.split('—')[0].strip()}</span>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── PERSONALISED TIPS ─────────────────────────────────────────────────
    st.markdown("### 💡 Personalised Tips for Next Period")
    tips = _generate_tips(curr_reports)
    for tip in tips:
        st.markdown(f"""<div style="background:#e8f5e9;border-left:4px solid #43a047;
            border-radius:8px;padding:9px 14px;margin:5px 0;font-size:13px">
            ✔️ {tip}
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── PDF DOWNLOAD ──────────────────────────────────────────────────────
    st.markdown("### 📥 Download Your Report Card")
    st.markdown("""<div style="background:#e3f2fd;border-radius:10px;padding:12px 16px;
        font-size:13px;border-left:4px solid #1565c0;margin-bottom:12px">
        📄 Download this as a professional PDF to show your doctor at your next visit.
        It includes all assessments, your health grade, trends, and personalised recommendations.
    </div>""", unsafe_allow_html=True)

    period_label = f"{period} · {datetime.now().strftime('%B %Y')}"
    pdf_bytes = _generate_pdf(uid, period_label, curr_reports, grade,
                               grade_color, tips, uname, days)
    if pdf_bytes:
        st.download_button(
            label="📥 Download Health Report Card (PDF)",
            data=pdf_bytes,
            file_name=f"MediSense_HealthReport_{uname.replace(' ','_')}_{datetime.now().strftime('%d%b%Y')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    else:
        st.warning("PDF generation requires reportlab. Run: python -m pip install reportlab")

    st.markdown("""<div class="footer">
        MediSense Pro · Health Report Card · SWE1904 · VIT · R.Divya 21MIS0261
    </div>""", unsafe_allow_html=True)

def _generate_tips(reports):
    tips = []
    sevs = [r[1] for r in reports]
    mods = [r[0] for r in reports]
    if "Severe" in sevs:
        tips.append("You had severe alerts this period — please ensure you have seen a specialist and are on treatment.")
    if "Diabetes Prediction" in mods:
        tips.append("Monitor your fasting blood sugar every morning. Target: below 100 mg/dL.")
    if "Heart Disease" in mods:
        tips.append("Do 30 minutes of cardio exercise (walking/cycling) at least 5 days this week.")
    if "Parkinson's Disease" in mods:
        tips.append("Practice voice exercises and balance training daily. Consult a neurologist if not already done.")
    if "BMI Calculator" in mods:
        tips.append("Focus on portion control — replace refined carbs with whole grains and vegetables.")
    if not tips:
        tips = [
            "Continue your current health routine — your parameters look good.",
            "Stay hydrated — drink at least 8 glasses of water daily.",
            "Sleep 7-8 hours every night — it directly impacts all health markers.",
            "Annual full-body health checkup recommended for preventive care.",
        ]
    tips.append("Share this report card with your doctor at your next visit for contextual guidance.")
    return tips[:6]
