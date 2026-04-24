"""
Kidney Disease (CKD) Module — MediSense Pro v11
Two modes:
  🏠 Home Screener  — 11 self-observable symptoms + risk factors
  🔬 Lab Values     — Creatinine + Urea → auto-calculate eGFR + CKD staging

Clinical basis: KDIGO CKD Guidelines + CKD-EPI equation for eGFR
India context: 17 crore Indians have CKD. Most don't know until Stage 3-4.
Connection: Directly downstream of Diabetes + Hypertension modules.
"""
import streamlit as st, math
from utils.report_renderer import render_clinical_report
from utils.database import save_report

# ─── eGFR CALCULATION (CKD-EPI 2021 equation) ────────────────────────────────
def _egfr(creatinine_mgdl, age, sex):
    """CKD-EPI Creatinine equation 2021"""
    kappa = 0.7 if sex == "Female" else 0.9
    alpha = -0.241 if sex == "Female" else -0.302
    ratio = creatinine_mgdl / kappa
    sex_factor = 1.012 if sex == "Female" else 1.0
    if ratio <= 1:
        egfr = 142 * (ratio ** alpha) * (0.9938 ** age) * sex_factor
    else:
        egfr = 142 * (ratio ** -1.200) * (0.9938 ** age) * sex_factor
    return round(egfr, 1)

def _ckd_stage(egfr):
    if egfr >= 90:   return 1, "G1 — Normal or High", "#43a047", "Kidney function normal. Risk factors present."
    elif egfr >= 60: return 2, "G2 — Mildly Decreased", "#8bc34a", "Mild reduction. Manage risk factors aggressively."
    elif egfr >= 45: return 3, "G3a — Mild to Moderate Decrease", "#fdd835", "Nephrology referral recommended."
    elif egfr >= 30: return 4, "G3b — Moderate to Severe Decrease", "#fb8c00", "Nephrology care essential. Prepare for dialysis planning."
    elif egfr >= 15: return 5, "G4 — Severe Decrease", "#e53935", "Approaching kidney failure. Dialysis/transplant planning urgent."
    else:            return 6, "G5 — Kidney Failure", "#b71c1c", "Kidney failure. Dialysis or transplant required."

# ─── HOME SCREENER SCORING ────────────────────────────────────────────────────
def _home_ckd_score(data):
    score = 0
    flags = []

    age     = data["age"]
    sex     = data["sex"]
    family  = data["family_history"]
    dm      = data["has_diabetes"]
    htn     = data["has_hypertension"]
    syms    = data["symptoms"]
    urine   = data["urine_changes"]
    dur     = data["duration_months"]
    meds    = data["nsaid_use"]
    pain    = data["painkillers"]

    # ── Age & Sex (10 pts) ────────────────────────────────────────────
    if age >= 70:
        score += 10; flags.append("🔴 Age 70+ — kidney function naturally declines with age")
    elif age >= 60:
        score += 7;  flags.append("🔴 Age 60+ — CKD risk rises significantly")
    elif age >= 45:
        score += 4;  flags.append("🟡 Age 45+ — early monitoring recommended")
    else:
        flags.append("🟢 Age below 45 — lower baseline CKD risk")

    if sex == "Male":
        score += 2; flags.append("🟡 Male sex — slightly higher CKD progression rate")

    # ── Primary Risk Factors (30 pts) — the two biggest ──────────────
    if dm == "Yes — diagnosed diabetic":
        score += 18; flags.append("🔴 Diabetes — single biggest cause of CKD in India (40% of all CKD)")
    elif dm == "Yes — pre-diabetic / borderline":
        score += 8;  flags.append("🟡 Pre-diabetes — elevated CKD risk, especially with high BP")

    if htn == "Yes — on BP medication":
        score += 14; flags.append("🔴 Hypertension on medication — 2nd biggest CKD cause, damages kidney vessels")
    elif htn == "Yes — high BP, not on medication":
        score += 18; flags.append("🔴 Uncontrolled hypertension — most damaging CKD driver")
    elif htn == "Borderline / sometimes elevated":
        score += 6;  flags.append("🟡 Borderline BP — monitor closely, especially with diabetes")

    # ── Family History (8 pts) ────────────────────────────────────────
    if family == "Yes — parent or sibling with CKD or kidney failure":
        score += 8; flags.append("🔴 Family history of CKD — significant genetic risk")
    elif family == "Yes — extended family":
        score += 3; flags.append("🟡 Extended family history of kidney disease")

    # ── Medication Use (8 pts) ────────────────────────────────────────
    if pain == "Daily or near-daily (chronic use)":
        score += 8; flags.append("🔴 Chronic painkiller use — NSAIDs (Ibuprofen, Diclofenac) are a leading cause of kidney damage in India")
    elif pain == "Several times a week":
        score += 5; flags.append("🔴 Frequent painkiller use — reduces kidney blood flow over time")
    elif pain == "Occasionally (a few times a month)":
        score += 2; flags.append("🟡 Occasional painkiller use — limit where possible")
    else:
        flags.append("🟢 No regular painkiller use — protective")

    # ── Symptoms (up to 20 pts) ───────────────────────────────────────
    sym_scores = {
        "Persistent fatigue — tired even after rest": 4,
        "Ankle or leg swelling (oedema)": 6,
        "Puffiness around eyes in the morning": 5,
        "Shortness of breath without exertion": 5,
        "Nausea or loss of appetite for weeks": 4,
        "Persistent itching of skin without rash": 5,
        "Muscle cramps especially at night": 3,
        "Difficulty concentrating or brain fog": 3,
    }
    sym_total = 0
    for sym in syms:
        pts = sym_scores.get(sym, 0)
        sym_total += pts
        score += pts
        if pts >= 5:
            flags.append(f"🔴 Symptom: {sym}")
        elif pts >= 3:
            flags.append(f"🟡 Symptom: {sym}")

    # ── Urine Changes (up to 15 pts) — most specific CKD signs ────────
    urine_scores = {
        "Foamy or bubbly urine (proteinuria sign)": 8,
        "Urine is dark brown or tea-coloured": 6,
        "Noticeably reduced urine output": 7,
        "Needing to urinate more often at night": 4,
        "Blood in urine (pink/red/brown tinge)": 8,
    }
    for u in urine:
        pts = urine_scores.get(u, 0)
        score += pts
        if pts >= 6:
            flags.append(f"🔴 Urine change: {u} — specific CKD warning sign")
        elif pts >= 4:
            flags.append(f"🟡 Urine change: {u}")

    # ── Duration (bonus weight) ───────────────────────────────────────
    if dur == "More than 3 months":
        score += 5; flags.append("🔴 Symptoms persistent >3 months — CKD definition requires 3+ months")
    elif dur == "1 to 3 months":
        score += 3; flags.append("🟡 Symptoms 1-3 months — approaching CKD timeframe")

    score = min(score, 100)

    if score >= 55:   risk = "High Risk"
    elif score >= 30: risk = "Moderate Risk"
    else:             risk = "Low Risk"

    return score, risk, flags

def _build_ckd_report(risk, score, source, stage=None, egfr=None):
    sev_map = {"High Risk": "Severe", "Moderate Risk": "Moderate", "Low Risk": "Mild"}
    severity = sev_map.get(risk, "Moderate")

    if risk == "High Risk" or (egfr and egfr < 45):
        conditions = [
            {"condition": "Chronic Kidney Disease — High Risk",
             "probability": min(35 + score * 0.45, 85),
             "description": "Multiple strong CKD risk factors or significantly reduced kidney function.",
             "icd": "N18.3"},
            {"condition": "Diabetic Nephropathy",
             "probability": 10.0,
             "description": "Kidney damage caused by long-term high blood sugar.",
             "icd": "N08"},
            {"condition": "Hypertensive Nephropathy",
             "probability": 5.0,
             "description": "Kidney damage from chronic uncontrolled blood pressure.",
             "icd": "I12"},
        ]
        do_list = [
            "🚨 See a Nephrologist (kidney specialist) within 1-2 weeks",
            "Get Serum Creatinine, Blood Urea, and Urine Albumin-Creatinine Ratio tested immediately",
            "Control blood sugar strictly — HbA1c below 7% slows CKD progression",
            "Control BP strictly — target below 130/80 mmHg for CKD patients",
            "Stop all NSAIDs immediately — Ibuprofen and Diclofenac are toxic to kidneys",
            "Reduce protein intake if eGFR below 30 — follow nephrologist diet plan",
            "Stay well hydrated — drink 2-3 litres of water daily unless restricted",
            "Monitor weight daily — sudden weight gain = fluid retention",
        ]
        dont_list = [
            "Do NOT take Ibuprofen, Diclofenac, or Naproxen — they worsen kidney damage rapidly",
            "Do NOT use any herbal kidney remedies without nephrologist approval",
            "Do NOT delay treatment — CKD is silent until 60-70% function is lost",
            "Avoid high-potassium foods if eGFR below 30 (banana, coconut water, orange)",
            "Do NOT take Metformin if eGFR below 30 (risk of lactic acidosis)",
            "Avoid contrast dye procedures without telling the doctor about CKD",
        ]
        when_doc = [
            "🚨 Within 1-2 weeks — Nephrologist urgently",
            "Immediately if urine output drops significantly",
            "Immediately if severe swelling develops suddenly",
            "Immediately if confusion or extreme fatigue develops",
        ]
        specialist = "Nephrologist — URGENT"
    elif risk == "Moderate Risk" or (egfr and egfr < 60):
        conditions = [
            {"condition": "Elevated CKD Risk — Early Monitoring Needed",
             "probability": min(20 + score * 0.4, 65),
             "description": "Risk factors present or mildly reduced kidney function.",
             "icd": "N18.2"},
            {"condition": "Diabetic or Hypertensive Kidney Risk",
             "probability": 20.0,
             "description": "Kidney stress from metabolic risk factors.",
             "icd": "N08"},
            {"condition": "NSAID-Related Kidney Stress",
             "probability": 10.0,
             "description": "Painkiller use affecting kidney blood flow.",
             "icd": "N14.0"},
        ]
        do_list = [
            "Get Serum Creatinine and urine Albumin-Creatinine Ratio tested this month",
            "See a physician for kidney function evaluation within 4 weeks",
            "Control blood pressure — target below 130/80",
            "Control blood sugar if diabetic — HbA1c below 7%",
            "Reduce NSAID use — switch to Paracetamol for pain where possible",
            "Drink 2-3 litres of water daily",
        ]
        dont_list = [
            "Do not ignore persistent ankle swelling or foamy urine",
            "Reduce NSAID/painkiller use significantly",
            "Do not add salt to food — reduce sodium intake",
        ]
        when_doc = [
            "Within 4 weeks for kidney function blood test",
            "Sooner if swelling, reduced urine, or foamy urine develop",
            "Annual kidney function test from now on",
        ]
        specialist = "Physician / Nephrologist (within 4 weeks)"
    else:
        conditions = [
            {"condition": "Low CKD Risk Currently",
             "probability": 85.0,
             "description": "No significant kidney disease risk factors identified.",
             "icd": "Z03.89"},
            {"condition": "Baseline Kidney Health",
             "probability": 10.0,
             "description": "Normal kidney function range with no concerning signs.",
             "icd": "Z82.49"},
            {"condition": "Preventive Monitoring Recommended",
             "probability": 5.0,
             "description": "Lifestyle monitoring to maintain kidney health long-term.",
             "icd": "Z13.6"},
        ]
        do_list = [
            "Stay well hydrated — 2-3 litres of water daily",
            "Annual kidney function check after age 40 especially with diabetes/hypertension",
            "Keep blood sugar and BP in normal range — prevention is everything in CKD",
            "Limit NSAID use — use Paracetamol for routine pain instead",
        ]
        dont_list = [
            "Do not take NSAIDs regularly — even occasional overuse harms kidneys",
            "Avoid excess salt — raises BP which damages kidneys",
            "Do not ignore ankle swelling or foamy urine if they develop",
        ]
        when_doc = [
            "Annual checkup with creatinine test after age 40",
            "If foamy urine, ankle swelling, or reduced urine develops",
            "Any time blood pressure becomes persistently elevated",
        ]
        specialist = "General Physician (annual checkup)"

    sev_expl = {
        "High Risk": "Multiple strong CKD risk factors identified. Kidney function evaluation urgently needed.",
        "Moderate Risk": "Several CKD risk factors present. Kidney function testing recommended soon.",
        "Low Risk": "No significant CKD risk factors at this time. Maintain kidney-healthy habits.",
    }.get(risk, "")

    if egfr:
        sev_expl += f" Calculated eGFR: {egfr} mL/min/1.73m²."

    sev_reasons = ["Multiple CKD risk factors identified" if risk == "High Risk"
                   else "Some CKD risk factors present"]
    confidence = min(40 + score * 0.45, 88)

    home_care = [
        "Drink 2-3 litres of water daily — most important single habit for kidney health",
        "Reduce salt — avoid pickle, papad, packaged food, extra salt at table",
        "Replace Ibuprofen/Diclofenac with Paracetamol for routine pain",
        "Monitor ankle swelling daily — note if it worsens",
        "Check and record BP every morning",
        "If diabetic — check blood sugar daily and keep HbA1c below 7%",
        "National Kidney Foundation India helpline: 1800-103-6363",
    ]
    do_dont = {"do": do_list, "dont": dont_list}
    extra = f"**Stage:** {stage if stage else 'Not calculated'} · **eGFR:** {egfr if egfr else 'Not calculated'} · **Refer:** {specialist}"
    return severity, sev_expl, sev_reasons, conditions, confidence, do_dont, home_care, when_doc, extra


# ─── MAIN SHOW ────────────────────────────────────────────────────────────────
def show():
    uid   = st.session_state.user_id
    uname = st.session_state.get("full_name", "Patient")

    st.markdown("""<div class="main-header">
        <h1>🫘 Kidney Disease (CKD) Assessment</h1>
        <p>Chronic Kidney Disease screening — symptom check · lab values · eGFR calculator</p>
    </div>""", unsafe_allow_html=True)

    st.markdown("""<div style="background:#e3f2fd;border-left:5px solid #1565c0;
        border-radius:10px;padding:12px 18px;font-size:13px;margin-bottom:16px">
        🫘 <b>CKD is called the Silent Killer</b> — it has almost no symptoms until
        60-70% of kidney function is already lost. Over 17 crore Indians have CKD.
        The two biggest causes are <b>Diabetes and Hypertension</b> — both screened in
        other MediSense modules. If you got High Risk in those — check your kidneys here.
    </div>""", unsafe_allow_html=True)

    home_tab, lab_tab = st.tabs([
        "🏠 Home Screener — Symptoms & Risk Factors",
        "🔬 Lab Values — Creatinine, Urea & eGFR Calculator",
    ])

    # ════════════════════════════════════════════════════════════════════
    # TAB 1 — HOME SCREENER
    # ════════════════════════════════════════════════════════════════════
    with home_tab:
        st.markdown("""<div style="background:#e8f5e9;border-left:5px solid #43a047;
            border-radius:10px;padding:12px 18px;font-size:13px;margin-bottom:16px">
            🏠 <b>No devices. No lab tests. No technical knowledge needed.</b>
            Uses only what you already know about yourself and your health history.
        </div>""", unsafe_allow_html=True)

        st.markdown("### 👤 About You")
        a1, a2, a3 = st.columns(3)
        with a1:
            h_age = st.number_input("🎂 Age", 18, 100, 50, key="ck_age")
            h_sex = st.selectbox("⚤ Sex", ["Male", "Female"], key="ck_sex")
        with a2:
            h_dm = st.selectbox("🩸 Diabetes Status",
                ["No diabetes",
                 "Yes — pre-diabetic / borderline",
                 "Yes — diagnosed diabetic"])
            h_htn = st.selectbox("💓 Blood Pressure Status",
                ["Normal BP",
                 "Borderline / sometimes elevated",
                 "Yes — on BP medication",
                 "Yes — high BP, not on medication"])
        with a3:
            h_family = st.selectbox("👨‍👩‍👧 Family History of Kidney Disease",
                ["None / Not known",
                 "Yes — extended family",
                 "Yes — parent or sibling with CKD or kidney failure"])
            h_pain = st.selectbox("💊 Painkiller Use (Ibuprofen/Diclofenac/Combiflam)",
                ["Rarely or never",
                 "Occasionally (a few times a month)",
                 "Several times a week",
                 "Daily or near-daily (chronic use)"])

        st.markdown("---")
        st.markdown("### 🤒 Symptoms")
        st.markdown("""<div style="background:#fff3e0;border-left:4px solid #fb8c00;
            border-radius:8px;padding:10px 14px;font-size:13px;margin-bottom:10px">
            ⚠️ <b>These symptoms appear late in CKD</b> — when significant damage has already occurred.
            Their absence does NOT mean your kidneys are healthy, especially if you have diabetes or high BP.
        </div>""", unsafe_allow_html=True)

        sym_opts = [
            "Persistent fatigue — tired even after rest",
            "Ankle or leg swelling (oedema)",
            "Puffiness around eyes in the morning",
            "Shortness of breath without exertion",
            "Nausea or loss of appetite for weeks",
            "Persistent itching of skin without rash",
            "Muscle cramps especially at night",
            "Difficulty concentrating or brain fog",
            "None of the above",
        ]
        sc = st.columns(3)
        h_syms = []
        for i, sym in enumerate(sym_opts):
            with sc[i % 3]:
                if st.checkbox(sym, key=f"cksym_{i}"):
                    h_syms.append(sym)

        st.markdown("---")
        st.markdown("### 🚿 Urine Changes")
        st.markdown("""<div style="background:#ffebee;border-left:4px solid #e53935;
            border-radius:8px;padding:10px 14px;font-size:13px;margin-bottom:10px">
            🔴 <b>Urine changes are the most specific early warning signs of kidney damage.</b>
            Foamy urine means protein is leaking — a key early sign of diabetic kidney disease.
        </div>""", unsafe_allow_html=True)

        urine_opts = [
            "Foamy or bubbly urine (proteinuria sign)",
            "Urine is dark brown or tea-coloured",
            "Noticeably reduced urine output",
            "Needing to urinate more often at night",
            "Blood in urine (pink/red/brown tinge)",
            "No urine changes noticed",
        ]
        uc = st.columns(3)
        h_urine = []
        for i, u in enumerate(urine_opts):
            with uc[i % 3]:
                if st.checkbox(u, key=f"ckurine_{i}"):
                    h_urine.append(u)

        st.markdown("---")
        h_dur = st.selectbox("⏱️ How long have these symptoms been present?",
            ["No symptoms",
             "Less than 2 weeks",
             "2 weeks to 1 month",
             "1 to 3 months",
             "More than 3 months"])

        st.markdown("---")
        if st.button("🔍 Run Kidney Risk Assessment", use_container_width=True, key="ck_home_btn"):
            data = {
                "age": h_age, "sex": h_sex,
                "has_diabetes": h_dm, "has_hypertension": h_htn,
                "family_history": h_family, "nsaid_use": False,
                "painkillers": h_pain, "symptoms": h_syms,
                "urine_changes": h_urine, "duration_months": h_dur,
            }
            score, risk, flags = _home_ckd_score(data)

            rc = {"High Risk": "#e53935", "Moderate Risk": "#fb8c00", "Low Risk": "#43a047"}.get(risk)
            ri = {"High Risk": "🚨", "Moderate Risk": "⚠️", "Low Risk": "✅"}.get(risk)

            st.markdown(f"""<div style="background:{rc};color:white;border-radius:16px;
                padding:22px 32px;text-align:center;margin:12px 0;
                box-shadow:0 6px 24px {rc}44">
                <h1 style="margin:0;font-size:2em">{ri} {risk}</h1>
                <h3 style="margin:8px 0 0;opacity:0.95">CKD Risk Score: {score}/100</h3>
            </div>""", unsafe_allow_html=True)

            # Score bar
            st.markdown(f"""<div style="background:#f0f0f0;border-radius:8px;height:14px;margin:6px 0">
                <div style="background:linear-gradient(90deg,#43a047,#fb8c00,#e53935);
                    width:{score}%;height:14px;border-radius:8px"></div>
            </div>""", unsafe_allow_html=True)

            # Foamy urine specific call-out
            if "Foamy or bubbly urine" in h_urine:
                st.markdown("""<div style="background:#ffebee;border-left:5px solid #e53935;
                    border-radius:10px;padding:12px 18px;font-size:13px;margin:8px 0">
                    🔴 <b>Foamy Urine Detected:</b> This is a specific early warning sign of
                    <b>Proteinuria</b> — protein leaking into urine because kidney filters are damaged.
                    In a diabetic patient, this is the first sign of <b>Diabetic Nephropathy.</b>
                    Get a Urine Albumin-Creatinine Ratio (UACR) test immediately — costs ₹150.
                </div>""", unsafe_allow_html=True)

            # Connection to diabetes/heart
            if h_dm != "No diabetes":
                st.markdown("""<div style="background:#e3f2fd;border-left:4px solid #1565c0;
                    border-radius:8px;padding:10px 14px;font-size:13px;margin:6px 0">
                    💡 <b>Diabetes-CKD Connection:</b> 40% of all CKD in India is caused by diabetes.
                    Every diabetic patient should get a kidney function test (Creatinine + UACR)
                    annually — even if they feel completely fine. Most diabetic kidney disease
                    is caught only at Stage 3 because Stage 1-2 has no symptoms.
                </div>""", unsafe_allow_html=True)

            r1, r2 = st.tabs(["📋 Factor Analysis", "📄 Full Report"])
            with r1:
                for f in flags:
                    bg = ("#ffebee" if "🔴" in f else "#fff8e1" if "🟡" in f else "#e8f5e9")
                    bd = ("#e53935" if "🔴" in f else "#fb8c00" if "🟡" in f else "#43a047")
                    st.markdown(f"""<div style="background:{bg};border-left:4px solid {bd};
                        border-radius:8px;padding:9px 14px;margin:4px 0;font-size:13px">{f}</div>""",
                        unsafe_allow_html=True)
            with r2:
                sev, se, sr, cond, conf, dd, hc, wd, ex = _build_ckd_report(risk, score, "home")
                render_clinical_report("Kidney Disease Screening", sev, se, sr, cond, conf,
                                        dd, hc, wd, ex, patient_name=uname)

            save_report(uid, "Kidney Disease Screening", sev,
                        "CKD Risk Assessment", conf,
                        f"Age:{h_age}|DM:{h_dm[:3]}|HTN:{h_htn[:3]}|Score:{score}|Risk:{risk}",
                        numeric_value=float(score))
            st.success("✅ Assessment saved to your history.")

    # ════════════════════════════════════════════════════════════════════
    # TAB 2 — LAB VALUES + eGFR
    # ════════════════════════════════════════════════════════════════════
    with lab_tab:
        st.markdown("""<div style="background:#e3f2fd;border-left:5px solid #1565c0;
            border-radius:10px;padding:12px 18px;font-size:13px;margin-bottom:16px">
            🔬 <b>For patients who have had a blood test.</b>
            Enter your Serum Creatinine and the app automatically calculates your
            <b>eGFR</b> (estimated Glomerular Filtration Rate) — the gold standard
            measure of kidney function — and stages your CKD. Creatinine test costs
            ₹100 at any diagnostic lab.
        </div>""", unsafe_allow_html=True)

        st.markdown("### 📋 Patient Details + Lab Values")
        l1, l2, l3 = st.columns(3)
        with l1:
            l_age  = st.number_input("🎂 Age", 18, 100, 50, key="ck_l_age")
            l_sex  = st.selectbox("⚤ Sex", ["Male", "Female"], key="ck_l_sex")
        with l2:
            l_creat = st.number_input("🧪 Serum Creatinine (mg/dL)",
                0.1, 20.0, 1.0, step=0.1,
                help="Normal: Male 0.7-1.3 mg/dL · Female 0.6-1.1 mg/dL")
            l_urea  = st.number_input("🧪 Blood Urea (mg/dL) — 0 to skip",
                0.0, 300.0, 0.0, step=1.0,
                help="Normal: 7-20 mg/dL. Above 40 is elevated.")
        with l3:
            l_uacr  = st.number_input("🧪 Urine Albumin-Creatinine Ratio (mg/g) — 0 to skip",
                0.0, 5000.0, 0.0, step=1.0,
                help="Normal below 30. 30-300 = Moderately increased. Above 300 = Severely increased.")
            l_bp_s  = st.number_input("💓 Systolic BP (mmHg)", 80, 240, 120, key="ck_bp")

        # Live eGFR calculation
        if l_creat > 0:
            egfr_val = _egfr(l_creat, l_age, l_sex)
            stage_num, stage_desc, stage_color, stage_note = _ckd_stage(egfr_val)

            st.markdown(f"""<div style="background:{stage_color};color:white;border-radius:14px;
                padding:18px 28px;text-align:center;margin:14px 0">
                <h2 style="margin:0">eGFR: {egfr_val} mL/min/1.73m²</h2>
                <h3 style="margin:8px 0 0;opacity:0.95">CKD {stage_desc}</h3>
                <p style="margin:6px 0 0;font-size:13px;opacity:0.9">{stage_note}</p>
            </div>""", unsafe_allow_html=True)

            # eGFR reference table
            st.markdown("""<div style="background:#f8f9fa;border-radius:10px;padding:14px;
                font-size:12px;border:1px solid #e0e0e0;margin:8px 0">
                <b>eGFR Reference — CKD Stages:</b><br>
                🟢 G1: ≥90 — Normal kidney function ·
                🟡 G2: 60-89 — Mildly decreased ·
                🟡 G3a: 45-59 — Mild to moderate ·
                🔴 G3b: 30-44 — Moderate to severe ·
                🔴 G4: 15-29 — Severe ·
                🔴 G5: &lt;15 — Kidney failure
            </div>""", unsafe_allow_html=True)

            # Creatinine interpretation
            normal_creat = (0.7, 1.3) if l_sex == "Male" else (0.6, 1.1)
            creat_status = "🟢 Normal" if normal_creat[0] <= l_creat <= normal_creat[1] else "🔴 Above normal range"
            st.markdown(f"""<div style="background:#f8f9fa;border-radius:8px;padding:10px 14px;
                font-size:13px;border-left:4px solid {'#43a047' if '🟢' in creat_status else '#e53935'}">
                Serum Creatinine {l_creat} mg/dL — {creat_status}
                (Normal for {l_sex}: {normal_creat[0]}–{normal_creat[1]} mg/dL)
            </div>""", unsafe_allow_html=True)

            # Urea interpretation
            if l_urea > 0:
                urea_s = "🟢 Normal" if l_urea <= 40 else ("🟡 Mildly elevated" if l_urea <= 80 else "🔴 Significantly elevated")
                st.markdown(f"""<div style="background:#f8f9fa;border-radius:8px;padding:10px 14px;
                    font-size:13px;border-left:4px solid {'#43a047' if '🟢' in urea_s else '#e53935'}">
                    Blood Urea {l_urea} mg/dL — {urea_s} (Normal: 7–40 mg/dL)
                </div>""", unsafe_allow_html=True)

            # UACR interpretation
            if l_uacr > 0:
                if l_uacr < 30:
                    uacr_s = "🟢 Normal (below 30)"
                elif l_uacr < 300:
                    uacr_s = "🟡 Moderately increased — early kidney leak (30-300)"
                else:
                    uacr_s = "🔴 Severely increased — significant protein leak (above 300)"
                st.markdown(f"""<div style="background:#f8f9fa;border-radius:8px;padding:10px 14px;
                    font-size:13px;border-left:4px solid {'#43a047' if '🟢' in uacr_s else '#e53935'}">
                    Urine Albumin-Creatinine Ratio {l_uacr} mg/g — {uacr_s}
                </div>""", unsafe_allow_html=True)

            if st.button("📄 Generate Full CKD Report", use_container_width=True):
                risk_from_egfr = ("High Risk" if egfr_val < 45 else
                                   "Moderate Risk" if egfr_val < 60 else "Low Risk")
                sev, se, sr, cond, conf, dd, hc, wd, ex = _build_ckd_report(
                    risk_from_egfr, int((1 - min(egfr_val/90,1))*80),
                    "lab", stage=stage_desc, egfr=egfr_val)
                render_clinical_report("Kidney Disease — Lab Values", sev, se, sr, cond, conf,
                                        dd, hc, wd, ex, patient_name=uname)
                save_report(uid, "Kidney Disease Lab Values", sev,
                            f"CKD {stage_desc}", conf,
                            f"Creatinine:{l_creat}|eGFR:{egfr_val}|Stage:{stage_num}",
                            numeric_value=float(egfr_val))
                st.success("✅ Report saved to your history.")

    st.markdown("""<div class="footer">
        MediSense Pro · Kidney Disease Assessment · SWE1904 · VIT · R.Divya 21MIS0261
    </div>""", unsafe_allow_html=True)
