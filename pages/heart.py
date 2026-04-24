"""
Heart Disease Module — MediSense Pro v10
Solving all 7 clinical holes:
1. Stable vs Unstable Angina distinguished
2. Cholesterol type (LDL/HDL/Total) context added
3. Chest pain character + duration asked
4. Family history included
5. Lifestyle factors (smoking, activity, diet, alcohol)
6. Emergency urgency detection — 108 triage FIRST
7. BMI included in home screener

Three modes:
  🚨 Emergency Triage  — 5 questions, active heart attack detection
  🏠 Home Screener     — what a person at home actually has
  🔬 Clinical ML       — Cleveland dataset, full lab reports
"""
import streamlit as st, pickle, os, numpy as np
from utils.report_renderer import render_clinical_report
from utils.database import save_report
from utils.explainability import explain_heart
from utils.xai_renderer import render_xai_panel
from datetime import datetime

MODEL = pickle.load(open(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                      "models","heart_disease_model1.sav"),"rb"))

# ─── WHO SCORE-India Risk Weights (Home Screener) ─────────────────────────────
# Based on Framingham + WHO SCORE adapted for Indian population
def _home_cardiac_score(data):
    score = 0
    flags = []

    age    = data["age"]
    sex    = data["sex"]
    bmi    = data["bmi"]
    sys_bp = data["systolic_bp"]
    dia_bp = data["diastolic_bp"]
    rhr    = data["resting_hr"]
    spo2   = data["spo2"]
    fbs    = data["fasting_sugar"]
    smoke  = data["smoking"]
    steps  = data["daily_steps"]
    sleep  = data["sleep_hours"]
    family = data["family_history"]
    chol   = data["cholesterol"]
    hdl    = data["hdl"]
    symptoms = data["symptoms"]
    pain_type= data["pain_type"]
    pain_dur = data["pain_duration"]
    alcohol  = data["alcohol"]
    stress   = data["stress_level"]

    # ── Age (15 pts) ──────────────────────────────────────────────────
    if sex == "Male":
        if age >= 65:   score += 15; flags.append("🔴 Age 65+ male — very high cardiac risk")
        elif age >= 55: score += 10; flags.append("🔴 Age 55+ male — high cardiac risk zone")
        elif age >= 45: score += 6;  flags.append("🟡 Age 45+ male — risk rising")
        else:                        flags.append("🟢 Age below 45 male — lower baseline risk")
    else:
        if age >= 65:   score += 12; flags.append("🔴 Age 65+ female — post-menopausal, high risk")
        elif age >= 55: score += 7;  flags.append("🟡 Age 55+ female — post-menopausal risk")
        elif age >= 45: score += 3;  flags.append("🟡 Age 45+ female — peri-menopausal")
        else:                        flags.append("🟢 Age below 45 female — hormonal protection active")

    # ── Blood Pressure (15 pts) ───────────────────────────────────────
    if sys_bp >= 180 or dia_bp >= 110:
        score += 15; flags.append(f"🔴 BP {sys_bp}/{dia_bp} mmHg — Hypertensive Crisis — major CAD risk")
    elif sys_bp >= 160 or dia_bp >= 100:
        score += 12; flags.append(f"🔴 BP {sys_bp}/{dia_bp} mmHg — Stage 2 Hypertension")
    elif sys_bp >= 140 or dia_bp >= 90:
        score += 8;  flags.append(f"🔴 BP {sys_bp}/{dia_bp} mmHg — Stage 1 Hypertension — treat now")
    elif sys_bp >= 130 or dia_bp >= 85:
        score += 4;  flags.append(f"🟡 BP {sys_bp}/{dia_bp} mmHg — Elevated — monitor closely")
    else:
        flags.append(f"🟢 BP {sys_bp}/{dia_bp} mmHg — Normal")

    # ── Smoking (15 pts — biggest modifiable risk) ────────────────────
    if smoke == "Current smoker (daily)":
        score += 15; flags.append("🔴 Current daily smoker — 200-300% increased CAD risk")
    elif smoke == "Current smoker (occasional)":
        score += 10; flags.append("🔴 Occasional smoker — significant CAD risk")
    elif smoke == "Ex-smoker (quit < 5 years ago)":
        score += 5;  flags.append("🟡 Ex-smoker — risk reducing but still elevated")
    elif smoke == "Ex-smoker (quit > 5 years ago)":
        score += 2;  flags.append("🟡 Ex-smoker (5+ years) — risk nearly normalised")
    else:
        flags.append("🟢 Non-smoker — no smoking risk")

    # ── Cholesterol (12 pts) ──────────────────────────────────────────
    if chol > 0:
        if hdl > 0:
            # Use ratio — much more accurate
            ratio = chol / hdl
            if ratio > 6:
                score += 12; flags.append(f"🔴 Cholesterol/HDL ratio {ratio:.1f} — very high risk (>6 is dangerous)")
            elif ratio > 5:
                score += 8;  flags.append(f"🔴 Cholesterol/HDL ratio {ratio:.1f} — high risk (target <5)")
            elif ratio > 4:
                score += 4;  flags.append(f"🟡 Cholesterol/HDL ratio {ratio:.1f} — borderline")
            else:
                flags.append(f"🟢 Cholesterol/HDL ratio {ratio:.1f} — good ratio (below 4)")
        else:
            # Total cholesterol only
            if chol >= 240:
                score += 10; flags.append(f"🔴 Total Cholesterol {chol} mg/dL — High (≥240)")
            elif chol >= 200:
                score += 5;  flags.append(f"🟡 Total Cholesterol {chol} mg/dL — Borderline High (200-239)")
            else:
                flags.append(f"🟢 Total Cholesterol {chol} mg/dL — Desirable (<200)")

    # ── Blood Sugar (8 pts) ───────────────────────────────────────────
    if fbs > 0:
        if fbs > 126:
            score += 8; flags.append(f"🔴 Fasting Blood Sugar {fbs} mg/dL — Diabetic range (doubles heart disease risk)")
        elif fbs > 100:
            score += 4; flags.append(f"🟡 Fasting Blood Sugar {fbs} mg/dL — Pre-diabetic (increases cardiac risk)")
        else:
            flags.append(f"🟢 Fasting Blood Sugar {fbs} mg/dL — Normal")

    # ── BMI (8 pts) ───────────────────────────────────────────────────
    if bmi > 0:
        if bmi >= 35:
            score += 8; flags.append(f"🔴 BMI {bmi:.1f} — Severe obesity (all three CVD risk factors worsened)")
        elif bmi >= 30:
            score += 5; flags.append(f"🔴 BMI {bmi:.1f} — Obese (major cardiac risk driver)")
        elif bmi >= 25:
            score += 3; flags.append(f"🟡 BMI {bmi:.1f} — Overweight")
        else:
            flags.append(f"🟢 BMI {bmi:.1f} — Healthy weight")

    # ── Family History (8 pts) ────────────────────────────────────────
    if family == "Yes — father/brother heart attack before 55":
        score += 8; flags.append("🔴 Paternal/brother CAD before 55 — 2x genetic risk")
    elif family == "Yes — mother/sister heart attack before 65":
        score += 6; flags.append("🔴 Maternal/sister CAD before 65 — significant genetic risk")
    elif family == "Yes — but after the above ages":
        score += 3; flags.append("🟡 Family history of CAD (older age onset)")
    else:
        flags.append("🟢 No significant family history of heart disease")

    # ── Chest Pain (10 pts) ───────────────────────────────────────────
    pain_score = {
        "No chest pain":                          0,
        "Mild discomfort — goes away in minutes": 3,
        "Pressure/tightness during exertion":     7,
        "Pressure/tightness at rest":            10,
        "Sharp pain radiating to left arm/jaw":  10,
    }.get(pain_type, 0)
    score += pain_score
    if pain_score >= 10:
        flags.append(f"🔴 Chest pain pattern: '{pain_type}' — HIGH CARDIAC CONCERN")
    elif pain_score >= 7:
        flags.append(f"🟡 Chest pain pattern: '{pain_type}' — Exertional angina pattern")
    elif pain_score > 0:
        flags.append(f"🟡 Chest discomfort noted: '{pain_type}'")
    else:
        flags.append("🟢 No chest pain reported")

    # Pain duration (additional weight)
    if pain_dur == "More than 20 minutes (ongoing or recent)":
        score += 5; flags.append("🔴 Pain duration >20 minutes — possible unstable angina or MI")
    elif pain_dur == "5 to 20 minutes":
        score += 3; flags.append("🟡 Pain duration 5-20 min — concerning, needs evaluation")

    # Angina type distinction
    pain_at_rest = pain_type == "Pressure/tightness at rest"
    if pain_at_rest:
        flags.append("🚨 PAIN AT REST — This pattern suggests Unstable Angina. See cardiologist TODAY.")

    # ── Wearable data ─────────────────────────────────────────────────
    if rhr > 0:
        if rhr > 100:
            score += 5; flags.append(f"🔴 Resting HR {rhr} bpm — Tachycardia (cardiac stress signal)")
        elif rhr > 90:
            score += 3; flags.append(f"🟡 Resting HR {rhr} bpm — Elevated (target 60-80)")
        else:
            flags.append(f"🟢 Resting HR {rhr} bpm — Normal")

    if spo2 > 0 and spo2 < 95:
        score += 6; flags.append(f"🔴 SpO2 {spo2}% — Low oxygen — possible cardiac/pulmonary concern")
    elif spo2 > 0:
        flags.append(f"🟢 SpO2 {spo2}% — Normal oxygen saturation")

    if steps > 0:
        if steps < 3000:
            score += 5; flags.append(f"🔴 {steps:,} steps/day — Very sedentary (35% higher CAD risk)")
        elif steps < 6000:
            score += 2; flags.append(f"🟡 {steps:,} steps/day — Below recommended 8,000+")
        else:
            flags.append(f"🟢 {steps:,} steps/day — Active (protective against CAD)")

    if sleep > 0:
        if sleep < 5:
            score += 4; flags.append(f"🔴 Sleep {sleep}h — Severe deprivation raises BP and cardiac risk")
        elif sleep < 7:
            score += 2; flags.append(f"🟡 Sleep {sleep}h — Below recommended 7-8h")
        else:
            flags.append(f"🟢 Sleep {sleep}h — Adequate rest")

    # ── Alcohol (3 pts) ───────────────────────────────────────────────
    if alcohol in ["Heavy drinker (daily/near daily)", "Very heavy drinker"]:
        score += 5; flags.append("🔴 Heavy alcohol use — cardiac muscle damage (cardiomyopathy) risk")
    elif alcohol == "Moderate (1-2 drinks/day)":
        score += 2; flags.append("🟡 Moderate alcohol — borderline effect")

    # ── Stress (3 pts) ────────────────────────────────────────────────
    if stress_level := data.get("stress_level",""):
        if "Very High" in stress_level:
            score += 4; flags.append("🔴 Very high stress — cortisol raises BP and promotes arterial inflammation")
        elif "High" in stress_level:
            score += 2; flags.append("🟡 High stress — monitor BP closely")

    # ── Symptoms (up to 8 pts) ────────────────────────────────────────
    high_risk_syms = [
        "Breathlessness climbing stairs",
        "Palpitations (heart racing/skipping)",
        "Ankle/leg swelling",
        "Dizziness or near-fainting",
        "Excessive fatigue with mild activity",
        "Cold sweats without exertion",
    ]
    matched = [s for s in symptoms if s in high_risk_syms]
    sym_score = min(len(matched) * 2, 8)
    score += sym_score
    if matched:
        flags.append(f"🟡 Cardiac symptoms: {', '.join(matched)}")

    score = min(score, 100)

    if score >= 60:   risk = "High Risk"
    elif score >= 35: risk = "Moderate Risk"
    else:             risk = "Low Risk"

    return score, risk, flags, pain_at_rest

def _build_home_report(risk, score, data, flags):
    sev_map = {"High Risk":"Severe","Moderate Risk":"Moderate","Low Risk":"Mild"}
    severity = sev_map.get(risk,"Moderate")

    pain_at_rest = data.get("pain_type","") == "Pressure/tightness at rest"

    if risk == "High Risk":
        conditions = [
            {"condition":"Coronary Artery Disease — High Risk",
             "probability": min(40+score*0.4,88),
             "description":"Multiple strong risk factors. Significant probability of coronary artery narrowing.",
             "icd":"I25.1"},
            {"condition":"Hypertensive Heart Disease",
             "probability":8.0,
             "description":"Chronic high BP causing structural changes in the heart.",
             "icd":"I11.9"},
            {"condition":"Angina Pectoris",
             "probability":4.0,
             "description":"Chest pain from reduced blood supply to heart muscle.",
             "icd":"I20.9"},
        ]
        do_list = [
            "🚨 See a Cardiologist within 48 hours — do not delay",
            "Get a 12-lead ECG done at your nearest diagnostic centre (₹200-500)",
            "Get a Fasting Lipid Profile blood test (Total, LDL, HDL, Triglycerides)",
            "Monitor BP twice daily — morning and evening",
            "Start low-sodium diet immediately — less than 2g salt per day",
            "If chest pain occurs — rest immediately and call 108",
            "Take Aspirin 75mg daily if not allergic (confirm with doctor first)",
        ]
        dont_list = [
            "Do NOT ignore any chest pain — even mild pressure",
            "Do NOT exert yourself — avoid stairs, heavy lifting, running",
            "Stop smoking immediately — every cigarette raises heart attack risk",
            "Do NOT eat fried food, red meat, full-fat dairy, packaged snacks",
            "Do NOT drink alcohol — it weakens heart muscle",
            "Do NOT take ibuprofen or diclofenac — they raise BP and cardiac risk",
        ]
        when_doc = [
            "🚨 IMMEDIATELY if chest pain, jaw pain, left arm pain, cold sweat",
            "Within 48 hours for a cardiologist consultation",
            "Call 108 if pain lasts more than 20 minutes and does not stop with rest",
        ]
        specialist = "Cardiologist — URGENT (within 48 hours)"
    elif risk == "Moderate Risk":
        conditions = [
            {"condition":"Elevated Cardiovascular Risk",
             "probability": min(20+score*0.4,70),
             "description":"Several risk factors present. Not yet disease but needs intervention.",
             "icd":"Z82.49"},
            {"condition":"Metabolic Syndrome with Cardiac Risk",
             "probability":15.0,
             "description":"Combination of BP, weight, and sugar risk factors.",
             "icd":"E88.81"},
            {"condition":"Hypertension-Related Cardiac Risk",
             "probability":8.0,
             "description":"Elevated BP contributing to long-term cardiac risk.",
             "icd":"I10"},
        ]
        do_list = [
            "Get a Fasting Lipid Profile blood test this week",
            "Get an ECG done at any diagnostic centre",
            "See a physician within 2 weeks for full cardiac risk evaluation",
            "Walk 30 minutes daily — most effective single intervention",
            "Reduce salt intake — aim for less than 5g per day",
            "Quit smoking if you smoke — single biggest impact",
        ]
        dont_list = [
            "Do not ignore your risk factors — they compound over time",
            "Avoid trans fats, fried food, and packaged snacks",
            "Do not skip your BP medicines if prescribed",
            "Avoid high-stress situations where possible",
        ]
        when_doc = [
            "Within 2 weeks for a physician or cardiologist",
            "Immediately if any new chest pain or breathlessness develops",
            "Annual ECG and lipid profile from now on",
        ]
        specialist = "General Physician or Cardiologist (within 2 weeks)"
    else:
        conditions = [
            {"condition":"Low Cardiac Risk Currently",
             "probability":80.0,
             "description":"No significant risk factors identified. Maintain healthy habits.",
             "icd":"Z03.89"},
            {"condition":"Baseline Cardiovascular Risk",
             "probability":12.0,
             "description":"Everyone carries some baseline cardiac risk — managed with lifestyle.",
             "icd":"Z82.49"},
            {"condition":"Lifestyle-Modifiable Risk",
             "probability":8.0,
             "description":"Some lifestyle factors that may increase future risk if not addressed.",
             "icd":"Z72.3"},
        ]
        do_list = [
            "Continue current lifestyle — it is working",
            "Annual BP and cholesterol check after age 40",
            "Walk 8,000-10,000 steps daily to maintain cardiac fitness",
            "Eat heart-healthy: oats, fish, nuts, fruits, vegetables",
            "Annual ECG after age 45",
        ]
        dont_list = [
            "Do not start smoking — even occasional smoking increases risk",
            "Avoid trans fats and excessive salt long-term",
            "Do not neglect stress management",
        ]
        when_doc = [
            "Annual checkup after age 40",
            "If any chest pain or breathlessness develops",
            "Lipid profile every 3 years",
        ]
        specialist = "General Physician (annual checkup)"

    sev_expl = {
        "High Risk":     "Multiple strong cardiac risk factors detected. Cardiologist consultation urgently needed.",
        "Moderate Risk": "Several risk factors present. Lifestyle changes and medical evaluation recommended soon.",
        "Low Risk":      "No significant cardiac risk factors at this time. Maintain healthy lifestyle.",
    }.get(risk,"")

    sev_reasons = [f.replace("🔴","").replace("🟡","").strip()
                   for f in flags if "🔴" in f or "🟡" in f][:5]

    confidence = min(45 + score * 0.45, 90)

    home_care = [
        "Check and record blood pressure every morning before eating",
        "Walk 10 minutes after every meal — reduces BP and cholesterol",
        "DASH diet: fruits, vegetables, whole grains, low-fat dairy, nuts",
        "Reduce sodium — avoid pickle, papad, packaged food, extra salt",
        "Practice 5 minutes of deep breathing daily — reduces BP measurably",
        "Keep emergency number 108 and your nearest cardiac hospital number saved",
    ]

    extra = f"**Likely condition:** {conditions[0]['condition']} · **See:** {specialist}"

    do_dont = {"do": do_list, "dont": dont_list}
    return severity, sev_expl, sev_reasons, conditions, confidence, do_dont, home_care, when_doc, extra

def _build_clinical_report(result, age, chol, thalach):
    if result == "Positive":
        severity = "Severe"
        conditions = [
            {"condition":"Coronary Artery Disease (CAD)","probability":65.0,
             "description":"Narrowing of coronary arteries due to plaque buildup.","icd":"I25.1"},
            {"condition":"Angina Pectoris","probability":22.0,
             "description":"Chest pain due to reduced blood flow to heart muscle.","icd":"I20.9"},
            {"condition":"Cardiac Ischemia","probability":13.0,
             "description":"Insufficient blood supply to heart muscle.","icd":"I25.9"},
        ]
        sev_expl = "Parameters indicate significant coronary artery disease risk. Seek cardiologist immediately."
        sev_reasons = [f"Age: {age} — risk rises sharply after 55" if age>50 else "",
                       f"Cholesterol: {chol} mg/dL — elevated" if chol>200 else "",
                       f"Max heart rate: {thalach} bpm — stress response" if thalach>150 else ""]
        sev_reasons = [r for r in sev_reasons if r]
        confidence = 85.0
        do_dont = {
            "do": ["🚨 Visit a Cardiologist IMMEDIATELY",
                   "Rest completely — no physical exertion",
                   "Monitor BP and pulse every hour",
                   "Follow DASH diet strictly",
                   "Take prescribed medications without skipping",
                   "Keep 108 and cardiologist number ready at all times"],
            "dont": ["Do NOT ignore chest pain or breathlessness",
                     "Do NOT drive yourself — call 108",
                     "Avoid salt, fried food, trans fats completely",
                     "No smoking or alcohol",
                     "Do NOT take NSAIDs without doctor advice",
                     "Do NOT miss any cardiology follow-up"]
        }
        home_care = ["Record BP twice daily — morning and evening",
                     "Practice deep breathing — 5 minutes every morning",
                     "DASH diet: fruits, vegetables, whole grains, low sodium",
                     "Limit sodium to less than 2g/day",
                     "Sleep on left side — reduces cardiac load",
                     "Keep emergency numbers saved — 108, cardiologist"]
        when_doc  = ["🚨 IMMEDIATELY — do not wait",
                     "If chest tightness, arm pain, or jaw pain develops",
                     "Difficulty breathing even at rest",
                     "Fainting or sudden dizziness"]
        extra = "**Specialists:** Cardiologist (urgent), Interventional Cardiologist, Cardiac Surgeon"
    else:
        severity = "Mild"
        conditions = [
            {"condition":"No Significant CAD Detected","probability":84.0,
             "description":"Cardiac parameters within acceptable range.","icd":"Z03.89"},
            {"condition":"Mild Cardiovascular Risk","probability":10.0,
             "description":"Some risk factors present but no active disease detected.","icd":"Z82.49"},
            {"condition":"Lifestyle-Related Cardiac Risk","probability":6.0,
             "description":"Diet and lifestyle may increase long-term risk.","icd":"Z72.3"},
        ]
        sev_expl = "No significant heart disease detected. Maintain heart-healthy habits."
        sev_reasons = ["Parameters within acceptable clinical range"]
        confidence = 80.0
        do_dont = {
            "do": ["Exercise 30 min/day — walking, cycling, swimming",
                   "Eat heart-healthy: oats, fish, nuts, olive oil",
                   "Annual ECG and lipid profile after age 40",
                   "Manage stress through yoga or meditation",
                   "Maintain healthy BMI (18.5–24.9)"],
            "dont": ["Avoid trans fats, fried food, excess red meat",
                     "Quit smoking if you smoke",
                     "Limit alcohol to minimal amounts",
                     "Do not skip annual cardiac checkup after 40"]
        }
        home_care = ["Morning walk 10 minutes daily",
                     "Replace cooking oil with olive or mustard oil",
                     "5-minute deep breathing daily — proven BP reduction"]
        when_doc  = ["Annual cardiac checkup after age 40",
                     "If chest pain or palpitations develop",
                     "Cholesterol check every 2 years after 30"]
        extra = "✅ Cardiac parameters look healthy. Keep up the lifestyle!"
    return severity, sev_expl, sev_reasons, conditions, confidence, do_dont, home_care, when_doc, extra

# ─── EMERGENCY TRIAGE ─────────────────────────────────────────────────────────
def _render_emergency_triage():
    st.markdown("""<div style="background:#e53935;color:white;border-radius:14px;
        padding:18px 24px;margin-bottom:16px;text-align:center">
        <h2 style="margin:0">🚨 Emergency Heart Attack Triage</h2>
        <p style="margin:6px 0 0;opacity:0.9;font-size:14px">
            Answer 5 quick questions. If you may be having a heart attack right now,
            this screen will tell you immediately.
        </p>
    </div>""", unsafe_allow_html=True)

    st.markdown("""<div style="background:#fff3e0;border-left:5px solid #fb8c00;
        border-radius:10px;padding:12px 18px;font-size:13px;margin-bottom:16px">
        ⚠️ <b>Golden Window:</b> In a heart attack, every minute matters.
        Opening a blocked artery within 90 minutes saves the heart muscle.
        After 6 hours, damage becomes permanent. <b>Do not delay if any 3 answers are YES.</b>
    </div>""", unsafe_allow_html=True)

    st.markdown("### Answer honestly — these 5 questions take 30 seconds")

    q1 = st.checkbox("1. 🫀 Do you have chest pain, pressure, or tightness RIGHT NOW?")
    q2 = st.checkbox("2. 💪 Is the pain or discomfort spreading to your left arm, jaw, neck, or back?")
    q3 = st.checkbox("3. 💧 Are you sweating unusually, feeling cold and clammy — without a reason?")
    q4 = st.checkbox("4. 😮‍💨 Are you short of breath, even sitting still?")
    q5 = st.checkbox("5. ⏰ Did these symptoms start in the last 2 hours?")

    yes_count = sum([q1, q2, q3, q4, q5])

    if st.button("🔍 Check My Emergency Status", use_container_width=True):
        if yes_count >= 3:
            st.markdown("""<div style="background:#b71c1c;color:white;border-radius:16px;
                padding:28px 32px;text-align:center;margin:12px 0;
                box-shadow:0 6px 30px rgba(183,28,28,0.5);animation:pulse 1s infinite">
                <h1 style="margin:0;font-size:2.5em">🚨 CALL 108 NOW</h1>
                <h2 style="margin:12px 0;opacity:0.95">THIS MAY BE A HEART ATTACK</h2>
                <p style="font-size:16px;margin:10px 0">
                    <b>3 or more emergency signs are present.</b><br>
                    Do NOT use this app further. Do NOT drive yourself.<br>
                    Ask someone to call 108 immediately.
                </p>
                <div style="background:white;color:#b71c1c;border-radius:10px;
                    padding:14px 20px;margin:14px 0;font-size:1.8em;font-weight:800">
                    📞 108 — Free Ambulance (India)
                </div>
                <p style="font-size:13px;opacity:0.9">
                    While waiting: Sit or lie down · Loosen tight clothing ·
                    Chew 1 Aspirin 325mg if available and not allergic ·
                    Unlock your front door · Stay calm
                </p>
            </div>""", unsafe_allow_html=True)

        elif yes_count == 2:
            st.markdown("""<div style="background:#e53935;color:white;border-radius:14px;
                padding:20px 28px;text-align:center;margin:12px 0">
                <h2 style="margin:0">⚠️ HIGH CONCERN — Go to a Hospital Now</h2>
                <p style="margin:10px 0;font-size:14px">
                    2 warning signs are present. This may be cardiac or another serious condition.<br>
                    <b>Do not wait — go to the nearest hospital's emergency department now.</b><br>
                    If symptoms worsen or you feel very unwell — call 108 immediately.
                </p>
                <div style="font-size:1.4em;font-weight:700;margin-top:10px">
                    📞 108 — Free Ambulance &nbsp;|&nbsp; 📞 104 — Health Helpline
                </div>
            </div>""", unsafe_allow_html=True)

        elif yes_count == 1:
            st.markdown("""<div style="background:#fb8c00;color:white;border-radius:14px;
                padding:16px 24px;text-align:center;margin:12px 0">
                <h3 style="margin:0">🟡 Monitor Closely — See a Doctor Today</h3>
                <p style="margin:8px 0;font-size:13px">
                    1 warning sign present. Not an immediate emergency but do not ignore it.<br>
                    Book a doctor appointment for today or tomorrow.<br>
                    If any additional symptoms develop — go to emergency immediately.
                </p>
            </div>""", unsafe_allow_html=True)

        else:
            st.markdown("""<div style="background:#43a047;color:white;border-radius:14px;
                padding:16px 24px;text-align:center;margin:12px 0">
                <h3 style="margin:0">✅ No Active Emergency Signs</h3>
                <p style="margin:8px 0;font-size:13px">
                    None of the emergency indicators are present right now.<br>
                    You can proceed to the Home Screener or Clinical ML tab
                    to assess your long-term cardiac risk.
                </p>
            </div>""", unsafe_allow_html=True)

        # Always show these
        st.markdown("""<div style="background:#f8f9fa;border-radius:10px;padding:14px 18px;
            font-size:13px;margin-top:12px;border:1px solid #e0e0e0">
            <b>🏥 India Emergency Numbers:</b><br>
            📞 <b>108</b> — Free Ambulance (all states) &nbsp;·&nbsp;
            📞 <b>104</b> — Health Helpline &nbsp;·&nbsp;
            📞 <b>112</b> — National Emergency &nbsp;·&nbsp;
            📞 <b>1800-180-1104</b> — Cardiac helpline
        </div>""", unsafe_allow_html=True)

# ─── MAIN SHOW ────────────────────────────────────────────────────────────────
def show():
    uid   = st.session_state.user_id
    uname = st.session_state.get("full_name","Patient")

    st.markdown("""<div class="main-header">
        <h1>❤️ Heart Disease Assessment</h1>
        <p>Emergency triage · Home cardiac screener · Clinical ML model with Explainable AI</p>
    </div>""", unsafe_allow_html=True)

    emerg_tab, home_tab, clinical_tab = st.tabs([
        "🚨 Emergency Triage — Am I Having a Heart Attack?",
        "🏠 Home Cardiac Screener — Long-term Risk",
        "🔬 Clinical ML Model — With Lab Reports",
    ])

    # ════════════════════════════════════════════════════════════════════
    # TAB 1 — EMERGENCY TRIAGE
    # ════════════════════════════════════════════════════════════════════
    with emerg_tab:
        _render_emergency_triage()

    # ════════════════════════════════════════════════════════════════════
    # TAB 2 — HOME SCREENER
    # ════════════════════════════════════════════════════════════════════
    with home_tab:
        st.markdown("""<div style="background:#e8f5e9;border-left:5px solid #43a047;
            border-radius:10px;padding:12px 18px;font-size:14px;margin-bottom:16px">
            🏠 <b>This is for anyone at home.</b> Uses only what you actually have —
            BP machine, glucometer, smartwatch, and your own symptoms and lifestyle.
            No ECG, no TMT, no lab visit required.
            Assesses long-term coronary artery disease risk using WHO SCORE-India factors.
        </div>""", unsafe_allow_html=True)

        # ── SECTION 1: About You ──────────────────────────────────────
        st.markdown("### 👤 About You")
        a1, a2, a3 = st.columns(3)
        with a1:
            h_age    = st.number_input("🎂 Age", 18, 120, 45, key="h_age")
            h_sex    = st.selectbox("⚤ Sex", ["Male","Female"], key="h_sex")
        with a2:
            h_weight = st.number_input("⚖️ Weight (kg)", 30.0, 200.0, 70.0, step=0.5)
            h_height = st.number_input("📏 Height (cm)", 100.0, 220.0, 168.0, step=0.5)
        with a3:
            h_family = st.selectbox("👨‍👩‍👧 Family History of Heart Attack",
                ["None / Not known",
                 "Yes — father/brother heart attack before 55",
                 "Yes — mother/sister heart attack before 65",
                 "Yes — but after the above ages"])
        h_bmi = round(h_weight/((h_height/100)**2), 1)
        bmi_label = ("🟢 Healthy" if h_bmi<25 else ("🟡 Overweight" if h_bmi<30 else "🔴 Obese"))
        st.markdown(f"""<div style="background:#e3f2fd;border-radius:8px;padding:8px 14px;
            font-size:13px;border-left:4px solid #1565c0;margin-bottom:4px">
            📊 Your BMI: <b>{h_bmi}</b> — {bmi_label}
        </div>""", unsafe_allow_html=True)

        st.markdown("---")

        # ── SECTION 2: Home Devices ───────────────────────────────────
        st.markdown("### 🩺 Home Device Readings")
        d1, d2, d3 = st.columns(3)
        with d1:
            st.markdown("**💓 Blood Pressure (BP machine)**")
            h_sys = st.number_input("Systolic (top number) mmHg", 70, 260, 120)
            h_dia = st.number_input("Diastolic (bottom number) mmHg", 40, 160, 80)
            if h_sys > 0:
                bp_s = ("🔴 Hypertensive Crisis" if h_sys>=180 else
                        "🔴 Stage 2 HTN" if h_sys>=160 else
                        "🔴 Stage 1 HTN" if h_sys>=140 else
                        "🟡 Elevated" if h_sys>=130 else "🟢 Normal")
                st.caption(f"BP Status: {bp_s}")
        with d2:
            st.markdown("**🩸 Blood Sugar (Glucometer)**")
            h_fbs = st.number_input("Fasting Blood Sugar (mg/dL) — 0 to skip", 0, 500, 0)
            if h_fbs > 0:
                fbs_s = ("🔴 Diabetic" if h_fbs>126 else ("🟡 Pre-diabetic" if h_fbs>100 else "🟢 Normal"))
                st.caption(f"Sugar Status: {fbs_s}")
        with d3:
            st.markdown("**🧪 Cholesterol (Lab Report)**")
            h_chol = st.number_input("Total Cholesterol mg/dL — 0 to skip", 0, 600, 0)
            h_hdl  = st.number_input("HDL (Good) Cholesterol mg/dL — 0 to skip\n(makes ratio much more accurate)", 0, 200, 0)
            if h_chol > 0 and h_hdl > 0:
                ratio = h_chol/h_hdl
                ratio_s = ("🔴 Very High Risk" if ratio>6 else
                            "🔴 High Risk" if ratio>5 else
                            "🟡 Borderline" if ratio>4 else "🟢 Good")
                st.caption(f"Chol/HDL Ratio: {ratio:.1f} — {ratio_s}")

        st.markdown("---")

        # ── SECTION 3: Smartwatch ─────────────────────────────────────
        st.markdown("### ⌚ Smartwatch / Fitness Tracker")
        w1, w2, w3 = st.columns(3)
        with w1:
            h_rhr   = st.number_input("Resting HR (bpm) — 0 to skip", 0, 200, 0)
        with w2:
            h_spo2  = st.number_input("SpO2 % — 0 to skip", 0, 100, 0)
        with w3:
            h_steps = st.number_input("Daily Steps — 0 to skip", 0, 50000, 0, step=100)
        h_sleep = st.number_input("Sleep last night (hours) — 0 to skip", 0.0, 14.0, 0.0, step=0.5)

        st.markdown("---")

        # ── SECTION 4: Chest Pain ─────────────────────────────────────
        st.markdown("### 🫀 Chest Pain — Describe What You Feel")
        st.markdown("""<div style="background:#fff3e0;border-left:4px solid #fb8c00;
            border-radius:8px;padding:10px 14px;font-size:13px;margin-bottom:10px">
            ⚠️ <b>Important:</b> Do not describe using medical terms. Just describe what you feel.
            If you have chest pain RIGHT NOW that is severe — go to Emergency Triage tab first.
        </div>""", unsafe_allow_html=True)
        p1, p2 = st.columns(2)
        with p1:
            h_pain_type = st.selectbox("What does your chest feel like?",
                ["No chest pain",
                 "Mild discomfort — goes away in minutes",
                 "Pressure/tightness during exertion",
                 "Pressure/tightness at rest",
                 "Sharp pain radiating to left arm/jaw"])
        with p2:
            h_pain_dur  = st.selectbox("How long does the discomfort last?",
                ["No pain / Not applicable",
                 "Seconds only",
                 "1 to 5 minutes",
                 "5 to 20 minutes",
                 "More than 20 minutes (ongoing or recent)"])

        st.markdown("---")

        # ── SECTION 5: Lifestyle ──────────────────────────────────────
        st.markdown("### 🏃 Lifestyle Factors")
        l1, l2, l3 = st.columns(3)
        with l1:
            h_smoke = st.selectbox("🚬 Smoking Status",
                ["Never smoked",
                 "Ex-smoker (quit > 5 years ago)",
                 "Ex-smoker (quit < 5 years ago)",
                 "Current smoker (occasional)",
                 "Current smoker (daily)"])
        with l2:
            h_alcohol = st.selectbox("🍺 Alcohol",
                ["Non-drinker",
                 "Occasional (social only)",
                 "Moderate (1-2 drinks/day)",
                 "Heavy drinker (daily/near daily)"])
        with l3:
            h_stress  = st.selectbox("😰 Stress Level",
                ["Low — calm and settled",
                 "Moderate — normal daily stress",
                 "High — significant pressure",
                 "Very High — crisis level"])

        st.markdown("---")

        # ── SECTION 6: Symptoms ───────────────────────────────────────
        st.markdown("### 🤒 Symptoms (Tick All That Apply)")
        sym_opts = [
            "Breathlessness climbing stairs",
            "Palpitations (heart racing/skipping)",
            "Ankle/leg swelling",
            "Dizziness or near-fainting",
            "Excessive fatigue with mild activity",
            "Cold sweats without exertion",
            "None of the above",
        ]
        sc = st.columns(4)
        h_symptoms = []
        for i, sym in enumerate(sym_opts):
            with sc[i % 4]:
                if st.checkbox(sym, key=f"hsym_h_{sym}"):
                    h_symptoms.append(sym)

        st.markdown("---")

        if st.button("🔍 Run Home Cardiac Risk Assessment", use_container_width=True):
            data = {
                "age": h_age, "sex": h_sex, "bmi": h_bmi,
                "systolic_bp": h_sys, "diastolic_bp": h_dia,
                "resting_hr": h_rhr, "spo2": h_spo2, "daily_steps": h_steps,
                "sleep_hours": h_sleep, "fasting_sugar": h_fbs,
                "cholesterol": h_chol, "hdl": h_hdl,
                "smoking": h_smoke, "alcohol": h_alcohol,
                "stress_level": h_stress, "family_history": h_family,
                "pain_type": h_pain_type, "pain_duration": h_pain_dur,
                "symptoms": h_symptoms,
            }
            score, risk, flags, pain_at_rest = _home_cardiac_score(data)

            risk_color = {"High Risk":"#e53935","Moderate Risk":"#fb8c00","Low Risk":"#43a047"}.get(risk,"#888")
            risk_icon  = {"High Risk":"🚨","Moderate Risk":"⚠️","Low Risk":"✅"}.get(risk,"⚪")

            # Unstable angina warning — override
            if pain_at_rest:
                st.markdown("""<div style="background:#b71c1c;color:white;border-radius:14px;
                    padding:20px 28px;text-align:center;margin:12px 0">
                    <h2 style="margin:0">🚨 UNSTABLE ANGINA WARNING</h2>
                    <p style="margin:10px 0;font-size:14px">
                        Chest pressure or tightness AT REST is the classic sign of Unstable Angina —
                        which can rapidly progress to a heart attack.<br>
                        <b>Do not wait. Go to a cardiac emergency department TODAY.</b>
                    </p>
                    <div style="font-size:1.6em;font-weight:800;margin-top:10px">
                        📞 108 — Free Ambulance
                    </div>
                </div>""", unsafe_allow_html=True)

            st.markdown(f"""<div style="background:{risk_color};color:white;border-radius:16px;
                padding:22px 32px;text-align:center;margin:12px 0;
                box-shadow:0 6px 24px {risk_color}44">
                <h1 style="margin:0;font-size:2em">{risk_icon} {risk}</h1>
                <h3 style="margin:8px 0 0;opacity:0.95">Cardiac Risk Score: {score}/100</h3>
            </div>""", unsafe_allow_html=True)

            # Score meter
            st.markdown(f"""<div style="background:#f0f0f0;border-radius:8px;height:16px;margin:8px 0">
                <div style="background:linear-gradient(90deg,#43a047,#fb8c00,#e53935);
                    width:{score}%;height:16px;border-radius:8px"></div>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:10px;color:#aaa;margin-bottom:12px">
                <span>0 — Low</span><span>35 — Moderate</span><span>60 — High</span><span>100</span>
            </div>""", unsafe_allow_html=True)

            # Stable vs Unstable distinction panel
            stable_angina = h_pain_type == "Pressure/tightness during exertion"
            if stable_angina:
                st.markdown("""<div style="background:#fff3e0;border-left:5px solid #fb8c00;
                    border-radius:10px;padding:14px 18px;font-size:13px;margin:8px 0">
                    <b>⚠️ Stable Angina Pattern Detected:</b> Chest tightness during exertion that
                    goes away with rest is the pattern of <b>Stable Angina</b> — coronary arteries
                    narrowed but not completely blocked. This needs a cardiologist appointment
                    within 1 week for a proper stress test (TMT). Do not exercise vigorously
                    until evaluated.
                </div>""", unsafe_allow_html=True)

            rt1, rt2, rt3 = st.tabs(["📋 Factor Analysis",
                                      "📄 Full Report & Advice",
                                      "🧠 Explainable AI"])
            with rt1:
                st.markdown("### 🔍 Factor-by-Factor Breakdown")
                for f in flags:
                    bg = ("#ffebee" if "🔴" in f or "🚨" in f else
                          "#fff8e1" if "🟡" in f else
                          "#e8f5e9" if "🟢" in f else "#f0f4ff")
                    bd = ("#e53935" if "🔴" in f or "🚨" in f else
                          "#fb8c00" if "🟡" in f else
                          "#43a047" if "🟢" in f else "#1565c0")
                    st.markdown(f"""<div style="background:{bg};border-left:4px solid {bd};
                        border-radius:8px;padding:9px 14px;margin:4px 0;font-size:13px">
                        {f}</div>""", unsafe_allow_html=True)

                # Cholesterol explanation
                if h_chol > 0:
                    st.markdown("""<div style="background:#e3f2fd;border-left:4px solid #1565c0;
                        border-radius:10px;padding:12px 16px;font-size:13px;margin-top:10px">
                        💡 <b>About Cholesterol:</b> Your app uses Total Cholesterol.
                        But what actually matters is the ratio of Total Cholesterol to HDL (good cholesterol).
                        A total of 240 with HDL of 60 = ratio 4.0 = LOW risk.
                        A total of 200 with HDL of 28 = ratio 7.1 = VERY HIGH risk.
                        Same total number — completely different risk. Always ask your doctor for
                        your HDL value separately.
                    </div>""", unsafe_allow_html=True)

            with rt2:
                severity, sev_expl, sev_reasons, conditions, confidence, do_dont, home_care, when_doc, extra = \
                    _build_home_report(risk, score, data, flags)
                render_clinical_report("Heart Disease Home Screening", severity, sev_expl, sev_reasons,
                                        conditions, confidence, do_dont, home_care, when_doc, extra,
                                        patient_name=uname, vital_summary=None)

            with rt3:
                explanation = explain_heart(h_age, h_chol if h_chol>0 else 200,
                                             150, 1.0, 0, 0, h_sys, risk)
                render_xai_panel(explanation, "Heart Disease Home Screening")

            save_report(uid, "Heart Disease Home Screening", severity,
                        conditions[0]["condition"], confidence,
                        f"Age:{h_age}|BP:{h_sys}/{h_dia}|Score:{score}|Risk:{risk}",
                        numeric_value=h_sys)
            st.success("✅ Assessment saved to your history.")

    # ════════════════════════════════════════════════════════════════════
    # TAB 3 — CLINICAL ML MODEL
    # ════════════════════════════════════════════════════════════════════
    with clinical_tab:
        st.markdown("""<div style="background:#e3f2fd;border-left:5px solid #1565c0;
            border-radius:10px;padding:12px 18px;font-size:14px;margin-bottom:16px">
            🔬 <b>Clinical Mode:</b> For patients who have done an ECG, Treadmill Stress Test (TMT),
            and have their Lipid Profile report. Uses the Cleveland Heart Disease ML model
            with Explainable AI. <b>All 13 parameters require clinical testing.</b>
        </div>""", unsafe_allow_html=True)

        st.markdown("""<div style="background:#fff3e0;border-left:4px solid #fb8c00;
            border-radius:8px;padding:10px 14px;font-size:13px;margin-bottom:12px">
            📋 <b>Where to get these values:</b> Resting BP → home BP machine ·
            Cholesterol → any diagnostic lab (₹150) · ECG findings → cardiologist clinic ·
            Max Heart Rate, ST Depression, Slope → from your TMT/Treadmill Test report ·
            No. of Vessels → from Coronary Angiography or CT Coronary Angiogram ·
            Thalassemia → from blood test with doctor referral
        </div>""", unsafe_allow_html=True)

        with st.expander("ℹ️ Parameter Guide — What Each Value Means"):
            st.markdown("""
| Parameter | Values | What It Measures |
|---|---|---|
| Chest Pain Type | 0=Typical Angina, 1=Atypical, 2=Non-anginal, 3=Asymptomatic | Type of chest pain — Typical is highest risk |
| Fasting Blood Sugar | 0=≤120 mg/dL, 1=>120 mg/dL | Diabetes doubles cardiac risk |
| Resting ECG | 0=Normal, 1=ST-T Abnormality, 2=LV Hypertrophy | Heart's electrical activity at rest |
| Max Heart Rate | Beats/min during stress test | How high heart rate goes under exertion |
| Exercise Angina | Yes/No | Chest pain triggered by exercise — classic CAD sign |
| ST Depression | 0-10 (mm) | How much ST segment drops during exercise — most important ECG finding |
| ST Slope | 0=Upsloping, 1=Flat, 2=Downsloping | Direction of ST change — Downsloping is most dangerous |
| Major Vessels | 0-3 | Number of coronary arteries with significant blockage |
| Thalassemia | 0=Normal, 1=Fixed Defect, 2=Reversible Defect | Blood oxygen-carrying disorder |
            """)

        st.markdown("### 📝 Enter Clinical Parameters")
        c1, c2, c3 = st.columns(3)
        with c1:
            age      = st.number_input("Age", 1, 120, 45, key="cl_age")
            sex      = st.selectbox("Sex", ["Male","Female"], key="cl_sex")
            cp       = st.selectbox("Chest Pain Type", [0,1,2,3], key="cl_cp",
                                    format_func=lambda x:["Typical Angina","Atypical Angina","Non-anginal","Asymptomatic"][x])
            trestbps = st.number_input("Resting Blood Pressure (mmHg)", 80, 220, 120, key="cl_bp")
            chol     = st.number_input("Serum Cholesterol (mg/dL)", 100, 600, 200, key="cl_chol")
        with c2:
            fbs      = st.selectbox("Fasting Blood Sugar >120?", [0,1], key="cl_fbs",
                                    format_func=lambda x:"Yes" if x else "No")
            restecg  = st.selectbox("Resting ECG", [0,1,2], key="cl_ecg",
                                    format_func=lambda x:["Normal","ST-T Abnormality","LV Hypertrophy"][x])
            thalach  = st.number_input("Max Heart Rate Achieved", 60, 250, 150, key="cl_thal")
            exang    = st.selectbox("Exercise Induced Angina", [0,1], key="cl_exang",
                                    format_func=lambda x:"Yes" if x else "No")
        with c3:
            oldpeak  = st.number_input("ST Depression (Oldpeak)", 0.0, 10.0, 1.0, step=0.1, key="cl_op")
            slope    = st.selectbox("Slope of ST Segment", [0,1,2], key="cl_slope",
                                    format_func=lambda x:["Upsloping","Flat","Downsloping"][x])
            ca       = st.selectbox("No. of Major Vessels (0-3)", [0,1,2,3], key="cl_ca")
            thal     = st.selectbox("Thalassemia", [0,1,2], key="cl_thal2",
                                    format_func=lambda x:["Normal","Fixed Defect","Reversible Defect"][x])

        sex_n = 1 if sex == "Male" else 0

        if st.button("🔍 Run Clinical Heart Disease Assessment", use_container_width=True):
            from sklearn.preprocessing import StandardScaler
            raw = np.array([[age,sex_n,cp,trestbps,chol,fbs,restecg,
                             thalach,exang,oldpeak,slope,ca,thal]], dtype=float)
            scaler = StandardScaler()
            # Cleveland dataset mean and std for manual scaling
            means = np.array([54.4,0.68,0.97,131.6,246.7,0.15,0.99,149.6,0.33,1.04,1.40,0.73,2.31])
            stds  = np.array([9.04,0.47,1.03,17.52,51.78,0.36,1.00,22.88,0.47,1.16,0.62,1.02,0.61])
            inp   = (raw - means) / stds
            pred   = MODEL.predict(inp)[0]
            result = "Positive" if pred==1 else "Negative"

            severity, sev_expl, sev_reasons, conditions, confidence, do_dont, home_care, when_doc, extra = \
                _build_clinical_report(result, age, chol, thalach)

            res_color = "#e53935" if result=="Positive" else "#43a047"
            res_icon  = "🚨" if result=="Positive" else "✅"
            st.markdown(f"""<div style="background:{res_color};color:white;border-radius:16px;
                padding:20px 28px;text-align:center;margin:16px 0;
                box-shadow:0 4px 20px {res_color}44">
                <h2 style="margin:0;font-size:1.8em">{res_icon} Cardiac Result: {result}</h2>
                <p style="margin:6px 0 0;opacity:0.9">{sev_expl}</p>
            </div>""", unsafe_allow_html=True)

            # Cholesterol type education
            if chol > 0:
                st.markdown(f"""<div style="background:#e3f2fd;border-left:4px solid #1565c0;
                    border-radius:10px;padding:12px 16px;font-size:13px;margin:8px 0">
                    ℹ️ <b>Cholesterol Note:</b> This model uses Total Serum Cholesterol ({chol} mg/dL).
                    For a more accurate cardiac risk picture, ask your doctor for your
                    <b>LDL, HDL, and Triglycerides</b> separately.
                    Total/HDL ratio below 4.0 is the real target — not just the total number.
                </div>""", unsafe_allow_html=True)

            # Stable vs unstable distinction for clinical
            if cp == 0 and exang == 1:
                st.markdown("""<div style="background:#ffebee;border-left:4px solid #e53935;
                    border-radius:10px;padding:12px 16px;font-size:13px;margin:8px 0">
                    ⚠️ <b>Angina Pattern:</b> Typical Angina + Exercise-induced Angina = classic
                    <b>Stable Angina</b> pattern — coronary arteries narrowed but not acutely blocked.
                    Needs cardiology workup. If angina occurs at rest — treat as Unstable Angina emergency.
                </div>""", unsafe_allow_html=True)

            tab1, tab2 = st.tabs(["🧠 Explainable AI — Why this result?",
                                   "📄 Full Clinical Report"])
            with tab1:
                explanation = explain_heart(age, chol, thalach, oldpeak, ca, cp, trestbps, result)
                render_xai_panel(explanation, "Heart Disease Prediction")
            with tab2:
                render_clinical_report("Heart Disease", severity, sev_expl, sev_reasons,
                                        conditions, confidence, do_dont, home_care, when_doc, extra,
                                        patient_name=uname, vital_summary=None)

            save_report(uid, "Heart Disease", severity,
                        conditions[0]["condition"], confidence,
                        f"Age:{age}|Chol:{chol}|Thalach:{thalach}|Result:{result}",
                        numeric_value=chol)
            st.success("✅ Report saved to your history.")

    st.markdown("""<div class="footer">
        MediSense Pro · Heart Disease Assessment v10 · SWE1904 · VIT · R.Divya 21MIS0261
    </div>""", unsafe_allow_html=True)
