"""
Health Analytics — MediSense Pro v13
Simple. Clean. Three sections only.
1. Alerts     — unread notifications first
2. My Journey — how each module's results changed over time
3. Last Checked — how long ago each module was last run
"""
import streamlit as st
from datetime import datetime
from utils.database import get_reports, get_alerts, mark_alerts_read

# All module name variants grouped by display name
MODULE_GROUPS = [
    ("🩸", "Diabetes",
     ["Diabetes Prediction", "Diabetes Home Screening"]),
    ("❤️", "Heart Disease",
     ["Heart Disease", "Heart Disease Home Screening"]),
    ("🧠", "Parkinson's",
     ["Parkinson's Disease", "Parkinson's Symptom Screening",
      "Parkinson's Voice Analysis"]),
    ("🫘", "Kidney",
     ["Kidney Disease Screening", "Kidney Disease Lab Values"]),
    ("🦋", "Thyroid",
     ["Thyroid Screening", "Thyroid TSH Interpretation"]),
    ("🔬", "General",
     ["General Diagnosis"]),
]

SEV_COLOR = {"Severe": "#e53935", "Moderate": "#fb8c00", "Mild": "#43a047"}
SEV_ICON  = {"Severe": "🔴", "Moderate": "🟡", "Mild": "🟢"}
PAGE_KEY  = {
    "Diabetes":     "🩸 Diabetes Prediction",
    "Heart Disease":"❤️ Heart Disease",
    "Parkinson's":  "🧠 Parkinson's Disease",
    "Kidney":       "🫘 Kidney Disease",
    "Thyroid":      "🦋 Thyroid Disorder",
    "General":      "🔬 General Diagnosis",
}


def _days_ago(dt_str):
    try:
        delta = (datetime.now() -
                 datetime.strptime(dt_str, "%Y-%m-%d %H:%M")).days
        if delta == 0:   return "today"
        elif delta == 1: return "yesterday"
        else:            return f"{delta} days ago"
    except:
        return "—"


def _trend_label(results):
    """
    Given list of severities oldest→newest, return trend.
    Severe=3, Moderate=2, Mild=1
    """
    val = {"Severe": 3, "Moderate": 2, "Mild": 1}
    nums = [val.get(r, 0) for r in results if r in val]
    if len(nums) < 2:
        return None, None
    if nums[-1] < nums[0]:
        return "📈 Improving", "#2e7d32"
    elif nums[-1] > nums[0]:
        return "📉 Worsening", "#e53935"
    else:
        return "➡️ Stable", "#fb8c00"


def show():
    uid     = st.session_state.user_id
    uname   = st.session_state.full_name
    reports = get_reports(uid)

    # ── Header ────────────────────────────────────────────────────────
    st.markdown("""<div class="main-header">
        <h1>📈 Health Analytics</h1>
        <p>Your alerts · Your health journey · When you last checked each module</p>
    </div>""", unsafe_allow_html=True)

    if not reports:
        st.markdown("""
        <div style="background:#f8f9fa;border-radius:14px;padding:48px 24px;
            text-align:center;border:1.5px dashed #e0e0e0;margin-top:16px">
            <p style="font-size:2.5em;margin:0">📊</p>
            <p style="font-size:15px;font-weight:700;color:#555;margin:10px 0 4px">
                No data yet
            </p>
            <p style="font-size:13px;color:#aaa;margin:0">
                Run any disease assessment from the sidebar
                to start seeing your health analytics here.
            </p>
        </div>""", unsafe_allow_html=True)
        return

    # ════════════════════════════════════════════════════════════════
    # SECTION 1 — ALERTS
    # ════════════════════════════════════════════════════════════════
    try:
        all_alerts    = get_alerts(uid, unread_only=False)
        unread_alerts = [a for a in all_alerts if not a[4]]
    except:
        all_alerts = unread_alerts = []

    st.markdown("""
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px">
        <div style="width:4px;height:18px;background:#e53935;border-radius:2px"></div>
        <p style="margin:0;font-size:12px;font-weight:700;letter-spacing:0.8px;
            text-transform:uppercase;color:#e53935">Alerts</p>
    </div>""", unsafe_allow_html=True)

    if not all_alerts:
        st.markdown("""
        <div style="background:#f1f8f1;border-radius:10px;padding:14px 18px;
            font-size:13px;color:#2e7d32;border-left:4px solid #2e7d32;
            margin-bottom:20px">
            ✅ No alerts. All your results are being monitored.
        </div>""", unsafe_allow_html=True)
    else:
        if unread_alerts:
            st.markdown(f"""
            <div style="background:#ffebee;border-radius:8px;padding:10px 16px;
                font-size:13px;color:#e53935;font-weight:600;margin-bottom:10px">
                🔔 You have {len(unread_alerts)} unread alert{'s' if len(unread_alerts)!=1 else ''}
            </div>""", unsafe_allow_html=True)
            if st.button("Mark all as read ✓", key="mark_read"):
                try:
                    mark_alerts_read(uid)
                    st.rerun()
                except:
                    pass

        # Show last 5 alerts
        for a in all_alerts[:5]:
            # a = (id, user_id, alert_type, message, is_read, created_at)
            try:
                msg     = a[3]
                is_read = a[4]
                dt      = a[5] if len(a) > 5 else "—"
            except:
                continue

            bg     = "#fff" if is_read else "#fff8f0"
            border = "#e0e0e0" if is_read else "#fb8c00"
            dot    = "" if is_read else """<span style="display:inline-block;
                width:7px;height:7px;background:#fb8c00;border-radius:50%;
                margin-right:6px;vertical-align:middle"></span>"""

            st.markdown(f"""
            <div style="background:{bg};border:1px solid {border};
                border-radius:10px;padding:12px 16px;margin:5px 0;
                box-shadow:0 1px 4px rgba(0,0,0,0.04)">
                <div style="display:flex;justify-content:space-between;
                    align-items:flex-start">
                    <p style="margin:0;font-size:13px;color:#333;line-height:1.5">
                        {dot}{msg}
                    </p>
                    <span style="font-size:11px;color:#ccc;margin-left:16px;
                        flex-shrink:0">{dt}</span>
                </div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<hr style='border:none;border-top:1px solid #f0f0f0;margin:20px 0'>",
                unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════
    # SECTION 2 — MY HEALTH JOURNEY
    # ════════════════════════════════════════════════════════════════
    st.markdown("""
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
        <div style="width:4px;height:18px;background:#1565c0;border-radius:2px"></div>
        <p style="margin:0;font-size:12px;font-weight:700;letter-spacing:0.8px;
            text-transform:uppercase;color:#1565c0">My Health Journey</p>
    </div>
    <p style="font-size:13px;color:#888;margin:0 0 16px">
        How your results have changed over time across each module.
        Seeing a trend is more useful than any single result.
    </p>""", unsafe_allow_html=True)

    # Build per-module history
    journey_found = False
    for icon, name, module_names in MODULE_GROUPS:
        # Get all results for this module, oldest first
        matches = sorted(
            [r for r in reports if r[2] in module_names],
            key=lambda r: r[7] or ""
        )
        if not matches:
            continue

        journey_found = True
        severities = [r[3] for r in matches]
        trend_label, trend_color = _trend_label(severities)

        st.markdown(f"""
        <div style="background:white;border:1px solid #f0f0f0;border-radius:12px;
            padding:16px 18px;margin-bottom:10px;
            box-shadow:0 1px 6px rgba(0,0,0,0.04)">
            <div style="display:flex;justify-content:space-between;
                align-items:center;margin-bottom:10px">
                <div style="display:flex;align-items:center;gap:8px">
                    <span style="font-size:1.4em">{icon}</span>
                    <span style="font-weight:700;font-size:14px;color:#1a1a2e">{name}</span>
                    <span style="font-size:12px;color:#aaa">
                        {len(matches)} check{'s' if len(matches)!=1 else ''}
                    </span>
                </div>
                {f'<span style="background:{trend_color}18;color:{trend_color};font-size:12px;font-weight:700;padding:4px 12px;border-radius:20px">{trend_label}</span>' if trend_label else ''}
            </div>""", unsafe_allow_html=True)

        # Result timeline — dots connected by arrow
        timeline_html = '<div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px">'
        for i, r in enumerate(matches):
            sev  = r[3] or "—"
            dt   = r[7] or ""
            sc   = SEV_COLOR.get(sev, "#888")
            si   = SEV_ICON.get(sev, "⚪")
            # short date
            try:
                short_dt = datetime.strptime(dt, "%Y-%m-%d %H:%M").strftime("%d %b")
            except:
                short_dt = dt[:10]

            timeline_html += f"""
            <div style="text-align:center">
                <div style="background:{sc}15;border:1.5px solid {sc};
                    border-radius:8px;padding:6px 10px;font-size:12px">
                    <span>{si} {sev}</span>
                </div>
                <div style="font-size:10px;color:#bbb;margin-top:3px">{short_dt}</div>
            </div>"""

            if i < len(matches) - 1:
                timeline_html += """<span style="color:#ccc;font-size:16px;
                    margin:0 2px;padding-bottom:14px">→</span>"""

        timeline_html += "</div>"

        # Plain English summary
        if len(matches) == 1:
            sev = matches[0][3]
            summary = f"Checked once — result was <b>{sev}</b>. Run again to see if anything has changed."
        elif trend_label and "Improving" in trend_label:
            summary = f"Your {name} risk has been <b style='color:#2e7d32'>improving</b>. Keep up whatever you are doing."
        elif trend_label and "Worsening" in trend_label:
            summary = f"Your {name} risk has been <b style='color:#e53935'>worsening</b>. Please see a doctor."
        else:
            summary = f"Your {name} risk has been <b style='color:#fb8c00'>stable</b> across {len(matches)} checks."

        st.markdown(f"""
            {timeline_html}
            <p style="margin:10px 0 0;font-size:12px;color:#666;
                line-height:1.5">{summary}</p>
        </div>""", unsafe_allow_html=True)

    if not journey_found:
        st.markdown("""
        <div style="background:#f8f9fa;border-radius:10px;padding:16px 18px;
            font-size:13px;color:#aaa;text-align:center">
            Run each module at least once to see your health journey here.
        </div>""", unsafe_allow_html=True)

    st.markdown("<hr style='border:none;border-top:1px solid #f0f0f0;margin:20px 0'>",
                unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════
    # SECTION 3 — LAST CHECKED
    # ════════════════════════════════════════════════════════════════
    st.markdown("""
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
        <div style="width:4px;height:18px;background:#6a1b9a;border-radius:2px"></div>
        <p style="margin:0;font-size:12px;font-weight:700;letter-spacing:0.8px;
            text-transform:uppercase;color:#6a1b9a">Last Checked</p>
    </div>
    <p style="font-size:13px;color:#888;margin:0 0 16px">
        How long ago you last ran each module.
        Regular checks catch changes early.
    </p>""", unsafe_allow_html=True)

    cols = st.columns(3)
    for i, (icon, name, module_names) in enumerate(MODULE_GROUPS):
        matches = [r for r in reports if r[2] in module_names]

        with cols[i % 3]:
            if matches:
                last   = matches[0]  # newest first
                sev    = last[3]
                dt_str = last[7] or ""
                ago    = _days_ago(dt_str)
                sc     = SEV_COLOR.get(sev, "#888")
                si     = SEV_ICON.get(sev, "⚪")

                # Urgency colour for the card border
                try:
                    days_n = (datetime.now() -
                              datetime.strptime(dt_str, "%Y-%m-%d %H:%M")).days
                except:
                    days_n = 0

                border = ("#e53935" if sev == "Severe" else
                          "#fb8c00" if days_n > 30 else "#e8e8e8")

                st.markdown(f"""
                <div style="background:white;border:1.5px solid {border};
                    border-radius:12px;padding:14px 14px;margin-bottom:10px;
                    box-shadow:0 1px 5px rgba(0,0,0,0.04)">
                    <div style="display:flex;align-items:center;gap:8px;
                        margin-bottom:6px">
                        <span style="font-size:1.3em">{icon}</span>
                        <span style="font-weight:700;font-size:13px;
                            color:#1a1a2e">{name}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;
                        align-items:center">
                        <span style="background:{sc}15;color:{sc};
                            font-size:11px;font-weight:700;padding:2px 8px;
                            border-radius:20px">{si} {sev}</span>
                        <span style="font-size:11px;color:#bbb">{ago}</span>
                    </div>
                    {f'<p style="margin:6px 0 0;font-size:11px;color:#e53935">Checked over 30 days ago — consider re-checking</p>' if days_n > 30 else ''}
                </div>""", unsafe_allow_html=True)

                if st.button(f"Re-check {name}", key=f"rc_{name}",
                             use_container_width=True):
                    st.session_state.page = PAGE_KEY.get(name, "🔬 General Diagnosis")
                    st.rerun()
            else:
                st.markdown(f"""
                <div style="background:#fafafa;border:1.5px dashed #d0d0d0;
                    border-radius:12px;padding:14px 14px;margin-bottom:10px">
                    <div style="display:flex;align-items:center;gap:8px;
                        margin-bottom:6px">
                        <span style="font-size:1.3em;opacity:0.4">{icon}</span>
                        <span style="font-weight:600;font-size:13px;
                            color:#aaa">{name}</span>
                    </div>
                    <p style="margin:0;font-size:11px;color:#ccc">Never checked</p>
                </div>""", unsafe_allow_html=True)

                if st.button(f"Check {name} now", key=f"cn_{name}",
                             use_container_width=True):
                    st.session_state.page = PAGE_KEY.get(name, "🔬 General Diagnosis")
                    st.rerun()

    st.markdown("""<div class="footer">
        MediSense Pro · Health Analytics · SWE1904 · VIT · R.Divya 21MIS0261
    </div>""", unsafe_allow_html=True)
