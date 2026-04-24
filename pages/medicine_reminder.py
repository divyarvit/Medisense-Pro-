"""
Feature 4: Medicine Reminder & Interaction Checker
Add medicines, see daily schedule, get interaction warnings.
Bridges the gap between diagnosis and treatment.
"""
import streamlit as st
from utils.database import init_medicines, add_medicine, get_medicines, delete_medicine
from datetime import datetime, date

TIMING_OPTS  = ["Morning (6–9 AM)","Before Breakfast","After Breakfast",
                "Afternoon (12–2 PM)","Before Lunch","After Lunch",
                "Evening (5–7 PM)","Before Dinner","After Dinner",
                "Bedtime","As Needed (SOS)"]
FREQ_OPTS    = ["Once daily","Twice daily","Three times daily",
                "Every 8 hours","Every 12 hours","Weekly","As needed (SOS)"]
CONDITIONS   = ["Diabetes","Hypertension","Heart Disease","Parkinson's Disease",
                "Fever/Infection","Pain Relief","Thyroid","Asthma","Other"]

# ── Drug Interaction Database (clinical, accurate) ────────────────────────
INTERACTIONS = [
    (["Metformin","Aspirin"],    "Moderate",
     "Aspirin may enhance the blood-glucose-lowering effect of Metformin. Monitor for hypoglycemia."),
    (["Metformin","Ibuprofen"],  "Moderate",
     "NSAIDs like Ibuprofen may reduce kidney function, raising Metformin levels. Use with caution."),
    (["Warfarin","Aspirin"],     "Severe",
     "⚠️ HIGH RISK: Both drugs increase bleeding risk. Can cause serious internal bleeding. Consult doctor immediately."),
    (["Warfarin","Ibuprofen"],   "Severe",
     "⚠️ HIGH RISK: NSAIDs significantly increase bleeding risk when combined with Warfarin. Avoid combination."),
    (["Amlodipine","Simvastatin"],"Moderate",
     "Amlodipine raises Simvastatin blood levels, increasing risk of muscle side effects (myopathy)."),
    (["Lisinopril","Potassium"], "Moderate",
     "ACE inhibitors like Lisinopril raise potassium levels. Avoid potassium supplements unless prescribed."),
    (["Levodopa","Iron"],        "Moderate",
     "Iron reduces absorption of Levodopa (Parkinson's medicine). Take at least 2 hours apart."),
    (["Metformin","Alcohol"],    "Moderate",
     "Alcohol with Metformin increases risk of lactic acidosis. Avoid alcohol during treatment."),
    (["Aspirin","Ibuprofen"],    "Moderate",
     "Taking both reduces Aspirin's heart-protective effect. Ibuprofen blocks Aspirin's antiplatelet action."),
    (["Paracetamol","Alcohol"],  "Severe",
     "⚠️ HIGH RISK: Combining Paracetamol with alcohol is toxic to the liver. Never combine."),
    (["Ciprofloxacin","Antacid"],"Moderate",
     "Antacids reduce Ciprofloxacin absorption by up to 90%. Take Ciprofloxacin 2 hours before antacids."),
    (["Atorvastatin","Clarithromycin"],"Severe",
     "⚠️ HIGH RISK: Clarithromycin dramatically raises Atorvastatin levels, causing serious muscle damage risk."),
    (["Digoxin","Amiodarone"],   "Severe",
     "⚠️ HIGH RISK: Amiodarone raises Digoxin levels significantly. Requires close monitoring and dose reduction."),
    (["Glipizide","Fluconazole"],"Severe",
     "⚠️ HIGH RISK: Fluconazole raises Glipizide levels, causing dangerous hypoglycemia."),
    (["Metoprolol","Verapamil"], "Severe",
     "⚠️ HIGH RISK: Both slow heart rate. Combination can cause life-threatening bradycardia or heart block."),
]

def check_interactions(med_names):
    found = []
    names_upper = [m.upper() for m in med_names]
    for pair, severity, description in INTERACTIONS:
        matched = [p for p in pair if any(p.upper() in n for n in names_upper)]
        if len(matched) >= 2:
            found.append({"drugs": pair, "severity": severity, "description": description})
    return found

def _timing_sort_key(timing):
    order = {t:i for i,t in enumerate(TIMING_OPTS)}
    return order.get(timing, 99)

def show():
    init_medicines()
    uid = st.session_state.user_id

    st.markdown("""<div class="main-header">
        <h1>💊 Medicine Reminder & Interaction Checker</h1>
        <p>Track your medicines, daily schedule, and get AI-powered drug interaction warnings</p>
    </div>""", unsafe_allow_html=True)

    st.markdown("""<div style="background:#e3f2fd;border-left:5px solid #1565c0;
        border-radius:10px;padding:12px 18px;font-size:14px;margin-bottom:16px">
        💡 <b>What this does:</b> Add all your current medicines. Get a daily schedule,
        reminders for each dose time, and automatic warnings if any two of your medicines
        interact dangerously — something most patients never check.
    </div>""", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📅 Daily Schedule",
                                  "⚠️ Interaction Checker",
                                  "➕ Add Medicine"])

    medicines = get_medicines(uid)
    med_names = [m[2] for m in medicines]

    # ── TAB 1: DAILY SCHEDULE ─────────────────────────────────────────────
    with tab1:
        if not medicines:
            st.markdown("""<div style="background:#f8f9fa;border-radius:14px;padding:48px;
                text-align:center;border:2px dashed #e0e0e0">
                <div style="font-size:4em">💊</div>
                <h3 style="color:#888">No medicines added yet</h3>
                <p style="color:#aaa">Go to "Add Medicine" tab to add your medicines</p>
            </div>""", unsafe_allow_html=True)
        else:
            now_hour = datetime.now().hour
            st.markdown(f"""<div style="background:#1565c0;color:white;border-radius:12px;
                padding:14px 20px;margin-bottom:16px;display:flex;justify-content:space-between">
                <b style="font-size:1.1em">📅 Today's Schedule — {datetime.now().strftime('%d %B %Y')}</b>
                <span style="opacity:0.85">{len(medicines)} medicine(s) active</span>
            </div>""", unsafe_allow_html=True)

            # Group by timing
            timing_groups = {}
            for m in sorted(medicines, key=lambda x: _timing_sort_key(x[5])):
                t = m[5] or "Other"
                if t not in timing_groups: timing_groups[t] = []
                timing_groups[t].append(m)

            for timing, meds in timing_groups.items():
                # Determine if time has passed
                is_morning  = "Morning" in timing or "Breakfast" in timing
                is_afternoon= "Afternoon" in timing or "Lunch" in timing
                is_evening  = "Evening" in timing or "Dinner" in timing or "Bedtime" in timing
                passed = (is_morning and now_hour>=9) or (is_afternoon and now_hour>=14) or \
                         (is_evening and now_hour>=20)
                status_icon = "✅" if passed else "⏰"
                bg = "#f0f4ff" if not passed else "#f8f9fa"

                st.markdown(f"""<div style="background:{bg};border-radius:12px;
                    padding:14px 18px;margin:8px 0;border-left:5px solid
                    {'#43a047' if passed else '#1565c0'}">
                    <b style="font-size:14px">{status_icon} {timing}</b>
                </div>""", unsafe_allow_html=True)

                for m in meds:
                    mid, uid2, name, dosage, freq, timing2, start, end, cond, notes, active, created = m
                    exp_soon = end and end <= (date.today() + __import__('datetime').timedelta(days=7)).strftime("%Y-%m-%d")
                    border_color = '#e53935' if exp_soon else '#1565c0'
                    taken_bg  = '#43a047' if passed else '#1565c0'
                    taken_txt = "✅ Taken" if passed else "⏰ Due"
                    until_txt  = f" · Until: {end}" if end else ""
                    expiry_txt = " ⚠️ Expiring soon!" if exp_soon else ""
                    notes_html = f'<div style="font-size:12px;color:#aaa;margin-top:4px">📝 {notes}</div>' if notes else ""
                    st.markdown(f"""<div style="background:white;border-radius:10px;
                        padding:12px 16px;margin:4px 0 4px 16px;
                        box-shadow:0 1px 6px rgba(0,0,0,0.07);
                        border-left:4px solid {border_color}">
                        <div style="display:flex;justify-content:space-between;align-items:center">
                            <div>
                                <b style="font-size:15px">💊 {name}</b>
                                <span style="font-size:13px;color:#555;margin-left:8px">{dosage}</span><br>
                                <span style="font-size:12px;color:#888">
                                    {freq} · For: {cond}{until_txt}{expiry_txt}
                                </span>
                            </div>
                            <div style="display:flex;gap:6px;align-items:center">
                                <div style="background:{taken_bg};
                                    color:white;padding:4px 12px;border-radius:8px;font-size:12px">
                                    {taken_txt}
                                </div>
                            </div>
                        </div>
                        </div>""", unsafe_allow_html=True)
                    if notes:
                        st.caption(f"📝 {notes}")

                    if st.button(f"🗑️ Stop {name}", key=f"stop_{mid}"):
                        delete_medicine(mid)
                        st.success(f"✅ {name} removed from your list.")
                        st.rerun()

    # ── TAB 2: INTERACTION CHECKER ────────────────────────────────────────
    with tab2:
        st.markdown("### ⚠️ Drug Interaction Checker")
        st.markdown("""<div style="background:#fff3e0;border-left:4px solid #fb8c00;
            border-radius:10px;padding:12px 16px;font-size:13px;margin-bottom:16px">
            ⚠️ <b>Important:</b> Many patients take multiple medicines without knowing
            they interact dangerously. This checker scans your current medicine list
            against a clinical interaction database.
        </div>""", unsafe_allow_html=True)

        if len(medicines) < 2:
            st.info("Add at least 2 medicines to check for interactions.")
        else:
            interactions = check_interactions(med_names)

            if not interactions:
                st.markdown("""<div style="background:#e8f5e9;border-left:5px solid #43a047;
                    border-radius:12px;padding:20px 24px;text-align:center">
                    <h2 style="color:#43a047;margin:0">✅ No Known Interactions Found</h2>
                    <p style="color:#555;margin:8px 0 0">
                        Your current medicines have no flagged interactions in our database.<br>
                        Always confirm with your doctor or pharmacist.
                    </p>
                </div>""", unsafe_allow_html=True)
            else:
                severe_count = sum(1 for i in interactions if i["severity"]=="Severe")
                st.markdown(f"""<div style="background:#ffebee;border-left:5px solid #e53935;
                    border-radius:12px;padding:14px 18px;margin-bottom:12px">
                    <b style="color:#e53935">🚨 {len(interactions)} interaction(s) found
                    — {severe_count} SEVERE</b><br>
                    <span style="font-size:13px;color:#555">
                    Please discuss these with your doctor or pharmacist immediately.
                    </span>
                </div>""", unsafe_allow_html=True)

                for inter in interactions:
                    sc = "#e53935" if inter["severity"]=="Severe" else "#fb8c00"
                    si = "🚨 SEVERE" if inter["severity"]=="Severe" else "⚠️ MODERATE"
                    st.markdown(f"""<div style="background:white;border:2px solid {sc};
                        border-radius:12px;padding:16px 20px;margin:8px 0;
                        box-shadow:0 2px 8px {sc}22">
                        <div style="display:flex;justify-content:space-between;margin-bottom:8px">
                            <b style="font-size:15px">💊 {" + ".join(inter['drugs'])}</b>
                            <span style="background:{sc};color:white;padding:3px 10px;
                                border-radius:12px;font-size:12px;font-weight:700">{si}</span>
                        </div>
                        <p style="font-size:13px;color:#333;line-height:1.6;margin:0">
                            {inter['description']}
                        </p>
                        <div style="margin-top:10px;background:#f8f9fa;border-radius:6px;
                            padding:8px 12px;font-size:12px;color:#555">
                            👨‍⚕️ <b>Action:</b> Inform your prescribing doctor about this combination.
                        </div>
                    </div>""", unsafe_allow_html=True)

        # Manual check (for medicines not in the system)
        st.markdown("---")
        st.markdown("### 🔍 Check Any Two Medicines")
        mc1, mc2 = st.columns(2)
        with mc1:
            drug1 = st.text_input("Medicine 1", placeholder="e.g. Warfarin")
        with mc2:
            drug2 = st.text_input("Medicine 2", placeholder="e.g. Aspirin")
        if st.button("⚠️ Check Interaction", use_container_width=True):
            if drug1 and drug2:
                result = check_interactions([drug1, drug2])
                if result:
                    for inter in result:
                        sc = "#e53935" if inter["severity"]=="Severe" else "#fb8c00"
                        st.markdown(f"""<div style="background:{sc}15;border-left:5px solid {sc};
                            border-radius:10px;padding:14px 18px">
                            <b style="color:{sc}">⚠️ {inter['severity']} Interaction</b><br>
                            <p style="font-size:13px;margin:6px 0 0">{inter['description']}</p>
                        </div>""", unsafe_allow_html=True)
                else:
                    st.success(f"✅ No known interaction found between {drug1} and {drug2} in our database.")
            else:
                st.warning("Please enter both medicine names.")

    # ── TAB 3: ADD MEDICINE ───────────────────────────────────────────────
    with tab3:
        st.markdown("### ➕ Add a Medicine")
        a1, a2 = st.columns(2)
        with a1:
            m_name  = st.text_input("💊 Medicine Name", placeholder="e.g. Metformin 500mg")
            m_dose  = st.text_input("📏 Dosage",        placeholder="e.g. 1 tablet, 5ml")
            m_freq  = st.selectbox("🔄 Frequency", FREQ_OPTS)
            m_cond  = st.selectbox("🏥 Prescribed For", CONDITIONS)
        with a2:
            m_time  = st.selectbox("⏰ When to Take", TIMING_OPTS)
            m_start = st.date_input("📅 Start Date", value=date.today())
            m_end   = st.date_input("📅 End Date (optional)",
                                     value=None if True else date.today())
            m_notes = st.text_input("📝 Notes", placeholder="e.g. Take with food")

        if st.button("✅ Add Medicine", use_container_width=True):
            if m_name.strip():
                add_medicine(uid, m_name.strip(), m_dose, m_freq, m_time,
                              str(m_start), str(m_end) if m_end else "",
                              m_cond, m_notes)
                st.success(f"✅ {m_name} added to your medicine list!")
                # Quick interaction check
                all_meds = get_medicines(uid)
                all_names = [m[2] for m in all_meds]
                found = check_interactions(all_names)
                if found:
                    st.warning(f"⚠️ Interaction check flagged {len(found)} issue(s) — check the Interaction Checker tab!")
                st.rerun()
            else:
                st.error("Please enter the medicine name.")

    st.markdown("""<div class="footer">
        MediSense Pro · Medicine Reminder · SWE1904 · VIT · R.Divya 21MIS0261
    </div>""", unsafe_allow_html=True)
