import streamlit as st
from utils.database import get_reports
from utils.pdf_generator import generate_report_pdf
from datetime import datetime

MODULE_ICONS = {
    "General Diagnosis":"🔬","Diabetes Prediction":"🩸",
    "Heart Disease":"❤️","Parkinson's Disease":"🧠",
    "BMI Calculator":"⚖️","AI Doctor Chat":"🤖"
}

SEV_COLOR = {"Severe":"#e53935","Moderate":"#fb8c00","Mild":"#43a047"}
SEV_ICON  = {"Severe":"🔴","Moderate":"🟡","Mild":"🟢"}
SEV_BG    = {"Severe":"#ffebee","Moderate":"#fff3e0","Mild":"#e8f5e9"}

def show():
    st.markdown("""<div class="main-header">
        <h1>📋 My Health Reports</h1>
        <p>Complete history of all your consultations and diagnoses</p>
    </div>""", unsafe_allow_html=True)

    uid     = st.session_state.user_id
    reports = get_reports(uid)

    if not reports:
        st.markdown("""<div style="text-align:center;padding:60px 20px">
            <div style="font-size:5em">📋</div>
            <h3 style="color:#888">No reports yet</h3>
            <p style="color:#aaa">Run a diagnosis from the sidebar to generate your first report!</p>
        </div>""", unsafe_allow_html=True)
        return

    # ── Summary Stats ─────────────────────────────────────────────────────
    total    = len(reports)
    severe   = sum(1 for r in reports if r[3]=="Severe")
    moderate = sum(1 for r in reports if r[3]=="Moderate")
    mild     = sum(1 for r in reports if r[3]=="Mild")

    c1,c2,c3,c4 = st.columns(4)
    for col, label, val, color, icon in [
        (c1,"Total Reports",  total,    "#1565c0","📋"),
        (c2,"🔴 Severe",      severe,   "#e53935","🚨"),
        (c3,"🟡 Moderate",    moderate, "#fb8c00","⚠️"),
        (c4,"🟢 Mild",        mild,     "#43a047","✅"),
    ]:
        with col:
            st.markdown(f"""<div style="background:white;border-radius:12px;padding:16px;
                text-align:center;box-shadow:0 2px 10px rgba(0,0,0,0.08);
                border-top:4px solid {color}">
                <h2 style="color:{color};margin:4px 0">{val}</h2>
                <p style="margin:0;color:#666;font-size:12px">{label}</p>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Filters ───────────────────────────────────────────────────────────
    st.markdown("### 🔍 Filter Reports")
    f1,f2,f3 = st.columns([2,2,1])
    with f1:
        mod_opts = ["All Modules"] + sorted(set(r[2] for r in reports))
        mod_filter = st.selectbox("📦 Module", mod_opts)
    with f2:
        sev_filter = st.selectbox("⚡ Severity", ["All Severities","Severe","Moderate","Mild"])
    with f3:
        sort_order = st.selectbox("🔃 Sort", ["Newest First","Oldest First"])

    filtered = [r for r in reports
                if (mod_filter=="All Modules" or r[2]==mod_filter)
                and (sev_filter=="All Severities" or r[3]==sev_filter)]

    if sort_order=="Oldest First":
        filtered = list(reversed(filtered))

    st.markdown(f"""<div style="background:#e3f2fd;border-radius:8px;padding:10px 16px;
        margin:8px 0;font-size:14px;border-left:4px solid #1565c0">
        📊 Showing <b>{len(filtered)}</b> of <b>{total}</b> total reports
    </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Report Cards ──────────────────────────────────────────────────────
    for i, r in enumerate(filtered):
        rid, uid_r, module, severity, diagnosis, confidence, full_data, timestamp = r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]
        sc   = SEV_COLOR.get(severity,"#888")
        si   = SEV_ICON.get(severity,"⚪")
        sbg  = SEV_BG.get(severity,"#f5f5f5")
        icon = MODULE_ICONS.get(module,"📋")

        # Try to parse timestamp nicely
        try:
            dt  = datetime.strptime(timestamp, "%Y-%m-%d %H:%M")
            ts_display = dt.strftime("%d %b %Y · %I:%M %p")
        except:
            ts_display = timestamp or "—"

        with st.expander(
            f"{icon}  {module}  ·  {si} {severity}  ·  {diagnosis[:45]}  ·  {ts_display}",
            expanded=(i==0)
        ):
            row1, row2, row3 = st.columns([1.5, 1.5, 1])

            with row1:
                st.markdown(f"""<div style="background:#f8f9fa;border-radius:10px;padding:14px">
                    <p style="margin:0 0 6px;font-size:12px;color:#888;font-weight:600">MODULE</p>
                    <p style="margin:0;font-size:15px;font-weight:700">{icon} {module}</p>
                    <p style="margin:8px 0 6px;font-size:12px;color:#888;font-weight:600">DATE & TIME</p>
                    <p style="margin:0;font-size:14px">📅 {ts_display}</p>
                </div>""", unsafe_allow_html=True)

            with row2:
                st.markdown(f"""<div style="background:{sbg};border-radius:10px;padding:14px;
                    border-left:4px solid {sc}">
                    <p style="margin:0 0 6px;font-size:12px;color:#888;font-weight:600">SEVERITY</p>
                    <p style="margin:0;font-size:16px;font-weight:700;color:{sc}">{si} {severity}</p>
                    <p style="margin:8px 0 6px;font-size:12px;color:#888;font-weight:600">CONFIDENCE</p>
                    <div style="background:#e0e0e0;border-radius:4px;height:8px;margin-bottom:4px">
                        <div style="background:{sc};width:{confidence:.0f}%;height:8px;border-radius:4px"></div>
                    </div>
                    <p style="margin:0;font-size:13px;color:{sc};font-weight:600">{confidence:.0f}%</p>
                </div>""", unsafe_allow_html=True)

            with row3:
                st.markdown(f"""<div style="background:#e8f0fe;border-radius:10px;padding:14px;
                    border-left:4px solid #1565c0;height:100%">
                    <p style="margin:0 0 6px;font-size:12px;color:#888;font-weight:600">TOP DIAGNOSIS</p>
                    <p style="margin:0;font-size:13px;font-weight:700;color:#1565c0;line-height:1.4">
                        🔬 {diagnosis}</p>
                </div>""", unsafe_allow_html=True)

            # Input data (if saved)
            if full_data:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("**📝 Input Data Recorded:**")
                st.markdown(f"""<div style="background:#f8f9fa;border-radius:8px;padding:12px 16px;
                    font-size:13px;color:#555;font-family:monospace;border:1px solid #e0e0e0">
                    {full_data.replace('|','  ·  ')}
                </div>""", unsafe_allow_html=True)

            # PDF Download button
            st.markdown("<br>", unsafe_allow_html=True)
            col_dl, col_del = st.columns([3,1])

            with col_dl:
                try:
                    pdf_buf = generate_report_pdf(
                        module_name        = module,
                        patient_name       = st.session_state.get("full_name","Patient"),
                        patient_info       = full_data or "",
                        severity           = severity,
                        severity_explanation = f"Severity assessed as {severity} based on clinical data.",
                        conditions         = [{"condition": diagnosis,
                                               "probability": confidence,
                                               "description": f"Top diagnosis from {module} assessment.",
                                               "icd": "—"}],
                        confidence         = confidence,
                        do_list            = ["Follow up with your doctor for confirmed diagnosis.",
                                              "Monitor your symptoms carefully.",
                                              "Maintain a healthy diet and stay hydrated.",
                                              "Keep this report for your doctor's reference."],
                        dont_list          = ["Do NOT self-medicate based on this report alone.",
                                              "Do NOT ignore worsening symptoms.",
                                              "Do NOT skip prescribed medications."],
                        home_care          = ["Rest adequately and stay hydrated.",
                                              "Monitor your symptoms and note any changes.",
                                              "Follow up with a qualified healthcare professional."],
                        when_doctor        = ["Symptoms worsen or new symptoms appear.",
                                              "You want a confirmed diagnosis with lab tests.",
                                              "Any doubt about your health condition."],
                        summary            = f"Report generated by MediSense Pro AI System on {ts_display}. Top diagnosis: {diagnosis}.",
                    )
                    st.download_button(
                        label    = "📄  Download PDF Report",
                        data     = pdf_buf,
                        file_name= f"MediSense_{module.replace(' ','_')}_{timestamp[:10] if timestamp else 'report'}.pdf",
                        mime     = "application/pdf",
                        key      = f"pdf_{rid}",
                        use_container_width = True,
                    )
                except Exception as e:
                    st.warning(f"PDF generation issue: {e}")

            with col_del:
                st.markdown(f"""<div style="background:#f8f9fa;border-radius:8px;
                    padding:8px;text-align:center;font-size:12px;color:#aaa">
                    Report #{rid}
                </div>""", unsafe_allow_html=True)

    # ── Export All ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📤 Export All Reports")

    export_col1, export_col2 = st.columns(2)
    with export_col1:
        # CSV export
        import io
        csv_lines = ["Module,Severity,Diagnosis,Confidence,Date"]
        for r in reports:
            csv_lines.append(f'"{r[2]}","{r[3]}","{r[4]}","{r[5]:.0f}%","{r[7]}"')
        csv_data = "\n".join(csv_lines)
        st.download_button(
            label    = "📊  Download All as CSV",
            data     = csv_data.encode("utf-8"),
            file_name= f"MediSense_AllReports_{datetime.now().strftime('%Y%m%d')}.csv",
            mime     = "text/csv",
            use_container_width=True,
        )
        st.caption("CSV file — open in Excel or Google Sheets")

    with export_col2:
        st.markdown(f"""<div style="background:#e3f2fd;border-radius:10px;
            padding:14px;text-align:center;font-size:13px;border:1px solid #bbdefb">
            💡 <b>Tip:</b> Use individual <b>Download PDF</b> buttons above
            for full clinical reports with all sections.
        </div>""", unsafe_allow_html=True)

    st.markdown("""<div class="footer">
        MediSense Pro v1.0 · SWE1904 Capstone · VIT · R.Divya 21MIS0261
    </div>""", unsafe_allow_html=True)
