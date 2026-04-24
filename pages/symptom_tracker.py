"""
Feature 1: Symptom Progression Tracker
Patient logs symptoms daily. System draws progression line showing
if condition is improving, worsening, or stable over 7 days.
"""
import streamlit as st
from datetime import datetime, timedelta
from utils.database import (init_symptom_tracker, log_symptom_entry,
                             get_symptom_logs, get_tracker_names)

SEV_LABELS = {1:"Very Mild",2:"Mild",3:"Mild-Moderate",4:"Moderate",
              5:"Moderate",6:"Moderate-Severe",7:"Severe",8:"Severe",9:"Very Severe",10:"Critical"}
SEV_COLORS = {1:"#43a047",2:"#43a047",3:"#66bb6a",4:"#fb8c00",5:"#fb8c00",
              6:"#ef6c00",7:"#e53935",8:"#e53935",9:"#b71c1c",10:"#b71c1c"}

def _sparkline_progression(days, scores, temps, pulses):
    """SVG multi-line progression chart."""
    if len(scores) < 1:
        return ""
    w, h, pad = 560, 120, 20
    max_s = 10; min_s = 0
    max_t = max(t for t in temps if t>0) if any(t>0 for t in temps) else 104
    min_t = min(t for t in temps if t>0) if any(t>0 for t in temps) else 97

    n = len(days)
    if n == 1:
        # Single point
        return f"""<svg width="100%" viewBox="0 0 {w} {h+30}">
            <text x="{w//2}" y="{h//2}" text-anchor="middle" font-size="13" fill="#888">
                Only 1 entry — add more days to see trend
            </text></svg>"""

    def px(i): return pad + i*(w-2*pad)/(n-1)
    def py_score(v): return h - pad - (v-min_s)/(max_s-min_s+0.01)*(h-2*pad)
    def py_temp(v): return h - pad - (v-min_t)/(max_t-min_t+0.01)*(h-2*pad)

    # Severity line
    sev_path = " ".join(f"{'M' if i==0 else 'L'}{px(i):.0f},{py_score(s):.0f}"
                        for i,s in enumerate(scores))
    # Temp line
    valid_temps = [(i,t) for i,t in enumerate(temps) if t > 0]
    temp_path = " ".join(f"{'M' if j==0 else 'L'}{px(i):.0f},{py_temp(t):.0f}"
                         for j,(i,t) in enumerate(valid_temps))

    # Points & labels
    pts = ""
    for i,(d,s) in enumerate(zip(days,scores)):
        c = SEV_COLORS.get(s,"#1565c0")
        pts += f'<circle cx="{px(i):.0f}" cy="{py_score(s):.0f}" r="6" fill="{c}" stroke="white" stroke-width="2"/>'
        pts += f'<text x="{px(i):.0f}" y="{py_score(s)-10:.0f}" text-anchor="middle" font-size="10" fill="{c}" font-weight="bold">{s}</text>'
        pts += f'<text x="{px(i):.0f}" y="{h+15}" text-anchor="middle" font-size="9" fill="#999">D{d}</text>'

    # Trend arrow
    if len(scores) >= 2:
        trend = scores[-1] - scores[0]
        trend_txt = "📈 Worsening" if trend > 1 else ("📉 Improving ✅" if trend < -1 else "➡️ Stable")
        trend_col = "#e53935" if trend > 1 else ("#43a047" if trend < -1 else "#fb8c00")
    else:
        trend_txt, trend_col = "—", "#888"

    return f"""
    <div style="background:#f8f9fa;border-radius:12px;padding:16px;border:1px solid #e0e0e0">
        <div style="display:flex;justify-content:space-between;margin-bottom:8px">
            <span style="font-size:13px;font-weight:600;color:#333">Severity Score (1–10)</span>
            <span style="font-size:13px;font-weight:700;color:{trend_col}">{trend_txt}</span>
        </div>
        <svg width="100%" viewBox="0 0 {w} {h+24}" style="overflow:visible">
            <defs>
                <linearGradient id="sevGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#e53935" stop-opacity="0.15"/>
                    <stop offset="100%" stop-color="#e53935" stop-opacity="0.01"/>
                </linearGradient>
            </defs>
            <!-- Grid lines -->
            {" ".join(f'<line x1="{pad}" y1="{py_score(v):.0f}" x2="{w-pad}" y2="{py_score(v):.0f}" stroke="#eee" stroke-width="1"/><text x="{pad-4}" y="{py_score(v)+4:.0f}" text-anchor="end" font-size="9" fill="#ccc">{v}</text>' for v in [2,4,6,8,10])}
            <!-- Severity path -->
            <path d="{sev_path}" fill="none" stroke="#e53935" stroke-width="2.5"
                stroke-linecap="round" stroke-linejoin="round"/>
            <!-- Temp path -->
            {"" if not temp_path else f'<path d="{temp_path}" fill="none" stroke="#1565c0" stroke-width="1.5" stroke-dasharray="4,3" stroke-linecap="round"/>'}
            {pts}
        </svg>
        <div style="font-size:11px;color:#aaa;margin-top:4px">
            <span style="color:#e53935">─── Severity score</span>
            &nbsp;&nbsp;
            <span style="color:#1565c0">- - - Temperature (°F)</span>
        </div>
    </div>"""

def show():
    init_symptom_tracker()
    uid = st.session_state.user_id

    st.markdown("""<div class="main-header">
        <h1>📅 Symptom Progression Tracker</h1>
        <p>Log your symptoms daily — see if your condition is improving, worsening, or stable</p>
    </div>""", unsafe_allow_html=True)

    st.markdown("""<div style="background:#e8f5e9;border-left:5px solid #43a047;border-radius:10px;
        padding:12px 18px;font-size:14px;margin-bottom:16px">
        💡 <b>How it works:</b> Start a new tracker for any illness (e.g. "Fever Week 1").
        Log your symptoms each day. The system draws a progression chart showing your recovery trend.
        This is something <b>no other health app does</b> — it tracks you over time, not just once.
    </div>""", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📝 Log Today's Symptoms", "📈 View My Progression Charts"])

    # ── TAB 1: LOG ENTRY ─────────────────────────────────────────────────
    with tab1:
        st.markdown("### 🆕 Start or Continue a Tracker")

        existing = get_tracker_names(uid)
        col_new, col_exist = st.columns(2)

        with col_new:
            st.markdown("**Create new tracker:**")
            new_name = st.text_input("Illness/condition name",
                                      placeholder="e.g. Fever - March 2026, Cold & Cough")
            use_new = st.button("➕ Start New Tracker", use_container_width=True)

        with col_exist:
            st.markdown("**Continue existing tracker:**")
            if existing:
                sel_existing = st.selectbox("Select tracker", existing)
                use_existing = st.button("📝 Log to This Tracker", use_container_width=True)
            else:
                st.info("No trackers yet — create one on the left.")
                sel_existing = None
                use_existing = False

        # Determine active tracker
        if "active_tracker" not in st.session_state:
            st.session_state.active_tracker = None

        if use_new and new_name.strip():
            st.session_state.active_tracker = new_name.strip()
        elif use_existing and sel_existing:
            st.session_state.active_tracker = sel_existing

        tracker = st.session_state.active_tracker

        if tracker:
            logs = get_symptom_logs(uid, tracker)
            day_num = len(logs) + 1

            st.markdown(f"""<div style="background:#e3f2fd;border-radius:10px;
                padding:12px 18px;border-left:4px solid #1565c0;margin:12px 0;font-size:14px">
                📋 <b>Active Tracker:</b> {tracker} &nbsp;·&nbsp;
                <b>Logging Day {day_num}</b>
                {" (already logged today)" if logs and logs[-1][4]==datetime.now().strftime("%Y-%m-%d") else ""}
            </div>""", unsafe_allow_html=True)

            st.markdown("### 📊 Today's Readings")
            v1, v2 = st.columns(2)
            with v1:
                temp = st.number_input("🌡️ Temperature (°F)", 95.0, 110.0, 98.6, step=0.1)
                temp_note = ("🟢 Normal" if temp<99 else("🟡 Low Fever" if temp<100.4
                              else("🔴 Fever" if temp<103 else "🚨 High Fever")))
                st.caption(temp_note)
                pulse = st.number_input("💓 Pulse (bpm)", 40, 200, 72)
            with v2:
                severity_score = st.slider(
                    "📊 Overall Severity Score",
                    min_value=1, max_value=10, value=5,
                    help="1=Very mild, 5=Moderate, 10=Critical"
                )
                sev_label = SEV_LABELS.get(severity_score,"Moderate")
                sev_color = SEV_COLORS.get(severity_score,"#fb8c00")
                st.markdown(f"""<div style="background:{sev_color};color:white;border-radius:8px;
                    padding:8px 14px;text-align:center;font-weight:700">
                    {severity_score}/10 — {sev_label}
                </div>""", unsafe_allow_html=True)

            st.markdown("### 🤒 Symptoms Today")
            sym_cols = st.columns(4)
            symptom_options = [
                "Fever","Headache","Cough","Sore Throat",
                "Body Ache","Fatigue","Nausea","Vomiting",
                "Diarrhoea","Chills","Runny Nose","Chest Pain",
                "Difficulty Breathing","Dizziness","Loss of Appetite","Other"
            ]
            selected_symptoms = []
            for i, sym in enumerate(symptom_options):
                with sym_cols[i % 4]:
                    if st.checkbox(sym, key=f"sym_{sym}"):
                        selected_symptoms.append(sym)

            notes = st.text_area("📝 Additional notes",
                                  placeholder="Any other observations, medicines taken today...",
                                  height=70)

            if st.button("💾 Save Today's Entry", use_container_width=True):
                symptoms_str = ", ".join(selected_symptoms) if selected_symptoms else "None reported"
                log_symptom_entry(uid, tracker, day_num, temp, pulse,
                                   symptoms_str, severity_score, notes)
                st.success(f"✅ Day {day_num} logged for '{tracker}'!")
                st.balloons()
                st.rerun()

        else:
            st.markdown("""<div style="background:#f8f9fa;border-radius:12px;padding:40px;
                text-align:center;border:2px dashed #e0e0e0">
                <div style="font-size:4em">📅</div>
                <h3 style="color:#888">Select or create a tracker above to begin</h3>
            </div>""", unsafe_allow_html=True)

    # ── TAB 2: PROGRESSION CHARTS ────────────────────────────────────────
    with tab2:
        trackers = get_tracker_names(uid)
        if not trackers:
            st.info("No trackers yet. Go to 'Log Today's Symptoms' to start tracking.")
            return

        selected_tracker = st.selectbox("📋 Select Tracker to View", trackers)
        logs = get_symptom_logs(uid, selected_tracker)

        if not logs:
            st.info("No entries yet for this tracker.")
            return

        st.markdown(f"### 📈 Progression: **{selected_tracker}**")
        st.markdown(f"**{len(logs)} day(s) logged**")

        # Extract data
        days    = [l[3] for l in logs]
        scores  = [l[8] for l in logs]
        temps   = [float(l[5]) if l[5] else 0 for l in logs]
        pulses  = [int(l[6]) if l[6] else 0 for l in logs]

        # Chart
        chart_html = _sparkline_progression(days, scores, temps, pulses)
        st.markdown(chart_html, unsafe_allow_html=True)

        # Trend analysis
        if len(scores) >= 2:
            trend    = scores[-1] - scores[0]
            avg      = sum(scores)/len(scores)
            peak_day = scores.index(max(scores)) + 1
            peak_val = max(scores)

            trend_col = "#e53935" if trend>1 else ("#43a047" if trend<-1 else "#fb8c00")
            trend_txt = "📈 WORSENING — Consider seeing a doctor" if trend>1 \
                   else ("📉 IMPROVING — Keep resting and following care plan" if trend<-1 \
                   else "➡️ STABLE — Monitor for further changes")

            st.markdown(f"""<div style="background:{trend_col}15;border:2px solid {trend_col};
                border-radius:12px;padding:16px 20px;margin:12px 0">
                <h3 style="color:{trend_col};margin:0">{trend_txt}</h3>
                <div style="display:flex;gap:24px;margin-top:12px;font-size:13px">
                    <div><b>Start Score:</b> {scores[0]}/10</div>
                    <div><b>Current Score:</b> {scores[-1]}/10</div>
                    <div><b>Peak:</b> {peak_val}/10 (Day {peak_day})</div>
                    <div><b>Average:</b> {avg:.1f}/10</div>
                </div>
            </div>""", unsafe_allow_html=True)

        # Daily log table
        st.markdown("### 📋 Daily Log")
        for l in logs:
            lid, uid2, tname, day_n, date, temp2, pulse2, syms, sev_sc, notes2, created = l
            sc = SEV_COLORS.get(sev_sc, "#888")
            # Build card using native Streamlit — avoids old Streamlit HTML rendering bug
            with st.container():
                st.markdown(f"""<div style="border-left:5px solid {sc};
                    padding:10px 14px;margin:6px 0;background:white;
                    border-radius:10px;border:1px solid #e0e0e0;
                    box-shadow:0 1px 4px rgba(0,0,0,0.05)">
                    <div style="display:flex;justify-content:space-between;align-items:center">
                        <b style="font-size:14px">Day {day_n} — {date}</b>
                        <span style="background:{sc};color:white;padding:2px 10px;
                            border-radius:12px;font-size:12px;font-weight:700">{sev_sc}/10</span>
                    </div>
                    <p style="margin:6px 0 0;font-size:13px;color:#555">
                        🌡️ {temp2}°F &nbsp;·&nbsp; 💓 {pulse2} bpm &nbsp;·&nbsp; 🤒 {syms or "None"}
                    </p>
                </div>""", unsafe_allow_html=True)
                if notes2:
                    st.caption(f"📝 {notes2}")

        # Doctor recommendation
        if scores and scores[-1] >= 7:
            st.markdown("""<div style="background:#ffebee;border-left:5px solid #e53935;
                border-radius:10px;padding:14px 18px;margin-top:12px">
                🚨 <b>Alert:</b> Your severity score is HIGH. Based on your progression,
                please consult a doctor TODAY. Do not delay further.
            </div>""", unsafe_allow_html=True)
        elif len(scores) >= 5 and scores[-1] >= scores[0]:
            st.markdown("""<div style="background:#fff3e0;border-left:5px solid #fb8c00;
                border-radius:10px;padding:14px 18px;margin-top:12px">
                ⚠️ <b>Note:</b> After 5+ days with no improvement, a doctor consultation
                is strongly recommended.
            </div>""", unsafe_allow_html=True)

    st.markdown("""<div class="footer">
        MediSense Pro · Symptom Tracker · SWE1904 · VIT · R.Divya 21MIS0261
    </div>""", unsafe_allow_html=True)
