"""
Dashboard — MediSense Pro v13
Clean, beautiful, instantly understandable.
Story told top to bottom:
  1. One-line health summary
  2. Needs Attention  (Severe/High)
  3. Looking Good     (Mild/Moderate)
  4. Not Checked Yet  (gaps)
  5. What to do next  (1-2 smart actions)
  6. Recent activity  (last 4)
"""
import streamlit as st
from utils.database import get_reports, get_user
from datetime import datetime

DISEASE_MODULES = [
    ("🩸", "Diabetes",       ["Diabetes Prediction", "Diabetes Home Screening"]),
    ("❤️", "Heart Disease",  ["Heart Disease", "Heart Disease Home Screening"]),
    ("🧠", "Parkinson's",    ["Parkinson's Disease", "Parkinson's Symptom Screening",
                               "Parkinson's Voice Analysis"]),
    ("🫘", "Kidney",         ["Kidney Disease Screening", "Kidney Disease Lab Values"]),
    ("🦋", "Thyroid",        ["Thyroid Screening", "Thyroid TSH Interpretation"]),
    ("🔬", "General",        ["General Diagnosis"]),
]

PAGE_KEY = {
    "Diabetes":     "🩸 Diabetes Prediction",
    "Heart Disease":"❤️ Heart Disease",
    "Parkinson's":  "🧠 Parkinson's Disease",
    "Kidney":       "🫘 Kidney Disease",
    "Thyroid":      "🦋 Thyroid Disorder",
    "General":      "🔬 General Diagnosis",
}

MODULE_ICON = {
    "General Diagnosis":             "🔬",
    "Diabetes Prediction":           "🩸",
    "Diabetes Home Screening":       "🩸",
    "Heart Disease":                 "❤️",
    "Heart Disease Home Screening":  "❤️",
    "Parkinson's Disease":           "🧠",
    "Parkinson's Symptom Screening": "🧠",
    "Parkinson's Voice Analysis":    "🧠",
    "Kidney Disease Screening":      "🫘",
    "Kidney Disease Lab Values":     "🫘",
    "Thyroid Screening":             "🦋",
    "Thyroid TSH Interpretation":    "🦋",
}


def _days_ago(dt_str):
    try:
        delta = (datetime.now() - datetime.strptime(dt_str, "%Y-%m-%d %H:%M")).days
        if delta == 0:   return "today"
        elif delta == 1: return "yesterday"
        else:            return f"{delta} days ago"
    except:
        return "—"


def _build_status(reports):
    """Return dict: display_name → result data"""
    status = {}
    for icon, name, module_names in DISEASE_MODULES:
        matches = [r for r in reports if r[2] in module_names]
        if matches:
            r = matches[0]
            status[name] = {
                "icon": icon, "severity": r[3],
                "diagnosis": str(r[4])[:42] if r[4] else "",
                "days_ago": _days_ago(r[7]),
            }
        else:
            status[name] = {"icon": icon, "severity": None}
    return status


def _risk_card(icon, name, severity, diagnosis, days_ago, show_btn=False):
    """Render one disease status card."""
    colors = {
        "Severe":   ("#e53935", "#ffebee", "#ffd7d5"),
        "Moderate": ("#fb8c00", "#fff8f0", "#ffe0b2"),
        "Mild":     ("#2e7d32", "#f1f8f1", "#c8e6c9"),
    }
    labels = {
        "Severe":   "🔴  High Risk",
        "Moderate": "🟡  Moderate",
        "Mild":     "🟢  Low Risk",
    }
    text_c, bg, border = colors.get(severity, ("#888","#f9f9f9","#eee"))
    label = labels.get(severity, severity)

    st.markdown(f"""
    <div style="background:{bg};border:1.5px solid {border};border-radius:14px;
        padding:18px 16px;height:110px;position:relative;
        box-shadow:0 2px 8px rgba(0,0,0,0.05)">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
            <span style="font-size:1.6em;line-height:1">{icon}</span>
            <span style="font-weight:700;font-size:14px;color:#1a1a2e">{name}</span>
            <span style="margin-left:auto;background:white;color:{text_c};
                font-size:11px;font-weight:700;padding:3px 10px;
                border-radius:20px;border:1px solid {border};white-space:nowrap">
                {label}
            </span>
        </div>
        <p style="margin:0;font-size:12px;color:#666;line-height:1.4">{diagnosis}</p>
        <p style="margin:4px 0 0;font-size:11px;color:#aaa">Checked {days_ago}</p>
    </div>""", unsafe_allow_html=True)
    if show_btn:
        if st.button(f"Re-check →", key=f"recheck_{name}", use_container_width=True):
            st.session_state.page = PAGE_KEY.get(name, "🔬 General Diagnosis")
            st.rerun()


def _empty_card(icon, name):
    """Render a not-checked card."""
    st.markdown(f"""
    <div style="background:#fafafa;border:1.5px dashed #d0d0d0;border-radius:14px;
        padding:18px 16px;height:110px">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
            <span style="font-size:1.6em;line-height:1;opacity:0.4">{icon}</span>
            <span style="font-weight:600;font-size:14px;color:#aaa">{name}</span>
            <span style="margin-left:auto;background:#f0f0f0;color:#bbb;
                font-size:11px;font-weight:600;padding:3px 10px;
                border-radius:20px;white-space:nowrap">
                Not checked
            </span>
        </div>
        <p style="margin:0;font-size:12px;color:#ccc">Run an assessment to see your risk level</p>
    </div>""", unsafe_allow_html=True)
    if st.button(f"Check now →", key=f"check_{name}", use_container_width=True):
        st.session_state.page = PAGE_KEY.get(name, "🔬 General Diagnosis")
        st.rerun()


def show():
    uid     = st.session_state.user_id
    uname   = st.session_state.full_name
    reports = get_reports(uid)
    status  = _build_status(reports)

    hour  = datetime.now().hour
    greet = "Good Morning" if hour < 12 else ("Good Afternoon" if hour < 17 else "Good Evening")

    # ── Greeting ──────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="padding:20px 0 4px">
        <h2 style="margin:0;font-size:1.7em;color:#1a1a2e;font-weight:800;
            letter-spacing:-0.3px">{greet}, {uname} 👋</h2>
    </div>""", unsafe_allow_html=True)

    # ── One-line health summary ───────────────────────────────────────
    checked   = [n for n,d in status.items() if d["severity"] is not None]
    unchecked = [n for n,d in status.items() if d["severity"] is None]
    severe_l  = [n for n,d in status.items() if d["severity"] == "Severe"]
    moderate_l= [n for n,d in status.items() if d["severity"] == "Moderate"]
    clear_l   = [n for n,d in status.items() if d["severity"] == "Mild"]

    if not reports:
        summary_bg, summary_icon, summary_msg = (
            "#e3f2fd", "👋",
            "Welcome! You haven't run any health assessments yet. Pick a module below to get started."
        )
    elif severe_l:
        names = " and ".join(severe_l)
        summary_bg, summary_icon, summary_msg = (
            "#ffebee", "🔴",
            f"<b>{names}</b> {'show' if len(severe_l)>1 else 'shows'} High Risk. "
            f"Please see a doctor and take your report with you."
        )
    elif moderate_l:
        names = " and ".join(moderate_l)
        summary_bg, summary_icon, summary_msg = (
            "#fff8f0", "🟡",
            f"<b>{names}</b> {'show' if len(moderate_l)>1 else 'shows'} Moderate Risk. "
            f"Monitor regularly and consider a doctor visit."
        )
    else:
        summary_bg, summary_icon, summary_msg = (
            "#f1f8f1", "✅",
            f"All {len(checked)} checked module{'s are' if len(checked)!=1 else ' is'} showing Low Risk. "
            f"Keep up your healthy habits."
        )

    st.markdown(f"""
    <div style="background:{summary_bg};border-radius:12px;padding:14px 20px;
        margin:8px 0 20px;display:flex;align-items:center;gap:12px">
        <span style="font-size:1.5em">{summary_icon}</span>
        <p style="margin:0;font-size:14px;color:#333;line-height:1.5">{summary_msg}</p>
    </div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════
    # SECTION A — NEEDS ATTENTION  (Severe only)
    # ════════════════════════════════════════════════════════════════
    if severe_l:
        st.markdown("""
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
            <div style="width:4px;height:18px;background:#e53935;border-radius:2px"></div>
            <p style="margin:0;font-size:12px;font-weight:700;letter-spacing:0.8px;
                text-transform:uppercase;color:#e53935">Needs Attention</p>
        </div>""", unsafe_allow_html=True)

        cols = st.columns(min(len(severe_l), 3))
        for col, name in zip(cols, severe_l):
            d = status[name]
            with col:
                _risk_card(d["icon"], name, d["severity"],
                           d["diagnosis"], d["days_ago"], show_btn=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════
    # SECTION B — MODERATE RISK
    # ════════════════════════════════════════════════════════════════
    if moderate_l:
        st.markdown("""
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
            <div style="width:4px;height:18px;background:#fb8c00;border-radius:2px"></div>
            <p style="margin:0;font-size:12px;font-weight:700;letter-spacing:0.8px;
                text-transform:uppercase;color:#fb8c00">Monitor Closely</p>
        </div>""", unsafe_allow_html=True)

        cols = st.columns(min(len(moderate_l), 3))
        for col, name in zip(cols, moderate_l):
            d = status[name]
            with col:
                _risk_card(d["icon"], name, d["severity"],
                           d["diagnosis"], d["days_ago"], show_btn=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════
    # SECTION C — LOOKING GOOD
    # ════════════════════════════════════════════════════════════════
    if clear_l:
        st.markdown("""
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
            <div style="width:4px;height:18px;background:#2e7d32;border-radius:2px"></div>
            <p style="margin:0;font-size:12px;font-weight:700;letter-spacing:0.8px;
                text-transform:uppercase;color:#2e7d32">Looking Good</p>
        </div>""", unsafe_allow_html=True)

        cols = st.columns(min(len(clear_l), 3))
        for col, name in zip(cols, clear_l):
            d = status[name]
            with col:
                _risk_card(d["icon"], name, d["severity"],
                           d["diagnosis"], d["days_ago"])
        st.markdown("<br>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════
    # SECTION D — NOT CHECKED YET
    # ════════════════════════════════════════════════════════════════
    if unchecked:
        st.markdown("""
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
            <div style="width:4px;height:18px;background:#bbb;border-radius:2px"></div>
            <p style="margin:0;font-size:12px;font-weight:700;letter-spacing:0.8px;
                text-transform:uppercase;color:#aaa">Not Checked Yet</p>
        </div>""", unsafe_allow_html=True)

        cols = st.columns(min(len(unchecked), 3))
        for col, name in zip(cols, unchecked):
            d = status[name]
            with col:
                _empty_card(d["icon"], name)
        st.markdown("<br>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════
    # SECTION E — WHAT TO DO NEXT
    # ════════════════════════════════════════════════════════════════
    if reports:
        st.markdown("<hr style='border:none;border-top:1px solid #f0f0f0;margin:8px 0 20px'>",
                    unsafe_allow_html=True)
        st.markdown("""
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px">
            <div style="width:4px;height:18px;background:#1565c0;border-radius:2px"></div>
            <p style="margin:0;font-size:12px;font-weight:700;letter-spacing:0.8px;
                text-transform:uppercase;color:#1565c0">What To Do Next</p>
        </div>""", unsafe_allow_html=True)

        actions = []

        # Severe → download report + see doctor
        for name in severe_l[:1]:
            d = status[name]
            actions.append({
                "icon": "🔴",
                "bg": "#ffebee", "border": "#e53935",
                "text": f"<b>{name}</b> is High Risk ({d['days_ago']}). "
                        "Download your report from <b>My Reports</b> "
                        "and take it to a doctor.",
                "btn": "📋 Go to My Reports",
                "page": "📋 My Reports",
            })

        # Kidney never checked but diabetes/heart is severe/moderate
        dm_sev = status.get("Diabetes", {}).get("severity")
        hd_sev = status.get("Heart Disease", {}).get("severity")
        if "Kidney" in unchecked and dm_sev in ["Severe", "Moderate"]:
            actions.append({
                "icon": "💡",
                "bg": "#e3f2fd", "border": "#1565c0",
                "text": "You have a <b>Diabetes</b> risk. "
                        "Kidney disease is directly caused by uncontrolled diabetes — "
                        "you have never screened your kidneys.",
                "btn": "🫘 Check Kidney Now",
                "page": "🫘 Kidney Disease",
            })
        elif "Thyroid" in unchecked and len(checked) >= 2:
            actions.append({
                "icon": "💡",
                "bg": "#f3e5f5", "border": "#6a1b9a",
                "text": "You have never screened for <b>Thyroid</b> disorder. "
                        "It is the easiest check — no devices needed, "
                        "just answer a few questions.",
                "btn": "🦋 Check Thyroid Now",
                "page": "🦋 Thyroid Disorder",
            })

        # Moderate older than 14 days
        if not actions or len(actions) < 2:
            for name in moderate_l:
                d = status[name]
                try:
                    days = int(d["days_ago"].replace(" days ago","")) \
                           if "days ago" in str(d["days_ago"]) else 0
                except:
                    days = 0
                if days >= 14:
                    pg = PAGE_KEY.get(name, "🔬 General Diagnosis")
                    btn_label = name[:12]
                    actions.append({
                        "icon": "🟡",
                        "bg": "#fff8f0", "border": "#fb8c00",
                        "text": f"<b>{name}</b> was Moderate Risk — last checked "
                                f"{d['days_ago']}. Time to re-assess.",
                        "btn": f"Re-check {btn_label}",
                        "page": pg,
                    })
                    break

        # All clear
        if not actions:
            st.markdown("""
            <div style="background:#f1f8f1;border-radius:12px;padding:16px 20px;
                display:flex;align-items:center;gap:14px">
                <span style="font-size:1.8em">✅</span>
                <div>
                    <p style="margin:0;font-weight:700;font-size:14px;color:#2e7d32">
                        No urgent actions right now
                    </p>
                    <p style="margin:4px 0 0;font-size:13px;color:#555">
                        Your results are looking good. Keep tracking regularly
                        and check any unchecked modules above.
                    </p>
                </div>
            </div>""", unsafe_allow_html=True)
        else:
            for a in actions[:2]:
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(f"""
                    <div style="background:{a['bg']};border-left:4px solid {a['border']};
                        border-radius:10px;padding:14px 18px;margin-bottom:8px">
                        <p style="margin:0;font-size:13px;color:#333;line-height:1.6">
                            {a['icon']}&nbsp; {a['text']}
                        </p>
                    </div>""", unsafe_allow_html=True)
                with c2:
                    st.markdown("<div style='padding-top:8px'>", unsafe_allow_html=True)
                    btn_key = "act_" + a["page"].replace(" ","_")[:20]
                    if st.button(a["btn"], key=btn_key, use_container_width=True):
                        st.session_state.page = a["page"]
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════
    # SECTION F — RECENT ACTIVITY
    # ════════════════════════════════════════════════════════════════
    if reports:
        st.markdown("<hr style='border:none;border-top:1px solid #f0f0f0;margin:20px 0 16px'>",
                    unsafe_allow_html=True)
        st.markdown("""
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px">
            <div style="width:4px;height:18px;background:#555;border-radius:2px"></div>
            <p style="margin:0;font-size:12px;font-weight:700;letter-spacing:0.8px;
                text-transform:uppercase;color:#888">Recent Activity</p>
        </div>""", unsafe_allow_html=True)

        sev_colors = {"Severe":"#e53935","Moderate":"#fb8c00","Mild":"#43a047"}
        sev_icons  = {"Severe":"🔴","Moderate":"🟡","Mild":"🟢"}

        for r in reports[:4]:
            mod  = r[2] or "—"
            sev  = r[3] or "—"
            diag = str(r[4])[:50] if r[4] else "—"
            dt   = r[7] or "—"
            ico  = MODULE_ICON.get(mod, "📋")
            sc   = sev_colors.get(sev, "#888")
            si   = sev_icons.get(sev, "⚪")

            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;
                padding:12px 16px;margin:4px 0;background:white;border-radius:10px;
                border:1px solid #f0f0f0;box-shadow:0 1px 4px rgba(0,0,0,0.04)">
                <div style="display:flex;align-items:center;gap:12px">
                    <span style="font-size:1.3em">{ico}</span>
                    <div>
                        <p style="margin:0;font-size:13px;font-weight:600;
                            color:#1a1a2e">{mod}</p>
                        <p style="margin:2px 0 0;font-size:11px;color:#aaa">{diag}</p>
                    </div>
                </div>
                <div style="text-align:right;flex-shrink:0;margin-left:16px">
                    <span style="background:{sc}18;color:{sc};font-size:11px;
                        font-weight:700;padding:3px 10px;border-radius:20px">
                        {si} {sev}
                    </span>
                    <p style="margin:4px 0 0;font-size:10px;color:#ccc">{dt}</p>
                </div>
            </div>""", unsafe_allow_html=True)

        if len(reports) > 4:
            col_a, col_b, col_c = st.columns([1,1,1])
            with col_b:
                if st.button("View all reports →", key="all_rpts"):
                    st.session_state.page = "📋 My Reports"
                    st.rerun()

    # Zero reports state
    elif not reports:
        st.markdown("""
        <div style="background:#f8f9fa;border-radius:14px;padding:40px 24px;
            text-align:center;border:1.5px dashed #e0e0e0;margin-top:8px">
            <p style="font-size:2.5em;margin:0">🏥</p>
            <p style="font-size:15px;font-weight:700;color:#555;margin:10px 0 4px">
                No assessments yet
            </p>
            <p style="font-size:13px;color:#aaa;margin:0">
                Pick any disease module from the sidebar to run your first health check.
            </p>
        </div>""", unsafe_allow_html=True)

    st.markdown("""<div class="footer">
        MediSense Pro · SWE1904 · VIT · R.Divya 21MIS0261 ·
        ⚠️ For educational purposes only
    </div>""", unsafe_allow_html=True)
