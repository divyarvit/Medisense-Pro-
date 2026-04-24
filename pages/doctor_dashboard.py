"""
Doctor Dashboard — MediSense Pro
Second login role. Shows all patient assessments sorted by severity.
Panel sees you designed for real clinical deployment, not just one user.
"""
import streamlit as st
from utils.database import get_conn
from datetime import datetime

SEV_COLOR = {"Severe":"#e53935","Moderate":"#fb8c00","Mild":"#43a047"}
SEV_ICON  = {"Severe":"🔴","Moderate":"🟡","Mild":"🟢"}
SEV_ORDER = {"Severe":0,"Moderate":1,"Mild":2}
MODULE_ICONS = {"General Diagnosis":"🔬","Diabetes Prediction":"🩸",
                "Heart Disease":"❤️","Parkinson's Disease":"🧠",
                "BMI Calculator":"⚖️","AI Doctor Chat":"🤖",
                "Visual Symptom Analysis":"📸"}

DEMO_DOCTOR = {"username":"doctor","password":"doc123","name":"Dr. Priya Sharma"}

def get_all_patients_reports():
    conn = get_conn(); c = conn.cursor()
    c.execute("""
        SELECT r.id, u.full_name, u.age, u.gender, u.city,
               r.module, r.severity, r.diagnosis, r.confidence,
               r.full_report, r.created_at, u.id as user_id
        FROM reports r JOIN users u ON r.user_id = u.id
        ORDER BY
            CASE r.severity WHEN 'Severe' THEN 0 WHEN 'Moderate' THEN 1 ELSE 2 END,
            r.created_at DESC
    """)
    rows = c.fetchall(); conn.close(); return rows

def get_patient_history(user_id):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM reports WHERE user_id=? ORDER BY created_at DESC", (user_id,))
    rows = c.fetchall(); conn.close(); return rows

def add_doctor_note(report_id, note):
    conn = get_conn(); c = conn.cursor()
    try:
        c.execute("ALTER TABLE reports ADD COLUMN doctor_note TEXT")
    except: pass
    c.execute("UPDATE reports SET doctor_note=? WHERE id=?", (note, report_id))
    conn.commit(); conn.close()

def show():
    # Doctor login gate
    if not st.session_state.get("doctor_logged_in"):
        st.markdown("""<div class="main-header">
            <h1>👨‍⚕️ Doctor Dashboard</h1>
            <p>Clinical review portal — for healthcare professionals only</p>
        </div>""", unsafe_allow_html=True)

        st.markdown("""<div style="background:#e3f2fd;border-radius:12px;padding:14px 18px;
            border-left:5px solid #1565c0;margin-bottom:20px;font-size:14px">
            🏥 <b>This is the Doctor's View</b> — Doctors log in here to review all patient
            AI assessments, prioritised by severity, and add clinical notes.
            <br><br>Demo credentials: username <code>doctor</code> / password <code>doc123</code>
        </div>""", unsafe_allow_html=True)

        _, col, _ = st.columns([1,1.4,1])
        with col:
            st.markdown("""<div style="background:white;border-radius:14px;padding:28px;
                box-shadow:0 4px 20px rgba(0,0,0,0.1);border-top:4px solid #1565c0">
                <h3 style="color:#1565c0;margin:0 0 16px">👨‍⚕️ Doctor Login</h3>""",
                unsafe_allow_html=True)
            doc_user = st.text_input("👤 Doctor Username", placeholder="doctor")
            doc_pass = st.text_input("🔒 Password", type="password", placeholder="doc123")
            if st.button("🔐 Login as Doctor", use_container_width=True):
                if doc_user == DEMO_DOCTOR["username"] and doc_pass == DEMO_DOCTOR["password"]:
                    st.session_state.doctor_logged_in = True
                    st.session_state.doctor_name = DEMO_DOCTOR["name"]
                    st.rerun()
                else:
                    st.error("❌ Invalid doctor credentials.")
            st.markdown("</div>", unsafe_allow_html=True)
        return

    # ── Doctor is logged in ───────────────────────────────────────────────
    doc_name = st.session_state.get("doctor_name", "Doctor")

    st.markdown(f"""<div class="main-header">
        <h1>👨‍⚕️ Doctor Dashboard</h1>
        <p>Welcome, <b>{doc_name}</b> — Patient queue sorted by severity</p>
    </div>""", unsafe_allow_html=True)

    col_logout, col_time = st.columns([1,4])
    with col_logout:
        if st.button("🚪 Doctor Logout"):
            st.session_state.doctor_logged_in = False
            st.rerun()
    with col_time:
        st.markdown(f"""<div style="background:#f0f4ff;border-radius:8px;padding:8px 14px;
            font-size:13px;color:#555">
            🕐 Dashboard as of {datetime.now().strftime("%d %b %Y, %I:%M %p")}
        </div>""", unsafe_allow_html=True)

    reports = get_all_patients_reports()

    # ── Summary Stats ─────────────────────────────────────────────────────
    total    = len(reports)
    severe   = sum(1 for r in reports if r[6]=="Severe")
    moderate = sum(1 for r in reports if r[6]=="Moderate")
    mild     = sum(1 for r in reports if r[6]=="Mild")
    patients = len(set(r[11] for r in reports))

    c1,c2,c3,c4,c5 = st.columns(5)
    for col, lbl, val, color in [
        (c1,"👥 Total Patients", patients,  "#1565c0"),
        (c2,"📋 Total Reports",  total,     "#6a1b9a"),
        (c3,"🔴 Severe Cases",   severe,    "#e53935"),
        (c4,"🟡 Moderate",       moderate,  "#fb8c00"),
        (c5,"🟢 Mild",           mild,      "#43a047"),
    ]:
        with col:
            st.markdown(f"""<div style="background:white;border-radius:12px;padding:16px;
                text-align:center;box-shadow:0 2px 10px rgba(0,0,0,0.08);
                border-top:4px solid {color}">
                <h2 style="color:{color};margin:4px 0">{val}</h2>
                <p style="margin:0;color:#666;font-size:12px">{lbl}</p>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")

    if not reports:
        st.info("No patient reports yet. Patients need to run assessments first.")
        return

    # ── Filters ───────────────────────────────────────────────────────────
    st.markdown("### 🔍 Filter Patient Queue")
    f1, f2, f3 = st.columns(3)
    with f1:
        sev_filter = st.selectbox("Severity", ["All","Severe","Moderate","Mild"])
    with f2:
        mod_filter = st.selectbox("Module", ["All"] + list(set(r[5] for r in reports)))
    with f3:
        search = st.text_input("🔍 Search patient name", placeholder="Type name...")

    filtered = [r for r in reports
                if (sev_filter=="All" or r[6]==sev_filter)
                and (mod_filter=="All" or r[5]==mod_filter)
                and (not search or search.lower() in (r[1] or "").lower())]

    st.markdown(f"""<div style="background:#e3f2fd;border-radius:8px;padding:9px 16px;
        font-size:13px;border-left:4px solid #1565c0;margin-bottom:8px">
        📊 Showing <b>{len(filtered)}</b> reports · Sorted: Severe → Moderate → Mild
    </div>""", unsafe_allow_html=True)

    # ── Severe Alert Banner ───────────────────────────────────────────────
    severe_cases = [r for r in filtered if r[6]=="Severe"]
    if severe_cases:
        st.markdown(f"""<div style="background:#ffebee;border:2px solid #e53935;
            border-radius:12px;padding:14px 20px;margin:8px 0">
            <b style="color:#e53935">🚨 {len(severe_cases)} SEVERE case{'s' if len(severe_cases)>1 else ''}
            require{'s' if len(severe_cases)==1 else ''} immediate attention!</b>
        </div>""", unsafe_allow_html=True)

    # ── Patient Report Cards ──────────────────────────────────────────────
    st.markdown("### 👥 Patient Queue")

    for r in filtered:
        rid, pname, page, pgender, pcity, module, severity, diagnosis, confidence, full_data, ts, uid = r
        sc   = SEV_COLOR.get(severity,"#888")
        si   = SEV_ICON.get(severity,"⚪")
        icon = MODULE_ICONS.get(module,"📋")

        try: ts_display = datetime.strptime(ts,"%Y-%m-%d %H:%M").strftime("%d %b %Y, %I:%M %p")
        except: ts_display = ts or "—"

        with st.expander(
            f"{si} {severity}  ·  {icon} {module}  ·  {pname or 'Unknown'}  ·  {ts_display}",
            expanded=(severity=="Severe")
        ):
            row1, row2, row3 = st.columns([1.5, 1.5, 1])

            with row1:
                st.markdown(f"""<div style="background:#f0f4ff;border-radius:10px;padding:14px">
                    <p style="margin:0 0 4px;font-size:12px;color:#888;font-weight:600">PATIENT</p>
                    <p style="margin:0;font-size:16px;font-weight:700">👤 {pname or 'Anonymous'}</p>
                    <p style="margin:6px 0 0;font-size:13px;color:#555">
                        🎂 {page or '—'} yrs &nbsp;·&nbsp; ⚤ {pgender or '—'}
                        &nbsp;·&nbsp; 📍 {pcity or '—'}
                    </p>
                    <p style="margin:6px 0 0;font-size:12px;color:#888">🕐 {ts_display}</p>
                </div>""", unsafe_allow_html=True)

            with row2:
                st.markdown(f"""<div style="background:{sc}15;border-left:4px solid {sc};
                    border-radius:10px;padding:14px">
                    <p style="margin:0 0 4px;font-size:12px;color:#888;font-weight:600">AI ASSESSMENT</p>
                    <p style="margin:0;font-size:14px;font-weight:700;color:{sc}">{si} {severity}</p>
                    <p style="margin:6px 0 4px;font-size:12px;color:#888;font-weight:600">MODULE</p>
                    <p style="margin:0;font-size:13px">{icon} {module}</p>
                    <p style="margin:6px 0 4px;font-size:12px;color:#888;font-weight:600">DIAGNOSIS</p>
                    <p style="margin:0;font-size:13px;color:#1565c0;font-weight:600">🔬 {diagnosis[:45]}</p>
                </div>""", unsafe_allow_html=True)

            with row3:
                # Confidence meter
                conf_c = "#43a047" if confidence>=70 else ("#fb8c00" if confidence>=45 else "#e53935")
                st.markdown(f"""<div style="background:white;border-radius:10px;padding:14px;
                    border:1px solid #e0e0e0;text-align:center">
                    <p style="margin:0 0 6px;font-size:12px;color:#888;font-weight:600">AI CONFIDENCE</p>
                    <div style="font-size:2em;font-weight:800;color:{conf_c}">{confidence:.0f}%</div>
                    <div style="background:#eee;border-radius:4px;height:8px;margin:8px 0">
                        <div style="background:{conf_c};width:{confidence:.0f}%;height:8px;border-radius:4px"></div>
                    </div>
                    <p style="margin:0;font-size:11px;color:#aaa">Report #{rid}</p>
                </div>""", unsafe_allow_html=True)

            # Input data
            if full_data:
                st.markdown(f"""<div style="background:#f8f9fa;border-radius:8px;padding:10px 14px;
                    font-size:12px;color:#555;margin-top:8px;border:1px solid #e0e0e0">
                    📝 <b>Input Data:</b> {full_data.replace('|','  ·  ')}
                </div>""", unsafe_allow_html=True)

            # Doctor note area
            st.markdown("<br>", unsafe_allow_html=True)
            note_col, action_col = st.columns([3,1])
            with note_col:
                note = st.text_input(
                    f"📝 Doctor's note for this report",
                    placeholder="e.g. Confirmed diagnosis, prescribed Metformin, follow-up in 2 weeks...",
                    key=f"note_{rid}"
                )
            with action_col:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("💾 Save Note", key=f"save_{rid}", use_container_width=True):
                    if note.strip():
                        add_doctor_note(rid, note.strip())
                        st.success("✅ Note saved!")
                    else:
                        st.warning("Please enter a note first.")

            # Action buttons
            btn1, btn2, btn3 = st.columns(3)
            with btn1:
                st.markdown(f"""<div style="background:#e8f5e9;border-radius:8px;padding:8px;
                    text-align:center;font-size:12px;color:#2e7d32;border:1px solid #a5d6a7">
                    ✅ Mark as Reviewed
                </div>""", unsafe_allow_html=True)
            with btn2:
                st.markdown(f"""<div style="background:#e3f2fd;border-radius:8px;padding:8px;
                    text-align:center;font-size:12px;color:#1565c0;border:1px solid #90caf9">
                    📅 Schedule Follow-up
                </div>""", unsafe_allow_html=True)
            with btn3:
                st.markdown(f"""<div style="background:#fff3e0;border-radius:8px;padding:8px;
                    text-align:center;font-size:12px;color:#e65100;border:1px solid #ffcc02">
                    🚨 Flag as Urgent
                </div>""", unsafe_allow_html=True)

    st.markdown("""<div class="footer">
        MediSense Pro · Doctor Dashboard · SWE1904 · VIT · R.Divya 21MIS0261
    </div>""", unsafe_allow_html=True)
