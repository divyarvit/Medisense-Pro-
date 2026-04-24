"""
Feature 2: Family Health Vault
One account manages the whole family.
Add members, run assessments for them, view their history.
India-specific: one smartphone serves the whole family.
"""
import streamlit as st
from utils.database import (get_family_members, add_family_member,
                             delete_family_member, get_conn)
from datetime import datetime

RELATIONS = ["Self","Father","Mother","Spouse","Son","Daughter",
             "Brother","Sister","Grandfather","Grandmother","Other"]
BLOOD_GROUPS = ["A+","A-","B+","B-","O+","O-","AB+","AB-","Unknown"]

RISK_COLORS = {"Severe":"#e53935","Moderate":"#fb8c00","Mild":"#43a047","None":"#9e9e9e"}
RISK_ICONS  = {"Severe":"🔴","Moderate":"🟡","Mild":"🟢","None":"⚪"}

def get_member_reports(owner_id, member_name):
    conn = get_conn(); c = conn.cursor()
    try:
        c.execute("""SELECT module,severity,diagnosis,confidence,created_at
                     FROM reports WHERE user_id=? AND family_member_name=?
                     ORDER BY created_at DESC LIMIT 10""",
                  (owner_id, member_name))
    except:
        return []
    rows = c.fetchall(); conn.close(); return rows

def get_member_last_risk(owner_id, member_name):
    reports = get_member_reports(owner_id, member_name)
    if not reports: return "None"
    sevs = [r[1] for r in reports]
    if "Severe"   in sevs: return "Severe"
    if "Moderate" in sevs: return "Moderate"
    return "Mild"

def show():
    uid   = st.session_state.user_id
    uname = st.session_state.get("full_name","User")

    st.markdown("""<div class="main-header">
        <h1>👨‍👩‍👧 Family Health Vault</h1>
        <p>Manage your entire family's health from one account — India's real health challenge solved</p>
    </div>""", unsafe_allow_html=True)

    st.markdown("""<div style="background:#e8f5e9;border-left:5px solid #43a047;
        border-radius:10px;padding:12px 18px;font-size:14px;margin-bottom:16px">
        🇮🇳 <b>Built for India:</b> In most Indian families, one person manages everyone's health.
        Add your family members here, run health assessments for them, and track everyone's
        history in one place — on one phone.
    </div>""", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["👨‍👩‍👧 Family Members", "➕ Add New Member"])

    # ── TAB 1: VIEW FAMILY ───────────────────────────────────────────────
    with tab1:
        members = get_family_members(uid)

        if not members:
            st.markdown("""<div style="background:#f8f9fa;border-radius:14px;padding:48px;
                text-align:center;border:2px dashed #e0e0e0">
                <div style="font-size:4em">👨‍👩‍👧</div>
                <h3 style="color:#888">No family members added yet</h3>
                <p style="color:#aaa">Go to "Add New Member" tab to add your family</p>
            </div>""", unsafe_allow_html=True)

        st.markdown(f"### 👥 Your Family ({len(members)} members)")

        # Family overview grid
        cols = st.columns([1, 1, 1])
        for i, m in enumerate(members):
            mid, owner, name, relation, age, gender, blood, conditions, created = m
            last_risk = get_member_last_risk(uid, name)
            rc = RISK_COLORS.get(last_risk, "#9e9e9e")
            ri = RISK_ICONS.get(last_risk, "⚪")
            gender_icon = "👨" if gender=="Male" else ("👩" if gender=="Female" else "🧑")

            with cols[i % 3]:
                st.markdown(f"""<div style="background:white;border-radius:14px;padding:18px;
                    box-shadow:0 2px 12px rgba(0,0,0,0.08);border-top:4px solid {rc};
                    text-align:center;margin-bottom:8px">
                    <div style="font-size:2.5em">{gender_icon}</div>
                    <h3 style="margin:4px 0;color:#1a1a2e">{name}</h3>
                    <p style="margin:0;color:#888;font-size:13px">
                        {relation} · {age} yrs · {blood}
                    </p>
                    <div style="margin:10px 0">
                        <span style="background:{rc};color:white;padding:3px 12px;
                            border-radius:12px;font-size:12px">
                            {ri} Last Risk: {last_risk}
                        </span>
                    </div>
                    {f'<p style="font-size:11px;color:#aaa;margin:0">Known: {conditions[:40]}</p>' if conditions else ""}
                </div>""", unsafe_allow_html=True)

        st.markdown("---")

        # Detailed view per member
        st.markdown("### 📋 Detailed Health History")
        member_names = [m[2] for m in members]
        sel_name = st.selectbox("Select family member", member_names)
        sel_member = next((m for m in members if m[2]==sel_name), None)

        if sel_member:
            mid, owner, name, relation, age, gender, blood, conditions, created = sel_member
            last_risk = get_member_last_risk(uid, name)
            rc = RISK_COLORS.get(last_risk,"#9e9e9e")

            # Member info card
            c1, c2, c3 = st.columns(3)
            for col, label, val in [
                (c1, "👤 Name",       f"{name} ({relation})"),
                (c2, "🎂 Age / Gender", f"{age} yrs · {gender}"),
                (c3, "🩸 Blood Group", blood),
            ]:
                with col:
                    st.markdown(f"""<div style="background:#f0f4ff;border-radius:10px;
                        padding:12px 16px;text-align:center">
                        <p style="margin:0;font-size:11px;color:#888">{label}</p>
                        <p style="margin:4px 0;font-weight:700;font-size:14px">{val}</p>
                    </div>""", unsafe_allow_html=True)

            if conditions:
                st.markdown(f"""<div style="background:#fff3e0;border-left:4px solid #fb8c00;
                    border-radius:8px;padding:10px 14px;font-size:13px;margin:8px 0">
                    ⚕️ <b>Known Conditions:</b> {conditions}
                </div>""", unsafe_allow_html=True)

            # Reports for this member
            reports = get_member_reports(uid, name)
            if reports:
                st.markdown(f"#### 📊 Health Reports for {name}")
                for r in reports:
                    module, severity, diagnosis, conf, ts = r
                    sc = RISK_COLORS.get(severity,"#888")
                    si = RISK_ICONS.get(severity,"⚪")
                    try: ts_fmt = datetime.strptime(ts,"%Y-%m-%d %H:%M").strftime("%d %b %Y")
                    except: ts_fmt = ts
                    st.markdown(f"""<div style="background:white;border-left:5px solid {sc};
                        border-radius:10px;padding:11px 16px;margin:5px 0;
                        box-shadow:0 1px 5px rgba(0,0,0,0.06)">
                        <div style="display:flex;justify-content:space-between;align-items:center">
                            <div>
                                <b style="font-size:14px">{diagnosis}</b><br>
                                <span style="font-size:12px;color:#888">{module} · {ts_fmt}</span>
                            </div>
                            <span style="background:{sc};color:white;padding:3px 10px;
                                border-radius:12px;font-size:12px">{si} {severity}</span>
                        </div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.info(f"No health assessments recorded for {name} yet.")

            # Run assessment for this member
            st.markdown(f"#### 🔬 Run Assessment for {name}")
            st.markdown(f"""<div style="background:#e3f2fd;border-radius:10px;padding:12px 16px;
                font-size:13px;border-left:4px solid #1565c0">
                💡 To run an assessment for <b>{name}</b>, go to any diagnosis module
                (General, Diabetes, Heart, etc.). At the top, select
                <b>"{name}"</b> as the patient — the result will be saved
                under their profile here.
            </div>""", unsafe_allow_html=True)

            # Delete member
            if st.button(f"🗑️ Remove {name} from Family Vault",
                          key=f"del_{mid}"):
                delete_family_member(mid)
                st.success(f"✅ {name} removed.")
                st.rerun()

    # ── TAB 2: ADD MEMBER ─────────────────────────────────────────────────
    with tab2:
        st.markdown("### ➕ Add a Family Member")

        a1, a2 = st.columns(2)
        with a1:
            m_name     = st.text_input("👤 Full Name", placeholder="e.g. Rajesh Kumar")
            m_relation = st.selectbox("🔗 Relation", RELATIONS)
            m_age      = st.number_input("🎂 Age", 0, 120, 45)
        with a2:
            m_gender   = st.selectbox("⚤ Gender", ["Male","Female","Other"])
            m_blood    = st.selectbox("🩸 Blood Group", BLOOD_GROUPS)
            m_cond     = st.text_input("⚕️ Known Conditions (optional)",
                                        placeholder="e.g. Hypertension, Asthma")

        st.markdown("""<div style="background:#f8f9fa;border-radius:8px;padding:10px 14px;
            font-size:12px;color:#888;margin-bottom:12px">
            🔒 All family health data is stored securely on your device only.
            Only you can see your family's health information.
        </div>""", unsafe_allow_html=True)

        if st.button("✅ Add to Family Vault", use_container_width=True):
            if m_name.strip():
                add_family_member(uid, m_name.strip(), m_relation,
                                   m_age, m_gender, m_blood, m_cond)
                st.success(f"✅ {m_name} added to your Family Health Vault!")
                st.balloons()
                st.rerun()
            else:
                st.error("Please enter the member's name.")

    st.markdown("""<div class="footer">
        MediSense Pro · Family Health Vault · SWE1904 · VIT · R.Divya 21MIS0261
    </div>""", unsafe_allow_html=True)
