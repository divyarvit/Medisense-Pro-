"""
Feature 3: Doctor's Prescription Card
A professional referral slip the patient can print and take to a real doctor.
"""
import streamlit as st
from datetime import datetime
from utils.database import get_reports, get_user
from utils.pdf_generator import generate_report_pdf
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO

BLUE   = colors.HexColor("#1565c0")
BLUE_L = colors.HexColor("#e3f2fd")
GREEN  = colors.HexColor("#43a047")
RED    = colors.HexColor("#e53935")
ORANGE = colors.HexColor("#fb8c00")
GREY   = colors.HexColor("#555555")
LGREY  = colors.HexColor("#f8f9fa")
WHITE  = colors.white

SPECIALIST_MAP = {
    "Diabetes Prediction":   ("Endocrinologist / Diabetologist",
                              "HbA1c, Fasting Glucose, Post-meal Glucose, Lipid Profile, Kidney Function Test"),
    "Heart Disease":         ("Cardiologist",
                              "ECG, Echocardiogram, Lipid Profile, Troponin, Chest X-Ray"),
    "Parkinson's Disease":   ("Neurologist",
                              "MRI Brain, DaTscan, Neurological Examination, UPDRS Assessment"),
    "General Diagnosis":     ("General Physician / Internal Medicine",
                              "Tests to be determined by the consulting physician based on clinical examination and presenting symptoms."),
    "AI Doctor Chat":        ("Appropriate Specialist based on symptoms",
                              "As recommended by the consulting doctor"),
    "BMI Calculator":        ("Dietitian / Endocrinologist",
                              "Thyroid Panel (TSH/T3/T4), Fasting Glucose, Lipid Profile"),
}

URGENCY_MAP = {
    "Severe":   ("URGENT — Within 24–48 Hours", RED,    "⚠️ Please prioritise this appointment."),
    "Moderate": ("Soon — Within 1 Week",         ORANGE, "📅 Schedule at earliest convenience."),
    "Mild":     ("Routine — Within 1 Month",     GREEN,  "📋 Routine follow-up recommended."),
}

def _generate_prescription_pdf(patient_name, patient_age, patient_gender,
                                 patient_blood, module, severity, diagnosis,
                                 confidence, symptoms_summary, custom_note):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=1.5*cm, bottomMargin=2*cm)

    def sty(name, **kw):
        return ParagraphStyle(name, **kw)

    story = []
    now   = datetime.now().strftime("%d %B %Y")
    specialist, tests = SPECIALIST_MAP.get(module, ("General Physician","As advised"))
    urgency_txt, urgency_col, urgency_note = URGENCY_MAP.get(severity, URGENCY_MAP["Mild"])

    # ── Letterhead ─────────────────────────────────────────────────────────
    hdr_data = [[
        Paragraph("""<font color="white" size="18"><b>🏥 MediSense Pro</b></font><br/>
                  <font color="white" size="10">AI-Based Clinical Referral Summary</font>""",
                  sty("H", fontName="Helvetica-Bold", fontSize=18,
                      textColor=WHITE, alignment=TA_LEFT, leading=22)),
        Paragraph(f"""<font color="white" size="9">Date: {now}</font><br/>
                  <font color="white" size="9">Ref: MS-{datetime.now().strftime('%Y%m%d%H%M')}</font><br/>
                  <font color="white" size="9">System: MediSense Pro v1.0</font>""",
                  sty("HR", fontName="Helvetica", fontSize=9,
                      textColor=WHITE, alignment=TA_LEFT, leading=14)),
    ]]
    hdr_tbl = Table(hdr_data, colWidths=[11*cm, 6*cm])
    hdr_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), BLUE),
        ("TOPPADDING",   (0,0),(-1,-1), 14),
        ("BOTTOMPADDING",(0,0),(-1,-1), 14),
        ("LEFTPADDING",  (0,0),(-1,-1), 14),
    ]))
    story.append(hdr_tbl)
    story.append(Spacer(1, 0.4*cm))

    # ── Urgency Banner ─────────────────────────────────────────────────────
    urg_data = [[
        Paragraph(f"<b>APPOINTMENT URGENCY: {urgency_txt}</b>",
                  sty("Urg", fontName="Helvetica-Bold", fontSize=11,
                      textColor=WHITE, alignment=TA_CENTER)),
    ]]
    urg_tbl = Table(urg_data, colWidths=[17*cm])
    urg_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), urgency_col),
        ("TOPPADDING",   (0,0),(-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
    ]))
    story.append(urg_tbl)
    story.append(Spacer(1, 0.3*cm))

    # ── Patient Details ────────────────────────────────────────────────────
    story.append(Paragraph("PATIENT INFORMATION", sty("SH", fontName="Helvetica-Bold",
                            fontSize=10, textColor=BLUE, spaceBefore=4)))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE))
    story.append(Spacer(1, 0.15*cm))

    pt_data = [
        [Paragraph("<b>Patient Name:</b>",        sty("L",fontName="Helvetica-Bold",fontSize=10)),
         Paragraph(patient_name,                   sty("V",fontName="Helvetica",fontSize=10)),
         Paragraph("<b>Date of Visit:</b>",        sty("L",fontName="Helvetica-Bold",fontSize=10)),
         Paragraph(now,                            sty("V",fontName="Helvetica",fontSize=10))],
        [Paragraph("<b>Age / Gender:</b>",         sty("L",fontName="Helvetica-Bold",fontSize=10)),
         Paragraph(f"{patient_age} yrs / {patient_gender}", sty("V",fontName="Helvetica",fontSize=10)),
         Paragraph("<b>Blood Group:</b>",          sty("L",fontName="Helvetica-Bold",fontSize=10)),
         Paragraph(patient_blood or "Not recorded",sty("V",fontName="Helvetica",fontSize=10))],
    ]
    pt_tbl = Table(pt_data, colWidths=[4*cm, 5*cm, 4*cm, 4*cm])
    pt_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), LGREY),
        ("TOPPADDING",   (0,0),(-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("LEFTPADDING",  (0,0),(-1,-1), 8),
        ("GRID",         (0,0),(-1,-1), 0.5, colors.HexColor("#e0e0e0")),
    ]))
    story.append(pt_tbl)
    story.append(Spacer(1, 0.3*cm))

    # ── AI Assessment ──────────────────────────────────────────────────────
    story.append(Paragraph("AI CLINICAL ASSESSMENT", sty("SH2", fontName="Helvetica-Bold",
                            fontSize=10, textColor=BLUE, spaceBefore=4)))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE))
    story.append(Spacer(1, 0.15*cm))

    sev_color = {"Severe":RED,"Moderate":ORANGE,"Mild":GREEN}.get(severity, BLUE)
    ai_data = [
        [Paragraph("<b>Presenting Module:</b>",    sty("L",fontName="Helvetica-Bold",fontSize=10)),
         Paragraph(module,                          sty("V",fontName="Helvetica",fontSize=10)),
         Paragraph("<b>AI Confidence:</b>",        sty("L",fontName="Helvetica-Bold",fontSize=10)),
         Paragraph(f"{confidence:.0f}%",           sty("V",fontName="Helvetica",fontSize=10))],
        [Paragraph("<b>Most Likely Diagnosis:</b>",sty("L",fontName="Helvetica-Bold",fontSize=10)),
         Paragraph(f"<b>{diagnosis}</b>",          sty("V",fontName="Helvetica-Bold",fontSize=10,textColor=BLUE)),
         Paragraph("<b>Severity Assessment:</b>",  sty("L",fontName="Helvetica-Bold",fontSize=10)),
         Paragraph(f"<b>{severity}</b>",           sty("V",fontName="Helvetica-Bold",fontSize=10,textColor=sev_color))],
        [Paragraph("<b>Presenting Complaint:</b>", sty("L",fontName="Helvetica-Bold",fontSize=10)),
         Paragraph(symptoms_summary[:120],         sty("V",fontName="Helvetica",fontSize=9)),
         Paragraph("",sty("X",fontName="Helvetica",fontSize=10)),
         Paragraph("",sty("X",fontName="Helvetica",fontSize=10))],
    ]
    ai_tbl = Table(ai_data, colWidths=[4*cm, 5*cm, 4*cm, 4*cm])
    ai_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), colors.HexColor("#e8f0fe")),
        ("BACKGROUND",   (0,2),(1,2),   colors.HexColor("#e8f0fe")),
        ("SPAN",         (1,2),(3,2)),
        ("TOPPADDING",   (0,0),(-1,-1), 7),
        ("BOTTOMPADDING",(0,0),(-1,-1), 7),
        ("LEFTPADDING",  (0,0),(-1,-1), 8),
        ("GRID",         (0,0),(-1,-1), 0.5, colors.HexColor("#bbdefb")),
        ("LINEAFTER",    (0,0),(0,-1),  2, BLUE),
    ]))
    story.append(ai_tbl)
    story.append(Spacer(1, 0.3*cm))

    # ── Referral Note ──────────────────────────────────────────────────────
    story.append(Paragraph("REFERRAL & RECOMMENDATIONS TO DOCTOR", sty("SH3",
                            fontName="Helvetica-Bold", fontSize=10, textColor=BLUE, spaceBefore=4)))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE))
    story.append(Spacer(1, 0.15*cm))

    ref_data = [
        [Paragraph("<b>Refer To:</b>",             sty("L",fontName="Helvetica-Bold",fontSize=10)),
         Paragraph(specialist,                      sty("V",fontName="Helvetica-Bold",fontSize=10,textColor=BLUE))],
        [Paragraph("<b>Suggested Tests:</b>",       sty("L",fontName="Helvetica-Bold",fontSize=10)),
         Paragraph(tests,                           sty("V",fontName="Helvetica",fontSize=10))],
        [Paragraph("<b>AI Note to Doctor:</b>",    sty("L",fontName="Helvetica-Bold",fontSize=10)),
         Paragraph(f"AI system assessment indicates {diagnosis} with {confidence:.0f}% confidence "
                   f"based on {module}. Severity: {severity}. {urgency_note} "
                   f"Patient has been advised to follow up with a qualified specialist for "
                   f"confirmed diagnosis, appropriate investigations, and treatment plan.",
                   sty("V",fontName="Helvetica",fontSize=9))],
    ]
    if custom_note:
        ref_data.append([
            Paragraph("<b>Patient's Note:</b>",    sty("L",fontName="Helvetica-Bold",fontSize=10)),
            Paragraph(custom_note,                  sty("V",fontName="Helvetica",fontSize=9))
        ])

    ref_tbl = Table(ref_data, colWidths=[4*cm, 13*cm])
    ref_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), colors.HexColor("#fff8e1")),
        ("TOPPADDING",   (0,0),(-1,-1), 7),
        ("BOTTOMPADDING",(0,0),(-1,-1), 7),
        ("LEFTPADDING",  (0,0),(-1,-1), 8),
        ("GRID",         (0,0),(-1,-1), 0.5, colors.HexColor("#ffe082")),
        ("LINEAFTER",    (0,0),(0,-1),  2, ORANGE),
        ("VALIGN",       (0,0),(-1,-1), "TOP"),
    ]))
    story.append(ref_tbl)
    story.append(Spacer(1, 0.3*cm))

    # ── Signature Area ─────────────────────────────────────────────────────
    sig_data = [[
        Paragraph("___________________________<br/><font size='9' color='grey'>Doctor's Signature & Stamp</font>",
                  sty("S1",fontName="Helvetica",fontSize=10,alignment=TA_CENTER)),
        Paragraph("___________________________<br/><font size='9' color='grey'>Date of Consultation</font>",
                  sty("S2",fontName="Helvetica",fontSize=10,alignment=TA_CENTER)),
        Paragraph("___________________________<br/><font size='9' color='grey'>Patient's Signature</font>",
                  sty("S3",fontName="Helvetica",fontSize=10,alignment=TA_CENTER)),
    ]]
    sig_tbl = Table(sig_data, colWidths=[5.5*cm, 5.5*cm, 5.5*cm])
    sig_tbl.setStyle(TableStyle([
        ("TOPPADDING",   (0,0),(-1,-1), 20),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("ALIGN",        (0,0),(-1,-1), "CENTER"),
    ]))
    story.append(sig_tbl)
    story.append(Spacer(1, 0.2*cm))

    # ── Disclaimer ─────────────────────────────────────────────────────────
    disc = Paragraph(
        "DISCLAIMER: This referral summary is generated by MediSense Pro AI system for informational "
        "purposes only. It is NOT a prescription or confirmed medical diagnosis. This document is "
        "intended to assist the consulting doctor by summarising the AI assessment. Final diagnosis "
        "and treatment must be determined by a qualified licensed healthcare professional only.",
        sty("D", fontName="Helvetica", fontSize=8, textColor=GREY, alignment=TA_CENTER))
    disc_tbl = Table([[disc]], colWidths=[17*cm])
    disc_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), LGREY),
        ("TOPPADDING",   (0,0),(-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
        ("BOX",          (0,0),(-1,-1), 0.5, colors.HexColor("#e0e0e0")),
    ]))
    story.append(disc_tbl)

    doc.build(story)
    buf.seek(0)
    return buf


def show():
    uid     = st.session_state.user_id
    user    = get_user(uid)
    reports = get_reports(uid)

    st.markdown("""<div class="main-header">
        <h1>🖨️ Doctor's Prescription Card</h1>
        <p>Generate a professional AI referral slip — print it and take it to your real doctor</p>
    </div>""", unsafe_allow_html=True)

    if not reports:
        st.info("Run at least one diagnosis first to generate a prescription card.")
        return

    st.markdown("""<div style="background:#e8f5e9;border-radius:12px;padding:14px 18px;
        border-left:5px solid #43a047;margin-bottom:16px;font-size:14px">
        💡 <b>What is this?</b> This generates a professional one-page referral slip that looks like
        a real doctor's referral note. You can <b>print it and show it to any doctor</b> when you visit —
        it tells them your AI assessment, the specialist you should see, and tests to order.
    </div>""", unsafe_allow_html=True)

    col_form, col_preview = st.columns([1, 1.2])

    with col_form:
        st.markdown("### ⚙️ Prescription Settings")

        # Select report
        report_options = {
            f"{r[2]} — {r[3]} — {r[7]}": r for r in reports
        }
        selected_key = st.selectbox("📋 Select Diagnosis Report", list(report_options.keys()))
        sel_report   = report_options[selected_key]

        # Patient info (pre-filled from profile)
        st.markdown("---")
        st.markdown("**👤 Patient Details**")
        p_name   = st.text_input("Full Name", value=st.session_state.get("full_name",""))
        p_age    = st.text_input("Age", value=str(user[4] or "") if user else "")
        p_gender = st.selectbox("Gender", ["Female","Male","Other"],
                                index=["Female","Male","Other"].index(user[5]) if user and user[5] in ["Female","Male","Other"] else 0)
        p_blood  = st.text_input("Blood Group", value=user[6] or "" if user else "")

        st.markdown("---")
        custom_note = st.text_area("📝 Add a personal note to the doctor (optional)",
                                    placeholder="e.g. I have had this problem for 2 weeks, I am allergic to penicillin...",
                                    height=80)
        generate = st.button("🖨️ Generate Prescription PDF", use_container_width=True)

    with col_preview:
        st.markdown("### 👁️ Preview")

        r = sel_report
        module   = r[2]; severity = r[3]; diagnosis = r[4]
        confidence = float(r[5]) if r[5] else 70
        raw_syms = r[6] or ""
        # Clean up Python list format if present
        if raw_syms.startswith("["):
            import ast
            try:
                syms_list = ast.literal_eval(raw_syms)
                symptoms = ", ".join(str(s).replace("_"," ").title() for s in syms_list)
            except:
                symptoms = raw_syms.replace("[","").replace("]","").replace("'","").replace('"',"")
        elif "|" in raw_syms:
            # Format: Symptoms:['x','y']|Temp:100|Pulse:90
            parts = raw_syms.split("|")
            clean_parts = []
            for p in parts:
                if "Symptoms" in p:
                    sym_part = p.replace("Symptoms:","").replace("[","").replace("]","").replace("'","")
                    sym_part = "Symptoms: " + sym_part.replace("_"," ").title()
                    clean_parts.append(sym_part)
                elif "Temp" in p:
                    clean_parts.append(p.replace("Temp","Temperature"))
                elif "Pulse" in p:
                    clean_parts.append(p)
                else:
                    clean_parts.append(p)
            symptoms = " · ".join(clean_parts)
        else:
            symptoms = raw_syms or "Symptoms as assessed by AI system"

        specialist, tests = SPECIALIST_MAP.get(module, ("General Physician","As advised"))
        urgency_txt, _, urgency_note = URGENCY_MAP.get(severity, URGENCY_MAP["Mild"])
        sev_c = {"Severe":"#e53935","Moderate":"#fb8c00","Mild":"#43a047"}.get(severity,"#888")

        # Header banner
        st.markdown(f"""<div style="border:2px solid #1565c0;border-radius:10px;overflow:hidden;margin-bottom:8px">
            <div style="background:#1565c0;padding:12px 16px;color:white">
                <b>🏥 MediSense Pro</b>
                <span style="float:right;font-size:11px;opacity:0.8">{datetime.now().strftime("%d %b %Y")}</span>
                <br><span style="font-size:11px;opacity:0.75">AI Clinical Referral Summary</span>
            </div>
            <div style="background:{sev_c};padding:7px 16px;color:white;font-weight:700;font-size:12px">
                ⚡ {urgency_txt}
            </div>
        </div>""", unsafe_allow_html=True)

        # Patient info cards
        pr1, pr2 = st.columns(2)
        with pr1:
            st.markdown(f"""<div style="background:#f8f9fa;border-radius:8px;padding:10px 12px;font-size:12px;margin-bottom:6px">
                <span style="color:#888">Patient</span><br><b>{p_name or "—"}</b>
            </div>""", unsafe_allow_html=True)
        with pr2:
            st.markdown(f"""<div style="background:#f8f9fa;border-radius:8px;padding:10px 12px;font-size:12px;margin-bottom:6px">
                <span style="color:#888">Age / Gender</span><br><b>{p_age or "—"} yrs / {p_gender}</b>
            </div>""", unsafe_allow_html=True)

        pr3, pr4 = st.columns(2)
        with pr3:
            st.markdown(f"""<div style="background:#f8f9fa;border-radius:8px;padding:10px 12px;font-size:12px;margin-bottom:6px">
                <span style="color:#888">Module</span><br><b>{module}</b>
            </div>""", unsafe_allow_html=True)
        with pr4:
            st.markdown(f"""<div style="background:#f8f9fa;border-radius:8px;padding:10px 12px;font-size:12px;margin-bottom:6px">
                <span style="color:#888">AI Confidence</span><br><b style="color:{sev_c}">{confidence:.0f}%</b>
            </div>""", unsafe_allow_html=True)

        # Diagnosis
        st.markdown(f"""<div style="background:#e3f2fd;border-radius:8px;padding:12px 14px;
            border-left:4px solid #1565c0;font-size:13px;margin-bottom:6px">
            <span style="color:#888;font-size:10px;text-transform:uppercase">Primary Diagnosis</span><br>
            <b style="color:#1565c0;font-size:14px">{diagnosis}</b>
            <span style="color:#666;font-size:11px;margin-left:8px">· {severity}</span>
        </div>""", unsafe_allow_html=True)

        # Refer to
        st.markdown(f"""<div style="background:#f8f9fa;border-radius:8px;padding:10px 14px;font-size:12px;margin-bottom:6px">
            <span style="color:#888">Refer To</span><br><b>{specialist}</b>
        </div>""", unsafe_allow_html=True)

        # Tests
        st.markdown(f"""<div style="background:#fff3e0;border-radius:8px;padding:12px 14px;
            border-left:4px solid #fb8c00;font-size:12px;margin-bottom:6px">
            <span style="color:#888;font-size:10px;text-transform:uppercase">Recommended Investigations</span><br>
            <span style="color:#555;line-height:1.7">{tests}</span>
        </div>""", unsafe_allow_html=True)

        st.caption("⚠️ Final investigations to be decided by the consulting doctor after examination.")



        if generate:
            try:
                pdf_buf = _generate_prescription_pdf(
                    patient_name     = p_name,
                    patient_age      = p_age,
                    patient_gender   = p_gender,
                    patient_blood    = p_blood,
                    module           = module,
                    severity         = severity,
                    diagnosis        = diagnosis,
                    confidence       = confidence,
                    symptoms_summary = symptoms,
                    custom_note      = custom_note,
                )
                st.download_button(
                    label    = "⬇️ Download Prescription PDF",
                    data     = pdf_buf,
                    file_name= f"MediSense_Prescription_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime     = "application/pdf",
                    use_container_width=True,
                )
                st.success("✅ Prescription PDF ready! Click above to download.")
                st.balloons()
            except Exception as e:
                st.error(f"PDF error: {e}")

    st.markdown("""<div class="footer">
        MediSense Pro · Doctor Prescription Card · SWE1904 · VIT · R.Divya 21MIS0261
    </div>""", unsafe_allow_html=True)
